import os
import numpy as np

from ab_framework import ABTest

from demos.agent_sessions.agent_sessions_loader import load_agent_sessions, summarize_agent_sessions


def main() -> None:
    # Ensure we run from repo root for relative paths
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.chdir(repo_root)

    print("=" * 70)
    print("AGENT SESSIONS DEMO - RESOLVED SESSION RATE OVER TIME")
    print("Using JSON logs as if they arrive day by day")
    print("=" * 70)

    df = load_agent_sessions()
    summarize_agent_sessions(df)

    if df.empty:
        return

    # Note: we do not run SRM across days here, because
    # real-world traffic can vary a lot by weekday/weekend.

    # Sort days and define A/A warmup vs A/B period
    days = sorted(df["day"].unique())
    aa_days = days[:7]
    ab_days = days[7:]

    print("\n" + "-" * 70)
    print("PHASE 0: A/A WARMUP (RESOLVED RATE)")
    print("First 7 days: sanity-check metric collection and experiment infra")
    print("-" * 70)

    df_aa = df[df["day"].isin(aa_days)].copy()
    if df_aa.empty:
        print("Not enough days for A/A warmup; skipping straight to A/B simulation.")
    else:
        # One session per (implicit) conversation; use row_id as conversation_id
        df_aa["conversation_id"] = df_aa["row_id"]
        df_aa["variant"] = np.where(df_aa["conversation_id"] % 2 == 0, "A", "B")

        test_aa = ABTest(
            name="agent_sessions_resolved_AA",
            data=df_aa,
            variant_col="variant",
            unit_id="conversation_id",
        )

        @test_aa.metric(metric_type="proportion")
        def resolved_rate(data):
            # One row per conversation, so this is effectively per-session
            return data.groupby("conversation_id")["resolved"].max()

        # Defensive check: ensure both variants have data for this metric
        metric_values = resolved_rate(df_aa)
        metric_df = metric_values.reset_index()
        metric_df.columns = ["conversation_id", "metric_value"]
        variants = df_aa[["conversation_id", "variant"]].drop_duplicates()
        joined = metric_df.merge(variants, on="conversation_id", how="left")
        counts = joined["variant"].value_counts().to_dict()

        if counts.get("A", 0) == 0 or counts.get("B", 0) == 0:
            print(
                "Not enough conversations in both variants for resolved_rate in A/A; "
                "skipping A/A analysis."
            )
        else:
            aa_results = test_aa.analyze(["resolved_rate"], run_srm_check=True)
            print(aa_results.summary())
        print("\nA/A interpretation:")
        print(
            "We expect no significant difference between A and B here; "
            "this checks that the resolved metric and randomization behave as expected."
        )

    if not ab_days:
        print("\nNo days left for A/B period; demo complete.")
        return

    print("\n" + "-" * 70)
    print("PHASE 1: A/B SIMULATION (RESOLVED RATE)")
    print("Using remaining days as if a new resolution policy is rolled out")
    print("-" * 70)

    df_ab = df[df["day"].isin(ab_days)].copy()
    if df_ab.empty:
        print("No data available for A/B phase.")
        return

    df_ab["conversation_id"] = df_ab["row_id"]
    rng = np.random.default_rng(123)
    df_ab["variant"] = np.where(rng.random(len(df_ab)) < 0.5, "A", "B")

    # Day-by-day cumulative monitoring
    print("\nSequential monitoring: cumulative resolved rate up to each day")
    for day in sorted(ab_days):
        current = df_ab[df_ab["day"] <= day].copy()
        if current.empty:
            continue

        test = ABTest(
            name=f"agent_resolved_rate_until_{day.isoformat()}",
            data=current,
            variant_col="variant",
            unit_id="conversation_id",
        )

        @test.metric(metric_type="proportion")
        def resolved_rate(data):
            return data.groupby("conversation_id")["resolved"].max()

        # Skip slices where one variant has no conversations
        metric_values = resolved_rate(current)
        metric_df = metric_values.reset_index()
        metric_df.columns = ["conversation_id", "metric_value"]
        variants = current[["conversation_id", "variant"]].drop_duplicates()
        joined = metric_df.merge(variants, on="conversation_id", how="left")
        counts = joined["variant"].value_counts().to_dict()

        if counts.get("A", 0) == 0 or counts.get("B", 0) == 0:
            print(
                f"\nDAY {day.isoformat()} - Skipping resolved_rate: "
                "one of the variants has no conversations yet."
            )
            continue

        results = test.analyze(["resolved_rate"], run_srm_check=True)

        print("\n" + "=" * 70)
        print(f"DAY {day.isoformat()} - CUMULATIVE RESOLVED RATE CHECK")
        print("=" * 70)
        print(results.summary())

    print("\nDemo complete: resolved session rate monitored over time.")


if __name__ == "__main__":
    main()
