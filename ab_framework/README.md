> Purpose: Package-level documentation for the ab_framework Python library (installation, usage, examples)
> Generated: Manually authored, maintained under version control.

# AB Testing Orchestration Framework

A production-ready A/B testing **orchestration and standardization layer** with pluggable statistical backends (currently `owl_ab_test`, with a `scipy` fallback planned), providing a clean, Pythonic API for experiment analysis.

## Features

✅ **Decorator-based metric registration** - Define metrics as simple Python functions  
✅ **Explicit metric types** - Declare binary vs continuous per metric  
✅ **Multi-metric orchestration** - Bonferroni and FDR correction for multiple testing  
✅ **SRM (Sample Ratio Mismatch) detection** - Automatic data quality checks  
✅ **Sample size calculation** - Pre-experiment power analysis via backend helper methods  
✅ **Flexible data sources** - Works with pandas DataFrames from any source  
✅ **Pluggable statistical backends** - Currently uses `owl_ab_test`, easily extensible (e.g., `scipy`)  
✅ **Rich reporting** - Markdown summaries, DataFrames, JSON exports

## Soft Monitoring Mode (Primary-Driven)

For most experiments, decisions should be driven by a single primary metric while additional metrics are monitored for context. The framework supports a soft monitoring mode where you:

- Designate exactly one metric as the primary via `is_primary=True`.
- Keep multiple-testing correction disabled for soft monitoring (`correction=None`).
- Optionally annotate monitor metrics with `inferiority_margin`, `monitor_alpha`, and `monitor_power` to display non-inferiority context in summaries.

Example:

```python
test = ABTest(name="checkout_redesign", variants=["A", "B"])

# SRM is explicit in stateless mode
observed_counts = df.groupby("variant")["user_id"].nunique().to_dict()

@test.metric(metric_type="proportion", is_primary=True, monitor_alpha=0.05, monitor_power=0.80)
def conversion_rate(data):
    user_level = data.groupby(["variant", "user_id"])["purchased"].max()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
    return out

@test.metric(metric_type="proportion", inferiority_margin=0.01, monitor_alpha=0.05, monitor_power=0.80)
def resolved_rate(data):
    # Example guardrail-like monitor (descriptive only in soft mode)
    user_level = data.groupby(["variant", "user_id"])["resolved"].max()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
    return out

results = test.analyze(
    df,
    run_srm_check=True,
    observed_counts=observed_counts,
    correction=None,
)

# Primary-driven decision helper
print(results.decision_soft_monitoring())

# Summary includes monitor settings and an NI Check (CI lower bound vs -inferiority_margin)
print(results.summary())
```

Notes:
- In soft monitoring, only the primary metric determines the decision; monitors are descriptive.
- Use `inferiority_margin` to show non-inferiority checks in the summary (no automatic blocking).
- Keep correction off (`None`) to avoid unnecessary power loss when the primary drives the decision.

## Installation

```bash
pip install pandas numpy scipy owl-ab-test
```

Then add the `ab_framework` directory to your project. The framework itself is backend‑agnostic; as long as a backend implements the expected interface, callers do not need to change.

## Quick Start

```python
from ab_framework import ABTest
import pandas as pd

# Load your experiment data
df = pd.read_csv('experiment_data.csv')

# Create test
test = ABTest(
    name="homepage_redesign",
    variants=["A", "B"],
)

# Register metrics using decorator
@test.metric(metric_type="proportion")
def conversion_rate(data):
    """User-level conversion rate."""
    user_level = data.groupby(["variant", "user_id"])["converted"].max()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
    return out

@test.metric(metric_type="mean")
def revenue_per_user(data):
    """Total revenue per user."""
    user_level = data.groupby(["variant", "user_id"])["revenue"].sum()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {
            "mean": float(v.mean()) if n else 0.0,
            "std": float(v.std(ddof=1)) if n > 1 else 0.0,
            "n": n,
        }
    return out

# Analyze with multi-metric correction
results = test.analyze(
    df,
    metrics=['conversion_rate', 'revenue_per_user'],
    run_srm_check=True,
    observed_counts=df.groupby("variant")["user_id"].nunique().to_dict(),
    correction='bonferroni'  # or 'fdr' or None
)

# View results
print(results.summary())
```

## Using Pre-Aggregated Daily Inputs (No Raw Logs)

The framework core is schema-agnostic: it does not require raw event logs as long as your
metric function can return the required per-variant summary stats.

If your upstream system already produces daily aggregates for a proportion metric, such as:

- `day`
- `rate_A`, `rate_B` (daily rates)
- `n_A`, `n_B` (daily denominators)

You can analyze either a single day or a cumulative window by converting rates into integer
success counts and then returning `{variant: {successes, n}}`.

Best practice: if you can, provide true integer `successes_A` / `successes_B` instead of
deriving them by rounding `rate * n`.

Note on output formatting: for proportion metrics the framework summary prints **SE** (standard error)
per variant rather than a raw “Std”, since for Bernoulli outcomes the per-row standard deviation
($\sqrt{p(1-p)}$) is usually less interpretable than the sampling uncertainty of the estimated rate.

