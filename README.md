> Purpose: Main project overview, installation instructions, quickstart guide, and comprehensive framework documentation.
> Generated: Manually authored, maintained under version control.

[TOC]

# 🧠 A/B Testing Analysis Standardization Layer

> **How to use these docs**
>
> * Start with this `README.md` to understand what the **standardization layer** does, how it fits into your experimentation stack, and how to configure and call its APIs.
> * Use `AB_TESTING_THEORY.md` for the detailed statistical background: full math, derivations, and methodology justifications that underpin the helpers and decisions described here.

## 1. 🔬 Understanding A/B Testing: Goals and Fundamentals

### What is A/B Testing?

**A/B testing** (also called split testing) is a randomized controlled experiment that compares two or more versions of a product feature, algorithm, or user experience to determine which performs better on specific business metrics.

### Core Goals of A/B Testing

* **Causal Inference**: Establish whether changes directly cause improvements in business metrics
* **Risk Mitigation**: Test changes on a subset before full rollout to minimize potential negative impact
* **Data-Driven Decisions**: Replace intuition and opinions with statistical evidence
* **Continuous Optimization**: Iteratively improve products through systematic experimentation
* **Business Impact Measurement**: Quantify the effect of changes on key performance indicators (KPIs)

### Key A/B Testing Methodology

#### 1. **Hypothesis Formation**
```
H₀ (Null): No difference between variant A and variant B
H₁ (Alternative): Variant B performs better than variant A by at least X%
```

#### 2. **Experimental Design**
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

### Who Does What: Experimentation System vs. Analysis Framework

To keep responsibilities clean and avoid mixing concerns, we explicitly separate:

#### 1. Experimentation / Product / Logging System (Upstream)

This is your existing system that owns **traffic and logging**. It is responsible for:

* **Randomization & Routing**
    * Choose the **unit of randomization** (`unit_id` such as `user_id`, `conversation_id`, `session_id`)
    * Assign each unit to a **variant label** (e.g., `control`, `treatment`, `variant_A`, `variant_B`, `shadow_variant_B`)
    * For **shadow testing**:
        * Route all real user responses from the **control** variant
        * In parallel, send a copy of the same requests to a **shadow variant** (e.g., `shadow_variant_B`), but never expose its outputs to users

* **Data Capture**
    * Produce an **assignment table**, for example:

        ```text
        unit_id | variant_label      | assignment_timestamp | mode
        ------- | ------------------ | -------------------- | ------
        U1      | control            | 2025-11-10T10:00:00Z | live
        U1      | shadow_variant_B   | 2025-11-10T10:00:00Z | shadow
        ```
    * Produce an **events/metrics table**, for example:

        ```text
        unit_id | variant_label      | metric_value | timestamp           | ...
        ------- | ------------------ | ------------ | ------------------- | ---
        U1      | shadow_variant_B   | 0.029        | 2025-11-10T10:00:01Z| ...
        ```

* **Shadow Awareness**
    * Knows which variants are **shadow-only** vs. user-visible
    * Ensures user experience is **never** impacted by shadow outputs

#### 2. A/B Analysis Framework (This Package)

This framework sits **on top of** the experimentation system and owns **math and decisions**, not routing. It:

* Treats `unit_id` and `variant_label` as **opaque data**
    * It doesn't know or care whether `variant_label` is `control`, `variant_B`, or `shadow_variant_B` beyond grouping and comparison

* Provides **metric abstraction**
    * You pass in a metric function, e.g.:

        ```python
        def metric(df: pd.DataFrame) -> float:
                return df["conversions"].sum() / df["visitors"].sum()
        ```

* Implements the **statistical engine**
    * Aggregates data by `unit_id` and `variant_label`
    * Computes per-variant metrics
    * Runs hypothesis tests, confidence intervals, power/sample size, etc.

* Drives **Go/NoGo decisions**
    * Compares any pair of variants (e.g., `control` vs `shadow_variant_B` during shadow, `control` vs `variant_B` during A/B)
    * Produces structured recommendations (GO / NO-GO / EXTEND / INCONCLUSIVE)

From the framework's point of view, **shadow variants are just additional variant labels**. The special behavior of "shadow" (not user-visible, used only for pre-A/B validation) is enforced entirely by the upstream system.

### Choosing the Unit of Randomization vs. Unit of Analysis (Framework View)

When configuring this package you must choose a **`unit_id`** (for example `user_id`, `conversation_id`, or `session_id`). In practice:

* Most product teams should start with **user‑level experiments** (`unit_id = user_id`) for user‑centric metrics.
* Conversation‑ or session‑level units are appropriate only when the metric and experience are truly conversation/session‑centric and you are comfortable with mixed exposure across a user’s lifetime.

The detailed trade‑offs (including the bot example, correlation, and cluster‑robust analysis) are covered in:

*See: `AB_TESTING_THEORY.md` – Section 2, “Choosing the Unit of Randomization vs. Unit of Analysis”.*

### Statistical Framework (high level)

For this package, you mainly need to configure a small set of **statistical knobs**. Under the hood, the framework delegates actual test computations to well‑known Python libraries via **pluggable backends** (currently `owl_ab_test`, with a `scipy` backend planned as a fallback). The orchestration layer stays the same even if the backend changes.

* **Significance level (α)** – false‑positive budget (often 0.05).
* **Statistical power (1−β)** – probability of detecting a true effect when it exists (often 0.8).
* **Minimum Detectable Effect (MDE)** – smallest lift that is business‑meaningful, defined relative to the baseline.
* **Sample size** – number of randomized units required, computed from the above.

Under the hood, the framework uses standard tests implemented in the chosen backend:

* Proportion tests for **rate metrics** (e.g., conversion, CTR).
* Mean tests (e.g., Welch’s t‑test) for **continuous metrics** (e.g., revenue per user, time).
* Confidence intervals around estimated lifts.

