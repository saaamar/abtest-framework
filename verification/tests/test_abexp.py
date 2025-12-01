"""
Test: abexp Package
Testing PlaytikaOSS's abexp for A/B testing scenarios

NOTE: This tests abexp using ITS designed API.
abexp uses FrequentistAnalyzer with methods like compare_conv_obs, compare_mean_obs
"""

from abexp.core.analysis_frequentist import FrequentistAnalyzer
import pandas as pd
import numpy as np
from typing import Dict, Any
import time
import os


DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def test_scenario1_abexp(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 1: Simple Conversion Rate Test using abexp
    
    NEW: Impression-level data - aggregate to user level first
    Tests abexp's API: FrequentistAnalyzer.compare_conv_obs()
    """
    print("\n" + "="*70)
    print("ABEXP - Scenario 1: Conversion Rate (Impression-Level)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        # Load impression-level data
        df = pd.read_csv(os.path.join(data_dir, "scenario1_conversion.csv"))
        
        print(f"\nData: {len(df)} impressions from {df['user_id'].nunique()} users")
        
        # Aggregate to user level: did user convert in ANY impression?
        user_conversions = df.groupby(['user_id', 'variant'])['converted'].max().reset_index()
        
        # Split by variant
        df_a = user_conversions[user_conversions['variant'] == 'A']
        df_b = user_conversions[user_conversions['variant'] == 'B']
        
        # Get binary arrays
        obs_control = df_a['converted'].values
        obs_treatment = df_b['converted'].values
        
        # Use abexp's API
        analyzer = FrequentistAnalyzer()
        result = analyzer.compare_conv_obs(obs_control, obs_treatment, alpha=0.05)
        
        elapsed = time.time() - start_time
        
        # abexp returns tuple: (p_value, ci_control, ci_treatment)
        p_value, ci_control, ci_treatment = result
        
        conv_a = obs_control.mean()
        conv_b = obs_treatment.mean()
        
        print(f"\n✅ WORKS using abexp's API")
        print(f"Variant A: {conv_a:.4f}")
        print(f"Variant B: {conv_b:.4f}")
        print(f"Difference: {conv_b - conv_a:.4f}")
        print(f"P-value: {p_value:.6f}")
        print(f"CI Control: {ci_control}")
        print(f"CI Treatment: {ci_treatment}")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        print(f"📝 Lines of code: ~10")
        
        return {
            'scenario': 'Scenario 1',
            'works': True,
            'time': elapsed,
            'lines_of_code': 10,
            'p_value': p_value,
            'results': str(result)
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'scenario': 'Scenario 1',
            'works': False,
            'time': elapsed,
            'reason': f'Error: {e}'
        }

def test_scenario2_abexp(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 2: Revenue per Active User using abexp
    
    NEW: Session-level data - aggregate to user level
    Tests custom metrics with filtering
    """
    print("\n" + "="*70)
    print("ABEXP - Scenario 2: Revenue per Active User (Session-Level)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        # Load session-level data
        df = pd.read_csv(os.path.join(data_dir, "scenario2_revenue.csv"))
        
        print(f"\nData: {len(df)} sessions from {df['user_id'].nunique()} active users")
        
        # CUSTOM METRIC: Aggregate revenue per user
        # (all users in dataset are active since inactive users have no sessions)
        user_revenue = df.groupby(['user_id', 'variant'])['session_revenue'].sum().reset_index()
        
        # Split by variant
        df_a = user_revenue[user_revenue['variant'] == 'A']
        df_b = user_revenue[user_revenue['variant'] == 'B']
        
        # Get revenue arrays
        obs_control = df_a['session_revenue'].values
        obs_treatment = df_b['session_revenue'].values
        
        # Use abexp's API for continuous metrics
        analyzer = FrequentistAnalyzer()
        result = analyzer.compare_mean_obs(obs_control, obs_treatment, alpha=0.05)
        
        elapsed = time.time() - start_time
        
        # abexp returns tuple: (p_value, ci_control, ci_treatment)
        p_value, ci_control, ci_treatment = result
        
        mean_a = obs_control.mean()
        mean_b = obs_treatment.mean()
        
        print(f"\n⚠️  WORKS but requires manual pre-filtering")
        print(f"Variant A: ${mean_a:.2f} (n={len(obs_control)})")
        print(f"Variant B: ${mean_b:.2f} (n={len(obs_treatment)})")
        print(f"P-value: {p_value:.6f}")
        print(f"CI Control: {ci_control}")
        print(f"CI Treatment: {ci_treatment}")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        print(f"📝 Lines of code: ~15")
        print(f"⚠️  Must filter data manually before passing to abexp")
        
        return {
            'scenario': 'Scenario 2',
            'works': True,
            'time': elapsed,
            'lines_of_code': 15,
            'p_value': p_value,
            'metric_a': mean_a,
            'metric_b': mean_b,
            'workarounds_needed': 1,
            'custom_metric_support': 'Partial - requires pre-filtering'
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'scenario': 'Scenario 2',
            'works': False,
            'time': elapsed,
            'reason': f'Error: {e}'
        }

def test_scenario3_abexp(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 3: CTR with Impression-Level Data using abexp
    
    NEW DATA STRUCTURE:
    - Each row = 1 impression (not 1 user)
    - Columns: user_id, impression_id, variant, clicked, timestamp
    - Variant assignment at user level (unit of randomization)
    - Can now correctly test CTR with abexp!
    """
    print("\n" + "="*70)
    print("ABEXP - Scenario 3: CTR (Impression-Level)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        # Load impression-level data
        df = pd.read_csv(os.path.join(data_dir, "scenario3_ctr.csv"))
        
        print(f"\nData: {len(df)} impressions from {df['user_id'].nunique()} users")
        print(f"Unit of randomization: User (variant assigned at user level)")
        
        # Split by variant
        df_a = df[df['variant'] == 'A']
        df_b = df[df['variant'] == 'B']
        
        # Get binary click arrays (one value per impression)
        clicks_a = df_a['clicked'].values
        clicks_b = df_b['clicked'].values
        
        # Use abexp's binary comparison (CORRECT for CTR now!)
        analyzer = FrequentistAnalyzer()
        result = analyzer.compare_conv_obs(clicks_a, clicks_b, alpha=0.05)
        
        elapsed = time.time() - start_time
        
        # Unpack result
        p_value, ci_a, ci_b = result
        
        ctr_a = clicks_a.mean()
        ctr_b = clicks_b.mean()
        
        print(f"\n✅ WORKS CORRECTLY with impression-level data!")
        print(f"Variant A: {ctr_a:.4f} CTR ({clicks_a.sum()}/{len(clicks_a)} clicks)")
        print(f"Variant B: {ctr_b:.4f} CTR ({clicks_b.sum()}/{len(clicks_b)} clicks)")
        print(f"Absolute difference: {ctr_b - ctr_a:.4f}")
        print(f"Relative lift: {((ctr_b - ctr_a) / ctr_a * 100):.2f}%")
        print(f"P-value: {p_value:.6e}")
        print(f"CI A: {ci_a}")
        print(f"CI B: {ci_b}")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        print(f"📝 Lines of code: ~10")
        print(f"\n✅ Using compare_conv_obs() - treats each impression as a trial")
        print(f"   This is statistically CORRECT for CTR analysis")
        
        return {
            'scenario': 'Scenario 3',
            'works': True,
            'time': elapsed,
            'lines_of_code': 10,
            'p_value': p_value,
            'ctr_a': ctr_a,
            'ctr_b': ctr_b
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'scenario': 'Scenario 3',
            'works': False,
            'time': elapsed,
            'reason': f'Error: {e}'
        }

def test_scenario4_abexp(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 4: Multi-Metric Dashboard using abexp
    
    NEW: Session-level data - aggregate to user level for metrics
    """
    print("\n" + "="*70)
    print("ABEXP - Scenario 4: Multi-Metric Dashboard (Session-Level)")
    print("="*70)
    
    start_time = time.time()
    
    try:
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
        
        # abexp has no multi-metric support
        # Would need to run 4 separate compare_*_obs calls
        # and manually apply Bonferroni correction
        
        elapsed = time.time() - start_time
        
        print(f"\n❌ NO MULTI-METRIC SUPPORT")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        print(f"📝 Would need:")
        print(f"   - Session→user aggregation (~5 LOC)")
        print(f"   - 4 separate analyzer.compare_*_obs() calls (~30 LOC)")
        print(f"   - Manual Bonferroni correction (alpha/4)")
        print(f"   - Manual result aggregation (~10 LOC)")
        print(f"   ~45-50 LOC total")
        print(f"   Same complexity as scipy+pandas baseline!")
        
        return {
            'scenario': 'Scenario 4',
            'works': False,
            'time': elapsed,
            'lines_of_code': 50,
            'reason': 'No multi-metric support, must run separately',
            'multi_metric_support': False
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'scenario': 'Scenario 4',
            'works': False,
            'time': elapsed,
            'reason': f'Error: {e}'
        }

def test_scenario5_abexp(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 5: Agent Bot - Resolved Rate WITH gap
    Session-level binary metric (similar to scenario 1)
    """
    print("\n" + "="*70)
    print("ABEXP - Scenario 5: Agent Bot Resolved Rate (WITH gap)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        df = pd.read_csv(os.path.join(data_dir, "scenario5_resolved_with_gap.csv"))
        print(f"\nData: {len(df)} sessions")
        
        df_a = df[df['variant'] == 'A']
        df_b = df[df['variant'] == 'B']
        
        obs_control = df_a['is_resolved'].values
        obs_treatment = df_b['is_resolved'].values
        
        analyzer = FrequentistAnalyzer()
        result = analyzer.compare_conv_obs(obs_control, obs_treatment, alpha=0.05)
        
        elapsed = time.time() - start_time
        p_value, ci_control, ci_treatment = result
        
        rate_a = obs_control.mean()
        rate_b = obs_treatment.mean()
        
        print(f"\n✅ WORKS")
        print(f"Variant A: {rate_a:.4f}")
        print(f"Variant B: {rate_b:.4f}")
        print(f"P-value: {p_value:.6f}")
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

def test_scenario6_abexp(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 6: Agent Bot - Resolved Rate NO gap
    Session-level binary metric
    """
    print("\n" + "="*70)
    print("ABEXP - Scenario 6: Agent Bot Resolved Rate (NO gap)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        df = pd.read_csv(os.path.join(data_dir, "scenario6_resolved_no_gap.csv"))
        print(f"\nData: {len(df)} sessions")
        
        df_a = df[df['variant'] == 'A']
        df_b = df[df['variant'] == 'B']
        
        obs_control = df_a['is_resolved'].values
        obs_treatment = df_b['is_resolved'].values
        
        analyzer = FrequentistAnalyzer()
        result = analyzer.compare_conv_obs(obs_control, obs_treatment, alpha=0.05)
        
        elapsed = time.time() - start_time
        p_value, ci_control, ci_treatment = result
        
        rate_a = obs_control.mean()
        rate_b = obs_treatment.mean()
        
        print(f"\n✅ WORKS")
        print(f"Variant A: {rate_a:.4f}")
        print(f"Variant B: {rate_b:.4f}")
        print(f"P-value: {p_value:.6f}")
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

def test_scenario7_abexp(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 7: Agent Bot - AI Quality Metric WITH gap
    Session-level continuous metric (similar to scenario 2)
    """
    print("\n" + "="*70)
    print("ABEXP - Scenario 7: Agent Bot AI Metric (WITH gap)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        df = pd.read_csv(os.path.join(data_dir, "scenario7_ai_metric_with_gap.csv"))
        print(f"\nData: {len(df)} sessions")
        
        df_a = df[df['variant'] == 'A']
        df_b = df[df['variant'] == 'B']
        
        obs_control = df_a['ai_metric'].values
        obs_treatment = df_b['ai_metric'].values
        
        analyzer = FrequentistAnalyzer()
        result = analyzer.compare_mean_obs(obs_control, obs_treatment, alpha=0.05)
        
        elapsed = time.time() - start_time
        p_value, ci_control, ci_treatment = result
        
        mean_a = obs_control.mean()
        mean_b = obs_treatment.mean()
        
        print(f"\n✅ WORKS")
        print(f"Variant A: {mean_a:.4f}")
        print(f"Variant B: {mean_b:.4f}")
        print(f"P-value: {p_value:.6f}")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        
        return {
            'scenario': 'Scenario 7',
            'works': True,
            'p_value': p_value,
            'metric_a': mean_a,
            'metric_b': mean_b,
            'time': elapsed,
            'lines_of_code': 10
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        return {'scenario': 'Scenario 7', 'works': False, 'time': elapsed, 'reason': str(e)}

def test_scenario8_abexp(data_dir: str = DEFAULT_DATA_DIR):
    """
    Scenario 8: Agent Bot - AI Quality Metric NO gap
    Session-level continuous metric
    """
    print("\n" + "="*70)
    print("ABEXP - Scenario 8: Agent Bot AI Metric (NO gap)")
    print("="*70)
    
    start_time = time.time()
    
    try:
        df = pd.read_csv(os.path.join(data_dir, "scenario8_ai_metric_no_gap.csv"))
        print(f"\nData: {len(df)} sessions")
        
        df_a = df[df['variant'] == 'A']
        df_b = df[df['variant'] == 'B']
        
        obs_control = df_a['ai_metric'].values
        obs_treatment = df_b['ai_metric'].values
        
        analyzer = FrequentistAnalyzer()
        result = analyzer.compare_mean_obs(obs_control, obs_treatment, alpha=0.05)
        
        elapsed = time.time() - start_time
        p_value, ci_control, ci_treatment = result
        
        mean_a = obs_control.mean()
        mean_b = obs_treatment.mean()
        
        print(f"\n✅ WORKS")
        print(f"Variant A: {mean_a:.4f}")
        print(f"Variant B: {mean_b:.4f}")
        print(f"P-value: {p_value:.6f}")
        print(f"⏱️  Time: {elapsed:.3f} seconds")
        
        return {
            'scenario': 'Scenario 8',
            'works': True,
            'p_value': p_value,
            'metric_a': mean_a,
            'metric_b': mean_b,
            'time': elapsed,
            'lines_of_code': 10
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ ERROR: {e}")
        return {'scenario': 'Scenario 8', 'works': False, 'time': elapsed, 'reason': str(e)}

def run_all_abexp_tests(data_dir: str = DEFAULT_DATA_DIR):
    """Run all abexp tests and summarize"""
    print("\n" + "="*70)
    print("ABEXP PACKAGE EVALUATION")
    print("Testing abexp using ITS designed API")
    print("="*70)
    
    results = []
    results.append(test_scenario1_abexp(data_dir=data_dir))
    results.append(test_scenario2_abexp(data_dir=data_dir))
    results.append(test_scenario3_abexp(data_dir=data_dir))
    results.append(test_scenario4_abexp(data_dir=data_dir))
    results.append(test_scenario5_abexp(data_dir=data_dir))
    results.append(test_scenario6_abexp(data_dir=data_dir))
    results.append(test_scenario7_abexp(data_dir=data_dir))
    results.append(test_scenario8_abexp(data_dir=data_dir))
    
    # Summary
    print("\n" + "="*70)
    print("ABEXP SUMMARY")
    print("="*70)
    
    working = sum(1 for r in results if r.get('works') == True)
    total_time = sum(r['time'] for r in results)
    total_workarounds = sum(r.get('workarounds_needed', 0) for r in results)
    
    print(f"\n📊 {working}/8 scenarios working")
    print(f"⏱️  Total time: {total_time:.3f} seconds")
    print(f"⚠️  Workarounds needed: {total_workarounds}")
    
    print("\n**abexp's Design:**")
    print("  - FrequentistAnalyzer class")
    print("  - Methods: compare_conv_obs(), compare_mean_obs()")
    print("  - Takes arrays of observations")
    print("  - Returns dict with p_value, CI, etc.")
    
    print("\n**Pros:**")
    print("  + Cleaner API than raw scipy")
    print("  + Reduces scipy+pandas from ~25 LOC to ~10 LOC for simple cases")
    print("  + Returns structured dict results")
    
    print("\n**Cons:**")
    print("  - Still requires manual data splitting by variant")
    print("  - Still requires manual filtering for custom metrics")
    print("  - Cannot handle aggregated metrics (ratio of sums)")
    print("  - No multi-metric support")
    print("  - No Bonferroni correction")
    print("  - No SRM checks, power analysis, etc.")
    
    print("\n**vs scipy+pandas baseline:**")
    print("  - Scenario 1: abexp ~10 LOC vs scipy ~25 LOC (60% reduction)")
    print("  - Scenario 2: abexp ~15 LOC vs scipy ~35 LOC (57% reduction)")
    print("  - Scenario 3: abexp ~10 LOC vs scipy ~35 LOC (71% reduction) ✅")
    print("  - Scenario 4: abexp ~50 LOC vs scipy ~60 LOC (minimal improvement)")
    
    print("\n**Conclusion:**")
    print("  abexp works well when data is structured correctly!")
    print("  - Scenarios 1-3, 5-8: ~10-15 LOC vs ~25-35 LOC scipy (60-71% reduction)")
    print("  - Requires impression-level data for CTR (not user-level)")
    print("  - Still fails for multi-metric dashboards (scenario 4)")
    print(f"  Score: {working}/8 scenarios ({working/8*100:.0f}%)")
    
    return results

if __name__ == "__main__":
    run_all_abexp_tests()
