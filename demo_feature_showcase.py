"""
Feature Showcase Demo - AB Framework
Demonstrates all key features with clear examples
"""

from ab_framework import ABTest, QualityChecker
import pandas as pd
import numpy as np

print("=" * 80)
print("AB FRAMEWORK - FEATURE SHOWCASE")
print("Comprehensive demonstration of all framework capabilities")
print("=" * 80)

# =============================================================================
# FEATURE 1: SAMPLE SIZE PLANNING
# =============================================================================
print("\n" + "=" * 80)
print("FEATURE 1: SAMPLE SIZE PLANNING")
print("=" * 80)

planning_test = ABTest(
    name="planning_only",
    data=df.head(2).assign(variant=["A", "B"]),
)

print("\n### 1A: Sample Size for Conversion Rate (Proportions)")
print("-" * 80)
print("Scenario: Increase signup conversion from 5% to 6%")

result = calc.for_proportion(
    baseline_rate=0.05,
    mde=0.20,  # 20% relative increase (5% -> 6%)
    power=0.80,
    alpha=0.05
)

print(f"\nRequired Sample Size:")
print(f"  * Control: {result['control_size']:,} users")
print(f"  * Treatment: {result['treatment_size']:,} users")
print(f"  * Total: {result['total_size']:,} users")
print(f"  * Baseline: {result['assumptions']['baseline_rate']:.1%}")
print(f"  * Expected Treatment: {result['assumptions']['treatment_rate']:.1%}")

print("\n### 1B: Sample Size for Continuous Metrics (Means)")
print("-" * 80)
print("Scenario: Increase average session duration from 180s to 200s")

result = calc.for_mean(
    baseline_mean=180,
    baseline_std=60,
    mde=0.11,  # 11% increase (180s -> 200s)
    power=0.80,
    alpha=0.05
)

print(f"\nRequired Sample Size:")
print(f"  * Control: {result['control_size']:,} users")
print(f"  * Treatment: {result['treatment_size']:,} users")
print(f"  * Total: {result['total_size']:,} users")
print(f"  * Baseline: {result['assumptions']['baseline_mean']:.0f}s")
print(f"  * Standard Deviation: {result['assumptions']['baseline_std']:.0f}s")
print(f"  * Expected Treatment: {result['assumptions']['treatment_mean']:.0f}s")

print("\n### 1C: Power Analysis")
print("-" * 80)
print("Question: What power do we have with only 5,000 users?")

power = calc.calculate_power_proportion(
    n_control=2500,
    n_treatment=2500,
    baseline_rate=0.05,
    treatment_rate=0.06,
    alpha=0.05
)

print(f"\nWith 5,000 users (2,500 each):")
print(f"  * Statistical Power: {power:.1%}")
print(f"  * Interpretation: {power:.0%} chance to detect the effect if it exists")

# =============================================================================
# FEATURE 2: MULTIPLE TESTING CORRECTIONS
# =============================================================================
print("\n" + "=" * 80)
print("FEATURE 2: MULTIPLE TESTING CORRECTIONS")
print("=" * 80)

print("\nWhen testing multiple metrics, we need to adjust significance levels")
print("to control family-wise error rate (FWER).")

# Generate sample data
np.random.seed(42)
n_users = 2000
df_multi = pd.DataFrame({
    'user_id': range(n_users),
    'variant': np.random.choice(['A', 'B'], n_users),
    'converted': np.random.binomial(1, 0.05, n_users),
    'revenue': np.random.exponential(50, n_users),
    'engagement_score': np.random.normal(3.5, 1.0, n_users)
})

test_multi = ABTest(
    name="multi_metric_test",
    data=df_multi,
    variant_col="variant",
    unit_id="user_id"
)

@test_multi.metric
def conversion_rate(data):
    return data.groupby('user_id')['converted'].max()

@test_multi.metric
def revenue_per_user(data):
    return data.groupby('user_id')['revenue'].sum()

@test_multi.metric
def avg_engagement(data):
    return data.groupby('user_id')['engagement_score'].mean()

print("\n### 2A: No Correction (Not Recommended)")
print("-" * 80)
results_none = test_multi.analyze(
    metrics=['conversion_rate', 'revenue_per_user', 'avg_engagement'],
    correction=None
)
print("\nWith 3 metrics at alpha=0.05 each:")
print("  * Probability of at least one false positive: ~14%")
print(results_none.summary())

print("\n### 2B: Bonferroni Correction (Conservative)")
print("-" * 80)
results_bonf = test_multi.analyze(
    metrics=['conversion_rate', 'revenue_per_user', 'avg_engagement'],
    correction='bonferroni'
)
print("\nBonferroni: alpha_adjusted = 0.05 / 3 = 0.0167 per metric")
print("  * Controls FWER at 5%")
print("  * More conservative, may miss real effects")
print(results_bonf.summary())

