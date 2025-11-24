"""Base interface for statistical backends."""

from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np


class StatisticalBackend(ABC):
    """Abstract base class for statistical computation backends.
    
    This interface allows pluggable statistical engines (owl_ab_test, scipy, etc.)
    while keeping the orchestration layer independent.
    """
    
    @abstractmethod
    def test_proportion(
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
    def test_mean(
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
