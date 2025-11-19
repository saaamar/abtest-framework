# 🧠 Dynamic A/B Testing Analysis Framework

## 1. 🔬 Understanding A/B Testing: Goals and Fundamentals

### What is A/B Testing?

**A/B testing** (also called split testing) is a randomized controlled experiment that compares two or more variants of a product feature, algorithm, or user experience to determine which performs better on specific business metrics.

### Core Goals of A/B Testing

* **Causal Inference**: Establish whether changes directly cause improvements in business metrics
* **Risk Mitigation**: Test changes on a subset before full rollout to minimize potential negative impact
* **Data-Driven Decisions**: Replace intuition and opinions with statistical evidence
* **Continuous Optimization**: Iteratively improve products through systematic experimentation
* **Business Impact Measurement**: Quantify the effect of changes on key performance indicators (KPIs)

### Key A/B Testing Methodology

#### 1. **Hypothesis Formation**
```
H₀ (Null): No difference between variants A and B
H₁ (Alternative): Variant B performs better than variant A by at least X%
```

#### 2. **Experimental Design**
* **Randomization Unit**: Define what gets randomized (users, sessions, accounts)
* **Traffic Allocation**: Determine split ratio (50/50, 90/10, etc.)
* **Success Metrics**: Primary and secondary metrics to measure
* **Guardrail Metrics**: Metrics that must not be negatively affected

### Choosing the Unit of Randomization vs. Unit of Analysis

One of the first practical decisions in any experiment is: **"What is my unit?"**

The golden rule is:

> **Unit of randomization = Unit of analysis**

This keeps your statistics valid and your interpretation simple: you analyze the same entity you randomized.

#### Example Dilemma: Users vs. Conversations in a Bot System

Imagine your product is a **bot assistant**:

* You have **users** (with `user_id`)
* Each user can open multiple **conversations** (with `conversation_id`)
* You want to change the bot logic and run an A/B test

You now face a natural question:

> Should the **unit_id** be `user_id` or `conversation_id`?

Both choices are legitimate, but they answer **slightly different questions** and affect user experience.

#### Option 1: Randomize by `user_id`

**What it means**

* Each user is assigned once to a variant (A or B)
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

In this framework, if you randomize by `user_id`, you should also **analyze metrics at user level** (aggregate conversation data per user before running tests).

#### Option 2: Randomize by `conversation_id`

**What it means**

* Each new conversation is randomized independently to A or B
* The same user can see A in one conversation and B in another

**Pros**

* Many more units (conversations) → potentially **shorter tests** for **conversation-level** metrics
* Direct answer to: "Does variant B improve metrics **per conversation**?"

**Cons**

* The same user can experience **mixed behavior** (sometimes A, sometimes B)
* User-level interpretation becomes more complex (each user sees a blend of both variants)
* Conversations from the same user are often **correlated**; naive per-conversation analysis can **overstate significance** unless you use clustered/robust methods

**When to prefer `conversation_id` as unit**

* Your primary metric is truly **per-conversation**, and user-level experience consistency is less critical
    * e.g., "resolution rate per conversation", "average handling time per conversation"
* Conversations are relatively **independent tasks** from the user's perspective

If you randomize by `conversation_id`, the framework should either:

* Analyze at **conversation level** with appropriate **cluster-robust** methods (cluster by `user_id`), or
* Aggregate to **user level** first and accept that each user may have seen both variants (more complex interpretation).

#### Practical Guidance for This Framework

For most product scenarios (including the bot use case), the recommended **default** is:

* Choose **`user_id` as the `unit_id`** (unit of randomization)
* Aggregate conversation events to **user-level metrics** (unit of analysis)

Conversation-level randomization (`conversation_id`) is still valid, but should be a deliberate choice when:

* The experiment is focused on **conversation-level operations**, and
* You are comfortable with users seeing a **mix of variants**, and
* You adjust your statistical analysis to respect the correlation between conversations of the same user.

In short:

> Start with **user-level experiments** for user-centric metrics and experience.
> Use **conversation-level experiments** for low-level operational metrics, with careful analysis.

#### 3. **Statistical Framework**
* **Significance Level (α)**: How likely your experiment is to find a difference that doesn't actually exist. Technically, this is the probability of false positive (Type I error), typically 0.05 = 5% chance of being fooled
* **Statistical Power (1-β)**: How likely your experiment is to catch a real improvement when there actually is one. Technically, this is the probability of detecting true effect when it exists (Type II error), typically 0.8 = 80% chance of spotting real changes
* **Minimum Detectable Effect (MDE)**: Minimum meaningful difference you want to be able to detect
* **Sample Size**: Number of units needed for reliable results

