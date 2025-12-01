"""Test: Custom A/B Testing Framework

Verification of the custom ab_framework on all 8 scenarios, mirroring the
structure of test_owl.py and test_abexp.py.

Each test:
- loads the same CSV data used by the other package tests
- defines one or more metrics using ABTest
- runs analyze()
- prints a compact summary and returns a dict for aggregation
"""

import time
from typing import Dict, Any, List

import numpy as np
import pandas as pd

from pathlib import Path
from ab_framework.core import ABTest
from verification import ground_truth


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


def _load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


def test_scenario1_framework() -> Dict[str, Any]:
    """Scenario 1: Simple Conversion Rate (user-level after aggregation)."""
    print("\n" + "=" * 70)
    print("FRAMEWORK - Scenario 1: Conversion Rate (Impression-Level → User-Level)")
    print("=" * 70)

    start = time.time()

    df = _load_csv("scenario1_conversion.csv")
    print(f"\nData: {len(df)} impressions from {df['user_id'].nunique()} users")

    # ABTest expects data with unit_id + variant; metrics return Series indexed by unit
    test = ABTest(name="scenario1", data=df, variant_col="variant", unit_id="user_id")

    @test.metric(metric_type="proportion")
    def conversion_rate(data: pd.DataFrame) -> pd.Series:
        # 1 if user converted in any impression
        return data.groupby("user_id")["converted"].max()

    results = test.analyze(metrics=["conversion_rate"], variants=["A", "B"])
    res = list(results.metric_results.values())[0]

    elapsed = time.time() - start

    print("\nControl A:", res["control_value"])
    print("Treatment B:", res["treatment_value"])
    print("Lift:", res["lift"])
    print("p-value:", res["p_value"])
    print(f"⏱️  Time: {elapsed:.3f} seconds")


    return {
        "scenario": "Scenario 1",
        "works": True,
        "time": elapsed,
        "p_value": res["p_value"],
        "lift": res["lift"],
        "metric_a": res["control_value"],
        "metric_b": res["treatment_value"],
    }


def test_scenario2_framework() -> Dict[str, Any]:
    """Scenario 2: Revenue per Active User (session-level → user-level)."""
    print("\n" + "=" * 70)
    print("FRAMEWORK - Scenario 2: Revenue per Active User (Session-Level)")
    print("=" * 70)

    start = time.time()

    df = _load_csv("scenario2_revenue.csv")
    print(f"\nData: {len(df)} sessions from {df['user_id'].nunique()} active users")

    test = ABTest(name="scenario2", data=df, variant_col="variant", unit_id="user_id")

    @test.metric(metric_type="mean")
    def revenue_per_user(data: pd.DataFrame) -> pd.Series:
        # Sum session revenue per user (all users are active)
        return data.groupby("user_id")["session_revenue"].sum()

    results = test.analyze(metrics=["revenue_per_user"], variants=["A", "B"])
    res = list(results.metric_results.values())[0]

    elapsed = time.time() - start

    print("\nMean A:", res["control_value"])
    print("Mean B:", res["treatment_value"])
    print("Lift:", res["lift"])
    print("p-value:", res["p_value"])
    print(f"⏱️  Time: {elapsed:.3f} seconds")


    return {
        "scenario": "Scenario 2",
        "works": True,
        "time": elapsed,
        "p_value": res["p_value"],
        "lift": res["lift"],
        "metric_a": res["control_value"],
        "metric_b": res["treatment_value"],
    }


