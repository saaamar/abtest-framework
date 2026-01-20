"""Base interface for statistical backends."""

from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np


class StatisticalBackend(ABC):
    """Abstract base class for statistical computation backends.
    
    This interface covers *all* statistical responsibilities of the framework:
    both *analysis* (running hypothesis tests) and *planning* (sample size
    calculations done before an experiment starts).

    Backends are free to implement the planning methods using any engine
    (closed-form formulas with scipy, abexp.SampleSize, in-house tooling,
    etc.). Analysis methods are required and are used by :class:`ABTest`.
    Planning methods are optional convenience helpers for users who want a
    single entry point for "everything statistical". If your workflow already
    handles planning elsewhere (for example in a separate tool or spreadsheet)
    you can ignore the planning methods and use only the analysis APIs.
    """
    
    @abstractmethod
    def proportion_z_test(
        self,
        successes_a: int,
        trials_a: int,
        successes_b: int,
        trials_b: int,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """Test difference in proportions (e.g., conversion rate, CTR).
        
        Args:
            successes_a: Number of successes in control group
            trials_a: Total trials in control group
            successes_b: Number of successes in treatment group
            trials_b: Total trials in treatment group
            alpha: Significance level (default 0.05)
        
        Returns:
            Dictionary containing:
                - p_value: float
                - ci_lower: float (lower bound of 95% CI for difference)
                - ci_upper: float (upper bound of 95% CI for difference)
                - lift: float (relative lift, e.g., 0.15 = 15% improvement)
                - statistic: float (test statistic, e.g., z-score)
                - control_rate: float (control proportion)
                - treatment_rate: float (treatment proportion)
        """
        pass
    
    @abstractmethod
    def mean_t_test(
        self,
        values_a: np.ndarray,
        values_b: np.ndarray,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """Test difference in means (e.g., revenue, session duration).
        
        Args:
            values_a: Array of values from control group
            values_b: Array of values from treatment group
            alpha: Significance level (default 0.05)
        
        Returns:
            Dictionary containing:
                - p_value: float
                - ci_lower: float (lower bound of 95% CI for difference)
                - ci_upper: float (upper bound of 95% CI for difference)
                - mean_diff: float (absolute difference)
                - lift: float (relative lift)
                - statistic: float (test statistic, e.g., t-statistic)
                - control_mean: float
                - treatment_mean: float
                - control_std: float
                - treatment_std: float
        """
        pass

    @abstractmethod
    def sample_size_proportion(
        self,
        baseline_rate: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.80,
        treatment_fraction: float = 0.5,
    ) -> Dict[str, Any]:
        """Plan sample size for a binary/proportion metric.

        This method is intended for pre-experiment planning for metrics such as
        conversion rate or click-through rate.

        Implementations typically either:

        - use a closed-form normal approximation (e.g. via ``scipy.stats``), or
        - delegate to a planning helper exposed by the underlying library
          (e.g. ``abexp.SampleSize.ssd_prop``).

        Args:
            baseline_rate: Current/expected control conversion rate,
                e.g. ``0.10`` for 10%.
            mde: Minimum detectable effect **as a relative change**,
                e.g. ``0.05`` for a 5% relative lift over ``baseline_rate``.
            alpha: Significance level for the two-sided test (default 0.05).
            power: Desired statistical power (1 - beta), default ``0.80``.
            treatment_fraction: Planned fraction of experiment traffic allocated
                to the treatment variant, e.g. ``0.5`` for 50/50,
                ``0.3`` for 30% treatment / 70% control.

        Returns:
            Dictionary containing at least:

            - ``control_size``: required control group sample size (int)
            - ``treatment_size``: required treatment group sample size (int)
            - ``total_size``: total required sample size (int)
                        - ``assumptions``: nested dict echoing inputs and any useful
                            derived quantities (e.g. absolute MDE, planned treatment rate,
                            internal treatment:control ratio).

        Note:
            This API is a *planning helper*; the :class:`ABTest` orchestration
            does not call it internally. It exists so that users who pick a
            backend (owl, abexp, in-house, etc.) can optionally get planning
            and analysis from the same place.
        """
        pass

    @abstractmethod
    def sample_size_mean(
        self,
        baseline_mean: float,
        baseline_std: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
    ) -> Dict[str, Any]:
        """Plan sample size for a continuous metric.

        This method plans experiments on metrics such as revenue per user,
        session duration, or any approximately normal/CLT-friendly signal.

        Implementations typically either:

        - implement the standard normal-approximation formulas directly,
        - or delegate to a helper such as ``abexp.SampleSize.ssd_mean``.

        Args:
            baseline_mean: Expected control mean (e.g. ``50.0`` dollars).
            baseline_std: Estimated standard deviation in the control group.
            mde: Minimum detectable effect as a relative change over
                ``baseline_mean`` (e.g. ``0.10`` for +10%).
            alpha: Significance level for the two-sided test (default 0.05).
            power: Desired statistical power (1 - beta), default ``0.80``.
            ratio: Planned treatment:control allocation ratio.

        Returns:
            Dictionary containing at least:

            - ``control_size``: required control group sample size (int)
            - ``treatment_size``: required treatment group sample size (int)
            - ``total_size``: total required sample size (int)
            - ``assumptions``: nested dict echoing inputs and any useful
              derived quantities (e.g. absolute MDE, Cohen's d).

        Note:
            Like :meth:`sample_size_proportion`, this is a planning-only API
            provided for convenience. Choosing a backend should determine both
            how you *analyze* experiments and, if desired, how you *plan* them,
            but callers are free to ignore these helpers if they already have
            an established planning workflow.
        """
        pass
