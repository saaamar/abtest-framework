# 🧠 Dynamic A/B Testing Analysis Framework

## 1. 🎯 Purpose and Vision

A **generic, reusable A/B testing analysis framework** in Python — a package that is **agnostic to the product domain**, **metric type**, and **variant design**, yet flexible enough to plug into *any system* where A/B experiments run (web UI, backend algorithms, etc.).

### Core Mission

* **Ingest near real-time experiment data** (from log files or streams)
* **Compute experiment metrics dynamically**, regardless of whether they are CTR, Conversion Rate, Revenue per User, etc.
* **Perform rigorous statistical analysis** (power, alpha, confidence intervals, significance tests)
* **Monitor experiment progress and data quality** (sample size, traffic balance, contamination, etc.)
* **Be modular**, allowing integration into different company systems and different types of experiments

---

## 2. 🏗️ Context and Existing Infrastructure

The framework integrates with a **running experimentation system** that:

* Controls **traffic allocation** between A and B variants
* Allows **defining randomization rules** (percentage, user/session-based)
* Produces **log files or data streams** that include:
  * Population assignment (unit_id → variant A/B)
  * Events or actions to measure
  * Data available for on-demand querying

### Data Scientist Role

* Define **experiment design parameters**: minimum sample size, experiment duration, alpha, power, etc.
* Request analysis on-demand when needed (no continuous monitoring required)
* Provide interpretable outputs for business and engineering teams

---

## 3. 🧩 Core Components and Architecture

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

## 4. ⚙️ Technical Flow Overview

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

## 5. ✅ Proposed Approach

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

## 6. 💡 Design Principles

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

## 7. 📊 Statistical Parameters to Support

| Parameter              | Description                                     |
| ---------------------- | ----------------------------------------------- |
| α (alpha)              | Significance level (e.g., 0.05)                 |
| Power (1−β)            | Probability to detect a true effect (e.g., 0.8) |
| MDE                    | Minimum Detectable Effect size                  |
| Sample size estimation | Based on chosen test type                       |
| CI                     | Confidence Interval for effect estimate         |
| Sequential correction  | Optional (for continuous monitoring)            |

---

## 8. 🔧 Implementation Options

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

## 9. 🧰 Existing Packages / Alternatives

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

## 10. 🧩 Key Gaps in Existing Solutions

1. Lack of **generic metric abstraction** (user-defined `metric()` function)
2. Tightly coupled to specific metric types or experiment designs
3. Limited flexibility in **data source adapters** (most tied to specific platforms)
4. No clear separation between **framework logic** and **business logic** (metric definitions)
5. Complex setup requirements - not suitable for simple on-demand analysis needs

---

## 11. 🏁 Summary

This framework will:

* Sit **on top of existing experimentation infrastructure**
* Handle **data ingestion, metric abstraction, and statistical rigor**
* Provide **flexibility and transparency**
* Potentially reuse **existing libraries** for internal components (tests, power calculations)
* Serve as a **standardized A/B analytics platform** across teams

---

## 12. 📋 Next Steps

1. Define MVP scope and prioritize core modules
2. Set up project structure and development environment
3. Implement data contracts and ingestion layer
4. Build metric engine with user-defined function support
5. Develop statistical layer with basic hypothesis tests
6. Create monitoring dashboard and reporting capabilities
7. Write comprehensive tests and documentation
8. Pilot with real experiments and iterate based on feedback
