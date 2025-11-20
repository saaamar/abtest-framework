[TOC]

# 📘 A/B Testing Theory for the Dynamic A/B Testing Analysis Framework

> **How to use these docs**
>
> * Use `README.md` as your primary entry point for the package: what the framework does, how to configure it, and example usage.
> * Use this `AB_TESTING_THEORY.md` file when you want the underlying statistical theory: detailed formulas, derivations, design trade‑offs, and methodological justifications referenced from the README.

This document gathers the **statistical theory and methodology** that underpins the framework in `README.md`.

It is deliberately more detailed and math-heavy. The goal is that engineers can use the framework with just the README, while data scientists and reviewers can come here for full details and justifications.

---

## 1. Goals and Fundamentals

### What is A/B Testing?

**A/B testing** (also called split testing) is a randomized controlled experiment that compares two or more versions of a product feature, algorithm, or user experience to determine which performs better on specific business metrics.

### Core Goals of A/B Testing

* **Causal Inference**: Establish whether changes directly cause improvements in business metrics
* **Risk Mitigation**: Test changes on a subset before full rollout to minimize potential negative impact
* **Data-Driven Decisions**: Replace intuition and opinions with statistical evidence
* **Continuous Optimization**: Iteratively improve products through systematic experimentation
* **Business Impact Measurement**: Quantify the effect of changes on key performance indicators (KPIs)

### Key A/B Testing Methodology

#### 1. Hypothesis Formation

```text
H₀ (Null): No difference between variant A and variant B
H₁ (Alternative): Variant B performs better than variant A by at least X%
```

#### 2. Experimental Design

* **Randomization Unit**: Define what gets randomized (users, sessions, accounts)
* **Traffic Allocation**: Determine split ratio (50/50, 90/10, etc.)
* **Success Metrics**: Primary and secondary metrics to measure
* **Guardrail Metrics**: Metrics that must not be negatively affected

> **Important design principle of this framework**  
> This framework is intentionally **not** an experimentation platform. It does not decide *who* sees control or treatment and it does not collect raw logs. Those responsibilities stay in your own product / experimentation system. This package assumes you already have:
>
> 1. An **assignment table**: `unit_id → variant_label` (produced by your assignment logic, e.g., values like "control" or "treatment")
> 2. An **events/metrics table**: logs of what happened for each `unit_id`
>
> Given only these inputs and your metric definitions, the framework focuses purely on the **math and methodology**: sample size, hypothesis tests, monitoring, and Go/NoGo decisions.

---

## 2. Choosing the Unit of Randomization vs. Unit of Analysis

One of the first practical decisions in any experiment is: **"What is my unit?"**

The golden rule is:[^kohavi-unit]

> **Unit of randomization = Unit of analysis**

This keeps your statistics valid and your interpretation simple: you analyze the same entity you randomized.

### Example Dilemma: Users, Conversations, and Sessions in a Bot System

Imagine your product is a **bot assistant**:

* You have **users** (with `user_id`)
* Each user can open multiple **conversations** (with `conversation_id`)
* A single conversation with an agent can stay **open for days**, and is split into multiple **sessions** according to your sessionization logic (e.g., inactivity timeout, reopen rules), each with its own `session_id`
* You want to change the bot logic and run an A/B test

This gives you a natural hierarchy:

```text
user_id → conversation_id → session_id
```

You now face a natural question:

> Should the **unit_id** be `user_id` or `session_id`?

Both choices are legitimate, but they answer **slightly different questions** and affect both user experience and statistical properties.

### Option 1: Randomize by `user_id`

**What it means**

* Each user is assigned once to an experiment variant (e.g., variant A or variant B — in many systems named control and treatment)
* All conversations for that user follow the same variant during the experiment

**Pros**

* **Consistent experience** per user – the same human always sees the same behavior
* Natural for user-level metrics:
    * "% of users with at least one resolved conversation"
    * "Average conversations per user per week"
    * "User retention after N days"
* Easier interpretation: "If a user is exposed to B instead of A, how does their behavior change?"

**Cons**

* Fewer independent units than conversations → may require **longer duration** for the same power

**When to prefer `user_id` as unit**

* Your primary metrics are **user-centric** (engagement, satisfaction, retention)
* You care about a **stable, predictable** experience for the same person
* Conversations for the same user are clearly **not independent** (very common)

If you randomize by `user_id`, you should also **analyze metrics at user level** (aggregate conversation data per user before running tests).

### Option 2: Randomize by `session_id`

**What it means**

