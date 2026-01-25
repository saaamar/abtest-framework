> Purpose: Architecture Decision Record (ADR) explaining why we built a custom A/B testing framework instead of using existing packages
> Generated: Manually authored, maintained under version control.

# A/B Testing Framework Decision

**Date:** November 23, 2025  
**Decision:** ✅ **BUILD CUSTOM FRAMEWORK**  
**Confidence Level:** HIGH (Evidence-based through empirical testing)  
**Status:** ✅ **Verification Complete - 8 Scenarios Tested**

---

## Executive Summary

After comprehensive empirical testing of three A/B testing approaches against **eight realistic test scenarios**, we conclude that **building a custom A/B testing orchestration and standardization layer** (sitting on top of existing stats packages) is the correct and necessary decision.

This document combines:
- **Scientific verification results** (Methods, Results, Statistical Analysis)
- **Business justification** (ROI, Architecture, Implementation Plan)
- **Complete evidence base** for the BUILD decision

### Latest Verification Results (November 23, 2025)

**Test Environment:**
- 8 comprehensive scenarios (conversion, revenue, CTR, multi-metric, agent bot metrics)
- Event-level data structure (sessions/impressions)
import pandas as pd

from ab_framework import ABTest

df = pd.read_csv("sessions.csv")

test = ABTest(name="homepage_redesign", variants=["A", "B"])
observed_counts = df.groupby("variant")["user_id"].nunique().to_dict()

@test.metric(metric_type="mean")
def revenue_per_active_user(data):
    active = data[data["sessions"] > 0]
    user_rev = active.groupby(["variant", "user_id"])["revenue"].sum()

    stats = (
        user_rev.groupby("variant")
        .agg(["mean", "std", "count"])
        .rename(columns={"count": "n"})
        .fillna({"std": 0.0})
    )
    return {
        v: {"mean": float(r["mean"]), "std": float(r["std"]) if int(r["n"]) > 1 else 0.0, "n": int(r["n"]) }
        for v, r in stats.iterrows()
    }

@test.metric(metric_type="proportion")
def conversion_rate(data):
    user_conv = data.groupby(["variant", "user_id"])["converted"].max()
    stats = (
        user_conv.groupby("variant")
        .agg(["sum", "count"])
        .rename(columns={"sum": "successes", "count": "n"})
    )
    return {v: {"successes": int(r["successes"]), "n": int(r["n"])} for v, r in stats.iterrows()}

results = test.analyze(
    df,
    metrics=["revenue_per_active_user", "conversion_rate"],
    correction="bonferroni",
    run_srm_check=True,
    observed_counts=observed_counts,
)

print(results.summary())

| Scenario | Data Structure | Metric Type | Sample Size | True Effect |
|----------|---------------|-------------|-------------|-------------|
| S1: Conversion Rate | Impression-level | Binary | 11,111 impressions, 2,000 users | +12% (NS) |
| S2: Revenue per Active User | Session-level | Continuous | 3,680 sessions, 641 users | +19.2% (p<0.001) |
| S3: Click-Through Rate | Impression-level | Binary (rate) | 197,617 impressions, 1,584 users | +23.2% (p<0.001) |
| S4: Multi-Metric Dashboard | Session-level | Mixed (3 metrics) | 6,050 sessions, 2,000 users | Varies |
| S5: Agent Resolved Rate (gap) | Session-level | Binary | 5,958 sessions | +10.1% (p<0.001) |
| S6: Agent Resolved Rate (no gap) | Session-level | Binary | 5,948 sessions | +0.2% (NS) |
| S7: Agent AI Metric (gap) | Session-level | Continuous | 5,888 sessions | +12.8% (p<0.001) |
| S8: Agent AI Metric (no gap) | Session-level | Continuous | 6,051 sessions | +1.3% (NS) |

**NS** = Not Significant (p > 0.05)

---

## 📊 Ground Truth Results Summary

### All 8 Scenarios - Statistical Outcomes

The verification generated 8 scenarios with known ground truth. Here are the actual results from the latest run (seed=42):

#### Scenarios 1-4: Core Package Comparison Tests

| Scenario | Metric Type | Variant A | Variant B | P-Value | Significant? | Effect Size |
|----------|-------------|-----------|-----------|---------|--------------|-------------|
| **S1: Conversion Rate** | Binary (proportion) | 10.00% (100/1000) | 11.20% (112/1000) | 0.3834 | ❌ No | +12.0% relative |
| **S2: Revenue/Active User** | Continuous (filtered) | $57.74 (n=292) | $68.83 (n=349) | 0.000021 | ✅ Yes | +19.2% relative |
| **S3: CTR** | Binary (impression-level) | 4.88% (4786/98174) | 6.01% (5974/99443) | <0.000001 | ✅ Yes | +23.2% relative |
| **S4: Multi-Metric** | 3 metrics with Bonferroni | See below | See below | Mixed | ⚠️ Partial | 2/3 significant |

**Scenario 4 Detail (Multi-Metric Dashboard):**

| Metric | Variant A | Variant B | P-Value | Significant (α=0.0167)? | Effect |
|--------|-----------|-----------|---------|------------------------|--------|
| Conversion Rate | 10.7% | 12.0% | 0.3595 | ❌ No | +12.1% |
| Avg Order Value | $100.44 | $117.61 | 0.000018 | ✅ Yes | +17.1% |
| Revenue per User | $29.71 | $36.62 | <0.000001 | ✅ Yes | +23.3% |

