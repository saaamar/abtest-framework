# Slide 0 – Why A/B Testing Theory Matters

- We want to answer:
  - Is there a **real effect** or just **noise**?
  - Are we **controlling error rates** (false positives / false negatives)?
  - Is our **experiment design** (unit choice, metrics, duration) valid?
- Without clear theory:
  - Different people apply different rules
  - Risk of over‑interpreting noise as signal
  - Hard to trust “no difference” conclusions
- Purpose of this talk:
  - Summarize a **practical theory toolkit** for A/B testing
  - Align on **design choices** that our framework assumes

---

## Slide 1 – Core Goals of Online Experiments

- **Causal inference** – estimate the effect of a change vs status quo
- **Risk management** – test on a subset before full rollout
- **Business impact** – quantify lift in KPIs (conversion, revenue, quality)
- **Learning** – understand *why* things work or not (diagnostic metrics)
- Framing:
  - Null hypothesis $H_0$: no difference between variants
  - Alternative $H_1$: variant B improves metric by at least some amount

---

## Slide 2 – Units: Randomization vs Analysis

- Golden rule:
  > **Unit of randomization = unit of analysis**
- Typical hierarchy in our bot example:
  - user_id → conversation_id → session_id
- Design choice examples:
  - **Randomize by user_id** (recommended default)
    - Stable experience per user
    - Natural for user‑centric metrics (retention, satisfaction)
  - **Randomize by session_id**
    - More units, but users see a mix of variants
    - Interpretation is per‑session, not per‑user
  - **Randomize by conversation_id, analyze by session_id**
    - Use clustered SEs with cluster = conversation_id
- Takeaway:
  - Start with **user‑level experiments** for user‑centric questions
  - Use conversation/session‑level designs deliberately, with correct analysis

---

## Slide 3 – Metric Types and Roles

- Metric types:
  - **Proportions / rates** – conversion, CTR, success rate
  - **Continuous** – revenue per user, time, amount
  - **Counts** – events per user, items, page views
- Metric roles:
  - **Primary metric** – single success criterion
  - **Guardrails** – must not worsen (e.g., errors, latency)
  - **Diagnostics** – help explain behavior, but don’t drive the decision
- Why one primary metric:
  - Clean decision rule: “Ship if primary improves (and guardrails are ok)”
  - Easier to reason about power and multiple testing

---

## Slide 4 – Error Rates: α, β, Power, MDE

- **Type I error (α)** – false positive
  - Conclude there is an effect when there is none
- **Type II error (β)** – false negative
  - Miss a real effect
- **Power** = $1 - β$ – probability to detect a true effect of interest
- **MDE (Minimum Detectable Effect)**
  - Smallest effect that is **business‑meaningful**
  - Chosen relative to baseline (e.g., detect +10% lift vs 3.2% baseline)
- Standard planning knob choices:
  - α ≈ 0.05, power ≈ 0.8, MDE set by business

---

## Slide 5 – Statistical Engine (High Level)

- For each metric, we use standard tests:
  - **Proportion tests** (two‑proportion z‑test) for rates
  - **Mean tests** (Welch’s t‑test) for continuous metrics
- Key quantities:
  - Point estimates for each variant (means / rates)
  - Difference (lift) between variants
  - Standard errors, p‑values, confidence intervals
- Conceptual question the engine answers:
  > “Given α, power, baseline, and MDE, how many units do I need?
  >  And with my data, is the observed difference signal or noise?”

---

## Slide 6 – Sample Size for Proportion Metrics

- For a proportion metric with equal split:
  $$
  n_{\text{per group}} \approx 2 (Z_{\alpha/2} + Z_{\beta})^2 \frac{p(1-p)}{\text{MDE}^2}
  $$
  - $p$ – baseline rate
  - MDE – absolute minimum detectable effect
  - $Z_{\alpha/2}, Z_\beta$ – normal quantiles for α and power
