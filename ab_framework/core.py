"""Core ABTest class for experiment analysis."""

from typing import Dict, List, Callable, Optional, Any, Literal
import pandas as pd
import numpy as np
from datetime import datetime
import traceback

from .backends import AbexpBackend, StatisticalBackend
from .quality import QualityChecker

class ABTest:
    """Main class for A/B test analysis.
    
    This class orchestrates the entire A/B testing workflow:
    - Metric registration
    - Data validation
    - Statistical testing
    - Multi-metric orchestration
    - Quality checks (SRM)
    - Result reporting
    
    Example:
        >>> test = ABTest(
        ...     name="homepage_redesign",
        ...     data=df,
        ...     variant_col="variant",
        ...     unit_id="user_id"
        ... )
        >>> 
        >>> @test.metric
        ... def conversion_rate(data):
        ...     return data.groupby('user_id')['converted'].max()
        >>> 
        >>> results = test.analyze(['conversion_rate'])
        >>> print(results.summary())
    """
    
    def __init__(
        self,
        name: str,
        data: pd.DataFrame,
        variant_col: str = 'variant',
        unit_id: str = 'user_id',
        backend: Optional[StatisticalBackend] = None,
        alpha: float = 0.05,
        variants: Optional[List[str]] = None,
    ):
        """Initialize A/B test.
        
        Args:
            name: Experiment name
            data: DataFrame with experiment data (event-level or aggregated)
            variant_col: Column name containing variant assignments ('A', 'B', etc.)
            unit_id: Column name for randomization unit (usually 'user_id')
            backend: Statistical backend (defaults to AbexpBackend)
            alpha: Significance level (default 0.05)
        """
        self.name = name
        self.data = data.copy()
        self.variant_col = variant_col
        self.unit_id = unit_id
        self.backend = backend if backend is not None else AbexpBackend()
        self.alpha = alpha
        self.timestamp = datetime.now().isoformat()
        
        # Explicit variants configuration (e.g. ["A", "B"])
        self.variants: Optional[List[str]] = variants
        
        # Metric registry: name -> metadata dict.
        # For backward compatibility this at least contains:
        #   {"func": callable, "metric_type": str}
        # Additional fields (role, mde, non_inferiority_margin, etc.)
        # can be added later without breaking existing users.
        self._metrics: Dict[str, Dict[str, Any]] = {}
        
        # Validate inputs
        self._validate_data()
    
    def _validate_data(self):
        """Validate input data structure."""
        if self.variant_col not in self.data.columns:
            raise ValueError(f"Variant column '{self.variant_col}' not found in data")
        
        if self.unit_id not in self.data.columns:
            raise ValueError(f"Unit ID column '{self.unit_id}' not found in data")
        
        data_variants = sorted(self.data[self.variant_col].unique())
        if len(data_variants) < 2:
            raise ValueError(f"Need at least 2 variants, found {len(data_variants)}")
        
        # If explicit variants were provided, validate them against the data
        if self.variants is not None:
            if len(self.variants) != 2:
                raise ValueError(f"'variants' must contain exactly 2 labels, got {self.variants}")
            missing = [v for v in self.variants if v not in data_variants]
            if missing:
                raise ValueError(f"Configured variants {missing} not found in data")
        else:
            # Default: first 2 variants in sorted order
            self.variants = data_variants[:2]
    
    def metric(
        self,
        func: Callable = None,
        *,
        metric_type: str,
        is_primary: bool = False,
        monitor_alpha: Optional[float] = None,
        monitor_power: Optional[float] = None,
        inferiority_margin: Optional[float] = None,
    ) -> Callable:
        """Decorator to register a metric function.
        
        The metric function should take a DataFrame and return a pandas Series
        indexed by unit_id with the metric value for each unit.

        Args:
            func: Metric function that takes DataFrame and returns Series.
                When omitted (i.e. using ``@test.metric(metric_type="proportion")``),
                the decorator will return a configured wrapper.
            metric_type: Required hint for how this metric should be analyzed.
                Supported values:

                - ``"proportion"``: binary proportion metric (0/1), analyzed via
                  :meth:`StatisticalBackend.proportion_z_test`.
                - ``"mean"``: continuous metric, analyzed via
                  :meth:`StatisticalBackend.mean_t_test`.
        
        Returns:
            The original function (unchanged).
        """

        def decorator(f: Callable) -> Callable:
            if metric_type not in ("proportion", "mean"):
                raise ValueError("metric_type must be 'proportion' or 'mean'")
            # Track primary metric (only one allowed)
            if is_primary:
                existing_primary = getattr(self, "_primary_metric", None)
                if existing_primary is not None and existing_primary != f.__name__:
                    raise ValueError(f"Primary metric already set to '{existing_primary}'. Only one primary metric is allowed.")
                self._primary_metric = f.__name__
            self._metrics[f.__name__] = {
                "func": f,
                "metric_type": metric_type,
                "is_primary": is_primary,
                "monitor_alpha": monitor_alpha,
                "monitor_power": monitor_power,
                "inferiority_margin": inferiority_margin,
            }
            return f

        # Support both @test.metric and @test.metric(...)
        if func is not None:
            return decorator(func)
        return decorator
    
    def register_metric(
        self,
        name: str,
        func: Callable,
        metric_type: str,
        is_primary: bool = False,
        monitor_alpha: Optional[float] = None,
        monitor_power: Optional[float] = None,
        inferiority_margin: Optional[float] = None,
    ):
        """Register a metric function programmatically.
        
        Alternative to the @metric decorator for dynamic registration.
        
        Args:
            name: Metric name
            func: Metric function that takes DataFrame and returns Series
            metric_type: Type hint ("proportion" or "mean").
        """
        if metric_type not in ("proportion", "mean"):
            raise ValueError("metric_type must be 'proportion' or 'mean'")
        if is_primary:
            existing_primary = getattr(self, "_primary_metric", None)
            if existing_primary is not None and existing_primary != name:
                raise ValueError(f"Primary metric already set to '{existing_primary}'. Only one primary metric is allowed.")
            self._primary_metric = name
        self._metrics[name] = {
            "func": func,
            "metric_type": metric_type,
            "is_primary": is_primary,
            "monitor_alpha": monitor_alpha,
            "monitor_power": monitor_power,
            "inferiority_margin": inferiority_margin,
        }

    def set_primary_metric(self, metric_name: str):
        """Convenience method to set the primary metric after registration."""
        if metric_name not in self._metrics:
            raise ValueError(f"Primary metric '{metric_name}' is not registered")
        existing_primary = getattr(self, "_primary_metric", None)
        if existing_primary is not None and existing_primary != metric_name:
            raise ValueError(f"Primary metric already set to '{existing_primary}'. Only one primary metric is allowed.")
        self._primary_metric = metric_name
        # Update registry flag for consistency
        self._metrics[metric_name]["is_primary"] = True
    
    def _compute_metric(self, metric_name: str) -> pd.DataFrame:
        """Compute metric values for all units.
        
        Args:
            metric_name: Name of registered metric
        
        Returns:
            DataFrame with columns: [unit_id, variant, metric_value]
        """
        if metric_name not in self._metrics:
            raise ValueError(f"Metric '{metric_name}' not registered")
        entry = self._metrics[metric_name]
        metric_func = entry["func"]
        
        # Apply metric function
        metric_values = metric_func(self.data)
        
        # Convert to DataFrame if Series
        if isinstance(metric_values, pd.Series):
            metric_df = metric_values.reset_index()
            metric_df.columns = [self.unit_id, 'metric_value']
        else:
            raise TypeError(f"Metric function must return pandas Series, got {type(metric_values)}")
        
        # Join with variant assignments
        variants = self.data[[self.unit_id, self.variant_col]].drop_duplicates()
        result = metric_df.merge(variants, on=self.unit_id, how='left')
        
        return result
    
    def _test_metric(
        self,
        metric_name: str,
        variant_a: str,
        variant_b: str
    ) -> Dict[str, Any]:
        """Test a single metric between two variants.
        
        Args:
            metric_name: Name of metric to test
            variant_a: Control variant name
            variant_b: Treatment variant name
        
        Returns:
            Dictionary with test results
        """
        # Compute metric
        metric_df = self._compute_metric(metric_name)
        
        # Split by variant
        data_a = metric_df[metric_df[self.variant_col] == variant_a]['metric_value'].values
        data_b = metric_df[metric_df[self.variant_col] == variant_b]['metric_value'].values
        
        if len(data_a) == 0 or len(data_b) == 0:
            raise ValueError(f"No data for one or both variants: {variant_a}={len(data_a)}, {variant_b}={len(data_b)}")
        
        # Determine metric type (must be provided at registration time)
        entry = self._metrics.get(metric_name)
        if not entry or "metric_type" not in entry:
            raise ValueError(
                f"Metric '{metric_name}' is missing required metric_type; "
                "register it with metric_type='proportion' or 'mean'."
            )
        metric_type = entry["metric_type"]

        if metric_type == "proportion":
            # Proportion test
            successes_a = int(data_a.sum())
            trials_a = len(data_a)
            successes_b = int(data_b.sum())
            trials_b = len(data_b)
            
            result = self.backend.proportion_z_test(
                successes_a=successes_a,
                trials_a=trials_a,
                successes_b=successes_b,
                trials_b=trials_b,
                alpha=self.alpha,
            )
            result["metric_type"] = "binary"
            result["control_value"] = successes_a / trials_a
            result["treatment_value"] = successes_b / trials_b
            # Fallback dispersion metrics when backend doesn't provide them
            try:
                p_a = result["control_value"]
                p_b = result["treatment_value"]
                # Standard deviation of Bernoulli variable per group
                std_a = float(np.sqrt(p_a * (1.0 - p_a)))
                std_b = float(np.sqrt(p_b * (1.0 - p_b)))
                # Pooled proportion and its std (Bernoulli)
                p_pool = (successes_a + successes_b) / float(trials_a + trials_b)
                std_pool = float(np.sqrt(p_pool * (1.0 - p_pool)))
                result.setdefault("std_control", std_a)
                result.setdefault("std_treatment", std_b)
                result.setdefault("std_pooled", std_pool)
            except Exception:
                pass
        elif metric_type == "mean":
            # Continuous test
            result = self.backend.mean_t_test(
                values_a=data_a,
                values_b=data_b,
                alpha=self.alpha
            )
            result['metric_type'] = 'continuous'
            result['control_value'] = result['control_mean']
            result['treatment_value'] = result['treatment_mean']
            # Fallback per-group sample std if backend doesn't provide
            try:
                std_a = float(np.std(data_a, ddof=1)) if len(data_a) > 1 else float('nan')
                std_b = float(np.std(data_b, ddof=1)) if len(data_b) > 1 else float('nan')
                result.setdefault('std_control', std_a)
                result.setdefault('std_treatment', std_b)
            except Exception:
                pass
        else:
            raise ValueError(f"Unknown metric_type '{metric_type}' for metric '{metric_name}'")
        
        # Add metadata
        result['metric_name'] = metric_name
        result['variant_control'] = variant_a
        result['variant_treatment'] = variant_b
        result['significant'] = result['p_value'] < self.alpha
        result['sample_size_control'] = len(data_a)
        result['sample_size_treatment'] = len(data_b)
        # Attach soft monitoring metadata from registry for summary purposes
        try:
            reg = self._metrics.get(metric_name, {})
            for k in ('monitor_alpha', 'monitor_power', 'inferiority_margin', 'is_primary'):
                if k in reg:
                    result[k] = reg[k]
        except Exception:
            pass
        
        return result
    
    def analyze(
        self,
        metrics: Optional[List[str]] = None,
        correction: Optional[str] = None,
        run_srm_check: bool = True
    ) -> 'ExperimentResults':
        """Analyze experiment metrics.
        
        Args:
            metrics: Optional list of metric names to analyze.
                Defaults to all registered metrics.
            correction: Multiple testing correction ('bonferroni', 'fdr', or None)
            run_srm_check: Whether to run SRM check (default True)
        
        Returns:
            ExperimentResults object with all analysis results.
        """
        # Determine variants: always use configured variants (validated in __init__)
        if not self.variants or len(self.variants) != 2:
            raise ValueError("ABTest.variants must contain exactly 2 variant labels")
        variant_a, variant_b = self.variants
        
        # Determine metrics: default to all registered metrics
        if metrics is None:
            metrics = list(self._metrics.keys())
        if not metrics:
            raise ValueError("No metrics specified and no metrics registered")
        
        # Run SRM check
        srm_result = None
        if run_srm_check:
            counts = self.data.groupby(self.variant_col)[self.unit_id].nunique().to_dict()
            # Filter to only the variants we're testing
            counts_filtered = {k: v for k, v in counts.items() if k in [variant_a, variant_b]}
            checker = QualityChecker()
            srm_result = checker.check_srm(counts_filtered)
        
        # Test each metric
        metric_results: Dict[str, Dict[str, Any]] = {}
        for metric_name in metrics:
            try:
                result = self._test_metric(metric_name, variant_a, variant_b)
                metric_results[metric_name] = result
            except Exception as e:
                traceback.print_exc()
                metric_results[metric_name] = {
                    'error': str(e),
                    'metric_name': metric_name
                }
        
        # Apply multiple testing correction if requested
        if correction and len(metrics) > 1:
            metric_results = self._apply_correction(metric_results, correction)
        
        # Create results object
        return ExperimentResults(
            experiment_name=self.name,
            timestamp=self.timestamp,
            metric_results=metric_results,
            srm_result=srm_result,
            alpha=self.alpha,
            correction=correction,
            variants=self.variants,
            primary_metric=getattr(self, "_primary_metric", None),
        )
    
    def _apply_correction(
        self,
        metric_results: Dict[str, Dict],
        method: str
    ) -> Dict[str, Dict]:
        """Apply multiple testing correction.
        
        Args:
            metric_results: Dict of metric results
            method: 'bonferroni' or 'fdr'
        
        Returns:
            Updated metric results with adjusted significance
        """
        # Get p-values (skip errors)
        valid_metrics = {
            name: res for name, res in metric_results.items()
            if 'error' not in res
        }
        
        n_tests = len(valid_metrics)
        if n_tests == 0:
            return metric_results
        
        if method == 'bonferroni':
            adjusted_alpha = self.alpha / n_tests
            for name in valid_metrics:
                metric_results[name]['adjusted_alpha'] = adjusted_alpha
                metric_results[name]['significant'] = (
                    metric_results[name]['p_value'] < adjusted_alpha
                )
                metric_results[name]['correction_method'] = 'bonferroni'
        
        elif method == 'fdr':
            # Benjamini-Hochberg FDR correction
            p_values = [(name, res['p_value']) for name, res in valid_metrics.items()]
            p_values.sort(key=lambda x: x[1])
            
            for rank, (name, p_val) in enumerate(p_values, 1):
                threshold = (rank / n_tests) * self.alpha
                significant = p_val <= threshold
                metric_results[name]['adjusted_threshold'] = threshold
                metric_results[name]['significant'] = significant
                metric_results[name]['correction_method'] = 'benjamini_hochberg'
                metric_results[name]['rank'] = rank
        
        return metric_results