```python
import pandas as pd
from ab_framework import ABTest

df_daily = pd.DataFrame({
    "day": ["2026-01-01", "2026-01-02"],
    "rate_A": [0.100, 0.098],
    "rate_B": [0.106, 0.105],
    "n_A": [10000, 12000],
    "n_B": [10000, 12000],
})

# Convert rates to integer successes (prefer true counts if available)
df_daily["successes_A"] = (df_daily["rate_A"] * df_daily["n_A"]).round().astype(int)
df_daily["successes_B"] = (df_daily["rate_B"] * df_daily["n_B"]).round().astype(int)

test = ABTest(name="agg_daily_example", variants=["A", "B"])

@test.metric(metric_type="proportion", is_primary=True)
def conversion_rate_from_daily(data: pd.DataFrame):
    # Analyze the entire window in `data` (sum across days)
    return {
        "A": {"successes": int(data["successes_A"].sum()), "n": int(data["n_A"].sum())},
        "B": {"successes": int(data["successes_B"].sum()), "n": int(data["n_B"].sum())},
    }

observed_counts = {"A": int(df_daily["n_A"].sum()), "B": int(df_daily["n_B"].sum())}
results = test.analyze(
    df_daily,
    metrics=["conversion_rate_from_daily"],
    run_srm_check=True,
    observed_counts=observed_counts,
    correction=None,
)

print(results.summary())
```

## Core Concepts

### 1. Metric Functions

Metric functions take the raw DataFrame and return **per-variant summary stats**.
The core stays schema-agnostic; your metric function is allowed to be schema-aware.

```python
@test.metric(metric_type="proportion")
def conversion_rate(data):
    # User-level conversion → per-variant successes / n
    user_level = data.groupby(["variant", "user_id"])["converted"].max()
    return {
        "A": {"successes": int(user_level.loc["A"].sum()), "n": int(user_level.loc["A"].shape[0])},
        "B": {"successes": int(user_level.loc["B"].sum()), "n": int(user_level.loc["B"].shape[0])},
    }

@test.metric(metric_type="mean")
def revenue_per_active_user(data):
    # Aggregation + filtering example
    user_revenue = data.groupby(["variant", "user_id"])["revenue"].sum()
    out = {}
    for variant in ["A", "B"]:
        v = user_revenue.loc[variant]
        v = v[v > 0]
        n = int(v.shape[0])
        out[variant] = {
            "mean": float(v.mean()) if n else 0.0,
            "std": float(v.std(ddof=1)) if n > 1 else 0.0,
            "n": n,
        }
    return out

@test.metric(metric_type="mean")
def avg_session_duration(data):
    # Continuous metric
    user_level = data.groupby(["variant", "user_id"])["session_seconds"].mean()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant]
        n = int(v.shape[0])
        out[variant] = {
            "mean": float(v.mean()) if n else 0.0,
            "std": float(v.std(ddof=1)) if n > 1 else 0.0,
            "n": n,
        }
    return out
```

### 2. Metric Type Selection

You must declare the metric type at registration time:
- **Binary metrics** → `metric_type="proportion"`
- **Continuous metrics** → `metric_type="mean"`

### 3. Multi-Metric Testing

When analyzing multiple metrics, use correction to control family-wise error rate:

```python
results = test.analyze(
    metrics=['conversion', 'revenue', 'engagement'],
    correction='bonferroni'  # Adjusted α = 0.05/3 = 0.0167
)
```

Options:
- `'bonferroni'` - Conservative, controls FWER
- `'fdr'` - Benjamini-Hochberg, controls false discovery rate
- `None` - No correction (not recommended for multiple metrics)

## Working with Multiple Metrics

When running experiments, you typically track several metrics with different purposes. Understanding these roles helps make clear, confident decisions.

**Important convention – MDE and lift are cumulative:** throughout this documentation, the "Minimum Detectable Effect" (MDE) and the reported "lift" for a metric refer to the **overall effect on the full experiment window** (all data from day 1 up to the analysis time), not to per‑day effects. You are free to plot per‑day rates and p‑values for monitoring and diagnostics, but the formal hypothesis tests and planning math are always about the **cumulative difference between variants over the chosen window**.

### Metric Roles

#### Primary Metric (What You Want to Improve)
- The **main success metric** for your experiment
- Must show statistically significant improvement to ship
- **Recommendation: Use exactly ONE primary metric per experiment**
- Examples: `conversion_rate`, `revenue_per_user`, `engagement_score`

**Why one primary?**
- Clear decision criteria (ship if primary improves)
- Maintains statistical power at designed level
- Avoids confusion when metrics conflict
- Simplifies communication with stakeholders

#### Guardrail Metrics (What You Must Not Harm)
- **Safety checks** - metrics that must not degrade significantly
- If any guardrail violated → DO NOT SHIP (even if primary wins)
- Examples: `error_rate`, `page_load_time`, `user_satisfaction`, `revenue_per_order`
- **Recommendation: Use 2-5 guardrails**

**Purpose:**
- Prevent optimizing one metric at the expense of user experience
- Catch unintended negative side effects
- Protect business-critical metrics
- Maintain long-term product health

