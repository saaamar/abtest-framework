"""
Ground Truth Calculator
Uses scipy directly to calculate correct statistical results for each scenario
These results serve as the baseline to validate other packages
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any

def calculate_proportion_test(
    successes_a: int,
    n_a: int,
    successes_b: int,
    n_b: int,
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Two-proportion z-test for comparing conversion rates
    
    Returns:
        Dictionary with test results
    """
    p_a = successes_a / n_a
    p_b = successes_b / n_b
    
    # Pooled proportion for null hypothesis
    p_pooled = (successes_a + successes_b) / (n_a + n_b)
    
    # Standard error
    se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n_a + 1/n_b))
    
    # Z-statistic
    z_stat = (p_b - p_a) / se
    
    # P-value (two-tailed)
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    
    # Confidence interval for difference
    se_diff = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    ci_lower = (p_b - p_a) - 1.96 * se_diff
    ci_upper = (p_b - p_a) + 1.96 * se_diff
    
    # Effect size (relative lift)
    relative_lift = (p_b - p_a) / p_a if p_a > 0 else 0
    
    return {
        'metric_a': p_a,
        'metric_b': p_b,
        'absolute_diff': p_b - p_a,
        'relative_lift': relative_lift,
        'z_stat': z_stat,
        'p_value': p_value,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'significant': p_value < alpha,
        'n_a': n_a,
        'n_b': n_b
    }

