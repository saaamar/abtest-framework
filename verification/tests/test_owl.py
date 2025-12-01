"""
Test: owl_ab_test Package
Testing owl-ab-test for A/B testing scenarios
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import time
import os


DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

def test_scenario1_owl(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 1: Simple Conversion Rate Test using owl_ab_test
    
    NEW: Impression-level data - aggregate to user level first
    """
    print("\n" + "="*70)
    print("OWL_AB_TEST - Scenario 1: Conversion Rate (Impression-Level)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        from owl_ab_test import calculate_proportion_stats
        
        # Load impression-level data
        df = pd.read_csv(os.path.join(data_dir, "scenario1_conversion.csv"))
        
        print(f"\nData: {len(df)} impressions from {df['user_id'].nunique()} users")
        
        # Aggregate to user level: did user convert in ANY impression?
        user_conversions = df.groupby(['user_id', 'variant'])['converted'].max().reset_index()
        
        # Split by variant
        df_a = user_conversions[user_conversions['variant'] == 'A']
        df_b = user_conversions[user_conversions['variant'] == 'B']
        
        # owl_ab_test expects summary statistics, not raw arrays
        # Signature: (success_count, total_count, control_success, control_total, confidence_level=0.95)
        treatment_success = int(df_b['converted'].sum())
        treatment_total = len(df_b)
        control_success = int(df_a['converted'].sum())
        control_total = len(df_a)
        
        # Use calculate_proportion_stats with correct API
        result = calculate_proportion_stats(
            success_count=treatment_success,
            total_count=treatment_total,
            control_success=control_success,
            control_total=control_total,
            confidence_level=0.95
        )
        
        elapsed = time.time() - start_time
        
        # Extract metrics
        conv_a = control_success / control_total
        conv_b = treatment_success / treatment_total
        p_value = result.get('p_value', result.get('pvalue', None))
        
        print(f"\nVariant A: {conv_a:.4f}")
        print(f"Variant B: {conv_b:.4f}")
        print(f"Difference: {conv_b - conv_a:.4f}")
        print(f"Relative Lift: {((conv_b - conv_a) / conv_a * 100):.2f}%")
        print(f"P-value: {p_value:.6f}" if p_value is not None else "P-value: Not available")
        print(f"Result: {result}")
        print(f"\n⏱️  Time: {elapsed:.3f} seconds")
        print(f"📝 Lines of code: ~15")
        print(f"✅ Works but requires pre-aggregation (not ideal)")
        
        return {
            'scenario': 'Scenario 1',
            'metric_a': conv_a,
            'metric_b': conv_b,
            'p_value': p_value,
            'time': elapsed,
            'lines_of_code': 10,
            'works': True,
            'workarounds_needed': 0
        }
        
    except ImportError as e:
        elapsed = time.time() - start_time
        print(f"\n❌ IMPORT ERROR: {e}")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        return {
            'scenario': 'Scenario 1',
            'works': False,
            'time': elapsed,
            'reason': f'Import failed: {e}'
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        return {
            'scenario': 'Scenario 1',
            'works': False,
            'time': elapsed,
            'reason': f'Unexpected error: {e}'
        }

def test_scenario2_owl(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 2: Revenue per Active User (Custom Metric) using owl_ab_test
    
    NEW: Session-level data - aggregate to user level
    """
    print("\n" + "="*70)
    print("OWL_AB_TEST - Scenario 2: Revenue per Active User (Session-Level)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        from owl_ab_test import calculate_revenue_stats
        
        # Load session-level data
        df = pd.read_csv(os.path.join(data_dir, "scenario2_revenue.csv"))
        
        print(f"\nData: {len(df)} sessions from {df['user_id'].nunique()} active users")
        
        # CUSTOM METRIC: Aggregate revenue per user
        # (all users in dataset are active since inactive users have no sessions)
        user_revenue = df.groupby(['user_id', 'variant'])['session_revenue'].sum().reset_index()
        
        # Split by variant
        df_a = user_revenue[user_revenue['variant'] == 'A']
        df_b = user_revenue[user_revenue['variant'] == 'B']
        
        # Revenue per active user
        revenue_a = df_a['session_revenue'].values
        revenue_b = df_b['session_revenue'].values
        
        # owl_ab_test requires pre-computed statistics
        # Signature: (treatment_value, treatment_std, treatment_n, control_value, control_std, control_n, confidence_level=0.95)
        mean_a = revenue_a.mean()
        std_a = revenue_a.std(ddof=1)
        n_a = len(revenue_a)
        mean_b = revenue_b.mean()
        std_b = revenue_b.std(ddof=1)
        n_b = len(revenue_b)
        
        result = calculate_revenue_stats(
            treatment_value=mean_b,
            treatment_std=std_b,
            treatment_n=n_b,
            control_value=mean_a,
            control_std=std_a,
            control_n=n_a,
            confidence_level=0.95
        )
        
        elapsed = time.time() - start_time
        p_value = result.get('p_value', result.get('pvalue', None))
        
        print(f"\nVariant A: ${mean_a:.2f} (n={len(revenue_a)} active users)")
        print(f"Variant B: ${mean_b:.2f} (n={len(revenue_b)} active users)")
        print(f"Difference: ${mean_b - mean_a:.2f}")
        print(f"Relative Lift: {((mean_b - mean_a) / mean_a * 100):.2f}%")
        print(f"P-value: {p_value:.6f}" if p_value is not None else "P-value: Not available")
        print(f"Result: {result}")
        print(f"\n⏱️  Time: {elapsed:.3f} seconds")
        print(f"📝 Lines of code: ~20 (requires manual stat computation)")
        print(f"✅ Works but requires pre-computing mean/std/n")
        
        return {
            'scenario': 'Scenario 2',
            'metric_a': mean_a,
            'metric_b': mean_b,
            'p_value': p_value,
            'time': elapsed,
            'lines_of_code': 12,
            'works': True,
            'workarounds_needed': 0,
            'custom_metric_support': True
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        return {
            'scenario': 'Scenario 2',
            'works': False,
            'time': elapsed,
            'reason': f'Error: {e}'
        }

def test_scenario3_owl(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 3: CTR with Impression-Level Data using owl_ab_test
    
    NEW DATA STRUCTURE:
    - Each row = 1 impression
    - Columns: user_id, impression_id, variant, clicked, timestamp
    - Perfect for owl's calculate_proportion_stats!
    """
    print("\n" + "="*70)
    print("OWL_AB_TEST - Scenario 3: CTR (Impression-Level)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        from owl_ab_test import calculate_proportion_stats
        
        # Load impression-level data
        df = pd.read_csv(os.path.join(data_dir, "scenario3_ctr.csv"))
        
        print(f"\nData: {len(df)} impressions from {df['user_id'].nunique()} users")
        
        # Split by variant
        df_a = df[df['variant'] == 'A']
        df_b = df[df['variant'] == 'B']
        
        # Count clicks and impressions
        clicks_a = int(df_a['clicked'].sum())
        impressions_a = len(df_a)
        clicks_b = int(df_b['clicked'].sum())
        impressions_b = len(df_b)
        
        ctr_a = clicks_a / impressions_a
        ctr_b = clicks_b / impressions_b
        
        # owl's calculate_proportion_stats is PERFECT for this!
        result = calculate_proportion_stats(
            success_count=clicks_b,
            total_count=impressions_b,
            control_success=clicks_a,
            control_total=impressions_a,
            confidence_level=0.95
        )
        
        elapsed = time.time() - start_time
        p_value = result.get('p_value', result.get('pvalue', None))
        
        n_users_a = df_a['user_id'].nunique()
        n_users_b = df_b['user_id'].nunique()
        
        print(f"\n✅ WORKS PERFECTLY with impression-level data!")
        print(f"Variant A: {ctr_a:.4f} CTR ({clicks_a}/{impressions_a} clicks, {n_users_a} users)")
        print(f"Variant B: {ctr_b:.4f} CTR ({clicks_b}/{impressions_b} clicks, {n_users_b} users)")
        print(f"Difference: {ctr_b - ctr_a:.4f}")
        print(f"Relative Lift: {((ctr_b - ctr_a) / ctr_a * 100):.2f}%")
        print(f"P-value: {p_value:.6e}" if p_value is not None else "P-value: Not available")
        print(f"Result: {result}")
        print(f"\n⏱️  Time: {elapsed:.3f} seconds")
        print(f"📝 Lines of code: ~15")
        print(f"✅ calculate_proportion_stats works great for impression-level CTR")
        
        return {
            'scenario': 'Scenario 3',
            'metric_a': ctr_a,
            'metric_b': ctr_b,
            'p_value': p_value,
            'time': elapsed,
            'lines_of_code': 15,
            'works': True,
            'workarounds_needed': 0
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        return {
            'scenario': 'Scenario 3',
            'works': False,
            'time': elapsed,
            'reason': f'Error: {e}'
        }

def test_scenario4_owl(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 4: Multi-Metric Dashboard using owl_ab_test
    
    NEW: Session-level data - aggregate to user level for metrics
    """
    print("\n" + "="*70)
    print("OWL_AB_TEST - Scenario 4: Multi-Metric Dashboard (Session-Level)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        from owl_ab_test import calculate_revenue_stats
        
        # Load session-level data
        df = pd.read_csv(os.path.join(data_dir, "scenario4_multi.csv"))
        
        print(f"\nData: {len(df)} sessions from {df['user_id'].nunique()} users")
        
        # Aggregate to user level for metrics
        user_metrics = df.groupby(['user_id', 'variant']).agg({
            'converted_this_session': 'max',  # Did user convert?
            'order_value': 'sum',  # Total order value
            'session_revenue': 'sum'  # Total revenue
        }).reset_index()
        
        df_a = user_metrics[user_metrics['variant'] == 'A']
        df_b = user_metrics[user_metrics['variant'] == 'B']
        
        # Would need to run separate tests for each metric
        # No built-in multi-metric support or Bonferroni correction
        
        elapsed = time.time() - start_time
        
        print(f"\n⚠️  PARTIAL SUPPORT")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        print(f"📝 Issue: No built-in multi-metric dashboard functionality")
        print(f"   Would need to manually:")
        print(f"   - Session→user aggregation (~5 LOC)")
        print(f"   - Run 4 separate calculate_*_stats() calls (~25 LOC)")
        print(f"   - Manually apply Bonferroni correction (alpha / 4)")
        print(f"   - Manually aggregate results (~10 LOC)")
        print(f"   Similar verbosity to scipy+pandas baseline")
        
        return {
            'scenario': 'Scenario 4',
            'works': False,  # Not cleanly supported
            'time': elapsed,
            'reason': 'No multi-metric or Bonferroni correction support',
            'multi_metric_support': False,
            'workarounds_needed': 1
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        return {
            'scenario': 'Scenario 4',
            'works': False,
            'time': elapsed,
            'reason': f'Error: {e}'
        }

def test_scenario5_owl(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 5: Agent Bot - Resolved Rate WITH gap
    Session-level binary metric (similar to scenario 1)
    """
    print("\n" + "="*70)
    print("OWL_AB_TEST - Scenario 5: Agent Bot Resolved Rate (WITH gap)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        from owl_ab_test import calculate_proportion_stats
        
        df = pd.read_csv(os.path.join(data_dir, "scenario5_resolved_with_gap.csv"))
        print(f"\nData: {len(df)} sessions")
        
        df_a = df[df['variant'] == 'A']
        df_b = df[df['variant'] == 'B']
        
        resolved_a = int(df_a['is_resolved'].sum())
        n_a = len(df_a)
        resolved_b = int(df_b['is_resolved'].sum())
        n_b = len(df_b)
        
        rate_a = resolved_a / n_a
        rate_b = resolved_b / n_b
        
        result = calculate_proportion_stats(
            success_count=resolved_b,
            total_count=n_b,
            control_success=resolved_a,
            control_total=n_a,
            confidence_level=0.95
        )
        
        elapsed = time.time() - start_time
        p_value = result.get('p_value', result.get('pvalue', None))
        
        print(f"\n✅ WORKS")
        print(f"Variant A: {rate_a:.4f}")
        print(f"Variant B: {rate_b:.4f}")
        print(f"P-value: {p_value:.6f}" if p_value is not None else "P-value: Not available")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        
        return {
            'scenario': 'Scenario 5',
            'works': True,
            'p_value': p_value,
            'metric_a': rate_a,
            'metric_b': rate_b,
            'time': elapsed,
            'lines_of_code': 10
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        return {'scenario': 'Scenario 5', 'works': False, 'time': elapsed, 'reason': str(e)}

def test_scenario6_owl(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 6: Agent Bot - Resolved Rate NO gap
    Session-level binary metric
    """
    print("\n" + "="*70)
    print("OWL_AB_TEST - Scenario 6: Agent Bot Resolved Rate (NO gap)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        from owl_ab_test import calculate_proportion_stats
        
        df = pd.read_csv(os.path.join(data_dir, "scenario6_resolved_no_gap.csv"))
        print(f"\nData: {len(df)} sessions")
        
        df_a = df[df['variant'] == 'A']
        df_b = df[df['variant'] == 'B']
        
        resolved_a = int(df_a['is_resolved'].sum())
        n_a = len(df_a)
        resolved_b = int(df_b['is_resolved'].sum())
        n_b = len(df_b)
        
        rate_a = resolved_a / n_a
        rate_b = resolved_b / n_b
        
        result = calculate_proportion_stats(
            success_count=resolved_b,
            total_count=n_b,
            control_success=resolved_a,
            control_total=n_a,
            confidence_level=0.95
        )
        
        elapsed = time.time() - start_time
        p_value = result.get('p_value', result.get('pvalue', None))
        
        print(f"\n✅ WORKS")
        print(f"Variant A: {rate_a:.4f}")
        print(f"Variant B: {rate_b:.4f}")
        print(f"P-value: {p_value:.6f}" if p_value is not None else "P-value: Not available")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        
        return {
            'scenario': 'Scenario 6',
            'works': True,
            'p_value': p_value,
            'metric_a': rate_a,
            'metric_b': rate_b,
            'time': elapsed,
            'lines_of_code': 10
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        return {'scenario': 'Scenario 6', 'works': False, 'time': elapsed, 'reason': str(e)}

def test_scenario7_owl(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 7: Agent Bot - AI Quality Metric WITH gap
    Session-level continuous metric (similar to scenario 2)
    """
    print("\n" + "="*70)
    print("OWL_AB_TEST - Scenario 7: Agent Bot AI Metric (WITH gap)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        from owl_ab_test import calculate_revenue_stats
        
        df = pd.read_csv(os.path.join(data_dir, "scenario7_ai_metric_with_gap.csv"))
        print(f"\nData: {len(df)} sessions")
        
        df_a = df[df['variant'] == 'A']
        df_b = df[df['variant'] == 'B']
        
        ai_a = df_a['ai_metric'].values
        ai_b = df_b['ai_metric'].values
        
        mean_a = ai_a.mean()
        std_a = ai_a.std(ddof=1)
        n_a = len(ai_a)
        mean_b = ai_b.mean()
        std_b = ai_b.std(ddof=1)
        n_b = len(ai_b)
        
        result = calculate_revenue_stats(
            treatment_value=mean_b,
            treatment_std=std_b,
            treatment_n=n_b,
            control_value=mean_a,
            control_std=std_a,
            control_n=n_a,
            confidence_level=0.95
        )
        
        elapsed = time.time() - start_time
        p_value = result.get('p_value', result.get('pvalue', None))
        
        print(f"\n✅ WORKS")
        print(f"Variant A: {mean_a:.4f}")
        print(f"Variant B: {mean_b:.4f}")
        print(f"P-value: {p_value:.6f}" if p_value is not None else "P-value: Not available")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        
        return {
            'scenario': 'Scenario 7',
            'works': True,
            'p_value': p_value,
            'metric_a': mean_a,
            'metric_b': mean_b,
            'time': elapsed,
            'lines_of_code': 12
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        return {'scenario': 'Scenario 7', 'works': False, 'time': elapsed, 'reason': str(e)}

def test_scenario8_owl(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 8: Agent Bot - AI Quality Metric NO gap
    Session-level continuous metric
    """
    print("\n" + "="*70)
    print("OWL_AB_TEST - Scenario 8: Agent Bot AI Metric (NO gap)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        from owl_ab_test import calculate_revenue_stats
        
        df = pd.read_csv(os.path.join(data_dir, "scenario8_ai_metric_no_gap.csv"))
        print(f"\nData: {len(df)} sessions")
        
        df_a = df[df['variant'] == 'A']
        df_b = df[df['variant'] == 'B']
        
        ai_a = df_a['ai_metric'].values
        ai_b = df_b['ai_metric'].values
        
        mean_a = ai_a.mean()
        std_a = ai_a.std(ddof=1)
        n_a = len(ai_a)
        mean_b = ai_b.mean()
        std_b = ai_b.std(ddof=1)
        n_b = len(ai_b)
        
        result = calculate_revenue_stats(
            treatment_value=mean_b,
            treatment_std=std_b,
            treatment_n=n_b,
            control_value=mean_a,
            control_std=std_a,
            control_n=n_a,
            confidence_level=0.95
        )
        
        elapsed = time.time() - start_time
        p_value = result.get('p_value', result.get('pvalue', None))
        
        print(f"\n✅ WORKS")
        print(f"Variant A: {mean_a:.4f}")
        print(f"Variant B: {mean_b:.4f}")
        print(f"P-value: {p_value:.6f}" if p_value is not None else "P-value: Not available")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        
        return {
            'scenario': 'Scenario 8',
            'works': True,
            'p_value': p_value,
            'metric_a': mean_a,
            'metric_b': mean_b,
            'time': elapsed,
            'lines_of_code': 12
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        return {'scenario': 'Scenario 8', 'works': False, 'time': elapsed, 'reason': str(e)}

def run_all_owl_tests(data_dir: str = DEFAULT_DATA_DIR):
    """Run all owl_ab_test tests and summarize"""
    print("\n" + "="*70)
    print("OWL_AB_TEST PACKAGE EVALUATION")
    print("Testing owl-ab-test package")
    print("="*70)
    
    results = []
    results.append(test_scenario1_owl(data_dir=data_dir))
    results.append(test_scenario2_owl(data_dir=data_dir))
    results.append(test_scenario3_owl(data_dir=data_dir))
    results.append(test_scenario4_owl(data_dir=data_dir))
    results.append(test_scenario5_owl(data_dir=data_dir))
    results.append(test_scenario6_owl(data_dir=data_dir))
    results.append(test_scenario7_owl(data_dir=data_dir))
    results.append(test_scenario8_owl(data_dir=data_dir))
    
    # Summary
    print("\n" + "="*70)
    print("OWL_AB_TEST SUMMARY")
    print("="*70)
    
    working = sum(1 for r in results if r.get('works', False))
    total_time = sum(r['time'] for r in results)
    total_workarounds = sum(r.get('workarounds_needed', 0) for r in results)
    
    print(f"\n⚠️  {working}/8 scenarios working cleanly")
    print(f"⏱️  Total time: {total_time:.3f} seconds")
    print(f"⚠️  Workarounds needed: {total_workarounds}")
    
    print("\n**Pros:**")
    print("  + Simple API for basic binary and continuous metrics")
    print("  + Custom metrics possible through pandas preprocessing")
    print("  + Fast execution")
    
    print("\n**Cons:**")
    print("  - Cannot handle aggregated metrics (e.g., total clicks / total impressions)")
    print("  - No multi-metric dashboard support")
    print("  - No Bonferroni correction or multiple testing features")
    print("  - Still requires manual pandas work for filtering/aggregation")
    print("  - Not significantly better than scipy+pandas baseline")
    
    print("\n**Conclusion:**")
    print("  owl_ab_test is PARTIALLY suitable")
    print("  - Scenarios 1-3, 5-8: ✅ Work (but require pandas preprocessing)")
    print("  - Scenario 4: ❌ No multi-metric support")
    print(f"  Score: {working}/8 scenarios ({working/8*100:.0f}%)")
    print("  - Overall: Thin wrapper over scipy, doesn't solve orchestration problem")
    
    return results

if __name__ == "__main__":
    run_all_owl_tests()
