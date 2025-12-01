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

	test = ABTest(
		name="scenario1_conversion",
		data=df,
		variant_col="variant",
		unit_id="user_id",
	)

	@test.metric(metric_type="proportion")
	def conversion_rate(data):
		return data.groupby("user_id")["converted"].max()

	results = test.analyze(["conversion_rate"])
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

	test = ABTest(
		name="scenario3_ctr",
		data=df,
		variant_col="variant",
		unit_id="impression_id",  # Event-level!
	)

	@test.metric(metric_type="proportion")
	def click_through_rate(data):
		"""CTR at impression level."""
		return data.set_index("impression_id")["clicked"]

	results = test.analyze(["click_through_rate"])
	result = results.metric_results["click_through_rate"]
	assert "p_value" in result
	assert 0 <= result["p_value"] <= 1
	# We engineered B to have higher CTR; expect non-trivial signal but
	# don't require an extremely small p-value to avoid brittleness.
	assert result["p_value"] < 0.5
