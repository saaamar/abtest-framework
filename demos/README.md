# AB Framework - Demo Files

This directory contains ready-to-run demonstration files showcasing the AB Framework's capabilities.

## 📁 Demo Files Overview

### 1. Quick Start Demo (`demo_quick_start.txt`)
**Purpose**: Introduction to basic framework usage  
**Duration**: ~2 minutes to read  
**Best for**: New users, quick overview

**Contents**:
- Sample size calculation (pre-experiment planning)
- Loading experiment data
- Creating ABTest instance
- Defining metrics
- Running analysis
- Reviewing results
- Multi-metric analysis with Bonferroni correction
- Quality checks (SRM)

**Key Takeaway**: Complete A/B test workflow in ~50 lines of code

---

### 2. Real World Workflow Demo (`demo_real_world_workflow.txt`)
**Purpose**: End-to-end enterprise A/B testing pipeline  
**Duration**: ~5 minutes to read  
**Best for**: Understanding production workflows

**Contents**:
- **Phase 0**: A/A testing for infrastructure validation
- **Phase 1**: Sample size planning using A/A test learnings
- **Phase 2**: Gradual rollout strategy
- **Phase 3-4**: A/B test with sequential monitoring (checks every 3 days)
- **Phase 5**: Final analysis
- **Phase 6**: Business decision making
- **Phase 7**: Complete workflow summary

**Scenario**: Testing AI model v2.0 for quality metric improvement (7% target lift)

**Key Takeaway**: Proper validation before experimentation prevents false results

---

### 3. Feature Showcase Demo (`demo_features.md`)
**Purpose**: Comprehensive feature demonstration  
**Duration**: ~10 minutes to read  
**Best for**: Technical evaluation, feature comparison

**Contents**:

#### Feature 1: Sample Size Planning
- Conversion rates (proportions)
- Continuous metrics (means)
- Power analysis

#### Feature 2: Multiple Testing Corrections
- No correction (baseline)
- Bonferroni correction (conservative)
- Benjamini-Hochberg FDR (balanced)

#### Feature 3: Quality Checks
- Sample Ratio Mismatch (SRM) detection
- Minimum Detectable Effect (MDE) calculation

#### Feature 4: Sequential Testing
- Peek at results without inflating error rates
- Early stopping rules
- Monitoring at different sample sizes

#### Feature 5: Flexible Metric Definitions
- Session-level metrics
- User-level metrics
- Conditional metrics (e.g., Average Order Value)

#### Feature 6: Result Export Options
- DataFrame export for analysis
- Dictionary export for APIs/JSON
- Plain English conclusions

#### Feature 7: Confidence Intervals
- Precision estimates
- 95% CI for all metrics
- Effect size uncertainty

**Key Takeaway**: Professional-grade features for rigorous experimentation

---

### 4. Verification Results Demo (`demo_verification.txt`)
**Purpose**: Framework validation against other libraries  
**Duration**: ~3 minutes to read  
**Best for**: Trust building, accuracy validation

**Contents**:
- Comparison with scipy (baseline)
- Comparison with py-ab-testing
- Comparison with abexp
- Multiple test scenarios
- Agreement analysis

**Scenarios Tested**:
1. Basic conversion rate test
2. Revenue per user (continuous metric)
3. Click-through rate
4. Multi-metric analysis
5. Resolved metric with gap
6. Resolved metric without gap
7. AI metric with gap
8. AI metric without gap

**Key Takeaway**: Our framework produces identical results to established libraries

---

## 🚀 How to Use These Demos

### For Presentations
```bash
# Quick 2-minute overview
type demos\demo_quick_start.txt

# Full 5-minute walkthrough
type demos\demo_real_world_workflow.txt
```

### For Technical Review
```bash
# Browse features interactively
code demos\demo_features.md

# Verify accuracy
type demos\demo_verification.txt
```

### Re-run Demos
```bash
# Quick start
python example_usage.py > demos\demo_quick_start.txt 2>&1

# Real world workflow
python example_real_world_workflow.py > demos\demo_real_world_workflow.txt 2>&1

# Feature showcase
python demo_feature_showcase.py > demos\demo_features.md 2>&1

# Verification
python run_comparison_all.py > demos\demo_verification.txt 2>&1
```

---

## 📊 Demo Comparison Matrix