---

## 2. 👩‍🔬 The Data Scientist's Role in A/B Testing

### Pre-Experiment Responsibilities

* **Metric Definition**: Clearly define what you're measuring - this can be:
  * **Ratio/Percentage metrics**: CTR (clicks/impressions), Conversion Rate (purchases/visitors), Success Rate (completions/attempts)
  * **Quantity/Value metrics**: Revenue per User, Time on Site, Items per Order, Page Load Time
* **Experiment Design**: Define hypothesis, success metrics, and statistical parameters
  * **Statistical parameters** include: significance level (α), power (1-β), minimum detectable effect (MDE), and baseline metric value
* **Sample Size Calculation**: Determine required sample size based on expected effect and constraints
* **Randomization Strategy**: Choose appropriate randomization unit and allocation method
* **Success Criteria**: Set clear thresholds for statistical and practical significance

### During Experiment

* **Data Quality Monitoring**: Check for Sample Ratio Mismatch (SRM) and other data issues
* **Sequential Analysis**: Monitor experiment progress without compromising statistical validity
* **Interim Analysis**: Provide updates while maintaining experiment integrity
* **Issue Detection**: Identify technical problems or unexpected behavior patterns

### Post-Experiment Analysis

* **Statistical Testing**: Apply appropriate tests (t-test, chi-square, Mann-Whitney U, etc.)
* **Effect Size Estimation**: Calculate confidence intervals for business impact
* **Practical Significance**: Interpret statistical results in business context
* **Recommendation**: Provide clear go/no-go decision with supporting evidence

---

## 3. 📊 Sample Size Determination: The Foundation

### Required Inputs for Sample Size Calculation

#### Statistical Parameters
* **Significance Level (α)**: Risk of false positive (Type I error)
  * Common choice: α = 0.05 (5% false positive rate)
* **Statistical Power (1-β)**: Probability of detecting true effect (Type II error)
  * Common choice: Power = 0.8 (80% chance to detect real effect)

#### Business Parameters
* **Baseline Rate**: Current performance of the control variant
  * Example: Current conversion rate = 3.2% (or 0.032)
* **Minimum Detectable Effect (MDE)**: Smallest change worth detecting - **IMPORTANT: This is relative to baseline, not absolute**
  * Example: Baseline = 70% (0.7), MDE = 10% relative improvement
  * Calculation: 0.7 × (1 + 0.10) = 0.7 × 1.10 = 0.77 (77%)
  * So we're testing: 70% → 77% (not 70% → 80%)
* **Traffic Allocation**: Proportion of users in each variant
  * Example: 50/50 split vs. 90/10 split

#### Metric Type Considerations
* **Proportion Metrics** (CTR, Conversion Rate): Use normal approximation or exact tests
* **Continuous Metrics** (Revenue, Time Spent): Requires variance estimation
* **Count Metrics** (Page Views, Purchases): May need Poisson or negative binomial models

### Sample Size Formula Example

For **proportion metrics** with equal allocation:

```
n = 2 × (Z_α/2 + Z_β)² × p̂(1-p̂) / (MDE)²

Where:
- n = sample size per variant
- Z_α/2 = critical value for significance level
- Z_β = critical value for power
- p̂ = baseline proportion
- MDE = minimum detectable effect
```

### Practical Considerations

* **Seasonality**: Account for weekly/monthly patterns in user behavior
* **External Factors**: Consider marketing campaigns, holidays, product launches
* **Multiple Testing**: Adjust for multiple metrics or sequential testing
* **Variance Reduction**: Use CUPED or stratification to reduce required sample size

---

## 4. 🎯 Complete A/B Testing Workflow

### Step-by-Step Process

#### 1. **Planning Phase**
```
Choose α (significance level) → Choose Power → Define Meaningful Impact → Calculate Sample Size → Estimate Duration
```

**Example Planning Session:**
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

# Step 4: Calculate required sample size per variant
sample_size_per_variant = calculate_sample_size(alpha, power, baseline_rate, mde)
total_sample_size = sample_size_per_variant * len(traffic_allocation)

# Step 5: Estimate experiment duration
daily_users = 10000  # Historical average daily user count
daily_experiment_users = daily_users * experiment_traffic_pct  # Users in experiment per day
buffer_factor = 1.2  # 20% buffer for traffic fluctuations

