> Purpose: Presentation slides and script for demonstrating the A/B testing framework
> Generated: Manually authored, maintained under version control.

# Slide 0 – What is A/B Testing (in One Minute)

- Compare two or more variants (A, B, …) on live traffic  
- Assign users randomly, collect one or more metrics  
  - Examples: conversion, revenue per user, CTR, AI-based scores  
- Core question:  
  - “Is the observed difference likely to be real, or just noise?”  
- Mechanically simple, but small implementation/statistical details matter a lot  

---

## Slide 1 – Common Pitfalls in A/B Testing

- Misinterpreting randomness  
  - Treating every fluctuation as a “trend”  
  - Looking too early and overreacting  
- P-hacking / repeated peeking  
  - Continuously checking results and stopping when you see a “good” p-value  
- Ignoring power and sample size  
  - Declaring “no effect” when the test never had power to detect the expected uplift  
- Multiple metrics / variants  
  - Looking at many metrics and only reporting the “nice” ones  
- Black-box tooling  
  - Relying on library defaults without understanding assumptions  

---

## Slide 2 – Practical Challenges We Hit in Reality

- Non-ideal data  
  - Missing events, delayed logging, bots, outliers  
  - Non-stationary traffic, campaigns, seasonality  
- Complex metrics  
  - Revenue per active user, exposure-filtered CTR  
  - AI-based metrics that are not simple 0/1 (Bernoulli) variables  
- Organizational constraints  
  - Need a clear decision even when signals are messy  
  - Different code paths / libraries can analyze the same experiment differently  
- Resulting risk  
  - Same experiment can be analyzed in inconsistent ways depending on implementation and statistical choices  

---

## Slide 3 – Why This Work Was Needed (Updated / Robust)

- We evaluated several Python A/B testing approaches plus a `scipy+pandas` baseline using the verification suite in this repo  
- In practice we found:  
  - Some libraries had **practical issues** (installation, imports, or fragile APIs)  
  - Others had **APIs that did not fit** our DataFrame-based, on-demand analysis pattern  
  - The only approach that reliably supported our verification scenarios was “roll your own” with **`scipy+pandas`**  
- Gap in the ecosystem:  
  - No option that is both:
    - Convenient and high-level, and  
    - Flexible enough for our real metrics and workflows  
- This motivated building a thin **orchestration framework on top of `scipy+pandas`**  

---

## Slide 4 – Requirements & Scope

- Technical requirements:
  - Accept arbitrary metric functions over DataFrames  
  - Support on-demand, stateless analysis (analyze any DataFrame without sessions)  
  - Cleanly separate experiment spec from statistical backend implementation  
- Non-functional:
  - Reproducible verification via a scenario suite and baselines  
  - Readable, reviewable decision logic (no opaque black boxes)  
  - Reasonable amount of boilerplate per metric  
- Scope (what this work is **not**):
  - A full experimentation platform / UI  
  - A user tutorial; focus is on design, implementation and verification  

---

## Slide 5 – High-Level Architecture

- `ab_framework.core`  
  - Experiment orchestration and decision logic  
  - Knows about variants, metrics, configs, and how to call backends  

- `ab_framework.sample_size`  
  - Utilities for sample size / power-related calculations (where needed)  

- `ab_framework.quality`  
  - **Data quality and experiment health checks (not business guardrails)**  
  - `check_srm`: chi-square Sample Ratio Mismatch test on variant counts  
  - `check_data_quality`: missingness + IQR-based outlier analysis on metric columns  

- `ab_framework.backends`  
  - Backend interface + concrete implementations (e.g. OWL-based backend)  
  - Input: cleaned metric data + configuration  
  - Output: effect sizes, confidence intervals, p-values, decision flags  

- Surrounding tooling  
  - `verification/`: scenario suite + comparison harness vs other packages  
  - `demos/`: example scripts that exercise the framework end-to-end  

---

## Slide 6 – Backend Abstraction & Data / Result Model

- Backend abstraction:
  - Minimal contract for a statistical engine behind the scenes  
  - Inputs:
    - Variant-level metric data  
    - Configuration (alpha, tails, multiple-testing behavior, etc.)  
  - Outputs:
    - Effect sizes, p-values, confidence intervals, decision flags, diagnostics  
