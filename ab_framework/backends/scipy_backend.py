"""Generic statistical backend using only standard libraries (scipy, numpy)."""

from typing import Dict, Any
import numpy as np
from scipy import stats
from .base import StatisticalBackend


class ScipyBackend(StatisticalBackend):
    """Statistical backend using scipy and standard libraries only.
    
    This backend provides statistical computations without relying on
    specialized A/B testing packages, using only scipy and numpy.
    """
    
    def proportion_z_test(
        self,
        successes_a: int,
        trials_a: int,
        successes_b: int,
        trials_b: int,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """Test difference in proportions using two-proportion z-test.
        
        Args:
            successes_a: Number of successes in control group
            trials_a: Total trials in control group
            successes_b: Number of successes in treatment group
            trials_b: Total trials in treatment group
            alpha: Significance level (default 0.05)
        
        Returns:
            Dictionary with test results
        """
        # Calculate proportions
        p1 = successes_a / trials_a if trials_a > 0 else 0
        p2 = successes_b / trials_b if trials_b > 0 else 0
        
        # Pooled proportion for standard error calculation
        n1, n2 = trials_a, trials_b
        p_pool = (successes_a + successes_b) / (n1 + n2) if (n1 + n2) > 0 else 0
        
        # Standard error of difference in proportions
        se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2)) if (n1 > 0 and n2 > 0) else 1.0
        
        # Z-statistic
        z_stat = (p2 - p1) / se if se > 0 else 0
        
        # Two-tailed p-value
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        
        # Confidence interval for difference (p2 - p1)
        # Using Wald method for difference in proportions
        se_diff = np.sqrt((p1*(1-p1)/n1) + (p2*(1-p2)/n2)) if (n1 > 0 and n2 > 0) else 1.0
        z_critical = stats.norm.ppf(1 - alpha/2)
        diff = p2 - p1
        ci_lower = diff - z_critical * se_diff
        ci_upper = diff + z_critical * se_diff
        
        # Relative lift
        lift = (p2 - p1) / p1 if p1 > 0 else 0.0
        
        return {
            'p_value': p_value,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'lift': lift,
            'statistic': z_stat,
            'control_rate': p1,
            'treatment_rate': p2,
            'backend': 'scipy'
        }
    
    def mean_t_test(
        self,
        values_a: np.ndarray,
        values_b: np.ndarray,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """Test difference in means using two-sample t-test.
        
        Args:
            values_a: Array of values from control group
            values_b: Array of values from treatment group
            alpha: Significance level (default 0.05)
        
        Returns:
            Dictionary with test results
        """
        # Perform two-sample t-test (assumes unequal variances - Welch's t-test)
        t_stat, p_value = stats.ttest_ind(values_b, values_a, equal_var=False)
        
        # Calculate descriptive statistics
        mean_a = np.mean(values_a)
        mean_b = np.mean(values_b)
        std_a = np.std(values_a, ddof=1)
        std_b = np.std(values_b, ddof=1)
        n_a = len(values_a)
        n_b = len(values_b)
        
        # Mean difference
        mean_diff = mean_b - mean_a
        
        # Standard error for difference in means (Welch's method)
        se_diff = np.sqrt((std_a**2 / n_a) + (std_b**2 / n_b))
        
        # Degrees of freedom (Welch-Satterthwaite equation)
        df = ((std_a**2 / n_a) + (std_b**2 / n_b))**2 / (
            (std_a**2 / n_a)**2 / (n_a - 1) + (std_b**2 / n_b)**2 / (n_b - 1)
        )
        
        # Confidence interval for difference
        t_critical = stats.t.ppf(1 - alpha/2, df)
        ci_lower = mean_diff - t_critical * se_diff
        ci_upper = mean_diff + t_critical * se_diff
        
        # Relative lift
        lift = mean_diff / mean_a if mean_a != 0 else 0.0
        
        return {
            'p_value': p_value,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'mean_diff': mean_diff,
            'lift': lift,
            'statistic': t_stat,
            'control_mean': mean_a,
            'treatment_mean': mean_b,
            'control_std': std_a,
            'treatment_std': std_b,
            'control_n': n_a,
            'treatment_n': n_b,
            'backend': 'scipy'
        }

    def sample_size_proportion(
        self,
        baseline_rate: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
    ) -> Dict[str, Any]:
        """Plan sample size for proportion metrics using standard formulas.
        
        Args:
            baseline_rate: Current/expected control conversion rate
            mde: Minimum detectable effect as relative change
            alpha: Significance level (default 0.05)
            power: Desired statistical power (default 0.80)
            ratio: Treatment:control allocation ratio (default 1.0)
        
        Returns:
            Dictionary with sample size requirements
        """
        # Treatment rate
        treatment_rate = baseline_rate * (1 + mde)
        
        # Pooled proportion for variance calculation
        pooled_rate = (baseline_rate + treatment_rate) / 2
        pooled_variance = pooled_rate * (1 - pooled_rate)
        
        # Critical values
        z_alpha = stats.norm.ppf(1 - alpha / 2)  # Two-tailed
        z_beta = stats.norm.ppf(power)
        
        # Sample size calculation (equal allocation adjusted for ratio)
        n_control = (
            (z_alpha + z_beta)**2 * pooled_variance * (1 + 1/ratio) 
            / (treatment_rate - baseline_rate)**2
        )
        
        n_control = int(np.ceil(n_control))
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
                'pooled_rate': pooled_rate,
            },
            'backend': 'scipy',
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
        """Plan sample size for continuous metrics using standard formulas.
        
        Args:
            baseline_mean: Expected control group mean
            baseline_std: Expected standard deviation
            mde: Minimum detectable effect as relative change
            alpha: Significance level (default 0.05)
            power: Desired statistical power (default 0.80)
            ratio: Treatment:control allocation ratio (default 1.0)
        
        Returns:
            Dictionary with sample size requirements
        """
        # Treatment mean
        treatment_mean = baseline_mean * (1 + mde)
        
        # Effect size (Cohen's d)
        effect_size = abs(treatment_mean - baseline_mean) / baseline_std
        
        # Critical values
        z_alpha = stats.norm.ppf(1 - alpha / 2)  # Two-tailed
        z_beta = stats.norm.ppf(power)
        
        # Sample size calculation for two-sample t-test
        n_control = int(np.ceil(
            2 * (z_alpha + z_beta)**2 / effect_size**2 * (1 + 1/ratio)
        ))
        n_treatment = int(np.ceil(n_control * ratio))
        
        return {
            'control_size': n_control,
            'treatment_size': n_treatment,
            'total_size': n_control + n_treatment,
            'assumptions': {
                'baseline_mean': baseline_mean,
                'baseline_std': baseline_std,
                'treatment_mean': treatment_mean,
                'effect_size_cohen_d': effect_size,
                'mde_relative': mde,
                'mde_absolute': treatment_mean - baseline_mean,
                'alpha': alpha,
                'power': power,
                'ratio': ratio,
            },
            'backend': 'scipy',
        }