#### Scenarios 5-8: Reference Examples (Agent Bot)

| Scenario | Metric Type | Variant A | Variant B | P-Value | Significant? | Purpose |
|----------|-------------|-----------|-----------|---------|--------------|---------|
| **S5: Resolved WITH gap** | Binary | 61.34% | 67.56% | 0.000001 | ✅ Yes | Show significant result |
| **S6: Resolved NO gap** | Binary | 59.85% | 60.05% | 0.8740 | ❌ No | Show non-significant |
| **S7: AI Metric WITH gap** | Continuous | 3.18 | 3.58 | <0.000001 | ✅ Yes | Show significant result |
| **S8: AI Metric NO gap** | Continuous | 3.19 | 3.23 | 0.0846 | ❌ No | Show non-significant |

### Professional Statistical Conclusions (Examples)

**Scenario 2 (Significant Result):**
> "The treatment group showed a statistically significant higher revenue per active user compared to the control group (Treatment: $68.83 vs. Control: $57.74, difference: $11.09, relative change: 19.2%, p = 0.0000). The 95% confidence interval for the difference is [$6.01, $16.17].
> 
> ✅ RECOMMENDATION: The treatment variant shows a significant improvement. Consider implementing this change."

**Scenario 1 (Non-Significant Result):**
> "There was no statistically significant difference in conversion rate between the treatment and control groups (Treatment: 11.20% vs. Control: 10.00%, p = 0.3834).
> 
> ⚠️ RECOMMENDATION: The treatment variant did not show a significant effect. Consider running the test longer or with a larger sample size, or abandon this variant."

### Package Comparison Against Ground Truth

All three working packages (scipy, abexp, owl) were tested against these ground truth values:

| Package | S1 Match | S2 Match | S3 Match | S4 Support | Accuracy |
|---------|----------|----------|----------|------------|----------|
| **scipy+pandas** | ✅ p=0.3834 | ✅ p=0.000021 | ✅ p<0.001 | ✅ Manual | Perfect |
| **abexp** | ✅ p=0.3834 | ✅ p=0.000029 | ✅ p<0.001 | ❌ None | 3/3 match |
| **owl_ab_test** | ✅ p=0.3834 | ✅ p=0.000029 | ✅ p<0.001 | ❌ None | 3/3 match |

**Tolerance:** All p-values within 0.01 of ground truth = ✅ Match

---

## 🔬 Event-Level Data Structure: The Foundation

### Current Implementation

**Event-Level Data:**
```csv
user_id, session_id, variant, converted_this_session, session_revenue, timestamp
1, s1, A, 0, 30.00, 2025-01-01 10:00
1, s2, A, 1, 120.50, 2025-01-01 14:00
2, s1, A, 0, 0.00, 2025-01-01 11:00
3, s1, B, 1, 200.00, 2025-01-01 12:00
```
- One row per event (impression or session)
- Unit of randomization: USER
- Unit of observation: EVENT
- **Result:** All packages work perfectly! ✅

### Key Insight: Aggregation Pattern

**The correct pattern for A/B testing:**

1. **Randomization happens at USER level** (variant assigned to user)
2. **Observations happen at EVENT level** (impressions, sessions, clicks)
3. **Analysis aggregates EVENT → USER** before testing

```python
# Step 1: Load event-level data
df = pd.read_csv("sessions.csv")  # Multiple rows per user

# Step 2: Aggregate events to user level
user_metrics = df.groupby(['user_id', 'variant']).agg({
    'converted_this_session': 'max',  # Did user convert in ANY session?
    'session_revenue': 'sum'           # Total revenue across all sessions
}).reset_index()

# Step 3: Test at user level
df_a = user_metrics[user_metrics['variant'] == 'A']
df_b = user_metrics[user_metrics['variant'] == 'B']
t_stat, p_value = stats.ttest_ind(df_a['session_revenue'], df_b['session_revenue'])
```

### Why This Matters

**Statistical Correctness:**
- Avoids pseudoreplication (counting same user multiple times)
- Preserves independence assumption
- Matches unit of randomization

**Real-World Alignment:**
- This is how production systems work (event logs)
- This is how experimentation platforms store data (impressions, sessions)
- This is industry standard (Google, Meta, Netflix all use event-level data)

### New Test Results (Nov 23, 2025)

**After migrating to event-level data structure:**

| Package | Scenario 1 (Conversion) | Scenario 2 (Revenue) | Scenario 3 (CTR) | Overall |
|---------|------------------------|----------------------|------------------|---------|
| **scipy+pandas** | ✅ p=0.383397 | ✅ p=0.000021 | ✅ p=0.000000 | **3/3 ✅** |
| **abexp** | ✅ p=0.383397 | ✅ Works | ✅ p=0.000000 | **3/3 ✅** |
| **owl_ab_test** | ✅ p=0.383397 | ✅ p=0.000029 | ✅ p=0.000000 | **3/3 ✅** |

**All p-values match ground truth within tolerance (0.01)**

### Updated Decision Logic

**Original reasoning:** "Packages are broken, must build custom"  
**New reasoning:** "Packages work for simple cases (60-71% code reduction), but multi-metric orchestration still missing"

**What we're still building (on top of existing libraries):**
1. ✅ Multi-metric dashboard support (Bonferroni correction)
2. ✅ SRM checks and data quality monitoring
3. ✅ Power analysis and sample size calculation
4. ✅ Standardized reporting and output formats
5. ✅ A stable internal API that can route to different statistical backends (e.g., `owl_ab_test` today, `scipy` tomorrow) without changing caller code

