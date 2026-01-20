import os
import numpy as np
import pandas as pd

from ab_framework import ABTest

# Configuration constants
REQUESTED_P_VALUE = 0.05  # alpha level used for interpretations
REQUESTED_POWER = 0.80    # target power for planning (informational)
DEFAULT_WARMUP_DAYS = 7

# MDE options (relative improvement targets). Examples: 5%, 10%, 15%, 30%
MDE_OPTIONS = [0.30] # 0.05, 0.10, 0.15, 0.30]

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
    # Ensure we run from repo root for consistent relative paths
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    os.chdir(repo_root)

    print("=" * 70)
    print("AGENT SESSIONS DEMO - QUALITY UPLIFT WITH RESOLUTION MONITOR")
    print("Primary metric: AI answer quality rate")
    print("Monitor metric: session resolved rate (soft monitoring)")
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
    aa_days = days[:DEFAULT_WARMUP_DAYS]
    ab_days = days[DEFAULT_WARMUP_DAYS:]

    print("\n" + "-" * 70)
    print("PHASE 0: A/A WARMUP (QUALITY + RESOLUTION MONITOR)")
    print(f"First {DEFAULT_WARMUP_DAYS} days: verify metrics before comparing models (soft monitoring)")
    print("-" * 70)

    df_aa = df[df["day"].isin(aa_days)].copy()
    if df_aa.empty:
        print("Not enough days for A/A warmup; skipping straight to A/B simulation.")
    else:
        # Standardize unit to conversation_id and deterministic 50/50 split
        df_aa["user_id"] = df_aa["conversation_id"]
        h_aa = pd.util.hash_pandas_object(df_aa["conversation_id"], index=False).astype(np.int64)
        df_aa["variant"] = np.where((h_aa % 2) == 0, "A", "B")
        # Debug: show sample of user_id assignment in A/A phase
        print("AA phase sample user_id:", df_aa["user_id"].head().tolist())

        test_aa = ABTest(
            name="agent_sessions_quality_vs_resolution_AA",
            variants=["A", "B"],
        )

        observed_counts_aa = df_aa.groupby("variant")["user_id"].nunique().to_dict()

        @test_aa.metric(metric_type="proportion", is_primary=True, monitor_alpha=REQUESTED_P_VALUE, monitor_power=REQUESTED_POWER)
        def quality_rate(data):
            user_level = data.groupby(["variant", "user_id"])["quality"].max()
            out = {}
            for variant in ["A", "B"]:
                v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
                out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
            return out

        @test_aa.metric(metric_type="proportion", inferiority_margin=0.02, monitor_alpha=REQUESTED_P_VALUE, monitor_power=REQUESTED_POWER)
        def resolved_rate(data):
            user_level = data.groupby(["variant", "user_id"])["resolved"].max()
            out = {}
            for variant in ["A", "B"]:
                v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
                out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
            return out

        aa_results = test_aa.analyze(
            df_aa,
            run_srm_check=True,
            observed_counts=observed_counts_aa,
            correction=None,
        )
        print(aa_results.summary())
        print("\nSOFT MONITORING DECISION:")
        print(aa_results.decision_soft_monitoring())
        print("\nA/A interpretation:")
        print(
            "We expect no significant differences here on either metric; "
            "this checks the joint behavior of quality and resolution before rollout."
        )

        # Sample size planning for primary metric (quality_rate)
        quality_metric = aa_results.metric_results.get("quality_rate", {})
        baseline_rate = quality_metric.get("control_value", 0.0)

        print("\n" + "-" * 70)
        print("SAMPLE SIZE PLANNING (Primary: quality_rate, Based on A/A)")
        print("-" * 70)

        if baseline_rate > 0:
            print(f"\nBaseline quality rate from A/A: {baseline_rate:.3%}")
            print("\nSample size requirements for different MDEs:")
            print(f"{'MDE':<10} {'Target Rate':<15} {'Sample Size':<15} {'Est. Duration':<20}")
            print("-" * 70)

            avg_daily_traffic = len(df_aa) / len(aa_days) if aa_days else 0

            # Plan with last MDE for downstream controls
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
            print("\nWarning: Baseline quality rate is 0. Cannot calculate sample size.")
            print("Need more data or different metric definition.")
            planned_sample_size = 0
            planned_days = 0

    if not ab_days:
        print("\nNo days left for A/B period; demo complete.")
        return

    print("\n" + "-" * 70)
    print("PHASE 1: A/B SIMULATION (QUALITY PRIMARY, RESOLUTION MONITOR)")
    print("Using remaining days as if a higher-quality model is rolled out (soft monitoring)")
    print("-" * 70)
    print(f"Assumptions: 50/50 split, alpha={REQUESTED_P_VALUE}, power={REQUESTED_POWER}")

    df_ab = df[df["day"].isin(ab_days)].copy()
    if df_ab.empty:
        print("No data available for A/B phase.")
        return

    # Standardize unit to conversation_id and deterministic 50/50 split
    df_ab["user_id"] = df_ab["conversation_id"]
    h_ab = pd.util.hash_pandas_object(df_ab["conversation_id"], index=False).astype(np.int64)
    df_ab["variant"] = np.where((h_ab % 2) == 0, "A", "B")
    # Debug: show sample of user_id assignment in A/B phase
    print("AB phase sample user_id:", df_ab["user_id"].head().tolist())

    # Day-by-day cumulative monitoring
    print("\nSequential monitoring: quality vs resolution up to each day")
    experiment_start = min(ab_days)
    for day in sorted(ab_days):
        current = df_ab[df_ab["day"] <= day].copy()
        if current.empty:
            continue

        test = ABTest(
            name=f"agent_quality_vs_resolution_until_{day.isoformat()}",
            variants=["A", "B"],
        )

        observed_counts = current.groupby("variant")["user_id"].nunique().to_dict()

        @test.metric(metric_type="proportion", is_primary=True, monitor_alpha=REQUESTED_P_VALUE, monitor_power=REQUESTED_POWER)
        def quality_rate(data):
            user_level = data.groupby(["variant", "user_id"])["quality"].max()
            out = {}
            for variant in ["A", "B"]:
                v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
                out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
            return out

        @test.metric(
            metric_type="proportion",
            inferiority_margin=0.02,  # allow up to 2 percentage points degradation (descriptive only)
            monitor_alpha=REQUESTED_P_VALUE,
            monitor_power=REQUESTED_POWER,
        )
        def resolved_rate(data):
            user_level = data.groupby(["variant", "user_id"])["resolved"].max()
            out = {}
            for variant in ["A", "B"]:
                v = user_level.loc[variant] if variant in user_level.index.get_level_values(0) else pd.Series(dtype=float)
                out[variant] = {"successes": int(v.sum()), "n": int(v.shape[0])}
            return out

        results = test.analyze(
            current,
            run_srm_check=True,
            observed_counts=observed_counts,
            correction=None,
        )

        # Progress tracking
        days_elapsed = (day - experiment_start).days + 1
        weeks_elapsed = days_elapsed / 7
        total_sessions = len(current)

        print("\n" + "=" * 70)
        print(f"DAY {day.isoformat()} - QUALITY (PRIMARY) VS RESOLUTION (MONITOR)")
        print(f"Experiment Progress: Day {days_elapsed} ({weeks_elapsed:.1f} weeks) | Sample: {total_sessions:,}")
        print("=" * 70)
        print(results.summary())
        print("\nSOFT MONITORING DECISION:")
        print(results.decision_soft_monitoring())
        print("\nDecision heuristics:")
        print("- Ship if quality_rate is significantly higher in B vs A.")
        print("- Review resolved_rate descriptively; it does not block decisions (soft monitoring).")

        # Significance status summary
        qm = results.metric_results.get("quality_rate", {})
        rm = results.metric_results.get("resolved_rate", {})
        q_stat = "SIG" if qm.get("significant", False) else "NOT-SIG"
        r_stat = "SIG" if rm.get("significant", False) else "NOT-SIG"
        print(f"Status: quality_rate [{q_stat}], resolved_rate [{r_stat}]")

        # Dual stop criteria using planned values from A/A planning
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

        # Stop when both planned days and planned sample size are reached
        if reached_days and reached_sample:
            print("Both planned days and sample size reached; stopping checks.")
            break

    print("\nDemo complete: quality uplift with resolution monitored (soft monitoring).")


if __name__ == "__main__":
    main()
