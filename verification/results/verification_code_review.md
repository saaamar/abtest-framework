# Verification Code Review

## Scope

This review covers the verification implementation described in `AB_LIBRARY_VERIFICATION.md`:

- Synthetic data generation (`verification/data_generator.py`)
- Ground truth calculations (`verification/ground_truth.py`)
- Baseline verification tests using SciPy + pandas (`verification/tests/test_scipy_baseline.py`)
- Package‑specific evaluation for `abexp` (`verification/results/abexp_evaluation.md`)

The goal is to check that the code:

- Implements the documented scenarios and metrics faithfully
- Uses transparent, standard statistical methods
- Clearly demonstrates what each package can (and cannot) do
- Has no hidden behavior or silent failures

---

## 1. Data Generation (`verification/data_generator.py`)

### 1.1 Global properties

- Uses a **fixed random seed**: `RANDOM_SEED = 42` and `np.random.seed(RANDOM_SEED)`, ensuring reproducible datasets.
- Generates four CSV files under `verification/data/`:
  - `scenario1_conversion.csv`
  - `scenario2_revenue.csv`
  - `scenario3_ctr.csv`
  - `scenario4_multi.csv`
- Each scenario uses `n_users=2000` in `generate_all_scenarios`, matching the “~2000 users” note referenced in the decision document.

### 1.2 Scenario 1 – Simple Conversion Rate

- Function: `generate_scenario1_conversion(...)`
- Output schema:

  ```text
  user_id | variant | converted | timestamp
  ```

- Logic:
  - `variant` split: A/B with configurable `split` (default 0.5).
  - Conversions:
    - Variant A: `converted ~ Binom(1, baseline_rate)`
    - Variant B: `converted ~ Binom(1, baseline_rate + effect_size)`
  - In `generate_all_scenarios`:
    - `baseline_rate = 0.10`
    - `effect_size = 0.02` → B has about 12% vs A 10%

**Assessment:**  
Schema and effect sizes match the **Scenario 1** plan in `AB_LIBRARY_VERIFICATION.md`. The effect is simple, explicit, and appropriate for verifying a two‑proportion test.

### 1.3 Scenario 2 – Revenue per Active User (Custom Metric)

- Function: `generate_scenario2_revenue(...)`
- Output schema:

  ```text
  user_id | variant | revenue | sessions | timestamp
  ```

- “Active user” definition:

  ```python
  sessions > 0
  ```

- Logic:
  - Activity:
    - A: `active_a ~ Binom(1, baseline_active_rate)`
    - B: `active_b ~ Binom(1, baseline_active_rate + effect_size_rate)`
  - Sessions:
    - Active: uniform from 1–10
    - Inactive: 0
  - Revenue (only for active users):
    - A: `Normal(baseline_revenue_mean, baseline_revenue_std)` truncated at 0.
    - B: `Normal(baseline_revenue_mean + effect_size_revenue, baseline_revenue_std)` truncated at 0.

**Assessment:**  
Exactly implements the “revenue per active user” scenario defined in the plan:

- Active users are controlled by `sessions > 0`
- Both the **fraction of active users** and their **average revenue** are improved in B
- This gives a realistic, multi‑component effect for the custom metric

### 1.4 Scenario 3 – CTR with Exposure Filtering

- Function: `generate_scenario3_ctr(...)`
- Output schema:

  ```text
  user_id | variant | clicks | impressions | exposed | timestamp
  ```

- Logic:
  - Exposure: `exposed ~ Binom(1, exposure_rate)` in both arms (default 0.80)
  - Impressions:
    - Exposed: uniform 50–200
    - Not exposed: small counts 0–10
  - Clicks:
    - A: `Binom(impressions_a, baseline_ctr * exposed_a)`
    - B: `Binom(impressions_b, (baseline_ctr + effect_size) * exposed_b)`

**Assessment:**  
This is a faithful implementation of the **“CTR among exposed users only”** metric:

- Non‑exposed users carry almost no impressions.
- The difference is injected as a 1 percentage‑point increase in CTR for exposed users.

### 1.5 Scenario 4 – Multi‑Metric Dashboard

- Function: `generate_scenario4_multi_metric(...)`
- Output schema:

  ```text
  user_id | variant | converted | order_value | revenue | time_to_conversion | timestamp
  ```

- Metrics encoded:
  1. Conversion rate (A: baseline, B: +effect_conversion)
  2. AOV (converted users only, B has increased mean)
  3. Revenue per user (all users, B has higher mean)
  4. Time to conversion (converted users only, B is faster: effect_time < 0)

**Assessment:**  
All four metrics from **Scenario 4** are present with clear and independent effect sizes. This is a good synthetic “dashboard” case for multi‑metric analysis and multiple testing correction.

---

## 2. Ground Truth (`verification/ground_truth.py`)