* Each new **session** is randomized independently to A or B
* The same user (and even the same long‑lived conversation) can see A in some sessions and B in others

**Pros**

* Many more units (sessions) → potentially **shorter tests** for **session‑level** metrics
* Direct answer to: "Does the treatment improve metrics **per session**?" (e.g., resolution rate per session, average handling time per session)

**Cons**

* The same user can experience **mixed behavior** (sometimes variant A, sometimes variant B across sessions)
* User-level interpretation becomes more complex (each user sees a blend of both variants / treatments)
* Sessions from the same user are often **correlated**; naive per‑session analysis can **overstate significance** unless you use clustered/robust methods

**When to prefer `session_id` as unit**

* Your primary metric is truly **per-session**, and user-level experience consistency is less critical
    * e.g., "resolution rate per session", "average handling time per session"
* Sessions are relatively **independent tasks** from the user's perspective (even if they belong to the same long‑running conversation)

### Randomize by `conversation_id`, analyze by `session_id`

In many real systems (including this bot example), you can also **randomize at `conversation_id` and analyze at `session_id`**:

* Each **conversation** is assigned once to A or B (unit of randomization = `conversation_id`).
* All **sessions within that conversation** inherit the same treatment, so they are valid sub‑units for analysis.

In that setup, you typically:

* Run primary tests at the **conversation level** (respecting the randomization unit), and
* Optionally use **session‑level aggregates** for richer diagnostics, with cluster‑robust methods that **cluster by `conversation_id`**.

For example, in Python with `statsmodels` you might:

```python
import statsmodels.formula.api as smf

# conversation_id is the randomized unit; sessions are repeated observations
model = smf.ols(
    "session_metric ~ C(variant_label)",
    data=session_level_df
).fit(cov_type="cluster", cov_kwds={"groups": session_level_df["conversation_id"]})

print(model.summary())  # treatment coefficient with conversation-level clustered SEs
```

### Practical guidance

For most product scenarios (including the bot use case), the recommended **default** is:

* Choose **`user_id` as the `unit_id`** (unit of randomization)
* Aggregate session / conversation events to **user-level metrics** (unit of analysis)

Conversation-level randomization (`conversation_id`) is still valid, but should be a deliberate choice when:

* The experiment is focused on **conversation-level operations** where an entire conversation is the natural indivisible unit, and
* You are comfortable with users seeing a **mix of variants (e.g., control/treatment or A/B) across different conversations and sessions**, and
* You adjust your statistical analysis to respect the correlation between conversations/sessions of the same user.

In short:

> Start with **user-level experiments** for user-centric metrics and experience.  
> Use **conversation-level experiments** for low-level operational metrics, with careful analysis.

---

## 3. Statistical Framework & Math Cheat‑Sheet

### High-level role of the statistical engine

At a high level, the framework’s statistical engine answers:

> "Given my baseline performance, desired minimum detectable effect (MDE), significance level (α), and power, how many units do I need — and, once I have data, is the observed difference real or just noise?"

We mainly use:

* **Proportion tests** for rate metrics (e.g., conversion, CTR)
* **Mean tests** for continuous metrics (e.g., revenue per user, time)
* **Confidence intervals** to express uncertainty around the estimated lift

These choices follow standard A/B testing practice (e.g., z‑tests for proportions and Welch’s t‑test for means; see common treatments in introductory statistics texts or Kohavi et al., *Trustworthy Online Controlled Experiments*).

For quick reference inside this framework, we will often summarize the core statistical knobs as:

* **Significance level (α)** – risk of a false positive (Type I error), typically 0.05
* **Statistical power (1−β)** – probability of detecting a true effect, typically 0.8
* **Minimum Detectable Effect (MDE)** – the *smallest business‑relevant change* you want to be able to detect
* **Sample size** – number of randomized units needed to reach your chosen α, power, and MDE

### A) Proportion / rate metrics (conversion rate, CTR, etc.)

Let:

* $p_A$ = conversion rate in control  
* $p_B$ = conversion rate in treatment  
* $n_A$, $n_B$ = sample sizes per group  
* $\Delta = p_B - p_A$ = absolute difference

Approximate **standard error** of a proportion near baseline $p$ (for planning):

$$
\text{SE}(p) \approx \sqrt{\frac{p(1-p)}{n}}
$$

For the **difference in proportions** during analysis, we use a pooled standard error and compute a z‑statistic:

$$
Z = \frac{\Delta}{\text{SE}_\text{pooled}}
$$

