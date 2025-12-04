import json
import os
import glob
import hashlib
from datetime import date
from typing import Optional

import pandas as pd


def _infer_day_from_filename(path: str) -> date:
    """Infer a date from a filename like 'Sessions 2025_11_28.json'.

    Strictly enforces the expected pattern; raises on malformed names.
    """
    name = os.path.basename(path)
    # Expect pattern: Sessions 2025_MM_DD.json
    base = name.replace("Sessions ", "").replace(".json", "")
    year_str, month_str, day_str = base.split("_")
    year = int(year_str)
    month = int(month_str)
    day_num = int(day_str)
    return date(year, month, day_num)


def _create_deterministic_id(day: date, file_name: str, local_index: int) -> str:
    """Create a deterministic ID from day, file, and index.
    
    This ensures that the same session always gets the same ID across runs,
    making A/B variant assignment reproducible.
    """
    # Use SHA256 hash for deterministic but unpredictable IDs
    content = f"{day.isoformat()}|{file_name}|{local_index}"
    hash_digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
    # Return first 16 chars for readability (64 bits of entropy)
    return hash_digest[:16]


def load_agent_sessions(data_dir: Optional[str] = None) -> pd.DataFrame:
    """Load all agent session JSON files into a normalized DataFrame.

    Expected file pattern: 'Sessions MM_DD.json' under data/agent_data.
    Each file is a JSON array of objects with a top-level 'Value' field.
    
    Key features:
    - Every file gets a timestamp entry (even if empty)
    - Deterministic session_id and conversation_id ensure reproducible A/B assignment
    - session_id = conversation_id (one session per conversation assumption)
    """
    # Resolve default data directory relative to repo root
    if data_dir is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        data_dir = os.path.join(repo_root, "data", "agent_data")

    pattern = os.path.join(data_dir, "Sessions *.json")
    paths = sorted(glob.glob(pattern))

    # Track all days present (including empty files)
    all_days = []
    rows = []
    
    for path in paths:
        day_val = _infer_day_from_filename(path)
        file_name = os.path.basename(path)
        all_days.append(day_val)
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                items = json.load(f)
        except json.JSONDecodeError:
            # Empty or malformed file - still track the day
            continue
        except Exception:
            # File doesn't exist or other error - skip
            continue

        for idx, item in enumerate(items):
            value = item.get("Value") or {}
            rq = value.get("responseQuality") or {}

            session_outcome = value.get("sessionOutcome") or "Unknown"
            is_quality_answer = bool(rq.get("isQualityAnswer", False))
            bad_root_cause = rq.get("badQualityPrimaryRootCause")

            resolved = 1 if session_outcome == "ResolvedImplied" else 0
            quality = 1 if is_quality_answer else 0
            
            # Create deterministic IDs
            session_id = _create_deterministic_id(day_val, file_name, idx)
            conversation_id = session_id  # One session per conversation

            rows.append(
                {
                    "day": day_val,
                    "file_name": file_name,
                    "local_index": idx,
                    "session_id": session_id,
                    "conversation_id": conversation_id,
                    "sessionOutcome": session_outcome,
                    "isQualityAnswer": is_quality_answer,
                    "badQualityPrimaryRootCause": bad_root_cause,
                    "resolved": resolved,
                    "quality": quality,
                }
            )

    if not rows:
        # Return empty DataFrame with all expected columns
        return pd.DataFrame(
            columns=[
                "day",
                "file_name",
                "local_index",
                "session_id",
                "conversation_id",
                "row_id",
                "sessionOutcome",
                "isQualityAnswer",
                "badQualityPrimaryRootCause",
                "resolved",
                "quality",
            ]
        )

    df = pd.DataFrame(rows)
    
    # Create row_id for backward compatibility (sequential index)
    df = df.reset_index(drop=True)
    df["row_id"] = df.index.astype(int)
    
    # Ensure all days are represented (even those with no data)
    # This helps with timeline visualization and gap detection
    if all_days:
        unique_days = sorted(set(all_days))
        df.attrs['all_days'] = unique_days
        df.attrs['days_with_data'] = sorted(df['day'].unique())
    
    return df


def summarize_agent_sessions(df: pd.DataFrame) -> None:
    """Print high-level statistics for the loaded agent-session data."""
    if df.empty:
        print("# Agent Session Data Overview")
        print("No agent session data found.")
        return

    # Check for missing days
    all_days = df.attrs.get('all_days', [])
    days_with_data = df.attrs.get('days_with_data', [])
    days_present = len(days_with_data)
    total_files = len(all_days)
    missing_days = set(all_days) - set(days_with_data)
    
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
    print(f"- Total files found: {total_files}")
    print(f"- Days with data: {days_present}")
    if missing_days:
        print(f"- Days with no sessions (empty files): {len(missing_days)}")
        if len(missing_days) <= 5:
            print(f"  → {', '.join(d.isoformat() for d in sorted(missing_days))}")
    print(f"- Total sessions: {total_sessions}")
    print(f"- Average sessions per day: {avg_sessions_per_day:.1f}")
    print(f"- Min sessions per day: {min_sessions_per_day}")
    print(f"- Max sessions per day: {max_sessions_per_day}")
    print(f"- Median sessions per day: {median_sessions_per_day:.1f}")
    print(f"- Overall resolved rate: {overall_resolved_rate:.3%}")
    print(f"- Overall AI quality rate: {overall_quality_rate:.3%}")
    print(f"- Resolved & high-quality rate: {resolved_and_quality_rate:.3%}")
    print(f"- Groundedness share among bad-quality answers: {grounded_share:.3%}")

    # Show first few days with their counts
    print("\n## Sessions per day (first 5 days with data)")
    for d, n in sessions_per_day.sort_index().head(5).items():
        print(f"- {d.isoformat()}: {n} sessions")
