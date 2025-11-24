# AB Testing Framework

A production-ready A/B testing orchestration framework built on top of `owl_ab_test`, providing a clean, Pythonic API for experiment analysis.

## Features

✅ **Decorator-based metric registration** - Define metrics as simple Python functions  
✅ **Automatic metric type detection** - Binary (conversion) vs continuous (revenue) metrics  
✅ **Multi-metric orchestration** - Bonferroni and FDR correction for multiple testing  
✅ **SRM (Sample Ratio Mismatch) detection** - Automatic data quality checks  
✅ **Sample size calculation** - Pre-experiment power analysis  
✅ **Flexible data sources** - Works with pandas DataFrames from any source  
✅ **Pluggable statistical backends** - Currently uses owl_ab_test, easily extensible  
✅ **Rich reporting** - Markdown summaries, DataFrames, JSON exports

## Installation

```bash
pip install pandas numpy scipy owl-ab-test
```

Then add the `ab_framework` directory to your project.

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
    def test_proportion(self, successes_a, trials_a, successes_b, trials_b, alpha):
        # Your implementation
        return {
            'p_value': ...,
            'ci_lower': ...,
            'ci_upper': ...,
            'lift': ...,
            # ... other fields
        }
    
    def test_mean(self, values_a, values_b, alpha):
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
