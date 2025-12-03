"""
Example usage of the ab_framework package.

This script demonstrates a complete A/B test analysis workflow using the framework.
"""

import os
import sys
import pandas as pd

"""Quick-start demo: basic A/B test workflow."""

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ab_framework import ABTest, QualityChecker

def main():
    print("=" * 70)
    print("AB FRAMEWORK - EXAMPLE USAGE")
    print("=" * 70)
    
    # =========================================================================
    # STEP 1: Pre-experiment - Calculate required sample size
    # =========================================================================
    print("\n### STEP 1: Sample Size Calculation ###\n")
    
    sample_size = ABTest(
        name="planning_only",
        data=pd.DataFrame({"user_id": [1, 2], "variant": ["A", "B"]}),
    ).backend.sample_size_proportion(
        baseline_rate=0.10,  # Current 10% conversion rate
        mde=0.05,            # Want to detect 5% relative improvement
        power=0.80,          # 80% power
        alpha=0.05           # 5% significance level
    )
    
    print(f"Planning an experiment to improve conversion from 10% to 10.5%")
    print(f"Required sample size: {sample_size['total_size']:,} users")
    print(f"  - Control: {sample_size['control_size']:,}")
    print(f"  - Treatment: {sample_size['treatment_size']:,}")
    
    # =========================================================================
    # STEP 2: Run experiment and load data
    # =========================================================================
    print("\n### STEP 2: Load Experiment Data ###\n")
    
    # Using verification scenario 1 data as example
    df = pd.read_csv('data/scenario1_conversion.csv')
    print(f"Loaded {len(df):,} observations")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst few rows:")
    print(df.head())
    
    # =========================================================================
    # STEP 3: Create ABTest instance
    # =========================================================================
    print("\n### STEP 3: Create AB Test ###\n")
    
    test = ABTest(
        name="homepage_redesign",
        data=df,
        variant_col="variant",
        unit_id="user_id"
    )
    print(f"Test created: {test.name}")
    print(f"Variants found: {sorted(df['variant'].unique())}")
    print(f"Total users: {df['user_id'].nunique():,}")
    
    # =========================================================================
    # STEP 4: Define metrics
    # =========================================================================
    print("\n### STEP 4: Define Metrics ###\n")
    
    @test.metric(metric_type="proportion", is_primary=True, monitor_alpha=0.05, monitor_power=0.80)
    def conversion_rate(data):
        """User-level conversion rate (% of users who converted)."""
        return data.groupby('user_id')['converted'].max()
    
    print("Registered metric: conversion_rate")
    print("  Description: % of users who converted")
    
    # =========================================================================
    # STEP 5: Run analysis
    # =========================================================================
    print("\n### STEP 5: Analyze Experiment ###\n")
    
    results = test.analyze(
        run_srm_check=True,
        correction=None
    )
    
    # =========================================================================
    # STEP 6: Review results
    # =========================================================================
    print("\n### STEP 6: Results ###\n")
    print(results.summary())
    
    # =========================================================================
    # STEP 7: Statistical Conclusion
    # =========================================================================
    print("\n### STEP 7: Statistical Conclusion ###\n")
    
    # Generate plain-English conclusion
    print(results.conclusion('conversion_rate'))
    print("\nSOFT MONITORING DECISION:")
    print(results.decision_soft_monitoring())
    
    # =========================================================================
    # STEP 8: Export results
    # =========================================================================
    print("\n### STEP 8: Export Results ###\n")
    
    # As DataFrame
    df_results = results.to_dataframe()
    print("Results as DataFrame:")
    print(df_results)
    
    # As dictionary (e.g., for JSON API)
    dict_results = results.to_dict()
    print(f"\nResults as dict (keys): {list(dict_results.keys())}")
    
    # =========================================================================
    # BONUS: Multi-metric example
    # =========================================================================
    print("\n" + "=" * 70)
    print("BONUS: Multi-Metric Analysis with Correction")
    print("=" * 70 + "\n")
    
    # Load multi-metric data
    df_multi = pd.read_csv('data/scenario4_multi.csv')
    
    test_multi = ABTest(
        name="checkout_optimization",
        data=df_multi,
        variant_col="variant",
        unit_id="user_id"
    )
    
    @test_multi.metric(metric_type="proportion")
    def conversion_rate(data):
        return data.groupby('user_id')['converted_this_session'].max()
    
    @test_multi.metric(metric_type="mean")
    def revenue_per_user(data):
        return data.groupby('user_id')['order_value'].sum()
    
    @test_multi.metric(metric_type="mean")
    def avg_order_value(data):
        converters = data[data['converted_this_session'] == 1]
        if len(converters) == 0:
            return pd.Series(dtype=float)
        return converters.groupby('user_id')['order_value'].mean()
    
    results_multi = test_multi.analyze(
        metrics=['conversion_rate', 'revenue_per_user', 'avg_order_value'],
        correction='bonferroni'  # Adjust for multiple testing
    )
    
    print(results_multi.summary())
    
    # Print conclusions for each metric
    print("\n" + "=" * 70)
    print("STATISTICAL CONCLUSIONS FOR EACH METRIC")
    print("=" * 70)
    
    for metric in ['conversion_rate', 'revenue_per_user', 'avg_order_value']:
        print("\n" + results_multi.conclusion(metric))
    
    # =========================================================================
    # BONUS: Manual SRM check
    # =========================================================================
    print("\n" + "=" * 70)
    print("BONUS: Manual SRM Check")
    print("=" * 70 + "\n")
    
    checker = QualityChecker()
    
    # Good split
    srm_good = checker.check_srm({'A': 1000, 'B': 1005})
    print("Good split (1000 vs 1005):")
    print(srm_good['recommendation'])
    print(f"P-value: {srm_good['p_value']:.6f}\n")
    
    # Bad split
    srm_bad = checker.check_srm({'A': 10523, 'B': 9477})
    print("Bad split (10523 vs 9477):")
    print(srm_bad['recommendation'])
    print(f"P-value: {srm_bad['p_value']:.6f}")
    
    print("\n" + "=" * 70)
    print("EXAMPLE COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