def calculate_ttest(
    values_a: np.ndarray,
    values_b: np.ndarray,
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Independent samples t-test for comparing means
    
    Returns:
        Dictionary with test results
    """
    mean_a = np.mean(values_a)
    mean_b = np.mean(values_b)
    
    # Welch's t-test (unequal variances)
    t_stat, p_value = stats.ttest_ind(values_a, values_b, equal_var=False)
    
    # Confidence interval for difference
    n_a = len(values_a)
    n_b = len(values_b)
    var_a = np.var(values_a, ddof=1)
    var_b = np.var(values_b, ddof=1)
    
    se_diff = np.sqrt(var_a/n_a + var_b/n_b)
    
    # Degrees of freedom (Welch-Satterthwaite)
    df = (var_a/n_a + var_b/n_b)**2 / ((var_a/n_a)**2/(n_a-1) + (var_b/n_b)**2/(n_b-1))
    
    t_critical = stats.t.ppf(1 - alpha/2, df)
    ci_lower = (mean_b - mean_a) - t_critical * se_diff
    ci_upper = (mean_b - mean_a) + t_critical * se_diff
    
    # Effect size (Cohen's d)
    pooled_std = np.sqrt((var_a + var_b) / 2)
    cohens_d = (mean_b - mean_a) / pooled_std if pooled_std > 0 else 0
    
    return {
        'metric_a': mean_a,
        'metric_b': mean_b,
        'absolute_diff': mean_b - mean_a,
        'relative_lift': (mean_b - mean_a) / mean_a if mean_a > 0 else 0,
        't_stat': t_stat,
        'p_value': p_value,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'cohens_d': cohens_d,
        'significant': p_value < alpha,
        'n_a': n_a,
        'n_b': n_b
    }

def scenario1_ground_truth(file_path: str = "verification/data/scenario1_conversion.csv") -> Dict[str, Any]:
    """
    Ground truth for Scenario 1: Simple Conversion Rate Test
    """
    df = pd.read_csv(file_path)
    
    df_a = df[df['variant'] == 'A']
    df_b = df[df['variant'] == 'B']
    
    successes_a = df_a['converted'].sum()
    n_a = len(df_a)
    successes_b = df_b['converted'].sum()
    n_b = len(df_b)
    
    result = calculate_proportion_test(successes_a, n_a, successes_b, n_b)
    result['scenario'] = 'Scenario 1: Conversion Rate'
    result['test_type'] = 'Two-proportion z-test'
    
    return result

def scenario2_ground_truth(file_path: str = "verification/data/scenario2_revenue.csv") -> Dict[str, Any]:
    """
    Ground truth for Scenario 2: Revenue per Active User
    Custom metric: revenue divided by number of active users (sessions > 0)
    """
    df = pd.read_csv(file_path)
    
    # Filter to active users only
    df_active = df[df['sessions'] > 0]
    
    # Group by variant and calculate per-user revenue
    df_a = df_active[df_active['variant'] == 'A']
    df_b = df_active[df_active['variant'] == 'B']
    
    # Revenue per active user (each row is a user)
    revenue_a = df_a['revenue'].values
    revenue_b = df_b['revenue'].values
    
    result = calculate_ttest(revenue_a, revenue_b)
    result['scenario'] = 'Scenario 2: Revenue per Active User'
    result['test_type'] = 'Welch\'s t-test'
    result['note'] = 'Only active users (sessions > 0) included'
    
    return result

def scenario3_ground_truth(file_path: str = "verification/data/scenario3_ctr.csv") -> Dict[str, Any]:
    """
    Ground truth for Scenario 3: CTR with Exposure Filtering
    Custom metric: clicks / impressions for exposed users only
    """
    df = pd.read_csv(file_path)
    
    # Filter to exposed users only
    df_exposed = df[df['exposed'] == 1]
    
    df_a = df_exposed[df_exposed['variant'] == 'A']
    df_b = df_exposed[df_exposed['variant'] == 'B']
    
    # Total clicks and impressions
    clicks_a = df_a['clicks'].sum()
    impressions_a = df_a['impressions'].sum()
    clicks_b = df_b['clicks'].sum()
    impressions_b = df_b['impressions'].sum()
    
    # Use proportion test treating total clicks as successes, impressions as trials
    result = calculate_proportion_test(clicks_a, impressions_a, clicks_b, impressions_b)
    result['scenario'] = 'Scenario 3: CTR with Exposure'
    result['test_type'] = 'Two-proportion z-test (aggregated)'
    result['note'] = 'Only exposed users included, aggregated clicks/impressions'
    
    return result

def scenario4_ground_truth(file_path: str = "verification/data/scenario4_multi.csv") -> Dict[str, Any]:
    """
    Ground truth for Scenario 4: Multi-Metric Dashboard
    Multiple metrics tested simultaneously
    """
    df = pd.read_csv(file_path)
    
    df_a = df[df['variant'] == 'A']
    df_b = df[df['variant'] == 'B']
    
    results = {}
    
    # Metric 1: Conversion Rate
    successes_a = df_a['converted'].sum()
    n_a = len(df_a)
    successes_b = df_b['converted'].sum()
    n_b = len(df_b)
    results['conversion_rate'] = calculate_proportion_test(successes_a, n_a, successes_b, n_b)
    
    # Metric 2: Average Order Value (for converted users only)
    converted_a = df_a[df_a['converted'] == 1]['order_value'].values
    converted_b = df_b[df_b['converted'] == 1]['order_value'].values
    results['avg_order_value'] = calculate_ttest(converted_a, converted_b)
    
    # Metric 3: Revenue per User (all users)
    revenue_a = df_a['revenue'].values
    revenue_b = df_b['revenue'].values
    results['revenue_per_user'] = calculate_ttest(revenue_a, revenue_b)
    
    # Metric 4: Time to Conversion (for converted users only)
    time_a = df_a[df_a['converted'] == 1]['time_to_conversion'].dropna().values
    time_b = df_b[df_b['converted'] == 1]['time_to_conversion'].dropna().values
    results['time_to_conversion'] = calculate_ttest(time_a, time_b)
    
    # Bonferroni correction for multiple testing
    n_tests = 4
    bonferroni_alpha = 0.05 / n_tests
    
    results['bonferroni_alpha'] = bonferroni_alpha
    results['scenario'] = 'Scenario 4: Multi-Metric Dashboard'
    results['note'] = f'4 metrics tested, Bonferroni-corrected alpha = {bonferroni_alpha:.4f}'
    
    return results

def print_result(result: Dict[str, Any], indent: int = 0):
    """Pretty print test results"""
    prefix = "  " * indent
    
    if 'scenario' in result:
        print(f"\n{prefix}{'='*60}")
        print(f"{prefix}{result['scenario']}")
        print(f"{prefix}{'='*60}")
    
    if 'test_type' in result:
        print(f"{prefix}Test: {result['test_type']}")
    
    if 'note' in result:
        print(f"{prefix}Note: {result['note']}")
    
    if 'metric_a' in result:
        print(f"\n{prefix}Variant A: {result['metric_a']:.6f}")
        print(f"{prefix}Variant B: {result['metric_b']:.6f}")
        print(f"{prefix}Absolute Difference: {result['absolute_diff']:.6f}")
        print(f"{prefix}Relative Lift: {result['relative_lift']*100:.2f}%")
        
        if 't_stat' in result:
            print(f"{prefix}T-statistic: {result['t_stat']:.4f}")
        elif 'z_stat' in result:
            print(f"{prefix}Z-statistic: {result['z_stat']:.4f}")
        
        print(f"{prefix}P-value: {result['p_value']:.6f}")
        print(f"{prefix}95% CI: [{result['ci_lower']:.6f}, {result['ci_upper']:.6f}]")
        print(f"{prefix}Significant (α=0.05): {result['significant']}")
        print(f"{prefix}Sample sizes: A={result['n_a']}, B={result['n_b']}")

def generate_all_ground_truths():
    """Calculate and display ground truth for all scenarios"""
    
    print("\n" + "="*70)
    print("GROUND TRUTH CALCULATIONS (using scipy)")
    print("="*70)
    
    # Scenario 1
    result1 = scenario1_ground_truth()
    print_result(result1)
    
    # Scenario 2
    result2 = scenario2_ground_truth()
    print_result(result2)
    
    # Scenario 3
    result3 = scenario3_ground_truth()
    print_result(result3)
    
    # Scenario 4
    result4 = scenario4_ground_truth()
    print(f"\n{'='*60}")
    print(result4['scenario'])
    print('='*60)
    print(f"Note: {result4['note']}")
    
    metrics = ['conversion_rate', 'avg_order_value', 'revenue_per_user', 'time_to_conversion']
    metric_names = ['Conversion Rate', 'Average Order Value', 'Revenue per User', 'Time to Conversion']
    
    for metric, name in zip(metrics, metric_names):
        print(f"\n  Metric: {name}")
        print_result(result4[metric], indent=1)
    
    print("\n" + "="*70)
    print("Ground truth calculations complete!")
    print("="*70)
    
    return result1, result2, result3, result4

if __name__ == "__main__":
    generate_all_ground_truths()