#### Diagnostic Metrics (For Understanding)
- **Informational only** - help explain WHY the change worked
- Do not block shipping decisions
- Examples: `funnel_steps`, `feature_usage`, `session_depth`, `time_to_first_action`
- **Use freely for learning and iteration**

**Purpose:**
- Understand mechanism of change
- Generate hypotheses for future experiments
- Identify opportunities for optimization
- Build institutional knowledge

### Example: Clear Metric Hierarchy

```python
from ab_framework import ABTest

test = ABTest(name="checkout_redesign", variants=["A", "B"])
observed_counts = df.groupby("variant")["user_id"].nunique().to_dict()

# PRIMARY: What we're trying to improve
@test.metric(metric_type="proportion")
def conversion_rate(data):
    """PRIMARY - Main success metric"""
    user_level = data.groupby(["variant", "user_id"])["purchased"].max()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
    return out

# GUARDRAILS: What we must not harm
@test.metric(metric_type="mean")
def revenue_per_order(data):
    """GUARDRAIL - Ensure we don't reduce order value"""
    orders = data[data['purchased'] == 1]
    user_level = orders.groupby(["variant", "user_id"])["order_value"].sum() if not orders.empty else pd.Series(dtype=float)
    out = {}
    for variant in ["A", "B"]:
        if isinstance(user_level, pd.Series) and not user_level.empty and variant in user_level.index.get_level_values(0):
            v = user_level.loc[variant]
        else:
            v = pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {"mean": float(v.mean()) if n else 0.0, "std": float(v.std(ddof=1)) if n > 1 else 0.0, "n": n}
    return out

@test.metric(metric_type="mean")
def page_load_time(data):
    """GUARDRAIL - Ensure performance doesn't degrade"""
    user_level = data.groupby(["variant", "user_id"])["load_time"].mean()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {"mean": float(v.mean()) if n else 0.0, "std": float(v.std(ddof=1)) if n > 1 else 0.0, "n": n}
    return out

@test.metric(metric_type="mean")
def user_satisfaction(data):
    """GUARDRAIL - Protect user experience"""
    user_level = data.groupby(["variant", "user_id"])["satisfaction_score"].mean()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {"mean": float(v.mean()) if n else 0.0, "std": float(v.std(ddof=1)) if n > 1 else 0.0, "n": n}
    return out

# DIAGNOSTICS: For understanding behavior
@test.metric(metric_type="proportion")
def cart_abandonment(data):
    """DIAGNOSTIC - Understand funnel behavior"""
    added = data.groupby(["variant", "user_id"])["added_to_cart"].max()
    purchased = data.groupby(["variant", "user_id"])["purchased"].max()
    out = {}
    for variant in ["A", "B"]:
        if variant in added.index.get_level_values(0) and variant in purchased.index.get_level_values(0):
            v_added = added.loc[variant]
            v_purchased = purchased.loc[variant]
            abandoned = ((v_added == 1) & (v_purchased == 0)).astype(int)
        else:
            abandoned = pd.Series(dtype=int)
        out[variant] = {"successes": int(abandoned.sum()) if not abandoned.empty else 0, "n": int(abandoned.shape[0])}
    return out

@test.metric(metric_type="mean")
def checkout_page_views(data):
    """DIAGNOSTIC - Track engagement"""
    user_level = data.groupby(["variant", "user_id"])["checkout_views"].sum()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {"mean": float(v.mean()) if n else 0.0, "std": float(v.std(ddof=1)) if n > 1 else 0.0, "n": n}
    return out

# Analyze all metrics with correction
results = test.analyze(
    df,
    metrics=[
        'conversion_rate',      # Primary
        'revenue_per_order',    # Guardrail
        'page_load_time',       # Guardrail
        'user_satisfaction',    # Guardrail
        'cart_abandonment',     # Diagnostic
        'checkout_page_views'   # Diagnostic
    ],
    run_srm_check=True,
    observed_counts=observed_counts,
    correction='bonferroni'  # Apply correction for multiple testing
)

# Manual decision framework
primary = results.metric_results['conversion_rate']
guardrails = ['revenue_per_order', 'page_load_time', 'user_satisfaction']

# Check primary improved
primary_wins = primary['significant'] and primary['lift'] > 0

# Check guardrails safe (no significant degradation)
guardrails_safe = all([
    not (results.metric_results[g]['significant'] and 
         results.metric_results[g]['lift'] < 0)
    for g in guardrails
])

# Decision
if primary_wins and guardrails_safe:
    print("✅ SHIP - Primary improved, all guardrails safe")
    print(f"   Conversion: +{primary['lift']:.1%} (p={primary['p_value']:.4f})")
    
    # Review diagnostics for learning
    cart_aband = results.metric_results['cart_abandonment']
    print(f"   Cart abandonment: {cart_aband['lift']:+.1%} (diagnostic)")
elif primary_wins and not guardrails_safe:
    print("⚠️  DO NOT SHIP - Guardrails violated")
    print(f"   Primary improved, but negative side effects detected")
else:
    print("❌ DO NOT SHIP - Primary did not improve significantly")
```