All formulas, variance definitions, sample‑size equations, and clustered standard‑error details live in the theory reference:

*See: `AB_TESTING_THEORY.md` – Section 3, “Statistical Framework & Math Cheat‑Sheet”.*

> **Note on traffic / data‑quality monitoring**  
> This library **does not** implement runtime traffic monitoring, SRM alerting, or “daily sample health” checks. Those responsibilities live in your upstream experimentation / logging system (dashboards, alerts, data‑quality monitors).  
> The theory reference describes recommended practices for these checks in **AB_TESTING_THEORY.md – Section 5.0.1, “Traffic and Data Quality Monitoring (daily checks)”**, but they are intentionally **out of scope** for this analysis layer’s APIs.

## Repository Structure

- `ab_framework/`: Core A/B testing framework package
- `data/`: Shared CSV scenario data generated by `verification/data_generator.py`
- `verification/`: Cross-library verification harness, ground truth, and scenario docs/tests (reads from `data/`)
- `demos/`: Example scripts and markdown showing realistic workflows

## 3. 📊 Sample Size Determination: The Foundation

This framework exposes **sample-size planning** via the statistical backend interface (`StatisticalBackend`). In practice, you call backend helper methods like `sample_size_proportion` and `sample_size_mean` to turn your **statistical choices** into concrete **sample sizes and durations**.

At configuration time you typically provide:

* Statistical parameters: **α**, **power (1−β)**, and an **MDE** (defined relative to the baseline).

Given these, the helpers:

* Compute the **required sample size per variant** for your primary metric, and
* Map that requirement into an **estimated number of days** given your historical traffic and chosen experiment‑traffic percentage.

All underlying formulas (e.g., for proportions, continuous metrics, and practical considerations such as seasonality, external shocks, and variance reduction) are detailed in:

*`AB_TESTING_THEORY.md` – Section 4, “Sample Size Determination and Experiment Planning (high level)”.*

---

## 4. 🎯 Complete A/B Testing Workflow

### Step-by-Step Process


High‑level planning follows:

```
Choose α and power → Define meaningful business impact → Translate to MDE →
Choose metric and baseline → Compute required sample size → Map to duration via traffic
```

In code, this looks like configuring parameters and then calling backend helpers from an `ABTest` instance. For example:
```python
# Step 1: Choose statistical parameters
alpha = 0.05          # 5% false positive rate
power = 0.80          # 80% chance to detect real effect

# Step 2: Define meaningful business impact
baseline_rate = 0.032  # Current 3.2% conversion rate
meaningful_lift = 0.10 # Want to detect 10% relative improvement
mde = baseline_rate * meaningful_lift  # 0.0032 (0.32 percentage points)

# Step 3: Determine traffic allocation
traffic_allocation = {"control": 0.50, "treatment": 0.50}  # 50/50 split
experiment_traffic_pct = sum(traffic_allocation.values())  # 1.0 = 100% of users

# Step 4: Calculate required sample size per variant (control/treatment)
from ab_framework import ABTest

planning_test = ABTest(
    name="planning_only",
    data=pd.DataFrame({"user_id": [1, 2], "variant": ["A", "B"]}),
)

result = planning_test.backend.sample_size_proportion(
    baseline_rate=baseline_rate,
    mde=mde,
    alpha=alpha,
    power=power,
)

total_sample_size = result['total_size']
print(f"  Control: {result['control_size']:,}")

# Step 5: Estimate experiment duration (manual calculation)
daily_users = 10000  # Historical average daily user count
daily_experiment_users = daily_users * experiment_traffic_pct

duration_days = math.ceil((total_sample_size * buffer_factor) / daily_experiment_users)
print(f"Estimated duration: {duration_days} days")
```

The **theory details** behind these calculations (effects of seasonality, external factors, multiple testing, and variance reduction) are covered in the theory reference. Here in the README we focus on **how to call** the helpers and wire them into your planning flow.

For more on planning theory, see:

*`AB_TESTING_THEORY.md` – Section 4, “Sample Size Determination and Experiment Planning (high level)”.*

**Example Scenarios (framework usage with backend helpers):**
```python
import math
from ab_framework import ABTest

planning_test = ABTest(
    name="planning_only",
    data=pd.DataFrame({"user_id": [1, 2], "variant": ["A", "B"]}),
)

# Get required sample size for a proportion metric
result = planning_test.backend.sample_size_proportion(
    baseline_rate=0.10,
    mde=0.05,
    power=0.80,
    alpha=0.05,
)
required_sample_size = result['total_size']

# Scenario 1: High traffic site, full allocation
daily_experiment_users = 50000 * 1.0
duration = math.ceil((required_sample_size * 1.2) / daily_experiment_users)
# Result: ~3 days

# Scenario 2: Conservative allocation (50% of users)
daily_experiment_users = 50000 * 0.5
duration = math.ceil((required_sample_size * 1.2) / daily_experiment_users)
# Result: ~5 days

# Scenario 3: Lower traffic site
daily_experiment_users = 5000 * 1.0
duration = math.ceil((required_sample_size * 1.2) / daily_experiment_users)
# Result: ~24 days
```

#### 2. **A/A Testing Phase (Critical First Step)**
**Before running A/B tests, always run A/A tests to validate your system:**

```python
# A/A Test Configuration
import math

required_sample_size = 10000  # Smaller sample for validation
daily_traffic = 10000
experiment_traffic_pct = 1.0
buffer_factor = 1.1

daily_experiment_users = daily_traffic * experiment_traffic_pct
aa_duration_days = math.ceil((required_sample_size * buffer_factor) / daily_experiment_users)

aa_test = {
    "control": "variant_A",
    "treatment": "variant_A",  # Same as control!
    "traffic_allocation": {
    "control": 0.50,          # 50% get control (control_model)
    "treatment": 0.50         # 50% get treatment (also control_model!)
    },
    # total_experiment_traffic = sum(traffic_allocation) = 1.0 (calculated automatically)
    "duration_days": aa_duration_days  # Calculated: typically 2-3 days
}
```