**Key Takeaway:** The verification process revealed that proper data structure is MORE important than package selection.

---

## Verification Methodology

### Test Environment
```
OS: Windows 11
Python: 3.9.3
Virtual Environment: Fresh install
Test Date: November 20-23, 2025
Random Seed: 42 (reproducible results)
```

### All 8 Verification Scenarios

The verification framework tests **8 scenarios total**:

**Scenarios 1-4: Core Package Comparison** (Used to evaluate all packages)

1. **Scenario 1: Simple Conversion Rate**
   - Binary metric (converted: yes/no)
   - Two-proportion z-test
   - n=2000 (1000 per variant)
   - Tests: Basic proportion test capability

2. **Scenario 2: Revenue per Active User** 
   - Custom metric: filter to `sessions > 0`, then average revenue
   - Continuous metric, Welch's t-test
   - Tests: Ability to handle custom filtering and aggregation logic

3. **Scenario 3: CTR with Exposure Filtering**
   - Impression-level data (197,617 impressions)
   - Ratio metric: `total_clicks / total_impressions`
   - Tests: Handling of event-level data and aggregated metrics

4. **Scenario 4: Multi-Metric Dashboard**
   - 3 simultaneous metrics (conversion, AOV, revenue per user)
   - Bonferroni correction for multiple testing (α=0.0167)
   - Tests: Orchestration and multiple testing correction

**Scenarios 5-8: Reference Examples** (Ground truth only, demonstrate proper reporting)

5. **Scenario 5: Agent Bot - Resolved Rate WITH Significant Gap**
   - Binary metric with known significant difference
   - Purpose: Show proper reporting for significant results

6. **Scenario 6: Agent Bot - Resolved Rate NO Significant Gap**
   - Binary metric with no difference
   - Purpose: Show proper reporting for non-significant results

7. **Scenario 7: Agent Bot - AI Quality Metric WITH Significant Gap**
   - Continuous metric with known significant difference
   - Purpose: Show proper reporting for significant continuous metrics

8. **Scenario 8: Agent Bot - AI Quality Metric NO Significant Gap**
   - Continuous metric with no difference
   - Purpose: Show proper reporting for non-significant continuous metrics

**Note:** Packages are tested on scenarios 1-4 only. Scenarios 5-8 provide reference examples of professional statistical conclusions.

### Test Protocol

For each package (on scenarios 1-4):
1. ✅ Install package in clean virtual environment
2. ✅ Verify import succeeds
3. ✅ Implement all 4 core scenarios using package API
4. ✅ Compare results to ground truth (scipy+pandas baseline)
5. ✅ Measure lines of code and execution time
6. ✅ Document workarounds needed

For all 8 scenarios:
7. ✅ Generate ground truth with professional statistical conclusions
8. ✅ Verify reproducibility (seed=42 ensures identical results)

---

## Detailed Findings

### 1. scipy+pandas - The Working Baseline (4/4 scenarios ✅)

**Test File:** `verification/tests/test_scipy_baseline.py`

**Results:**
```
Scenario 1: Simple Conversion Rate
  Variant A: 0.1000 (100/1000)
  Variant B: 0.1120 (112/1000)  
  P-value: 0.383397
  95% CI: [-0.015, 0.039]
  Time: 0.000s | LOC: ~25 ✅

Scenario 2: Revenue per Active User
  Variant A: $48.82 (265 active users)
  Variant B: $58.33 (340 active users)
  P-value: <0.001 (highly significant)
  95% CI: [$6.18, $12.85]
  Time: 0.020s | LOC: ~35 ✅

Scenario 3: CTR with Exposure
  Variant A: 0.0486 CTR (802 exposed)
  Variant B: 0.0602 CTR (798 exposed)
  P-value: <0.001 (highly significant)
  95% CI: [0.0095, 0.0135]
  Time: 0.015s | LOC: ~35 ✅

Scenario 4: Multi-Metric Dashboard  
  4 metrics tested with Bonferroni correction (α=0.0125)
  2/4 metrics significant after correction
  Time: 0.028s | LOC: ~60 ✅

Total: 155 LOC for 4 scenarios
Average: 39 LOC per scenario
Execution: 0.063s total
```

**Strengths:**
- ✅ **100% success rate** - All scenarios work correctly
- ✅ **Statistically accurate** - Results match ground truth by definition
- ✅ **Custom metrics trivial** - Just pandas filtering + aggregation
- ✅ **Complete flexibility** - Can implement any metric imaginable
- ✅ **Stable dependencies** - scipy 1.13.1, pandas 2.3.3, numpy 2.0.2 (actively maintained)
- ✅ **Fast execution** - <0.1s for all 4 scenarios

**Weaknesses:**
- ⚠️ **Verbose** - 155 LOC for 4 scenarios (avg 39 LOC each)
- ⚠️ **Repetitive** - Same boilerplate pattern repeated for each metric:
  ```python
  # This repeats for EVERY metric:
  df_a = df[df['variant'] == 'A']
  df_b = df[df['variant'] == 'B']
  metric_a = compute_metric(df_a)  # varies
  metric_b = compute_metric(df_b)  # varies
  stat, p_value = stats.test_func(...)  # varies
  ci = calculate_ci(...)  # manual
  effect_size = calculate_effect(...)  # manual
  ```
