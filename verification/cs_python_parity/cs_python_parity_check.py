import json
import math
import subprocess
import sys
from typing import Dict, Any, Tuple

import pandas as pd

REPO_ROOT = str((__file__).rsplit("\\verification\\", 1)[0])
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ab_framework import ABTest


def _python_proportion_result() -> Dict[str, Any]:
    df = pd.DataFrame(
        {
            "day": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
                "2026-01-04",
                "2026-01-05",
            ],
            "successes_control": [1197, 1162, 1189, 1145, 1175],
            "n_control": [12000, 12000, 12000, 12000, 12000],
            "successes_treatment": [1302, 1270, 1324, 1307, 1266],
            "n_treatment": [12000, 12000, 12000, 12000, 12000],
        }
    )

    test = ABTest(name="parity_proportion", variants=["control", "treatment"])
    test.setup(alpha=0.05)

    @test.metric(metric_type="proportion", is_primary=True)
    def conversion_rate(data: pd.DataFrame):
        return {
            "control": {
                "successes": int(data["successes_control"].sum()),
                "n": int(data["n_control"].sum()),
            },
            "treatment": {
                "successes": int(data["successes_treatment"].sum()),
                "n": int(data["n_treatment"].sum()),
            },
        }

    results = test.analyze(df, metrics=["conversion_rate"], run_srm_check=False, correction=None)
    r = results.metric_results["conversion_rate"]
    return {
        "kind": "proportion",
        "metric": {
            "MetricName": "conversion_rate",
            "MetricType": "Proportion",
            "ControlVariant": "control",
            "TreatmentVariant": "treatment",
            "ControlValue": float(r["control_value"]),
            "TreatmentValue": float(r["treatment_value"]),
            "SampleSizeControl": int(r["sample_size_control"]),
            "SampleSizeTreatment": int(r["sample_size_treatment"]),
            "Lift": float(r["lift"]),
            "PValue": float(r["p_value"]),
            "CiLower": float(r["ci_lower"]),
            "CiUpper": float(r["ci_upper"]),
            "Significant": bool(r["significant"]),
        },
    }


def _combine_sample_stats(df: pd.DataFrame, mean_col: str, std_col: str, n_col: str) -> Tuple[float, float, int]:
    total_n = int(df[n_col].sum())
    if total_n <= 0:
        raise ValueError("total_n must be > 0")

    total_sum = float((df[mean_col] * df[n_col]).sum())
    overall_mean = total_sum / total_n

    # sumsq_i = (n_i - 1) * s_i^2 + n_i * mean_i^2
    total_sumsq = float((((df[n_col] - 1) * (df[std_col] ** 2)) + (df[n_col] * (df[mean_col] ** 2))).sum())

    if total_n <= 1:
        overall_std = 0.0
    else:
        var_num = total_sumsq - total_n * (overall_mean**2)
        sample_var = max(var_num / (total_n - 1), 0.0)
        overall_std = math.sqrt(sample_var)

    return overall_mean, overall_std, total_n


def _python_mean_result() -> Dict[str, Any]:
    df = pd.DataFrame(
        {
            "day": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
                "2026-01-04",
                "2026-01-05",
            ],
            "mean_control": [2.50, 2.47, 2.51, 2.49, 2.50],
            "std_control": [4.20, 4.10, 4.30, 4.25, 4.15],
            "n_control": [12000, 12000, 12000, 12000, 12000],
            "mean_treatment": [2.58, 2.56, 2.60, 2.57, 2.59],
            "std_treatment": [4.25, 4.15, 4.35, 4.28, 4.22],
            "n_treatment": [12000, 12000, 12000, 12000, 12000],
        }
    )

    test = ABTest(name="parity_mean", variants=["control", "treatment"])
    test.setup(alpha=0.05)

    @test.metric(metric_type="mean", is_primary=True)
    def avg_revenue(data: pd.DataFrame):
        mean_c, std_c, n_c = _combine_sample_stats(data, "mean_control", "std_control", "n_control")
        mean_t, std_t, n_t = _combine_sample_stats(data, "mean_treatment", "std_treatment", "n_treatment")
        return {
            "control": {"mean": float(mean_c), "std": float(std_c), "n": int(n_c)},
            "treatment": {"mean": float(mean_t), "std": float(std_t), "n": int(n_t)},
        }

    results = test.analyze(df, metrics=["avg_revenue"], run_srm_check=False, correction=None)
    r = results.metric_results["avg_revenue"]
    return {
        "kind": "mean",
        "metric": {
            "MetricName": "avg_revenue",
            "MetricType": "Mean",
            "ControlVariant": "control",
            "TreatmentVariant": "treatment",
            "ControlValue": float(r["control_value"]),
            "TreatmentValue": float(r["treatment_value"]),
            "SampleSizeControl": int(r["sample_size_control"]),
            "SampleSizeTreatment": int(r["sample_size_treatment"]),
            "Lift": float(r["lift"]),
            "PValue": float(r["p_value"]),
            "CiLower": float(r["ci_lower"]),
            "CiUpper": float(r["ci_upper"]),
            "Significant": bool(r["significant"]),
        },
    }


