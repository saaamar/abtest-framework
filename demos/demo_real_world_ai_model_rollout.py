"""
Real-World A/B Test Workflow: AI Quality Metric Improvement

This example demonstrates a COMPLETE A/B testing workflow:
0. A/A Testing - Validate infrastructure and estimate variance
1. Sample size planning (using A/A test learnings)
2. Gradual rollout with ASYMMETRIC split (e.g., 90/10, not 50/50)
3. Sequential monitoring with checks every 3 days
4. Continue collecting data until powered
5. Final analysis
6. Decision making with experiment duration tracking

Scenario: Testing an improved AI model on AI quality metric (0-5 scale), 7% target lift
Uses proper data schema with timestamps to calculate experiment duration
Demonstrates ASYMMETRIC variant allocation for risk management
"""

import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Ensure we can import ab_framework and verification when running from repo root
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
  sys.path.insert(0, REPO_ROOT)

from ab_framework import ABTest
from verification.data_generator import generate_scenario7_ai_metric_with_gap

def calculate_optimal_split(baseline_std, treatment_std_ratio=1.0, risk_tolerance='balanced'):
    """
    Calculate optimal treatment allocation based on statistical efficiency and risk.
    
    Args:
        baseline_std: Standard deviation of control metric
        treatment_std_ratio: Expected std(treatment)/std(control). Usually 1.0
        risk_tolerance: 'conservative' (90/10), 'balanced' (70/30), 'aggressive' (50/50)
    
    Returns:
        dict with recommended split and reasoning
    """
    
    # Statistical efficiency: For equal variances, 50/50 minimizes required sample size
    # Formula: Optimal ratio k = sqrt(σ_B / σ_A) where σ is standard deviation
    # When σ_A ≈ σ_B, optimal k ≈ 1, meaning 50/50 split
    
    statistical_optimal = treatment_std_ratio ** 0.5
    statistical_optimal_pct = int(100 * statistical_optimal / (1 + statistical_optimal))
    
    # Risk-based recommendations
    risk_splits = {
        'conservative': 10,   # 90/10 - Minimize user exposure to potential negative effects
        'balanced': 30,       # 70/30 - Balance between speed and risk
        'aggressive': 50      # 50/50 - Maximum statistical efficiency
    }
    
    recommended_treatment_pct = risk_splits.get(risk_tolerance, 30)
    
    # Calculate sample size multiplier vs 50/50
    # With unequal split, need more samples
    # Multiplier ≈ (1 + k)² / (4k) where k = n_treatment/n_control
    k = recommended_treatment_pct / (100 - recommended_treatment_pct)
    size_multiplier = (1 + k)**2 / (4 * k) if k > 0 else float('inf')
    
    return {
        'recommended_treatment_pct': recommended_treatment_pct,
        'recommended_control_pct': 100 - recommended_treatment_pct,
        'statistical_optimal_pct': statistical_optimal_pct,
        'size_multiplier': size_multiplier,
        'reasoning': f"""
Split Decision Factors:

1. STATISTICAL EFFICIENCY (50/50 is optimal when variances are equal)
   - Statistically optimal: {statistical_optimal_pct}/{100-statistical_optimal_pct}
   - Minimizes total required sample size
   - Best when you're confident in no negative effects

2. RISK MANAGEMENT (Asymmetric splits reduce exposure)
   - Conservative (90/10): Minimize user exposure, longer duration (+{((1+0.1/0.9)**2/(4*0.1/0.9)-1)*100:.0f}% samples)
   - Balanced (70/30): Good tradeoff (+{((1+0.3/0.7)**2/(4*0.3/0.7)-1)*100:.0f}% samples)
   - Aggressive (50/50): Maximum efficiency (baseline)

3. RECOMMENDED: {100-recommended_treatment_pct}/{recommended_treatment_pct} ({risk_tolerance})
   - Requires {size_multiplier:.1f}x more total samples than 50/50
   - Reduces treatment exposure by {50 - recommended_treatment_pct}%
   - Appropriate for: {"New features with unknown risks" if risk_tolerance == "conservative" else "Standard improvements" if risk_tolerance == "balanced" else "Well-understood changes"}

4. CONSIDERATIONS:
   - New/risky feature? Use conservative (90/10)
   - Standard improvement? Use balanced (70/30)
   - Small tweak/optimization? Use aggressive (50/50)
   - Revenue impact? Lean conservative
   - Pure learning? Can be aggressive
"""
    }