**What A/A Testing Validates:**
* **Randomization System**: Traffic is split correctly (no Sample Ratio Mismatch)
* **Data Pipeline**: Events are captured and attributed properly  
* **Statistical Framework**: False positive rate matches expected α
* **Infrastructure**: No technical biases or bugs in assignment logic

At a theory level, SRM checks are typically implemented via a **χ² goodness‑of‑fit test** on counts per variant, and frequent peeking at p‑values must be accounted for via sequential‑testing corrections. Those details live in:

*`AB_TESTING_THEORY.md` – Section 5, “Data Quality, SRM, and Sequential Monitoring”.*

**A/A Test Success Criteria (package view):**
* **SRM Check Passed**: Traffic split matches expected allocation (p > 0.001)
* **No Significant Differences**: Metrics show no statistically significant difference (p‑value > α)
* If a difference appears significant, or SRM is flagged, investigate before proceeding to A/B testing

#### Understanding Sample Ratio Mismatch (SRM) in Detail

**What is SRM?**

Sample Ratio Mismatch (SRM) detects when the actual distribution of users across experiment variants differs significantly from the expected allocation. This is a **critical data quality check** that must pass before trusting any experiment results.

**Why SRM Matters:**
- Broken randomization invalidates all metric results
- Even statistically significant results cannot be trusted if SRM is detected
- Common causes: buggy assignment logic, biased filtering, technical issues, bot traffic, data pipeline errors

**The Statistical Test: Chi-Square Goodness-of-Fit**

SRM uses a **chi-square (χ²) test** to compare observed vs. expected user counts:

```
χ² = Σ [(observed - expected)² / expected]

For 2 variants:
χ² = [(n_control - E_control)² / E_control] + [(n_treatment - E_treatment)² / E_treatment]
```

**Example Calculation:**
```python
# Expected 50/50 split with 1000 total users
expected_control = 500
expected_treatment = 500

# Observed: 450 control, 550 treatment
observed_control = 450
observed_treatment = 550

χ² = (450 - 500)² / 500 + (550 - 500)² / 500
   = 2500 / 500 + 2500 / 500
   = 5.0 + 5.0
   = 10.0

# Convert χ² to p-value (degrees of freedom = 1)
p-value ≈ 0.0016

# Since p < 0.001 (SRM alpha threshold) → SRM DETECTED ⚠️
```

**P-Value Interpretation for SRM:**
- **p-value**: "If randomization was working correctly, how surprising is this mismatch?"
- **p > 0.001**: ✅ Mismatch is within normal random variation
- **p < 0.001**: ❌ Mismatch is too extreme to be random chance alone

**Why alpha=0.001 for SRM (stricter than metric tests)?**
- Metric tests use α=0.05 (5% false positive rate)
- SRM uses α=0.001 (0.1% false positive rate)
- We only raise SRM alarms when **extremely confident** something is broken
- This prevents false alarms from normal day-to-day traffic fluctuations

**SRM for Non-50/50 Splits:**

The framework supports any traffic allocation (e.g., 70/30, 90/10):

```python
# 70% control / 30% treatment with 1000 users
expected_control = 700
expected_treatment = 300

# Observed: 680 control, 320 treatment
χ² = (680 - 700)² / 700 + (320 - 300)² / 300
   = 400 / 700 + 400 / 300
   = 0.571 + 1.333
   = 1.904

p-value ≈ 0.168 → No SRM (within normal variation)
```

**SRM Monitoring Over Time:**

The framework enables tracking SRM **per-day** to catch issues early:

```python
# Day-by-day SRM checks
Day 1: 78 control / 82 treatment, expected 80/80 → p=0.752 ✅ PASS
Day 2: 112 control / 128 treatment, expected 120/120 → p=0.302 ✅ PASS  
Day 5: 450 control / 550 treatment, expected 500/500 → p=0.002 ❌ SRM DETECTED

# Visual tracking: Plot T/C ratio over time with confidence intervals
# Red dots = SRM detected on that day → STOP and investigate
```

**Recommended Visualizations:**
1. **SRM History Graph**: Treatment/Control ratio per day with 95% CI error bars
   - Y-axis: Observed T/C ratio (e.g., 1.0 for 50/50, 0.43 for 30/70)
   - Expected ratio shown as horizontal dashed line
   - Green dots: CI crosses expected ratio (no SRM)
   - Red dots: CI doesn't cross expected ratio (SRM detected)

2. **Metric Value Over Time**: Track how metrics evolve day-by-day
   - Separate lines for control vs treatment
   - Helps identify when changes stabilize
   - Useful for detecting temporal effects

3. **P-Value Over Time**: Monitor statistical significance progression
   - Shows when experiment reaches significance
   - Helps prevent premature stopping
   - Identifies trends in effect size stability

**Framework Implementation:**

```python
from ab_framework import ABTest

test = ABTest(
    name="homepage_redesign",
    data=df,
    variant_col="variant",
    unit_id="user_id",
)

# Configure analysis knobs (including treatment allocation) after construction
test.setup(
    treatment_fraction=0.3,  # Treatment allocation: 30% of traffic to treatment, 70% to control
)

# Run analysis with automatic SRM check
results = test.analyze(run_srm_check=True)

# Check SRM result
if not results.srm_result['passed']:
    print("⚠️ SRM DETECTED - DO NOT TRUST METRIC RESULTS")
    print(results.srm_result['recommendation'])
    # Example output:
    # [WARNING] SRM DETECTED (p=0.000123, alpha=0.001)
    # Variant B deviates by +15.2%
    # Action: Check randomization logic and data collection
```