A stats library then converts $Z$ into a **p‑value**; if $p_\text{value} < \alpha$, the result is *statistically significant*.

### B) Continuous metrics (revenue per user, time, etc.)

Let:

* $\mu_A$, $\mu_B$ = sample means per group  
* $s_A$, $s_B$ = sample standard deviations  
* $n_A$, $n_B$ = sample sizes

The **standard error of the mean** is approximately:

$$
\text{SE}(\mu) \approx \frac{s}{\sqrt{n}}
$$

For the difference in means, we use a (Welch) **t‑test**:

For the difference in means, we use a (Welch) **t‑test**:

$$
t = \frac{\mu_B - \mu_A}{\text{SE}_\text{diff}}
$$

Again, a stats library converts $t$ into a p‑value and confidence interval.

### C) Sample size for proportion metrics

For a proportion metric with equal split between control and treatment, a standard approximation for **required sample size per group** is:

$$
n_{\text{per group}} \approx 2 \cdot (Z_{\alpha/2} + Z_{\beta})^2 \cdot \frac{p(1-p)}{\text{MDE}^2}
$$

Where:

* $Z_{\alpha/2}$ = critical value for significance level (e.g., 1.96 for $\alpha = 0.05$)  
* $Z_{\beta}$ = critical value for power (e.g., 0.84 for power = 0.8)  
* $p$ = baseline rate (e.g., current conversion rate)  
* **MDE** = absolute minimum detectable effect (e.g., 10% relative lift on 3.2% → 0.0032 absolute)

This is the formula implemented by functions like `calculate_sample_size(...)` in the framework.

### D) Clustered standard errors (when observations are grouped)

In many practical experiments, the **randomization unit** and the **raw rows in your dataset** are not the same:

* You might randomize at **user** or **conversation** level, but observe multiple **sessions** or **events** per unit.
* Those rows inside the same user/conversation are typically **correlated** (same person, same context).

If you naively treat all rows as independent and use standard formulas for the standard error, you will typically **underestimate variance** and get p‑values that are **too optimistic**.

Cluster‑robust standard errors fix this by:

1. Keeping the **same point estimate** (e.g., difference in means or regression coefficient), but  
2. Changing how the **variance of that estimate** is computed, so that residuals are allowed to be arbitrarily correlated **within** a cluster (user, conversation) but treated as independent **across** clusters.

Very schematically, for a linear model with design matrix $X$, coefficients $\hat{\beta}$, and clusters $g = 1, \dots, G$:

$$
\widehat{\text{Var}}_{\text{cluster}}(\hat{\beta})
    = (X'X)^{-1} \Bigg( \sum_{g=1}^G X_g' \hat{u}_g \hat{u}_g' X_g \Bigg) (X'X)^{-1},
$$

where $X_g$ and $\hat{u}_g$ are the rows of $X$ and residuals corresponding to cluster $g$.

**When to use clustered SEs**

* Whenever **randomization happens at a higher level** than the rows you are modeling.
    * e.g., randomize by `conversation_id`, analyze per‑session rows → **cluster by `conversation_id`**.
    * e.g., randomize by `user_id`, analyze per‑event rows → **cluster by `user_id`**.
* Rule of thumb: **cluster at least at the level of randomization**. If in doubt, cluster by the highest natural grouping (usually users).

In the conversation/session example above (conversation‑level randomization, session‑level analysis), we use this clustered variance to keep inference aligned with the randomization unit.

---

## 4. Sample Size Determination and Experiment Planning (high level)

This section captures the **conceptual foundations** of sample size and planning. The concrete helper functions and configuration examples live in `README.md`.

### 4.1 Inputs to sample size calculations

To design an experiment you typically need:

#### Statistical parameters

* **Significance level (α)** – risk of a false positive (Type I error). A common choice is $\alpha = 0.05$.
* **Power (1−β)** – probability of detecting a true effect (1 minus Type II error). A common choice is power = 0.8.

#### Business parameters

* **Baseline level** – current performance of the control variant (rate, mean, etc.).
    * Example: current conversion rate = 3.2% (0.032).
* **Minimum Detectable Effect (MDE)** – smallest change worth detecting, usually defined **relative to the baseline**.
    * Example: baseline = 70% (0.7), MDE = 10% relative improvement → test 0.7 vs 0.77, not 0.7 vs 0.8.
* **Traffic allocation** – proportion of total traffic you are willing to send into the experiment and how you split it between variants (e.g., 50/50 vs 90/10).

#### Metric‑type considerations