class ExperimentResults:
    """Container for experiment analysis results."""
    
    def __init__(
        self,
        experiment_name: str,
        timestamp: str,
        metric_results: Dict[str, Dict],
        srm_result: Optional[Dict],
        alpha: float,
        correction: Optional[str],
        variants: Optional[List[str]] = None,
        primary_metric: Optional[str] = None,
    ):
        self.experiment_name = experiment_name
        self.timestamp = timestamp
        self.metric_results = metric_results
        self.srm_result = srm_result
        self.alpha = alpha
        self.correction = correction
        self.variants = variants
        self.primary_metric = primary_metric
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = []
        lines.append(f"# {self.experiment_name}")
        lines.append(f"**Analysis Date:** {self.timestamp}")
        lines.append(f"**Significance Level:** alpha = {self.alpha}")
        if self.correction:
            lines.append(f"**Multiple Testing Correction:** {self.correction}")
        if self.primary_metric:
            lines.append(f"**Primary Metric (soft monitoring):** {self.primary_metric}")
            lines.append("Other metrics are descriptive and do not drive decisions.")
        lines.append("")
        
        # SRM check
        if self.srm_result:
            lines.append("## Sample Ratio Mismatch Check")
            lines.append(self.srm_result['recommendation'])
            lines.append("")
        
        # Metrics
        lines.append("## Metric Results")
        lines.append("")

        for metric_name, result in self.metric_results.items():
            if 'error' in result:
                lines.append(f"### [ERROR] {metric_name}")
                lines.append(f"Error: {result['error']}")
                lines.append("")
                continue

            sig_icon = '[SIG]' if result['significant'] else '[NOT-SIG]'
            lines.append(f"### {sig_icon} {metric_name}")
            lines.append(f"- **Type:** {result['metric_type']}")
            role = "primary" if metric_name == self.primary_metric else "monitor"
            lines.append(f"- **Role:** {role}")
            # Show soft monitoring metadata for monitors if available
            if role == "monitor":
                entry = None
                # Find registration info for extra context (alpha/power/margin)
                # metric_results does not carry registry fields; rely on result extras if present
                monitor_alpha = result.get('monitor_alpha')
                monitor_power = result.get('monitor_power')
                inferiority_margin = result.get('inferiority_margin')
                details = []
                if monitor_alpha is not None:
                    details.append(f"alpha={monitor_alpha}")
                if monitor_power is not None:
                    details.append(f"power={monitor_power}")
                if inferiority_margin is not None:
                    details.append(f"inferiority_margin={inferiority_margin}")
                if details:
                    lines.append(f"- **Monitor Settings:** {'; '.join(details)}")
                # Simple CI vs margin note (non-blocking)
                if inferiority_margin is not None:
                    try:
                        lb = float(result['ci_lower'])
                        if lb >= -inferiority_margin:
                            lines.append(f"- **NI Check:** CI lower bound ≥ -inferiority_margin (lb={lb:.4f} ≥ {-inferiority_margin:.4f})")
                        else:
                            lines.append(f"- **NI Check:** CI lower bound < -inferiority_margin (lb={lb:.4f} < {-inferiority_margin:.4f})")
                    except Exception:
                        pass
            lines.append(f"- **Control:** {result['control_value']:.4f} (n={result['sample_size_control']})")
            lines.append(f"- **Treatment:** {result['treatment_value']:.4f} (n={result['sample_size_treatment']})")
            # Dispersion: prefer per-group stds; fallback to pooled only if both missing
            sc = result.get('std_control')
            st = result.get('std_treatment')
            printed_std = False
            if sc is not None:
                lines.append(f"- **Std (control):** {float(sc):.6f}")
                printed_std = True
            if st is not None:
                lines.append(f"- **Std (treatment):** {float(st):.6f}")
                printed_std = True
            if not printed_std and ('std_pooled' in result and result['std_pooled'] is not None):
                lines.append(f"- **Std (pooled):** {float(result['std_pooled']):.6f}")
            lines.append(f"- **Lift:** {result['lift']:.2%}")
            lines.append(f"- **P-value:** {result['p_value']:.6f}")
            lines.append(f"- **95% CI:** [{result['ci_lower']:.4f}, {result['ci_upper']:.4f}]")
            if 'adjusted_alpha' in result:
                lines.append(f"- **Adjusted alpha:** {result['adjusted_alpha']:.4f}")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """Export as dictionary."""
        return {
            'experiment': self.experiment_name,
            'timestamp': self.timestamp,
            'alpha': self.alpha,
            'correction': self.correction,
            'srm_check': self.srm_result,
            'variants': self.variants,
            'primary_metric': self.primary_metric,
            'metrics': self.metric_results
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """Export as DataFrame."""
        rows = []
        for metric_name, result in self.metric_results.items():
            if 'error' not in result:
                rows.append({
                    'experiment': self.experiment_name,
                    'metric': metric_name,
                    'metric_type': result.get('metric_type'),
                    'control_value': result.get('control_value'),
                    'treatment_value': result.get('treatment_value'),
                    'lift': result.get('lift'),
                    'p_value': result.get('p_value'),
                    'significant': result.get('significant'),
                    'ci_lower': result.get('ci_lower'),
                    'ci_upper': result.get('ci_upper'),
                    'sample_size_control': result.get('sample_size_control'),
                    'sample_size_treatment': result.get('sample_size_treatment'),
                })
        return pd.DataFrame(rows)
    
    def conclusion(self, metric_name: str = None) -> str:
        """Generate a statistical conclusion for a specific metric or first metric.
        
        Args:
            metric_name: Name of metric to summarize (defaults to first metric)
        
        Returns:
            Formatted statistical conclusion string
        
        Example:
            >>> print(results.conclusion('conversion_rate'))
        """
        if metric_name is None:
            # Use first metric if not specified
            metric_name = list(self.metric_results.keys())[0]
        
        if metric_name not in self.metric_results:
            return f"Metric '{metric_name}' not found in results"
        
        result = self.metric_results[metric_name]
        
        if 'error' in result:
            return f"Error analyzing {metric_name}: {result['error']}"
        
        lines = []
        lines.append("=" * 70)
        lines.append("STATISTICAL CONCLUSION")
        lines.append("=" * 70)
        
        # Format values based on metric type
        is_percentage = result.get('metric_type') == 'binary'
        
        if is_percentage:
            control_fmt = f"{result['control_value']:.2%}"
            treatment_fmt = f"{result['treatment_value']:.2%}"
            diff_abs = (result['treatment_value'] - result['control_value']) * 100
            diff_fmt = f"{diff_abs:.2f} percentage points"
        else:
            control_fmt = f"{result['control_value']:.2f}"
            treatment_fmt = f"{result['treatment_value']:.2f}"
            diff_abs = result['treatment_value'] - result['control_value']
            diff_fmt = f"{diff_abs:.2f}"
        
        lift_fmt = f"{result['lift']:.1%}"
        p_val = result['p_value']
        
        # Determine significance (considering correction if applied)
        is_significant = result['significant']
        alpha_used = result.get('adjusted_alpha', self.alpha)
        
        if is_significant:
            # Significant result
            direction = "higher" if result['lift'] > 0 else "lower"
            lines.append(
                f"The treatment group showed a statistically significant {direction} "
                f"{metric_name.replace('_', ' ')} compared to the control group "
                f"(Treatment: {treatment_fmt} vs. Control: {control_fmt}, "
                f"difference: {diff_fmt}, relative change: {lift_fmt}, "
                f"p = {p_val:.4f})."
            )
            
            # CI bounds
            if is_percentage:
                ci_lower_fmt = f"{result['ci_lower'] * 100:.2f}%"
                ci_upper_fmt = f"{result['ci_upper'] * 100:.2f}%"
            else:
                ci_lower_fmt = f"{result['ci_lower']:.2f}"
                ci_upper_fmt = f"{result['ci_upper']:.2f}"
            
            lines.append(
                f"The 95% confidence interval for the difference is "
                f"[{ci_lower_fmt}, {ci_upper_fmt}]."
            )
            
            if self.correction:
                lines.append(
                    f"\nNote: Multiple testing correction applied ({self.correction}), "
                    f"adjusted alpha = {alpha_used:.4f}."
                )
        else:
            # Not significant
            lines.append(
                f"There was no statistically significant difference in "
                f"{metric_name.replace('_', ' ')} between the treatment and control groups "
                f"(Treatment: {treatment_fmt} vs. Control: {control_fmt}, "
                f"p = {p_val:.4f})."
            )
            lines.append("")
            lines.append(
                "[!] RECOMMENDATION: The treatment variant did not show a significant effect. "
                "Consider running the test longer or with a larger sample size, or abandon "
                "this variant."
            )
            
            if self.correction:
                lines.append(
                    f"\nNote: Multiple testing correction applied ({self.correction}), "
                    f"adjusted alpha = {alpha_used:.4f}."
                )
        
        lines.append("=" * 70)
        return "\n".join(lines)

    def decision_soft_monitoring(self) -> str:
        """Primary-driven decision helper for soft monitoring mode.

        Returns a concise decision based only on the primary metric. Other metrics
        are treated as descriptive and do not block shipping.
        """
        if not self.primary_metric:
            return "No primary metric configured. Set is_primary=True on one metric."
        res = self.metric_results.get(self.primary_metric)
        if not res or 'error' in res:
            return f"Primary metric '{self.primary_metric}' has no valid result."
        p = res.get('p_value')
        sig = res.get('significant', False)
        lift = res.get('lift')
        if sig:
            return (
                f"Ship: primary '{self.primary_metric}' is significant "
                f"(p={p:.4f}, lift={lift:.2%}). Monitored metrics are descriptive only."
            )
        return (
            f"Do not ship: primary '{self.primary_metric}' is not significant "
            f"(p={p:.4f}). Monitored metrics are descriptive only."
        )
