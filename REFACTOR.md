# ABTest Refactor Plan: Primary Metric and Soft Monitoring

This document summarizes the current state of the `ABTest` API and the planned refactor to support:

- A **primary metric** (decision-driving).
- Additional metrics in **soft monitoring** mode (descriptive / non-blocking).
- A future extension path toward **hard guardrails** and sample-size planning, without complicating the simple use cases.

The goal is to keep the interface minimal for the single-metric case, while enabling more advanced setups when needed.

---

## 1. Current `ABTest` Design (Post-Changes)

File: `ab_framework/core.py`

### 1.1. Constructor

```python
class ABTest:
    def __init__(
        self,
        name: str,
        backend: Optional[StatisticalBackend] = None,
        variants: Optional[List[str]] = None,
    ):
        self.name = name
        self.backend = backend if backend is not None else AbexpBackend()
        self.alpha = 0.05
        self.timestamp = None

        # Explicit variants configuration (e.g. ["A", "B"])
        self.variants: List[str] = list(variants) if variants is not None else ["A", "B"]

        # Metric registry: name -> metadata dict
        self._metrics: Dict[str, Dict[str, Any]] = {}

        if len(self.variants) != 2:
            raise ValueError("'variants' must contain exactly 2 labels")
```

Validation:

```python
def analyze(self, data: pd.DataFrame, *, run_srm_check: bool = True, observed_counts: Optional[Dict[str, int]] = None, ...):
    # Data validation happens at analysis time.
    # The core does NOT inspect the DataFrame schema to infer units/variants;
    # metric functions compute per-variant sufficient statistics.
    # If SRM is enabled, observed_counts must be provided explicitly.
    ...
```

**Outcome:**  
- `ABTest` now always analyzes exactly 2 variants, either configured explicitly or inferred from the data once at construction time.

---

### 1.2. Metric Registration and Roles

Decorator:

```python
def metric(
    self,
    func: Callable = None,
    *,
    metric_type: str,
    is_primary: bool = False,
    monitor_alpha: Optional[float] = None,
    monitor_power: Optional[float] = None,
    inferiority_margin: Optional[float] = None,
) -> Callable:
    def decorator(f: Callable) -> Callable:
        if metric_type not in ("proportion", "mean"):
            raise ValueError(...)
        if is_primary:
            existing_primary = getattr(self, "_primary_metric", None)
            if existing_primary is not None and existing_primary != f.__name__:
                raise ValueError("Primary metric already set ...")
            self._primary_metric = f.__name__

        self._metrics[f.__name__] = {
            "func": f,
            "metric_type": metric_type,
            "is_primary": is_primary,
            "monitor_alpha": monitor_alpha,
            "monitor_power": monitor_power,
            "inferiority_margin": inferiority_margin,
        }
        return f

    if func is not None:
        return decorator(func)
    return decorator
```

Programmatic registration (without using `@` syntax):

```python
def my_metric(data):
    user_level = data.groupby(["variant", "user_id"])["value"].sum()
    return {
        "A": {"mean": float(user_level.loc["A"].mean()), "std": float(user_level.loc["A"].std(ddof=1)), "n": int(user_level.loc["A"].shape[0])},
        "B": {"mean": float(user_level.loc["B"].mean()), "std": float(user_level.loc["B"].std(ddof=1)), "n": int(user_level.loc["B"].shape[0])},
    }

test.metric(metric_type="mean")(my_metric)
```

Primary metric selection is done at registration time:

```python
@test.metric(metric_type="proportion", is_primary=True)
def conversion_rate(data):
    user_level = data.groupby(["variant", "user_id"])["converted"].max()
    return {
        "A": {"successes": int(user_level.loc["A"].sum()), "n": int(user_level.loc["A"].shape[0])},
        "B": {"successes": int(user_level.loc["B"].sum()), "n": int(user_level.loc["B"].shape[0])},
    }
```

**Key behavior now:**

- Exactly one metric may be designated as primary (`is_primary=True`).
- All other metrics act as **monitors** (soft monitoring) and do **not** block decisions.