* **Proportion metrics** (CTR, conversion rate) – use binomial/normal approximations or exact tests.
* **Continuous metrics** (revenue, time, amount) – require a variance estimate from historical data.
* **Count metrics** (page views, purchases) – may call for Poisson or negative‑binomial models.

### 4.2 Conceptual workflow for planning

At a high level, planning an experiment follows this chain:

```text
Choose α and power → Define meaningful business impact → Translate to MDE →
Choose metric and baseline → Compute required sample size → Map to duration via traffic
```

The framework’s helpers (described in the `README.md` examples) automate the last part of this chain given your choices of α, power, baseline, MDE, and traffic.

### 4.3 Practical considerations

When interpreting required sample sizes and planned durations, you should also account for:

* **Seasonality** – weekly or monthly cycles can change baseline behavior; avoid planning over an unrepresentative window.
* **External factors** – marketing campaigns, product launches, outages, and holidays can all distort results.
* **Multiple testing** – if you look at many metrics or peek frequently, your effective false‑positive rate grows; use corrections or pre‑defined monitoring rules.
* **Variance reduction** – methods like CUPED or stratification can reduce variance and therefore reduce required sample size without changing α or power.

These considerations are general to A/B testing, regardless of the specific implementation. The `README.md` shows how this framework exposes them via configuration fields and helper functions such as `calculate_sample_size(...)` and `calculate_experiment_duration(...)`.

---

## 5. Data Quality, SRM, and Sequential Monitoring

This section collects the theory behind **data quality checks** and **sequential monitoring** that the framework expects users to understand, even though the concrete checks and configuration live in the package API.

### 5.1 Data quality and Sample Ratio Mismatch (SRM)

Even a perfectly specified hypothesis test is only as trustworthy as the **data** fed into it. A key failure mode in online experiments is **Sample Ratio Mismatch (SRM)**:

> You planned to send, say, 50% of units to control and 50% to treatment, but the observed allocation in your logged data is materially different.

Common causes include:

* Bugs in randomization or routing logic
* Silent drop of events in one branch
* Filtering or eligibility rules applied asymmetrically
* Clock/time‑zone bugs or partial log ingestion

#### SRM as a χ² goodness‑of‑fit test

The standard way to diagnose SRM is a **chi‑square (χ²) goodness‑of‑fit test** on the **counts of units** per variant.

Suppose you planned a 50/50 split and observed:

* $n_A$ units in control
* $n_B$ units in treatment

Let $N = n_A + n_B$ and the **expected** counts under the design be $E_A = E_B = N/2$. The chi‑square statistic is:

$$
\chi^2 = \sum_{v \in \{A,B\}} \frac{(n_v - E_v)^2}{E_v}.
$$

Under the null hypothesis of *no SRM* (i.e., routing behaves as designed), this statistic is approximately χ²‑distributed with 1 degree of freedom, and a p‑value $p_\text{SRM}$ is obtained from that distribution.

* If $p_\text{SRM}$ is very small (e.g., $< 10^{-4}$), the imbalance is **extremely unlikely** under proper randomization.
* In that case, results should be treated as **INCONCLUSIVE** until you investigate and fix the underlying issue.

In the framework, the SRM test is conceptually part of a broader **data quality check** that also looks at minimum sample sizes, duration vs. plan, external events, and pipeline health.

### 5.2 Sequential monitoring and peeking

In practice, teams rarely wait strictly until the pre‑planned end of an experiment before looking at results. Every **unplanned peek** at a running p‑value, however, increases the chance of a **false positive** (Type I error) beyond the nominal α.

If you commit in advance to one or more **interim looks**, you should treat the experiment as a **group‑sequential design**:

* The overall experiment is assigned a total α (e.g., 0.05).
* Each interim analysis “spends” part of that α.
* Boundaries such as **O’Brien–Fleming** or **Pocock** specify critical values $Z_1, Z_2, \dots$ for each look so that the **experiment‑level** Type I error stays at 5%.

Conceptually, you can think of an **alpha‑spending function** $\alpha(t)$ that tells you how much of the total α has been spent by information time $t$ (often proportional to cumulative sample size). At each planned look, the instantaneous significance threshold is tighter early on and relaxes as more data accrue.

This framework does **not** implement a full sequential‑design engine. Instead, it:

* Encourages you to plan a small number of interim looks (or none), and
* Surfaces configuration hooks for future extensions (e.g., plugging in alpha‑spending rules), while
* Treating overly frequent, ad‑hoc peeking as a **data quality / process issue** rather than a feature.