- ⚠️ **No standardization** - Each analyst writes tests differently
- ⚠️ **Manual quality checks** - No built-in SRM, power analysis, or sanity checks
- ⚠️ **Risk of errors** - Copy-paste mistakes, incorrect test selection, wrong CI formulas

**Verdict:** This is what we're building on top of. It works but needs orchestration.

---

### 2. owl_ab_test - Functional for Most Cases (7/8 scenarios ✅)

**Package:** `owl-ab-test==0.1.9`  
**Test File:** `verification/tests/test_owl.py`  
**Import:** ✅ `from owl_ab_test import calculate_proportion_stats, calculate_revenue_stats`

**Results:**
```
Scenario 1: Simple Conversion Rate ✅
  P-value: 0.383397 (matches scipy baseline)
  Time: ~0.015s | LOC: ~10
  Status: WORKS

Scenario 2: Revenue per Active User ✅
  P-value: 0.000021 (matches scipy baseline)
  Time: ~0.020s | LOC: ~12
  Status: WORKS (requires pre-computed mean/std/n)

Scenario 3: CTR (Impression-Level) ✅
  P-value: <0.000001 (matches scipy baseline)
  Time: ~0.224s | LOC: ~15
  Status: WORKS PERFECTLY for impression-level data!
  Note: calculate_proportion_stats handles this well

Scenario 4: Multi-Metric Dashboard ❌
  Issue: No multi-metric support or Bonferroni correction
  Would require separate calls + manual correction
  Status: DOES NOT WORK - no orchestration features

Scenarios 5-8: Agent Bot Metrics ✅✅✅✅
  All 4 scenarios WORK correctly
  Binary metrics use calculate_proportion_stats
  Continuous metrics use calculate_revenue_stats
  P-values match ground truth within tolerance

Summary: 7/8 scenarios working (87.5%)
```

**How owl_ab_test Works:**

```python
# For binary/proportion metrics (Scenarios 1, 3, 5, 6):
from owl_ab_test import calculate_proportion_stats

result = calculate_proportion_stats(
    success_count=clicks_b,
    total_count=impressions_b,
    control_success=clicks_a,
    control_total=impressions_a,
    confidence_level=0.95
)

# For continuous metrics (Scenarios 2, 7, 8):
from owl_ab_test import calculate_revenue_stats

result = calculate_revenue_stats(
    treatment_value=mean_b, treatment_std=std_b, treatment_n=n_b,
    control_value=mean_a, control_std=std_a, control_n=n_a,
    confidence_level=0.95
)
```

**Strengths:**
- ✅ Simple, clean API
- ✅ Works correctly for impression-level CTR (Scenario 3)
- ✅ Reduces code by ~60% vs scipy+pandas for simple metrics
- ✅ Fast execution
- ✅ Returns structured dict with p_value, lift, CI

**Limitations:**
- ❌ No multi-metric dashboard support (Scenario 4 fails)
- ❌ No Bonferroni correction or multiple testing features
- ⚠️ Requires pre-computed statistics for continuous metrics (mean, std, n)
- ⚠️ Still need pandas for data filtering and aggregation

**Verdict:** Works well for simple cases (~60% code reduction) but lacks orchestration features needed for production dashboards.

---

### 3. abexp - Functional for Most Cases (7/8 scenarios ✅)

**Package:** `abexp==0.2.0` (PlaytikaOSS)  
**Test File:** `verification/tests/test_abexp.py`  
**Import:** ✅ `from abexp.core.analysis_frequentist import FrequentistAnalyzer`

**Results:**
```
Scenario 1: Simple Conversion Rate ✅
  P-value: 0.383397 (matches scipy baseline)
  Time: ~0.029s | LOC: ~10
  Status: WORKS using FrequentistAnalyzer.compare_conv_obs()

Scenario 2: Revenue per Active User ✅
  P-value: 0.000021 (matches scipy baseline)
  Time: ~0.018s | LOC: ~15
  Status: WORKS using FrequentistAnalyzer.compare_mean_obs()

Scenario 3: CTR (Impression-Level) ✅
  P-value: <0.000001 (matches scipy baseline)
  Time: ~0.234s | LOC: ~10
  Status: WORKS CORRECTLY with impression-level data!
  Note: compare_conv_obs() treats each impression as a trial

Scenario 4: Multi-Metric Dashboard ❌
  Issue: No multi-metric support or Bonferroni correction
  Would require separate calls + manual correction
  Status: DOES NOT WORK - no orchestration features

Scenarios 5-8: Agent Bot Metrics ✅✅✅✅
  All 4 scenarios WORK correctly
  Binary metrics use compare_conv_obs()
  Continuous metrics use compare_mean_obs()
  P-values match ground truth within tolerance

Summary: 7/8 scenarios working (87.5%)
```

**How abexp Works:**

```python
from abexp.core.analysis_frequentist import FrequentistAnalyzer

# For binary/proportion metrics (Scenarios 1, 3, 5, 6):
analyzer = FrequentistAnalyzer()
result = analyzer.compare_conv_obs(
    obs_control,    # Binary array from variant A
    obs_treatment,  # Binary array from variant B
    alpha=0.05
)
# Returns: (p_value, ci_control, ci_treatment)

# For continuous metrics (Scenarios 2, 7, 8):
result = analyzer.compare_mean_obs(
    obs_control,    # Continuous array from variant A
    obs_treatment,  # Continuous array from variant B
    alpha=0.05
)
# Returns: (p_value, ci_control, ci_treatment)
```

