# A/B Testing Package Verification Summary

**Scientific Report on Empirical Package Evaluation**

**Date:** November 20, 2025  
**Authors:** Verification Framework Team  
**Environment:** Python 3.9.3, Windows 11, fresh virtual environment  
**Repository:** https://github.com/saaamar/abtest-framework

---

## Abstract

We conducted an empirical evaluation of several approaches to A/B testing in Python: a `scipy+pandas` baseline and three third-party packages (`abexp`, `owl_ab_test`, `py-ab-testing`). Using standardized scenarios covering conversion rates, custom revenue metrics, exposure-filtered CTR, multi-metric dashboards, and agent/AI-style metrics, we tested each package's ability to support custom metric functions, on-demand stateless analysis, and maintainability.

**Key Findings (current run, see comparison scripts for details):**
- All three third-party packages can be installed and imported in our current environment.
- For simple single-metric scenarios, `abexp` and `owl_ab_test` can reproduce the `scipy+pandas` ground truth within tolerance.
- None of the third-party packages provide first-class support for multi-metric dashboards, Bonferroni-style multiple-testing control, or orchestration features such as SRM/data-quality checks.
- `scipy+pandas` remains the most flexible and explicit option, at the cost of more boilerplate.

We conclude that a thin, custom orchestration framework on top of `scipy+pandas` is justified. The main gap is in multi-metric orchestration, quality checks, and ergonomics, not in basic package installability.

---

## 1. Introduction

### 1.1 Motivation

Modern A/B testing requires:
- **Custom metric functions** (e.g., revenue per active user, CTR among exposed users)
- **On-demand, stateless analysis** (analyze any DataFrame without maintaining sessions)
- **Flexible data sources** (CSV, Parquet, SQL, cloud storage)
- **Maintainability** (low boilerplate, consistent patterns)

Many data science teams default to `scipy+pandas` for statistics, but face substantial boilerplate (30–60 lines per metric). Third-party A/B testing packages promise higher-level abstractions, but their suitability for production use is unclear.

### 1.2 Research Questions

1. Can existing Python A/B testing packages implement the verification scenarios defined in `AB_LIBRARY_VERIFICATION.md`?
2. Do they reduce boilerplate compared to `scipy+pandas`?
3. Are they production-ready for our use cases (maintainable, documented, practical to use)?

### 1.3 Scope

We evaluate:
- **scipy+pandas** (baseline approach using standard scientific libraries)
- **abexp** (PlaytikaOSS package, 0.0.1)
- **owl_ab_test** (0.1.9)
- **py-ab-testing** (1.3.1)

Against scenarios including:
1. Simple conversion rate (binary metric, proportion test)
2. Revenue per active user (custom filter + continuous metric, t-test)
3. CTR with exposure filtering (aggregated ratio metric, proportion test)
4. Multi-metric dashboard (multiple metrics + Bonferroni correction)
5. Agent/AI-style metrics (continuous scores and resolved-rate combinations)

---

## 2. Methods

### 2.1 Data Generation

Synthetic datasets are generated via `verification/data_generator.py`:

- **Sample size:** typically $n \approx 2000$ users per scenario (about 1000 per variant), with per-scenario adjustments.
- **Random seed:** 42 (reproducible results).
- **Effect patterns:**  
  - Conversion scenarios with moderate lifts.  
  - Revenue scenarios with differences in activation rate and spend distribution.  
  - CTR scenarios with impression-level data and exposure filtering.  
  - Multi-metric and AI scenarios with “with gap” and “no gap” variants.

### 2.2 Ground Truth

`verification/ground_truth.py` implements oracle results using `scipy+pandas`. Examples:

**Conversion Rate:**

Let $n_v$ be users in variant $v$, and $x_v$ conversions. The estimated rate is  
$ \hat{p}_v = x_v / n_v $.  
We use a two-proportion z-test with pooled variance under $H_0 : p_A = p_B$:

