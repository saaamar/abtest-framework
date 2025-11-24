"""Data quality and experiment health checks."""

from typing import Dict, List
from scipy import stats
import pandas as pd
import numpy as np

class QualityChecker:
    """Data quality and experiment health checks.
    
    Provides automatic checks for:
    - Sample Ratio Mismatch (SRM)
    - Missing values
    - Outliers
    - Data integrity issues
    """
    
    @staticmethod
    def check_srm(
        observed_counts: Dict[str, int],
        expected_ratio: Dict[str, float] = None,
        alpha: float = 0.001
    ) -> Dict[str, any]:
        """Check for Sample Ratio Mismatch using chi-square test.
        
        SRM occurs when the actual split between variants differs significantly
        from the expected split, indicating potential randomization issues.
        
        Args:
            observed_counts: Observed sample sizes, e.g., {'A': 1000, 'B': 950}
            expected_ratio: Expected ratios, e.g., {'A': 0.5, 'B': 0.5} or None for equal
            alpha: Significance level (default 0.001, more stringent than experiment alpha)
        
        Returns:
            Dictionary containing:
                - passed: bool, True if no SRM detected
                - p_value: float, p-value from chi-square test
                - chi_square: float, chi-square statistic
                - observed: Dict of observed counts
                - expected: Dict of expected counts
                - deviations_pct: Dict of percentage deviations
                - recommendation: str, human-readable recommendation
        
        Example:
            >>> checker = QualityChecker()
            >>> result = checker.check_srm({'A': 10523, 'B': 9477})
            >>> if not result['passed']:
            ...     print(result['recommendation'])
        """
        variants = list(observed_counts.keys())
        observed = list(observed_counts.values())
        total = sum(observed)
        
        # Default to equal split if not specified
        if expected_ratio is None:
            expected_ratio = {v: 1.0 / len(variants) for v in variants}
        
        # Validate expected_ratio sums to 1.0
        ratio_sum = sum(expected_ratio.values())
        if not np.isclose(ratio_sum, 1.0):
            raise ValueError(f"Expected ratios must sum to 1.0, got {ratio_sum}")
        
        expected = [expected_ratio[v] * total for v in variants]
        
        # Chi-square test
        chi_square, p_value = stats.chisquare(observed, expected)
        
        passed = p_value > alpha
        
        # Calculate deviations
        deviations = {
            v: (observed_counts[v] - exp) / exp 
            for v, exp in zip(variants, expected)
        }
        
        # Generate recommendation
        if passed:
            recommendation = '[OK] No SRM detected - randomization looks good'
        else:
            max_dev_variant = max(deviations, key=lambda k: abs(deviations[k]))
            max_dev = deviations[max_dev_variant] * 100
            recommendation = (
                f'[WARNING] SRM DETECTED (p={p_value:.6f}, alpha={alpha})\n'
                f'Variant {max_dev_variant} deviates by {max_dev:+.1f}%\n'
                f'Action: Check randomization logic and data collection'
            )
        
        return {
            'passed': passed,
            'p_value': p_value,
            'chi_square': chi_square,
            'observed': observed_counts,
            'expected': {v: exp for v, exp in zip(variants, expected)},
            'deviations_pct': {v: d * 100 for v, d in deviations.items()},
            'recommendation': recommendation,
            'alpha': alpha
        }
    
    @staticmethod
    def check_data_quality(
        df: pd.DataFrame,
        metrics: List[str],
        missing_threshold: float = 0.05,
        outlier_threshold: float = 0.01
    ) -> Dict[str, any]:
        """Check for data quality issues in metrics.
        
        Args:
            df: DataFrame containing metric data
            metrics: List of metric column names to check
            missing_threshold: Flag if >X% missing (default 5%)
            outlier_threshold: Flag if >X% outliers (default 1%)
        
        Returns:
            Dictionary containing:
                - passed: bool, True if no issues
                - issues: List of issue descriptions
                - details: Dict with per-metric details
                - recommendation: str
        
        Example:
            >>> checker = QualityChecker()
            >>> result = checker.check_data_quality(
            ...     df=experiment_data,
            ...     metrics=['conversion', 'revenue']
            ... )
        """
        issues = []
        details = {}
        
        for metric in metrics:
            metric_details = {}
            
            if metric not in df.columns:
                issues.append(f'[ERROR] Missing column: {metric}')
                continue
            
            # Check missing values
            missing_count = df[metric].isna().sum()
            missing_pct = missing_count / len(df) * 100
            metric_details['missing_count'] = missing_count
            metric_details['missing_pct'] = missing_pct
            
            if missing_pct > missing_threshold * 100:
                issues.append(
                    f'[WARNING] {metric}: {missing_pct:.1f}% missing values '
                    f'(threshold: {missing_threshold*100:.1f}%)'
                )
            
            # Check outliers using IQR method (only for numeric data)
            if pd.api.types.is_numeric_dtype(df[metric]):
                valid_data = df[metric].dropna()
                if len(valid_data) > 0:
                    q1 = valid_data.quantile(0.25)
                    q3 = valid_data.quantile(0.75)
                    iqr = q3 - q1
                    
                    lower_bound = q1 - 3 * iqr
                    upper_bound = q3 + 3 * iqr
                    
                    outliers = ((valid_data < lower_bound) | (valid_data > upper_bound)).sum()
                    outlier_pct = outliers / len(valid_data) * 100
                    
                    metric_details['outlier_count'] = outliers
                    metric_details['outlier_pct'] = outlier_pct
                    metric_details['outlier_bounds'] = (lower_bound, upper_bound)
                    
                    if outlier_pct > outlier_threshold * 100:
                        issues.append(
                            f'[WARNING] {metric}: {outlier_pct:.1f}% outliers '
                            f'(threshold: {outlier_threshold*100:.1f}%)'
                        )
                    
                    # Basic statistics
                    metric_details['mean'] = float(valid_data.mean())
                    metric_details['std'] = float(valid_data.std())
                    metric_details['min'] = float(valid_data.min())
                    metric_details['max'] = float(valid_data.max())
            
            details[metric] = metric_details
        
        passed = len(issues) == 0
        
        if passed:
            recommendation = '[OK] Data quality looks good - no issues detected'
        else:
            recommendation = (
                f'[WARNING] Found {len(issues)} data quality issue(s)\n' +
                '\n'.join(issues)
            )
        
        return {
            'passed': passed,
            'issues': issues,
            'details': details,
            'recommendation': recommendation
        }