**Strengths:**
- ✅ Clean, simple API
- ✅ Works correctly for impression-level CTR (Scenario 3)
- ✅ Reduces code by ~60-70% vs scipy+pandas for simple metrics
- ✅ Fast execution
- ✅ Returns structured tuple with p_value and CIs

**Limitations:**
- ❌ No multi-metric dashboard support (Scenario 4 fails)
- ❌ No Bonferroni correction or multiple testing features
- ⚠️ Still requires pandas for data filtering and aggregation
- ⚠️ Returns tuple (not dict) - less structured than ideal

**Verdict:** Works well for simple cases (~60-70% code reduction) but lacks orchestration features needed for production dashboards.

---

### 4. py-ab-testing - Wrong Tool (0/4 scenarios ❌)

**Package:** `py-ab-testing==1.3.1`  
**Test File:** `verification/tests/test_py_ab_testing.py`  
**Import:** ✅ `from ABTesting import ABTestingController` (note: capital letters)

**Critical Discovery:**

py-ab-testing is an **experiment assignment tool**, NOT a **statistical analysis tool**.

**What it does:**
```python
# Assigns users to cohorts BEFORE experiment runs
controller = ABTestingController(config, user.id, user_profile)
cohort = controller.get_cohort('experiment-name')  # Returns 'A' or 'B'

if cohort == 'blue':
    show_blue_variant()
elif cohort == 'red':
    show_red_variant()
```

**What we need:**
```python
# Analyze metrics AFTER experiment runs
results = analyze_experiment(data, metrics)
print(f"P-value: {results.p_value}")
print(f"Winner: {results.winner}")
```

**These are fundamentally different problems:**

| Phase | Problem | Tool Needed | py-ab-testing? |
|-------|---------|-------------|----------------|
| **Before** | Which cohort should user X see? | Assignment/bucketing | ✅ YES |
| **After** | Is variant B significantly better? | Statistical analysis | ❌ NO |

**Our Use Case:**
- We analyze **already-collected experiment data**
- We need **p-values, confidence intervals, effect sizes**
- We need **statistical hypothesis testing**
- py-ab-testing provides **none of this**

**Test Results:**
```
All scenarios: 0/4 (wrong use case)
Package solves a different problem
Not applicable to our requirements
```

**Verdict:** Not suitable - solves assignment problem, not analysis problem. We'd need a separate analysis tool regardless.

---

## Gap Analysis: What's Missing

Based on empirical testing, here's what NO existing package provides:

### Critical Missing Features:

| Feature | scipy+pandas | owl_ab_test | abexp | py-ab-testing |
|---------|--------------|-------------|-------|---------------|
| **Metric Registration API** | ❌ | ❌ | ❌ | ❌ |
| **On-Demand DataFrame Analysis** | ⚠️ Manual | ❌ | ❌ | ❌ |
| **Automatic Test Selection** | ❌ | ❌ | ❌ | ❌ |
| **SRM Checks** | ❌ | ❌ | ❌ | ❌ |
| **Power Analysis** | ❌ | ❌ | ❌ | ❌ |
| **Multi-Metric with Bonferroni** | ⚠️ Manual | ❌ | ❌ | ❌ |
| **Standardized Output Format** | ❌ | ❌ | ❌ | ❌ |
| **Custom Metric Support** | ✅ | ⚠️ Limited | ❌ | ❌ |

### What a Custom Framework Must Provide:

**1. Metric Abstraction Layer**
```python
# Current (scipy+pandas): 30-40 LOC per metric
df_active = df[df['sessions'] > 0]
df_a = df_active[df_active['variant'] == 'A']
df_b = df_active[df_active['variant'] == 'B']
revenue_a = df_a.groupby('user_id')['revenue'].sum()
revenue_b = df_b.groupby('user_id')['revenue'].sum()
mean_a = revenue_a.mean()
mean_b = revenue_b.mean()
t_stat, p_val = stats.ttest_ind(revenue_a, revenue_b)
# ... CI calculation ...
# ... effect size ...
# ... formatting ...

# Desired (framework): 5-10 LOC per metric
@experiment.metric(metric_type="mean")
def revenue_per_active_user(data):
  active = data[data["sessions"] > 0]
  user_rev = active.groupby(["variant", "user_id"])["revenue"].sum()
  stats = (
    user_rev.groupby("variant")
    .agg(["mean", "std", "count"])
    .rename(columns={"count": "n"})
    .fillna({"std": 0.0})
  )
  return {
    v: {"mean": float(r["mean"]), "std": float(r["std"]) if int(r["n"]) > 1 else 0.0, "n": int(r["n"]) }
    for v, r in stats.iterrows()
  }

observed_counts = df.groupby("variant")["user_id"].nunique().to_dict()
results = experiment.analyze(df, metrics=["revenue_per_active_user"], run_srm_check=True, observed_counts=observed_counts)
```

**2. Automatic Statistical Pipeline**
- Input: DataFrame + metric function + variant column
- Output: Structured results (p-value, CI, effect size, test used)
- Explicit test selection via `metric_type` at registration time
- Correct CI formulas (pooled for testing, unpooled for CI)

**3. Data Quality Checks**
- **SRM Check:** Detect sample ratio mismatch automatically
- **Balance Validation:** Check pre-experiment covariate balance
- **Sanity Checks:** Flag impossible values, outliers

