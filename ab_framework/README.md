> Purpose: Package-level documentation for the ab_framework Python library (installation, usage, examples)
> Generated: Manually authored, maintained under version control.

# AB Testing Orchestration Framework

A production-ready A/B testing **orchestration and standardization layer** with pluggable statistical backends (currently `owl_ab_test`, with a `scipy` fallback planned), providing a clean, Pythonic API for experiment analysis.

## Features

✅ **Decorator-based metric registration** - Define metrics as simple Python functions  
✅ **Automatic metric type detection** - Binary (conversion) vs continuous (revenue) metrics  
✅ **Multi-metric orchestration** - Bonferroni and FDR correction for multiple testing  
✅ **SRM (Sample Ratio Mismatch) detection** - Automatic data quality checks  
✅ **Sample size calculation** - Pre-experiment power analysis  
✅ **Flexible data sources** - Works with pandas DataFrames from any source  
✅ **Pluggable statistical backends** - Currently uses `owl_ab_test`, easily extensible (e.g., `scipy`)  
✅ **Rich reporting** - Markdown summaries, DataFrames, JSON exports

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
    data=df,
    variant_col="variant",  # Column with 'A', 'B', etc.
    unit_id="user_id"       # Randomization unit
)

# Register metrics using decorator
@test.metric
def conversion_rate(data):
    """User-level conversion rate."""
    return data.groupby('user_id')['converted'].max()

@test.metric
def revenue_per_user(data):
    """Total revenue per user."""
    return data.groupby('user_id')['revenue'].sum()

# Analyze with multi-metric correction
results = test.analyze(
    metrics=['conversion_rate', 'revenue_per_user'],
    correction='bonferroni'  # or 'fdr' or None
)

# View results
print(results.summary())
```

## Core Concepts

### 1. Metric Functions

Metric functions take the raw DataFrame and return a pandas Series indexed by the unit_id:

```python
@test.metric
def conversion_rate(data):
    # Return one value per user
    return data.groupby('user_id')['converted'].max()

@test.metric
def revenue_per_active_user(data):
    # Aggregation + filtering example
    user_revenue = data.groupby('user_id')['revenue'].sum()
    active = user_revenue[user_revenue > 0]
    return active

@test.metric
def avg_session_duration(data):
    # Continuous metric
    return data.groupby('user_id')['session_seconds'].mean()
```

### 2. Automatic Type Detection

The framework automatically detects:
- **Binary metrics** (0/1 values) → Uses proportion test
- **Continuous metrics** → Uses t-test for means

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

test = ABTest(name="checkout_redesign", data=df)

# PRIMARY: What we're trying to improve
@test.metric
def conversion_rate(data):
    """PRIMARY - Main success metric"""
    return data.groupby('user_id')['purchased'].max()

# GUARDRAILS: What we must not harm
@test.metric
def revenue_per_order(data):
    """GUARDRAIL - Ensure we don't reduce order value"""
    orders = data[data['purchased'] == 1]
    return orders.groupby('user_id')['order_value'].sum()

@test.metric
def page_load_time(data):
    """GUARDRAIL - Ensure performance doesn't degrade"""
    return data.groupby('user_id')['load_time'].mean()

@test.metric
def user_satisfaction(data):
    """GUARDRAIL - Protect user experience"""
    return data.groupby('user_id')['satisfaction_score'].mean()

# DIAGNOSTICS: For understanding behavior
@test.metric
def cart_abandonment(data):
    """DIAGNOSTIC - Understand funnel behavior"""
    added = data.groupby('user_id')['added_to_cart'].max()
    purchased = data.groupby('user_id')['purchased'].max()
    return ((added == 1) & (purchased == 0)).astype(int)

@test.metric
def checkout_page_views(data):
    """DIAGNOSTIC - Track engagement"""
    return data.groupby('user_id')['checkout_views'].sum()

# Analyze all metrics with correction
results = test.analyze(
    metrics=[
        'conversion_rate',      # Primary
        'revenue_per_order',    # Guardrail
        'page_load_time',       # Guardrail
        'user_satisfaction',    # Guardrail
        'cart_abandonment',     # Diagnostic
        'checkout_page_views'   # Diagnostic
    ],
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

### 4. SRM Checks

Sample Ratio Mismatch checks run automatically:

```python
results = test.analyze(
    metrics=['conversion_rate'],
    run_srm_check=True  # Default
)

