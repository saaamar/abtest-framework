import json
import os
import glob
from datetime import date
from typing import Optional

import pandas as pd


def _infer_day_from_filename(path: str, default_year: int = 2024) -> date:
    """Infer a date from a filename like 'Sessions 11_28.json'."""
    name = os.path.basename(path)
    # Expect pattern: Sessions MM_DD.json
    try:
        base = name.replace("Sessions ", "").replace(".json", "")
        month_str, day_str = base.split("_")
        month = int(month_str)
        day_num = int(day_str)
        return date(default_year, month, day_num)
    except Exception:
        # Fallback: treat entire month as 1st if parsing fails
        return date(default_year, 1, 1)


def load_agent_sessions(data_dir: Optional[str] = None) -> pd.DataFrame:
    """Load all agent session JSON files into a normalized DataFrame.

    Expected file pattern: 'Sessions MM_DD.json' under data/agent_data.
    Each file is a JSON array of objects with a top-level 'Value' field.
    """
    # Resolve default data directory relative to repo root
    if data_dir is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        data_dir = os.path.join(repo_root, "data", "agent_data")

    pattern = os.path.join(data_dir, "Sessions *.json")
    paths = sorted(glob.glob(pattern))

    rows = []
    for path in paths:
        day_val = _infer_day_from_filename(path)
        file_name = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                items = json.load(f)
        except json.JSONDecodeError:
            # Skip malformed files but keep going
            continue

        for idx, item in enumerate(items):
            value = item.get("Value") or {}
            rq = value.get("responseQuality") or {}

            session_outcome = value.get("sessionOutcome") or "Unknown"
            is_quality_answer = bool(rq.get("isQualityAnswer", False))
            bad_root_cause = rq.get("badQualityPrimaryRootCause")

            resolved = 1 if session_outcome == "ResolvedImplied" else 0
            quality = 1 if is_quality_answer else 0

            rows.append(
                {
                    "day": day_val,
                    "file_name": file_name,
                    "local_index": idx,
                    "sessionOutcome": session_outcome,
                    "isQualityAnswer": is_quality_answer,
                    "badQualityPrimaryRootCause": bad_root_cause,
                    "resolved": resolved,
                    "quality": quality,
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "day",
                "file_name",
                "row_id",
                "sessionOutcome",
                "isQualityAnswer",
                "badQualityPrimaryRootCause",
                "resolved",
                "quality",
            ]
        )

    df = pd.DataFrame(rows)
    # Create a global row_id / user_id surrogate
    df = df.reset_index(drop=True)
    df["row_id"] = df.index.astype(int)
    return df


def summarize_agent_sessions(df: pd.DataFrame) -> None:
    """Print high-level statistics for the loaded agent-session data."""
    if df.empty:
        print("# Agent Session Data Overview")
        print("No agent session data found.")
        return

    days_present = df["day"].nunique()
    total_sessions = len(df)

    sessions_per_day = df.groupby("day").size()
    avg_sessions_per_day = sessions_per_day.mean()
    min_sessions_per_day = sessions_per_day.min()
    max_sessions_per_day = sessions_per_day.max()
    median_sessions_per_day = sessions_per_day.median()

    overall_resolved_rate = df["resolved"].mean()
    overall_quality_rate = df["quality"].mean()
    resolved_and_quality_rate = ((df["resolved"] == 1) & (df["quality"] == 1)).mean()

    bad = df[df["quality"] == 0]
    if not bad.empty:
        grounded_mask = bad["badQualityPrimaryRootCause"] == "Groundedness"
        grounded_share = grounded_mask.mean()
    else:
        grounded_share = 0.0

    print("# Agent Session Data Overview")
    print(f"- Days present: {days_present}")
    print(f"- Total sessions: {total_sessions}")
    print(f"- Average sessions per day: {avg_sessions_per_day:.1f}")
    print(f"- Min sessions per day: {min_sessions_per_day}")
    print(f"- Max sessions per day: {max_sessions_per_day}")
    print(f"- Median sessions per day: {median_sessions_per_day:.1f}")
    print(f"- Overall resolved rate: {overall_resolved_rate:.3%}")
    print(f"- Overall AI quality rate: {overall_quality_rate:.3%}")
    print(f"- Resolved & high-quality rate: {resolved_and_quality_rate:.3%}")
    print(f"- Groundedness share among bad-quality answers: {grounded_share:.3%}")

    # Optionally show the first few days with their counts for context
    print("\n## Sessions per day (first 5 days)")
    for d, n in sessions_per_day.sort_index().head(5).items():
        print(f"- {d.isoformat()}: {n} sessions")