print("\n### 2C: Benjamini-Hochberg FDR (Balanced)")
print("-" * 80)
results_fdr = test_multi.analyze(
    metrics=['conversion_rate', 'revenue_per_user', 'avg_engagement'],
    correction='fdr_bh'
)
print("\nFalse Discovery Rate control:")
print("  * Controls proportion of false discoveries")
print("  * More powerful than Bonferroni")
print("  * Good balance for multiple metrics")
print(results_fdr.summary())

# =============================================================================
# FEATURE 3: QUALITY CHECKS
# =============================================================================
print("\n" + "=" * 80)
print("FEATURE 3: QUALITY CHECKS")
print("=" * 80)

checker = QualityChecker()

print("\n### 3A: Sample Ratio Mismatch (SRM) Check")
print("-" * 80)
print("\nSRM detects randomization issues that could invalidate results.")

# Good split (50/50)
srm_good = checker.check_srm({'A': 10000, 'B': 10050})
print(f"\nGood Split (10,000 vs 10,050):")
print(f"  * Chi-square: {srm_good['chi2_statistic']:.4f}")
print(f"  * P-value: {srm_good['p_value']:.6f}")
print(f"  * Status: {srm_good['recommendation']}")

# Bad split (imbalanced)
srm_bad = checker.check_srm({'A': 10500, 'B': 9500})
print(f"\nBad Split (10,500 vs 9,500):")
print(f"  * Chi-square: {srm_bad['chi2_statistic']:.4f}")
print(f"  * P-value: {srm_bad['p_value']:.6f}")
print(f"  * Status: {srm_bad['recommendation']}")

print("\n### 3B: Minimum Detectable Effect (MDE)")
print("-" * 80)
print("\nMDE tells you the smallest effect you can reliably detect.")

mde_result = checker.check_mde(
    sample_size_control=5000,
    sample_size_treatment=5000,
    baseline_mean=100,
    baseline_std=50,
    alpha=0.05,
    power=0.80
)

print(f"\nWith 10,000 users (5,000 each):")
print(f"  * MDE (absolute): {mde_result['mde_absolute']:.2f} points")
print(f"  * MDE (relative): {mde_result['mde_relative']:.1%}")
print(f"  * Interpretation: {mde_result['interpretation']}")

# =============================================================================
# FEATURE 4: PROGRESSIVE MONITORING
# =============================================================================
print("\n" + "=" * 80)
print("FEATURE 4: PROGRESSIVE MONITORING")
print("=" * 80)

print("\nMonitor your experiment over time by analyzing subsets of data.")

# Generate sequential data
np.random.seed(42)
n_total = 5000
df_seq = pd.DataFrame({
    'user_id': range(n_total),
    'variant': np.random.choice(['A', 'B'], n_total),
    'converted': np.random.binomial(1, 0.05, n_total)
})
df_seq.loc[df_seq['variant'] == 'B', 'converted'] = np.random.binomial(
    1, 0.06, (df_seq['variant'] == 'B').sum()
)

print("\n### Monitoring at Different Sample Sizes")
print("-" * 80)
print("As data accumulates, check for emerging patterns:")

for n_check in [1000, 2000, 3000, 5000]:
    df_subset = df_seq.iloc[:n_check].copy()
    
    test_check = ABTest(
        name=f"check_n{n_check}",
        data=df_subset,
        variant_col="variant",
        unit_id="user_id"
    )
    
    @test_check.metric
    def conversion(data):
        return data.groupby('user_id')['converted'].max()
    
    results = test_check.analyze(['conversion'])
    
    print(f"\nCheck at n={n_check:,}:")
    print(f"  * Conversion A: {results.metric_results['conversion']['control_value']:.2%}")
    print(f"  * Conversion B: {results.metric_results['conversion']['treatment_value']:.2%}")
    print(f"  * Lift: {results.metric_results['conversion']['lift']:.1%}")
    print(f"  * P-value: {results.metric_results['conversion']['p_value']:.4f}")
    print(f"  * Significant? {'[OK] YES' if results.metric_results['conversion']['significant'] else '[X] NO'}")

print("\nNote: For proper sequential testing with early stopping,")
print("use dedicated sequential testing methodologies to control error rates.")

# =============================================================================
# FEATURE 5: FLEXIBLE METRIC DEFINITIONS
# =============================================================================
print("\n" + "=" * 80)
print("FEATURE 5: FLEXIBLE METRIC DEFINITIONS")
print("=" * 80)

print("\nDefine metrics using simple Python functions with full flexibility.")

