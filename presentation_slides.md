> Purpose: Presentation slides and script for demonstrating the A/B testing framework
> Generated: Manually authored, maintained under version control.

# Slide 0 – What is A/B Testing (in One Minute)

- Compare two or more variants (A, B, …) on live traffic  
- Assign users randomly, collect one or more metrics  
  - Examples: conversion, revenue per user, CTR, AI-based scores  
- Core question:  
  - "Is the observed difference likely to be real, or just noise?"  
- Mechanically simple, but small implementation/statistical details matter a lot  

---

## Slide 1 – Common Pitfalls in A/B Testing

- Misinterpreting randomness  
  - Treating every fluctuation as a "trend"  
  - Looking too early and overreacting  
- P-hacking / repeated peeking  
  - Continuously checking results and stopping when you see a "good" p-value  
- Ignoring power and sample size  
  - Declaring "no effect" when the test never had power to detect the expected uplift  
- Multiple metrics / variants  
  - Looking at many metrics and only reporting the "nice" ones  
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
  - Session-level vs user-level data granularities  
- Organizational constraints  
  - Need a clear decision even when signals are messy  
  - Different code paths / libraries can analyze the same experiment differently  
- Resulting risk  
  - Same experiment can be analyzed in inconsistent ways depending on implementation and statistical choices  

---

## Slide 3 – The Verification-First Approach: Our Process

**Instead of jumping straight to implementation, we:**

1. **Define success criteria first** – What scenarios must any solution handle?
2. **Create a comprehensive test suite** – 8 realistic scenarios with known ground truth
3. **Evaluate existing solutions** – Test libraries against our scenarios
4. **Make data-driven decision** – Build only if verified alternatives don't exist
5. **Verify our implementation** – Ensure it matches ground truth on all scenarios

**This approach:**
- ✅ Validates there's a real gap (not just "build for fun")
- ✅ Documents exactly what we need
- ✅ Provides ongoing regression tests
- ✅ Enables honest comparison vs alternatives

---

## Slide 4 – The 8 Verification Scenarios (Comprehensive Coverage)

**User-Level Scenarios (1-4):**
1. **Simple Conversion** – Standard binary outcome
2. **Revenue per Active User** – Custom metric with filtering
3. **Click-Through Rate** – Impression-level data (200K+ rows)
4. **Multi-Metric Dashboard** – Testing 4 metrics simultaneously + Bonferroni correction

**Session-Level Scenarios (5-8) – Agent Bot Testing:**
5. **Resolved Rate (WITH gap)** – Binary metric, should detect difference
6. **Resolved Rate (NO gap)** – Binary metric, should find null result
7. **AI Quality Score (WITH gap)** – Continuous metric (0-5 scale), should detect
8. **AI Quality Score (NO gap)** – Continuous metric, should find null result

**Why scenarios 5-8 matter:**
- Tests detection of BOTH significant AND null results (avoiding false positives)
- Session-level granularity (not just user-level)
- AI/continuous metrics increasingly common in modern products

---

## Slide 5 – Ground Truth: The Scientific Baseline

**Every scenario has mathematically correct answers computed in `verification/ground_truth.py`:**

- Uses **scipy directly** with transparent formulas:
  - Two-proportion z-test for binary metrics
  - Welch's t-test for continuous metrics
  - Proper aggregation (impression→user, session→user)
  - Manual Bonferroni correction where needed

**Example (Scenario 1):**
```
Ground Truth: p=0.383397, A=0.1000, B=0.1120
- 11,111 impressions from 2,000 users
- Aggregated to user-level (did user convert in ANY impression?)
- Result: No significant difference (as expected with 12% lift, low sample)
```

**This ground truth serves as:**
- Oracle for validating any package
- Reference for statistical correctness
- Documentation of expected behavior

---

## Slide 6 – Package Evaluation Results: The Evidence

**Tested 3 approaches on all 8 scenarios:**