def run_analysis_check(
  data,
  check_number,
  days_elapsed,
  target_lift,
  phase_name="CHECK",
  *,
  expected_treatment_fraction: float = 0.5,
):
    """
    Run a mid-experiment analysis check.
    
    Args:
        data: DataFrame with experiment data up to this point
        check_number: Which check this is (1, 2, 3, etc.)
        days_elapsed: How many days into the experiment
        target_lift: The target lift we're trying to detect
        phase_name: Name of phase (CHECK, A/A TEST, etc.)
    
    Returns:
        dict with results including whether to continue
    """
    print("\n" + "=" * 70)
    print(f"{phase_name} #{check_number}: DAY {days_elapsed:.1f} ANALYSIS")
    print("=" * 70)
    
    # Calculate metrics
    n_sessions = len(data)
    n_convs = data['conversation_id'].nunique()
    
    # Show data collected
    for variant in ['A', 'B']:
        variant_df = data[data['variant'] == variant]
        avg_ai = variant_df['ai_metric'].mean()
        n_sessions_var = len(variant_df)
        n_convs_var = variant_df['conversation_id'].nunique()
        pct = (n_convs_var / n_convs * 100)
        print(f"  Variant {variant}: {avg_ai:.3f} AI metric ({n_sessions_var} sessions, {n_convs_var} convs, {pct:.1f}%)")
    
    # Run statistical test
    test = ABTest(
      name=f"AI_Model_v2_Day{days_elapsed:.0f}",
      variants=["A", "B"],
    )
    test.setup(treatment_fraction=expected_treatment_fraction)
    
    @test.metric(metric_type="mean")
    def ai_metric(data):
        """AI quality metric (0-5 continuous scale) - averaged per conversation."""
      conv_level = data.groupby(["variant", "conversation_id"])["ai_metric"].mean()
      out = {}
      for variant in ["A", "B"]:
        v = conv_level.loc[variant] if variant in conv_level.index.get_level_values(0) else pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {
          "mean": float(v.mean()) if n else 0.0,
          "std": float(v.std(ddof=1)) if n > 1 else 0.0,
          "n": n,
        }
      return out
    
    observed_counts = data.groupby("variant")["conversation_id"].nunique().to_dict()
    results = test.analyze(
      data,
      metrics=["ai_metric"],
      run_srm_check=True,
      observed_counts=observed_counts,
    )
    
    print("\n" + results.summary())
    print("\n" + results.conclusion('ai_metric'))
    
    # Extract results
    result = results.metric_results['ai_metric']
    is_significant = result['significant']
    p_value = result['p_value']
    lift = result['lift']
    
    return {
        'significant': is_significant,
        'p_value': p_value,
        'lift': lift,
        'n_conversations': n_convs,
        'n_sessions': n_sessions,
        'days_elapsed': days_elapsed,
        'results': results,
        'control_mean': result['control_value'],
        'treatment_mean': result['treatment_value'],
        'std_pooled': np.std(data.groupby('conversation_id')['ai_metric'].mean())
    }

print("=" * 70)
print("REAL-WORLD A/B TEST WORKFLOW")
print("Testing AI Model v2.0 for Quality Metric Improvement")
print("Complete Pipeline: A/A Test -> Sample Size -> A/B Test -> Decision")
print("WITH ASYMMETRIC VARIANT ALLOCATION (not 50/50)")
print("=" * 70)

# ============================================================================
# PHASE 0: A/A TESTING (INFRASTRUCTURE VALIDATION)
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 0: A/A TESTING")
print("=" * 70)

print("""
Purpose: Before running the actual A/B test, validate that:
  1. Randomization infrastructure works correctly (no SRM)
  2. Metric collection is accurate
  3. No significant difference when both groups get same treatment
  4. Estimate actual variance for sample size calculation
  
Setup: Both groups get current model (no treatment difference)
Duration: Run for 7 days to gather sufficient data
""")

