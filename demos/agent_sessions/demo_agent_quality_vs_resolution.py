import os
import numpy as np

from ab_framework import ABTest

from demos.agent_sessions.agent_sessions_loader import load_agent_sessions, summarize_agent_sessions


def main() -> None:
    # Ensure we run from repo root for consistent relative paths
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.chdir(repo_root)

    print("=" * 70)
    print("AGENT SESSIONS DEMO - QUALITY UPLIFT WITH RESOLUTION GUARDRAIL")
    print("Primary metric: AI answer quality rate")
    print("Guardrail metric: session resolved rate")
    print("=" * 70)

    df = load_agent_sessions()
    summarize_agent_sessions(df)

    if df.empty:
        return

    # Quick SRM-style check on the raw data distribution across days
    # Note: we do not run SRM across days here, because
    # real-world traffic can vary a lot by weekday/weekend.

    # Sort days and define A/A warmup vs A/B period
    days = sorted(df["day"].unique())
    aa_days = days[:7]
    ab_days = days[7:]

    print("\n" + "-" * 70)
    print("PHASE 0: A/A WARMUP (QUALITY + RESOLUTION)")
    print("First 7 days: verify both metrics before comparing models")
    print("-" * 70)

    df_aa = df[df["day"].isin(aa_days)].copy()
    if df_aa.empty:
        print("Not enough days for A/A warmup; skipping straight to A/B simulation.")
    else:
        df_aa["user_id"] = df_aa["row_id"]
        df_aa["variant"] = np.where(df_aa["row_id"] % 2 == 0, "A", "B")

        test_aa = ABTest(
            name="agent_sessions_quality_vs_resolution_AA",
            data=df_aa,
            variant_col="variant",
            unit_id="user_id",
        )

        @test_aa.metric(metric_type="proportion")
        def quality_rate(data):
            return data.groupby("user_id")["quality"].max()

        @test_aa.metric(metric_type="proportion")
        def resolved_rate(data):
            return data.groupby("user_id")["resolved"].max()

        aa_results = test_aa.analyze(["quality_rate", "resolved_rate"], run_srm_check=True)
        print(aa_results.summary())
        print("\nA/A interpretation:")
        print(
            "We expect no significant differences here on either metric; "
            "this checks the joint behavior of quality and resolution before rollout."
        )

    if not ab_days:
        print("\nNo days left for A/B period; demo complete.")
        return

    print("\n" + "-" * 70)
    print("PHASE 1: A/B SIMULATION (QUALITY PRIMARY, RESOLUTION GUARDRAIL)")
    print("Using remaining days as if a higher-quality model is rolled out")
    print("-" * 70)

    df_ab = df[df["day"].isin(ab_days)].copy()
    if df_ab.empty:
        print("No data available for A/B phase.")
        return

    df_ab["user_id"] = df_ab["row_id"]
    rng = np.random.default_rng(123)
    df_ab["variant"] = np.where(rng.random(len(df_ab)) < 0.5, "A", "B")

    # Day-by-day cumulative monitoring
    print("\nSequential monitoring: quality vs resolution up to each day")
    for day in sorted(ab_days):
        current = df_ab[df_ab["day"] <= day].copy()
        if current.empty:
            continue

        test = ABTest(
            name=f"agent_quality_vs_resolution_until_{day.isoformat()}",
            data=current,
            variant_col="variant",
            unit_id="user_id",
        )

        @test.metric(metric_type="proportion")
        def quality_rate(data):
            return data.groupby("user_id")["quality"].max()

        @test.metric(metric_type="proportion")
        def resolved_rate(data):
            return data.groupby("user_id")["resolved"].max()

        results = test.analyze(["quality_rate", "resolved_rate"], run_srm_check=True)

        print("\n" + "=" * 70)
        print(f"DAY {day.isoformat()} - QUALITY (PRIMARY) VS RESOLUTION (GUARDRAIL)")
        print("=" * 70)
        print(results.summary())
        print("\nDecision heuristics:")
        print("- Ship if quality_rate is significantly higher in B vs A.")
        print("- Ensure resolved_rate is not significantly worse in B.")

    print("\nDemo complete: tradeoff between quality uplift and resolution safeguarded.")


if __name__ == "__main__":
    main()
