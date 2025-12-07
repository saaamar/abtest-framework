# Flask Agent A/B Planning App — Implementation Plan

Goal: Build a small Flask web app (in `webapp/` under repo root) to plan and monitor an A/B experiment between two AI agents ("Original" and "B") by collecting planning inputs (primary metric, alpha, power, MDE%) and returning sample size plans and daily experiment results, consistent with the framework’s soft monitoring mode.

## Screens & Flow

1. **Screen 1 — Starter Screen (`starter.html`)**
   - Static overview screen matching the Copilot-style screenshot.
   - All numbers and text are hardcoded for the demo.
   - Only interactive element: **“Run Experiment”** button.
   - When clicked → navigates to **Screen 2 — Experiment Setup**.

2. **Screen 2 — Experiment Setup (`form.html` inside `configure_experiment.html`)**
   - Agents panel on the left, experiment configuration on the right (reverse engineered from second screenshot; see concrete HTML section below).
   - User selects:
     - Primary metric (single select).
     - Additional metrics (multi-select, can “select all”).
       - Each additional metric can be labeled as `guardrail` or `soft_monitoring` (but we currently implement only soft monitoring).
     - Planning parameters: alpha, power, MDE (%) for the primary metric.
   - Buttons:
     - **“Calculate sample size”**:
       - Uses recent historical data (e.g. last 7 days) and `ab_framework` planning helpers to compute:
         - Required sample size (per variant and total) for the primary metric.
         - Estimated experiment duration based on traffic.
       - Updates the right-hand planning panel with the computed plan (cards).
     - **“Run experiment”**:
       - Enabled after a valid plan exists (user is “satisfied” with sample size and duration).
       - When clicked → navigates to **Screen 3 — Experiment Results** with chosen agents and metrics.

3. **Screen 3 — Experiment Results (`results.html` inside `configure_experiment.html`)**
   - Same overall layout (top bar, left agents panel, right results panel).
   - Top bar includes a **“today picker”** control (date picker or previous/next day).
   - For the selected “today” date:
     - Loads relevant static JSONs from `data/agent_data/` (e.g., up to that date / last N days).
     - Computes metrics on the fly using shared helpers based on `demos/agent_sessions`.
     - Calls `analyze()` from `ab_framework` using the experiment configuration and computed metrics.
     - Displays:
       - One prominent card for the **primary metric**.
       - One card per additional metric.
       - Each card shows effect (lift/degradation) and a **red/green indication**:
         - Green for uplift / acceptable behavior.
         - Red for degradation / concerning behavior.
   - Changing the “today” date re-runs `analyze()` for that date and refreshes all metric cards.
   - **Per-day results are not stored in SQLite**; they are always recomputed on demand from `data/agent_data/` plus `ab_framework`.

## Scope

- Experiment entities:
  - Two agents (per demo scenario):
    - `agent_id`
    - `display_name` (e.g. "Original", "B")
    - `model_name` (string)
    - `instructions` (multi-line text)
  - Agents are populated for the demo either:
    - Hardcoded in Python, or
    - Loaded from a small JSON/txt file under `webapp/` (e.g. `agents.json`).

- Metrics:
  - Primary metric (single-select):
    - Dropdown options (tied to existing agent-session metrics), for example:
      - `quality_ratio` — proportion of high-quality sessions.
      - `resolved_ratio` — proportion of resolved sessions.
      - (Optionally extendable later with additional derived metrics.)
    - Internally treated as a `proportion` metric with:
      - `baseline_rate ∈ [0,1]` (per metric, estimated from recent `data/agent_data/` or from preconfigured values).
  - Additional metrics (multi-select):
    - Same pool as above (e.g. `quality_ratio`, `resolved_ratio`, `csat`, etc.).
    - For each selected additional metric:
      - Role selector: `guardrail` | `soft_monitoring`.
      - Implementation note: For now, **only soft monitoring is functionally supported**; guardrail is recorded (label) but not enforced in logic.