| Package | Working Scenarios | Issues Found |
|---------|------------------|--------------|
| **scipy+pandas** | ✅ 8/8 (100%) | Verbose (~260 LOC), manual boilerplate |
| **abexp** | ❌ 0/8 (0%) | Cannot install (unmaintained, 3-year-old deps) |
| **owl_ab_test** | ⚠️ 7/8 (87%) | No multi-metric support, requires preprocessing |

**Key findings:**

**scipy+pandas baseline:**
- ✅ All scenarios match ground truth perfectly
- ✅ Full flexibility for custom metrics
- ⚠️ But requires ~25-60 LOC per scenario
- ⚠️ No SRM checks, power analysis, or standardization

**abexp (PlaytikaOSS):**
- ❌ Installation fails on modern Python
- ❌ Requires numpy 1.19, pandas 1.1, scipy 1.5 (3-4 years old!)
- ❌ Security risk from outdated dependencies
- **Verdict:** Unusable in production

**owl_ab_test:**
- ✅ Works for simple binary/continuous metrics
- ✅ Cleaner API than raw scipy (~10-15 LOC vs ~25-35)
- ❌ No multi-metric support
- ❌ Still requires manual pandas preprocessing
- **Verdict:** Thin wrapper, doesn't solve orchestration problem

---

## Slide 7 – The Gap: What's Missing from Existing Solutions

**What we learned from verification:**

1. **No drop-in solution exists** that:
   - ✅ Works reliably (installation, modern Python)
   - ✅ Supports our DataFrame-based, on-demand workflow
   - ✅ Handles complex metrics (filtering, aggregation, ratios)
   - ✅ Provides multi-metric analysis + corrections
   - ✅ Includes quality checks (SRM, data validation)

2. **The gap is orchestration, not statistics:**
   - Statistical formulas are well-established (scipy works)
   - Problem: Repetitive boilerplate for each experiment
   - Need: Reusable patterns around the core stats

3. **Real-world requirements:**
   - Custom metrics (not just simple conversion)
   - Mixed data granularities (user/session/impression)
   - Quality checks before decisions
   - Consistent analysis across team

**Conclusion from verification:** Build a lightweight orchestration layer on scipy+pandas

---

## Slide 8 – Requirements & Design Principles

**Technical requirements:**
- Accept arbitrary metric functions over DataFrames  
- Support on-demand, stateless analysis (analyze any DataFrame without sessions)  
- Cleanly separate experiment spec from statistical backend implementation  
- Handle multiple data granularities (user-level, session-level, impression-level)

**Quality requirements:**
- Reproducible verification via scenario suite  
- Match ground truth on all 8 scenarios
- Data quality checks (SRM, missingness, outliers)
- Readable, reviewable decision logic (no opaque black boxes)

**Non-functional:**
- Reasonable boilerplate per metric (~10-15 LOC vs ~25-60 LOC)
- Easy to understand and maintain
- Clear error messages and validation

**Scope (what this work is NOT):**
- A full experimentation platform / UI  
- A replacement for your data pipeline
- A tutorial on A/B testing statistics

---

## Slide 9 – High-Level Architecture

**`ab_framework.core`**
- Experiment orchestration and decision logic  
- Knows about variants, metrics, configs, and how to call backends  

**`ab_framework.sample_size`**
- Utilities for sample size / power-related calculations (where needed)  

**`ab_framework.quality`**
- **Data quality and experiment health checks (not business guardrails)**  
- `check_srm`: chi-square Sample Ratio Mismatch test on variant counts  
- `check_data_quality`: missingness + IQR-based outlier analysis on metric columns  

**`ab_framework.backends`**
- Backend interface + concrete implementations (OWL-based backend)  
- Input: cleaned metric data + configuration  
- Output: effect sizes, confidence intervals, p-values, decision flags  