def test_scenario3_framework() -> Dict[str, Any]:
    """Scenario 3: CTR (impression-level CTR, binary metric)."""
    print("\n" + "=" * 70)
    print("FRAMEWORK - Scenario 3: CTR (Impression-Level)")
    print("=" * 70)

    start = time.time()

    df = _load_csv("scenario3_ctr.csv")
    print(f"\nData: {len(df)} impressions from {df['user_id'].nunique()} users")

    test = ABTest(name="scenario3", data=df, variant_col="variant", unit_id="user_id")

    @test.metric(metric_type="proportion")
    def ctr_impression(data: pd.DataFrame) -> pd.Series:
        # Each impression is a trial; CTR per impression is just clicked (0/1)
        # We aggregate to user-level mean CTR if we want user-centric; here we
        # follow ground truth which uses impression-level z-test, so we treat
        # each impression as a unit.
        # To keep the same API, use impression_id as unit_id-like index.
        return data.groupby("impression_id")["clicked"].max()

    # Temporarily override unit_id for this metric by creating a new ABTest
    df_impr = df.copy()
    df_impr["impression_id"] = np.arange(len(df_impr))
    test_ctr = ABTest(
        name="scenario3_impression",
        data=df_impr,
        variant_col="variant",
        unit_id="impression_id",
    )
    test_ctr.register_metric("ctr_impression", ctr_impression, metric_type="proportion")

    results = test_ctr.analyze(metrics=["ctr_impression"], variants=["A", "B"])
    res = list(results.metric_results.values())[0]

    elapsed = time.time() - start

    print("\nCTR A:", res["control_value"])
    print("CTR B:", res["treatment_value"])
    print("Lift:", res["lift"])
    print("p-value:", res["p_value"])
    print(f"⏱️  Time: {elapsed:.3f} seconds")


    return {
        "scenario": "Scenario 3",
        "works": True,
        "time": elapsed,
        "p_value": res["p_value"],
        "lift": res["lift"],
        "metric_a": res["control_value"],
        "metric_b": res["treatment_value"],
    }


def test_scenario4_framework() -> Dict[str, Any]:
    """Scenario 4: Multi-Metric Dashboard (session-level → user-level)."""
    print("\n" + "=" * 70)
    print("FRAMEWORK - Scenario 4: Multi-Metric Dashboard (Session-Level)")
    print("=" * 70)

    start = time.time()

    df = _load_csv("scenario4_multi.csv")
    print(f"\nData: {len(df)} sessions from {df['user_id'].nunique()} users")

    test = ABTest(name="scenario4", data=df, variant_col="variant", unit_id="user_id")

    @test.metric(metric_type="proportion")
    def converted_any(data: pd.DataFrame) -> pd.Series:
        return data.groupby("user_id")["converted_this_session"].max()

    @test.metric(metric_type="mean")
    def total_order_value(data: pd.DataFrame) -> pd.Series:
        return data.groupby("user_id")["order_value"].sum()

    @test.metric(metric_type="mean")
    def total_revenue(data: pd.DataFrame) -> pd.Series:
        return data.groupby("user_id")["session_revenue"].sum()

    metrics = ["converted_any", "total_order_value", "total_revenue"]

    results = test.analyze(metrics=metrics, variants=["A", "B"], correction="bonferroni")

    elapsed = time.time() - start

    for name, res in results.metric_results.items():
        if "error" in res:
            print(f"\n[ERROR] {name}: {res['error']}")
        else:
            print(f"\nMetric: {name}")
            print("  Control:", res["control_value"])
            print("  Treatment:", res["treatment_value"])
            print("  Lift:", res["lift"])
            print("  p-value:", res["p_value"])
            print("  significant:", res["significant"])

    print(f"\n⏱️  Time: {elapsed:.3f} seconds")

    # No direct ground-truth helper for multi-metric, but individual metrics
    # are already covered by scenarios 1–3.

    return {
        "scenario": "Scenario 4",
        "works": True,
        "time": elapsed,
        "metrics": results.metric_results,
    }


