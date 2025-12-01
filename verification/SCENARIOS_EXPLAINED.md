> Purpose: Human-readable explanation of the 8 verification scenarios and their design
> Generated: Manually authored, maintained under version control.

# A/B Testing Verification Scenarios

This document explains the different scenarios used in the verification framework.

## Overview

The verification framework tests A/B testing packages across **8 scenarios** with different purposes:

### Scenarios 1-4: **Package Comparison Scenarios**
These scenarios are used to compare different A/B testing packages (scipy+pandas, abexp, owl_ab_test) against ground truth.

- **Scenario 1**: Simple Conversion Rate Test
- **Scenario 2**: Revenue per Active User (Custom Metric)
- **Scenario 3**: CTR with Impression-Level Data
- **Scenario 4**: Multi-Metric Dashboard

**Purpose**: Evaluate which packages can handle real-world A/B testing requirements

**Testing**: All packages are tested on these scenarios and compared

### Scenarios 5-8: **Ground Truth Reference Scenarios**
These scenarios demonstrate proper statistical methodology and professional reporting for agent bot experiments.

- **Scenario 5**: Agent Bot - Resolved Rate (WITH significant gap)
- **Scenario 6**: Agent Bot - Resolved Rate (NO significant gap)
- **Scenario 7**: Agent Bot - AI Quality Metric (WITH significant gap)
- **Scenario 8**: Agent Bot - AI Quality Metric (NO significant gap)

**Purpose**: Show how to properly analyze and report A/B test results

**Testing**: Only ground truth calculations with professional conclusions (no package comparison)

## Why This Split?

### Scenarios 1-4 (Package Comparison)
- Test package capabilities across diverse metric types
- Compare API ergonomics and code complexity
- Validate statistical correctness vs. ground truth
- Inform framework decision (build vs. use existing package)

### Scenarios 5-8 (Reference Examples)
- Demonstrate industry-standard statistical reporting
- Show proper handling of both significant and non-significant results
- Provide templates for professional experiment reports
- Illustrate domain-specific use cases (agent bot evaluation)

## Data Generation

All scenarios use the same data generator with **seed = 42** to ensure reproducible results. The generator lives in `verification/data_generator.py` and writes CSVs into the shared top-level `data/` folder:

```python
# In data_generator.py
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
```

**This means**: Deleting and regenerating data (into `data/`) will produce identical results every time.

## Running the Verification

### Full Verification (Scenarios 1-4 + Ground Truth for 5-8)
```bash
python run_full_verification.py
```

This runs:
1. Data generation (all 8 scenarios)
2. Ground truth calculations (all 8 scenarios with professional conclusions)
3. Package comparison (scenarios 1-4 only)

### Package Comparison Only (Scenarios 1-4)
```bash
python verification/compare_all_packages.py
```

This runs package tests and comparisons for scenarios 1-4.

### Ground Truth Only (All 8 Scenarios)
```bash
python verification/ground_truth.py
```

This shows professional statistical conclusions for all 8 scenarios.

## Output Format

### Package Comparison Output (Scenarios 1-4)
```
======================================================================
owl - Scenario 2
======================================================================
Ground Truth p-value: 0.000021
owl p-value:    0.000029
Difference:            0.000008
Match (tol=0.01):      ✅ YES

Metric A: GT=57.7415, PKG=57.7415, diff=0.000000
Metric B: GT=68.8327, PKG=68.8327, diff=0.000000

======================================================================
STATISTICAL CONCLUSION
======================================================================
The treatment group showed a statistically significant higher revenue 
per active user compared to the control group (Treatment: $68.83 vs. 
Control: $57.74, difference: $11.09, relative change: 19.2%, p = 0.0000).
The 95% confidence interval for the difference is [$6.01, $16.17].

✅ RECOMMENDATION: The treatment variant shows a significant improvement. 
Consider implementing this change.
======================================================================
```

### Ground Truth Output (All Scenarios)
Shows only the professional statistical analysis and conclusion without package comparison.

## Why Scenarios 5-8 Are Not in Package Comparison

1. **Different Purpose**: They're reference examples, not package tests
2. **No Added Value**: Package comparison for basic binary/continuous metrics is already covered in scenarios 1-3
3. **Redundant Testing**: Would just repeat the same statistical tests with different data
4. **Focus**: Keep package comparison focused on diverse capabilities (custom metrics, impression-level data, multi-metric)

## Summary

| Scenario | Type | Package Tests | Ground Truth | Purpose |
|----------|------|--------------|--------------|---------|
| 1-4 | Core | ✅ Yes | ✅ Yes | Package evaluation & comparison |
| 5-8 | Reference | ❌ No | ✅ Yes | Professional reporting examples |

**All scenarios** generate data with seed=42 for reproducibility.