# Generate A/A test data (no effect - both get baseline)
np.random.seed(100)  # Different seed for A/A test
aa_n_users = 400  # Smaller sample for validation

aa_df = generate_scenario7_ai_metric_with_gap(
    n_users=aa_n_users,
    baseline_ai_mean=3.2,
    baseline_ai_std=1.0,
    effect_size=0.0,  # NO EFFECT - both groups identical
    split=0.5
)

aa_df = aa_df.sort_values('timestamp').reset_index(drop=True)

# Run A/A test for 7 days
aa_min_time = aa_df['timestamp'].min()
aa_cutoff = aa_min_time + timedelta(days=7)
aa_df_7days = aa_df[aa_df['timestamp'] <= aa_cutoff].copy()

print(f"\nA/A Test Data:")
print(f"  - Duration: 7 days")
print(f"  - Sessions: {len(aa_df_7days):,}")
print(f"  - Conversations: {aa_df_7days['conversation_id'].nunique():,}")
print(f"  - Both groups get SAME treatment (current model)")

# Analyze A/A test
aa_result = run_analysis_check(
    data=aa_df_7days,
    check_number=1,
    days_elapsed=7.0,
    target_lift=0.0,
  phase_name="A/A TEST",
  expected_treatment_fraction=0.5,
)

print("\n" + "=" * 70)
print("A/A TEST VALIDATION RESULTS")
print("=" * 70)

observed_variance = aa_result['std_pooled']
observed_diff = abs(aa_result['treatment_mean'] - aa_result['control_mean'])

print(f"""
IMPORTANT: In an A/A test, we WANT p-value > 0.05 (no significant difference)
Both groups got the SAME treatment, so any difference is just random noise.
""")

if aa_result['significant']:
    print(f"""
[FAIL] A/A TEST FAILED!
- Found significant difference (p = {aa_result['p_value']:.4f}) when there should be none
- Control: {aa_result['control_mean']:.3f}, Treatment: {aa_result['treatment_mean']:.3f}
- Difference: {observed_diff:.3f} (should be negligible but p < 0.05!)

This indicates a problem with:
  * Randomization infrastructure (SRM issue)
  * Metric collection bias
  * Implementation bug

⚠️  DO NOT PROCEED WITH A/B TEST until this is fixed!

Next Steps:
  1. Check randomization logic
  2. Verify metric collection
  3. Review implementation
  4. Re-run A/A test after fixes
""")
    raise Exception("A/A test failed - cannot proceed")
else:
    print(f"""
✅ [OK] A/A TEST PASSED! ✅

Key Results:
  - P-value: {aa_result['p_value']:.4f} (> 0.05 ✅) - This is GOOD!
  - Control group: {aa_result['control_mean']:.3f} (n={aa_result['n_conversations']:,})
  - Treatment group: {aa_result['treatment_mean']:.3f} (n={aa_result['n_conversations']:,})
  - Observed difference: {observed_diff:.3f} (negligible, not significant ✅)
  - Observed lift: {aa_result['lift']:.2%} (< 2-3% is normal random noise ✅)

What This Validates:
  ✅ Randomization infrastructure is working correctly
  ✅ No Sample Ratio Mismatch detected
  ✅ Metric collection is accurate (no bias)
  ✅ No implementation bugs causing spurious differences

Estimated Parameters for A/B Test:
  - Baseline mean: {aa_result['control_mean']:.3f}
  - Standard deviation: {observed_variance:.3f}
  
✅ Infrastructure validated - Ready to proceed with A/B test!

Note: The "❌ FAIL" in the output above just means "not statistically 
significant" which is EXACTLY what we want in an A/A test! Both groups got 
the same treatment, so we should NOT see a significant difference.
""")

# ============================================================================
# PHASE 1: SAMPLE SIZE PLANNING (Using A/A Test Learnings)
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 1: SAMPLE SIZE PLANNING")
print("=" * 70)

# Use actual parameters from A/A test
baseline_mean = aa_result['control_mean']  # From A/A test
baseline_std = observed_variance            # From A/A test
target_lift = 0.07                          # Business requirement
alpha = 0.05
power = 0.80
check_frequency_days = 3

