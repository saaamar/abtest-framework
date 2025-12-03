import os
import numpy as np

from ab_framework import ABTest

# Configuration constants
DEFAULT_WARMUP_DAYS = 7
REQUESTED_P_VALUE = 0.05  # alpha level used for interpretations
REQUESTED_POWER = 0.80    # target power for planning (informational)
MDE_OPTIONS = [0.30] # 0.05, 0.10, 0.15, 0.30]  # example relative improvements for planning (informational)

from demos.agent_sessions.agent_sessions_loader import load_agent_sessions, summarize_agent_sessions


def estimate_experiment_duration(
    required_sample_size: int,
    avg_daily_traffic: float,
    allocation_ratio: float = 0.5
) -> dict:
    """Estimate how long an A/B test will take given current traffic.
    Mirrors the helper used in the quality-rate demo.
    """
    treatment_size = required_sample_size * allocation_ratio
    control_size = required_sample_size * (1 - allocation_ratio)
    daily_per_variant = avg_daily_traffic * allocation_ratio
    days_needed = treatment_size / daily_per_variant if daily_per_variant > 0 else float('inf')
    return {
        'total_sample_size': required_sample_size,
        'control_size': int(control_size),
        'treatment_size': int(treatment_size),
        'avg_daily_traffic': avg_daily_traffic,
        'daily_per_variant': daily_per_variant,
        'days_needed': days_needed,
        'weeks_needed': days_needed / 7,
    }


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
    aa_days = days[:DEFAULT_WARMUP_DAYS]
    ab_days = days[DEFAULT_WARMUP_DAYS:]

    print("\n" + "-" * 70)
    print("PHASE 0: A/A WARMUP (RESOLVED RATE)")
    print(f"First {DEFAULT_WARMUP_DAYS} days: sanity-check metric collection and experiment infra")
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

        # Sample size planning based on A/A
        quality_metric = aa_results.metric_results.get("resolved_rate", {})
        baseline_rate = quality_metric.get("control_value", 0.0)
        
        print("\n" + "-" * 70)
        print("SAMPLE SIZE PLANNING (Based on A/A Warmup)")
        print("-" * 70)
        
        if baseline_rate > 0:
            print(f"\nBaseline resolved rate from A/A: {baseline_rate:.3%}")
            print("\nSample size requirements for different MDEs:")
            print(f"{'MDE':<10} {'Target Rate':<15} {'Sample Size':<15} {'Est. Duration':<20}")
            print("-" * 70)

            avg_daily_traffic = len(df_aa) / len(aa_days) if aa_days else 0

            # Plan with the last MDE value for controls later
            global planned_sample_size, planned_days
            planned_sample_size = 0
            planned_days = 0
            for mde in MDE_OPTIONS:
                target_rate = baseline_rate * (1 + mde)

                sample_result = test_aa.backend.sample_size_proportion(
                    baseline_rate=baseline_rate,
                    mde=mde,
                    alpha=REQUESTED_P_VALUE,
                    power=REQUESTED_POWER,
                )

                total_size = sample_result['total_size']

                duration_est = estimate_experiment_duration(
                    required_sample_size=total_size,
                    avg_daily_traffic=avg_daily_traffic,
                    allocation_ratio=0.5
                )

                print(f"{mde*100:.0f}%{'':<6} "
                      f"{target_rate:.3%}{'':<7} "
                      f"{total_size:<15} "
                      f"{duration_est['days_needed']:.1f} days "
                      f"({duration_est['weeks_needed']:.1f} weeks)")

            print(f"\nNote: Estimates based on {avg_daily_traffic:.0f} avg daily sessions from A/A period")
            print(f"Assumptions: 50/50 split, alpha={REQUESTED_P_VALUE}, power={REQUESTED_POWER}")
            planned_sample_size = total_size
            planned_days = int(np.ceil(duration_est['days_needed'])) if np.isfinite(duration_est['days_needed']) else 0
        else:
            print("\nWarning: Baseline resolved rate is 0. Cannot calculate sample size.")
            print("Need more data or different metric definition.")
            planned_sample_size = 0
            planned_days = 0

    if not ab_days:
        print("\nNo days left for A/B period; demo complete.")
        return

    print("\n" + "-" * 70)
    print("PHASE 1: A/B SIMULATION (RESOLVED RATE)")
    print("Using remaining days as if a new resolution policy is rolled out")
    print("-" * 70)
    print(f"Assumptions: 50/50 split, alpha={REQUESTED_P_VALUE}, power={REQUESTED_POWER}")

    df_ab = df[df["day"].isin(ab_days)].copy()
    if df_ab.empty:
        print("No data available for A/B phase.")
        return

    df_ab["conversation_id"] = df_ab["row_id"]
    rng = np.random.default_rng(123)
    df_ab["variant"] = np.where(rng.random(len(df_ab)) < 0.5, "A", "B")

    # Day-by-day cumulative monitoring
    print("\nSequential monitoring: cumulative resolved rate up to each day")
    experiment_start = min(ab_days)
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

        # Progress tracking
        days_elapsed = (day - experiment_start).days + 1
        weeks_elapsed = days_elapsed / 7
        total_sessions = len(current)
        # No sample size planning in this demo; echo totals only

        print("\n" + "=" * 70)
        print(f"DAY {day.isoformat()} - CUMULATIVE RESOLVED RATE CHECK")
        print(f"Experiment Progress: Day {days_elapsed} ({weeks_elapsed:.1f} weeks) | Sample: {total_sessions:,}")
        print("=" * 70)
        print(results.summary())

        # Dual stop criteria (use planned values from A/A planning if available)
        reached_days = planned_days > 0 and days_elapsed >= planned_days
        reached_sample = planned_sample_size > 0 and total_sessions >= planned_sample_size

        if reached_days and not reached_sample:
            print("Reached planned experiment days; continuing until planned sample size for confidence.")
        elif reached_days and reached_sample:
            print("Reached planned experiment days.")
        if reached_sample and not reached_days:
            print("Reached planned sample size; continuing until planned days for confidence.")
        elif reached_sample and reached_days:
            print("Reached planned sample size.")

        # Significance status summary
        rm = results.metric_results.get("resolved_rate", {})
        r_stat = "SIG" if rm.get("significant", False) else "NOT-SIG"
        print(f"Status: resolved_rate [{r_stat}]")

    print("\nDemo complete: resolved session rate monitored over time.")


if __name__ == "__main__":
    main()