$ z = \dfrac{\hat{p}_B - \hat{p}_A}{\sqrt{\hat{p}(1-\hat{p})(1/n_A + 1/n_B)}}, \quad \hat{p} = \dfrac{x_A + x_B}{n_A + n_B}. $

Confidence intervals are computed with group-specific standard errors.

**Revenue per Active User:**

Define the active set $ A_v = \{ i : \text{sessions}_i > 0 \} $ and

$ \text{RPAU}_v = \dfrac{1}{|A_v|} \sum_{i \in A_v} \text{revenue}_i. $

Comparison uses Welch’s t-test with unequal variances and standard formulas for degrees of freedom.

**CTR with Exposure:**

For exposed users/impressions $E_v$:

$ \widehat{\text{CTR}}_v = \dfrac{\sum_{i \in E_v} \text{clicks}_i}{\sum_{i \in E_v} \text{impressions}_i}. $

We use a proportion-style test on aggregated counts.

**Multi-Metric Dashboard:**

Multiple metrics (e.g., conversion rate, AOV, revenue per user, time to conversion).  
Bonferroni correction is applied with $ \alpha_{\text{adj}} = 0.05 / m $ for $m$ metrics.

### 2.3 Verification Tests

For each package, the verification tests (under `verification/tests/`) follow a similar pattern:

1. Load scenario data from CSV.
2. Apply scenario-specific metric transformations (filters, aggregations).
3. Compute metric values per variant.
4. Run the package’s statistical routine(s).
5. Extract p-values, effect sizes, and confidence intervals (where available).
6. Compare against the `scipy+pandas` oracle (within tolerance, typically $ \epsilon = 0.01 $ for p-values).

### 2.4 Test Environment

```
OS: Windows 11
Python: 3.9.3
Virtual environment: c:\Users\saaamar\repos\ab_testing\venv

Installed packages (relevant subset):
  numpy         2.0.2
  pandas        2.3.3
  scipy         1.13.1
  matplotlib    3.9.3
  abexp         0.0.1
  owl_ab_test   0.1.9
  py-ab-testing 1.3.1
```

---

## 3. Results

### 3.1 Quantitative Summary

The table below summarizes, at a high level, what the current verification run shows for each approach. Exact numbers for LOC and execution time can be inspected in the console logs and helper scripts (e.g. `run_full_verification.py`, `verification/format_results.py`).

| Package       | Scenarios Passed (out of 8) | Import Success | Ground Truth Match on Supported Scenarios | Multi-Metric / Bonferroni Support | Orchestration / Quality Checks | Usability (for our use case) |
|---------------|-----------------------------|----------------|-------------------------------------------|-----------------------------------|-------------------------------|------------------------------|
| scipy+pandas  | 8/8                         | ✅             | ✅                                       | ⚠️ manual only                    | ⚠️ manual only                | ✅ Flexible but verbose      |
| abexp         | 8/8                         | ✅             | ✅ (where implemented)                    | ⚠️ manual only                    | ❌ none built-in              | ⚠️ OK for simple cases       |
| owl_ab_test   | 8/8                         | ✅             | ✅ (where implemented)                    | ⚠️ manual only                    | ❌ none built-in              | ⚠️ OK for simple cases       |
| py-ab-testing | not fully evaluated         | ✅             | not evaluated in current run              | ❌                                | ❌                            | ⚠️ Not used in our pipeline  |

Interpretation (high level):

- All evaluated packages can now be imported and used in basic scenarios.
- `scipy+pandas` remains the reference implementation and ground-truth oracle.
- `abexp` and `owl_ab_test` can replicate many scalar-metric results but do not provide first-class multi-metric orchestration.
- `py-ab-testing` is not actively integrated into our current verification pipeline.

### 3.2 Detailed Results by Package

#### 3.2.1 scipy+pandas

Example scenario outcomes (numbers illustrative from a typical run):