- Planning parameters (per planning request, configured on Screen 2):
  - `alpha ∈ (0,1)` — **UI label:** "Alpha (significance level)". Use "Alpha" in setup; reserve "P value" for results.
  - `power ∈ (0,1)` — **UI label:** "Power".
  - `mde_percent > 0` — **UI label:** "MDE (%)"; internally converted to relative lift:
    - `mde_relative = mde_percent / 100`.
  - Optional `allocation_ratio ∈ (0,1)` (default 0.5).
  - Optional `daily_per_variant > 0` (can be derived from recent data or user-entered).
  - Guard margin (optional): `inferiority_margin ≥ 0` (informational for NI checks in analysis).

- Planning vs analysis:
  - Planning (sample size, duration) is done on Screen 2 using historical data from `data/agent_data/`.
  - Analysis (daily experiment results) is done on Screen 3 using `analyze()` by date, with metrics recomputed from the same static JSONs.

## Architecture

- Framework:
  - **Flask** (not Django) for a lightweight, local demo.
  - Classic server-rendered views (HTML templates + form posts), no separate SPA or heavy REST API layer.

- Folder: `webapp/`
  - `app.py`: Flask entry point with routes and minimal wiring for SQLite via builtin `sqlite3` (no SQLAlchemy).
  - Optionally:
    - `agent_data_service.py`: helpers to load `data/agent_data/` JSONs and compute metrics (reusing logic from `demos/agent_sessions`).
    - `ab_planning_service.py`: helpers that wrap `ab_framework` planning and analysis calls.
  - `templates/`
    - `overview.html`: **static starter screen** (Screen 1; first screenshot).
    - `configure_experiment.html`: base layout for Screens 2 and 3:
      - Top bar with app title and date controls (for results screen).
      - Left agents sidebar.
      - Right planning/results panel (inner content varies by route).
    - `form.html`: experiment setup view rendered inside `configure_experiment.html` (Screen 2).
    - `results.html`: experiment results view rendered inside `configure_experiment.html` (Screen 3).
  - `static/css/styles.css`:
    - CSS to closely match the screenshots:
      - Dark header/top bar with date control on results screen.
      - Left panel with agent list and details (background, borders, hover/selected states).
      - Right panel with labeled form controls (primary metric dropdown, alpha, power, MDE%), results cards, and buttons.
      - Consistent spacing, typography, and button styles across starter/setup/results screens.
  - `agents.json` (optional): demo configuration file listing the two agents (Original, B) with model + instructions.
  - `ab_demo.db`: SQLite database file for experiment configuration (see schema below).
  - `README.md`: run instructions and notes (added after code scaffold).

## Database Model (SQLite via builtin `sqlite3`)

- Use **Python’s builtin `sqlite3`**, not SQLAlchemy.
- DB purpose (for this demo):
  - Store **experiment configuration only**:
    - Chosen agents.
    - Primary metric.
    - Additional metrics and their roles.
    - Planning parameters (alpha, power, MDE, allocation).
    - Experiment status (planned/running/completed).
  - **Do not** store per-day results; those are recomputed on the fly from `data/agent_data/`.

Suggested schema (logical):

- `experiments`
  - `id` INTEGER PRIMARY KEY
  - `name` TEXT
  - `created_at` TEXT  -- ISO timestamp
  - `status` TEXT CHECK(status IN ('planned', 'running', 'completed')) NOT NULL
  - `agent_a_id` TEXT
  - `agent_b_id` TEXT
  - `primary_metric` TEXT
  - `alpha` REAL
  - `power` REAL
  - `mde_relative` REAL  -- stored as fraction (e.g. 0.05 for 5%)
  - `allocation_ratio` REAL  -- treatment traffic share (e.g. 0.5)