- Data / result model:
  - Unified representation of:
    - Metrics (binary, continuous, AI metric, etc.)  
    - Variants and groups  
    - Per-metric and overall decisions  
  - Designed to be:
    - Machine-readable  
    - Easy to compare across backends and against ground truth  

---

## Slide 7 – Verification & Benchmarking Infrastructure

- Scenario suite (`verification/`):  
  - Synthetic datasets for:
    - Simple conversion  
    - Revenue per active user  
    - Exposure-filtered CTR  
    - Multi-metric dashboard with Bonferroni correction  
  - Each scenario has explicit “ground truth” implemented in `verification/ground_truth.py`  
- Comparison harness:
  - Shared pipeline that runs:
    - `scipy+pandas` baseline  
    - Third-party packages (as far as they work)  
    - This framework  
    - All on the *same* CSV scenarios  
  - Normalizes each tool’s outputs into a common schema  
- Reporting:
  - Markdown reports, matrices, and summaries in `verification/results/`  
  - Ability to re-run the full evaluation and regenerate evidence  

---

## Slide 8 – Results from Library Verification (Careful Wording)

- `scipy+pandas` baseline:
  - Implements all verification scenarios  
  - Matches the defined oracle ground truth  
  - Flexible but verbose (tens of LOC per scenario)  
- Third-party packages (based on the runs captured in this repo):
  - Showed **practical usability issues** (packaging, imports, or API fit) on our scenarios and environment  
  - Did not provide a drop-in, production-ready replacement for our needs  
- Takeaway:
  - For our use cases, **“raw `scipy+pandas` + custom code”** was the only reliable option  
  - The gap is orchestration and ergonomics, not core statistical formulas  

---

## Slide 9 – What the Framework Adds on Top of scipy+pandas

- Encodes **shared patterns**:
  - Metric registration and configuration  
  - Automatic choice of appropriate tests per metric type (e.g. proportions vs continuous)  
  - Standardized result objects (values, effects, intervals, decisions)  
- Integrates **health checks**:
  - SRM checks via `QualityChecker.check_srm`  
  - Data quality checks via `QualityChecker.check_data_quality`  
- Reduces **boilerplate**:
  - Compresses repeated `scipy+pandas` code into reusable building blocks  
  - Encourages consistent analysis patterns across engineers and projects  

---

## Slide 10 – Findings from Verification & Iterations

- Agreement:
  - Baseline oracle and framework are aligned by design  
- Useful insights:
  - Scenario design (multi-metric, exposure-based metrics, AI-like metrics) surfaces edge cases we care about  
  - SRM and data quality checks catch issues before we even look at uplift  
- Iterations:
  - Adjusted APIs, defaults, and checks based on what the scenario suite exposed  
  - Scenario suite used as an integration/regression test layer for statistical behavior  

---

## Slide 11 – My Engineering Work

- Architecture and design:
  - Worked from `AB_FRAMEWORK_DECISION.md` / `AB_FRAMEWORK_IMPLEMENTATION.md` into concrete modules  
  - Helped refine the separation between:
    - `core`, `backends`, `quality`, and `sample_size`  
- Implementation:
  - Implemented/extended:
    - Backend interface and at least one concrete backend  
    - `QualityChecker` with SRM and data-quality checks  
    - Parts of the execution/orchestration path and demos  
- Verification tooling:
  - Contributed to:
    - Scenario definitions and/or `verification/data_generator.py`  
    - Comparison and normalization logic in `verification/`  
    - Documentation of findings in `verification/results/*.md`  

---

## Slide 12 – Impact & Next Steps

- Impact today:
  - A reusable framework for A/B analysis on top of trusted `scipy+pandas`  
  - A verification suite that documents and checks the behavior of our stack  
  - A clearer internal standard for how we should analyze experiments  
- Possible next steps:
  - Extend scenario coverage (more metric types, experiment designs)  
  - Deepen backend support and configuration options  
  - Integrate with experiment pipelines / CI so checks and comparisons run automatically  

---

## Slide 13 – Summary

- Motivation:
  - Off-the-shelf A/B packages did not meet our practical and workflow requirements  
- Work done:
  - Built a verification suite with realistic scenarios and a `scipy+pandas` oracle  
  - Designed and implemented a modular A/B testing framework around that baseline  
  - Added data/experiment health checks and standardized outputs  
- Outcome:
  - More reliable, reproducible, and consistent A/B analysis for our use cases