if not results.srm_result['passed']:
    print("⚠️ WARNING:", results.srm_result['recommendation'])
```

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
    data=aa_data,
    variant_col="variant",
    unit_id="user_id"
)

@aa_test.metric
def key_metric(data):
    return data.groupby('user_id')['metric_value'].mean()

aa_results = aa_test.analyze(['key_metric'])

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

# Use for sample size calculation
from ab_framework import SampleSizeCalculator
calc = SampleSizeCalculator()

sample_plan = calc.for_mean(
    baseline_mean=baseline_mean,  # From A/A test (more accurate!)
    baseline_std=baseline_std,     # From A/A test (more accurate!)
    mde=0.07,  # Business requirement
    alpha=0.05,
    power=0.80
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
from ab_framework import SampleSizeCalculator

calc = SampleSizeCalculator()

# For conversion rates
result = calc.for_proportion(
    baseline_rate=0.10,  # Current 10% conversion
    mde=0.05,            # Want to detect 5% relative lift
    alpha=0.05,
    power=0.80
)
print(f"Need {result['total_size']:,} users")
# Output: Need 115,528 users

# For continuous metrics (revenue, time, etc.)
result = calc.for_mean(
    baseline_mean=50.0,    # $50 average
    baseline_std=25.0,     # $25 std dev
    mde=0.10,              # Detect 10% lift
    alpha=0.05,
    power=0.80
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

### Programmatic Metric Registration

If you can't use decorators:

```python
def my_metric(data):
    return data.groupby('user_id')['value'].sum()

test.register_metric('my_metric', my_metric)
```

## Real-World Examples

### Example 1: E-commerce Checkout Flow

```python
test = ABTest(name="checkout_v2", data=df)

@test.metric
def conversion_rate(data):
    return data.groupby('user_id')['purchased'].max()

@test.metric
def revenue_per_user(data):
    return data.groupby('user_id')['order_value'].sum()

@test.metric
def cart_abandonment_rate(data):
    added_to_cart = data.groupby('user_id')['added_to_cart'].max()
    purchased = data.groupby('user_id')['purchased'].max()
    abandoned = (added_to_cart == 1) & (purchased == 0)
    return abandoned.astype(int)

results = test.analyze(
    metrics=['conversion_rate', 'revenue_per_user', 'cart_abandonment_rate'],
    correction='bonferroni'
)
```

### Example 2: Content Engagement

```python
test = ABTest(name="video_layout", data=df)

@test.metric
def watch_rate(data):
    """% of users who watched video."""
    return data.groupby('user_id')['video_started'].max()

@test.metric
def completion_rate(data):
    """% completion among watchers."""
    watchers = data[data['video_started'] == 1]
    return watchers.groupby('user_id')['completion_pct'].mean()

@test.metric
def avg_watch_time(data):
    return data.groupby('user_id')['watch_seconds'].sum()

results = test.analyze(
    metrics=['watch_rate', 'completion_rate', 'avg_watch_time'],
    correction='fdr'
)
```

### Example 3: Event-Level Analysis (CTR)

```python
# For impression/click data, use impression_id as unit
test = ABTest(
    name="ad_creative",
    data=df,
    unit_id="impression_id"  # Not user_id!
)

@test.metric
def click_through_rate(data):
    return data.set_index('impression_id')['clicked']

results = test.analyze(['click_through_rate'])
```

## Architecture

```
ab_framework/
├── __init__.py           # Main exports
├── core.py               # ABTest class
├── backends/
│   ├── base.py          # StatisticalBackend interface
│   └── owl_backend.py   # OwlBackend implementation
├── sample_size.py        # SampleSizeCalculator
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
    
    def mean_t_test(self, values_a, values_b, alpha):
        # Your implementation
        return {...}

# Use it
test = ABTest(name="test", data=df, backend=MyBackend())
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
- ✅ Sample size calculator
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