#### 3. **A/B Testing Phase**
```python
# A/B Test Configuration - Different Traffic Allocation Options

# Calculate duration based on sample size and traffic
import math

required_sample_size = 38415  # From sample size calculation
daily_traffic = 10000
buffer_factor = 1.2

# Full allocation
ab_duration_full_days = math.ceil(
    (required_sample_size * buffer_factor) / (daily_traffic * 1.0)
)

# Conservative allocation
ab_duration_conservative_days = math.ceil(
    (required_sample_size * buffer_factor) / (daily_traffic * 0.5)
)

# Option 1: 50/50 split of ALL traffic
ab_test_full = {
    "control": "variant_A",       # Current version - 50% of users
    "treatment": "variant_B",   # New version - 50% of users
    "traffic_allocation": {
        "control": 0.50,              # 50% get control
        "treatment": 0.50             # 50% get treatment
    },
    # total_experiment_traffic = sum(0.50 + 0.50) = 1.0 (100% of users)
    "duration_days": ab_duration_full_days  # Calculated duration
}

# Option 2: Conservative split - only 50% of users in experiment
ab_test_conservative = {
    "control": "variant_A",       # Current version - 25% of users  
    "treatment": "variant_B",   # New version - 25% of users
    "traffic_allocation": {
        "control": 0.25,              # 25% get control
        "treatment": 0.25             # 25% get treatment
    },
    # total_experiment_traffic = sum(0.25 + 0.25) = 0.50 (50% of users)
    # remaining 50% automatically get normal production (not tracked by framework)
    "duration_days": ab_duration_conservative_days  # Calculated duration (2x longer)
}

# Option 3: Uneven split for high-risk changes
ab_duration_uneven_days = math.ceil(
    (required_sample_size * buffer_factor) / (daily_traffic * 1.0)
)

ab_test_uneven = {
    "control": "variant_A",       # Current version - 90% of experiment users
    "treatment": "variant_B",   # New version - 10% of experiment users  
    "traffic_allocation": {
        "control": 0.90,              # 90% get control
        "treatment": 0.10             # 10% get treatment
    },
    # total_experiment_traffic = sum(0.90 + 0.10) = 1.0 (100% of users)
    "duration_days": ab_duration_uneven_days  # Calculated duration
}

# Framework Validation Logic
def validate_traffic_allocation(config):
    """Validate traffic allocation doesn't exceed 100%"""
    allocation = config['traffic_allocation']
    
    # Calculate total experiment traffic (only experiment variants)
    experiment_traffic = sum(allocation.values())
    non_experiment_traffic = 1.0 - experiment_traffic
    
    # Validation checks
    if experiment_traffic > 1.0:
        raise ValueError(f"Experiment traffic allocation {experiment_traffic:.3f} exceeds 1.0 (100%)")
    
    if experiment_traffic <= 0:
        raise ValueError("Experiment traffic must be greater than 0")
        
    if any(v < 0 for v in allocation.values()):
        raise ValueError("Traffic allocation values cannot be negative")
    
    return {
        "experiment_traffic": experiment_traffic,
        "non_experiment_traffic": non_experiment_traffic,
        "is_valid": True
    }
```

#### 4. **Analysis and Conclusions**
```python
# Statistical Analysis
results = {
    "control_metric": 0.032,     # 3.2% conversion
    "treatment_metric": 0.035,   # 3.5% conversion  
    "lift": 0.094,               # 9.4% relative improvement
    "p_value": 0.023,            # Statistically significant
    "confidence_interval": [0.001, 0.005],  # 95% CI for difference
    "recommendation": "SHIP"      # Business decision
}
```

### 🎯 Go/NoGo Decision Framework

The package exposes helpers to combine **statistics**, **business impact**, and **data quality** into a single structured recommendation (`GO`, `NO-GO`, `EXTEND`, `INCONCLUSIVE`). At a practical level you:

* Compute a p‑value and lift for your **primary metric**.
* Compare the lift against your configured **MDE**.
* Run data‑quality checks (SRM, duration vs. plan, pipeline health, guardrails).
* Feed these into a small decision helper that returns a decision, reason, and suggested next action.

The underlying theory—how to think about statistical vs business significance, why data quality is a first‑class gate, and how the decision matrix is structured—is detailed in:

*`AB_TESTING_THEORY.md` – Section 8, “Decision Framework: Statistical vs Business Significance”.*

Here in the README, the focus is on **how to interpret** the outputs of those helpers and wire them into your experimentation workflow. A typical decision summary returned by the framework might look like:

```python
decision_report = {
    "experiment_id": "homepage_banner_v2",
    "decision": "GO",
    "confidence": "HIGH",
    "statistical_summary": {
        "p_value": 0.008,
        "lift": 0.12,  # 12% relative improvement
        "ci_lower": 0.045,
        "ci_upper": 0.195
    },
    "business_impact": {
        "estimated_revenue_increase": "$2.5M annually",
        "roi": 15.2,
        "payback_period": "2.3 months"
    },
    "risks": [
        "Minor increase in page load time (+50ms)",
        "Requires A/B test monitoring for 2 weeks post-launch"
    ],
    "next_steps": [
        "Deploy to 10% of users for 1 week",
        "Monitor key guardrails closely",
        "Full rollout if no issues detected"
    ]
}
```

---

## 5. 📊 Metric Types: Rate vs. Quantity

### Rate Metrics (Proportions)
**Definition**: Ratio of successes to total opportunities
- **Examples**: Conversion Rate, Click-Through Rate, Success Rate
- **Formula**: `rate = successes / total_trials`
- **Statistical Test**: Z-test for proportions, Chi-square test
- **Sample Size**: Based on binomial distribution

```python
def conversion_rate(df):
    return df['conversions'].sum() / df['visitors'].sum()

# Sample size formula for rates
n_rate = 2 * (z_alpha + z_beta)² * p̂(1-p̂) / (effect_size)²
```

