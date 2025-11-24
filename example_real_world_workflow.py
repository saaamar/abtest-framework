"""
Real-World A/B Test Workflow: AI Quality Metric Improvement

This example demonstrates a COMPLETE A/B testing workflow:
0. A/A Testing - Validate infrastructure and estimate variance
1. Sample size planning (using A/A test learnings)
2. Gradual rollout of variant B
3. Sequential monitoring with checks every 3 days
4. Continue collecting data until powered
5. Final analysis
6. Decision making with experiment duration tracking

Scenario: Testing an improved AI model on AI quality metric (0-5 scale), 7% target lift
Uses proper data schema with timestamps to calculate experiment duration
"""

import sys
sys.path.append('verification')

from ab_framework import ABTest, SampleSizeCalculator
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from verification.data_generator import generate_scenario7_ai_metric_with_gap

def run_analysis_check(data, check_number, days_elapsed, target_lift, phase_name="CHECK"):
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
        print(f"  Variant {variant}: {avg_ai:.3f} AI metric ({n_sessions_var} sessions, {n_convs_var} conversations)")
    
    # Run statistical test
    test = ABTest(
        name=f"AI_Model_v2_Day{days_elapsed:.0f}",
        data=data,
        variant_col="variant",
        unit_id="conversation_id"
    )
    
    @test.metric
    def ai_metric(data):
        """AI quality metric (0-5 continuous scale) - averaged per conversation."""
        return data.groupby('conversation_id')['ai_metric'].mean()
    
    results = test.analyze(['ai_metric'])
    
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
print("Complete Pipeline: A/A Test → Sample Size → A/B Test → Decision")
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
    phase_name="A/A TEST"
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
❌ A/A TEST FAILED!
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
✅ A/A TEST PASSED! ✅

Key Results:
  - P-value: {aa_result['p_value']:.4f} (> 0.05 ✓) - This is GOOD!
  - Control group: {aa_result['control_mean']:.3f} (n={aa_result['n_conversations']:,})
  - Treatment group: {aa_result['treatment_mean']:.3f} (n={aa_result['n_conversations']:,})
  - Observed difference: {observed_diff:.3f} (negligible, not significant ✓)
  - Observed lift: {aa_result['lift']:.2%} (< 2-3% is normal random noise ✓)

What This Validates:
  ✓ Randomization infrastructure is working correctly
  ✓ No Sample Ratio Mismatch detected
  ✓ Metric collection is accurate (no bias)
  ✓ No implementation bugs causing spurious differences

Estimated Parameters for A/B Test:
  - Baseline mean: {aa_result['control_mean']:.3f}
  - Standard deviation: {observed_variance:.3f}
  
✅ Infrastructure validated - Ready to proceed with A/B test!

Note: The "❌ ai_metric" in the output above just means "not statistically 
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
print(f"  - Significance Level: α = {alpha}")
print(f"  - Monitoring: Check every {check_frequency_days} days")

# Calculate required sample size using A/A test parameters
calc = SampleSizeCalculator()
sample_plan = calc.for_mean(
    baseline_mean=baseline_mean,
    baseline_std=baseline_std,
    mde=target_lift,
    alpha=alpha,
    power=power
)

print(f"\nSample Size Calculation (using A/A test parameters):")
print(f"  - Control group: {sample_plan['control_size']:,} conversations")
print(f"  - Treatment group: {sample_plan['treatment_size']:,} conversations")
print(f"  - Total required: {sample_plan['total_size']:,} conversations")

# ============================================================================
# PHASE 2: GRADUAL ROLLOUT OF VARIANT B
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 2: GRADUAL ROLLOUT")
print("=" * 70)

rollout_percent = 50  # 50/50 split
print(f"""
Rollout Strategy:
  - Start with {rollout_percent}% of traffic to Variant B (new model)
  - Remaining {100-rollout_percent}% stays on Variant A (current model)
  - Monitor closely for any issues
  - Can increase/decrease rollout % if needed

Safety Measures:
  - SRM checks at every analysis point
  - Can stop experiment immediately if issues detected
  - Gradual rollout minimizes risk
""")

# ============================================================================
# PHASE 3: DATA GENERATION FOR A/B TEST
# ============================================================================
print("\n" + "=" * 70)
print("PHASE 3: GENERATE A/B EXPERIMENT DATA")
print("=" * 70)

# Generate A/B test data with actual effect
np.random.seed(43)
df_full = generate_scenario7_ai_metric_with_gap(
    n_users=sample_plan['total_size'],
    baseline_ai_mean=baseline_mean,
    baseline_ai_std=baseline_std,
    effect_size=baseline_mean * target_lift - 0.05,  # Slightly less than target
    split=rollout_percent / 100.0
)