| Demo | Length | Technical Level | Best For |
|------|--------|-----------------|----------|
| Quick Start | Short (~150 lines) | Beginner | First-time users |
| Real World | Medium (~300 lines) | Intermediate | Understanding workflows |
| Features | Long (~500 lines) | Advanced | Technical evaluation |
| Verification | Medium (~200 lines) | Advanced | Trust building |

---

## 💡 Demo Selection Guide

**"I'm new to A/B testing"**
→ Start with `demo_quick_start.txt`

**"I need to implement A/B testing at my company"**
→ Review `demo_real_world_workflow.txt`

**"I'm evaluating different A/B testing frameworks"**
→ Study `demo_features.md` and `demo_verification.txt`

**"I want to see if this framework is accurate"**
→ Check `demo_verification.txt`

**"I need to present this to stakeholders"**
→ Use `demo_quick_start.txt` for overview, `demo_real_world_workflow.txt` for details

---

## 🎯 Key Differentiators Shown in Demos

### 1. Validation First (Real World Demo)
- A/A testing before A/B testing
- Prevents false results from infrastructure issues

### 2. Proper Sample Sizing (All Demos)
- Uses actual variance from data
- Prevents underpowered experiments

### 3. Multiple Testing Protection (Quick Start, Features)
- Bonferroni and FDR corrections
- Maintains statistical rigor with multiple metrics

### 4. Sequential Testing (Features Demo)
- Peek without inflating error rates
- Early stopping when appropriate

### 5. Quality Checks (All Demos)
- Automatic SRM detection
- MDE calculation
- Prevents invalid conclusions

### 6. Flexibility (Features Demo)
- Any metric definable via Python functions
- Session, user, or custom aggregations
- Works with any data schema

---

## 📝 Output Format Details

### Text Files (.txt)
- Raw console output
- Easy to read in any text editor
- Good for quick review
- Files: `demo_quick_start.txt`, `demo_real_world_workflow.txt`, `demo_verification.txt`

### Markdown Files (.md)
- Formatted for better readability
- Can be viewed in VSCode with preview
- Better for detailed technical content
- Files: `demo_features.md`, `README.md` (this file)

---

## 🔄 Updating Demos

If you modify the framework or example scripts, regenerate demos:

```bash
# Full refresh
python example_usage.py > demos\demo_quick_start.txt 2>&1
python example_real_world_workflow.py > demos\demo_real_world_workflow.txt 2>&1
python demo_feature_showcase.py > demos\demo_features.md 2>&1
python run_comparison_all.py > demos\demo_verification.txt 2>&1
```

---

## 📚 Additional Resources

- **Framework Documentation**: `ab_framework/README.md`
- **Theory Background**: `AB_TESTING_THEORY.md`
- **Main README**: `README.md`
- **Verification Details**: `verification/SCENARIOS_EXPLAINED.md`

---

## ✅ Demo Checklist for Stakeholders

Use this checklist when presenting to stakeholders:

**Quick Demo (5 minutes)**:
- [ ] Show `demo_quick_start.txt` - basic usage
- [ ] Highlight sample size calculation
- [ ] Show statistical results
- [ ] Explain business decision

**Detailed Demo (15 minutes)**:
- [ ] Walk through `demo_real_world_workflow.txt`
- [ ] Explain A/A testing importance
- [ ] Show sequential monitoring
- [ ] Demonstrate decision logic

**Technical Demo (30 minutes)**:
- [ ] Present `demo_features.md` features
- [ ] Show `demo_verification.txt` accuracy
- [ ] Answer technical questions
- [ ] Discuss integration approach

---

## 🎓 Learning Path

1. **Day 1**: Read `demo_quick_start.txt`
   - Understand basic concepts
   - See complete workflow

2. **Day 2**: Study `demo_real_world_workflow.txt`
   - Learn proper validation
   - Understand sequential testing

3. **Day 3**: Explore `demo_features.md`
   - Deep dive into capabilities
   - Compare correction methods

4. **Day 4**: Review `demo_verification.txt`
   - Validate accuracy claims
   - Build confidence in framework

5. **Day 5**: Run your own test
   - Use framework on real data
   - Apply learnings from demos

---

## 📞 Support

If you have questions about these demos or the framework:
- Check the main `README.md`
- Review theory in `AB_TESTING_THEORY.md`
- See framework docs in `ab_framework/README.md`

---

**Last Updated**: November 24, 2025  
**Framework Version**: 1.0.0  
**Python Version**: 3.8+