### Quantity Metrics (Continuous)
**Definition**: Measurements of amounts, durations, or counts per unit
- **Examples**: Revenue per User, Time on Site, Items per Order
- **Formula**: `quantity = total_amount / total_units`  
- **Statistical Test**: T-test for means, Mann-Whitney U (non-parametric)
- **Sample Size**: Based on variance estimation

```python
def revenue_per_user(df):
    return df['revenue'].sum() / df['users'].nunique()

# Sample size formula for continuous metrics
n_continuous = 2 * (z_alpha + z_beta)² * σ² / (effect_size)²
```

### Key Differences in Analysis

| Aspect | Rate Metrics | Quantity Metrics |
|--------|--------------|------------------|
| **Distribution** | Binomial → Normal (large n) | Often normal or log-normal |
| **Variance** | p(1-p) | Estimated from historical data |
| **Sample Size** | Depends on baseline rate | Depends on variance estimate |
| **Effect Size** | Absolute or relative % points | Absolute or relative units |
| **Common Issues** | Low baseline rates need large n | High variance inflates required n |

---

## 6. 🔢 Single vs. Multi-Metric Testing

### Current Framework Scope: Single Primary Metric
**For this framework’s decision helpers, we focus on ONE primary metric per experiment:**
- Simpler statistical analysis
- Clear decision-making criteria  
- Avoids multiple testing problems
- Easier to interpret business impact

### Multi-Metric Testing: Mathematical Considerations

**When testing multiple metrics simultaneously, statistical challenges arise:**

#### 1. **Multiple Testing Problem**
```
P(at least one false positive) = 1 - (1-α)^k

Where:
- k = number of metrics tested
- α = significance level per test

Example: Testing 5 metrics at α=0.05
P(false positive) = 1 - (0.95)^5 = 0.226 (22.6%!)
```

#### 2. **Bonferroni Correction**
```
α_adjusted = α / k

Example: 5 metrics, α=0.05
α_per_test = 0.05 / 5 = 0.01
```

#### 3. **Family-Wise Error Rate (FWER) Control**
- **Bonferroni**: Conservative, controls FWER exactly
- **Holm-Bonferroni**: Less conservative, step-down method
- **Benjamini-Hochberg**: Controls False Discovery Rate (FDR)

#### 4. **Sample Size Impact**
```
n_multi = n_single × correction_factor

Where correction_factor depends on:
- Number of metrics (k)
- Correlation between metrics
- Desired power for each metric
```

#### 5. **Advanced Approaches**
- **Hierarchical Testing**: Primary → Secondary → Tertiary metrics
- **Composite Metrics**: Combine multiple metrics into single score
- **Bayesian Multi-Armed Bandits**: Dynamic allocation based on posterior

**Framework Future Enhancement**: Multi-metric support with proper statistical corrections

---

## 7. 🎯 Framework Purpose and Vision

An internal, reusable **A/B testing analysis standardization layer** in Python — a package that is **agnostic to the product domain**, **metric type**, **statistical backend**, and **treatment design**, yet flexible enough to plug into *any system* where A/B experiments run (web UI, backend algorithms, etc.).

### Core Mission

* **Ingest near real-time experiment data** (from log files or streams)
* **Compute experiment metrics dynamically**, regardless of whether they are CTR, Conversion Rate, Revenue per User, etc.
* **Orchestrate rigorous statistical analysis** (power, alpha, confidence intervals, significance tests) using pluggable backends such as `owl_ab_test` or `scipy`.
* **Monitor experiment progress and data quality** (sample size, traffic balance, contamination, etc.)
* **Be modular**, allowing integration into different company systems and different types of experiments, without coupling callers to any particular stats library.

---

## 8. 🏗️ Context and Existing Infrastructure

The framework integrates with a **running experimentation system** that:

* Controls **traffic allocation** between control and treatment variants
* Allows **defining randomization rules** (percentage, user/session-based)
* Produces **log files or data streams** that include:
    * Population assignment (unit_id → treatment label such as control/treatment)
  * Events or actions to measure
  * Data available for on-demand querying

### Framework's Role in Data Science Workflow

* **Automate sample size calculations** based on user-defined parameters
* **Standardize statistical testing** across different experiment types and underlying libraries
* **Provide real-time experiment monitoring** and data quality checks
* **Generate interpretable reports** for stakeholders and decision-makers
* **Ensure statistical rigor** while keeping the choice of backend implementation an internal concern

---

## 9. 🧩 Core Components and Architecture

### A. **Setup / Configuration Stage**

User (analyst or experiment owner) defines:

* **Unit of randomization**: A unique identifier (`unit_id`) — could be `user_id`, `session_id`, `account_id`, etc. The framework treats it as opaque (no semantic meaning, just grouping key).

* **Metric definition method**: A user-defined function such as:

  ```python
  def metric(df: pd.DataFrame) -> float:
      # Custom aggregation logic (CTR, conversion rate, etc.)
      return (df["clicks"].sum() / df["views"].sum())
  ```

    This ensures full flexibility — the framework only requires a single numeric output per unit or per treatment variant.

* **Experiment configuration**:

  ```yaml
  experiment:
      name: "homepage_banner_test"
      alpha: 0.05
      power: 0.8
      metric: ctr_metric
      unit_id: user_id
      expected_duration_days: 7
  ```

---

### B. **Data Ingestion and Transformation**

**On-Demand Architecture**: The framework operates in an on-demand mode where analysis is computed when requested, rather than continuously running in the background.

* **On-demand data fetching**: Read all experiment data since experiment start when `get_latest_analysis()` is called
* **Data sources**: Supports logs (local files, S3, blob storage), databases, or data streams
* **Processing**: Clean and preprocess data (deduplicate, handle missing data, ensure correct treatment assignment)
* **Aggregation**: Aggregate by `unit_id` and `variant_label` (with values such as control/treatment) to produce:

    ```
        unit_id | variant_label | metric_value | timestamp
    ```