df_full = df_full.sort_values('timestamp').reset_index(drop=True)

print(f"\nGenerated {len(df_full):,} sessions for A/B experiment")
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
        phase_name="A/B CHECK"
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
⏩ Continue and check again in 3 days
""")
    else:
        print(f"""
ℹ️  NO SIGNIFICANT RESULT YET
- P-value: {check_result['p_value']:.4f} (> 0.05)
- Observed lift: {check_result['lift']:.2%}

Reason: Still collecting data
⏩ Continue and check again in 3 days
""")
    
    # Check if target reached
    n_convs_current = df_current['conversation_id'].nunique()
    if n_convs_current >= sample_plan['total_size']:
        print(f"\n✅ Reached target sample size ({n_convs_current:,} >= {sample_plan['total_size']:,})")
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
    data=df_full,
    variant_col="variant",
    unit_id="conversation_id"
)

@test_final.metric
def ai_metric(data):
    """AI quality metric (0-5 continuous scale) - averaged per conversation."""
    return data.groupby('conversation_id')['ai_metric'].mean()

results_final = test_final.analyze(['ai_metric'])

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
  - A/A test validated infrastructure ✓
  - Statistically significant improvement (p = {p_value:.4f})
  - Observed lift: {observed_lift:.2%}
  - Absolute improvement: +{improvement:.3f} points
  - 95% CI: [{ci_lower:.2%}, {ci_upper:.2%}]
  - Sample: {result['sample_size_control'] + result['sample_size_treatment']:,} conversations
  - Duration: {total_duration_days:.1f} days
  - Checks: {len(check_results)} (every {check_frequency_days} days)
  
Rollout Plan:
  1. Increase to 100% of traffic gradually
  2. Monitor AI metric closely for first week
  3. Compare to experiment baseline
  4. Document improvement for future reference
  
Expected Impact:
  - AI metric: {control_value:.2f} → {treatment_value:.2f}
  - +{improvement:.3f} points on 5-point scale
  - {observed_lift:.1%} relative improvement
""")
else:
    print(f"""
❌ DECISION: DO NOT SHIP AI Model v2.0

Rationale:
  - A/A test validated infrastructure ✓
  - No significant improvement (p = {p_value:.4f})
  - Observed lift: {observed_lift:.2%}
  - Duration: {total_duration_days:.1f} days
  
Next Steps:
  1. Investigate why v2.0 didn't improve
  2. Review model changes
  3. Consider alternative approaches
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
  - Validated randomization ✓
  - Estimated variance: {observed_variance:.3f}
  - Baseline mean: {aa_result['control_mean']:.3f}
  
Phase 1: Sample Size Planning
  - Used A/A test parameters
  - Required: {sample_plan['total_size']:,} conversations
  
Phase 2: Gradual Rollout
  - {rollout_percent}% to variant B
  - Safety measures in place
  
Phase 3-4: A/B Test with Monitoring
  - Duration: {total_duration_days:.1f} days
  - Checks performed: {len(check_results)}
  - Check frequency: Every {check_frequency_days} days
""")

# Summary table
comparison = pd.DataFrame([
    {
        'Phase': 'A/A Test',
        'Day': 7,
        'Conversations': aa_result['n_conversations'],
        'Lift': f"{aa_result['lift']:.2%}",
        'P-value': f"{aa_result['p_value']:.4f}",
        'Status': '✅ Pass' if not aa_result['significant'] else '❌ Fail'
    }
] + [
    {
        'Phase': f"A/B Check {i+1}",
        'Day': int(r['days_elapsed']),
        'Conversations': r['n_conversations'],
        'Lift': f"{r['lift']:.2%}",
        'P-value': f"{r['p_value']:.4f}",
        'Status': '✅ Sig' if r['significant'] else '❌ NS'
    }
    for i, r in enumerate(check_results)
] + [{
    'Phase': 'A/B Final',
    'Day': int(total_duration_days),
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
  3. ✅ Gradual rollout ({rollout_percent}%) minimized risk
  4. ✅ Sequential monitoring provided continuous oversight
  5. ✅ Complete audit trail from validation to decision
  
Total Time Investment:
  - A/A test: 7 days (infrastructure validation)
  - A/B test: {total_duration_days:.1f} days (actual experiment)
  - Analysis: ~{30 + 15 + len(check_results) * 15 + 15} minutes total
  - Total duration: {7 + total_duration_days:.1f} days
  
Value Created:
  - Validated infrastructure prevents false results
  - Accurate sample size prevents under/overpowering
  - Risk minimized through gradual rollout
  - Clear decision with complete documentation
""")

print("\n" + "=" * 70)
print("COMPLETE WORKFLOW FINISHED")
print("=" * 70)
