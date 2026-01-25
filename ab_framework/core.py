"""Core ABTest class for experiment analysis."""

from typing import Dict, List, Callable, Optional, Any, Literal, Mapping, TYPE_CHECKING
import numpy as np
from datetime import datetime
import traceback

from .backends import ScipyBackend, StatisticalBackend
from .quality import QualityChecker

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

class ABTest:
    """Main class for A/B test analysis.
    
    This class orchestrates the entire A/B testing workflow:
    - Metric registration
    - Statistical testing
    - Multi-metric orchestration
    - Quality checks (SRM)
    - Result reporting
    
    Example:
        >>> test = ABTest(name="homepage_redesign", variants=["A", "B"])
        >>> 
        >>> @test.metric(metric_type="proportion")
        ... def conversion_rate(data):
        ...     per_user = data.groupby(['variant', 'user_id'])['converted'].max().reset_index()
        ...     summary = per_user.groupby('variant')['converted'].agg(['sum', 'count']).to_dict('index')
        ...     return {v: {'successes': int(d['sum']), 'n': int(d['count'])} for v, d in summary.items()}
        >>> 
        >>> results = test.analyze(df, metrics=['conversion_rate'], run_srm_check=False)
        >>> print(results.summary())
    """
    
    def __init__(
        self,
        name: str,
        backend: Optional[StatisticalBackend] = None,
        variants: Optional[List[str]] = None,
    ):
        """Initialize A/B test.
        
        Args:
            name: Experiment name
            backend: Statistical backend (defaults to ScipyBackend)
            variants: Variant labels for control and treatment, e.g. ["A", "B"].
                Since the core is schema-agnostic and does not inspect raw data,
                variants cannot be inferred automatically and must be provided
                (or defaults are used).
        """
        self.name = name
        self.backend = backend if backend is not None else ScipyBackend()
        # Default significance level for hypothesis tests. This can be
        # overridden later via ``setup(alpha=...)``.
        self.alpha: float = 0.05
        # Analysis timestamp can be configured via ``setup(timestamp=...)``.
        # If left as None, it will be filled in at analysis time.
        self.timestamp: Optional[str] = None
        
        # Explicit variants configuration (e.g. ["A", "B"]).
        # When not provided, default to the canonical A/B labels.
        self.variants: List[str] = list(variants) if variants is not None else ["A", "B"]
        
        # Treatment fraction: proportion of traffic to treatment.
        # E.g., 0.3 means 30% treatment / 70% control. This is configured
        # post-construction via ``setup(treatment_fraction=...)``.
        self.treatment_fraction: Optional[float] = None
        
        # Metric registry: name -> metadata dict.
        # For backward compatibility this at least contains:
        #   {"func": callable, "metric_type": str}
        # Additional fields (role, mde, non_inferiority_margin, etc.)
        # can be added later without breaking existing users.
        self._metrics: Dict[str, Dict[str, Any]] = {}
        
        if len(self.variants) != 2:
            raise ValueError(f"'variants' must contain exactly 2 labels, got {self.variants}")
    
    def metric(
        self,
        func: Callable = None,
        *,
        metric_type: Literal["proportion", "mean"],
        is_primary: bool = False,
        monitor_alpha: Optional[float] = None,
        monitor_power: Optional[float] = None,
        inferiority_margin: Optional[float] = None,
    ) -> Callable:
        """Decorator to register a metric function.
        
                The framework core is schema-agnostic: it does not inspect raw data
                objects (pandas, SQL rows, API responses, etc.). Metric functions are
                responsible for knowing the experiment schema and returning per-variant
                **summary statistics** required for hypothesis tests.

                Metric functions are called as ``metric_func(data)`` where ``data`` is
                whatever object you pass to :meth:`analyze`.

                Required return shapes:

                - For ``metric_type="proportion"``:
                    ``{variant: {"successes": int, "n": int}, ...}``
                - For ``metric_type="mean"``:
                    ``{variant: {"mean": float, "std": float, "n": int}, ...}``

        Args:
            func: Metric function that takes ``data`` and returns per-variant
                summary statistics.
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

    @property
    def active_metrics(self) -> List[str]:
        """List of currently registered metric names.

        This reflects the metric registry state at access time (i.e. it is
        computed from ``self._metrics`` and is not separately stored).
        """
        return list(self._metrics.keys())

    def setup(
        self,
        *,
        alpha: Optional[float] = None,
        treatment_fraction: Optional[float] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """Configure analysis parameters after construction.

        This lets you separate *planning* from *analysis*:

        - Use backend-level helpers (e.g. :meth:`StatisticalBackend.sample_size_proportion`)
          for pre-experiment sample-size and power calculations with arbitrary
          ``alpha``, ``power``, ``mde``, etc.
        - Once you decide on the final analysis settings, call ``setup()`` to
          store them on the :class:`ABTest` instance so that :meth:`analyze`
          and SRM checks use the same configuration consistently.

        Args:
            alpha: Significance level to use for hypothesis tests
                and multiple-testing corrections.
            treatment_fraction: Expected fraction of traffic allocated to
                the treatment variant for SRM expectations (e.g., ``0.5``
                for a 50/50 split, ``0.3`` for 30/70).
            timestamp: Optional ISO-8601 analysis timestamp. If not set,
                it will default to the current time when :meth:`analyze`
                is first called.
        """
        if alpha is not None:
            self.alpha = alpha
        if treatment_fraction is not None:
            self.treatment_fraction = treatment_fraction
        if timestamp is not None:
            self.timestamp = timestamp

    def _compute_metric_stats(self, metric_name: str, data: Any) -> Mapping[str, Mapping[str, Any]]:
        if metric_name not in self._metrics:
            raise ValueError(f"Metric '{metric_name}' not registered")
        metric_func = self._metrics[metric_name]["func"]

        stats = metric_func(data)
        if not isinstance(stats, Mapping):
            raise TypeError(
                f"Metric '{metric_name}' must return a mapping of per-variant stats, got {type(stats)}"
            )
        return stats
    
    def _test_metric(
        self,
        metric_name: str,
        variant_a: str,
        variant_b: str,
        data: Any,
    ) -> Dict[str, Any]:
        """Test a single metric between two variants.
        
        Args:
            metric_name: Name of metric to test
            variant_a: Control variant name
            variant_b: Treatment variant name
        
        Returns:
            Dictionary with test results
        """
        metric_stats = self._compute_metric_stats(metric_name, data)
        if variant_a not in metric_stats or variant_b not in metric_stats:
            raise ValueError(
                f"Metric '{metric_name}' must provide stats for variants {self.variants}, "
                f"got keys={list(metric_stats.keys())}"
            )
        
        # Determine metric type (must be provided at registration time)
        entry = self._metrics.get(metric_name)
        if not entry or "metric_type" not in entry or entry["metric_type"] is None:
            raise ValueError(
                f"Metric '{metric_name}' is missing required metric_type; "
                "register it with metric_type='proportion' or 'mean'."
            )
        metric_type = entry["metric_type"]

        if metric_type == "proportion":
            a = metric_stats[variant_a]
            b = metric_stats[variant_b]
            if "successes" not in a or "n" not in a or "successes" not in b or "n" not in b:
                raise ValueError(
                    f"Proportion metric '{metric_name}' must return per-variant {{'successes','n'}}. "
                    f"Got A={a} B={b}"
                )
            successes_a = int(a["successes"])
            trials_a = int(a["n"])
            successes_b = int(b["successes"])
            trials_b = int(b["n"])
            if trials_a <= 0 or trials_b <= 0:
                raise ValueError(f"Invalid n for proportion metric '{metric_name}': A.n={trials_a}, B.n={trials_b}")
            
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
            a = metric_stats[variant_a]
            b = metric_stats[variant_b]
            required = ("mean", "std", "n")
            if any(k not in a for k in required) or any(k not in b for k in required):
                raise ValueError(
                    f"Mean metric '{metric_name}' must return per-variant {{'mean','std','n'}}. "
                    f"Got A={a} B={b}"
                )
            mean_a = float(a["mean"])
            std_a = float(a["std"])
            n_a = int(a["n"])
            mean_b = float(b["mean"])
            std_b = float(b["std"])
            n_b = int(b["n"])
            if n_a <= 1 or n_b <= 1:
                raise ValueError(f"Invalid n for mean metric '{metric_name}': A.n={n_a}, B.n={n_b}")

            result = self.backend.mean_t_test(
                mean_a=mean_a,
                std_a=std_a,
                n_a=n_a,
                mean_b=mean_b,
                std_b=std_b,
                n_b=n_b,
                alpha=self.alpha,
            )
            result['metric_type'] = 'continuous'
            result['control_value'] = result['control_mean']
            result['treatment_value'] = result['treatment_mean']
            result.setdefault('std_control', std_a)
            result.setdefault('std_treatment', std_b)
        else:
            raise ValueError(f"Unknown metric_type '{metric_type}' for metric '{metric_name}'")
        
        # Add metadata
        result['metric_name'] = metric_name
        result['variant_control'] = variant_a
        result['variant_treatment'] = variant_b
        result['significant'] = result['p_value'] < self.alpha
        if metric_type == "proportion":
            result['sample_size_control'] = trials_a
            result['sample_size_treatment'] = trials_b
        else:
            result['sample_size_control'] = n_a
            result['sample_size_treatment'] = n_b
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
        data: Any,
        metrics: Optional[List[str]] = None,
        correction: Optional[str] = None,
        run_srm_check: bool = True,
        observed_counts: Optional[Dict[str, int]] = None,
    ) -> 'ExperimentResults':
        """Analyze experiment metrics.
        
        Args:
            data: Arbitrary data object representing the analysis snapshot
                (e.g., a DataFrame for a given day). The core does not inspect
                its schema; it is passed verbatim into metric functions.
            metrics: Optional list of metric names to analyze (a subset of the
                registered metrics). Defaults to all registered metrics.
                All provided names must already be registered.
            correction: Optional multiple-testing correction to control false
                positives when analyzing multiple metrics (e.g. ``"bonferroni"``
                or ``"fdr"``). This is only applied when analyzing more than one
                metric; otherwise it is ignored (keep it None).
            run_srm_check: Whether to run SRM check (default True)
            observed_counts: Optional mapping ``{variant: exposed_units}`` used
                for SRM. When ``run_srm_check=True``, this must be provided.
        
        Returns:
            ExperimentResults object with all analysis results.
        """
        variant_a, variant_b = self.variants

        
        # Determine metrics: default to all registered metrics
        if metrics is None:
            metrics = self.active_metrics
        else:
            unknown = [m for m in metrics if m not in self._metrics]
            if unknown:
                raise ValueError(
                    f"Unknown metrics {unknown}. "
                    f"Registered metrics: {self.active_metrics}"
                )
        if not metrics:
            raise ValueError("No metrics specified and no metrics registered")
        
        # Run SRM check
        srm_result = None
        if run_srm_check:
            if observed_counts is None:
                raise ValueError(
                    "run_srm_check=True requires observed_counts to be provided "
                    "(core does not inspect raw data to compute it)."
                )
            counts_filtered = {k: int(v) for k, v in observed_counts.items() if k in [variant_a, variant_b]}
            checker = QualityChecker()
            
            # Build expected_ratio dict based on treatment_fraction if provided
            expected_ratio = None
            if self.treatment_fraction is not None:
                # treatment_fraction is proportion for treatment (variant_b)
                # control (variant_a) gets the remainder
                expected_ratio = {
                    variant_a: 1.0 - self.treatment_fraction,
                    variant_b: self.treatment_fraction
                }
            
            srm_result = checker.check_srm(counts_filtered, expected_ratio=expected_ratio)
        
        # Test each metric
        metric_results: Dict[str, Dict[str, Any]] = {}
        for metric_name in metrics:
            try:
                result = self._test_metric(metric_name, variant_a, variant_b, data)
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
        
        # Ensure we have an analysis timestamp; if the caller did not
        # configure one via ``setup(timestamp=...)``, default to now.
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

        # Create results object
        return ExperimentResults(
            experiment_name=self.name,
            timestamp=self.timestamp,
            metric_results=metric_results,
            srm_result=srm_result,
            alpha=self.alpha,
            correction=correction,
            variants=[variant_a, variant_b],
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
            # Dispersion
            # - For binary/proportion metrics: show Standard Error (SE) of the estimated proportion.
            # - For continuous metrics: show sample standard deviation (Std) per group.
            if result.get('metric_type') == 'binary':
                try:
                    p_c = float(result['control_value'])
                    n_c = int(result['sample_size_control'])
                    p_t = float(result['treatment_value'])
                    n_t = int(result['sample_size_treatment'])
                    if n_c > 0:
                        se_c = float(np.sqrt(max(p_c * (1.0 - p_c), 0.0) / n_c))
                        lines.append(f"- **SE (control):** {se_c:.6f}")
                    if n_t > 0:
                        se_t = float(np.sqrt(max(p_t * (1.0 - p_t), 0.0) / n_t))
                        lines.append(f"- **SE (treatment):** {se_t:.6f}")
                except Exception:
                    pass
            else:
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
    
    def to_dataframe(self) -> 'pd.DataFrame':
        """Export as DataFrame."""
        import pandas as pd

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
