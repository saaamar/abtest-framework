"""Abexp backend implementation."""

from typing import Dict, Any
import numpy as np
from abexp.core.analysis_frequentist import FrequentistAnalyzer
from abexp.core.design import SampleSize
from .base import StatisticalBackend
from scipy import stats


class AbexpBackend(StatisticalBackend):
    """Statistical backend using abexp package.
    
    This backend wraps abexp's FrequentistAnalyzer to provide a consistent
    interface for the AB testing framework.
    """
    
    def __init__(self):
        """Initialize the Abexp backend."""
        self.analyzer = FrequentistAnalyzer()
    
    def proportion_z_test(
        self,
        successes_a: int,
        trials_a: int,
        successes_b: int,
        trials_b: int,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """Test difference in proportions using abexp.
        
        Args:
            successes_a: Number of successes in control group
            trials_a: Total trials in control group
            successes_b: Number of successes in treatment group
            trials_b: Total trials in treatment group
            alpha: Significance level (default 0.05)
        
        Returns:
            Dictionary with test results
        """
        # abexp requires binary observation arrays
        obs_control = np.array([1] * successes_a + [0] * (trials_a - successes_a))
        obs_treatment = np.array([1] * successes_b + [0] * (trials_b - successes_b))
        
        # Call abexp's compare_conv_obs
        # Returns: (p_value, ci_control, ci_treatment)
        p_value, ci_control, ci_treatment = self.analyzer.compare_conv_obs(
            obs_control, obs_treatment, alpha=alpha
        )
        
        # Calculate rates and lift
        control_rate = successes_a / trials_a if trials_a > 0 else 0
        treatment_rate = successes_b / trials_b if trials_b > 0 else 0
        
        # Calculate relative lift (handle zero baseline gracefully)
        if control_rate > 0:
            lift = (treatment_rate - control_rate) / control_rate
        else:
            lift = 0.0
        
        # Calculate absolute difference for CI
        # abexp returns CIs for each group separately, we need CI for the difference
        # For now, use the treatment CI as an approximation (this is a simplification)
        ci_lower = ci_treatment[0] - ci_control[1]
        ci_upper = ci_treatment[1] - ci_control[0]
        
        return {
            'p_value': p_value,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'lift': lift,
            'statistic': None,  # abexp doesn't return test statistic directly
            'control_rate': control_rate,
            'treatment_rate': treatment_rate,
            'backend': 'abexp'
        }
    
    def mean_t_test(
        self,
        mean_a: float,
        std_a: float,
        n_a: int,
        mean_b: float,
        std_b: float,
        n_b: int,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """Test difference in means using abexp.
        
        Args:
            mean_a: Control mean
            std_a: Control sample standard deviation
            n_a: Control sample size
            mean_b: Treatment mean
            std_b: Treatment sample standard deviation
            n_b: Treatment sample size
            alpha: Significance level (default 0.05)
        
        Returns:
            Dictionary with test results
        """
        # abexp's mean comparison helper operates on raw observations.
        # For schema-agnostic workflows, use a Welch-style test from summary stats.
        mean_a = float(mean_a)
        mean_b = float(mean_b)
        std_a = float(std_a)
        std_b = float(std_b)
        n_a = int(n_a)
        n_b = int(n_b)
        if n_a <= 1 or n_b <= 1:
            raise ValueError(f"Need n_a>1 and n_b>1, got n_a={n_a}, n_b={n_b}")

        mean_diff = mean_b - mean_a
        se_diff = np.sqrt((std_a ** 2 / n_a) + (std_b ** 2 / n_b))
        if se_diff <= 0:
            raise ValueError("Standard error must be positive")

        t_stat = mean_diff / se_diff
        df = ((std_a ** 2 / n_a) + (std_b ** 2 / n_b)) ** 2 / (
            (std_a ** 2 / n_a) ** 2 / (n_a - 1) + (std_b ** 2 / n_b) ** 2 / (n_b - 1)
        )
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))

        t_critical = stats.t.ppf(1 - alpha / 2, df)
        ci_lower = mean_diff - t_critical * se_diff
        ci_upper = mean_diff + t_critical * se_diff

        if mean_a != 0:
            lift = (mean_b - mean_a) / abs(mean_a)
        else:
            lift = 0.0
        
        return {
            'p_value': p_value,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'lift': lift,
            'statistic': t_stat,
            'mean_diff': mean_diff,
            'control_mean': mean_a,
            'treatment_mean': mean_b,
            'control_std': std_a,
            'treatment_std': std_b,
            'control_n': n_a,
            'treatment_n': n_b,
            'backend': 'abexp'
        }
    
    def sample_size_proportion(
        self,
        baseline_rate: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
    ) -> Dict[str, Any]:
        """Sample size planning for proportion metrics using abexp.
        
        Args:
            baseline_rate: Baseline conversion rate (e.g., 0.10 for 10%)
            mde: Minimum detectable effect as relative change (e.g., 0.10 for 10% lift)
            alpha: Significance level (default 0.05)
            power: Statistical power (default 0.80)
            ratio: Ratio of treatment to control size (default 1.0)
        
        Returns:
            Dictionary with sample size recommendations
        """
        treatment_rate = baseline_rate * (1 + mde)
        
        # Calculate sample size using abexp
        # abexp's ssd_prop signature: ssd_prop(prop_contr, prop_treat, alpha, power)
        sample_size_calc = SampleSize()
        n_control = sample_size_calc.ssd_prop(
            prop_contr=baseline_rate,
            prop_treat=treatment_rate,
            alpha=alpha,
            power=power
        )
        
        n_control = int(np.ceil(n_control))
        # Note: abexp's ssd_prop doesn't support ratio parameter
        # For unequal allocation, you'd need to adjust manually
        n_treatment = int(np.ceil(n_control * ratio))
        
        return {
            'control_size': n_control,
            'treatment_size': n_treatment,
            'total_size': n_control + n_treatment,
            'assumptions': {
                'baseline_rate': baseline_rate,
                'treatment_rate': treatment_rate,
                'mde_relative': mde,
                'mde_absolute': treatment_rate - baseline_rate,
                'alpha': alpha,
                'power': power,
                'ratio': ratio,
            },
            'backend': 'abexp',
        }
    
    def sample_size_mean(
        self,
        baseline_mean: float,
        baseline_std: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
    ) -> Dict[str, Any]:
        """Sample size planning for continuous metrics using abexp.
        
        Args:
            baseline_mean: Baseline mean value
            baseline_std: Baseline standard deviation
            mde: Minimum detectable effect as relative change (e.g., 0.10 for 10% lift)
            alpha: Significance level (default 0.05)
            power: Statistical power (default 0.80)
            ratio: Ratio of treatment to control size (default 1.0)
        
        Returns:
            Dictionary with sample size recommendations
        """
        treatment_mean = baseline_mean * (1 + mde)
        
        # Calculate sample size using abexp
        # abexp's ssd_mean signature: ssd_mean(mean_contr, mean_treat, std_contr, alpha, power)
        # Note: abexp assumes equal std for both groups
        sample_size_calc = SampleSize()
        n_control = sample_size_calc.ssd_mean(
            mean_contr=baseline_mean,
            mean_treat=treatment_mean,
            std_contr=baseline_std,
            alpha=alpha,
            power=power
        )
        
        n_control = int(np.ceil(n_control))
        # Note: abexp's ssd_mean doesn't support ratio parameter
        # For unequal allocation, you'd need to adjust manually
        n_treatment = int(np.ceil(n_control * ratio))
        
        return {
            'control_size': n_control,
            'treatment_size': n_treatment,
            'total_size': n_control + n_treatment,
            'assumptions': {
                'baseline_mean': baseline_mean,
                'baseline_std': baseline_std,
                'treatment_mean': treatment_mean,
                'mde_relative': mde,
                'mde_absolute': treatment_mean - baseline_mean,
                'alpha': alpha,
                'power': power,
                'ratio': ratio,
            },
            'backend': 'abexp',
        }
