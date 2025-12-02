import os
import numpy as np

from ab_framework import ABTest

from demos.agent_sessions.agent_sessions_loader import load_agent_sessions, summarize_agent_sessions


def main() -> None:
    # Ensure we run from repo root for consistent relative paths
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.chdir(repo_root)

    print("=" * 70)
    print("AGENT SESSIONS DEMO - AI ANSWER QUALITY RATE OVER TIME")
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
    print("PHASE 0: A/A WARMUP (QUALITY RATE)")
    print("First 7 days: sanity-check metric collection and experiment infra")
    print("-" * 70)

    df_aa = df[df["day"].isin(aa_days)].copy()
    if df_aa.empty:
        print("Not enough days for A/A warmup; skipping straight to A/B simulation.")
    else:
        df_aa["user_id"] = df_aa["row_id"]
        df_aa["variant"] = np.where(df_aa["row_id"] % 2 == 0, "A", "B")

        test_aa = ABTest(
            name="agent_sessions_quality_AA",
            data=df_aa,
            variant_col="variant",
            unit_id="user_id",
        )

        @test_aa.metric(metric_type="proportion")
        def quality_rate(data):
            return data.groupby("user_id")["quality"].max()

        aa_results = test_aa.analyze(["quality_rate"], run_srm_check=True)
        print(aa_results.summary())
        print("\nA/A interpretation:")
        print(
            "We expect no significant difference between A and B here; "
            "this checks that the quality metric and randomization behave as expected."
        )

    if not ab_days:
        print("\nNo days left for A/B period; demo complete.")
        return

    print("\n" + "-" * 70)
    print("PHASE 1: A/B SIMULATION (QUALITY RATE)")
    print("Using remaining days as if a new model is rolled out")
    print("-" * 70)

    df_ab = df[df["day"].isin(ab_days)].copy()
    if df_ab.empty:
        print("No data available for A/B phase.")
        return

    df_ab["user_id"] = df_ab["row_id"]
    rng = np.random.default_rng(123)
    df_ab["variant"] = np.where(rng.random(len(df_ab)) < 0.5, "A", "B")

    # Day-by-day cumulative monitoring
    print("\nSequential monitoring: cumulative quality rate up to each day")
    for day in sorted(ab_days):
        current = df_ab[df_ab["day"] <= day].copy()
        if current.empty:
            continue

        test = ABTest(
            name=f"agent_quality_rate_until_{day.isoformat()}",
            data=current,
            variant_col="variant",
            unit_id="user_id",
        )

        @test.metric(metric_type="proportion")
        def quality_rate(data):
            return data.groupby("user_id")["quality"].max()

        results = test.analyze(["quality_rate"], run_srm_check=True)

        print("\n" + "=" * 70)
        print(f"DAY {day.isoformat()} - CUMULATIVE QUALITY RATE CHECK")
        print("=" * 70)
        print(results.summary())

    print("\nDemo complete: AI answer quality rate monitored over time.")


if __name__ == "__main__":
    main()