- `experiment_metrics`
  - `id` INTEGER PRIMARY KEY
  - `experiment_id` INTEGER REFERENCES experiments(id) ON DELETE CASCADE
  - `name` TEXT  -- e.g. 'quality_ratio'
  - `role` TEXT CHECK(role IN ('primary', 'soft_monitoring', 'guardrail')) NOT NULL

Notes:
- No `experiment_snapshots` or per-day results table in this version.
- On the results screen, the app:
  - Reads experiment config from `experiments` and `experiment_metrics`.
  - Loads sessions from `data/agent_data/` for the requested date window.
  - Computes metrics and passes them to `ab_framework.analyze()`.

## Screen 1 — Starter Screen (`overview.html`)

Purpose: Landing page matching the provided screenshot; **all numbers and texts are hardcoded**, only the **“Run Experiment”** button is interactive.

Concrete starter HTML (to be used as `templates/overview.html`):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AI Agent A/B Experiments</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
<body class="starter-body">
  <div class="app-root">
    <!-- Top header -->
    <header class="app-header">
      <div class="app-header-left">
        <div class="app-logo-circle">A/B</div>
        <div class="app-title-group">
          <div class="app-title">AI Agent A/B Experiments</div>
          <div class="app-subtitle">Plan and monitor AI agent rollouts</div>
        </div>
      </div>
      <div class="app-header-right">
        <span class="env-pill">Demo</span>
        <div class="user-avatar">SC</div>
      </div>
    </header>

    <!-- Main two-column layout -->
    <main class="starter-main">
      <!-- LEFT COLUMN -->
      <section class="starter-left">
        <!-- Overview card -->
        <section class="starter-summary-card">
          <div class="summary-title">Experiment overview</div>
          <div class="summary-text">
            Compare your existing support agent with a new B agent focused on
            higher answer quality and faster resolution.
          </div>
          <ul class="summary-list">
            <li>Channel: Web chat</li>
            <li>Traffic split: 50 / 50</li>
            <li>Audience: All signed-in users</li>
          </ul>
        </section>

        <!-- Small metric tiles -->
        <section class="starter-metrics-strip">
          <div class="metric-tile metric-tile-green">
            <div class="metric-label">Quality</div>
            <div class="metric-main">4.2 / 5</div>
            <div class="metric-delta">+8% vs. baseline</div>
          </div>
          <div class="metric-tile metric-tile-green">
            <div class="metric-label">Resolution</div>
            <div class="metric-main">73%</div>
            <div class="metric-delta">+5 pts vs. baseline</div>
          </div>
          <div class="metric-tile metric-tile-neutral">
            <div class="metric-label">CSAT</div>
            <div class="metric-main">4.6 / 5</div>
            <div class="metric-delta">–0.2 pts</div>
          </div>
        </section>
      </section>

      <!-- RIGHT COLUMN -->
      <section class="starter-right">
        <section class="starter-hero-card">
          <div class="hero-header">
            <div class="hero-title">Plan your AI agent experiment</div>
            <div class="hero-subtitle">
              Use controlled A/B experiments to validate new prompts and models
              before rolling them out to all customers.
            </div>
          </div>

          <div class="hero-kpi-row">
            <div class="hero-kpi-card">
              <div class="hero-kpi-label">Primary metric</div>
              <div class="hero-kpi-main">Quality score</div>
              <div class="hero-kpi-sub">Target uplift: +8%</div>
            </div>
            <div class="hero-kpi-card">
              <div class="hero-kpi-label">Resolution rate</div>
              <div class="hero-kpi-main">73%</div>
              <div class="hero-kpi-sub">Goal: +5 pts</div>
            </div>
            <div class="hero-kpi-card">
              <div class="hero-kpi-label">Expected duration</div>
              <div class="hero-kpi-main">14 days</div>
              <div class="hero-kpi-sub">Based on recent traffic</div>
            </div>
          </div>

          <div class="hero-footer">
            <button class="btn btn-primary run-experiment-btn"
                    type="button"
                    onclick="window.location.href='{{ url_for('setup_experiment') }}'">
              Run Experiment
            </button>
            <button class="btn btn-ghost" type="button">
              View assumptions
            </button>
          </div>
        </section>
      </section>
    </main>
  </div>