# Generate sample e-commerce data
np.random.seed(42)
n_sessions = 5000
df_ecom = pd.DataFrame({
    'session_id': range(n_sessions),
    'user_id': np.repeat(range(n_sessions // 3), 3)[:n_sessions],
    'variant': np.random.choice(['A', 'B'], n_sessions),
    'page_views': np.random.poisson(5, n_sessions),
    'time_spent': np.random.exponential(120, n_sessions),
    'purchased': np.random.binomial(1, 0.03, n_sessions),
    'revenue': np.random.exponential(50, n_sessions) * np.random.binomial(1, 0.03, n_sessions)
})

test_ecom = ABTest(
    name="ecommerce_test",
    data=df_ecom,
    variant_col="variant",
    unit_id="user_id"
)

print("\n### Session-Level Metrics")
print("-" * 80)

@test_ecom.metric
def pages_per_session(data):
    """Average pages viewed per session"""
    return data.groupby('user_id')['page_views'].mean()

@test_ecom.metric
def time_per_session(data):
    """Average time spent per session (seconds)"""
    return data.groupby('user_id')['time_spent'].mean()

print("\n### User-Level Metrics")
print("-" * 80)

@test_ecom.metric
def conversion_rate(data):
    """% of users who made at least one purchase"""
    return data.groupby('user_id')['purchased'].max()

@test_ecom.metric
def revenue_per_user(data):
    """Total revenue per user"""
    return data.groupby('user_id')['revenue'].sum()

print("\n### Conditional Metrics (Only for Converters)")
print("-" * 80)

@test_ecom.metric
def avg_order_value(data):
    """Average order value (AOV) - only for users who purchased"""
    purchasers = data[data['purchased'] == 1]
    if len(purchasers) == 0:
        return pd.Series(dtype=float)
    return purchasers.groupby('user_id')['revenue'].sum()

results_ecom = test_ecom.analyze([
    'pages_per_session',
    'time_per_session', 
    'conversion_rate',
    'revenue_per_user',
    'avg_order_value'
])

print("\n### Results for All Metrics")
print("-" * 80)
print(results_ecom.summary())

# =============================================================================
# FEATURE 6: RESULT EXPORT OPTIONS
# =============================================================================
print("\n" + "=" * 80)
print("FEATURE 6: RESULT EXPORT OPTIONS")
print("=" * 80)

print("\n### 6A: DataFrame Export (for further analysis)")
print("-" * 80)
df_results = results_ecom.to_dataframe()
print("\nDataFrame with shape:", df_results.shape)
print("\nColumns:", list(df_results.columns))
print("\nFirst few rows:")
print(df_results[['metric', 'control_value', 'treatment_value', 'lift', 'p_value', 'significant']].head())

print("\n### 6B: Dictionary Export (for APIs/JSON)")
print("-" * 80)
dict_results = results_ecom.to_dict()
print("\nDictionary keys:", list(dict_results.keys()))
print("\nSample metric result:")
metric_name = list(dict_results['metrics'].keys())[0]
print(f"  Metric: {metric_name}")
for key, value in list(dict_results['metrics'][metric_name].items())[:5]:
    print(f"    {key}: {value}")

print("\n### 6C: Plain English Conclusions")
print("-" * 80)
for metric in ['conversion_rate', 'revenue_per_user']:
    print("\n" + results_ecom.conclusion(metric))

# =============================================================================
# FEATURE 7: CONFIDENCE INTERVALS
# =============================================================================
print("\n" + "=" * 80)
print("FEATURE 7: CONFIDENCE INTERVALS")
print("=" * 80)

print("\nAll results include 95% confidence intervals for precision estimates.")

print("\n### Example: Revenue Per User")
print("-" * 80)
revenue_result = results_ecom.metric_results['revenue_per_user']
print(f"\nPoint Estimates:")
print(f"  * Control: ${revenue_result['control_value']:.2f}")
print(f"  * Treatment: ${revenue_result['treatment_value']:.2f}")
print(f"  * Absolute Difference: ${revenue_result['absolute_difference']:.2f}")

print(f"\n95% Confidence Interval for Lift:")
print(f"  * Lower Bound: {revenue_result['ci_lower']:.1%}")
print(f"  * Upper Bound: {revenue_result['ci_upper']:.1%}")
print(f"  * Point Estimate: {revenue_result['lift']:.1%}")

print(f"\nInterpretation:")
if revenue_result['significant']:
    print(f"  [OK] We are 95% confident the true lift is between")
    print(f"    {revenue_result['ci_lower']:.1%} and {revenue_result['ci_upper']:.1%}")
else:
    print(f"  The confidence interval includes zero, suggesting no significant effect")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 80)
print("FEATURE SUMMARY")
print("=" * 80)

print("""
[OK] Sample Size Planning
  - Proportions (conversion rates, CTR)
  - Means (revenue, time, continuous metrics)
  - Power analysis

[OK] Multiple Testing Corrections
  - Bonferroni (conservative)
  - Benjamini-Hochberg FDR (balanced)
  - Protects against false positives

[OK] Quality Checks
  - Sample Ratio Mismatch (SRM) detection
  - Minimum Detectable Effect (MDE)
  - Automatic validation

[OK] Progressive Monitoring
  - Check results at multiple timepoints
  - Track metric evolution
  - Informed decision timing

[OK] Flexible Metrics
  - Simple Python functions
  - Session, user, or custom aggregations
  - Conditional metrics (e.g., AOV)

[OK] Export Options
  - DataFrames for analysis
  - Dictionaries for APIs
  - Plain English conclusions

[OK] Confidence Intervals
  - Precision estimates
  - 95% CI for all metrics
  - Effect size uncertainty
""")

print("\n" + "=" * 80)
print("FEATURE SHOWCASE COMPLETE")
print("=" * 80)