### Decision Framework

**Conservative (Recommended):**
```
Ship if:
  ✓ Primary metric shows significant improvement (p < 0.05)
  AND
  ✓ No guardrail shows significant degradation (p < 0.05, lift < 0)
  
Diagnostic metrics are reviewed but don't block decisions.
```

**Aggressive (Use with Caution):**
```
Ship if:
  ✓ Primary metric shows significant improvement
  
Ignore guardrail warnings (only for low-risk experiments).
```

### Warning: Multiple Primary Metrics

⚠️ **Using multiple primary metrics significantly increases:**
- Required sample size (2-3x larger)
- Experiment duration (2-3x longer)
- Decision complexity (conflicting signals)
- Risk of Type I errors (false positives)

**Statistical Impact:**
```python
# Single primary metric
n_single = 1,000 per variant
power = 80%
alpha = 0.05

# Two primary metrics (both must improve)
n_both = 2,500 per variant  # 2.5x larger!
power = 80% × 80% = 64%     # Reduced power
# OR need to increase sample size to maintain 80% joint power

# Two primary metrics (either can improve)
alpha_family = 1 - (1-0.05)² ≈ 0.0975  # Nearly 10% false positive rate!
# Need Bonferroni: α = 0.05/2 = 0.025 per metric
```

**Only use multiple primaries when:**
- You TRULY need to improve multiple metrics simultaneously
- You're willing to collect 2-3x more data
- You have clear logic for handling conflicts (both must improve? either can improve?)
- Example: "Improve conversion AND reduce infrastructure cost"

**Example with Multiple Primaries:**

```python
# ⚠️ Advanced: Multiple primaries (use sparingly)
primary_metrics = ['conversion_rate', 'revenue_per_user']

results = test.analyze(
    metrics=primary_metrics + guardrails,
    correction='bonferroni'  # Critical for multiple primaries!
)

# Decision: BOTH must show significant improvement
both_improved = all([
    results.metric_results[m]['significant'] and 
    results.metric_results[m]['lift'] > 0
    for m in primary_metrics
])

if both_improved:
    print("✅ SHIP - Both primaries improved")
else:
    print("❌ DO NOT SHIP - Not all primaries improved")
    for m in primary_metrics:
        result = results.metric_results[m]
        status = "✅" if result['significant'] else "❌"
        print(f"   {status} {m}: {result['lift']:+.1%} (p={result['p_value']:.4f})")
```

### Best Practices Summary

1. **One Primary Metric** - Clear success criterion, maintains statistical power
2. **2-5 Guardrails** - Protect critical metrics without over-constraining
3. **Multiple Diagnostics** - Learn freely without impacting decisions
4. **Apply Corrections** - Use `correction='bonferroni'` or `'fdr'` for multiple metrics
5. **Document Roles** - Make it clear which metrics are primary/guardrail/diagnostic
6. **Pre-Register** - Decide metric roles BEFORE looking at results

### 4. SRM Checks (Sample Ratio Mismatch Detection)

**What is SRM?**

Sample Ratio Mismatch (SRM) occurs when the actual distribution of users across variants differs significantly from the expected allocation. This is a critical data quality check that runs automatically before analyzing metrics.

**The Chi-Square Test:**

SRM uses a chi-square (χ²) goodness-of-fit test to compare observed vs. expected counts:

```
χ² = Σ [(observed - expected)² / expected]

For 2 variants:
χ² = [(n_control - E_control)² / E_control] + [(n_treatment - E_treatment)² / E_treatment]

Then convert χ² to p-value with 1 degree of freedom
```

**Example:**
```python
# Expected 50/50 split with 1000 users
Expected: 500 control, 500 treatment

# Observed 450 control, 550 treatment
χ² = (450-500)²/500 + (550-500)²/500 = 10.0
p-value ≈ 0.0016

Since p < 0.001 → SRM DETECTED ⚠️
```

**Why alpha=0.001 for SRM (not 0.05)?**
- Metric tests use α=0.05 (5% false positive rate)
- SRM uses α=0.001 (0.1% false positive rate) - much stricter
- We only want to flag SRM when extremely confident something is broken
- This prevents false alarms from normal traffic variation

**Framework Usage:**

```python
from ab_framework import ABTest

# Flexible traffic allocation
test = ABTest(name="homepage_redesign", variants=["A", "B"])

# Configure expected allocation for SRM expectations
test.setup(treatment_fraction=0.3)  # 30% treatment / 70% control

# SRM check runs automatically by default
results = test.analyze(
    df,
    metrics=['conversion_rate'],
    observed_counts=df.groupby("variant")["user_id"].nunique().to_dict(),
    run_srm_check=True  # Default
)

# Check SRM result
if not results.srm_result['passed']:
    print("⚠️ SRM DETECTED - DO NOT TRUST RESULTS")
    print(results.srm_result['recommendation'])
    # Example output:
    # [WARNING] SRM DETECTED (p=0.000123, alpha=0.001)
    # Variant B deviates by +15.2%
    # Action: Check randomization logic and data collection
    
# Detailed SRM information
print(f"P-value: {results.srm_result['p_value']}")
print(f"Chi-square: {results.srm_result['chi_square']}")
print(f"Observed: {results.srm_result['observed']}")
print(f"Expected: {results.srm_result['expected']}")
print(f"Deviations: {results.srm_result['deviations_pct']}")
```