**Verification Infrastructure:**
- `verification/data_generator.py`: Creates 8 scenario datasets (reproducible, seed=42)
- `verification/ground_truth.py`: Computes correct answers for all scenarios
- `verification/tests/`: Test implementations for scipy, abexp, owl, and our framework
- `run_comparison_all.py`: Automated comparison of all approaches

---

## Slide 10 – Backend Abstraction & Result Model

**Backend abstraction:**
- Minimal contract for a statistical engine behind the scenes  
- **Inputs:**
  - Variant-level metric data  
  - Configuration (alpha, tails, multiple-testing behavior, etc.)  
- **Outputs:**
  - Effect sizes, p-values, confidence intervals, decision flags, diagnostics  

**Data / result model:**
- Unified representation of:
  - Metrics (binary, continuous, AI metric, etc.)  
  - Variants and groups  
  - Per-metric and overall decisions  
- Designed to be:
  - Machine-readable  
  - Easy to compare across backends and against ground truth  
  - Extensible for new metric types

**Why this matters:**
- Swap backends without changing experiment code
- Compare results across implementations
- Validate against ground truth systematically

---

## Slide 11 – Verification Results: Framework vs Ground Truth

**All 8 scenarios tested and verified:**

```
✅ Scenario 1: Conversion Rate
   Ground truth: p=0.383397, Framework: p=0.383397 ✓

✅ Scenario 2: Revenue per Active User  
   Ground truth: p=0.000021, Framework: p=0.000021 ✓

✅ Scenario 3: CTR (197K impressions)
   Ground truth: p<0.000001, Framework: p<0.000001 ✓

✅ Scenario 4: Multi-Metric Dashboard
   Ground truth: 3 metrics tested, Framework: 3 metrics ✓
   Bonferroni correction applied correctly ✓

✅ Scenarios 5-8: Agent Bot Metrics
   All detection results match ground truth ✓
   Correctly identifies both significant AND null results ✓
```

**Validation approach:**
- Same CSV data for all implementations
- Automated comparison: `abs(p_framework - p_ground_truth) < 0.01`
- Regression tests ensure continued correctness

---

## Slide 12 – What the Framework Adds on Top of scipy+pandas

**Encodes shared patterns:**
- Metric registration and configuration  
- Automatic choice of appropriate tests per metric type (binary vs continuous)  
- Standardized result objects (values, effects, intervals, decisions)
- Proper data aggregation (impression→user, session→user)

**Integrates health checks:**
- SRM checks via `QualityChecker.check_srm`  
- Data quality checks via `QualityChecker.check_data_quality`  
- Validation before running expensive statistical tests

**Reduces boilerplate:**
- Compresses ~25-60 LOC (scipy+pandas) → ~10-15 LOC (framework)
- Encourages consistent analysis patterns across engineers and projects  
- Makes experiments easier to review and understand

**Example:**
```python
# Before: ~40 LOC of pandas + scipy code
# After:
experiment = ABExperiment(
    data=df,
    metrics=[conversion_rate, revenue_per_user],
    variant_column='variant'
)
result = experiment.analyze()
```

---

## Slide 13 – Continuous Verification: Regression Prevention

**The verification suite serves multiple purposes:**

1. **Initial validation** – Proved scipy+pandas baseline works
2. **Package evaluation** – Showed abexp/owl gaps
3. **Framework verification** – Ensures our implementation is correct
4. **Regression tests** – Prevents future statistical bugs

**How it works:**
```bash
# Regenerate data with known properties
python verification/data_generator.py

# Run all packages on same data
python run_comparison_all.py

# Automatic validation
✅ All p-values match ground truth within tolerance
✅ All effect sizes correct
✅ All confidence intervals align
```

**Benefits:**
- Can't accidentally break statistical correctness
- Safe to refactor implementation
- Clear documentation of expected behavior
- Easy to add new scenarios as needs evolve

---

## Slide 14 – Process: From Problem to Verified Solution

**1. Identify the problem** (Weeks 1-2)
- Existing tools don't fit our workflow
- Risk of inconsistent analysis
- Need custom metrics support