**Key Benefits**:
* ✅ Simpler architecture (no schedulers, no background processes)
* ✅ Stateless operation (each call is independent)
* ✅ User controls when to analyze (flexible timing)
* ✅ Always computes from latest available data

**Optional Optimization**: For large datasets, implement incremental processing with caching to improve performance on repeated calls.

---

### C. **Statistical Engine**

Implements the statistical backbone:

* **Power & sample size estimation** (given baseline rate, MDE, alpha, power)
* **Hypothesis testing**:
  * Proportion tests (CTR, conversion)
  * Mean tests (time spent, revenue)
  * Optional: nonparametric or Bayesian methods
* **Confidence intervals** and **p-values** for reporting
* **Sequential monitoring** (optional) — avoid premature stopping

The statistical layer should be modular (so one can plug frequentist or Bayesian modules).

---

### D. **Monitoring & Reporting**

* **On-demand dashboards** showing:
  * Sample size progress vs. required size
    * Control vs. treatment balance check (traffic allocation validation)
  * Metric drift and variance trends
  * Statistical significance at time of request
* **Analysis results** returned include:
    * Current metrics for control and treatment
  * Statistical test results (p-values, confidence intervals)
  * Sample size adequacy assessment
  * SRM check results
  * Recommendations (continue/stop experiment)

---

### E. **Extensibility**

The framework should:

* Work with *different metric functions* (user-defined)
* Support *different experiment granularities* (per user, session, region, etc.)
* Allow *different data sources* (local, cloud logs, SQL, Kafka)
* Integrate with external libraries (e.g., SciPy, EconML, Plotly, etc.)
* Be deployable as:
  * A standalone Python module
  * A microservice in a data platform
  * Or a notebook-based toolkit for analysts

---

## 10. ⚙️ Technical Flow Overview

### On-Demand Analysis Pattern

```
[User/Service requests analysis]
       ↓
[Fetch all data since experiment start]
       ↓
[Data ingestion + cleaning layer]
       ↓
[Metric calculation (user-defined)]
       ↓
[Experiment summary dataset]
       ↓
[Statistical analysis module]
       ↓
[Return results (metrics, tests, CI)]
```

### Usage Examples

**API Service**:
```python
@app.get("/experiments/{experiment_id}/analysis")
def get_experiment_analysis(experiment_id: str):
    framework = ABTestFramework.load(experiment_id)
    return framework.get_latest_analysis()
```

**Interactive Notebook**:
```python
framework = ABTestFramework(config)
results = framework.get_latest_analysis()
display(results)
```

**Dashboard Refresh**:
```python
# Called when user clicks "Refresh" button
results = framework.get_latest_analysis()
update_dashboard(results)
```

---

## 11. 🔄 Shadow Testing: Pre-A/B Risk Mitigation

### What is Shadow Testing?

**Shadow testing** (or shadow deployment) is a crucial experimental methodology that runs a new system or model **in parallel** with the existing production system, using the same real-world traffic, but **without exposing its outputs to users**.

### How Shadow Testing Works

* All users continue to see the **control experience** (current production system)
* The **treatment experience** (new system) processes the same requests in the background
* Metrics are collected for the new system (latency, accuracy, resource usage) without impacting user experience
* Results provide early validation before proceeding to full A/B testing

### Shadow Testing vs. A/B Testing

| Aspect | Shadow Testing | A/B Testing |
|--------|----------------|-------------|
| **User Impact** | None (users only see control) | Users are split between control and treatment |
| **Data Collected** | Backend metrics only (no user engagement) | Full user interaction and engagement metrics |
| **Cost** | Higher (duplicate processing of requests) | Lower (single execution per user) |
| **Risk** | Zero user-facing risk | Potential negative user experience |
| **Generalization** | Limited—doesn't capture behavioral changes | Strong—results generalize to real-world impact |

### When to Use Shadow Testing

✅ **Ideal for**:
* Backend algorithm changes or model updates
* System migrations or infrastructure changes
* Early validation of potentially risky features
* Performance and stability testing under real load
* Changes that cannot be easily split across users

❌ **Not suitable for**:
* UI/UX changes requiring user interaction
* Features requiring user feedback for validation
* Simple configuration changes with low risk
* Cost-sensitive scenarios (doubles infrastructure load)

### Role in Experimentation Workflow

Shadow testing serves as a **pre-filter** before A/B testing:

```
[Development] → [Shadow Testing] → [A/B Testing] → [Full Rollout]
```

1. **Shadow Phase**: Validate technical performance and stability
2. **A/B Phase**: Measure user behavior and business impact
3. **Rollout Phase**: Deploy to all users based on positive results

### Framework Integration

The framework supports shadow testing through:

* **Dual Processing Mode**: Process requests for both control and shadow systems
* **Backend Metrics Collection**: Capture performance, accuracy, and system metrics
* **Statistical Comparison**: Compare shadow vs. control using paired statistical tests
* **Risk Assessment**: Evaluate readiness for A/B testing based on shadow results

### Shadow Testing: Math View

Because **control** and **shadow** see the exact same requests at the same time, we can often treat their outcomes as **paired** observations:

* For **continuous metrics** (e.g., per‑request latency), a **paired t‑test** compares the mean difference per request between control and shadow.
* For **binary / yes‑no metrics** on the same request (e.g., "did this violate a safety rule?"), **McNemar’s test** checks whether shadow meaningfully changes the pattern of successes vs. failures.

This usually gives more statistical power than treating control and shadow as two independent samples, and it is exactly what the framework’s "shadow vs. control" backend comparisons are designed to support.

### Shadow Testing Configuration