duration_days = math.ceil((total_sample_size * buffer_factor) / daily_experiment_users)

print(f"Required sample size: {total_sample_size:,}")
print(f"Daily experiment users: {daily_experiment_users:,}")
print(f"Estimated duration: {duration_days} days")
```

**Duration Calculation Function:**
```python
def calculate_experiment_duration(required_sample_size, daily_traffic, 
                                  experiment_traffic_pct, buffer_factor=1.2):
    """
    Calculate required experiment duration
    
    Args:
        required_sample_size: Total sample size needed across all variants
        daily_traffic: Average daily users/sessions
        experiment_traffic_pct: Fraction of traffic in experiment (0.0-1.0)
        buffer_factor: Safety buffer for traffic fluctuations (default 20%)
    
    Returns:
        dict: Duration info including days, expected sample size, etc.
    """
    daily_experiment_users = daily_traffic * experiment_traffic_pct
    duration_days = math.ceil((required_sample_size * buffer_factor) / daily_experiment_users)
    
    return {
        "duration_days": duration_days,
        "daily_experiment_users": daily_experiment_users,
        "required_sample_size": required_sample_size,
        "buffer_factor": buffer_factor,
        "expected_final_sample": duration_days * daily_experiment_users
    }

# Example calculations
duration_info = calculate_experiment_duration(
    required_sample_size=50000,
    daily_traffic=10000,
    experiment_traffic_pct=1.0,  # 100% of users in experiment
    buffer_factor=1.2
)
# Result: ~6 days
```

**Duration Calculation Considerations:**

| Factor | Impact on Duration | Example |
|--------|-------------------|---------|
| **Sample Size** | Larger sample → Longer duration | 100K vs 50K samples |
| **Daily Traffic** | More traffic → Shorter duration | 50K vs 10K daily users |
| **Experiment %** | Higher % → Shorter duration | 100% vs 50% in experiment |
| **Buffer Factor** | Higher buffer → Longer duration | 1.3 (30%) vs 1.1 (10%) |
| **Seasonality** | Weekends/holidays → Longer | Account for low-traffic days |

**Example Scenarios:**
```python
# Scenario 1: High traffic site, full allocation
calc_duration(required_sample_size=100000, daily_traffic=50000, experiment_traffic_pct=1.0)
# Result: ~3 days

# Scenario 2: Conservative allocation (50% of users)
calc_duration(required_sample_size=100000, daily_traffic=50000, experiment_traffic_pct=0.5)
# Result: ~5 days

# Scenario 3: Lower traffic site
calc_duration(required_sample_size=100000, daily_traffic=5000, experiment_traffic_pct=1.0)
# Result: ~24 days
```

#### 2. **A/A Testing Phase (Critical First Step)**
**Before running A/B tests, always run A/A tests to validate your system:**

```python
# A/A Test Configuration
aa_duration = calculate_experiment_duration(
    required_sample_size=10000,  # Smaller sample for validation
    daily_traffic=10000,
    experiment_traffic_pct=1.0,
    buffer_factor=1.1
)

aa_test = {
    "control": "variant_A",
    "treatment": "variant_A",  # Same as control!
    "traffic_allocation": {
        "control": 0.50,          # 50% get control (variant_A)
        "treatment": 0.50         # 50% get treatment (also variant_A!)
    },
    # total_experiment_traffic = sum(traffic_allocation) = 1.0 (calculated automatically)
    "duration_days": aa_duration["duration_days"]  # Calculated: typically 2-3 days
}
```

**What A/A Testing Validates:**
* **Randomization System**: Traffic is split correctly (no Sample Ratio Mismatch)
* **Data Pipeline**: Events are captured and attributed properly  
* **Statistical Framework**: False positive rate matches expected α
* **Infrastructure**: No technical biases or bugs in assignment logic

**A/A Test Success Criteria:**
* Traffic split should be 50/50 ± 1%
* Metrics should show **no significant difference** (p-value > α)
* If p-value < α, investigate before proceeding to A/B testing

#### 3. **A/B Testing Phase**
```python
# A/B Test Configuration - Different Traffic Allocation Options

# Calculate duration based on sample size and traffic
ab_duration_full = calculate_experiment_duration(
    required_sample_size=38415,  # From sample size calculation
    daily_traffic=10000,
    experiment_traffic_pct=1.0,  # 100% in experiment
    buffer_factor=1.2
)

