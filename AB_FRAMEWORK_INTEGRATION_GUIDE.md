# AB Testing Framework - Integration Guide

This guide explains how to integrate with the AB Testing Framework for UI developers and experiment managers responsible for parameter selection, randomization, and experiment setup.

## Quick Reference

### What You Need to Provide (Inputs):
- **Data table** with rows of individual sessions/conversations
- **Group assignments** (each row labeled as control or treatment)
- **Outcome measurements** (quality scores, resolution flags, etc. for each session)
- **Metric calculations** (how to compute rates from the raw data)
- **Test parameters** (significance level, desired power, minimum effect size)

### What You Get Back (Outputs):
- **Statistical significance** (is the difference real or just random?)
- **Effect magnitude** (how much better/worse is treatment vs control?)
- **Confidence bounds** (range of plausible true effect sizes)
- **Sample adequacy** (do you have enough data to trust the results?)
- **Data validation** (are the groups properly randomized?)
- **Decision summary** (launch/don't launch recommendation with evidence)

## Overview

The AB Testing Framework provides statistical analysis and sample size planning for A/B experiments. You provide the data and parameters, the framework handles the statistical computations and returns results.

## Core Integration Pattern

### 1. Import the Framework
```python
from ab_framework import ABTest
```

### 2. Prepare Your Data
Your data must be a pandas DataFrame with these required columns:
- **Variant column** (e.g., `variant`): Contains variant assignments ("A", "B", "control", "treatment", etc.)
- **Unit ID column** (e.g., `user_id`): Unique identifier for each randomization unit
- **Additional data columns**: Whatever data your metrics need

#### Example Data Structure:
```python
import pandas as pd

# AI agent session data (multiple sessions per conversation)
df = pd.DataFrame({
    'conversation_id': ['conv1', 'conv1', 'conv2', 'conv3', 'conv3'],
    'variant': ['control', 'control', 'treatment', 'control', 'control'],
    'quality': [0, 1, 1, 0, 1],          # AI answer quality (0/1)
    'resolved': [0, 1, 1, 0, 0],         # Session resolved (0/1)
    'day': ['2024-01-01', '2024-01-01', '2024-01-02', '2024-01-03', '2024-01-03']
})
```

### 3. Initialize ABTest
```python
test = ABTest(
    name="ai_agent_quality_improvement",
    data=df,
    variant_col="variant",               # Column containing agent assignments
    unit_id="conversation_id",           # Column with unique conversation identifiers
    alpha=0.05,                          # Significance level (default: 0.05)
    variants=["control", "treatment"],   # Optional: specify exact variants to test
    allocation_ratio=0.3                 # Optional: % traffic to new agent (0.3 = 30% treatment, 70% control)
)
```

## Required Parameters to Send

### Initialization Parameters:
| Parameter | Type | Mandatory | Description | Example/Default |
|-----------|------|-----------|-------------|-------|
| `name` | string | ✅ | Experiment identifier | "ai_agent_quality_improvement" |
| `data` | DataFrame | ✅ | Your experiment data | See data structure above |
| `variant_col` | string | ✅ | Column name with variant assignments | "variant" |
| `unit_id` | string | ✅ | Column name with user/unit IDs | "conversation_id" |
| `alpha` | float | ❌ | Significance level (2-tailed test) | Default: 0.05 |
| `variants` | list | ❌ | Specific variants to analyze | Default: First 2 variants found |
| `allocation_ratio` | float | ❌ | Treatment allocation % | Default: None (assumes 50/50) |

### Metric Definition:
You must define metrics using decorators or programmatic registration:

```python
# Option 1: Decorator (recommended)
@test.metric(metric_type="proportion", is_primary=True)
def quality_rate(data):
    """Calculate AI answer quality rate per conversation"""
    return data.groupby('conversation_id')['quality'].max()  # 1 if conversation had quality answer

@test.metric(metric_type="proportion")
def resolved_rate(data):
    """Calculate session resolution rate per conversation"""
    return data.groupby('conversation_id')['resolved'].max()  # 1 if conversation was resolved

# Option 2: Programmatic registration
def quality_rate_func(data):
    return data.groupby('conversation_id')['quality'].max()

test.register_metric(
    name="quality_rate",
    func=quality_rate_func,
    metric_type="proportion",
    is_primary=True
)
```

#### Metric Types:
- **`"proportion"`**: Binary metrics (quality rates, resolution rates, success flags) → analyzed with Z-test
- **`"mean"`**: Continuous metrics (session duration, quality scores, response times) → analyzed with T-test

### Statistical Assumptions:
- **Tests are 2-tailed**: The framework tests for differences in either direction (treatment better OR worse than control)
- **Alpha interpretation**: With α=0.05, there's a 5% chance of detecting a difference when none exists
- **Confidence intervals**: Reported at (1-α)×100% level (e.g., 95% CI for α=0.05)
- **Sample size planning**: Uses 2-tailed assumptions for power calculations

### Analysis Parameters:
| Parameter | Type | Mandatory | Description | Default |
|-----------|------|-----------|-------------|---------|
| `metrics` | list | ❌ | Which metrics to analyze | All registered metrics |
| `correction` | string | ❌ | Multiple testing correction method | None |
| `run_srm_check` | bool | ❌ | Check Sample Ratio Mismatch | True |

#### Multiple Testing Correction Options:
The framework is designed around **one primary metric** for decision-making, with additional metrics for **soft monitoring** only. In this design, correction is typically **not needed**.

- **`None`** (default): **Recommended** - One primary metric for decisions, others for monitoring
  - Primary metric: Make statistical decisions normally (α=0.05)
  - Monitoring metrics: Observe trends, don't make formal statistical decisions
- **`"bonferroni"`**: Conservative correction - divides α by number of tests (α/n)
  - Use when making formal statistical decisions across ALL metrics
  - Very conservative, reduces power significantly
- **`"fdr"`**: False Discovery Rate correction using Benjamini-Hochberg method
  - Use when making statistical decisions across multiple metrics simultaneously
  - Less conservative than Bonferroni, maintains higher statistical power

**Typical workflow (recommended):**
```python
@test.metric(metric_type="proportion", is_primary=True)
def quality_rate(data):  # PRIMARY - for decision making
    return data.groupby('conversation_id')['quality'].max()

@test.metric(metric_type="proportion")  
def resolved_rate(data):  # MONITORING - just observe, don't decide
    return data.groupby('conversation_id')['resolved'].max()

# No correction needed - only primary metric drives decisions
results = test.analyze(correction=None)
```

**When to use correction:**
- **No correction (default)**: Primary + monitoring metric design (recommended)
- **FDR/Bonferroni**: Only when making formal statistical decisions across multiple metrics

## What You Get Back

### Analysis Results Object
The `analyze()` method returns an `ExperimentResults` object:

```python
results = test.analyze(
    metrics=["quality_rate", "resolved_rate"],
    correction=None,    # Recommended: primary + monitoring design
    run_srm_check=True
)
```

### Result Structure:

#### Top-level Properties:
```python
results.experiment_name      # "ai_agent_quality_improvement"
results.timestamp           # "2024-01-15T10:30:00.123456"
results.alpha               # 0.05
results.correction          # "fdr" or None
results.variants            # ["control", "treatment"]
results.primary_metric      # "quality_rate" (if set)
```

#### Metric Results Dictionary:
```python
results.metric_results = {
    "quality_rate": {
        # Statistical test results
        "p_value": 0.023,
        "significant": True,                # p_value < alpha
        "ci_lower": 0.002,                 # Lower bound of confidence interval
        "ci_upper": 0.045,                 # Upper bound of confidence interval
        "lift": 0.127,                     # Relative lift (12.7% improvement)
        "statistic": 2.281,                # Test statistic (z-score or t-statistic)
        
        # Group values
        "control_value": 0.456,            # Control agent quality rate
        "treatment_value": 0.515,          # Treatment agent quality rate
        "sample_size_control": 2341,       # Control conversations
        "sample_size_treatment": 2298,     # Treatment conversations
        
        # Metadata
        "metric_name": "quality_rate",
        "metric_type": "proportion",       # "proportion" or "continuous"
        "variant_control": "control",
        "variant_treatment": "treatment",
        "is_primary": True
    },
    "resolved_rate": {
        # Similar structure for monitoring metric
        "p_value": 0.341,
        "significant": False,
        "control_value": 0.623,            # Control agent resolution rate
        "treatment_value": 0.641,          # Treatment agent resolution rate
        "lift": 0.029,                     # Relative lift (2.9% improvement)
        # ... other fields similar to above
    }
}
```

#### SRM Check Results:
```python
results.srm_result = {
    "p_value": 0.823,
    "significant": False,
    "chi2_statistic": 0.049,
    "recommendation": "✅ No sample ratio mismatch detected. Randomization appears healthy."
}
```

### Formatted Output:
```python
# Get human-readable summary
summary_text = results.summary()
print(summary_text)

# Get structured data for programmatic use
structured_data = results.to_dict()
```

## Sample Size Planning (Pre-Experiment)

For planning experiments before you have data:

```python
# Initialize with minimal data structure (just for backend access)
planner = ABTest(
    name="planning",
    data=pd.DataFrame({"user_id": ["dummy"], "variant": ["A"]}),
    variant_col="variant",
    unit_id="user_id"
)

# Plan for proportion metric (e.g., AI quality rate)
sample_size = planner.backend.sample_size_proportion(
    baseline_rate=0.45,        # Current AI quality rate (45%)
    mde=0.10,                  # Minimum detectable effect (10% relative lift)
    alpha=0.05,                # Significance level
    power=0.80,                # Statistical power (80%)
    ratio=1.0                  # Treatment:control ratio (1.0 = 50/50 split)
)

# Returns:
{
    "control_size": 3842,      # Required control agent conversations
    "treatment_size": 3842,    # Required treatment agent conversations
    "total_size": 7684,        # Total required conversations
    "assumptions": {
        "baseline_rate": 0.45,
        "mde_relative": 0.10,
        "mde_absolute": 0.045,   # 45% * 10% = 4.5 percentage points
        "alpha": 0.05,
        "power": 0.80,
        "ratio": 1.0
    }
}
```

## Data Requirements & Validation

### Required Data Structure:
1. **DataFrame format**: Must be pandas DataFrame
2. **Required columns**: variant_col and unit_id must exist
3. **Minimum variants**: At least 2 different variant values
4. **Unit-level aggregation**: Metrics should aggregate to unit_id level

### Common Data Patterns:

#### Event-Level Data (Recommended):
```python
# Multiple interactions per conversation - framework handles aggregation
df = pd.DataFrame({
    'conversation_id': ['conv1', 'conv1', 'conv2', 'conv2', 'conv3'],
    'variant': ['control', 'control', 'treatment', 'treatment', 'control'], 
    'quality': [0, 1, 0, 1, 0],
    'resolved': [0, 1, 0, 1, 0]
})

@test.metric(metric_type="proportion")
def quality_rate(data):
    return data.groupby('conversation_id')['quality'].max()  # Ever had quality = 1
```

#### Pre-Aggregated Data:
```python
# Already aggregated to conversation level
df = pd.DataFrame({
    'conversation_id': ['conv1', 'conv2', 'conv3'],
    'variant': ['control', 'treatment', 'control'],
    'session_duration': [23.45, 18.30, 31.20],
    'had_quality_answer': [1, 0, 1]
})

@test.metric(metric_type="mean")
def avg_session_duration(data):
    return data.set_index('conversation_id')['session_duration']  # Already per-conversation
```

## Error Handling

The framework validates inputs and returns helpful error messages:

```python
# Common validation errors:
ValueError: Variant column 'variant' not found in data
ValueError: Unit ID column 'conversation_id' not found in data  
ValueError: Need at least 2 variants, found 1
ValueError: No metrics specified and no metrics registered
ValueError: Primary metric already set to 'quality_rate'. Only one primary metric is allowed.
```

Metric-level errors are captured in results:
```python
results.metric_results["problematic_metric"] = {
    "error": "Division by zero in metric calculation",
    # ... no other statistical fields
}
```

## Integration Checklist

### Before Integration:
- [ ] Prepare data in pandas DataFrame format
- [ ] Ensure variant and unit_id columns exist
- [ ] Define your metrics (proportion vs mean type)
- [ ] Decide on statistical parameters (alpha, correction method)

### Required Integration Steps:
- [ ] Import `ABTest` from `ab_framework`
- [ ] Initialize `ABTest` with your data and configuration
- [ ] Register metrics using `@test.metric` decorator or `register_metric()`
- [ ] Call `test.analyze()` to get results
- [ ] Parse `ExperimentResults` object for your UI/reporting needs

### Data Validation:
- [ ] Verify all required columns are present (conversation_id, variant, quality, resolved)
- [ ] Check that variants match your agent selections (control, treatment, etc.)
- [ ] Ensure metric functions return proper pandas Series indexed by conversation_id
- [ ] Test with sample AI session data before production integration

### Result Handling:
- [ ] Extract p-values and significance flags for decision-making
- [ ] Use lift values and confidence intervals for reporting
- [ ] Check SRM results for data quality
- [ ] Handle metric errors gracefully in your UI

## Support

For questions about data formats, statistical methods, or integration issues, consult:
- Framework source code: `ab_framework/core.py`
- Demo examples: `demos/` directory  
- Backend documentation: `ab_framework/backends/`