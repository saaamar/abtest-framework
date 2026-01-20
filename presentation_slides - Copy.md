# Slide 0 – What Problem Does This Solve?

- You run experiments (A/B tests) and ask:
  - $“$Is there a real difference between variants, or just noise?$”$
  - $“$If there is no difference, can I trust that conclusion?$”$
  - $“$Did we randomize correctly (no SRM)?$”$
  - $“$Is my whole experimentation setup sane (AA tests, SRM, metrics)?$”$
- Today this is often:
  - Manual notebooks
  - Different teams using different libraries
  - No standard SRM checks, AA checks, or multi-metric handling

**Goal of this framework:**  
Give a **simple, consistent way** to:
- Run experiments (A/B and A/A)
- Detect differences (or correctly say “no difference”)
- Catch SRM / AA / data issues early
- Produce repeatable, auditable results

---

## Slide 1 – What the Framework Does for You (Value)

For any A/B or A/A test you run:

- **Input:**
  - A DataFrame with rows = events (users, sessions, orders, etc.)
  - Columns: variant, unit ID, metrics / raw signals

- **The framework handles:**
  - Metric computation and aggregation
  - Statistical tests under the hood
  - Multiple metrics with correction
  - SRM checks and basic data validation
  - **AA sanity checks** (A vs A) to validate your setup

- **Output:**
  - Clear decision per metric:
    - “No difference within noise”
    - “Treatment significantly better/worse”
  - Effect sizes, CIs, p-values
  - JSON / dict you can pipe into dashboards
  - Markdown/text summary you can paste in a report

---

## Slide 2 – Basic Usage: How to Run an Experiment

**Concepts:**

- **Experiment (ABTest):**  
  - Name, input data, variant column, unit identifier (user/session/…)
- **Metrics:**  
  - Functions that compute a scalar per unit (conversion, revenue, score, etc.)
- **Modes:**
  - **A/B:** Compare different variants (A vs B, …)
  - **A/A:** Both arms are the same on purpose, to test the system itself

**User workflow (high level):**

1. Create an experiment object with your DataFrame.
2. Define one or more metrics.
3. Call `analyze()` with the metrics you care about.
4. Read the summarized results.

(Details/actual code can be in docs / demo notebook, not in slides.)

---

## Slide 3 – Example: A/A Test – “System Sanity Check”

**Use case:** Before trusting any A/B test, you want to know:  
$“$If I split traffic into A and A, do I get ‘no difference’ as expected?$”$

- You intentionally send identical experience to both variants.
- You expect:
  - No significant differences on all main metrics.
  - SRM checks to pass.

**Framework interpretation (conceptual):**

- **A/A result should be:**
  - All metrics: “no statistically significant difference”
  - SRM: PASSED
- If A/A shows:
  - Many “significant” differences, or
  - SRM failures

  then something is wrong with:
  - Randomization
  - Data logging
  - Metric definitions

**Value:**  
The framework makes **A/A tests a first-class tool** to validate the entire experimentation pipeline, not just something you do ad hoc.

---

## Slide 4 – Skipping A/A and Using Historical Data

Sometimes you may **decide not to run an explicit A/A test** and instead:

- Rely on **historical data** to validate:
  - Metric definitions (stability over time)
  - Data quality (no sudden jumps, missingness, logging breaks)
  - Reasonable baselines (conversion, revenue, quality scores, etc.)

This is possible, but comes with **trade-offs**:

- **Pros:**
  - No extra runtime experiment just for A/A.
  - Faster time-to-decision if history is rich and clean.

- **Cons / consequences:**
  - Historical data may have:
    - Different traffic mix or seasonality.
    - Different funnels, pricing, or product changes.
  - You won’t catch:
    - New randomization bugs specific to the current test.
    - New logging issues introduced right before the experiment.
  - In short: you have **less direct evidence** that “if A = A, we see no difference.”

**Message:**  
The framework supports both approaches:
- **Recommended:** run dedicated A/A sanity tests periodically.
- **Alternative:** rely on rich historical data, but accept **higher risk** that unseen issues slip through.

---

## Slide 5 – Example: “No Difference” A/B Scenario

**Use case:** You shipped variant B to 50% of users. Business question:  
$“$Is B better than A, or is performance the same within noise?$”$

- Framework output example (conceptual):

  - **Metric:** Conversion rate  
    - Control: 9.9%  
    - Treatment: 10.1%  
    - Difference: +0.2 percentage points  
    - 95% CI: $[-0.3, +0.7]$  
    - p-value: 0.62  
    - **Decision:** *No statistically significant difference*

**What this tells you:**

- Within your data and power, A and B behave the same.
- Safe interpretation: “No evidence that B is better or worse.”
- You can:
  - Keep A (if simpler / cheaper), or
  - Roll B if there are non-metric reasons (tech, UX), knowing you’re not harming KPIs measurably.

**Value:** The framework **makes “no difference” a first-class, trustworthy outcome**, not an afterthought.

