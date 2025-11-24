"""Test ab_framework against verification scenarios."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import pandas as pd
import numpy as np
from ab_framework import ABTest, SampleSizeCalculator, QualityChecker

def test_scenario1_conversion():
    """Test Scenario 1: Simple Conversion Rate."""
    print("\n=== Testing Scenario 1: Conversion Rate ===")
    
    # Load data
    df = pd.read_csv('verification/data/scenario1_conversion.csv')
    print(f"Loaded {len(df)} rows")
    
    # Create test
    test = ABTest(
        name="scenario1_conversion",
        data=df,
        variant_col="variant",
        unit_id="user_id"
    )
    
    # Register metric
    @test.metric
    def conversion_rate(data):
        return data.groupby('user_id')['converted'].max()
    
    # Analyze
    results = test.analyze(['conversion_rate'])
    
    # Print results
    print(results.summary())
    
    # Validate
    result = results.metric_results['conversion_rate']
    print(f"\nValidation:")
    print(f"P-value: {result['p_value']:.6f}")
    print(f"Expected: ~0.383397")
    print(f"Match: {abs(result['p_value'] - 0.383397) < 0.01}")
    
    return results

def test_scenario2_revenue():
    """Test Scenario 2: Revenue per Active User."""
    print("\n=== Testing Scenario 2: Revenue per Active User ===")
    
    # Load data
    df = pd.read_csv('verification/data/scenario2_revenue.csv')
    print(f"Loaded {len(df)} rows")
    
    # Create test
    test = ABTest(
        name="scenario2_revenue",
        data=df,
        variant_col="variant",
        unit_id="user_id"
    )
    
    # Register metric with filtering
    @test.metric
    def revenue_per_active_user(data):
        """Revenue per user, filtered to active users (revenue > 0)."""
        # Aggregate to user level
        user_revenue = data.groupby('user_id')['session_revenue'].sum()
        
        # Filter to active users (revenue > 0)
        active = user_revenue[user_revenue > 0]
        
        return active
    
    # Analyze
    results = test.analyze(['revenue_per_active_user'])
    
    # Print results
    print(results.summary())
    
    # Validate
    result = results.metric_results['revenue_per_active_user']
    if 'error' in result:
        print(f"\nError: {result['error']}")
        return results
    
    print(f"\nValidation:")
    print(f"P-value: {result['p_value']:.6f}")
    print(f"Expected: ~0.000021")
    print(f"Match: {abs(result['p_value'] - 0.000021) < 0.01}")
    
    return results

def test_scenario3_ctr():
    """Test Scenario 3: Click-Through Rate."""
    print("\n=== Testing Scenario 3: CTR with Exposure ===")
    
    # Load data
    df = pd.read_csv('verification/data/scenario3_ctr.csv')
    print(f"Loaded {len(df)} rows")
    
    # Create test - NOTE: unit_id is 'impression_id' for this scenario!
    test = ABTest(
        name="scenario3_ctr",
        data=df,
        variant_col="variant",
        unit_id="impression_id"  # Event-level!
    )
    
    # Register metric
    @test.metric
    def click_through_rate(data):
        """CTR at impression level."""
        return data.set_index('impression_id')['clicked']
    
    # Analyze
    results = test.analyze(['click_through_rate'])
    
    # Print results
    print(results.summary())
    
    # Validate
    result = results.metric_results['click_through_rate']
    print(f"\nValidation:")
    print(f"P-value: {result['p_value']:.6f}")
    print(f"Expected: <0.000001")
    print(f"Match: {result['p_value'] < 0.00001}")
    
    return results

def test_multi_metric():
    """Test multi-metric with Bonferroni correction."""
    print("\n=== Testing Multi-Metric with Bonferroni ===")
    
    # Load data
    df = pd.read_csv('verification/data/scenario4_multi.csv')
    print(f"Loaded {len(df)} rows")
    
    # Create test
    test = ABTest(
        name="multi_metric_test",
        data=df,
        variant_col="variant",
        unit_id="user_id"
    )
    
    # Register multiple metrics
    @test.metric
    def conversion_rate(data):
        """User-level conversion (converted in any session)."""
        return data.groupby('user_id')['converted_this_session'].max()
    
    @test.metric
    def avg_order_value(data):
        """AOV among converters only."""
        converters = data[data['converted_this_session'] == 1]
        if len(converters) == 0:
            return pd.Series(dtype=float)
        return converters.groupby('user_id')['order_value'].mean()
    
    @test.metric
    def revenue_per_user(data):
        """Total revenue per user."""
        return data.groupby('user_id')['order_value'].sum()
    
    # Analyze with Bonferroni correction
    results = test.analyze(
        metrics=['conversion_rate', 'avg_order_value', 'revenue_per_user'],
        correction='bonferroni'
    )
    
    # Print results
    print(results.summary())
    
    # Check correction
    print(f"\nBonferroni Correction:")
    print(f"Original α: 0.05")
    print(f"Adjusted α: {0.05/3:.4f}")
    for metric, result in results.metric_results.items():
        if 'adjusted_alpha' in result:
            print(f"{metric}: adjusted_alpha = {result['adjusted_alpha']:.4f}")
    
    return results

def test_sample_size_calculator():
    """Test sample size calculator."""
    print("\n=== Testing Sample Size Calculator ===")
    
    calc = SampleSizeCalculator()
    
    # Test for conversion rate
    result = calc.for_proportion(
        baseline_rate=0.10,  # 10% conversion
        mde=0.05,            # 5% relative lift
        power=0.80
    )
    
    print(f"\nConversion Rate Test:")
    print(f"Baseline: {result['assumptions']['baseline_rate']:.1%}")
    print(f"Target: {result['assumptions']['treatment_rate']:.1%}")
    print(f"MDE: {result['assumptions']['mde_relative']:.1%}")
    print(f"Required sample size: {result['total_size']:,} total")
    print(f"  Control: {result['control_size']:,}")
    print(f"  Treatment: {result['treatment_size']:,}")
    
    # Test for revenue
    result = calc.for_mean(
        baseline_mean=50.0,
        baseline_std=25.0,
        mde=0.10,
        power=0.80
    )
    
    print(f"\nRevenue Test:")
    print(f"Baseline: ${result['assumptions']['baseline_mean']:.2f}")
    print(f"Target: ${result['assumptions']['treatment_mean']:.2f}")
    print(f"MDE: {result['assumptions']['mde_relative']:.1%}")
    print(f"Required sample size: {result['total_size']:,} total")

def test_srm_check():
    """Test SRM checker."""
    print("\n=== Testing SRM Check ===")
    
    checker = QualityChecker()
    
    # Test with good split
    result = checker.check_srm({'A': 1000, 'B': 1005})
    print(f"\nGood split (1000 vs 1005):")
    print(result['recommendation'])
    print(f"P-value: {result['p_value']:.6f}")
    
    # Test with bad split
    result = checker.check_srm({'A': 10523, 'B': 9477})
    print(f"\nBad split (10523 vs 9477):")
    print(result['recommendation'])
    print(f"P-value: {result['p_value']:.6f}")

if __name__ == '__main__':
    print("=" * 70)
    print("AB FRAMEWORK VERIFICATION TESTS")
    print("=" * 70)
    
    # Run all tests
    test_scenario1_conversion()
    test_scenario2_revenue()
    test_scenario3_ctr()
    test_multi_metric()
    test_sample_size_calculator()
    test_srm_check()
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)