**Traffic Allocation Options (configured via `setup`)**

```python
# 50/50 split (default)
test1 = ABTest(name="test1", variants=["A", "B"])
test1.setup(treatment_fraction=0.5)

# 70/30 split (70% control, 30% treatment)
test2 = ABTest(name="test2", variants=["A", "B"])
test2.setup(treatment_fraction=0.3)

# 90/10 split for high-risk changes
test3 = ABTest(name="test3", variants=["A", "B"])
test3.setup(treatment_fraction=0.1)

# Equal split (when treatment_fraction is left as None)
test4 = ABTest(name="test4", variants=["A", "B"])  # Assumes 50/50 in SRM expectations
```

**When SRM is Detected:**

1. **STOP** - Do not trust any metric results
2. **Investigate** - Common causes:
   - Buggy randomization logic
   - Data pipeline filtering bias
   - Technical issues (bot traffic, cache issues)
   - Variant-specific crashes or errors
3. **Fix** - Correct the root cause
4. **Restart** - Begin a new experiment after validation

## Advanced Usage

### Phase 0: A/A Testing (Infrastructure Validation)

Before running your actual A/B test, validate your infrastructure with an A/A test:

```python
from ab_framework import ABTest
import pandas as pd

# Generate A/A test data (both groups get same treatment)
# Run for 7 days with normal production traffic
aa_data = load_experiment_data(start_date='2024-01-01', days=7)

aa_test = ABTest(
    name="infrastructure_validation",
    variants=["A", "B"],
)

@aa_test.metric(metric_type="mean")
def key_metric(data):
    user_level = data.groupby(["variant", "user_id"])["metric_value"].mean()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {"mean": float(v.mean()) if n else 0.0, "std": float(v.std(ddof=1)) if n > 1 else 0.0, "n": n}
    return out

aa_results = aa_test.analyze(
    aa_data,
    metrics=["key_metric"],
    run_srm_check=True,
    observed_counts=aa_data.groupby("variant")["user_id"].nunique().to_dict(),
)

# Check A/A test results
if aa_results.metric_results['key_metric']['significant']:
    print("❌ A/A TEST FAILED!")
    print("Found significant difference when there should be none.")
    print("DO NOT PROCEED - Fix infrastructure first!")
else:
    print("✅ A/A TEST PASSED!")
    print(f"Baseline mean: {aa_results.metric_results['key_metric']['control_value']:.3f}")
    print(f"Observed std: {aa_results.metric_results['key_metric']['std_pooled']:.3f}")
    print("Ready to proceed with A/B test")
```

**What A/A Testing Validates:**

1. ✅ **Randomization works correctly** - No Sample Ratio Mismatch
2. ✅ **Metric collection is accurate** - No systematic bias
3. ✅ **No implementation bugs** - Would cause spurious differences
4. ✅ **Actual variance estimate** - For accurate sample size calculation

### Monitoring Experiments Over Time

**Recommended Time-Series Visualizations:**

When running multi-day experiments, track these three key graphs:

#### 1. SRM History (Randomization Quality Over Time)
```python
# Track Treatment/Control ratio per day
# Y-axis: Observed T/C ratio (e.g., 1.0 for 50/50, 0.43 for 30/70)
# X-axis: Experiment day

for day in experiment_days:
    day_data = df[df['day'] == day]
    n_control = day_data[day_data['variant'] == 'A']['user_id'].nunique()
    n_treatment = day_data[day_data['variant'] == 'B']['user_id'].nunique()
    
    ratio = n_treatment / n_control
    expected_ratio = treatment_fraction / (1 - treatment_fraction)
    
    # Calculate 95% CI for the ratio
    # Plot: dot at observed ratio, error bar for CI
    # Color: green if CI crosses expected, red if SRM detected
```

**Interpretation:**
- Green dots: Randomization working correctly
- Red dots: SRM detected → STOP and investigate
- Horizontal dashed line: Expected ratio from your allocation

#### 2. Metric Value Over Time
```python
# Track control vs treatment metric values per day
# Y-axis: Metric value (e.g., conversion rate, revenue)
# X-axis: Experiment day

for day in experiment_days:
    day_data = df[df['day'] == day]
    control_metric = calculate_metric(day_data[day_data['variant'] == 'A'])
    treatment_metric = calculate_metric(day_data[day_data['variant'] == 'B'])
    
    # Plot both lines
    # Control: dashed line
    # Treatment: solid line
```

**Interpretation:**
- Shows when treatment effect stabilizes
- Identifies temporal trends or day-of-week effects  
- Helps determine if experiment duration is sufficient
- Can reveal learning effects or novelty effects

