# Flask A/B Planning App — Implementation Plan

Goal: Build a small Flask web app (in `webapp/` under repo root) to collect per-metric planning inputs and return sample size plans and guidance consistent with the framework’s soft monitoring mode.

## Scope
- Inputs per metric:
  - name (string)
  - type: `proportion` | `mean`
  - baselines:
    - proportion: `baseline_rate ∈ [0,1]`
    - mean: `baseline_mean (float)`, `baseline_std > 0`
  - planning params: `alpha ∈ (0,1)`, `power ∈ (0,1)`, `mde > 0` (relative lift), optional `allocation_ratio ∈ (0,1)` (default 0.5)
  - guard margin (optional): `inferiority_margin ≥ 0` (informational for NI checks in analysis)
- Multiple metrics allowed; show adjusted alpha suggestion (Bonferroni) when `N > 1`.
- Optional duration estimate if `daily_per_variant` provided.

## Architecture
- Folder: `webapp/`
  - `app.py`: Flask entry point with routes
  - `templates/`
    - `layout.html`: base layout (header/sidebar/content)
    - `form.html`: planning form (dynamic metrics)
    - `results.html`: per-metric planning results
  - `static/css/styles.css`: simple CSS to echo Copilot Studio-style UI
  - `README.md`: run instructions and notes (added after code scaffold)

## Routes
- `GET /` → Render `form.html`
  - Form allows adding/removing metric rows with fields above
  - Optional global inputs: `allocation_ratio`, `daily_per_variant`
- `POST /plan` → Compute planning for each metric
  - For `type == proportion`: call `OwlBackend.sample_size_proportion(baseline_rate, mde, alpha, power)`
  - For `type == mean`: call `OwlBackend.sample_size_mean(baseline_mean, baseline_std, mde, alpha, power)`
  - Compute per-metric: `total_size`, `control_size`, `treatment_size`
  - If multiple metrics: `alpha_adjusted = alpha / N` (suggestion)
  - If `daily_per_variant` present: days_needed = treatment_size / daily_per_variant; echo assumptions
  - Return `results.html` with cards for each metric

## Backend Usage
- Prefer `OwlBackend` for planning calls (consistent with demos)
- Instantiate backend directly; no need to create an `ABTest` for planning
- Future `/analyze` (optional): build an `ABTest`, register metrics programmatically, call `analyze(..., correction=None)` and show soft monitoring summary

## UI & UX
- Copilot Studio-like layout:
  - Left sidebar: quick settings (alpha/power defaults, allocation)
  - Main: metric list with add/remove row; client-side validation hints
  - Right panel: explanations (MDE, alpha/power, NI guardrail note)
- Results page:
  - Card per metric: totals and assumptions (baseline, target rate/mean, absolute MDE, alpha/power, allocation)
  - If `N>1`: show Bonferroni adjusted-alpha hint
  - If guard margin set: note NI check is applied during analysis (informational)

## Validation
- `type ∈ {proportion, mean}`
- `alpha, power ∈ (0,1)`
- `mde > 0` (relative lift)
- `allocation_ratio ∈ (0,1)`; default 0.5
- Proportion: `baseline_rate ∈ [0,1]`
- Mean: `baseline_std > 0`; `baseline_mean` any float
- Optional `daily_per_variant > 0`
- Return clear inline errors, keep entered values on error

## Security & Ops
- Dev server only: bind `127.0.0.1`, default port 5000
- Limit file size if upload is added later; currently no uploads
- Sanitize and validate numeric inputs; reject malformed requests

## Dependencies
- Add `Flask` to `requirements.txt` (Flask brings Jinja2)
- Use existing `pandas`, `numpy`, `scipy`, `owl-ab-test` already in repo

## Run (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FLASK_APP = "webapp/app.py"; $env:FLASK_ENV = "development"
flask run
```
Or:
```powershell
python webapp\app.py
```

## Milestones
1) Implement `form.html` + `POST /plan` wiring to backend planning
2) Render `results.html` with per-metric cards and optional duration
3) Add CSS polish to match screenshot style
4) Optional: add `/analyze` soft monitoring summary using `ABTest`

## Acceptance Criteria
- User can add multiple metrics, submit, and see valid sample size plans per metric
- Alpha/power defaults can be overridden per metric
- Bonferroni suggestion shown when multiple metrics
- Guard margin displayed as NI note (planning-only)
- Clean layout and basic validation; runs locally via commands above