---

### 1.3. Metric Testing & Soft-Monitor Metadata

Metric test:

```python
def _test_metric(
    self,
    metric_name: str,
    variant_a: str,
    variant_b: str,
) -> Dict[str, Any]:
    metric_df = self._compute_metric(metric_name)
    ...

    entry = self._metrics.get(metric_name)
    metric_type = entry["metric_type"]

    if metric_type == "proportion":
        # proportion_z_test via backend
        ...
    elif metric_type == "mean":
        # mean_t_test via backend
        ...
    ...

    # Add metadata
    result["metric_name"] = metric_name
    result["variant_control"] = variant_a
    result["variant_treatment"] = variant_b
    result["significant"] = result["p_value"] < self.alpha
    result["sample_size_control"] = len(data_a)
    result["sample_size_treatment"] = len(data_b)

    # Attach soft monitoring metadata from registry
    try:
        reg = self._metrics.get(metric_name, {})
        for k in ("monitor_alpha", "monitor_power", "inferiority_margin", "is_primary"):
            if k in reg:
                result[k] = reg[k]
    except Exception:
        pass

    return result
```

**Outcome:**

- Each metric result now carries:
  - `monitor_alpha`, `monitor_power`, `inferiority_margin`, `is_primary` if configured.
- These are **descriptive** in current implementation (do not enforce hard blocks yet).

---

### 1.4. Analyze API

```python
def analyze(
    self,
    metrics: Optional[List[str]] = None,
    correction: Optional[str] = None,
    run_srm_check: bool = True,
) -> "ExperimentResults":
    if not self.variants or len(self.variants) != 2:
        raise ValueError("ABTest.variants must contain exactly 2 variant labels")
    variant_a, variant_b = self.variants

    if metrics is None:
        metrics = list(self._metrics.keys())
    if not metrics:
        raise ValueError("No metrics specified and no metrics registered")

    # SRM
    srm_result = None
    if run_srm_check:
        counts = self.data.groupby(self.variant_col)[self.unit_id].nunique().to_dict()
        counts_filtered = {k: v for k, v in counts.items() if k in [variant_a, variant_b]}
        checker = QualityChecker()
        srm_result = checker.check_srm(counts_filtered)

    metric_results: Dict[str, Dict[str, Any]] = {}
    for metric_name in metrics:
        try:
            result = self._test_metric(metric_name, variant_a, variant_b)
            metric_results[metric_name] = result
        except Exception as e:
            traceback.print_exc()
            metric_results[metric_name] = {"error": str(e), "metric_name": metric_name}

    if correction and len(metrics) > 1:
        metric_results = self._apply_correction(metric_results, correction)

    return ExperimentResults(
        experiment_name=self.name,
        timestamp=self.timestamp,
        metric_results=metric_results,
        srm_result=srm_result,
        alpha=self.alpha,
        correction=correction,
        variants=self.variants,
        primary_metric=getattr(self, "_primary_metric", None),
    )
```

**Key simplifications:**

- Variants always taken from `self.variants` (set once in `__init__` / `_validate_data`).
- `metrics` is optional; defaults to all registered metrics.

---

### 1.5. ExperimentResults and Soft-Monitoring Decision

Constructor:

```python
class ExperimentResults:
    def __init__(
        self,
        experiment_name: str,
        timestamp: str,
        metric_results: Dict[str, Dict],
        srm_result: Optional[Dict],
        alpha: float,
        correction: Optional[str],
        variants: Optional[List[str]] = None,
        primary_metric: Optional[str] = None,
    ):
        self.experiment_name = experiment_name
        self.timestamp = timestamp
        self.metric_results = metric_results
        self.srm_result = srm_result
        self.alpha = alpha
        self.correction = correction
        self.variants = variants
        self.primary_metric = primary_metric
```

`summary()`:

- Prints experiment info, SRM result.
- Lists metrics with:
  - `Type`, `Role` (`primary` vs `monitor`), and optional monitor settings (alpha, power, inferiority_margin).
  - A small info-only “NI check” against `inferiority_margin` if present.

