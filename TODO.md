# TODO: Production Interface Improvements

Status as of November 30, 2025

## ✅ Completed Items (3.5/6)

### A. API Surface - DONE ✅
- **Status:** Fully implemented (sample-size planning is handled via backend helpers)
- **Location:** `ab_framework/__init__.py`
- **Details:**
  - Clean public API exports: `ABTest`, `QualityChecker` (sample-size planning is available via backend methods on `StatisticalBackend`)
  - Backends kept mostly internal
- **Minor improvement:**
  - Consider removing `OwlBackend` and `StatisticalBackend` from `__all__` to keep them fully internal

### D. Logging & Observability - DONE ✅
- **Status:** Fully implemented
- **Location:** `ab_framework/core.py` - `ExperimentResults` class
- **Details:**
  - `summary()` - Human-readable markdown output
  - `to_dict()` - JSON-safe structure for logging/dashboards
  - `to_dataframe()` - Tabular export
  - Includes timestamps, alpha, correction method, SRM results

### F. ExperimentResults Class - DONE ✅
- **Status:** Fully implemented
- **Location:** `ab_framework/core.py` (lines 337+)
- **Details:**
  - Constructor with all key fields
  - Per-metric results in `metric_results` dict
  - All required output methods implemented

---

## ⚠️ Partially Completed Items

### B. Typed Exceptions and Validation - PARTIAL ⚠️
- **Status:** Validation exists, but no custom exception types
- **Location:** `ab_framework/core.py`
- **What's done:**
  - `_validate_data()` checks required columns and ≥2 variants
  - `_test_metric()` validates metric output is a Series
  - Clear error messages with `ValueError` and `TypeError`
- **What's missing:**
  - Custom exception hierarchy for better error handling

#### TODO: Implement Custom Exceptions
```python
# Add to ab_framework/exceptions.py (new file)

class ExperimentError(Exception):
    """Base exception for ab_framework."""
    pass

class ExperimentDefinitionError(ExperimentError):
    """Raised when experiment setup is invalid.
    
    Examples:
    - Missing required columns (variant_col, unit_id)
    - Less than 2 variants in data
    - Invalid experiment name or configuration
    """
    pass

class DataValidationError(ExperimentError):
    """Raised when data doesn't meet requirements.
    
    Examples:
    - Metric function returns non-Series
    - Metric output has wrong index (not unit_id)
    - Non-numeric values in metric results
    - NaN or infinite values in critical columns
    """
    pass

class BackendError(ExperimentError):
    """Raised when statistical backend fails.
    
    Examples:
    - Backend computation error
    - Unsupported metric type for backend
    - Invalid statistical test parameters
    """
    pass

class MetricDefinitionError(ExperimentError):
    """Raised when metric definition is invalid.
    
    Examples:
    - Metric function signature is incorrect
    - Metric returns wrong data structure
    - Metric name conflicts with existing metric
    """
    pass
```

**Steps:**
1. Create `ab_framework/exceptions.py` with exception classes
2. Update `ab_framework/__init__.py` to export exceptions
3. Replace `ValueError` → `ExperimentDefinitionError` in `_validate_data()`
4. Replace `TypeError` → `MetricDefinitionError` in `_test_metric()`
5. Use `DataValidationError` for data quality issues
6. Use `BackendError` for backend failures
7. Update tests to catch specific exception types

---

## ❌ Not Implemented Items

### C. Config & Reproducibility - NOT DONE ❌
- **Status:** Not implemented
- **Current approach:** Kwargs in `ABTest.__init__`
- **What's missing:** Structured configuration object

#### TODO: Implement Config Object
```python
# Add to ab_framework/config.py (new file)

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class ExperimentConfig:
    """Configuration for an A/B test experiment.
    
    This dataclass captures all experiment settings for reproducibility
    and can be serialized/deserialized for experiment tracking systems.
    
    Example:
        >>> config = ExperimentConfig(
        ...     name="pricing_test_v2",
        ...     variant_col="variant",
        ...     unit_id="user_id",
        ...     alpha=0.05,
        ...     correction="holm"
        ... )
        >>> test = ABTest.from_config(data=df, config=config)
    """
    name: str
    variant_col: str = "variant"
    unit_id: str = "user_id"
    alpha: float = 0.05
    correction: Optional[str] = None  # "bonferroni", "holm", "bh", None
    backend: Optional[str] = None     # "owl", "scipy", "abexp", None (auto-detect)
    tails: str = "two-sided"          # "one-sided", "two-sided"
    check_srm: bool = True
    srm_alpha: float = 0.001
    metadata: Dict[str, Any] = field(default_factory=dict)  # experiment_id, owner, etc.
    
    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization."""
        return {
            'name': self.name,
            'variant_col': self.variant_col,
            'unit_id': self.unit_id,
            'alpha': self.alpha,
            'correction': self.correction,
            'backend': self.backend,
            'tails': self.tails,
            'check_srm': self.check_srm,
            'srm_alpha': self.srm_alpha,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ExperimentConfig':
        """Create config from dictionary."""
        return cls(**data)
```

**Steps:**
1. Create `ab_framework/config.py` with `ExperimentConfig` dataclass
2. Add `ABTest.from_config(data, config)` classmethod in `core.py`
3. Store config in `ExperimentResults` for reproducibility
4. Update `ExperimentResults.to_dict()` to include config
5. Export `ExperimentConfig` from `ab_framework/__init__.py`
6. Add examples in tests showing config-based initialization
7. Document config serialization for experiment tracking

---