</body>
</html>
```

CSS expectations (`static/css/styles.css`):

- `body` / `.starter-body` / `.app-root`:
  - Dark background (e.g. `#101020`), system font stack, light text.
- `.app-header`:
  - Horizontal bar with darker background, box-shadow, flex layout (space-between), small logo/title on left.
- `.starter-main`:
  - 2-column responsive grid or flex layout:
    - Left column ~30–35% width.
    - Right column ~65–70% width.
    - Gap between columns ~24px.
- `.starter-summary-card`, `.starter-hero-card`:
  - Card styles with slightly lighter background, rounded corners, subtle border or shadow, internal padding (16–24px).
- `.starter-metrics-strip` and `.metric-tile`:
  - Row of small cards with consistent width (e.g. 150–180px), condensed font, colored number text (green/red).
- `.run-experiment-btn`:
  - Prominent primary button:
    - Background with accent color (e.g. `#3b82f6` / `#0b5fff`), white text, rounded corners, hover/active states.

Behavior:

- Clicking **“Run Experiment”** performs a navigation to the Experiment Setup route (e.g. `/setup_experiment`).
- No other dynamic behavior or data calls on this screen.

## Screen 2 — Experiment Setup (`form.html` inside `configure_experiment.html`)

Reverse-engineered from the second screenshot; must maintain the same dark theme and panel layout as Screen 1.