#### 3. P-Value Over Time
```python
# Track statistical significance progression
# Y-axis: P-value (log scale recommended)
# X-axis: Experiment day

for day in range(1, max_day + 1):
    cumulative_data = df[df['day'] <= day]
    test = ABTest(name=f"day_{day}", variants=["A", "B"])
    results = test.analyze(cumulative_data, metrics=["conversion_rate"], run_srm_check=False)
    
    p_value = results.metric_results['conversion_rate']['p_value']
    # Plot with horizontal line at alpha (e.g., 0.05)
```

**Interpretation:**
- Shows if/when experiment reaches significance
- Prevents premature stopping decisions
- Identifies if effect size is stable or volatile
- p-value crossing alpha = statistical significance achieved

**Example Visualization Code:**

```python
import matplotlib.pyplot as plt
import pandas as pd

def plot_experiment_progress(df, metric_name, treatment_fraction=0.5):
    """Generate 3 monitoring graphs for experiment tracking.

    treatment_fraction: treatment allocation (fraction of traffic sent to treatment).
    """
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # Graph 1: SRM History
    ax1 = axes[0]
    expected_ratio = treatment_fraction / (1 - treatment_fraction)
    
    days = []
    ratios = []
    ci_lower = []
    ci_upper = []
    
    for day in df['day'].unique():
        day_data = df[df['day'] == day]
        n_c = day_data[day_data['variant'] == 'A']['user_id'].nunique()
        n_t = day_data[day_data['variant'] == 'B']['user_id'].nunique()
        ratio = n_t / n_c
        
        days.append(day)
        ratios.append(ratio)
        # Calculate CI (simplified)
        ci_lower.append(ratio - 0.2)
        ci_upper.append(ratio + 0.2)
    
    ax1.errorbar(days, ratios, yerr=[ratios - ci_lower, ci_upper - ratios])
    ax1.axhline(expected_ratio, linestyle='--', color='blue', label='Expected')
    ax1.set_title('SRM Check History')
    ax1.set_ylabel('Treatment/Control Ratio')
    ax1.legend()
    
    # Graph 2: Metric Value Over Time  
    ax2 = axes[1]
    control_values = []
    treatment_values = []
    
    for day in df['day'].unique():
        day_data = df[df['day'] == day]
        control_values.append(
            day_data[day_data['variant'] == 'A'][metric_name].mean()
        )
        treatment_values.append(
            day_data[day_data['variant'] == 'B'][metric_name].mean()
        )
    
    ax2.plot(days, control_values, 'o--', label='Control')
    ax2.plot(days, treatment_values, 'o-', label='Treatment')
    ax2.set_title(f'{metric_name} Over Time')
    ax2.set_ylabel('Metric Value')
    ax2.legend()
    
    # Graph 3: P-Value Over Time
    ax3 = axes[2]
    p_values = []
    
    for day in range(1, len(days) + 1):
        cumulative_data = df[df['day'] <= day]
        # Calculate p-value for cumulative data
        # (simplified - actual implementation would use ABTest)
        p_values.append(0.05)  # Placeholder
    
    ax3.plot(range(1, len(days) + 1), p_values, 'o-')
    ax3.axhline(0.05, linestyle='--', color='red', label='α=0.05')
    ax3.set_title('P-Value Over Time')
    ax3.set_ylabel('P-Value')
    ax3.set_xlabel('Experiment Day')
    ax3.legend()
    
    plt.tight_layout()
    plt.show()
```

**A/A Test Duration Guidelines:**

| Daily Traffic | Recommended Duration | Rationale |
|--------------|---------------------|-----------|
| < 50 conversations/day | 10-14 days | Need more time to collect 300+ per variant |
| 50-100 conversations/day | 7-10 days | Standard duration for weekly patterns |
| 100-200 conversations/day | 7 days | Sufficient samples + full week |
| 200+ conversations/day | 3-7 days | High volume allows shorter validation |

**Key Principles:**

- **Minimum:** 300-500 samples per variant for reliable variance estimation
- **Weekly cycle:** At least 7 days to capture day-of-week effects
- **Converged variance:** Continue until variance estimate stabilizes

**Example: What "Success" Looks Like**

```
A/A Test Results (7 days):
  - Control: 3.199 (n=265)
  - Treatment: 3.222 (n=277)  
  - Lift: 0.69%
  - P-value: 0.7506 ✅ (NOT significant - this is good!)
  - Difference: 0.022 (negligible, not significant)
  
✅ This is PERFECT - no difference detected when both get same treatment
```

**What "Failure" Looks Like**

```
A/A Test Results (7 days):
  - Control: 3.200 (n=240)
  - Treatment: 3.510 (n=360)
  - Lift: 9.7%  
  - P-value: 0.0001 ❌ (Significant - should not be!)
  - SRM: ❌ DETECTED (expected 50/50, got 40/60)
  
❌ FAILED - indicates randomization bug or metric collection bias
DO NOT PROCEED until fixed!
```

**Using A/A Test Parameters for A/B Sample Size:**