`to_dict()` adds `primary_metric`.

Soft-monitoring decision helper:

```python
def decision_soft_monitoring(self) -> str:
    """Primary-driven decision helper for soft monitoring mode.

    Returns a concise decision based only on the primary metric.
    Other metrics are treated as descriptive and do not block shipping.
    """
    if not self.primary_metric:
        return "No primary metric configured. Set is_primary=True on one metric."
    res = self.metric_results.get(self.primary_metric)
    if not res or "error" in res:
        return f"Primary metric '{self.primary_metric}' has no valid result."
    p = res.get("p_value")
    sig = res.get("significant", False)
    lift = res.get("lift")
    if sig:
        return (
            f"Ship: primary '{self.primary_metric}' is significant "
            f"(p={p:.4f}, lift={lift:.2%}). Monitored metrics are descriptive only."
        )
    return (
        f"Do not ship: primary '{self.primary_metric}' is not significant "
        f"(p={p:.4f}). Monitored metrics are descriptive only."
    )
```

**Interpretation:**

- Current mode is **soft monitoring** only:
  - Primary metric drives the decision.
  - Other metrics are displayed with statistics and optional NI-check info.
  - They do not block shipping in this helper.

---

## 2. Desired Behavior / Feature Set

### 2.1. Use Cases

1. **Single-metric A/B** (simplest):
   - One metric, designated as `is_primary=True`.
   - User calls:
     ```python
     test = ABTest(...)
     @test.metric(metric_type="proportion", is_primary=True)
     def conversion_rate(df):
         ...
     results = test.analyze()
     print(results.decision_soft_monitoring())
     ```
   - No need to think about monitoring vs guardrails.

2. **Primary + soft monitoring (current behavior)**:
   - One primary metric.
   - One or more additional metrics with:
     - `monitor_alpha`, `monitor_power`, `inferiority_margin` optionally set.
   - Use `decision_soft_monitoring()` for rollout decision.
   - All extra metrics are descriptive only.

3. **Future (not yet implemented): primary + hard guardrails**:
   - Some non-primary metrics behave as **hard guardrails**:
     - Configured with role `hard_guardrail` and a non-inferiority margin.
     - Contribute to **sample-size planning** and **blocking** decisions if degraded beyond margin.
   - This requires:
     - A roles concept (`primary`, `hard_guardrail`, `soft_monitor`).
     - Sample-size utilities.
     - A guardrail-aware decision function.

---

## 3. Refactor Tasks / TODO

### 3.1. Roles Cleanup (optional, future)

**Goal:** Move from `is_primary` boolean to an explicit `role` field (while keeping backward compatibility).

- Introduce an internal role representation (e.g. string or small Enum-like literal):
  - `"primary"`, `"monitor"` (and later `"hard_guardrail"`).
- Map:
  - `is_primary=True` → `role="primary"`.
  - Default (no primary flag) → `role="monitor"`.

This allows a clean extension to hard guardrails without changing existing APIs.

---

### 3.2. Sample Size Planning (primary-only first)

**Goal:** Provide minimal sample-size utilities for the primary metric, aligned with current backend capabilities.

Proposed API on `ABTest`:

```python
def sample_size_primary(
    self,
    baseline_rate: Optional[float] = None,
    mde: Optional[float] = None,
    alpha: Optional[float] = None,
    power: Optional[float] = None,
) -> Dict[str, Any]:
    ...
```

- If `primary` is a `"proportion"` metric:
  - Delegate to something like `backend.sample_size_proportion(...)`.
- If `primary` is a `"mean"` metric:
  - Delegate to `backend.sample_size_mean(...)` (or similar when available).
- Use:
  - Passed `alpha` / `power` if provided,
  - Else:
    - `monitor_alpha` / `monitor_power` from the primary metric config if present,
    - Else defaults (e.g. `alpha=0.05`, `power=0.8`).

Return shape example:

