import os
from datetime import datetime, timedelta, date
from typing import Tuple, Optional

import pandas as pd
import numpy as np

from ab_framework import ABTest

# Reuse the existing demos loader for agent sessions
from demos.agent_sessions.agent_sessions_loader import load_agent_sessions


def _metric_column(primary_metric: str) -> str:
    """Map a metric name to the corresponding boolean column in the sessions DF."""
    mapping = {
        "quality_ratio": "quality",
        "resolved_ratio": "resolved",
        # Users may track combined metric; keep simple mapping for now
        "resolved_and_quality_ratio": None,
    }
    return mapping.get(primary_metric, "quality")


def _slice_recent_days(df: pd.DataFrame, days: int = 7, end_day: Optional[date] = None) -> pd.DataFrame:
    if df.empty:
        return df
    data_min = df["day"].min()
    data_max = df["day"].max()
    if end_day is None:
        max_day = data_max
    else:
        # clamp to data range
        if end_day > data_max:
            max_day = data_max
        else:
            max_day = end_day
    # Window of `days` ending at max_day
    start_day = max_day - timedelta(days=days - 1)
    if start_day < data_min:
        start_day = data_min
    return df[(df["day"] >= start_day) & (df["day"] <= max_day)].copy()


def get_recent_baseline_and_volume(primary_metric: str, days: int = 7) -> Tuple[float, float]:
    """Align baseline + traffic with the demo's A/A warmup.

    - Use first `days` worth of data as A/A warmup
    - Deterministically split users 50/50 into A/B via conversation_id hash
    - Build an A/A ABTest and take the **control** arm's value for the
      primary metric as the baseline (like demo_agent_quality_vs_resolution)
    - Compute avg daily sessions from the A/A window and derive
      daily_per_variant = avg_daily_sessions * 0.5
    """
    df = load_agent_sessions()

    # Sort by day and take the first `days` days as the A/A warmup window
    all_days = sorted(df["day"].unique())
    aa_days = all_days[:days]
    df_aa = df[df["day"].isin(aa_days)].copy()
    if df_aa.empty:
        return 0.5, 100.0

    # Deterministic 50/50 split by conversation_id, like demo
    df_aa["user_id"] = df_aa["conversation_id"]
    h = pd.util.hash_pandas_object(df_aa["conversation_id"], index=False).astype(np.int64)
    df_aa["variant"] = np.where((h % 2) == 0, "A", "B")

    # Build an A/A test and attach metrics; primary is quality_ratio
    test_aa = ABTest(
        name="agent_sessions_quality_vs_resolution_AA_webapp",
        variants=["A", "B"],
    )

    observed_counts = df_aa.groupby("variant")["user_id"].nunique().to_dict()

    @test_aa.metric(metric_type="proportion", is_primary=True)
    def quality_ratio(data):
        user_level = data.groupby(["variant", "user_id"])["quality"].max()
        out = {}
        for variant in ["A", "B"]:
            v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
            out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
        return out

    @test_aa.metric(metric_type="proportion")
    def resolved_ratio(data):
        user_level = data.groupby(["variant", "user_id"])["resolved"].max()
        out = {}
        for variant in ["A", "B"]:
            v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
            out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
        return out

    aa_results = test_aa.analyze(
        df_aa,
        run_srm_check=True,
        observed_counts=observed_counts,
        correction=None,
    )

    # Take the control arm's value for the requested primary metric
    metric_key = primary_metric if primary_metric in aa_results.metric_results else "quality_ratio"
    metric_info = aa_results.metric_results.get(metric_key, {})
    baseline_rate = float(metric_info.get("control_value", 0.5))

    # Average daily sessions in the A/A window
    sessions_per_day = df_aa.groupby("day").size()
    avg_daily_sessions = float(sessions_per_day.mean()) if not sessions_per_day.empty else 200.0

    daily_per_variant = max(1.0, avg_daily_sessions * 0.5)

    print("\n" + "-" * 70)
    print("WEBAPP A/A BASELINE (aligned with demo)")
    print("Days in A/A window:", [d.isoformat() for d in aa_days])
    print(f"Primary metric: {metric_key}")
    print(f"Baseline (control) from A/A: {baseline_rate:.3%}")
    print(f"Avg daily sessions (A/A): {avg_daily_sessions:.1f}")
    print(f"Daily per variant (approx.): {daily_per_variant:.1f}")

    return baseline_rate, daily_per_variant


def get_recent_user_variant_df(days: int = 7, end_day: Optional[date] = None) -> pd.DataFrame:
    """Return a minimal DataFrame with `conversation_id` and deterministic `variant`.

    - Loads recent N days of sessions
    - Uses `conversation_id` as the unit for assignment
    - Assigns 50/50 split using stable hash of `conversation_id`
    """
    df = load_agent_sessions()

    # Determine warmup (A/A) window: first 7 distinct days in the data
    all_days = sorted(df["day"].unique())
    if len(all_days) < 7:
        aa_end = all_days[-1]
    else:
        aa_end = all_days[6]  # index 6 = 7th day

    # If end_day is before or equal to warmup end, there is no experiment window yet
    if end_day is not None and end_day <= aa_end:
        return pd.DataFrame({"conversation_id": [], "variant": []})

    # For experiment analysis, start from the warmup end day (aa_end) and go forward
    # up to the requested end_day (or latest day in data if None).
    if end_day is None:
        max_day = df["day"].max()
    else:
        max_day = min(end_day, df["day"].max())

    recent = df[(df["day"] >= aa_end) & (df["day"] <= max_day)].copy()
    if recent.empty:
        return pd.DataFrame({"conversation_id": [], "variant": []})

    recent = recent.copy()
    h = pd.util.hash_pandas_object(recent["conversation_id"], index=False).astype(np.int64)
    recent["variant"] = np.where((h % 2) == 0, "A", "B")

    mapping = recent[["conversation_id", "variant"]].drop_duplicates()

    # Lightweight debug logging to understand the window and mapping size
    try:
        window_days = sorted(recent["day"].unique())
        print("\n" + "-" * 70)
        print("USER/VARIANT MAPPING WINDOW")
        print(f"end_day={end_day}")
        print("Days in window:", [d.isoformat() for d in window_days])
        print("Unique conversations in mapping:", len(mapping))
    except Exception:
        pass

    return mapping