```python
# Extract actual parameters from A/A test
baseline_mean = aa_results.metric_results['key_metric']['control_value']
baseline_std = aa_results.metric_results['key_metric']['std_pooled']

from ab_framework import ABTest

planning_test = ABTest(
    name="planning_only",
)

sample_plan = planning_test.backend.sample_size_mean(
    baseline_mean=baseline_mean,  # From A/A test (more accurate!)
    baseline_std=baseline_std,    # From A/A test (more accurate!)
    mde=0.07,                     # Business requirement
    alpha=0.05,
    power=0.80,
)

print(f"Need {sample_plan['total_size']:,} users for A/B test")
```

**Important Notes:**

1. **A/A test p-value SHOULD be > 0.05** - This means no difference (good!)
2. **Small observed lift (< 2-3%) is normal** - Random noise is expected
3. **SRM check must pass** - If not, fix randomization before A/B test
4. **Use A/A variance** - More accurate than historical estimates

### Pre-Experiment: Sample Size Calculation

```python
from ab_framework import ABTest

planning_test = ABTest(
    name="planning_only",
)

# For conversion rates
result = planning_test.backend.sample_size_proportion(
    baseline_rate=0.10,  # Current 10% conversion
    mde=0.05,            # Want to detect 5% relative lift
    alpha=0.05,
    power=0.80,
)
print(f"Need {result['total_size']:,} users")
# Output: Need 115,528 users

# For continuous metrics (revenue, time, etc.)
result = planning_test.backend.sample_size_mean(
    baseline_mean=50.0,    # $50 average
    baseline_std=25.0,     # $25 std dev
    mde=0.10,              # Detect 10% lift
    alpha=0.05,
    power=0.80,
)
print(f"Need {result['total_size']:,} users")
# Output: Need 1,570 users
```

### Manual SRM Check

```python
from ab_framework import QualityChecker

checker = QualityChecker()
result = checker.check_srm(
    observed_counts={'A': 10523, 'B': 9477},
    alpha=0.001  # More stringent than experiment alpha
)

if not result['passed']:
    print(result['recommendation'])
    # ⚠️ SRM DETECTED (p=0.000000, α=0.001)
    # Variant A deviates by +5.2%
    # Action: Check randomization logic
```

### Data Quality Checks

```python
checker = QualityChecker()
result = checker.check_data_quality(
    df=experiment_data,
    metrics=['conversion', 'revenue'],
    missing_threshold=0.05,   # Flag if >5% missing
    outlier_threshold=0.01    # Flag if >1% outliers
)

if not result['passed']:
    print('\n'.join(result['issues']))
```

### Export Results

```python
# Markdown summary
print(results.summary())

# Statistical conclusion (plain English)
print(results.conclusion('conversion_rate'))

# Dictionary for JSON
data = results.to_dict()

# DataFrame for further analysis
df = results.to_dataframe()
df.to_csv('experiment_results.csv')
```

### Statistical Conclusions

The framework generates clear, actionable conclusions in plain English:

**For significant results:**
```
STATISTICAL CONCLUSION
The treatment group showed a statistically significant higher click 
through rate compared to the control group (Treatment: 6.01% vs. 
Control: 4.88%, difference: 1.13 percentage points, relative change: 
23.2%, p = 0.0000).
The 95% confidence interval for the difference is [19.13%, 27.33%].
```

**For non-significant results:**
```
STATISTICAL CONCLUSION
There was no statistically significant difference in conversion rate 
between the treatment and control groups (Treatment: 11.20% vs. 
Control: 10.00%, p = 0.3834).

⚠️  RECOMMENDATION: The treatment variant did not show a significant 
effect. Consider running the test longer or with a larger sample size, 
or abandon this variant.
```

### Programmatic Metric Registration (Without `@` Syntax)

If you can't use `@test.metric(...)` as a decorator, you can still register metrics by calling it directly:

```python
def my_metric(data):
    user_level = data.groupby(["variant", "user_id"])["value"].sum()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {"mean": float(v.mean()) if n else 0.0, "std": float(v.std(ddof=1)) if n > 1 else 0.0, "n": n}
    return out

test.metric(metric_type="mean")(my_metric)
```

## Real-World Examples

### Example 1: E-commerce Checkout Flow

```python
test = ABTest(name="checkout_v2", variants=["A", "B"])
observed_counts = df.groupby("variant")["user_id"].nunique().to_dict()

@test.metric(metric_type="proportion")
def conversion_rate(data):
    user_level = data.groupby(["variant", "user_id"])["purchased"].max()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
    return out

@test.metric(metric_type="mean")
def revenue_per_user(data):
    user_level = data.groupby(["variant", "user_id"])["order_value"].sum()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {"mean": float(v.mean()) if n else 0.0, "std": float(v.std(ddof=1)) if n > 1 else 0.0, "n": n}
    return out

@test.metric(metric_type="proportion")
def cart_abandonment_rate(data):
    added = data.groupby(["variant", "user_id"])["added_to_cart"].max()
    purchased = data.groupby(["variant", "user_id"])["purchased"].max()
    out = {}
    for variant in ["A", "B"]:
        if variant in added.index.get_level_values(0) and variant in purchased.index.get_level_values(0):
            abandoned = ((added.loc[variant] == 1) & (purchased.loc[variant] == 0)).astype(int)
        else:
            abandoned = pd.Series(dtype=int)
        out[variant] = {"successes": int(abandoned.sum()) if not abandoned.empty else 0, "n": int(abandoned.shape[0])}
    return out

results = test.analyze(
    df,
    metrics=['conversion_rate', 'revenue_per_user', 'cart_abandonment_rate'],
    run_srm_check=True,
    observed_counts=observed_counts,
    correction='bonferroni'
)
```