```python
{
    "metric": primary_metric_name,
    "metric_type": "proportion",
    "alpha": alpha_used,
    "power": power_used,
    "baseline_rate": baseline_rate,
    "mde": mde,
    "n_per_variant": 1500,
}
```

**Notes:**

- This is intentionally **primary-only** to keep the first step small.
- Guardrail-aware sample size (max over primary + hard guardrails) can be added later.

---

### 3.3. Guardrail / Hard Mode (design stub, future)

**Not implemented yet; outline only:**

- Extend metric registration to allow:

  ```python
  @test.metric(
      metric_type="proportion",
      is_primary=False,
      monitor_alpha=0.05,
      monitor_power=0.8,
      inferiority_margin=-0.01,  # NI margin
      # role="hard_guardrail" in future
  )
  def resolved_rate(df):
      ...
  ```

- Introduce a dedicated decision helper, e.g.:

  ```python
  def decision_with_guardrails(self) -> str:
      ...
  ```

  Behavior:

  - Use primary metric as in `decision_soft_monitoring`.
  - For each hard guardrail metric:
    - Check non-inferiority: lower CI bound >= `-inferiority_margin`.
  - Combined rule:
    - Ship only if:
      - Primary significant (or meets configured superiority criterion), and
      - All hard guardrails are non-inferior.

- Later, add:

  ```python
  def sample_size_all(self) -> Dict[str, Any]:
      # per-metric sample size as if alone

  def sample_size(self) -> Dict[str, Any]:
      # combined: max over primary + hard guardrails
  ```

The current `monitor_alpha`, `monitor_power`, `inferiority_margin` fields were added exactly to support this evolution, but are currently **soft** and informational only in `summary()`.

---

## 4. Example: Using the Current API

### 4.1. Single primary + soft monitoring metric

```python
from ab_framework.core import ABTest

test = ABTest(name="agent_sessions_quality_vs_resolution_AB", variants=["A", "B"])

observed_counts = df.groupby("variant")["user_id"].nunique().to_dict()

@test.metric(
    metric_type="proportion",
    is_primary=True,
)
def quality_rate(data):
    user_level = data.groupby(["variant", "user_id"])["quality"].max()
    summary = user_level.groupby("variant").agg(["sum", "count"]).to_dict("index")
    return {v: {"successes": int(d["sum"]), "n": int(d["count"])} for v, d in summary.items()}

@test.metric(
    metric_type="proportion",
    # monitor-only, with some NI margin metadata for reporting
    monitor_alpha=0.05,
    monitor_power=0.8,
    inferiority_margin=-0.01,
)
def resolved_rate(data):
    user_level = data.groupby(["variant", "user_id"])["resolved"].max()
    summary = user_level.groupby("variant").agg(["sum", "count"]).to_dict("index")
    return {v: {"successes": int(d["sum"]), "n": int(d["count"])} for v, d in summary.items()}

results = test.analyze(df, run_srm_check=True, observed_counts=observed_counts)

print(results.summary())
print(results.decision_soft_monitoring())
```

- Decision is driven solely by `quality_rate`.
- `resolved_rate` is displayed with stats and optional NI-check note, but does **not** block shipping.

---

## 5. Summary

- The codebase has been refactored to:
  - Capture a **primary metric** in `ABTest` and in `ExperimentResults`.
  - Treat all other metrics as **soft monitors** with optional descriptive metadata (`monitor_alpha`, `monitor_power`, `inferiority_margin`).
  - Simplify `analyze()` to:
    - Always use the experiment’s configured 2 variants.
    - Default to all registered metrics if `metrics` not specified.
- A helper `decision_soft_monitoring()` now provides a simple, primary-driven decision summary that explicitly states that other metrics are descriptive only.
- Future work (optional, not implemented yet) includes:
  - Introducing explicit metric roles (primary / hard guardrail / soft monitor).
  - Adding sample-size utilities for the primary metric and, later, guardrail-aware planning.
  - Adding a guardrail-aware decision helper that enforces non-inferiority constraints on selected metrics.
