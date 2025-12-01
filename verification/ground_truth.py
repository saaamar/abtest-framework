"""
Ground Truth Calculator
Uses scipy directly to calculate correct statistical results for each scenario
These results serve as the baseline to validate other packages
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))
from format_results import format_conclusion, format_multi_metric_conclusion

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

def scenario1_ground_truth(data_dir: str = "data") -> Dict[str, Any]:
    """
    Ground truth for Scenario 1: Simple Conversion Rate Test
    
    NEW: Impression-level data - aggregate to user level first
    """
    file_path = os.path.join(data_dir, "scenario1_conversion.csv")
    df = pd.read_csv(file_path)
    
    # Aggregate to user level: did user convert in ANY impression?
    user_conversions = df.groupby(['user_id', 'variant'])['converted'].max().reset_index()
    
    df_a = user_conversions[user_conversions['variant'] == 'A']
    df_b = user_conversions[user_conversions['variant'] == 'B']
    
    successes_a = df_a['converted'].sum()
    n_a = len(df_a)
    successes_b = df_b['converted'].sum()
    n_b = len(df_b)
    
    result = calculate_proportion_test(successes_a, n_a, successes_b, n_b)
    result['scenario'] = 'Scenario 1: Conversion Rate'
    result['test_type'] = 'Two-proportion z-test'
    result['note'] = f'Aggregated from {len(df)} impressions to {len(user_conversions)} users'
    
    return result

def scenario2_ground_truth(data_dir: str = "data") -> Dict[str, Any]:
    """
    Ground truth for Scenario 2: Revenue per Active User
    
    NEW: Session-level data - aggregate to user level
    Custom metric: total session revenue per active user
    """
    file_path = os.path.join(data_dir, "scenario2_revenue.csv")
    df = pd.read_csv(file_path)
    
    # Aggregate session revenue to user level
    user_revenue = df.groupby(['user_id', 'variant'])['session_revenue'].sum().reset_index()
    
    # Split by variant
    df_a = user_revenue[user_revenue['variant'] == 'A']
    df_b = user_revenue[user_revenue['variant'] == 'B']
    
    # Revenue per active user
    revenue_a = df_a['session_revenue'].values
    revenue_b = df_b['session_revenue'].values
    
    result = calculate_ttest(revenue_a, revenue_b)
    result['scenario'] = 'Scenario 2: Revenue per Active User'
    result['test_type'] = 'Welch\'s t-test'
    result['note'] = f'Aggregated from {len(df)} sessions to {len(user_revenue)} active users'
    
    return result

def scenario3_ground_truth(data_dir: str = "data") -> Dict[str, Any]:
    """
    Ground truth for Scenario 3: CTR (Click-Through Rate)
    
    Impression-level data - each row is one impression
    CTR = total clicks / total impressions
    """
    file_path = os.path.join(data_dir, "scenario3_ctr.csv")
    df = pd.read_csv(file_path)
    
    df_a = df[df['variant'] == 'A']
    df_b = df[df['variant'] == 'B']
    
    # Total clicks and impressions (each row is one impression)
    clicks_a = df_a['clicked'].sum()
    impressions_a = len(df_a)
    clicks_b = df_b['clicked'].sum()
    impressions_b = len(df_b)
    
    # Use proportion test treating total clicks as successes, impressions as trials
    result = calculate_proportion_test(clicks_a, impressions_a, clicks_b, impressions_b)
    result['scenario'] = 'Scenario 3: CTR (Click-Through Rate)'
    result['test_type'] = 'Two-proportion z-test'
    result['note'] = f'Impression-level analysis: {len(df)} impressions from {df["user_id"].nunique()} users'
    
    return result

def scenario4_ground_truth(data_dir: str = "data") -> Dict[str, Any]:
    """
    Ground truth for Scenario 4: Multi-Metric Dashboard
    
    NEW: Session-level data - aggregate to user level for metrics
    Multiple metrics tested simultaneously
    """
    file_path = os.path.join(data_dir, "scenario4_multi.csv")
    df = pd.read_csv(file_path)
    
    # Aggregate to user level for different metrics
    user_metrics = df.groupby(['user_id', 'variant']).agg({
        'converted_this_session': 'max',  # Did user convert in any session?
        'order_value': 'sum',  # Total order value
        'session_revenue': 'sum'  # Total revenue
    }).reset_index()
    
    df_a = user_metrics[user_metrics['variant'] == 'A']
    df_b = user_metrics[user_metrics['variant'] == 'B']
    
    results = {}
    
    # Metric 1: Conversion Rate
    successes_a = int(df_a['converted_this_session'].sum())
    n_a = len(df_a)
    successes_b = int(df_b['converted_this_session'].sum())
    n_b = len(df_b)
    results['conversion_rate'] = calculate_proportion_test(successes_a, n_a, successes_b, n_b)
    
    # Metric 2: Average Order Value (for converted users only)
    converted_a = df_a[df_a['converted_this_session'] == 1]['order_value'].values
    converted_b = df_b[df_b['converted_this_session'] == 1]['order_value'].values
    results['avg_order_value'] = calculate_ttest(converted_a, converted_b)
    
    # Metric 3: Revenue per User (all users)
    revenue_a = df_a['session_revenue'].values
    revenue_b = df_b['session_revenue'].values
    results['revenue_per_user'] = calculate_ttest(revenue_a, revenue_b)
    
    # Bonferroni correction for multiple testing
    n_tests = 3
    bonferroni_alpha = 0.05 / n_tests
    
    results['bonferroni_alpha'] = bonferroni_alpha
    results['scenario'] = 'Scenario 4: Multi-Metric Dashboard'
    results['note'] = f'Aggregated from {len(df)} sessions to {len(user_metrics)} users, 3 metrics tested, Bonferroni α = {bonferroni_alpha:.4f}'
    
    return results

def print_result(result: Dict[str, Any], indent: int = 0, metric_name: str = None, is_percentage: bool = False, currency: bool = False):
    """Pretty print test results with professional conclusion"""
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
        
        # Add professional conclusion
        if metric_name and indent == 0:  # Only for top-level results
            conclusion = format_conclusion(
                metric_name=metric_name,
                variant_a_value=result['metric_a'],
                variant_b_value=result['metric_b'],
                p_value=result['p_value'],
                ci_lower=result['ci_lower'],
                ci_upper=result['ci_upper'],
                is_percentage=is_percentage,
                currency=currency
            )
            print(conclusion)

def scenario5_ground_truth(data_dir: str = "data") -> Dict[str, Any]:
    """
    Ground truth for Scenario 5: Agent Bot - Resolved Rate WITH gap
    
    Session-level data - testing resolved rate (binary metric)
    """
    file_path = os.path.join(data_dir, "scenario5_resolved_with_gap.csv")
    df = pd.read_csv(file_path)
    
    df_a = df[df['variant'] == 'A']
    df_b = df[df['variant'] == 'B']
    
    # Resolved rate at session level
    resolved_a = df_a['is_resolved'].sum()
    n_a = len(df_a)
    resolved_b = df_b['is_resolved'].sum()
    n_b = len(df_b)
    
    result = calculate_proportion_test(resolved_a, n_a, resolved_b, n_b)
    result['scenario'] = 'Scenario 5: Agent Bot - Resolved Rate (WITH gap)'
    result['test_type'] = 'Two-proportion z-test'
    result['note'] = f'Session-level analysis: {len(df)} sessions'
    
    return result

def scenario6_ground_truth(data_dir: str = "data") -> Dict[str, Any]:
    """
    Ground truth for Scenario 6: Agent Bot - Resolved Rate NO gap
    
    Session-level data - testing resolved rate (should show NO significance)
    """
    file_path = os.path.join(data_dir, "scenario6_resolved_no_gap.csv")
    df = pd.read_csv(file_path)
    
    df_a = df[df['variant'] == 'A']
    df_b = df[df['variant'] == 'B']
    
    resolved_a = df_a['is_resolved'].sum()
    n_a = len(df_a)
    resolved_b = df_b['is_resolved'].sum()
    n_b = len(df_b)
    
    result = calculate_proportion_test(resolved_a, n_a, resolved_b, n_b)
    result['scenario'] = 'Scenario 6: Agent Bot - Resolved Rate (NO gap)'
    result['test_type'] = 'Two-proportion z-test'
    result['note'] = f'Session-level analysis: {len(df)} sessions'
    
    return result

def scenario7_ground_truth(data_dir: str = "data") -> Dict[str, Any]:
    """
    Ground truth for Scenario 7: Agent Bot - AI Quality Metric WITH gap
    
    Session-level data - testing AI metric (continuous 0-5 score)
    """
    file_path = os.path.join(data_dir, "scenario7_ai_metric_with_gap.csv")
    df = pd.read_csv(file_path)
    
    df_a = df[df['variant'] == 'A']
    df_b = df[df['variant'] == 'B']
    
    ai_metric_a = df_a['ai_metric'].values
    ai_metric_b = df_b['ai_metric'].values
    
    result = calculate_ttest(ai_metric_a, ai_metric_b)
    result['scenario'] = 'Scenario 7: Agent Bot - AI Quality Metric (WITH gap)'
    result['test_type'] = 'Welch\'s t-test'
    result['note'] = f'Session-level analysis: {len(df)} sessions'
    
    return result

def scenario8_ground_truth(data_dir: str = "data") -> Dict[str, Any]:
    """
    Ground truth for Scenario 8: Agent Bot - AI Quality Metric NO gap
    
    Session-level data - testing AI metric (should show NO significance)
    """
    file_path = os.path.join(data_dir, "scenario8_ai_metric_no_gap.csv")
    df = pd.read_csv(file_path)
    
    df_a = df[df['variant'] == 'A']
    df_b = df[df['variant'] == 'B']
    
    ai_metric_a = df_a['ai_metric'].values
    ai_metric_b = df_b['ai_metric'].values
    
    result = calculate_ttest(ai_metric_a, ai_metric_b)
    result['scenario'] = 'Scenario 8: Agent Bot - AI Quality Metric (NO gap)'
    result['test_type'] = 'Welch\'s t-test'
    result['note'] = f'Session-level analysis: {len(df)} sessions'
    
    return result

def generate_all_ground_truths():
    """Calculate and display ground truth for all scenarios"""
    
    print("\n" + "="*70)
    print("GROUND TRUTH CALCULATIONS (using scipy)")
    print("="*70)
    
    # Scenario 1
    result1 = scenario1_ground_truth()
    print_result(result1, metric_name="conversion rate", is_percentage=True)
    
    # Scenario 2
    result2 = scenario2_ground_truth()
    print_result(result2, metric_name="revenue per active user", currency=True)
    
    # Scenario 3
    result3 = scenario3_ground_truth()
    print_result(result3, metric_name="click-through rate (CTR)", is_percentage=True)
    
    # Scenario 4
    result4 = scenario4_ground_truth()
    print(f"\n{'='*60}")
    print(result4['scenario'])
    print('='*60)
    print(f"Note: {result4['note']}")
    
    metrics = ['conversion_rate', 'avg_order_value', 'revenue_per_user']
    metric_names = ['Conversion Rate', 'Average Order Value', 'Revenue per User']
    
    for metric, name in zip(metrics, metric_names):
        print(f"\n  Metric: {name}")
        print_result(result4[metric], indent=1)
    
    # Add multi-metric conclusion
    multi_conclusion = format_multi_metric_conclusion(
        {k: result4[k] for k in metrics},
        bonferroni_alpha=result4['bonferroni_alpha']
    )
    print(multi_conclusion)
    
    # Scenario 5
    result5 = scenario5_ground_truth()
    print_result(result5, metric_name="resolved rate", is_percentage=True)
    
    # Scenario 6
    result6 = scenario6_ground_truth()
    print_result(result6, metric_name="resolved rate", is_percentage=True)
    
    # Scenario 7
    result7 = scenario7_ground_truth()
    print_result(result7, metric_name="AI quality metric (0-5 scale)")
    
    # Scenario 8
    result8 = scenario8_ground_truth()
    print_result(result8, metric_name="AI quality metric (0-5 scale)")
    
    print("\n" + "="*70)
    print("Ground truth calculations complete for all 8 scenarios!")
    print("="*70)
    
    return result1, result2, result3, result4, result5, result6, result7, result8

if __name__ == "__main__":
    generate_all_ground_truths()