- Intuition:
  - Smaller MDE ⇒ **more users** per variant
  - Lower α (more strict) or higher power ⇒ **more users**
- In the theory doc, we visualize:
  - Sample size vs MDE
  - Power vs sample size
  - Sample size vs power for different α

---

## Slide 7 – Clustered Data and Robust SEs

- Real data are often **clustered**:
  - Randomize by user, but observe many sessions/events per user
  - Randomize by conversation, analyze per session
- If we treat all rows as independent, we **underestimate variance**
- Cluster‑robust standard errors:
  - Same point estimate for the effect
  - Larger, more realistic standard errors that allow correlation within clusters
- Rule of thumb:
  - **Cluster at least** at the level of randomization
  - E.g., cluster by user_id or conversation_id

---

## Slide 8 – A/A Tests: Validating the Infrastructure

- A/A test: both arms are intentionally identical
- Purpose:
  - Check randomization (no systematic differences)
  - Check metric computation and logging
  - Get realistic baseline variance for planning
- Expectations in A/A:
  - p‑values mostly > α (no significant differences)
  - No SRM (sample ratio mismatch)
  - Variance estimates stable over time
- If A/A fails:
  - Treat results from A/B tests as **untrustworthy** until fixed

---

## Slide 9 – SRM (Sample Ratio Mismatch)

- Definition:
  - Planned split (e.g., 70/30) vs observed counts per variant
- We use a **χ² goodness‑of‑fit test** on user counts:
  - Null: routing matches design
  - Very small p‑value (e.g., < 0.001) ⇒ SRM detected
- Why a very strict α for SRM (≈ 0.001):
  - Only alert when extremely confident something is wrong
  - Avoid noisy alerts from minor, random imbalances
- Consequences of SRM:
  - Routing or logging bug ⇒ metric inferences are invalid
  - Correct action: stop, investigate, and rerun

---

## Slide 10 – Sequential Monitoring and Peeking

- In practice, teams **peek** at results during the run
- Every unplanned peek **inflates** the true false‑positive rate
- Group‑sequential designs:
  - Plan a small number of interim looks
  - Use α‑spending or boundaries (O’Brien–Fleming, Pocock)
- Practical stance in this project:
  - Encourage you to minimize ad‑hoc peeking
  - Treat heavy peeking as a **process / data‑quality** issue
- Message:
  - Decide your peeking policy **upfront** and factor it into error control

---

## Slide 11 – Multiple Metrics and Corrections

- Multiple metrics per experiment:
  - Primary, guardrail, and diagnostic metrics
- Multiple testing issue:
  - With $k$ tests at level α, $P(\ge 1$ false positive$) = 1 - (1-α)^k$
- Corrections:
  - Bonferroni, Holm, Benjamini–Hochberg (FDR), etc.
- Practical guidance:
  - Exactly **one primary** metric for power / Go‑NoGo
  - A small set of guardrails, with conservative thresholds
  - Diagnostics for understanding, not for shipping decisions

---

## Slide 12 – Shadow Testing (High‑Level Theory)

- Shadow test: new model/system runs in parallel, but users see control only
- Generates **paired observations** per request:
  - Control vs shadow latency, scores, safety flags, etc.
- Statistical tools:
  - Paired t‑tests for continuous metrics
  - McNemar’s test for paired binary outcomes
- Role in risk management:
  - Catch regressions in safety, cost, performance **before** user exposure
  - Decide if a model is ready for an online A/B test

---

## Slide 13 – From Theory to Framework

- The framework **implements** this theory:
  - Enforces unit and metric choices that make sense
  - Uses appropriate tests and clustered SEs under the hood
  - Exposes α, power, MDE, and allocation as explicit configuration
- Separation of concerns:
  - Theory doc: **why** (math, trade‑offs, recommended practices)
  - Framework: **how** (APIs, defaults, output format)
- Goal:
  - You can reason about experiments at a **theory level** when needed
  - Day‑to‑day, you still have a **simple, opinionated tool** to use