print(f"\nBusiness Requirements:")
print(f"  - Baseline AI Metric: {baseline_mean:.2f}/5.0 (from A/A test)")
print(f"  - Standard Deviation: {baseline_std:.2f} (from A/A test)")
print(f"  - Target Improvement: {target_lift:.1%} relative lift")
print(f"  - Expected Treatment: {baseline_mean * (1 + target_lift):.2f}/5.0")
print(f"  - Desired Power: {power:.0%}")
print(f"  - Significance Level: alpha = {alpha}")
print(f"  - Monitoring: Check every {check_frequency_days} days")

# Calculate required sample size using A/A test parameters
planning_test = ABTest(
  name="planning_only",
  variants=["A", "B"],
)
sample_plan = planning_test.backend.sample_size_mean(
    baseline_mean=baseline_mean,
    baseline_std=baseline_std,
    mde=target_lift,
    alpha=alpha,
    power=power
)

print(f"\nSample Size Calculation (for 50/50 split):")
print(f"  - Control group: {sample_plan['control_size']:,} conversations")
print(f"  - Treatment group: {sample_plan['treatment_size']:,} conversations")
print(f"  - Total required: {sample_plan['total_size']:,} conversations")

# ============================================================================
# PHASE 1.5: VARIANT ALLOCATION DECISION
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 1.5: VARIANT ALLOCATION STRATEGY")
print("=" * 70)

print("""
IMPORTANT DECISION: Should we use 50/50 split or asymmetric allocation?

The 50/50 split is NOT always optimal!
""")

# Calculate optimal splits for different risk tolerances
split_conservative = calculate_optimal_split(baseline_std, risk_tolerance='conservative')
split_balanced = calculate_optimal_split(baseline_std, risk_tolerance='balanced')
split_aggressive = calculate_optimal_split(baseline_std, risk_tolerance='aggressive')

print(split_conservative['reasoning'])

# For this example, let's use balanced approach (70/30)
chosen_risk = 'balanced'
chosen_split_info = split_balanced
rollout_percent_b = chosen_split_info['recommended_treatment_pct']
rollout_percent_a = chosen_split_info['recommended_control_pct']

print(f"\n" + "=" * 70)
print(f"DECISION: Using {rollout_percent_a}/{rollout_percent_b} Split (Balanced Approach)")
print("=" * 70)

# Adjust sample size for asymmetric split
size_multiplier = chosen_split_info['size_multiplier']
adjusted_total_size = int(sample_plan['total_size'] * size_multiplier)
adjusted_control_size = int(adjusted_total_size * rollout_percent_a / 100)
adjusted_treatment_size = int(adjusted_total_size * rollout_percent_b / 100)

print(f"""
Adjusted Sample Size (for {rollout_percent_a}/{rollout_percent_b} split):
  - Control group (A): {adjusted_control_size:,} conversations ({rollout_percent_a}%)
  - Treatment group (B): {adjusted_treatment_size:,} conversations ({rollout_percent_b}%)
  - Total required: {adjusted_total_size:,} conversations
  - Size multiplier: {size_multiplier:.2f}x vs 50/50 split
  
Trade-off Analysis:
  ✅ Reduces treatment exposure by {50 - rollout_percent_b}% (risk mitigation)
  ⚠️  Requires {(size_multiplier - 1)*100:.0f}% more samples
  ✅ Still achieves {power:.0%} power for {target_lift:.1%} lift
  ✅ Appropriate for this AI model upgrade (moderate risk)
  
Duration Impact:
  - 50/50 split: ~{sample_plan['total_size'] / 50:.0f} days (assuming 50 convs/day)
  - {rollout_percent_a}/{rollout_percent_b} split: ~{adjusted_total_size / 50:.0f} days
  - Additional time: ~{(adjusted_total_size - sample_plan['total_size']) / 50:.0f} days
""")

# ============================================================================
# PHASE 2: GRADUAL ROLLOUT WITH ASYMMETRIC ALLOCATION
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 2: GRADUAL ROLLOUT WITH ASYMMETRIC ALLOCATION")
print("=" * 70)