ab_duration_conservative = calculate_experiment_duration(
    required_sample_size=38415,
    daily_traffic=10000,
    experiment_traffic_pct=0.5,  # 50% in experiment  
    buffer_factor=1.2
)

# Option 1: 50/50 split of ALL traffic
ab_test_full = {
    "control": "variant_A",           # Current version - 50% of users
    "treatment": "variant_B",         # New version - 50% of users
    "traffic_allocation": {
        "control": 0.50,              # 50% get control
        "treatment": 0.50             # 50% get treatment
    },
    # total_experiment_traffic = sum(0.50 + 0.50) = 1.0 (100% of users)
    "duration_days": ab_duration_full["duration_days"]  # Calculated duration
}

# Option 2: Conservative split - only 50% of users in experiment
ab_test_conservative = {
    "control": "variant_A",           # Current version - 25% of users  
    "treatment": "variant_B",         # New version - 25% of users
    "traffic_allocation": {
        "control": 0.25,              # 25% get control
        "treatment": 0.25             # 25% get treatment
    },
    # total_experiment_traffic = sum(0.25 + 0.25) = 0.50 (50% of users)
    # remaining 50% automatically get normal production (not tracked by framework)
    "duration_days": ab_duration_conservative["duration_days"]  # Calculated duration (2x longer)
}

# Option 3: Uneven split for high-risk changes
ab_duration_uneven = calculate_experiment_duration(
    required_sample_size=38415,
    daily_traffic=10000,
    experiment_traffic_pct=1.0,
    buffer_factor=1.2
)