- **Scenario 1 – Simple Conversion Rate:**
  - A: 10.0%, B: 11.2%  
  - P-value ≈ 0.38 → not significant at $ \alpha = 0.05 $.  
  - Confidence interval for lift includes 0.

- **Scenario 2 – Revenue per Active User:**
  - Strong positive effect for B, p-value $ \ll 0.001 $, CI entirely above 0.

- **Scenario 3 – CTR (exposed users or impressions):**
  - B shows higher CTR, highly significant (p-value near 0).

- **Scenario 4 – Multi-Metric Dashboard:**
  - Some metrics significant after Bonferroni correction, others not.  
  - Dashboard-style interpretation requires checking all metrics together.

Overall:

- All scenarios run successfully and match the oracle by construction.
- Implementation is verbose but highly transparent.

#### 3.2.2 abexp

- Installs and imports successfully in the current environment.
- For single-metric problems (e.g., conversion or revenue-like metrics), results can match `scipy+pandas` closely when configured correctly.
- Lacks:
  - Native multi-metric orchestration.
  - Built-in multiple-testing corrections.
  - Built-in SRM or data-quality checks.

**Verdict:** usable for simple, single-metric analyses, but orchestration and guardrails must be implemented externally.

#### 3.2.3 owl_ab_test

- Installs and imports successfully.
- Provides helpers for common A/B calculations (proportions, means) and can match oracle results when given the right inputs.
- Expectation of pre-aggregated inputs in some APIs means:
  - Extra work to aggregate DataFrame data into summary counts/means.
  - Less direct integration with our DataFrame-based verification pipeline.
- Similar limitations to `abexp` regarding multi-metric dashboards and multiple-testing control.

**Verdict:** useful as a statistical helper in simple settings; not a full orchestration layer for our multi-metric scenarios.

#### 3.2.4 py-ab-testing

- Package is installed and importable in the current environment.
- In this iteration of the verification work, we have **not fully integrated** `py-ab-testing` into the scenario suite.
- No updated, scenario-by-scenario results are reported here.

**Verdict:** not part of our active verification pipeline; no current statement about its suitability beyond basic import/install checks.

---

## 4. Discussion

### 4.1 What Third-Party Packages Provide

The current verification run indicates that:

- Third-party A/B packages can be made to work for **simple, single-metric** experiments.
- Once installed and imported, they generally:
  - Provide a more “packaged” interface for standard tests.
  - Can match `scipy+pandas` oracle results for many scalar metrics.

However, for our use cases, they fall short in several key areas:

- **Multi-metric dashboards:**  
  - No unified abstraction for running and combining multiple metrics with a single configuration.
- **Multiple-testing control:**  
  - No built-in support for corrections like Bonferroni across an experiment’s metric set.
- **Experiment-level orchestration:**  
  - No notion of “scenario” or “experiment” that:
    - Runs quality checks (e.g., SRM, missing data, outlier diagnostics).
    - Produces standardized output schemas across metrics and variants.

### 4.2 Why scipy+pandas Still Matters

`scipy+pandas`:

- Acts as a **ground-truth oracle**:
  - Clear mapping from formulas to code.
  - Direct access to data for arbitrary metrics.
- Enables:
  - Any custom metric we can express in pandas.
  - Direct control over the exact statistical test and its parameters.

But it requires:

- Considerable boilerplate per metric and per scenario.
- Manual implementation of:
  - Multi-metric dashboards.
  - Multiple-testing corrections.
  - SRM and data-quality checks.
  - Standardized result schemas.

This is precisely the role of the custom framework: not to replace `scipy+pandas` statistics, but to **wrap and orchestrate** them.

### 4.3 The Gap and How the Framework Addresses It

**Gap identified:**

- No single package that is:
  - High-level and ergonomic for our DataFrame-based workflows.
  - Capable of handling multi-metric experiments, multiple-testing logic, and guardrails.
  - Transparent enough for debugging and verification.

**Framework contributions:**

- **Orchestration layer** on top of `scipy+pandas`:
  - Standard way to define metrics and attach them to experiments.
  - Shared result schema for metrics and variants.