def _cs_results() -> Dict[str, Dict[str, Any]]:
    project = "c:/Users/saaamar/repos/ab_testing/ab_framework_cs/examples/ParityCheck/ParityCheck.csproj"
    completed = subprocess.run(
        ["dotnet", "run", "--project", project, "-c", "Release"],
        capture_output=True,
        text=True,
        check=True,
    )

    lines = [ln.strip() for ln in completed.stdout.splitlines() if ln.strip()]
    print("\n=== C# OUTPUT (raw JSON lines) ===")
    for ln in lines:
        print(ln)

    out: Dict[str, Dict[str, Any]] = {}
    for ln in lines:
        obj = json.loads(ln)
        out[obj["kind"]] = obj
    return out


def _assert_close(a: float, b: float, *, tol: float, label: str) -> None:
    if math.isnan(a) and math.isnan(b):
        return
    if abs(a - b) > tol:
        raise AssertionError(f"{label} differs: python={a} cs={b} (tol={tol})")


def main() -> None:
    print("=== Python vs C# parity check ===")
    print("Running Python computations...")
    py = {
        "proportion": _python_proportion_result(),
        "mean": _python_mean_result(),
    }
    print("\n=== PYTHON RESULTS (computed) ===")
    print(json.dumps(py["proportion"], indent=2, sort_keys=True))
    print(json.dumps(py["mean"], indent=2, sort_keys=True))

    print("\nRunning C# project...")
    cs = _cs_results()
    print("\n=== C# RESULTS (parsed) ===")
    print(json.dumps(cs["proportion"], indent=2, sort_keys=True))
    print(json.dumps(cs["mean"], indent=2, sort_keys=True))

    comparisons = [
        ("proportion", [
            ("ControlValue", 1e-12),
            ("TreatmentValue", 1e-12),
            ("Lift", 1e-10),
            ("PValue", 5e-7),
            ("CiLower", 5e-7),
            ("CiUpper", 5e-7),
        ]),
        ("mean", [
            ("ControlValue", 1e-12),
            ("TreatmentValue", 1e-12),
            ("Lift", 1e-10),
            ("PValue", 5e-7),
            ("CiLower", 5e-7),
            ("CiUpper", 5e-7),
        ]),
    ]

    for kind, fields in comparisons:
        py_m = py[kind]["metric"]
        cs_m = cs[kind]["metric"]

        print(f"\n--- FIELD COMPARISON: {kind} ---")
        for key, tol in fields:
            a = float(py_m[key])
            b = float(cs_m[key])
            print(f"{kind}.{key}: python={a} cs={b} tol={tol}")
            _assert_close(float(py_m[key]), float(cs_m[key]), tol=tol, label=f"{kind}.{key}")

        if bool(py_m["Significant"]) != bool(cs_m["Significant"]):
            raise AssertionError(f"{kind}.Significant differs: python={py_m['Significant']} cs={cs_m['Significant']}")

        print(f"{kind}.Significant: python={py_m['Significant']} cs={cs_m['Significant']}")

    print("OK: C# and Python results match within tolerance")


if __name__ == "__main__":
    main()