ab_test_uneven = {
    "control": "variant_A",           # Current version - 90% of experiment users
    "treatment": "variant_B",         # New version - 10% of experiment users  
    "traffic_allocation": {
        "control": 0.90,              # 90% get control
        "treatment": 0.10             # 10% get treatment
    },
    # total_experiment_traffic = sum(0.90 + 0.10) = 1.0 (100% of users)
    "duration_days": ab_duration_uneven["duration_days"]  # Calculated duration
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

Making the right decision requires both **statistical significance** and **business significance**. Here's a comprehensive decision-making framework:

#### Decision Criteria Matrix

| Statistical Significance | Business Significance | Data Quality | Decision | Action |
|--------------------------|----------------------|--------------|----------|--------|
| ✅ Significant (p < α) | ✅ Meaningful Impact | ✅ High Quality | **GO** | Ship to production |
| ✅ Significant (p < α) | ❌ Too Small Impact | ✅ High Quality | **NO-GO** | Don't ship, try bigger change |
| ❌ Not Significant | ✅ Promising Direction | ✅ High Quality | **EXTEND** | Run longer or increase sample |
| ❌ Not Significant | ❌ Small Impact | ✅ High Quality | **NO-GO** | Abandon, try different approach |
| Any | Any | ❌ Poor Quality | **INCONCLUSIVE** | Fix data issues, re-run |

#### Detailed Decision Criteria

**1. Statistical Significance Check**
```python
def check_statistical_significance(p_value, alpha=0.05):
    return {
        "is_significant": p_value < alpha,
        "p_value": p_value,
        "alpha": alpha,
        "confidence_level": 1 - alpha
    }
```

**2. Business Significance Assessment**
```python
def check_business_significance(observed_lift, minimum_meaningful_effect):
    return {
        "is_meaningful": abs(observed_lift) >= minimum_meaningful_effect,
        "observed_lift": observed_lift,
        "minimum_required": minimum_meaningful_effect,
        "meets_threshold": abs(observed_lift) >= minimum_meaningful_effect
    }
```

**3. Data Quality Validation**
```python
def check_data_quality(results):
    quality_checks = {
        "sample_ratio_mismatch": abs(results['control_n'] / results['treatment_n'] - 1) < 0.05,
        "sufficient_sample_size": results['total_n'] >= results['required_n'],
        "experiment_duration": results['actual_days'] >= results['planned_days'],
        "no_external_interference": results['external_events'] == [],
        "data_pipeline_health": results['missing_data_rate'] < 0.01
    }
    return all(quality_checks.values()), quality_checks
```

#### Decision Tree Algorithm

```python
def make_go_nogo_decision(statistical_result, business_result, quality_result):
    
    # Check data quality first
    if not quality_result['is_high_quality']:
        return {
            "decision": "INCONCLUSIVE",
            "reason": "Data quality issues detected",
            "action": "Fix data pipeline and re-run experiment",
            "failed_checks": quality_result['failed_checks']
        }
    
    # Check for negative impact (guardrail violation)
    if statistical_result['is_significant'] and business_result['observed_lift'] < 0:
        return {
            "decision": "NO-GO",
            "reason": "Statistically significant negative impact",
            "action": "Do not ship - treatment hurts the metric",
            "risk_level": "HIGH"
        }
    
    # Positive results decision matrix
    if statistical_result['is_significant'] and business_result['is_meaningful']:
        return {
            "decision": "GO",
            "reason": "Statistically and practically significant improvement",
            "action": "Ship to production",
            "confidence": "HIGH"
        }
    
    elif statistical_result['is_significant'] and not business_result['is_meaningful']:
        return {
            "decision": "NO-GO",
            "reason": "Statistically significant but impact too small",
            "action": "Consider larger changes or different approach",
            "confidence": "MEDIUM"
        }
    
    elif not statistical_result['is_significant'] and business_result['observed_lift'] > 0:
        return {
            "decision": "EXTEND",
            "reason": "Promising direction but not yet significant",
            "action": "Run longer or increase sample size",
            "confidence": "LOW"
        }
    
    else:
        return {
            "decision": "NO-GO",
            "reason": "No significant improvement detected",
            "action": "Try different approach or abandon feature",
            "confidence": "MEDIUM"
        }
```

#### Risk Assessment Framework

**Low Risk Decisions (Quick Ship)**
- Statistical significance: p < 0.01
- Business impact: > 2x minimum meaningful effect
- Confidence interval: Entirely positive
- No guardrail violations

**Medium Risk Decisions (Ship with Monitoring)**
- Statistical significance: 0.01 < p < 0.05
- Business impact: 1-2x minimum meaningful effect
- Confidence interval: Mostly positive, small negative tail
- Minor guardrail concerns

**High Risk Decisions (Extended Testing)**
- Statistical significance: Borderline (p ≈ 0.05)
- Business impact: Close to minimum threshold
- Confidence interval: Includes zero or negative values
- Guardrail violations present

#### Example Decision Output

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
**For this framework, we focus on ONE primary metric per experiment:**
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

A **generic, reusable A/B testing analysis framework** in Python — a package that is **agnostic to the product domain**, **metric type**, and **variant design**, yet flexible enough to plug into *any system* where A/B experiments run (web UI, backend algorithms, etc.).

### Core Mission

* **Ingest near real-time experiment data** (from log files or streams)
* **Compute experiment metrics dynamically**, regardless of whether they are CTR, Conversion Rate, Revenue per User, etc.
* **Perform rigorous statistical analysis** (power, alpha, confidence intervals, significance tests)
* **Monitor experiment progress and data quality** (sample size, traffic balance, contamination, etc.)
* **Be modular**, allowing integration into different company systems and different types of experiments

---

## 8. 🏗️ Context and Existing Infrastructure

The framework integrates with a **running experimentation system** that:

* Controls **traffic allocation** between A and B variants
* Allows **defining randomization rules** (percentage, user/session-based)
* Produces **log files or data streams** that include:
  * Population assignment (unit_id → variant A/B)
  * Events or actions to measure
  * Data available for on-demand querying

### Framework's Role in Data Science Workflow

* **Automate sample size calculations** based on user-defined parameters
* **Standardize statistical testing** across different experiment types
* **Provide real-time experiment monitoring** and data quality checks
* **Generate interpretable reports** for stakeholders and decision-makers
* **Ensure statistical rigor** while maintaining ease of use

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

  This ensures full flexibility — the framework only requires a single numeric output per unit or per variant group.

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
* **Processing**: Clean and preprocess data (deduplicate, handle missing data, ensure correct variant assignment)
* **Aggregation**: Aggregate by `unit_id` and variant (A/B) to produce:

  ```
  unit_id | variant | metric_value | timestamp
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
  * Variant balance check (traffic allocation validation)
  * Metric drift and variance trends
  * Statistical significance at time of request
* **Analysis results** returned include:
  * Current metrics for each variant
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

1. **Assignment table**: `unit_id`, `variant`, `timestamps`
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
| **abexp**                 | PlaytikaOSS                                    | End-to-end A/B testing library                     | ⚙️ Moderate — includes assignment, metrics, and significance tests       | Designed for full experiment lifecycle; less flexible in metric abstraction |
| **owl_ab_test**           | Independent                                    | Frequentist A/B testing with multiple metric types | ✅ Good fit for metric-based testing                                      | Handles proportions and continuous outcomes; good baseline                  |
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

## 18. 🏁 Summary

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