Concrete structure for the setup screen content (inside `configure_experiment.html`'s right panel, e.g. `block content`):

```html
<!-- form.html (rendered inside configure_experiment.html) -->
<div class="experiment-setup-root">
  <!-- Top section: experiment header -->
  <section class="setup-header">
    <div class="setup-title-group">
      <h1 class="setup-title">Configure your A/B experiment</h1>
      <p class="setup-subtitle">
        Select a primary metric and additional metrics, then calculate the
        sample size and duration before starting the experiment.
      </p>
    </div>
  </section>

  <!-- Main grid: parameters + summary -->
  <section class="setup-main-grid">
    <!-- LEFT: parameter form -->
    <div class="setup-form-panel">
      <h2 class="panel-title">Experiment parameters</h2>

      <!-- Primary metric -->
      <div class="form-row">
        <label for="primary-metric" class="form-label">Primary metric</label>
        <select id="primary-metric" name="primary_metric" class="form-select">
          <option value="quality_ratio">Quality ratio</option>
          <option value="resolved_ratio">Resolved ratio</option>
        </select>
        <p class="form-helper">
          Used for sizing the experiment and primary decision-making.
        </p>
      </div>

      <!-- Additional metrics (multi-select) -->
      <div class="form-row">
        <label class="form-label">Additional metrics</label>
        <div class="multi-select-metrics">
          <!-- example checkboxes; in real app this is generated from config -->
          <label class="metric-checkbox">
            <input type="checkbox" name="metrics" value="quality_ratio" checked>
            <span>Quality ratio</span>
          </label>
          <label class="metric-checkbox">
            <input type="checkbox" name="metrics" value="resolved_ratio" checked>
            <span>Resolved ratio</span>
          </label>
          <label class="metric-checkbox">
            <input type="checkbox" name="metrics" value="csat">
            <span>CSAT</span>
          </label>
          <button type="button" class="btn-link select-all-metrics">
            Select all
          </button>
        </div>
        <p class="form-helper">
          These metrics are tracked as soft monitoring signals. Guardrail status
          can be configured but is not enforced in this demo.
        </p>
      </div>

      <!-- Role selector per metric (guardrail / soft monitoring) -->
      <div class="form-row">
        <label class="form-label">Metric roles</label>
        <div class="metric-role-row">
          <span class="metric-role-name">Quality ratio</span>
          <select name="role_quality_ratio" class="form-select-small">
            <option value="soft_monitoring" selected>Soft monitoring</option>
            <option value="guardrail">Guardrail (label only)</option>
          </select>
        </div>
        <div class="metric-role-row">
          <span class="metric-role-name">Resolved ratio</span>
          <select name="role_resolved_ratio" class="form-select-small">
            <option value="soft_monitoring" selected>Soft monitoring</option>
            <option value="guardrail">Guardrail (label only)</option>
          </select>
        </div>
      </div>

      <!-- Alpha / power / MDE -->
      <div class="form-row three-col">
        <div class="form-field">
          <label for="alpha" class="form-label">Alpha (significance level)</label>
          <input id="alpha" name="alpha" type="number" step="0.001" min="0" max="1"
                 class="form-input" value="0.05">
        </div>
        <div class="form-field">
          <label for="power" class="form-label">Power</label>
          <input id="power" name="power" type="number" step="0.01" min="0" max="1"
                 class="form-input" value="0.8">
        </div>
        <div class="form-field">
          <label for="mde" class="form-label">MDE (%)</label>
          <input id="mde" name="mde_percent" type="number" step="0.1" min="0"
                 class="form-input" value="5">
        </div>
      </div>

      <!-- Advanced options -->
      <details class="advanced-options">
        <summary>Advanced options</summary>
        <div class="form-row two-col">
          <div class="form-field">
            <label for="allocation" class="form-label">Traffic split (treatment)</label>
            <input id="allocation" name="allocation_ratio" type="number"
                   step="0.05" min="0.1" max="0.9"
                   class="form-input" value="0.5">
          </div>
          <div class="form-field">
            <label for="daily-volume" class="form-label">Daily traffic per variant (approx.)</label>
            <input id="daily-volume" name="daily_per_variant" type="number" min="0"
                   class="form-input" value="500">
          </div>
        </div>
      </details>

      <!-- Buttons -->
      <div class="setup-buttons-row">
        <button type="submit" name="action" value="plan"
                class="btn btn-primary">
          Calculate sample size
        </button>
        <button type="submit" name="action" value="start"
                class="btn btn-secondary"
                disabled>
          Run experiment
        </button>
      </div>

      <p class="form-helper">
        Use “Calculate sample size” to update the plan. Once you are satisfied
        with the sample size and duration, click “Run experiment” to start.
      </p>
    </div>

    <!-- RIGHT: planning summary -->
    <aside class="setup-summary-panel">
      <h2 class="panel-title">Plan summary</h2>

      <!-- Primary metric card -->
      <div class="plan-card primary-plan-card">
        <div class="plan-card-header">
          <span class="plan-badge">Primary metric</span>
          <span class="plan-metric-name">Quality ratio</span>
        </div>
        <div class="plan-card-body">
          <div class="plan-row">
            <span class="plan-label">Baseline</span>
            <span class="plan-value">0.72</span>
          </div>
          <div class="plan-row">
            <span class="plan-label">Target uplift</span>
            <span class="plan-value">+5%</span>
          </div>
          <div class="plan-row">
            <span class="plan-label">Required sample size</span>
            <span class="plan-value">18,000 per variant</span>
          </div>
          <div class="plan-row">
            <span class="plan-label">Estimated duration</span>
            <span class="plan-value">12 days</span>
          </div>
        </div>
        <div class="plan-card-footer">
          <span class="plan-footnote">
            Based on last 7 days of traffic and current alpha / power.
          </span>
        </div>
      </div>

      <!-- Additional metrics cards (soft monitoring) -->
      <div class="plan-card">
        <div class="plan-card-header">
          <span class="plan-badge plan-badge-soft">Soft monitoring</span>
          <span class="plan-metric-name">Resolved ratio</span>
        </div>
        <div class="plan-card-body">
          <div class="plan-row">
            <span class="plan-label">Baseline</span>
            <span class="plan-value">0.68</span>
          </div>
          <div class="plan-row">
            <span class="plan-label">Tracked, not used for sizing</span>
          </div>
        </div>
      </div>
    </aside>
  </section>
</div>
```

Key style expectations for Screen 2 (in `styles.css`):

- Maintain same **dark theme** and typography as Screen 1.
- `.experiment-setup-root`:
  - Full-width container with padding and vertical spacing.
- `.setup-main-grid`:
  - Two-column layout:
    - Left form panel (~60–65% width).
    - Right summary panel (~35–40% width).
    - Gap ~24–32px.
- `.setup-form-panel`, `.setup-summary-panel`:
  - Card-like containers with darker background, rounded corners, internal padding.
- Form controls (`.form-label`, `.form-input`, `.form-select`):
  - Styled to match Copilot / Fluent look: dark backgrounds, light borders, rounded corners, focus outline.
- Buttons:
  - `.btn.btn-primary` for **Calculate sample size** (accent color).
  - `.btn.btn-secondary` for **Run experiment**, which is disabled until plan exists (grayed-out style).
- Plan cards (`.plan-card`, `.primary-plan-card`):
  - Similar to metric cards in results screen, with headers, rows, and footnote text.
  - Primary plan card may have a subtle accent border.
 - Terminology consistency:
   - In setup views and plan cards, label the input as "Alpha (significance level)".
   - In results views and metric cards, label the computed statistic as "P value".

Behavior for Screen 2:

- On initial load:
  - Show default parameter values and static placeholder plan.
- When user clicks **Calculate sample size**:
  - POSTs to planning route with `action=plan`.
  - Backend recomputes plan using `ab_framework` and recent `data/agent_data` metrics; returns updated summary.
- When backend marks plan as valid:
  - **Run experiment** button is enabled (remove `disabled` attribute).
- When user clicks **Run experiment**:
  - POSTs with `action=start`, persists config to SQLite, and redirects to results screen with configuration persisted.

## Routes

- `GET /` → Render `overview.html` (Screen 1).
- `GET /setup_experiment` (or `/setup`) → Render `configure_experiment.html` with `form.html` embedded (Screen 2).
- `POST /setup_experiment` (or `/plan`) → Handle both:
  - `action=plan`:
    - Read parameters from form.
    - Use helpers based on `demos/agent_sessions` to:
      - Load last N days from `data/agent_data/`.
      - Compute baselines and daily volume.
    - Call `ab_framework` planning helper (e.g. `sample_size_proportion`) with `(baseline_rate, mde_relative, alpha, power)`.
    - Re-render Screen 2 with updated plan summary.
  - `action=start`:
    - Persist experiment configuration to SQLite (`experiments` + `experiment_metrics`).
    - Redirect to `/results`.

- `GET /results` (+ optional `date` query) → Render results screen (Screen 3) using `analyze()` and today picker.
  - On each request:
    - Read experiment config from SQLite.
    - Determine “today” from query or default.
    - Load appropriate JSONs from `data/agent_data/` for that date/window.
    - Compute metrics using shared logic (from `demos/agent_sessions`).
    - Build an `ABTest` and call `analyze()` for primary and additional metrics.
    - Render metric cards with the computed **P value** and a clear decision summary (compare p-value vs alpha), alongside red/green status.

## Backend Usage

- Use only the local `ab_framework` package for planning and analysis logic.
- Planning:
  - Primary metric (`quality_ratio`, `resolved_ratio`, etc.) treated as `proportion`.
  - Baseline rate and daily volume estimated from recent `data/agent_data/` via helper functions.
  - A proportion sample-size helper in `ab_framework` (e.g. `sample_size_proportion`) is used to compute required sample size:
    - Inputs: `(baseline_rate, mde_relative, alpha, power)`.
- Additional metrics:
  - Also treated as `proportion` metrics in this demo.
  - Their baselines can be computed and displayed, but the main planning focus is the primary metric.
- Analysis:
  - For Screen 3, use `ab_framework` `ABTest` + `analyze()`:
    - Construct or reuse an `ABTest` with the configured agents and metrics.
    - For each selected metric (primary + additional), call `analyze()` (soft monitoring mode, no multiple-comparison correction initially).
    - Map `analyze()` results to:
      - Effect estimate / lift.
      - **P value** (computed) and decision summary.
      - Red/green status for each metric card.
    - Decision rule: reject H0 when `p-value < alpha`; show alpha in a footnote or tooltip for transparency.

## UI & UX (Screens 2 and 3)

- Top bar in `configure_experiment.html` (dark header, app title, date control on results).
- Left agents panel common for setup and results:
  - Agents (Original, B) with model name and instructions, styled as cards/list with hover/selected state.
- Right panel:
  - Screen 2: form + planning cards, with **Calculate sample size** and **Run experiment**.
  - Screen 3:
    - Today picker in top bar.
    - Metric cards per metric with:
      - Metric name and role (primary, soft monitoring, guardrail label).
      - Control vs treatment values.
      - Lift or degradation.
      - Clear red/green indication.

## Validation

- Primary metric:
  - Must be one of the configured options (at least `quality_ratio`, `resolved_ratio`).
- Additional metrics:
  - Each selected metric must be from the same configured options.
  - Each has a valid role: `guardrail` or `soft_monitoring`.
- Planning params:
  - `alpha, power ∈ (0,1)`.
  - `mde_percent > 0` (percentage; converted to `mde_relative = mde_percent / 100`).
  - `allocation_ratio ∈ (0,1)`; default 0.5 if omitted.
- Proportion metrics:
  - `baseline_rate ∈ [0,1]` (estimated from `data/agent_data/`; not user-entered directly).
- Optional:
  - `daily_per_variant > 0`.
- Return clear inline errors and keep entered values on error.

## Security & Ops

- Dev server only: bind `127.0.0.1`, default port 5000.
- No file uploads in this demo.
- Sanitize and validate numeric inputs; reject malformed requests.

## Dependencies

- Add `Flask` to `requirements.txt` (Flask brings Jinja2).
- Use existing `pandas`, `numpy`, `scipy`, `owl-ab-test`, and local `ab_framework`.

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

1) Implement `overview.html` using the concrete HTML above and hook **Run Experiment** → `/setup_experiment`.
2) Implement `configure_experiment.html` + `form.html` for Screen 2 (agents sidebar, primary + multi-select metrics, planning parameters, Calculate sample size / Run experiment buttons).
3) Implement planning route using builtin `sqlite3` for config and `ab_framework` proportion sample-size helper plus metrics computed from `data/agent_data`.
4) Implement `results.html` + results routes for Screen 3 with today picker and per-metric cards using `analyze()` and metrics computed on the fly from `data/agent_data`.
5) Ensure CSS closely mimics the provided screenshots.
6) Optional: refine guardrail vs soft monitoring behavior beyond labeling; consider adding persisted snapshots if needed later.

## Acceptance Criteria

- Starter screen:
  - Matches screenshot visually using `overview.html` and CSS.
  - All values static, only “Run Experiment” navigates to setup screen.
- Experiment setup:
  - User sees two agents with model name and instructions.
  - User selects a primary metric and additional metrics (multi-select + roles).
  - User configures alpha, power, MDE% and runs “Calculate sample size” to see sample size and duration.
  - User can click “Run experiment” to proceed to results screen; config is persisted in SQLite.
- Experiment results:
  - Today picker controls which date’s results are shown.
  - For each date, metrics are computed from `data/agent_data` and passed through `ab_framework.analyze()`.
  - Cards for primary and each additional metric show control/treatment values, lift/degradation, and red/green indication.
- All planning and analysis use only `ab_framework` under the hood, with builtin `sqlite3` for configuration and static JSON under `data/agent_data/` as the system data source.