---

## Slide 6 – Example: Clear Difference A/B Scenario

**Use case:** Same setup, but this time there *is* a real effect.

- Output example (conceptual):

  - **Metric:** CTR  
    - Control: 4.0%  
    - Treatment: 4.8%  
    - Difference: +0.8 percentage points (+20%)  
    - 95% CI: $[+0.4, +1.2]$  
    - p-value: 0.0005  
    - **Decision:** *Treatment significantly better*

**What this tells you:**

- Effect is positive, statistically solid, and size is quantified.
- You know:
  - Approximate uplift range (here: +10–30% relative).
  - The risk of a false positive is below your chosen $\alpha$.

**Value:**  
You get a **ready-to-communicate story**:
- “Variant B increased CTR by about 20% (95% CI 10–30%, p=0.0005).”

---

## Slide 7 – When the Framework Says “SRM Detected”

**SRM (Sample Ratio Mismatch):**  
Your actual traffic split does not match your intended allocation (e.g., 50/50 expected, but data shows 60/40 in number or composition of users).

The framework automatically:

- Checks variant allocation against expectations.
- Flags large imbalances or suspicious patterns (SRM).
- Surfaces an explicit SRM status in the results.

**What the user sees conceptually:**

- **SRM check:** FAILED  
  - Expected allocation: 50% / 50%  
  - Observed: 61% Control / 39% Treatment  
  - **Recommendation:** *Do not trust the A/B inference. Investigate routing / eligibility logic.*

**What you do with this:**

- You **stop** before over-interpreting uplift/no difference.
- You investigate:
  - Experiment assignment logic
  - Traffic filters, feature flags, bots, etc.

**Value:** The framework makes **data quality / randomization checks automatic**, not something each analyst has to remember.

---

## Slide 8 – Multiple Metrics: How Results Are Presented

Real experiments rarely have a single KPI. Typical setup:

- Primary metric (e.g., conversion or resolution).
- Secondary metrics (e.g., revenue, time on site, quality score).
- Guardrail metrics (e.g., error rate, latency).

The framework:

- Lets you define multiple metrics on the same experiment.
- Runs proper multiple-testing correction (e.g., Bonferroni/FDR).
- Returns a **per-metric decision**, plus an overall summary.

**What the user gets:**

- Table / dict per metric:
  - Baseline and treatment values
  - Difference, CI, p-value, corrected p-value
  - Decision: “improve / worsen / no evidence / inconclusive”
- One consistent format for all experiments.

**Value:**  
You don’t have to hand-wire multiple-test logic. You get **dashboard-ready, comparable outputs** for every experiment.

---

## Slide 9 – How This Fits in Your Daily Workflow

Typical usage pattern:

1. **Experiment runs → data lands in warehouse.**
2. **You load data into a notebook / script.**
3. **You define:**
   - The experiment (variants, unit, expected split)
   - Metrics (conversion, revenue, quality, etc.)
   - Whether it’s an **A/A sanity test** or an **A/B decision test**
4. **You call the framework** to:
   - Run SRM checks
   - Analyze all metrics
   - Produce machine-readable and human-readable outputs
5. **You share results** with:
   - Product / business stakeholders (text summary, dashboards)
   - Engineering / data teams (raw numbers, JSON, logs)

**Key property:**  
All teams follow the **same process and logic**, so:
- Two people analyzing the same experiment get the **same answer**.
- Moving from “quick notebook” to “productionized analysis” is trivial (same interface).

---

## Slide 10 – What Users Don’t Need to Care About

Things **the framework hides** from end users:

- Which statistical library is used internally (scipy, OWL, etc.).
- Exact test choice per metric (e.g., two-proportion z-test vs. Welch’s t-test).
- Details of correction methods implementation.
- Boilerplate for grouping/aggregating raw rows.
- Low-level data validation routines.

Users care about:

- What data to provide.
- How to define metrics in domain language.
- How to read the decisions and confidence intervals.
- Trust that SRM, AA checks, and sanity checks are always run (or consciously skipped with clear understanding of consequences).

**Message:**  
The implementation is swappable; **your interface and results format stay stable.**

---

## Slide 11 – Summary for End Users

- **You get:**
  - A **single, simple way** to analyze experiments (A/B and A/A).
  - Automatic **SRM checks**, **AA sanity checks**, and data validation.
  - Clear **“difference vs no difference”** calls per metric.
  - Support for **multiple metrics** with proper corrections.
  - **Consistent outputs** for dashboards, reports, and audits.

- **You can choose:**
  - To run explicit A/A tests to fully validate the pipeline, or
  - To rely on historical data at the cost of higher risk that issues go unnoticed.

- **You don’t need to worry about:**
  - Which stats package is used.
  - Rewriting analyses when we change implementations.
  - Remembering every edge-case check by hand.

- **Result:**  
  - Faster, safer experiment analysis.  
  - Less room for subjective interpretation.  
  - A shared, production-grade standard for A/B and A/A decisions.