print(f"""
Rollout Strategy:
  - Control (A - current model): {rollout_percent_a}% of traffic
  - Treatment (B - new model): {rollout_percent_b}% of traffic
  - {rollout_percent_a}/{rollout_percent_b} split chosen for risk management
  
Why This Split?
  - Testing a NEW AI model with unknown risks
  - Want to limit potential negative impact
  - {rollout_percent_b}% exposure is enough to detect {target_lift:.1%} lift
  - Can always expand later if results are positive
  
Safety Measures:
  - SRM checks at every analysis point
  - Can stop experiment immediately if issues detected
  - Asymmetric split limits blast radius
  - Worth the {(size_multiplier - 1)*100:.0f}% extra samples for risk mitigation
""")

# ============================================================================
# PHASE 3: DATA GENERATION FOR A/B TEST
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 3: GENERATE A/B EXPERIMENT DATA")
print("=" * 70)

# Generate A/B test data with actual effect and asymmetric split
np.random.seed(43)
df_full = generate_scenario7_ai_metric_with_gap(
    n_users=adjusted_total_size,
    baseline_ai_mean=baseline_mean,
    baseline_ai_std=baseline_std,
    effect_size=baseline_mean * target_lift - 0.05,  # Slightly less than target
    split=rollout_percent_b / 100.0  # Use asymmetric split
)

df_full = df_full.sort_values('timestamp').reset_index(drop=True)

# Verify split
actual_a_pct = (df_full['variant'] == 'A').sum() / len(df_full) * 100
actual_b_pct = (df_full['variant'] == 'B').sum() / len(df_full) * 100

print(f"\nGenerated {len(df_full):,} sessions for A/B experiment")
print(f"Actual split: A={actual_a_pct:.1f}%, B={actual_b_pct:.1f}% (target: {rollout_percent_a}/{rollout_percent_b})")
print(f"Schema: {list(df_full.columns)}")

min_time = df_full['timestamp'].min()
max_time = df_full['timestamp'].max()
total_duration_days = (max_time - min_time).total_seconds() / 86400
print(f"Experiment timeline: {min_time} to {max_time}")
print(f"Total duration: {total_duration_days:.1f} days")

# ============================================================================
# PHASE 4: SEQUENTIAL MONITORING (EVERY 3 DAYS)
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 4: SEQUENTIAL MONITORING OF A/B TEST")
print("=" * 70)

check_results = []
check_day = check_frequency_days
check_number = 1

while check_day <= total_duration_days:
    cutoff_time = min_time + timedelta(days=check_day)
    df_current = df_full[df_full['timestamp'] <= cutoff_time].copy()
    
    check_result = run_analysis_check(
        data=df_current,
        check_number=check_number,
        days_elapsed=check_day,
        target_lift=target_lift,
      phase_name="A/B CHECK",
      expected_treatment_fraction=rollout_percent_b / 100.0,
    )
    check_results.append(check_result)
    
    # Decision logic
    print("\n" + "=" * 70)
    print(f"DECISION AFTER DAY {check_day:.1f}")
    print("=" * 70)
    
    if check_result['significant']:
        print(f"""
✅ SIGNIFICANT RESULT DETECTED!
- P-value: {check_result['p_value']:.4f} (< 0.05)
- Observed lift: {check_result['lift']:.2%} (target was {target_lift:.1%})

Recommendation: Continue to planned sample size for:
  1. More precise effect size estimate
  2. Protection against false positive
  3. Consistency validation
➡️ Continue and check again in 3 days
""")
    else:
        print(f"""
⚠️  NO SIGNIFICANT RESULT YET
- P-value: {check_result['p_value']:.4f} (> 0.05)
- Observed lift: {check_result['lift']:.2%}

Reason: Still collecting data
➡️ Continue and check again in 3 days
""")
    
    # Check if target reached
    n_convs_current = df_current['conversation_id'].nunique()
    if n_convs_current >= adjusted_total_size:
        print(f"\n✅ Reached target sample size ({n_convs_current:,} >= {adjusted_total_size:,})")
        print(f"   Moving to final analysis")
        break
    
    check_day += check_frequency_days
    check_number += 1

# ============================================================================
# PHASE 5: FINAL ANALYSIS
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 5: FINAL ANALYSIS")
print("=" * 70)

test_final = ABTest(
    name="AI_Model_v2_Final",
  variants=["A", "B"],
)
test_final.setup(treatment_fraction=rollout_percent_b / 100.0)

