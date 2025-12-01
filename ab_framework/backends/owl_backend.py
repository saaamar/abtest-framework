"""Owl AB Test backend implementation."""

from typing import Dict, Any
import numpy as np
from owl_ab_test import calculate_proportion_stats, calculate_revenue_stats
from .base import StatisticalBackend
from scipy import stats


class OwlBackend(StatisticalBackend):
    """Statistical backend using owl_ab_test package.
    
    This backend wraps owl_ab_test's functions to provide a consistent interface
    for the AB testing framework.
    """
    
    def proportion_z_test(
        self,
        successes_a: int,
        trials_a: int,
        successes_b: int,
        trials_b: int,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """Test difference in proportions using owl_ab_test.
        
        Args:
            successes_a: Number of successes in control group
            trials_a: Total trials in control group
            successes_b: Number of successes in treatment group
            trials_b: Total trials in treatment group
            alpha: Significance level (default 0.05)
        
        Returns:
            Dictionary with test results
        """
        # Call owl_ab_test function
        result = calculate_proportion_stats(
            success_count=successes_b,
            total_count=trials_b,
            control_success=successes_a,
            control_total=trials_a,
            confidence_level=1 - alpha
        )
        
        # owl_ab_test already returns a dict with most fields we need
        # Add any additional computed fields for consistency
        control_rate = successes_a / trials_a if trials_a > 0 else 0
        treatment_rate = successes_b / trials_b if trials_b > 0 else 0
        
        return {
            'p_value': result['p_value'],
            'ci_lower': result['ci_lower'],
            'ci_upper': result['ci_upper'],
            'lift': result['lift'],
            'statistic': result['statistic'],
            'control_rate': control_rate,
            'treatment_rate': treatment_rate,
            'backend': 'owl_ab_test'
        }
    
    def mean_t_test(
        self,
        values_a: np.ndarray,
        values_b: np.ndarray,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """Test difference in means using owl_ab_test.
        
        Args:
            values_a: Array of values from control group
            values_b: Array of values from treatment group
            alpha: Significance level (default 0.05)
        
        Returns:
            Dictionary with test results
        """
        # Pre-compute statistics required by owl_ab_test
        mean_a = float(np.mean(values_a))
        std_a = float(np.std(values_a, ddof=1))
        n_a = len(values_a)
        
        mean_b = float(np.mean(values_b))
        std_b = float(np.std(values_b, ddof=1))
        n_b = len(values_b)
        
        # Call owl_ab_test function
        result = calculate_revenue_stats(
            treatment_value=mean_b,
            treatment_std=std_b,
            treatment_n=n_b,
            control_value=mean_a,
            control_std=std_a,
            control_n=n_a,
            confidence_level=1 - alpha
        )
        
        # Add computed fields
        mean_diff = mean_b - mean_a
        
        return {
            'p_value': result['p_value'],
            'ci_lower': result['ci_lower'],
            'ci_upper': result['ci_upper'],
            'lift': result['lift'],
            'statistic': result['statistic'],
            'mean_diff': mean_diff,
            'control_mean': mean_a,
            'treatment_mean': mean_b,
            'control_std': std_a,
            'treatment_std': std_b,
            'control_n': n_a,
            'treatment_n': n_b,
            'backend': 'owl_ab_test'
        }

    def sample_size_proportion(
        self,
        baseline_rate: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
    ) -> Dict[str, Any]:
        """Sample size planning for proportion metrics using normal approximation.

            This uses the same closed-form normal-approximation formula described
            in the theory documentation for proportion metrics so that existing
            theoretical documentation remains accurate.
        """
        treatment_rate = baseline_rate * (1 + mde)
        pooled_rate = (baseline_rate + treatment_rate) / 2
        pooled_variance = pooled_rate * (1 - pooled_rate)

        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_beta = stats.norm.ppf(power)

        n_control = (
            (z_alpha + z_beta) ** 2 * pooled_variance * (1 + 1 / ratio)
            / (treatment_rate - baseline_rate) ** 2
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
            'backend': 'owl_ab_test',
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
        """Sample size planning for continuous metrics using normal approximation.

            This mirrors the normal-approximation formula described in the
            theory documentation for continuous metrics.
        """
        treatment_mean = baseline_mean * (1 + mde)
        effect_size = abs(treatment_mean - baseline_mean) / baseline_std

        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_beta = stats.norm.ppf(power)

        n_control = int(
            np.ceil(
                2 * (z_alpha + z_beta) ** 2 / effect_size ** 2 * (1 + 1 / ratio)
            )
        )
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
            'backend': 'owl_ab_test',
        }