Ground truth uses SciPy + pandas only, with small reusable helpers.

### 2.1 Common helpers

- `calculate_proportion_test(successes_a, n_a, successes_b, n_b, alpha=0.05)`
  - Implements a **two‑proportion z‑test**:
    - Computes group rates, pooled proportion, standard error, z‑statistic, two‑sided p‑value.
    - Computes 95% CI for the difference in rates using group‑specific standard errors.
    - Returns relative lift, sample sizes, and a boolean `significant` flag.
- `calculate_ttest(values_a, values_b, alpha=0.05)`
  - Implements a **Welch’s t‑test**:
    - Uses `stats.ttest_ind(..., equal_var=False)`.
    - Computes standard error, Welch–Satterthwaite df, 95% CI, Cohen’s d, relative lift, and significance.

**Assessment:**  
Both helpers are transparent and align with the formulas and recommendations in `AB_TESTING_THEORY.md` (Section 3).

### 2.2 Scenario‑specific ground truth functions

- `scenario1_ground_truth(...)`
  - Reads `scenario1_conversion.csv`.
  - Splits by `variant`.
  - Uses `calculate_proportion_test` with `converted` counts.
  - Annotates `scenario` and `test_type = "Two-proportion z-test"`.

- `scenario2_ground_truth(...)`
  - Reads `scenario2_revenue.csv`.
  - Filters to `sessions > 0` (only active users).
  - Splits by `variant` and uses active‑user `revenue` arrays.
  - Uses `calculate_ttest`.
  - Annotates scenario, `test_type`, and a note clarifying active‑user filter.

- `scenario3_ground_truth(...)`
  - Reads `scenario3_ctr.csv`.
  - Filters to `exposed == 1`.
  - Aggregates total clicks and impressions for A and B.
  - Uses `calculate_proportion_test(clicks_a, impressions_a, clicks_b, impressions_b)`.
  - Annotates scenario, `test_type`, and an explanatory note.

- `scenario4_ground_truth(...)`
  - Reads `scenario4_multi.csv`.
  - For each metric:
    - Conversion rate: `calculate_proportion_test` on `converted`.
    - Average order value: `calculate_ttest` on `order_value` for converted users.
    - Revenue per user: `calculate_ttest` on `revenue` for all users.
    - Time to conversion: `calculate_ttest` on `time_to_conversion` for converted users, after `dropna`.
  - Applies **Bonferroni**: `bonferroni_alpha = 0.05 / 4`.
  - Stores the corrected alpha and descriptive notes.

**Assessment:**  

- Ground truth **exactly** implements the metrics and tests from `AB_LIBRARY_VERIFICATION.md`.
- There are no undocumented transformations or “hidden tweaks”.
- The code is straightforward: pandas splits and aggregations, SciPy tests, and simple dicts.

**Conclusion:**  
`ground_truth.py` is a faithful, transparent “oracle” implementation suitable for validating any other package or baseline.

---

## 3. SciPy + pandas Baseline Tests (`verification/tests/test_scipy_baseline.py`)

`test_scipy_baseline.py` is the primary verification implementation for the baseline (“do nothing” with standard libraries).

### 3.1 Scenario mappings

- `test_scenario1_scipy_baseline()`
  - Loads `scenario1_conversion.csv`.
  - Splits `variant` A/B.
  - Computes conversion rates and a two‑proportion z‑test.
  - Computes a 95% CI for the difference using group‑level standard errors.
  - Prints metrics, p‑value, CI, relative lift, execution time, and approximate LOC.

- `test_scenario2_scipy_baseline()`
  - Loads `scenario2_revenue.csv`.
  - Filters to `sessions > 0` (active users).
  - Splits by `variant`.
  - Computes per‑active‑user revenue and runs Welch’s t‑test with CI and relative lift.
  - Prints metrics plus a note confirming custom metric support.

- `test_scenario3_scipy_baseline()`
  - Loads `scenario3_ctr.csv`.
  - Filters `exposed == 1`.
  - Aggregates clicks and impressions per variant.
  - Computes CTR, two‑proportion z‑test, and CI for the difference.
  - Prints metrics and a note confirming custom metric implementation.

- `test_scenario4_scipy_baseline()`
  - Loads `scenario4_multi.csv`.
  - Computes:
    - Conversion rate (two‑proportion z‑test).
    - AOV (converted‑only, Welch’s t‑test).
    - Revenue per user (Welch’s t‑test).
    - Time to conversion (converted‑only, Welch’s t‑test).
  - Prints p‑values and applies **Bonferroni** manually: `alpha / 4`.

### 3.2 Structure and behavior

- Each scenario follows a clean pattern:
  - Load data → prepare subsets → compute metric(s) → run statistical test(s) → compute CI → print results.