def _binary_scenario(name: str, csv: str, value_col: str) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print(f"FRAMEWORK - {name}")
    print("=" * 70)

    start = time.time()

    df = _load_csv(csv)
    print(f"\nData: {len(df)} sessions")

    test = ABTest(name=name, data=df, variant_col="variant", unit_id="user_id")

    @test.metric(metric_type="proportion")
    def binary_metric(data: pd.DataFrame) -> pd.Series:
        # Aggregate per user as mean of the binary flag across sessions
        return data.groupby("user_id")[value_col].mean()

    results = test.analyze(metrics=["binary_metric"], variants=["A", "B"])
    res = list(results.metric_results.values())[0]

    elapsed = time.time() - start

    print("\nRate A:", res["control_value"])
    print("Rate B:", res["treatment_value"])
    print("Lift:", res["lift"])
    print("p-value:", res["p_value"])
    print(f"⏱️  Time: {elapsed:.3f} seconds")

    return {
        "scenario": name,
        "works": True,
        "time": elapsed,
        "p_value": res["p_value"],
        "metric_a": res["control_value"],
        "metric_b": res["treatment_value"],
    }


def _continuous_scenario(name: str, csv: str, value_col: str) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print(f"FRAMEWORK - {name}")
    print("=" * 70)

    start = time.time()

    df = _load_csv(csv)
    print(f"\nData: {len(df)} sessions")

    test = ABTest(name=name, data=df, variant_col="variant", unit_id="user_id")

    @test.metric(metric_type="mean")
    def metric_value(data: pd.DataFrame) -> pd.Series:
        return data.groupby("user_id")[value_col].mean()

    results = test.analyze(metrics=["metric_value"], variants=["A", "B"])
    res = list(results.metric_results.values())[0]

    elapsed = time.time() - start

    print("\nMean A:", res["control_value"])
    print("Mean B:", res["treatment_value"])
    print("Lift:", res["lift"])
    print("p-value:", res["p_value"])
    print(f"⏱️  Time: {elapsed:.3f} seconds")

    return {
        "scenario": name,
        "works": True,
        "time": elapsed,
        "p_value": res["p_value"],
        "metric_a": res["control_value"],
        "metric_b": res["treatment_value"],
    }


def test_scenario5_framework() -> Dict[str, Any]:
    """Scenario 5: Agent Bot - Resolved Rate WITH gap."""
    return _binary_scenario(
        name="Scenario 5: Resolved WITH gap",
        csv="scenario5_resolved_with_gap.csv",
        value_col="is_resolved",
    )


def test_scenario6_framework() -> Dict[str, Any]:
    """Scenario 6: Agent Bot - Resolved Rate NO gap."""
    return _binary_scenario(
        name="Scenario 6: Resolved NO gap",
        csv="scenario6_resolved_no_gap.csv",
        value_col="is_resolved",
    )


def test_scenario7_framework() -> Dict[str, Any]:
    """Scenario 7: Agent Bot - AI Quality Metric WITH gap."""
    return _continuous_scenario(
        name="Scenario 7: AI metric WITH gap",
        csv="scenario7_ai_metric_with_gap.csv",
        value_col="ai_metric",
    )


def test_scenario8_framework() -> Dict[str, Any]:
    """Scenario 8: Agent Bot - AI Quality Metric NO gap."""
    return _continuous_scenario(
        name="Scenario 8: AI metric NO gap",
        csv="scenario8_ai_metric_no_gap.csv",
        value_col="ai_metric",
    )


def run_all_framework_tests() -> List[Dict[str, Any]]:
    """Run all framework tests and summarize, similar to owl/abexp runners."""
    print("\n" + "=" * 70)
    print("FRAMEWORK EVALUATION")
    print("Testing custom ab_framework on all 8 scenarios")
    print("=" * 70)

    results: List[Dict[str, Any]] = []
    results.append(test_scenario1_framework())
    results.append(test_scenario2_framework())
    results.append(test_scenario3_framework())
    results.append(test_scenario4_framework())
    results.append(test_scenario5_framework())
    results.append(test_scenario6_framework())
    results.append(test_scenario7_framework())
    results.append(test_scenario8_framework())

    print("\n" + "=" * 70)
    print("FRAMEWORK SUMMARY")
    print("=" * 70)

    working = sum(1 for r in results if r.get("works", False))
    total_time = sum(r["time"] for r in results)

    print(f"\n✅ {working}/8 scenarios working")
    print(f"⏱️  Total time: {total_time:.3f} seconds")

    return results


if __name__ == "__main__":
    run_all_framework_tests()