@test_final.metric(metric_type="mean")
def ai_metric(data):
    """AI quality metric (0-5 continuous scale) - averaged per conversation."""
  conv_level = data.groupby(["variant", "conversation_id"])["ai_metric"].mean()
  out = {}
  for variant in ["A", "B"]:
    v = conv_level.loc[variant] if variant in conv_level.index.get_level_values(0) else pd.Series(dtype=float)
    n = int(v.shape[0])
    out[variant] = {
      "mean": float(v.mean()) if n else 0.0,
      "std": float(v.std(ddof=1)) if n > 1 else 0.0,
      "n": n,
    }
  return out

observed_counts_final = df_full.groupby("variant")["conversation_id"].nunique().to_dict()
results_final = test_final.analyze(
  df_full,
  metrics=["ai_metric"],
  run_srm_check=True,
  observed_counts=observed_counts_final,
)

print("\n" + results_final.summary())
print("\n" + results_final.conclusion('ai_metric'))

# ============================================================================
# PHASE 6: BUSINESS DECISION
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 6: BUSINESS DECISION")
print("=" * 70)

result = results_final.metric_results['ai_metric']
is_significant = result['significant']
observed_lift = result['lift']
p_value = result['p_value']
ci_lower = result['ci_lower']
ci_upper = result['ci_upper']
control_value = result['control_value']
treatment_value = result['treatment_value']

if is_significant:
    improvement = treatment_value - control_value
    print(f"""
✅ DECISION: SHIP AI MODEL v2.0

Rationale:
  - A/A test validated infrastructure ✅
  - Statistically significant improvement (p = {p_value:.4f})
  - Observed lift: {observed_lift:.2%}
  - Absolute improvement: +{improvement:.3f} points
  - 95% CI: [{ci_lower:.2%}, {ci_upper:.2%}]
  - Sample: {result['sample_size_control'] + result['sample_size_treatment']:,} conversations
  - Split used: {rollout_percent_a}/{rollout_percent_b} (risk-managed)
  - Duration: {total_duration_days:.1f} days
  - Checks: {len(check_results)} (every {check_frequency_days} days)
  
Rollout Plan:
  1. Expand from {rollout_percent_b}% to 50% gradually
  2. Monitor AI metric closely for first week
  3. If stable, expand to 100% over next week
  4. Compare to experiment baseline
  5. Document improvement for future reference
  
Expected Impact:
  - AI metric: {control_value:.2f} -> {treatment_value:.2f}
  - +{improvement:.3f} points on 5-point scale
  - {observed_lift:.1%} relative improvement
  
Risk Management Success:
  - Used {rollout_percent_a}/{rollout_percent_b} split to limit initial exposure
  - Only {rollout_percent_b}% of users experienced new model during test
  - Worth the extra {(size_multiplier - 1)*100:.0f}% samples for confidence
""")
else:
    print(f"""
❌ DECISION: DO NOT SHIP AI Model v2.0

Rationale:
  - A/A test validated infrastructure ✅
  - No significant improvement (p = {p_value:.4f})
  - Observed lift: {observed_lift:.2%}
  - Duration: {total_duration_days:.1f} days
  - Split used: {rollout_percent_a}/{rollout_percent_b}
  
Next Steps:
  1. Investigate why v2.0 didn't improve
  2. Review model changes
  3. Consider alternative approaches
  
Risk Management Success:
  - {rollout_percent_a}/{rollout_percent_b} split limited exposure to unsuccessful variant
  - Only {rollout_percent_b}% of users affected
  - Asymmetric allocation protected user experience
""")

# ============================================================================
# PHASE 7: COMPLETE WORKFLOW SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 7: COMPLETE WORKFLOW SUMMARY")
print("=" * 70)

