> Purpose: Overview of demo scripts and instructions on how to run them
> Generated: Manually authored, maintained under version control.

# AB Framework - Demo Files

This directory contains ready-to-run demonstration files showcasing the AB Framework's capabilities.

## 📁 Demo Files Overview

### 1. Quick Start Demo (`demo_quickstart_basic_workflow.md`)
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

### 2. Real World Workflow Demo (`demo_real_world_ai_model_rollout.md`)
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

### 3. Significant CTR Uplift Demo (`demo_significant_ctr_uplift.md`)
**Purpose**: Show a clear, statistically significant win  
**Duration**: ~1 minute to read  
**Best for**: Seeing what a “ship it” result looks like

**Contents**:
- Impression-level click-through rate test
- Control vs. treatment CTR
- Statistically significant uplift with clear CI
- Plain-English interpretation and ship recommendation

**Key Takeaway**: What a strong, statistically significant result and conclusion looks like

---

## 🚀 How to Use These Demos

### For Presentations
```bash
# Quick 2-minute overview
type demos\demo_quickstart_basic_workflow.md

# Full 5-minute walkthrough
type demos\demo_real_world_ai_model_rollout.md

# One-slide uplift story
type demos\demo_significant_ctr_uplift.md
```

### Run Live Python Demos
```bash
# Quick start (basic workflow)
python demos\demo_quickstart_basic_workflow.py

# Real world AI model rollout
python demos\demo_real_world_ai_model_rollout.py

# Significant-result CTR example
python demos\demo_significant_ctr_uplift.py
```

---

## 📊 Demo Comparison Matrix

| Demo | Length | Technical Level | Best For |
|------|--------|-----------------|----------|
| Quick Start (basic workflow) | Short (~150 lines) | Beginner | First-time users |
| Real World AI model rollout | Medium (~300 lines) | Intermediate | Understanding production workflows |
| Significant CTR uplift | Very short | Beginner | Seeing a clear win example |

---

## 💡 Demo Selection Guide

**"I'm new to A/B testing"**  
→ Start with `demo_quickstart_basic_workflow.md`

**"I need to implement A/B testing at my company"**  
→ Review `demo_real_world_ai_model_rollout.md`

**"I want to see what a clear win looks like"**  
→ Skim `demo_significant_ctr_uplift.md`

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

### Markdown Files (.md)
- Formatted for better readability
- Can be viewed in VSCode with preview
- Better for detailed technical content
- Files: `demo_quickstart_basic_workflow.md`, `demo_real_world_ai_model_rollout.md`, `demo_significant_ctr_uplift.md`, `README.md` (this file)

---

## 🔄 Updating Demos

If you modify the framework or example scripts, you can optionally refresh the markdown outputs used in presentations:

```bash
# Refresh quick-start workflow demo
python demos\demo_quickstart_basic_workflow.py > demos\demo_quickstart_basic_workflow.md 2>&1

# Refresh real-world AI model rollout demo
python demos\demo_real_world_ai_model_rollout.py > demos\demo_real_world_ai_model_rollout.md 2>&1

# Refresh significant CTR uplift demo
python demos\demo_significant_ctr_uplift.py > demos\demo_significant_ctr_uplift.md 2>&1
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