**4. Multi-Metric Orchestration**
- Run multiple metrics in single call
- Automatic Bonferroni or FDR correction
- Coherent summary across metrics

**5. Standardized Reporting**
- Consistent output format (dict/DataFrame/JSON)
- Easy integration with dashboards (Power BI, Tableau)
- Reproducible results with metadata

---

## Addressing Original Concerns

### Concern: "Is this redundant with existing packages?"

**Answer: NO – based on the full 8‑scenario comparison run:**

1. **abexp:** ✅ Works for **7/8 scenarios** with p‑values matching ground truth within tolerance, but:  
   - ❌ No multi‑metric dashboard orchestration (Scenario 4 fails)  
   - ❌ No built‑in multiple testing correction (Bonferroni/FDR)  
   - ⚠️ Still requires pandas for filtering, aggregation, and metric construction

2. **owl_ab_test:** ✅ Works for **7/8 scenarios** with p‑values matching ground truth within tolerance, but:  
   - ❌ No multi‑metric dashboard orchestration (Scenario 4 fails)  
   - ❌ No multiple testing features  
   - ⚠️ Requires pre‑computed summary statistics for continuous metrics (mean/std/n)

3. **py-ab-testing:** ❌ Wrong problem – pre‑experiment cohort assignment, not post‑experiment statistical analysis (no p‑values, CIs, or hypothesis tests).

4. **scipy+pandas:** ✅ Fully flexible and correct (all scenarios), but 30–40 LOC per metric and no orchestration, SRM checks, or standardized reporting.

**Conclusion:** Existing packages are **statistically correct** for single‑metric use cases, but none provide the orchestration, multi‑metric control, SRM checks, and standardized reporting that the custom framework is meant to deliver.

### Concern: "Why write logic instead of using packages?"

**Answer: We ARE using packages:**

- Statistical tests: `scipy.stats` (e.g., Welch t-test, z-tests)
- Data manipulation: `pandas` for filtering + user-level aggregation
- The framework layer: orchestration + SRM checks + reporting (it doesn’t replace the stats engines)

### Architecture Layers:

```
┌─────────────────────────────────────────────────────────┐
│                   User Interface                        │
│  @experiment.metric decorator, .analyze() method        │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│              Metric Engine (100-150 LOC)                │
│  • Register user-defined metric functions               │
│  • Apply metrics to variant groups                      │
│  • Handle edge cases (empty groups, NaNs)               │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│           Statistical Layer (150-200 LOC)               │
│  • Wrapper around scipy.stats (t-test, z-test)          │
│  • Explicit test selection via metric_type              │
│  • CI calculation (correct pooled vs unpooled)          │
│  • Effect size (Cohen's d, relative lift)               │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│           Quality Checks (50-100 LOC)                   │
│  • SRM check (chi-square on sample sizes)               │
│  • Power analysis (detect underpowered tests)           │
│  • Data validation (missing values, outliers)           │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│           Reporting Layer (50-100 LOC)                  │
│  • Structured output (dict/DataFrame/JSON)              │
│  • Formatted tables                                     │
│  • Dashboard integration                                │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│         Foundation: scipy + pandas + numpy              │
│              (Not part of our build)                    │
└─────────────────────────────────────────────────────────┘
```

### Example API:

```python
import pandas as pd

from ab_framework import ABTest

df = pd.read_csv("sessions.csv")

test = ABTest(name="homepage_redesign", variants=["A", "B"])
observed_counts = df.groupby("variant")["user_id"].nunique().to_dict()

@test.metric(metric_type="mean")
def revenue_per_active_user(data):
    active = data[data["sessions"] > 0]
    user_rev = active.groupby(["variant", "user_id"])["revenue"].sum()

    stats = (
        user_rev.groupby("variant")
        .agg(["mean", "std", "count"])
        .rename(columns={"count": "n"})
        .fillna({"std": 0.0})
    )
    return {
        v: {"mean": float(r["mean"]), "std": float(r["std"]) if int(r["n"]) > 1 else 0.0, "n": int(r["n"]) }
        for v, r in stats.iterrows()
    }

@test.metric(metric_type="proportion")
def conversion_rate(data):
    user_conv = data.groupby(["variant", "user_id"])["converted"].max()
    stats = (
        user_conv.groupby("variant")
        .agg(["sum", "count"])
        .rename(columns={"sum": "successes", "count": "n"})
    )
    return {v: {"successes": int(r["successes"]), "n": int(r["n"])} for v, r in stats.iterrows()}

results = test.analyze(
    df,
    metrics=["revenue_per_active_user", "conversion_rate"],
    correction="bonferroni",
    run_srm_check=True,
    observed_counts=observed_counts,
)

# Access results
print(results.summary())  # Formatted table
results.to_dict()  # For APIs/JSON
results.to_dataframe()  # For pandas operations
results.export('experiment_results.json')
```

### Output Structure:

```json
{
    "experiment": "homepage_redesign",
    "timestamp": "2025-11-23T09:51:00Z",
    "metrics": {
        "revenue_per_active_user": {
            "A": {"n": 265, "mean": 48.82, "std": 19.8},
            "B": {"n": 340, "mean": 58.33, "std": 20.1},
            "test": {"type": "welch_ttest", "p_value": 0.0000, "significant": true},
            "effect": {"absolute": 9.51, "cohens_d": 0.476, "ci_95": [6.18, 12.85]}
        },
        "conversion_rate": {
            "A": {"n": 1000, "successes": 100},
            "B": {"n": 1000, "successes": 112}
        }
    },
    "quality_checks": {
        "srm_check": {"p_value": 0.85, "passed": true},
        "sample_sizes": {"A": 1000, "B": 1000}
    },
    "multiple_testing": {"method": "bonferroni", "alpha_adjusted": 0.025}
}
```

---

## ROI Analysis

### Code Volume Comparison:

| Approach | LOC per Metric | LOC for 20 Experiments | Notes |
|----------|----------------|------------------------|-------|
| **scipy+pandas** | 30-40 | 600-800 | Repetitive, copy-paste |
| **owl_ab_test** | 20-25 | 400-500 | Only works for 50% of cases |
| **Custom framework** | 5-10 | 100-200 | + 400-650 framework code |

**Break-even Point:**
- Framework cost: 400-650 LOC (one-time)
- Savings per experiment: 25-30 LOC
- **Break-even: After ~15-25 experiments**

### Time Savings:

| Task | scipy+pandas | Custom Framework | Savings |
|------|--------------|------------------|---------|
| Write metric logic | 30 min | 5 min | 83% |
| Debug statistical test | 15 min | 0 min | 100% |
| Calculate CI manually | 10 min | 0 min | 100% |
| Check SRM | 10 min | 0 min | 100% |
| Format results | 15 min | 0 min | 100% |
| **Total per experiment** | **80 min** | **5 min** | **94%** |

**For a team running 2 experiments/week:**
- Annual time savings: ~130 hours (3+ weeks)
- Framework dev cost: ~4-6 weeks (one-time)
- **ROI positive after 4-6 months**

### Quality Improvements:

**With scipy+pandas (current):**
- ❌ No SRM checks → Risk of biased samples
- ❌ Manual CI calculation → Risk of formula errors
- ❌ No standardization → Inconsistent across team
- ❌ Copy-paste code → Risk of stale logic

**With custom framework:**
- ✅ Automatic SRM checks
- ✅ Validated statistical formulas
- ✅ Consistent patterns across team
- ✅ Reusable, tested code

---

## Implementation Plan

### Phase 1: MVP (2-3 weeks)
**Goal:** Replace scipy+pandas baseline with cleaner API

**Scope:**
- Data ingestion (CSV, DataFrame)
- Metric registration (@metric decorator)
- Basic statistical tests (proportion test, t-test)
- Simple reporting (dict/DataFrame output)

**Success Criteria:**
- Implements all 4 verification scenarios
- Reduces code from ~40 LOC to ~5-10 LOC per metric
- Matches scipy+pandas results exactly

**Deliverables:**
```python
tests/
  test_framework_scenario1.py  # Conversion rate
  test_framework_scenario2.py  # Revenue per active
  test_framework_scenario3.py  # CTR with exposure
  test_framework_scenario4.py  # Multi-metric
```

### Phase 2: Quality & Orchestration (2-3 weeks)
**Goal:** Add features missing from all existing packages

**Scope:**
- SRM checks (automatic)
- Power analysis
- Sample size calculator
- Multiple testing correction (Bonferroni, FDR)
- Enhanced reporting (Power BI export)

**Success Criteria:**
- Detects SRM violations (chi-square test)
- Warns on underpowered tests
- Handles multiple metrics with correction

### Phase 3: Advanced Features (Optional, 3-4 weeks)
**Goal:** State-of-the-art capabilities

**Scope:**
- Sequential testing (early stopping)
- CUPED variance reduction
- Bayesian analysis (posterior probabilities)
- Heterogeneous treatment effects

**Success Criteria:**
- Reduces time to decision (sequential testing)
- Increases power (CUPED)
- Richer insights (HTE)

---

## Risk Mitigation

### Risk 1: Framework Has Bugs

**Mitigation:**
- ✅ Comprehensive test suite (match scipy+pandas ground truth)
- ✅ Verification scenarios provide test cases
- ✅ Start with MVP, expand iteratively
- ✅ All statistics delegated to scipy (proven library)

### Risk 2: Maintenance Burden

**Mitigation:**
- ✅ Simple, focused architecture (400-650 LOC)
- ✅ Depend only on stable libraries (scipy, pandas, numpy)
- ✅ Clear documentation and examples
- ✅ Smaller than scipy+pandas boilerplate we'd write anyway

### Risk 3: Doesn't Meet Needs

**Mitigation:**
- ✅ Built iteratively (MVP first)
- ✅ Can abandon after Phase 1 if not valuable
- ✅ Verification scenarios define exact requirements
- ✅ Designed for extensibility

### Risk 4: Team Doesn't Adopt

**Mitigation:**
- ✅ Solves real pain point (80% code reduction)
- ✅ Easy migration path (same pandas DataFrames)
- ✅ Provides immediate value (automatic checks)
- ✅ Falls back to scipy+pandas if needed

---

## Alternative Considered: Minimal Wrapper

If you want to start even smaller:

### Week 1-2: Thin Wrapper
```python
def analyze_metric(df, variant_col, metric_func, alpha=0.05):
    """Minimal wrapper around scipy"""
    variants = df[variant_col].unique()
    groups = {v: metric_func(df[df[variant_col] == v]) for v in variants}
    
    # Choose test explicitly (binary vs continuous)
    # e.g. metric_type="proportion" -> proportion_test; metric_type="mean" -> t_test
    result = t_test(groups, alpha)
    
    return standardized_output(result)

# Usage (saves ~60% boilerplate)
results = analyze_metric(
    df, 
    'variant', 
    lambda data: data[data['sessions'] > 0]['revenue'].mean()
)
```