```yaml
shadow_experiment:
    name: "ml_model_v2_shadow"
    shadow_traffic_percent: 100  # Process all traffic in shadow
    metrics:
        - latency_ms
        - accuracy_score
        - error_rate
        - resource_utilization
    duration_days: 3
    success_criteria:
        latency_regression_threshold: 0.05  # Max 5% latency increase
        accuracy_improvement_threshold: 0.02  # Min 2% accuracy gain
```

### Key Considerations

* **Infrastructure Load**: Shadowing doubles resource usage since requests are processed twice
* **Data Privacy**: Ensure shadow systems handle user data according to privacy policies
* **Monitoring**: Implement robust monitoring to detect issues in shadow systems
* **Transition Criteria**: Define clear success metrics for progressing to A/B testing

---

## 12. ✅ Proposed Approach

### Data Contracts

1. **Assignment table**: `unit_id`, `variant_label` (e.g., control/treatment), `timestamps`
2. **Event table**: raw telemetry data
3. **Analysis table**: aggregated metrics
4. **Pre-period table**: for variance reduction (optional)

### Core Modules

1. **Ingestion Layer**: Adapters for logs, cloud storage, or streams
2. **Metric Engine**: User-defined metric functions (CTR, CVR, revenue, etc.)
3. **Statistical Layer**:
   * SRM (Sample Ratio Mismatch) checks
   * Hypothesis tests (proportions, means)
   * Confidence intervals
   * Variance reduction (CUPED)
   * Sequential monitoring (optional)
4. **Monitoring & Reporting**: Dashboards, alerts, Power BI integration
5. **Extensibility Hooks**: Plug-in metrics, data sources, test types

---

## 13. 💡 Design Principles

| Principle                  | Meaning                                                                                      |
| -------------------------- | -------------------------------------------------------------------------------------------- |
| **Abstraction**            | Separate "metric logic" from "framework logic"                                               |
| **Reusability**            | Should work across multiple products and experiment types                                    |
| **Transparency**           | Log statistical assumptions and test results                                                 |
| **Modularity**             | Allow plug-in metrics, data sources, and test types                                          |
| **On-Demand Flexibility**  | Analysis computed when requested, not continuously; user controls timing                     |
| **Fresh Data Access**      | Always queries latest available data at request time                                         |
| **Efficient Computation**  | Handle large datasets efficiently through optimized aggregation and optional caching         |
| **Scalability**            | Support growing data volumes through efficient batch processing and potential pre-aggregation |

---

## 14. 📊 Statistical Parameters to Support

| Parameter              | Description                                     |
| ---------------------- | ----------------------------------------------- |
| α (alpha)              | Significance level (e.g., 0.05)                 |
| Power (1−β)            | Probability to detect a true effect (e.g., 0.8) |
| MDE                    | Minimum Detectable Effect size                  |
| Sample size estimation | Based on chosen test type                       |
| CI                     | Confidence Interval for effect estimate         |
| Sequential correction  | Optional (for continuous monitoring)            |

---

## 15. 🔧 Implementation Options

### Option 1: Core Python + SciPy/Statsmodels

**Best for**: Basic A/B testing with standard statistical methods

* Use `pandas` for data aggregation
* `SciPy` for z-tests, t-tests, chi-square
* `Statsmodels` for regression-based adjustments
* `Matplotlib`/`Plotly` for visualization
* Power BI for dashboards (via dataset export)

### Option 2: Add Variance Reduction & Sequential Testing

**Best for**: More sophisticated experiments with continuous monitoring

* Implement CUPED (Controlled-experiment Using Pre-Experiment Data) manually or via Statsmodels
* Add SPRT (Sequential Probability Ratio Test) or alpha-spending boundaries for sequential monitoring
* Integrate with Kusto/ADX for near real-time queries

### Option 3: Advanced Causal Analysis (Optional)

**Best for**: Post-experiment analysis and personalization insights

* Use `EconML` for heterogeneous treatment effect estimation
* Apply meta-learners (T-Learner, X-Learner) for personalization
* Keep this as a post-hoc analysis module, not mandatory for MVP

---

## 16. 🧰 Existing Packages / Alternatives

| Package                   | Maintainer                                     | Focus                                              | Fit vs. your vision                                                      | Notes                                                                       |
| ------------------------- | ---------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| **EconML**                | Microsoft Research                             | Causal inference, heterogeneous treatment effects  | ✅ Great for post-experiment analysis, not for ingestion or orchestration | Strong causal framework; could extend your analysis stage                   |
| **abexp**                 | PlaytikaOSS                                    | End-to-end A/B testing library                     | ⚙️ Moderate — includes assignment, metrics, significance tests, and basic sample-size helpers (`SampleSize.ssd_prop/ssd_mean`) | Designed for full experiment lifecycle; less flexible in metric abstraction |
| **owl_ab_test**           | Independent                                    | Frequentist A/B testing with multiple metric types | ✅ Good fit for metric-based testing                                      | Handles proportions and continuous outcomes; **no built-in sample-size/power API**; good analysis baseline       |
| **py-ab-testing**         | Community                                      | Simplified frequentist/Bayesian tests              | ⚙️ Partial — analysis only                                               | Good lightweight option for embedding inside your package                   |
| **ab-test-toolkit**       | Community                                      | Power analysis, sample size, effect estimation     | ✅ Strong analytical utilities                                            | Complements your framework's design phase                                   |
| **ABExperiment (Airbnb)** | Internal (not open-source)                     | Full-scale experiment platform                     | ❌ Not available                                                          | Mentioned for inspiration (metrics, assignment, dashboard)                  |
| **Etsy's ABBA**           | Community (based on Etsy's Bayesian framework) | Bayesian sequential analysis                       | ✅ Advanced analysis module                                               | Could serve as inspiration for Bayesian engine design                       |

---

## 17. 🧩 Key Gaps in Existing Solutions

