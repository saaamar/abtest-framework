# AB Testing Framework - Integration Guide

This guide explains how to integrate with the AB Testing Framework for UI developers and experiment managers responsible for parameter selection, randomization, and experiment setup.

## Quick Reference

### What You Need to Provide (Inputs):
- **Raw data** containing:
  - Individual sessions/conversations (one row per interaction)
  - Group assignments (each row labeled as control or treatment)
  - Outcome measurements (quality scores, resolution flags, etc. for each session)
- **Metric calculations** (business rules that process your raw data):
  - *What constitutes success?* (e.g., "conversation had at least one quality answer")
  - *How to aggregate?* (e.g., "percentage of conversations that succeeded")
  - *What's the primary decision metric?* vs *what's just monitoring?*
- **Test parameters** (significance level, desired power, minimum effect size)

### What You Get Back (Outputs):
- **Statistical significance** (is the difference real or just random?)
- **Effect magnitude** (how much better/worse is treatment vs control?)
- **Confidence bounds** (range of plausible true effect sizes)
- **Sample adequacy** (do you have enough data to trust the results?)
- **Data validation** (are the groups properly randomized?)
- **Decision summary** (launch/don't launch recommendation with evidence)

## Process Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raw Data      │    │ Metric          │    │ Statistical     │    │    Results      │
│                 │───▶│ Calculations    │───▶│ Analysis        │───▶│                 │
│ • Sessions      │    │                 │    │                 │    │ • Significance  │
│ • Groups        │    │ • Business      │    │ • Hypothesis    │    │ • Effect Size   │
│ • Outcomes      │    │   Rules         │    │   Testing       │    │ • Confidence    │
│                 │    │ • Aggregation   │    │ • Power Calc    │    │ • Decisions     │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

1. Your System           2. You Define        3. Framework Does    4. Framework Returns
   Provides                These Functions      This Automatically   These Results
```

**Step-by-Step:**
1. **Data Collection**: Your system captures individual interactions (sessions, clicks, outcomes) with A/B group assignments
2. **Metric Definition**: You write business rules that transform raw data into meaningful KPIs ("% conversations with quality answers")  
3. **Statistical Processing**: Framework applies hypothesis testing, calculates confidence intervals, validates randomization
4. **Decision Support**: Framework returns significance tests, effect sizes, and recommendations for launch decisions

## Overview

The AB Testing Framework provides statistical analysis and sample size planning for A/B experiments. You provide the data and parameters, the framework handles the statistical computations and returns results.

**Important design note:** the framework core is **schema-agnostic**. It does not inspect your DataFrame schema (or any other data object). You pass a data snapshot into `analyze(data=...)`, and your metric functions are responsible for converting that snapshot into per-variant summary statistics.

## Core Integration Pattern

### 1. Import the Framework
```python
from ab_framework import ABTest
```

### 2. Prepare Your Data
Your data can be any object (commonly a pandas DataFrame). The framework core will not inspect it.

Your metric functions decide:
- how to interpret variants (e.g. `"control"` vs `"treatment"`)
- what the unit of analysis is (user / conversation / impression)
- how to aggregate raw rows into the summary stats required for testing

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
    variants=["control", "treatment"],   # Variants to compare
)

# Configure analysis knobs after construction
test.setup(
    alpha=0.05,                 # Significance level (default is 0.05 if omitted)
    treatment_fraction=0.3,     # Treatment allocation: 30% treatment / 70% control (for SRM expectations)
)

# Run analysis on a specific snapshot (e.g., "today")
observed_counts = {
    "control": int((df["variant"] == "control").sum()),
    "treatment": int((df["variant"] == "treatment").sum()),
}

results = test.analyze(
    data=df,
    metrics=["quality_rate", "resolved_rate"],
    correction=None,
    run_srm_check=True,
    observed_counts=observed_counts,
)
```

## Required Parameters to Send

### Initialization Parameters:
| Parameter | Type | Mandatory | Description | Example/Default |
|-----------|------|-----------|-------------|-------|
| `name` | string | ✅ | Experiment identifier | "ai_agent_quality_improvement" |
| `alpha` | float | ❌ | Significance level (2-tailed test); configured via `setup(alpha=...)` | Default: 0.05 |
| `variants` | list | ❌ | Specific variants to analyze | Default: `["A", "B"]` |
| `treatment_fraction` | float | ❌ | Treatment allocation: fraction of experiment traffic allocated to the treatment variant (e.g., 0.3 = 30% treatment / 70% control). Configure via `setup(treatment_fraction=...)`. Used for SRM expectations in SRM checks. | Default: None (assumes equal allocation across variants) |

### Metric Definition:
You must define metrics using the `metric(...)` decorator API:

```python
# Option 1: Decorator (recommended)
@test.metric(metric_type="proportion", is_primary=True)
def quality_rate(data):
    """Calculate AI answer quality rate per variant.

    Return per-variant summary stats required for a proportion test:
    {variant: {"successes": int, "n": int}}
    """
    per_conv = data.groupby(['variant', 'conversation_id'])['quality'].max().reset_index()
    summary = per_conv.groupby('variant')['quality'].agg(['sum', 'count']).to_dict('index')
    return {v: {'successes': int(d['sum']), 'n': int(d['count'])} for v, d in summary.items()}

@test.metric(metric_type="proportion")
def resolved_rate(data):
    """Calculate resolved rate per variant."""
    per_conv = data.groupby(['variant', 'conversation_id'])['resolved'].max().reset_index()
    summary = per_conv.groupby('variant')['resolved'].agg(['sum', 'count']).to_dict('index')
    return {v: {'successes': int(d['sum']), 'n': int(d['count'])} for v, d in summary.items()}

# Option 2: Programmatic (without using @ syntax)
def quality_rate(data):
    per_conv = data.groupby(['variant', 'conversation_id'])['quality'].max().reset_index()
    summary = per_conv.groupby('variant')['quality'].agg(['sum', 'count']).to_dict('index')
    return {v: {'successes': int(d['sum']), 'n': int(d['count'])} for v, d in summary.items()}

test.metric(metric_type="proportion", is_primary=True)(quality_rate)
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
    conv_level = data.groupby(["variant", "conversation_id"])["quality"].max()
    out = {}
    for variant in ["A", "B"]:
        v = conv_level.loc[variant] if variant in conv_level.index.get_level_values(0) else pd.Series(dtype=float)
        out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
    return out

@test.metric(metric_type="proportion")  
def resolved_rate(data):  # MONITORING - just observe, don't decide
    conv_level = data.groupby(["variant", "conversation_id"])["resolved"].max()
    out = {}
    for variant in ["A", "B"]:
        v = conv_level.loc[variant] if variant in conv_level.index.get_level_values(0) else pd.Series(dtype=float)
        out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
    return out

# No correction needed - only primary metric drives decisions
observed_counts = data.groupby("variant")["conversation_id"].nunique().to_dict()
results = test.analyze(data, correction=None, run_srm_check=True, observed_counts=observed_counts)
```

**When to use correction:**
- **No correction (default)**: Primary + monitoring metric design (recommended)
- **FDR/Bonferroni**: Only when making formal statistical decisions across multiple metrics

## What You Get Back

### Analysis Results Object
The `analyze()` method returns an `ExperimentResults` object:

```python
results = test.analyze(
    data,
    metrics=["quality_rate", "resolved_rate"],
    correction=None,    # Recommended: primary + monitoring design
    run_srm_check=True,
    observed_counts=observed_counts,
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
        "metric_type": "binary",           # framework output label: "binary" or "continuous"
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

# Note on dispersion in summaries:
# - For proportion (binary) metrics, summaries show **SE** (standard error of the estimated rate).
# - For mean (continuous) metrics, summaries show **Std** (sample standard deviation).

# Get structured data for programmatic use
structured_data = results.to_dict()
```

## Sample Size Planning (Pre-Experiment)

For planning experiments before you have data:

```python
from ab_framework import ScipyBackend

backend = ScipyBackend()

# Plan for proportion metric (e.g., AI quality rate)
sample_size = backend.sample_size_proportion(
    baseline_rate=0.45,        # Current AI quality rate (45%)
    mde=0.10,                  # Minimum detectable effect (10% relative lift)
    alpha=0.05,                # Significance level
    power=0.80,                # Statistical power (80%)
    treatment_fraction=0.5,    # 50/50 variant split
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
2. **Metric-defined columns**: The framework core does not validate schema; your metric functions define what columns they require.
3. **Variants**: The ABTest is configured with explicit variant labels (e.g., `["A", "B"]`).
4. **Unit-level aggregation**: Metrics should aggregate to the experiment's randomization unit (user, conversation, impression, etc.) and return per-variant summary stats.

### How to Think About "Lift" and MDE

When you plan for a "2%" or "10%" lift (the MDE) and when the framework reports an observed lift for a metric, both are defined on the **cumulative experiment window**:

- All rows from **day 1 of the experiment up to the analysis timestamp** are pooled when your metric function computes per‑variant summary stats.
- The backend then tests the difference between those **cumulative** control/treatment summaries.

Per‑day metric curves (daily rates, daily p‑values) are recommended for **monitoring and diagnostics** only (catching SRM, obvious breaks, seasonality, etc.). They are typically under‑powered and should not be used as separate decision criteria. The decision about whether you achieved the planned MDE is always based on the **pooled, cumulative effect**.

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
    conv_level = data.groupby(["variant", "conversation_id"])["quality"].max()  # Ever had quality = 1
    out = {}
    for variant in ["control", "treatment"]:
        v = conv_level.loc[variant] if variant in conv_level.index.get_level_values(0) else pd.Series(dtype=float)
        out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
    return out
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
    conv_level = data.groupby(["variant", "conversation_id"])["session_duration"].mean()  # Already per-conversation
    out = {}
    for variant in ["control", "treatment"]:
        v = conv_level.loc[variant] if variant in conv_level.index.get_level_values(0) else pd.Series(dtype=float)
        n = int(v.shape[0])
        out[variant] = {"mean": float(v.mean()) if n else 0.0, "std": float(v.std(ddof=1)) if n > 1 else 0.0, "n": n}
    return out
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
- [ ] Register metrics using `@test.metric(metric_type=...)`
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