The key takeaway for users of this package is methodological:

> Decide on your peeking policy up front, and if you monitor frequently, account for that in your false‑positive budget.

---

## 6. Metric Types and Multiple Metrics

The framework is designed around a **single primary metric per experiment** for clean decision‑making, but in real analyses you often look at **multiple metrics** (primary, guardrail, diagnostics). This section captures the theory behind that choice.

### 6.1 Metric types recap

Broadly, we distinguish:

* **Rate / proportion metrics** – e.g., conversion rate, CTR, success rate
* **Quantity / continuous metrics** – e.g., revenue per user, time on site, items per order
* **Count metrics** – e.g., page views, purchases, events per user (sometimes modeled via Poisson or negative binomial)

From a planning standpoint, rate metrics rely on binomial/normal approximations, continuous metrics rely on variance estimates from historical data, and count metrics may use Poisson‑like models when appropriate. The cheat‑sheet in Section 3 summarizes the core formulas.

### 6.2 Why a single primary metric?

If you **declare one primary metric** per experiment, you can:

* Control the false‑positive rate **directly** at that metric’s α
* Keep the **decision logic simple** (“ship if the primary metric passes, subject to guardrails”)
* Avoid inflating required sample size to satisfy power requirements across many outcomes

Secondary and guardrail metrics are still analyzed, but they are interpreted with more caution and, if strictly tested, should be treated as a **family of tests**.

### 6.3 Multiple testing math

When you test $k$ independent metrics each at level $\alpha$, the probability of **at least one** false positive is:

$$
P(\text{≥1 false positive}) = 1 - (1 - \alpha)^k.
$$

For $k = 5$ and $\alpha = 0.05$, this yields:

$$
1 - 0.95^5 \approx 0.226, \quad \text{or about a 22.6% chance of at least one spurious “win”.}
$$

To keep your **family‑wise error rate (FWER)** under control, you can **adjust** the per‑metric significance level. The classic **Bonferroni correction** uses

$$
\alpha_\text{per metric} = \frac{\alpha_\text{family}}{k}.
$$

More powerful alternatives include **Holm–Bonferroni** (step‑down procedure) and **Benjamini–Hochberg** (which controls the **false discovery rate** rather than FWER).

The practical implication for this framework is not that you must use any specific correction, but that you should:

* Be explicit about which metrics are **primary vs. secondary vs. guardrail**, and
* Be conservative when declaring wins on many metrics at once.

### 6.4 Sample size implications

If you insist that **all** of a set of $k$ metrics have, say, 80% power at some corrected α, the required **sample size** often needs to be larger than for a single‑metric design. A rough conceptual relationship is:

$$
n_\text{multi} \approx n_\text{single} \times f(k, \rho),
$$

where $f(k, \rho)$ grows with the number of metrics $k$ and depends on their correlation structure $\rho$. Highly correlated metrics effectively carry less additional multiple‑testing burden than independent ones.

Because of this complexity, this framework’s initial design:

* Focuses on **one primary metric** for power calculations and Go/NoGo decisions, and
* Treats additional metrics primarily as **guardrails and diagnostics**, not as equally‑powered confirmatory endpoints.

---

## 7. Shadow Testing: Math and Risk Perspective

Shadow testing, as described in the main `README.md`, runs a **new system or model** side‑by‑side with the existing production system on the **same requests**, but only the control’s outputs are shown to users.

From a mathematical standpoint, this setup naturally creates **paired observations**:

* For each request (or unit), control and shadow both produce an outcome.
* The natural unit of analysis is the **request** (or unit) itself, with **two measurements** attached.

### 7.1 Paired t‑test for continuous shadow metrics

For a continuous per‑request metric (e.g., latency, model score, cost), we can form, for each unit $i$:

$$
d_i = y_{i, \text{shadow}} - y_{i, \text{control}}.
$$

If there are $n$ such paired observations, the **paired t‑test** examines whether the mean difference $\bar{d}$ differs from zero:

* $\bar{d}$ = average of the $d_i$
* $s_d$ = sample standard deviation of the $d_i$

The test statistic is

$$
t = \frac{\bar{d}}{s_d / \sqrt{n}},
$$

which, under the null hypothesis of **no systematic difference** between shadow and control, is approximately t‑distributed with $n-1$ degrees of freedom. A two‑sided p‑value then quantifies how compatible the observed differences are with “no change”.

Because each request serves as its **own control**, this test can be much more powerful than comparing two independent samples.

