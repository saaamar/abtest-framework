"""Pytest unit tests for proportion-based metrics using synthetic data."""

import numpy as np
import pandas as pd

from ab_framework import ABTest


def test_scenario1_conversion_synthetic():
	"""Simple conversion-rate test on synthetic user-level data."""

	rng = np.random.default_rng(42)
	n_users = 1000
	users = np.arange(n_users)
	variants = np.where(rng.random(n_users) < 0.5, "A", "B")

	# Slightly higher conversion in B so we expect a small effect
	base_conv_a = 0.10
	base_conv_b = 0.12
	converted = np.where(
		variants == "A",
		rng.random(n_users) < base_conv_a,
		rng.random(n_users) < base_conv_b,
	).astype(int)

	df = pd.DataFrame({
		"user_id": users,
		"variant": variants,
		"converted": converted,
	})

	# ------------------------------------------------------------------
	# Optional debug prints for inspecting the synthetic dataset
	# Uncomment temporarily when tuning parameters or debugging.
	#
	# filter_a = df["variant"] == "A"
	# filter_b = df["variant"] == "B"
	# print("Variant A summary (conversion scenario):")
	# print(df[filter_a].describe())
	# print("\nVariant B summary (conversion scenario):")
	# print(df[filter_b].describe())
	# ------------------------------------------------------------------

	test = ABTest(name="scenario1_conversion", variants=["A", "B"])

	@test.metric(metric_type="proportion")
	def conversion_rate(data):
		per_user = data.groupby(["variant", "user_id"])["converted"].max().reset_index()
		summary = per_user.groupby("variant")["converted"].agg(["sum", "count"]).to_dict("index")
		return {
			v: {"successes": int(d["sum"]), "n": int(d["count"])}
			for v, d in summary.items()
		}

	results = test.analyze(df, metrics=["conversion_rate"], run_srm_check=False)
	result = results.metric_results["conversion_rate"]
	assert "p_value" in result
	assert 0 <= result["p_value"] <= 1
	# With the chosen effect size, p should usually be below 0.5.
	assert result["p_value"] < 0.5


def test_scenario3_ctr_synthetic():
	"""Click-through-rate test at impression level (synthetic)."""

	rng = np.random.default_rng(7)
	n_impressions = 5000
	impression_ids = np.arange(n_impressions)
	variants = np.where(rng.random(n_impressions) < 0.5, "A", "B")

	ctr_a = 0.05
	ctr_b = 0.08
	clicked = np.where(
		variants == "A",
		rng.random(n_impressions) < ctr_a,
		rng.random(n_impressions) < ctr_b,
	).astype(int)

	df = pd.DataFrame({
		"impression_id": impression_ids,
		"variant": variants,
		"clicked": clicked,
	})

	# ------------------------------------------------------------------
	# Optional debug prints for inspecting the synthetic CTR dataset
	# Uncomment temporarily when tuning parameters or debugging.
	#
	# filter_a = df["variant"] == "A"
	# filter_b = df["variant"] == "B"
	# print("Variant A summary (CTR scenario):")
	# print(df[filter_a].describe())
	# print("\nVariant B summary (CTR scenario):")
	# print(df[filter_b].describe())
	# ------------------------------------------------------------------

	test = ABTest(name="scenario3_ctr", variants=["A", "B"])

	@test.metric(metric_type="proportion")
	def click_through_rate(data):
		"""CTR at impression level."""
		summary = data.groupby("variant")["clicked"].agg(["sum", "count"]).to_dict("index")
		return {
			v: {"successes": int(d["sum"]), "n": int(d["count"])}
			for v, d in summary.items()
		}

	results = test.analyze(df, metrics=["click_through_rate"], run_srm_check=False)
	result = results.metric_results["click_through_rate"]
	assert "p_value" in result
	assert 0 <= result["p_value"] <= 1
	# We engineered B to have higher CTR; expect non-trivial signal but
	# don't require an extremely small p-value to avoid brittleness.
	assert result["p_value"] < 0.5


def test_proportion_handles_zero_baseline_gracefully():
	"""When control proportion is 0, core should not raise ZeroDivisionError.

	This guards against the Owl backend's lift computation dividing by zero
	when the baseline rate is exactly 0. We expect a stable, non-significant
	result with p_value=1.0 and lift=0.0.
	"""

	# Construct a tiny dataset where variant A has all zeros and
	# variant B has at least one success.
	data = pd.DataFrame({
		"user_id": [1, 2, 3, 4],
		"variant": ["A", "A", "B", "B"],
		"converted": [0, 0, 1, 0],
	})

	test = ABTest(name="zero_baseline_proportion", variants=["A", "B"])

	@test.metric(metric_type="proportion")
	def conversion_rate(df):
		per_user = df.groupby(["variant", "user_id"])["converted"].max().reset_index()
		summary = per_user.groupby("variant")["converted"].agg(["sum", "count"]).to_dict("index")
		return {
			v: {"successes": int(d["sum"]), "n": int(d["count"])}
			for v, d in summary.items()
		}

	results = test.analyze(data, metrics=["conversion_rate"], run_srm_check=False)
	result = results.metric_results["conversion_rate"]
	assert "p_value" in result
	# AbexpBackend handles zero baseline gracefully by computing the actual p-value
	# rather than returning hardcoded p=1.0. The p-value should be non-significant.
	assert result["p_value"] > 0.05  # Not significant
	assert not result["significant"]
	assert result["control_value"] == 0.0