1. Lack of **generic metric abstraction** (user-defined `metric()` function)
2. Tightly coupled to specific metric types or experiment designs
3. Limited flexibility in **data source adapters** (most tied to specific platforms)
4. No clear separation between **framework logic** and **business logic** (metric definitions)
5. Complex setup requirements - not suitable for simple on-demand analysis needs

---

## 18. 📉 Code Footprint: scipy vs owl vs abexp vs This Framework

One of the practical benefits of this package is a **reduction in per‑experiment user‑written code**, because common patterns live in the framework instead of in each notebook.

### 18.1 Side‑by‑Side Code Sketch (Simple Conversion Test)

**Raw `scipy+pandas` (analysis + orchestration in one place)**

```python
import pandas as pd
from scipy import stats

df = pd.read_csv("sessions.csv")
df = df[df["in_experiment"] == 1]

user_level = (
    df.groupby(["user_id", "variant_label"])
      .agg(converted=("converted_this_session", "max"))
      .reset_index()
)

a = user_level[user_level["variant_label"] == "control"]
b = user_level[user_level["variant_label"] == "treatment"]

success_a = a["converted"].sum(); total_a = len(a)
success_b = b["converted"].sum(); total_b = len(b)

prop_a = success_a / total_a
prop_b = success_b / total_b

stat, p_value = stats.proportions_ztest(
    [success_b, success_a],
    [total_b, total_a],
)

lift = (prop_b - prop_a) / prop_a
```

- In practice, these scripts often end up with **dozens of lines** per scenario once you include SRM checks, logging, and interpretation.

**`owl_ab_test` (nicer API but still per‑experiment orchestration)**

```python
import pandas as pd
from owl_ab_test import calculate_proportion_stats

df = pd.read_csv("sessions.csv")
df = df[df["in_experiment"] == 1]

user_level = (
    df.groupby(["user_id", "variant_label"])
      .agg(converted=("converted_this_session", "max"))
      .reset_index()
)

a = user_level[user_level["variant_label"] == "control"]
b = user_level[user_level["variant_label"] == "treatment"]

result = calculate_proportion_stats(
    success_count=b["converted"].sum(),
    total_count=len(b),
    control_success=a["converted"].sum(),
    control_total=len(a),
    confidence_level=0.95,
)

p_value = result["p_value"]
lift = result["lift"]
```

- The `owl_ab_test` call itself is short, but you still write the same pandas aggregation and any SRM / decision logic per experiment.

**`abexp` (class‑based API, similar orchestration cost)**

```python
from abexp.core.analysis_frequentist import FrequentistAnalyzer

analyzer = FrequentistAnalyzer()
p_value, ci_control, ci_treatment = analyzer.compare_conv_obs(
    control_conversions=success_a,
    control_trials=total_a,
    variation_conversions=success_b,
    variation_trials=total_b,
    alpha=0.05,
)
```

- Adds an analyzer object and tuple unpacking on top of the same preprocessing.

**This framework (orchestration layer on top of these engines)**

```python
from ab_framework import ABTestFramework

config = {
    "experiment": {
        "name": "homepage_banner_test",
        "alpha": 0.05,
        "power": 0.8,
        "unit_id": "user_id",
        "metric": "conversion_rate",
    },
    "data_sources": {
        "assignment": "assignment_table_path_or_query",
        "events": "event_table_path_or_query",
    },
}

def conversion_rate(df):
    return (df["converted_this_session"].max())

framework = ABTestFramework(config=config, metric_fn=conversion_rate)
results = framework.get_latest_analysis()

print(results["decision"], results["p_value"], results["lift"])
```

- The framework call is similarly compact, but the key difference is that common ingestion, aggregation, SRM checks, sample‑size logic,
  and Go/NoGo decision helpers are implemented once in the framework instead of re-written in every notebook.

### 18.2 Takeaways for Engineers and Managers

- owl/abexp are excellent **statistical engines**, but each team still needs to hand‑roll
  ingestion, aggregation, checks, and decision logic per experiment.
- This framework moves that boilerplate into a **reusable orchestration layer**, which in practice
  reduces the amount of custom analysis code per experiment, encourages more consistent patterns across teams,
  and lowers the risk of subtle statistical or data‑handling bugs.

---

## 19. 🏁 Summary

This framework will:

* Sit **on top of existing experimentation infrastructure**
* Handle **data ingestion, metric abstraction, and statistical rigor**
* Provide **flexibility and transparency**
* Potentially reuse **existing libraries** for internal components (tests, power calculations)
* Serve as a **standardized A/B analytics platform** across teams

---

## 19. 📋 Next Steps

1. Define MVP scope and prioritize core modules
2. Set up project structure and development environment
3. Implement data contracts and ingestion layer
4. Build metric engine with user-defined function support
5. Develop statistical layer with basic hypothesis tests
6. Create monitoring dashboard and reporting capabilities
7. Write comprehensive tests and documentation
8. Pilot with real experiments and iterate based on feedback

---

## 20. TODO / Open Theory Items

Some methodological topics are intentionally left for deeper treatment in the theory companion document. As a reminder to future contributors, one key pending item is:

1. **When to use a two‑proportion z‑test vs. a Welch t‑test**  
    See `AB_TESTING_THEORY.md` – Section 9, “TODO / Open Theory Items”, for a placeholder and future elaboration. The high‑level current guidance is that the framework uses proportion tests for rate metrics (e.g., conversion, CTR) and Welch’s t‑test for continuous metrics (e.g., revenue per user, time), but we plan to document more nuanced decision rules and examples.

[^kohavi-unit]: For a detailed discussion of why the unit of randomization should match the unit of analysis, see Kohavi, Tang, Xu, and colleagues, *Trustworthy Online Controlled Experiments* (Cambridge University Press, 2020), and related controlled‑experiments literature.
