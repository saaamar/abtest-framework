"""Sample size calculation for A/B test planning."""

from typing import Dict
import numpy as np
from scipy import stats

class SampleSizeCalculator:
    """Calculate required sample size for experiments.
    
    Use this before running an experiment to determine how many users/samples
    you need to detect a given effect size with desired power.
    """
    
    @staticmethod
    def for_proportion(
        baseline_rate: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0
    ) -> Dict[str, any]:
        """Calculate sample size for proportion metrics (conversion, CTR).
        
        Args:
            baseline_rate: Current conversion rate (e.g., 0.10 = 10%)
            mde: Minimum detectable effect as relative change (e.g., 0.05 = 5% relative lift)
            alpha: Significance level (default 0.05 for 95% confidence)
            power: Statistical power (default 0.80)
            ratio: Treatment to control ratio (default 1.0 for 50/50 split)
        
        Returns:
            Dictionary containing:
                - control_size: Required control group size
                - treatment_size: Required treatment group size
                - total_size: Total required sample size
                - assumptions: Dict with all input parameters and derived values
        
        Example:
            >>> calc = SampleSizeCalculator()
            >>> result = calc.for_proportion(
            ...     baseline_rate=0.10,  # 10% current conversion
            ...     mde=0.05              # Want to detect 5% relative improvement
            ... )
            >>> print(f"Need {result['total_size']} users")
        """
        # Calculate effect size
        treatment_rate = baseline_rate * (1 + mde)
        pooled_rate = (baseline_rate + treatment_rate) / 2
        pooled_variance = pooled_rate * (1 - pooled_rate)
        
        # Z-scores for alpha and power
        z_alpha = stats.norm.ppf(1 - alpha / 2)  # Two-tailed
        z_beta = stats.norm.ppf(power)
        
        # Sample size calculation (per group for equal allocation)
        n_control = (
            (z_alpha + z_beta) ** 2 * pooled_variance * (1 + 1/ratio) / 
            (treatment_rate - baseline_rate) ** 2
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
                'pooled_rate': pooled_rate
            }
        }
    
    @staticmethod
    def for_mean(
        baseline_mean: float,
        baseline_std: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0
    ) -> Dict[str, any]:
        """Calculate sample size for continuous metrics (revenue, time on site).
        
        Args:
            baseline_mean: Current mean value (e.g., 50.0 for $50 revenue)
            baseline_std: Standard deviation of baseline (e.g., 25.0)
            mde: Minimum detectable effect as relative change (e.g., 0.10 = 10% lift)
            alpha: Significance level (default 0.05)
            power: Statistical power (default 0.80)
            ratio: Treatment to control ratio (default 1.0 for 50/50 split)
        
        Returns:
            Dictionary containing:
                - control_size: Required control group size
                - treatment_size: Required treatment group size
                - total_size: Total required sample size
                - assumptions: Dict with all input parameters and derived values
        
        Example:
            >>> calc = SampleSizeCalculator()
            >>> result = calc.for_mean(
            ...     baseline_mean=50.0,   # $50 average revenue
            ...     baseline_std=25.0,    # $25 std dev
            ...     mde=0.10              # Want to detect 10% improvement
            ... )
            >>> print(f"Need {result['total_size']} users")
        """
        treatment_mean = baseline_mean * (1 + mde)
        effect_size = abs(treatment_mean - baseline_mean) / baseline_std
        
        # Z-scores
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_beta = stats.norm.ppf(power)
        
        # Sample size calculation
        n_control = int(np.ceil(
            2 * (z_alpha + z_beta) ** 2 / effect_size ** 2 * (1 + 1/ratio)
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
                'ratio': ratio
            }
        }