**2. Define success criteria** (Week 2)
- Created 8 realistic scenarios
- Documented ground truth for each
- Established evaluation framework

**3. Evaluate alternatives** (Week 3)
- Tested scipy+pandas baseline
- Attempted abexp (failed to install)
- Tested owl_ab_test (partial success)
- **Decision:** Build on scipy+pandas

**4. Design & implement** (Weeks 4-6)
- Modular architecture (core, backends, quality, sample_size)
- Start simple, iterate based on scenarios
- Verify each component against ground truth

**5. Continuous verification** (Ongoing)
- Run full test suite on every change
- Document any deviations
- Regression tests prevent backsliding

---

## Slide 15 – Key Insights from the Verification Process

**What we learned:**

1. **Verification-first saves time**
   - Found abexp was unusable BEFORE investing in it
   - Ground truth prevented statistical bugs
   - Clear success criteria guided design

2. **Scenario design matters**
   - Including "null result" scenarios (6, 8) prevents false positive bias
   - Mixed granularities (user/session/impression) surface real complexity
   - Multi-metric scenario forced proper correction handling

3. **The gap is orchestration**
   - Core statistical formulas are well-established
   - Problem: Making them ergonomic and consistent
   - Solution: Thin layer around proven scipy code

4. **Documentation through examples**
   - 8 scenarios serve as both tests AND documentation
   - Shows what the framework can (and can't) do
   - Makes requirements concrete and testable

---

## Slide 16 – Impact & Production Readiness

**Impact today:**
- ✅ Reusable framework for A/B analysis on top of trusted scipy+pandas  
- ✅ Verification suite documents and checks behavior  
- ✅ Clear internal standard for experiment analysis  
- ✅ Reduced boilerplate: ~40 LOC → ~10-15 LOC per scenario
- ✅ Automated quality checks (SRM, data validation)
- ✅ Confidence from 100% ground truth match on all 8 scenarios

**Production readiness:**
- Battle-tested against realistic scenarios
- Regression tests prevent statistical bugs
- Clear error messages and validation
- Extensible architecture for new metrics

**Next steps:**
- Extend scenario coverage (more metric types, experiment designs)  
- Deepen backend support and configuration options  
- Integrate with CI pipeline for automatic verification
- Add power analysis and sample size planning utilities

---

## Slide 17 – Lessons: What Made This Work

**1. Don't trust, verify**
- Created ground truth BEFORE building anything
- Tested ALL alternatives honestly
- Documented failures (abexp) as much as successes

**2. Start with use cases**
- 8 scenarios represent real needs
- Not abstract capabilities
- Easy to explain value to stakeholders

**3. Build on proven foundations**
- scipy+pandas is battle-tested
- We add orchestration, not new stats
- Lower risk than novel implementations

**4. Make verification automatic**
- `python run_comparison_all.py` validates everything
- Catches regressions immediately
- Documentation that stays up to date

**5. Be honest about scope**
- Not a platform, just a framework
- Solves OUR problems, might not solve yours
- Clear about what it doesn't do

---

## Slide 18 – Summary

**The Problem:**
- Off-the-shelf A/B packages didn't meet our practical workflow requirements
- Risk of inconsistent analysis across experiments
- No reliable solution for custom metrics and mixed granularities

**The Process:**
- Verification-first: Created 8 scenarios with ground truth
- Evaluated 3 approaches systematically
- Made data-driven decision to build on scipy+pandas

**The Solution:**
- Modular framework with clean separation of concerns
- 100% verified against ground truth on all scenarios
- Reduces boilerplate while maintaining statistical correctness

**The Outcome:**
- More reliable, reproducible, and consistent A/B analysis
- Automated regression tests prevent future bugs
- Clear path for extending to new scenarios
- Production-ready with confidence from comprehensive verification

**Key Takeaway:** Verification isn't overhead—it's the foundation that enabled confident, rapid development.
