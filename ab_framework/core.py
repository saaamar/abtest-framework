"""Core ABTest class for experiment analysis."""

from typing import Dict, List, Callable, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime

from .backends import OwlBackend, StatisticalBackend
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
        alpha: float = 0.05
    ):
        """Initialize A/B test.
        
        Args:
            name: Experiment name
            data: DataFrame with experiment data (event-level or aggregated)
            variant_col: Column name containing variant assignments ('A', 'B', etc.)
            unit_id: Column name for randomization unit (usually 'user_id')
            backend: Statistical backend (defaults to OwlBackend)
            alpha: Significance level (default 0.05)
        """
        self.name = name
        self.data = data.copy()
        self.variant_col = variant_col
        self.unit_id = unit_id
        self.backend = backend if backend is not None else OwlBackend()
        self.alpha = alpha
        self.timestamp = datetime.now().isoformat()
        
        # Metric registry: name -> {"func": callable, "metric_type": str}
        self._metrics: Dict[str, Dict[str, Any]] = {}
        
        # Validate inputs
        self._validate_data()
    
    def _validate_data(self):
        """Validate input data structure."""
        if self.variant_col not in self.data.columns:
            raise ValueError(f"Variant column '{self.variant_col}' not found in data")
        
        if self.unit_id not in self.data.columns:
            raise ValueError(f"Unit ID column '{self.unit_id}' not found in data")
        
        variants = self.data[self.variant_col].unique()
        if len(variants) < 2:
            raise ValueError(f"Need at least 2 variants, found {len(variants)}")
    
    def metric(self, func: Callable = None, *, metric_type: str) -> Callable:
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
            self._metrics[f.__name__] = {"func": f, "metric_type": metric_type}
            return f

        # Support both @test.metric and @test.metric(...)
        if func is not None:
            return decorator(func)
        return decorator
    
    def register_metric(self, name: str, func: Callable, metric_type: str):
        """Register a metric function programmatically.
        
        Alternative to the @metric decorator for dynamic registration.
        
        Args:
            name: Metric name
            func: Metric function that takes DataFrame and returns Series
            metric_type: Type hint ("proportion" or "mean").
        """
        if metric_type not in ("proportion", "mean"):
            raise ValueError("metric_type must be 'proportion' or 'mean'")
        self._metrics[name] = {"func": func, "metric_type": metric_type}
    
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
                alpha=self.alpha
            )
            result['metric_type'] = 'binary'
            result['control_value'] = successes_a / trials_a
            result['treatment_value'] = successes_b / trials_b
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
        else:
            raise ValueError(f"Unknown metric_type '{metric_type}' for metric '{metric_name}'")
        
        # Add metadata
        result['metric_name'] = metric_name
        result['variant_control'] = variant_a
        result['variant_treatment'] = variant_b
        result['significant'] = result['p_value'] < self.alpha
        result['sample_size_control'] = len(data_a)
        result['sample_size_treatment'] = len(data_b)
        
        return result
    
    def analyze(
        self,
        metrics: List[str],
        variants: List[str] = None,
        correction: Optional[str] = None,
        run_srm_check: bool = True
    ) -> 'ExperimentResults':
        """Analyze experiment metrics.
        
        Args:
            metrics: List of metric names to analyze
            variants: List of 2 variants to compare (defaults to first 2 found)
            correction: Multiple testing correction ('bonferroni', 'fdr', or None)
            run_srm_check: Whether to run SRM check (default True)
        
        Returns:
            ExperimentResults object with all analysis results
        
        Example:
            >>> results = test.analyze(
            ...     metrics=['conversion_rate', 'revenue_per_user'],
            ...     correction='bonferroni'
            ... )
            >>> print(results.summary())
        """
        # Determine variants
        if variants is None:
            all_variants = sorted(self.data[self.variant_col].unique())
            if len(all_variants) < 2:
                raise ValueError("Need at least 2 variants")
            variants = all_variants[:2]
        
        if len(variants) != 2:
            raise ValueError(f"Must specify exactly 2 variants, got {len(variants)}")
        
        variant_a, variant_b = variants
        
        # Run SRM check
        srm_result = None
        if run_srm_check:
            counts = self.data.groupby(self.variant_col)[self.unit_id].nunique().to_dict()
            # Filter to only the variants we're testing
            counts_filtered = {k: v for k, v in counts.items() if k in [variant_a, variant_b]}
            checker = QualityChecker()
            srm_result = checker.check_srm(counts_filtered)
        
        # Test each metric
        metric_results = {}
        for metric_name in metrics:
            try:
                result = self._test_metric(metric_name, variant_a, variant_b)
                metric_results[metric_name] = result
            except Exception as e:
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
            correction=correction
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
        correction: Optional[str]
    ):
        self.experiment_name = experiment_name
        self.timestamp = timestamp
        self.metric_results = metric_results
        self.srm_result = srm_result
        self.alpha = alpha
        self.correction = correction
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = []
        lines.append(f"# {self.experiment_name}")
        lines.append(f"**Analysis Date:** {self.timestamp}")
        lines.append(f"**Significance Level:** alpha = {self.alpha}")
        if self.correction:
            lines.append(f"**Multiple Testing Correction:** {self.correction}")
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

            continue
            
            sig_icon = '[SIG]' if result['significant'] else '[NOT-SIG]'
            lines.append(f"### {sig_icon} {metric_name}")
            lines.append(f"- **Type:** {result['metric_type']}")
            lines.append(f"- **Control:** {result['control_value']:.4f} (n={result['sample_size_control']})")
            lines.append(f"- **Treatment:** {result['treatment_value']:.4f} (n={result['sample_size_treatment']})")
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