### Example 2: Content Engagement

```python
test = ABTest(name="video_layout", variants=["A", "B"])
observed_counts = df.groupby("variant")["user_id"].nunique().to_dict()

@test.metric(metric_type="proportion")
def watch_rate(data):
    """% of users who watched video."""
    user_level = data.groupby(["variant", "user_id"])["video_started"].max()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
    return out

@test.metric(metric_type="mean")
def completion_rate(data):
    """% completion among watchers."""
    watchers = data[data['video_started'] == 1]
    user_level = watchers.groupby(["variant", "user_id"])["completion_pct"].mean() if not watchers.empty else pd.Series(dtype=float)
    out = {}
    for variant in ["A", "B"]:
        if isinstance(user_level, pd.Series) and not user_level.empty and variant in user_level.index.get_level_values(0):
            v = user_level.loc[variant]
        else:
            v = pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {"mean": float(v.mean()) if n else 0.0, "std": float(v.std(ddof=1)) if n > 1 else 0.0, "n": n}
    return out

@test.metric(metric_type="mean")
def avg_watch_time(data):
    user_level = data.groupby(["variant", "user_id"])["watch_seconds"].sum()
    out = {}
    for variant in ["A", "B"]:
        v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {"mean": float(v.mean()) if n else 0.0, "std": float(v.std(ddof=1)) if n > 1 else 0.0, "n": n}
    return out

results = test.analyze(
    df,
    metrics=['watch_rate', 'completion_rate', 'avg_watch_time'],
    run_srm_check=True,
    observed_counts=observed_counts,
    correction='fdr'
)
```

### Example 3: Event-Level Analysis (CTR)

```python
# For impression/click data, use impression_id as unit
test = ABTest(
    name="ad_creative",
    variants=["A", "B"],
)

@test.metric(metric_type="proportion")
def click_through_rate(data):
    out = {}
    for variant in ["A", "B"]:
        v = data.loc[data["variant"] == variant, "clicked"]
        out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
    return out

observed_counts = df.groupby("variant")["impression_id"].nunique().to_dict()
results = test.analyze(df, metrics=["click_through_rate"], run_srm_check=True, observed_counts=observed_counts)
```

## Architecture

```
ab_framework/
├── __init__.py           # Main exports
├── core.py               # ABTest class
├── backends/
│   ├── base.py          # StatisticalBackend interface
│   └── owl_backend.py   # OwlBackend implementation
├── sample_size.py        # Legacy sample size module (use backend helpers)
├── quality.py            # QualityChecker (SRM, data quality)
└── tests/
    └── test_framework.py # Verification tests
```

### Pluggable Backends

The framework uses a backend interface for statistical tests. Currently implements `OwlBackend` using `owl_ab_test`. To add a custom backend:

```python
from ab_framework.backends import StatisticalBackend

class MyBackend(StatisticalBackend):
    def proportion_z_test(self, successes_a, trials_a, successes_b, trials_b, alpha):
        # Your implementation
        return {
            'p_value': ...,
            'ci_lower': ...,
            'ci_upper': ...,
            'lift': ...,
            # ... other fields
        }
    
    def mean_t_test(self, mean_a, std_a, n_a, mean_b, std_b, n_b, alpha):
        # Your implementation
        return {...}

# Use it
test = ABTest(name="test", variants=["A", "B"], backend=MyBackend())
```

## Testing

The framework includes comprehensive tests against synthetic data:

```bash
cd ab_framework/tests
python test_framework.py
```

Tests verify:
- ✅ Simple conversion rate (binary metrics)
- ✅ Revenue per active user (continuous + filtering)
- ✅ Click-through rate (event-level)
- ✅ Multi-metric with Bonferroni correction
- ✅ Sample size planning via backend helpers
- ✅ SRM detection

## Comparison to Alternatives

| Feature | ab_framework | scipy+pandas | abexp | owl_ab_test |
|---------|--------------|--------------|-------|-------------|
| Custom metrics | ✅ Decorator | ✅ Manual | ❌ | ❌ |
| Multi-metric | ✅ Built-in | ❌ Manual | ❌ | ❌ |
| SRM checks | ✅ Automatic | ❌ Manual | ❌ | ❌ |
| Sample size | ✅ Built-in | ❌ Manual | ❌ | ❌ |
| On-demand | ✅ Stateless | ✅ Yes | ❌ Session | ✅ Yes |
| Maintenance | Active | Core | Abandoned | Active |

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please:
1. Add tests for new features
2. Update documentation
3. Follow existing code style
4. Ensure all tests pass

## Support

For issues or questions:
- Check the examples in this README
- Review test cases in `tests/test_framework.py`
- Open an issue on GitHub