### 7.2 McNemar’s test for paired binary outcomes

For **binary** per‑request outcomes (e.g., “did this trigger a safety filter?”, “was this classification correct?”), you can summarize the joint outcomes in a 2×2 table:

|              | Shadow = 0 | Shadow = 1 |
|--------------|------------|------------|
| Control = 0  |    $n_{00}$    |    $n_{01}$    |
| Control = 1  |    $n_{10}$    |    $n_{11}$    |

McNemar’s test focuses on the **discordant pairs** $n_{01}$ and $n_{10}$ (where control and shadow disagree). The test statistic is

$$
\chi^2_\text{McN} = \frac{(\lvert n_{01} - n_{10} \rvert - 1)^2}{n_{01} + n_{10}},
$$

which, under the null hypothesis that the **marginal probabilities** are the same (no net change between control and shadow), is approximately χ²‑distributed with 1 degree of freedom. This gives a p‑value for whether shadow changes the outcome rate.

### 7.3 Risk framing

Shadow testing sits in the experimentation pipeline as a **risk‑mitigation layer**:

1. **Technical risk** – detect regressions in latency, error rates, or resource usage before any user sees the new system.
2. **Policy / safety risk** – measure whether a new model violates more safety constraints, even if it looks promising on offline metrics.
3. **Cost risk** – quantify changes in infrastructure or API spend per request.

The framework’s role is to **summarize these paired comparisons** and feed them into a decision process such as:

* “Safe to proceed to an online A/B test with user exposure?”
* “Need to iterate on the shadow model further?”

The **A/B testing** phase then takes over for user‑centric and business metrics.

---

## 8. Decision Framework: Statistical vs Business Significance

This section explains the theory underlying the Go/NoGo decision helpers exposed by the framework (e.g., `check_statistical_significance`, `check_business_significance`, `check_data_quality`, and `make_go_nogo_decision`).

### 8.1 Statistical significance

Given a test statistic (e.g., z‑statistic for proportions, t‑statistic for means) and a chosen significance level $\alpha$:

* A **p‑value** quantifies how extreme the observed data are under the null hypothesis of “no difference”.
* If $p < \alpha$, we say the result is **statistically significant** at level $\alpha$.

Importantly, $p < 0.05$ does **not** mean “there is a 95% chance the effect is real”; rather, it means “if there were truly no effect, we would see data at least this extreme at most 5% of the time under repeated experiments.”

The framework therefore treats statistical significance as a **necessary but not sufficient** condition for shipping.

### 8.2 Business / practical significance

Business stakeholders care about **effect size**, not just whether it is non‑zero. We define:

* An **MDE** (minimum detectable effect) up front, based on what is **meaningful** in context.
* An **observed lift** from the experiment (absolute or relative), denoted $L$.

We say an effect is **business‑significant** if $|L| \ge \text{MDE}$. In practice, many teams prefer a **safety margin**, e.g., requiring $|L|$ to be somewhat larger than the MDE before shipping.

Combining this with confidence intervals provides a richer view:

* If the entire confidence interval lies above the MDE, the business case is very strong.
* If the interval straddles the MDE, results are more borderline and often lead to “EXTEND” or “Ship with monitoring” recommendations.

### 8.3 Data quality as a gate

Even a statistically and practically compelling effect should **not** be shipped if the underlying data are unreliable. That is why the decision helpers place **data quality checks first**:

* SRM and routing sanity
* Sufficient sample size vs. plan
* Duration long enough to cover key cycles (e.g., at least one full week for weekly seasonality)
* Known external shocks (outages, major marketing campaigns)
* Pipeline health (missing data rates, schema changes)

If any of these fail in a serious way, the framework recommends an **INCONCLUSIVE** outcome: fix issues and re‑run.

### 8.4 Combined decision logic

Putting the three dimensions together gives a simple yet powerful **decision matrix** that the framework’s helpers encode:

* **GO** – data quality is high, the effect is statistically significant and business‑meaningful, and guardrails are not violated.
* **NO‑GO** – high‑quality data but either the effect is harmful (e.g., significant negative lift) or too small to matter.
* **EXTEND** – data look clean and the effect is directionally promising but not yet statistically significant; often implies running longer or increasing sample size.
* **INCONCLUSIVE** – data quality problems or severe process issues; the safest action is to diagnose and repeat.

This separation of concerns (statistics vs. business vs. data quality) is central to how the package structures its APIs and outputs in `README.md`. The theory lives here; the concrete function signatures and example usage remain with the package documentation.