### E. Documentation & Examples - NOT DONE ❌
- **Status:** Not implemented
- **Current state:** Tests serve as informal examples but no user-facing docs
- **What's missing:** User documentation and example recipes

#### TODO: Create Documentation Structure

**Directory structure:**
```
docs/
├── README.md                          # Overview and quick start
├── api/
│   ├── ABTest.md                      # ABTest API reference
│   ├── ExperimentResults.md           # Results object documentation
│   ├── QualityChecker.md              # SRM and quality checks
│   └── SampleSizePlanning.md         # Power analysis and planning via backend helpers
├── examples/
│   ├── 01_simple_conversion.md        # Basic binary metric test
│   ├── 02_revenue_per_user.md         # Continuous metric with filtering
│   ├── 03_ctr_impression_level.md     # Event-level analysis
│   ├── 04_multi_metric_dashboard.md   # Multiple metrics + correction
│   ├── 05_agent_bot_binary.md         # Real-world binary metric
│   ├── 06_agent_bot_continuous.md     # Real-world continuous metric
│   └── 07_custom_metrics.md           # Advanced metric definitions
├── guides/
│   ├── metric_definitions.md          # How to define metrics correctly
│   ├── unit_of_analysis.md            # User vs session vs impression
│   ├── multiple_testing.md            # When to use Bonferroni/Holm
│   ├── srm_detection.md               # Understanding SRM checks
│   └── production_usage.md            # Best practices for production
└── theory/
    ├── statistical_tests.md           # What tests are used when
    ├── power_analysis.md              # Sample size calculations
    └── effect_sizes.md                # Interpreting lifts and differences
```

**Priority examples to create:**

1. **`examples/01_simple_conversion.md`** - Based on `test_scenario1_conversion()`
   ```markdown
   # Simple Conversion Rate Test
   
   Testing whether variant B improves conversion rate over control A.
   
   ## Data Structure
   - Impression-level data (one row per impression)
   - Columns: user_id, impression_id, variant, converted, timestamp
   
   ## Code
   [Show complete working example]
   
   ## Interpretation
   [Explain p-value, lift, significance]
   ```

2. **`examples/02_revenue_per_user.md`** - Based on `test_scenario2_revenue()`
3. **`examples/03_ctr_impression_level.md`** - Based on `test_scenario3_ctr()`
4. **`examples/04_multi_metric_dashboard.md`** - Based on `test_multi_metric()`

**Steps:**
1. Create `docs/` directory structure
2. Write `docs/README.md` with quick start guide
3. Create example files based on existing test scenarios
4. Add inline code comments explaining each step
5. Include "Common Pitfalls" section in each example
6. Add "When to Use" guidance for each pattern
7. Link examples from main README.md

**Template for each example:**
```markdown
# [Example Title]

## Use Case
[When would you use this pattern?]

## Data Requirements
- Structure: [user-level | session-level | impression-level]
- Required columns: [list]
- Unit of analysis: [user | session | impression]

## Complete Code Example
```python
[Full working example with comments]
```

## Interpreting Results
[How to read the output]

## Common Pitfalls
- [Pitfall 1 and how to avoid it]
- [Pitfall 2 and how to avoid it]

## See Also
- [Link to related examples]
- [Link to theory docs]
```

---

## Implementation Priority

### High Priority (Block production use)
1. **Custom Exceptions (B)** - Important for debugging and error handling
   - Estimated effort: 2-3 hours
   - Impact: Better developer experience, clearer error messages

2. **Basic Documentation (E)** - At minimum: README + 4 core examples
   - Estimated effort: 4-6 hours
   - Impact: Enables other teams to self-serve

### Medium Priority (Nice to have)
3. **Config Object (C)** - Improves reproducibility and tracking
   - Estimated effort: 3-4 hours
   - Impact: Better experiment governance and auditability

4. **Extended Documentation (E)** - Guides and API reference
   - Estimated effort: 8-10 hours
   - Impact: Reduces support burden, increases adoption

### Low Priority (Future improvements)
5. **Hide backends from public API (A)** - Minor cleanup
   - Estimated effort: 30 minutes
   - Impact: Slightly cleaner API surface

---

## Success Criteria

The framework is "production interface ready" when:

- ✅ All custom exceptions are implemented and used consistently
- ✅ At least 4 core examples exist with clear documentation
- ✅ Config object enables reproducible experiments
- ✅ Teams can use the framework without asking for help
- ✅ Error messages clearly explain what went wrong and how to fix it
- ✅ All public API methods have docstrings with examples

---

## Notes

### Why these items matter:

- **Custom exceptions:** Generic `ValueError`/`TypeError` make debugging hard in production. Typed exceptions let users catch specific error categories and handle them appropriately.

- **Config object:** Makes experiments reproducible and trackable. Can serialize config to experiment management systems. Enables "config-driven" experiments where settings come from YAML/JSON files.

- **Documentation:** Current tests are great for verification but not discoverable by other teams. Need cookbook-style examples that teams can copy-paste and adapt.

### Current strengths (don't break these):

- ✅ Clean, intuitive API (`@test.metric` decorator is excellent)
- ✅ Multi-metric + correction handling (unique value vs owl/abexp)
- ✅ SRM checks built-in (rarely found in AB packages)
- ✅ Sample size planning integrated via backend helpers (no standalone calculator class)
- ✅ Backend-agnostic design
- ✅ Strong verification suite

### Future considerations (post-production):

- Bayesian backend option
- Sequential testing / early stopping
- Stratified analysis (by segment)
- Covariate adjustment (CUPED)
- Experiment metadata tracking integration
- Automated alerts for SRM/unusual patterns
