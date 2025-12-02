# Agent Sessions Demos

This folder contains demos that use the A/B testing framework on JSON agent-session logs under `data/agent_data` (`Sessions 11_*.json`). Each demo replays a month of data as if it were arriving day by day.

All scripts rely on `load_agent_sessions` and `summarize_agent_sessions` from `agent_sessions_loader.py` to normalize the JSON into a tabular format with two key per-session metrics:

- `resolved`: 1 if `sessionOutcome == "ResolvedImplied"`, else 0.
- `quality`: 1 if `responseQuality.isQualityAnswer` is true, else 0.

## Demos

### 1. Resolved-rate over time

Script: `demo_agent_resolved_rate.py`

- **Goal**: Monitor the session resolution rate as a new experience rolls out.
- **Phase 0 (A/A warmup)**: First 7 distinct days are split into variants `A` and `B` by even/odd `row_id`. The `resolved_rate` metric (proportion of users with any resolved session) is compared between A and B; we expect no significant difference.
- **Phase 1 (A/B)**: Remaining days are treated as if a new policy is rolled out. Each row is assigned 50/50 to `A`/`B` using a fixed RNG seed, and the demo prints cumulative resolved-rate results up to each A/B day, including an SRM check.

Run from the repo root:

```powershell
python -m demos.agent_sessions.demo_agent_resolved_rate
```

### 2. AI answer quality rate over time

Script: `demo_agent_quality_rate.py`

- **Goal**: Track the rate of high-quality AI answers over time.
- **Phase 0 (A/A warmup)**: Same structure as the resolved demo, but using `quality_rate` (proportion of users with any `quality == 1` session).
- **Phase 1 (A/B)**: Remaining days simulate a new model rollout. The demo prints cumulative quality-rate results per day with SRM checks.

Run from the repo root:

```powershell
python -m demos.agent_sessions.demo_agent_quality_rate
```

### 3. Quality uplift with resolution guardrail

Script: `demo_agent_quality_vs_resolution.py`

- **Goal**: Illustrate treating answer quality as a primary metric while safeguarding session resolution as a guardrail.
- **Phase 0 (A/A warmup)**: First 7 days are used to validate both `quality_rate` and `resolved_rate` behave as expected under randomization.
- **Phase 1 (A/B)**: Remaining days simulate a higher-quality model rollout. For each day cumulatively:
  - The demo analyzes both `quality_rate` (primary) and `resolved_rate` (guardrail).
  - The printed summary includes heuristic guidance:
    - Ship if `quality_rate` is significantly higher in B vs A.
    - Ensure `resolved_rate` is not significantly worse in B.

Run from the repo root:

```powershell
python -m demos.agent_sessions.demo_agent_quality_vs_resolution
```

## Notes

- All demos use `row_id` as the user identifier (`user_id`) and proportion metrics grouped per user.
- The apparent "day-by-day" behavior is a replay over static JSON logs; no real-time ingestion is required.