- The functions **return** dicts containing metrics, p‑values, execution time, and estimated lines‑of‑code; this supports higher‑level summarization (`run_all_scipy_baseline_tests()`).
- `run_all_scipy_baseline_tests()` runs all four scenarios, aggregates basic diagnostics, and prints a structured summary of pros/cons.

### 3.3 Gaps vs. ideal verification

- There are **no explicit assertions** comparing SciPy baseline results to `ground_truth.py`:
  - No checks like `abs(p_value_baseline - p_value_ground_truth) < 0.01`.
  - No numeric CI consistency checks vs ground truth.
- The tests use **print statements** rather than a test framework’s assertion mechanisms for verification.
- There is no integration yet with other packages (`owl_ab_test`, `py-ab-testing`) – only SciPy + pandas baseline is implemented.

**Assessment:**  

- For all four scenarios, SciPy + pandas tests are faithful to the specification and ground truth formulas.
- Methodologically, they validate that:
  - Custom metrics (Scenarios 2–3) are straightforward with pandas.
  - Multi‑metric dashboards and Bonferroni corrections are possible but verbose.
- From a **testing rigor** perspective:
  - The missing assertions vs `ground_truth.py` are the main weakness.
  - This is a coverage/robustness issue, not a correctness flaw in the implemented math.

---

## 4. abexp Evaluation (`verification/results/abexp_evaluation.md`)

The `abexp` package evaluation shows:

- Installation fails on modern environments due to:
  - Severely outdated dependency requirements (NumPy, pandas, SciPy, matplotlib, PyMC3).
  - Conflicts with current toolchain versions.
- The package is effectively **unmaintained** (last updates around 2020–2021).
- No scenarios can be implemented or run.

In the scoring:

- `abexp` receives **0/10** across all criteria:
  - Custom metrics, on‑demand analysis, maintainability, statistical accuracy – all **non‑testable** due to install failure.

**Assessment:**  

- This is clearly documented and consistent with the narrative in `AB_FRAMEWORK_DECISION.md`.
- It directly supports marking the `abexp` row as ❌ across all scenarios and objectives, with the justification “package cannot be installed on modern Python; unmaintained”.

---

## 5. Other package tests

A project‑wide search for tests named `test_abexp`, `test_owl`, or `test_py_ab_testing` found **no such files**, and there are no other test modules under `verification/tests/` besides `test_scipy_baseline.py`.

**Assessment:**  

- For `owl_ab_test` and `py-ab-testing`:
  - No verification tests are currently implemented in this repo.
  - Any scoring for these packages must therefore be marked as “Not yet implemented / TBD” rather than assumed.

---

## 6. Summary: Faithfulness and Gaps

### Faithful and solid components

- **Data generation (`data_generator.py`)**
  - Matches scenario schemas and effect‑size descriptions in `AB_LIBRARY_VERIFICATION.md`.
  - Uses a fixed random seed and simple, interpretable distributions.

- **Ground truth (`ground_truth.py`)**
  - Implements metrics exactly as defined for all scenarios.
  - Uses standard SciPy tests and constructs clear, structured result dicts.
  - Provides a transparent “oracle” for comparison.

- **SciPy baseline tests (`test_scipy_baseline.py`)**
  - For all 4 scenarios:
    - Metrics and filters (e.g. `sessions > 0`, `exposed == 1`) match the spec.
    - Statistical tests match the ground truth and theory doc.
    - There is clean separation of data loading, metric calculation, testing, and reporting.

- **abexp evaluation**
  - Accurately documents installation failure and maintenance status.
  - Justifies a score of 0/10 and a ❌ verdict in the evaluation matrix.

### Gaps and questionable patterns

- **Missing automated assertions**
  - Baseline tests rely on printing rather than asserting equality with ground truth within a tolerance.
  - No formal epsilon (e.g. 0.01 on p‑values) is enforced in code.

- **No tests for other packages**
  - `owl_ab_test` and `py-ab-testing` have no corresponding test files.
  - Any scoring for them must remain **TBD** until tests are written.

---

## 7. Conclusion

Overall, the verification implementation around SciPy + pandas is **technically correct** and **aligned with the documented plan**:

- Synthetic data and ground truth form a clean, controlled experiment harness.
- SciPy baseline tests demonstrate that:
  - All four scenarios can be implemented with standard libraries.
  - Custom metrics are straightforward but verbose.
  - Multi‑metric dashboards are possible but require manual multiple‑testing handling.
- The abexp evaluation confirms that the main candidate full‑stack package is **unusable** in modern environments, reinforcing the need for a custom orchestration layer.

The primary improvements to pursue (if the verification suite is expanded) are:

1. Add explicit **assertions vs. ground truth** in the baseline tests, with documented tolerances.
2. Implement and test scenarios for `owl_ab_test` and `py-ab-testing`, or explicitly leave them as “Not yet implemented / TBD” in the evaluation matrix.
