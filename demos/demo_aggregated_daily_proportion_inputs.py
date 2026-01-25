"""Demo: Using pre-aggregated *daily* proportion inputs (real-life workflow).

This demo shows how to use ab_framework when you *don't* have raw event logs.
In many teams, the only available data is a daily aggregate table like:

    - day
    - successes_A, successes_B (integer counts)
    - n_A, n_B (denominators)

Real-life usage pattern
-----------------------

At any point in time, you typically analyze *cumulative* data from day 1 up to
"today" (experiment start → now). This is the decision view.

Optionally, you might also look at a single day (or a rolling window) as a
diagnostic/monitoring view (e.g., to spot logging outages or unusual traffic).

Best practice: if you can, provide the *true* integer successes instead of
rate*n rounding. This demo generates true successes via a binomial process.
"""

import os
import sys

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ab_framework import ABTest


METRIC_NAME = "conversion_rate_from_daily_aggregates"


def _make_synthetic_daily_aggregates(
    *,
    start_day: str,
    num_days: int,
    n_a: int,
    n_b: int,
    p_a: float,
    p_b: float,
    seed: int = 7,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    days = pd.date_range(start=start_day, periods=num_days, freq="D").strftime("%Y-%m-%d")
    successes_a = rng.binomial(n=n_a, p=p_a, size=num_days)
    successes_b = rng.binomial(n=n_b, p=p_b, size=num_days)
    df = pd.DataFrame(
        {
            "day": days,
            "successes_A": successes_a.astype(int),
            "successes_B": successes_b.astype(int),
            "n_A": int(n_a),
            "n_B": int(n_b),
        }
    )
    df["rate_A"] = df["successes_A"] / df["n_A"]
    df["rate_B"] = df["successes_B"] / df["n_B"]
    return df


def _add_success_columns_from_rates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    required = {"day", "rate_A", "rate_B", "n_A", "n_B"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Convert rates to *integer* successes. Prefer true counts if available.
    df["successes_A"] = (df["rate_A"] * df["n_A"]).round().astype(int)
    df["successes_B"] = (df["rate_B"] * df["n_B"]).round().astype(int)
    return df


def _build_test() -> ABTest:
    test = ABTest(name="daily_aggregated_conversion", variants=["A", "B"])

    @test.metric(metric_type="proportion", is_primary=True)
    def conversion_rate_from_daily_aggregates(data: pd.DataFrame):
        successes_a = int(data["successes_A"].sum())
        n_a = int(data["n_A"].sum())
        successes_b = int(data["successes_B"].sum())
        n_b = int(data["n_B"].sum())
        return {
            "A": {"successes": successes_a, "n": n_a},
            "B": {"successes": successes_b, "n": n_b},
        }

    # Keep the string in sync with the registered function name.
    assert conversion_rate_from_daily_aggregates.__name__ == METRIC_NAME
    return test


def _analyze(test: ABTest, df_slice: pd.DataFrame):
    observed_counts = {"A": int(df_slice["n_A"].sum()), "B": int(df_slice["n_B"].sum())}
    return test.analyze(
        df_slice,
        metrics=[METRIC_NAME],
        run_srm_check=True,
        observed_counts=observed_counts,
        correction=None,
    )


def _print_compact_row(day: str, result: dict, *, n_a_total: int, n_b_total: int, label: str) -> None:
    lift_pp = (float(result["treatment_value"]) - float(result["control_value"])) * 100.0
    sig = "SIG" if result.get("significant") else "NOT-SIG"
    print(
        f"{label:<12} {day}  "
        f"nA={n_a_total:<7} nB={n_b_total:<7}  "
        f"A={result['control_value']:.3%}  B={result['treatment_value']:.3%}  "
        f"lift={lift_pp:+.2f}pp  p={result['p_value']:.4f}  {sig}"
    )


def main() -> None:
    # Realistic input option A: you already have integer successes + denominators.
    df = _make_synthetic_daily_aggregates(
        start_day="2026-01-01",
        num_days=14,
        n_a=12000,
        n_b=12000,
        p_a=0.100,
        p_b=0.106,
        seed=7,
    )

    print(df.head(10))

    # Realistic input option B: your colleague only has rates + denominators.
    # In that case, convert rate*n into integer successes (best-effort).
    # df = _add_success_columns_from_rates(df)

    test = _build_test()

    print("\nREAL-LIFE WORKFLOW: daily cumulative readout (day 1 → today)")
    print("-" * 100)
    print("Label        day         totals                     rates                 effect")
    print("-" * 100)

    # Simulate what a teammate would do operationally: every day, rerun analysis on
    # all data collected since day 1.
    for day in df["day"].tolist():
        df_to_date = df[df["day"] <= day]
        results = _analyze(test, df_to_date)
        metric_res = results.metric_results[METRIC_NAME]
        _print_compact_row(
            day,
            metric_res,
            n_a_total=int(df_to_date["n_A"].sum()),
            n_b_total=int(df_to_date["n_B"].sum()),
            label="cumulative",
        )

        # Optional diagnostic: look at "today" only.
        # This is useful for troubleshooting (logging outages, traffic changes),
        # but it is usually NOT the decision view.
        df_today = df[df["day"] == day]
        results_today = _analyze(test, df_today)
        metric_today = results_today.metric_results[METRIC_NAME]
        _print_compact_row(
            day,
            metric_today,
            n_a_total=int(df_today["n_A"].sum()),
            n_b_total=int(df_today["n_B"].sum()),
            label="today-only",
        )

        print("")

    # If you want a full narrative / detailed output, run it once for the latest day:
    latest_day = df["day"].iloc[-1]
    results_final = _analyze(test, df[df["day"] <= latest_day])
    print("\nFULL SUMMARY (latest cumulative)")
    print("=" * 70)
    print(results_final.summary())
    print("\n" + results_final.conclusion(METRIC_NAME))


if __name__ == "__main__":
    main()