- **Quality checks via `ab_framework.quality`:**
  - Sample Ratio Mismatch (SRM) detection.
  - Basic data-quality checks (missingness, outliers).
- **Backends interface (`ab_framework.backends`):**
  - Ability to plug in alternative engines in a controlled way.
  - Preserve consistent inputs/outputs for comparison and verification.

---

## 5. Conclusion

### 5.1 Summary of Findings

1. `scipy+pandas` continues to serve as the flexible and reliable baseline for all scenarios in our verification suite.  
2. Third-party packages such as `abexp` and `owl_ab_test` can:
   - Install and import cleanly in our environment.
   - Match ground-truth results for simple scalar metrics.
   - But do **not** solve multi-metric orchestration, multiple-testing control, or guardrails.
3. `py-ab-testing` is not yet fully integrated into the current verification runs, and we do not rely on it in our pipeline.

### 5.2 Recommendation

**Continue to build and rely on a custom orchestration framework on top of `scipy+pandas`.**

Reasons:

- We retain:
  - Statistical correctness from well-tested scientific libraries.
  - Maximum flexibility in metric definitions and data transformations.
- We gain:
  - Consistent experiment structures.
  - Shared result schemas.
  - Built-in health checks and room for richer orchestration.

### 5.3 Limitations

- The evaluation focuses on:
  - A limited number of scenarios (though they are designed to be realistic).
  - A small set of Python packages.  
- Other tools or ecosystems (e.g., R, SaaS experimentation platforms) are out of scope for this report.

### 5.4 Future Work

1. Extend the scenario suite to cover more designs (e.g., sequential tests, CUPED, more AI-style metrics).  
2. Integrate and systematically evaluate `py-ab-testing` if it becomes relevant.  
3. Improve reporting and visualization of multi-metric results.  
4. Explore automated integration of the framework into CI and production experiment pipelines.

---

## 6. References

### 6.1 Documentation

- `AB_LIBRARY_VERIFICATION.md` – Verification protocol and scenarios.  
- `AB_FRAMEWORK_DECISION.md` – Framework architecture decision.  
- `AB_TESTING_THEORY.md` – Statistical foundations.  
- `README.md` – Project overview.

### 6.2 Code

- `verification/data_generator.py` – Synthetic data generation.  
- `verification/ground_truth.py` – Oracle implementation.  
- `verification/tests/test_scipy_baseline.py` – `scipy+pandas` tests.  
- `verification/tests/test_abexp.py` – `abexp` tests.  
- `verification/tests/test_owl.py` – `owl_ab_test` tests.  
- `verification/tests/test_py_ab_testing.py` – `py-ab-testing` tests.

### 6.3 Results

- `verification/results/comparison_matrix.md` – Side-by-side comparison (see notes about scenario coverage).  
- `verification/results/verification_code_review.md` – Technical review of verification code.

---

## Appendix A: Statistical Formulas

### A.1 Two-Proportion Z-Test

Null hypothesis $ H_0: p_A = p_B $.  
Test statistic:

$ z = \dfrac{\hat{p}_B - \hat{p}_A}{\text{SE}_{\text{pooled}}}, \quad \text{SE}_{\text{pooled}} = \sqrt{\hat{p}(1-\hat{p})\left(\dfrac{1}{n_A} + \dfrac{1}{n_B}\right)}, $

with pooled proportion $ \hat{p} = \dfrac{x_A + x_B}{n_A + n_B} $.

### A.2 Welch’s T-Test

Null hypothesis $ H_0: \mu_A = \mu_B $ (unequal variances allowed).  
Test statistic:

$ t = \dfrac{\bar{x}_B - \bar{x}_A}{\text{SE}}, \quad \text{SE} = \sqrt{\dfrac{s_A^2}{n_A} + \dfrac{s_B^2}{n_B}}. $

Degrees of freedom use the Welch–Satterthwaite approximation.