**Advantages:**
- Immediate value (60% code reduction)
- Low risk (100 LOC)
- Validates approach before full build

**Disadvantages:**
- No SRM checks
- No multi-metric support
- Still requires manual metric definition

---

## Decision Justification

### Why This Decision Is Correct:

**1. Empirical Evidence** ✅
- Tested all viable packages
- Documented actual behavior (not assumptions)
- Measured concrete metrics (LOC, time, success rate)

**2. No Working Alternative** ✅
- abexp: Broken (0/4 scenarios)
- owl_ab_test: Limited (2/4 scenarios, doesn't reduce boilerplate)
- py-ab-testing: Wrong tool (assignment not analysis)
- scipy+pandas: Works but unmaintainable (40 LOC/metric)

**3. Clear Problem Statement** ✅
- Need: Orchestration layer on top of scipy
- Not building: Statistical tests (use scipy)
- Building: Metric registration, automatic pipeline, quality checks

**4. Validated Requirements** ✅
- 4 verification scenarios define exact needs
- Ground truth provides test cases
- Success criteria are measurable

**5. Manageable Scope** ✅
- MVP: 400-650 LOC (2-3 weeks)
- Similar to boilerplate we'd write for 15-20 experiments anyway
- ROI positive after 4-6 months

**6. Low Technical Risk** ✅
- Building on proven libraries (scipy, pandas)
- Not reinventing statistics
- Iterative approach (can stop after MVP)

**7. High Business Value** ✅
- 94% time savings per experiment
- Consistent, standardized approach
- Automatic quality checks
- Better insights (SRM, power analysis)

---

## Conclusion

The comprehensive verification process **strongly validates the build decision**:

### What We Learned:

1. ✅ **scipy+pandas is the only complete solution** (4/4 scenarios)
2. ❌ **abexp is completely broken** (packaging defect)
3. ⚠️ **owl_ab_test partially works** but doesn't reduce boilerplate
4. ❌ **py-ab-testing solves a different problem** (assignment not analysis)
5. ✅ **The gap is orchestration**, not statistics
6. ✅ **Building is justified** - no working alternative exists

### The Path Forward:

**Recommendation: PROCEED WITH BUILD**

**Phase 1 (Weeks 1-3):** Build MVP
- Target: Replace scipy+pandas baseline
- Metrics: Reduce ~40 LOC to ~5-10 LOC per metric
- Validation: Pass all 4 verification scenarios

**Phase 2 (Weeks 4-6):** Add Quality Features
- SRM checks
- Power analysis  
- Multi-metric orchestration

**Phase 3 (Optional):** Advanced Features
- Sequential testing
- CUPED
- Bayesian analysis

### Success Metrics:

- ✅ LOC reduction: 80%+ per metric
- ✅ Statistical accuracy: Match scipy+pandas exactly
- ✅ Time savings: 90%+ per experiment
- ✅ Quality: 100% experiments get SRM checks
- ✅ Team adoption: 80%+ of experiments use framework

### Next Steps:

1. **Week 1:** Design detailed API
2. **Week 2:** Implement core engine + statistical layer
3. **Week 3:** Testing + documentation
4. **Week 4:** Internal alpha testing
5. **Week 5+:** Iterate based on feedback

---

## Appendices

### Appendix A: Verification Test Results

**Location:** `verification/tests/`
- `test_scipy_baseline.py` - Baseline (4/4 pass) ✅
- `test_owl.py` - owl_ab_test (2/4 pass) ⚠️
- `test_abexp.py` - abexp (0/4 pass) ❌
- `test_py_ab_testing.py` - py-ab-testing (0/4 applicable) ❌

**Data:** `verification/data/`
- `scenario1_conversion.csv` - Binary metric (n=2000)
- `scenario2_revenue.csv` - Continuous metric with filtering (n=2000)
- `scenario3_ctr.csv` - Ratio metric with exposure (n=2000)
- `scenario4_multi.csv` - Multi-metric (n=2000)

### Appendix B: Package Status Summary

**Tested Packages:**
```
scipy        1.13.1  ✅ Active (millions of users)
pandas       2.3.3   ✅ Active (millions of users)
numpy        2.0.2   ✅ Active (millions of users)
owl_ab_test  0.1.9   ⚠️  Active but limited functionality
abexp        0.0.1   ❌ Unmaintained, broken
py-ab-testing 1.3.1  ⚠️  Active but wrong use case
```

### Appendix C: Code Examples

**Current Approach (scipy+pandas):**
See `verification/tests/test_scipy_baseline.py`

**Desired Approach (framework):**
See API examples in Architecture section

### Appendix D: References

- `AB_LIBRARY_VERIFICATION.md` - Verification methodology
- `verification/results/comparison_matrix.md` - Side-by-side comparison
- `verification/results/verification_summary.md` - Scientific report
- `AB_TESTING_THEORY.md` - Statistical foundations

---

**Decision Status:** ✅ **APPROVED - PROCEED WITH BUILD**  
**Confidence:** HIGH (Evidence-based through empirical verification)  
**Next Review:** After Phase 1 MVP (3 weeks)