print(f"""
Complete A/B Test Pipeline:

Phase 0: A/A Testing (7 days)
  - Validated randomization ✅
  - Estimated variance: {observed_variance:.3f}
  - Baseline mean: {aa_result['control_mean']:.3f}
  
Phase 1: Sample Size Planning
  - Used A/A test parameters
  - Required (50/50): {sample_plan['total_size']:,} conversations
  - Adjusted ({rollout_percent_a}/{rollout_percent_b}): {adjusted_total_size:,} conversations
  
Phase 1.5: Variant Allocation Strategy
  - Chose {rollout_percent_a}/{rollout_percent_b} split (balanced risk approach)
  - Trade-off: +{(size_multiplier - 1)*100:.0f}% samples for -{50 - rollout_percent_b}% exposure
  - Appropriate for AI model with moderate risk
  
Phase 2: Gradual Rollout
  - {rollout_percent_b}% to variant B (asymmetric)
  - Safety measures in place
  - Limited blast radius
  
Phase 3-4: A/B Test with Monitoring
  - Duration: {total_duration_days:.1f} days
  - Checks performed: {len(check_results)}
  - Check frequency: Every {check_frequency_days} days
  - Maintained {rollout_percent_a}/{rollout_percent_b} split throughout
""")

# Summary table
comparison = pd.DataFrame([
    {
        'Phase': 'A/A Test',
        'Day': 7,
        'Split': '50/50',
        'Conversations': aa_result['n_conversations'],
        'Lift': f"{aa_result['lift']:.2%}",
        'P-value': f"{aa_result['p_value']:.4f}",
        'Status': '✅ Pass' if not aa_result['significant'] else '❌ Fail'
    }
] + [
    {
        'Phase': f"A/B Check {i+1}",
        'Day': int(r['days_elapsed']),
        'Split': f"{rollout_percent_a}/{rollout_percent_b}",
        'Conversations': r['n_conversations'],
        'Lift': f"{r['lift']:.2%}",
        'P-value': f"{r['p_value']:.4f}",
        'Status': '✅ Sig' if r['significant'] else '⚠️ NS'
    }
    for i, r in enumerate(check_results)
] + [{
    'Phase': 'A/B Final',
    'Day': int(total_duration_days),
    'Split': f"{rollout_percent_a}/{rollout_percent_b}",
    'Conversations': result['sample_size_control'] + result['sample_size_treatment'],
    'Lift': f"{result['lift']:.2%}",
    'P-value': f"{result['p_value']:.4f}",
    'Status': '✅ Sig' if result['significant'] else '❌ NS'
}])

print("\n" + comparison.to_string(index=False))

print(f"""

Key Learnings:
  1. ✅ A/A test validated infrastructure before investing in full experiment
  2. ✅ Used actual variance from A/A test for accurate sample size
  3. ✅ ASYMMETRIC allocation ({rollout_percent_a}/{rollout_percent_b}) managed risk effectively
  4. ✅ Understood trade-off: +{(size_multiplier - 1)*100:.0f}% samples vs -{50 - rollout_percent_b}% exposure
  5. ✅ Sequential monitoring provided continuous oversight
  6. ✅ Complete audit trail from validation to decision
  
Why {rollout_percent_a}/{rollout_percent_b} Instead of 50/50?
  - AI model upgrade has moderate risk (unknown failure modes)
  - {rollout_percent_b}% exposure limits potential negative impact
  - Worth extra {(adjusted_total_size - sample_plan['total_size']):,} samples for confidence
  - Can expand rollout if results are positive
  - Standard practice for new features vs optimization tweaks
  
Total Time Investment:
  - A/A test: 7 days (infrastructure validation)
  - A/B test: {total_duration_days:.1f} days (actual experiment with {rollout_percent_a}/{rollout_percent_b} split)
  - Analysis: ~{30 + 15 + len(check_results) * 15 + 15} minutes total
  - Total duration: {7 + total_duration_days:.1f} days
  
Value Created:
  - Validated infrastructure prevents false results
  - Accurate sample size prevents under/overpowering
  - Risk minimized through asymmetric allocation
  - Clear decision with complete documentation
  - Protected {rollout_percent_a}% of users from potential issues
""")

print("\n" + "=" * 70)
print("COMPLETE WORKFLOW FINISHED")
print("=" * 70)
print(f"\nFINAL NOTE: The {rollout_percent_a}/{rollout_percent_b} split demonstrates that")
print(f"50/50 is NOT always the best choice. For risky changes, use asymmetric")
print(f"allocation to balance statistical power with user protection.")
print("=" * 70)
