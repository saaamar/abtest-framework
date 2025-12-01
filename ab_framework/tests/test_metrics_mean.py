"""Pytest unit tests for mean-based metrics using synthetic data."""

import numpy as np
import pandas as pd

from ab_framework import ABTest


def test_scenario2_revenue_synthetic():
	"""Revenue per active user with synthetic continuous data."""

	rng = np.random.default_rng(123)
	n_users = 800
	sessions_per_user = 3

	user_ids = np.repeat(np.arange(n_users), sessions_per_user)
	variants = np.where(rng.random(n_users) < 0.5, "A", "B")
	variants = np.repeat(variants, sessions_per_user)

	# Baseline revenue per session differs between variants
	mean_a, std_a = 5.0, 3.0
	mean_b, std_b = 6.0, 3.0
	revenue = np.where(
		variants == "A",
		rng.normal(mean_a, std_a, size=n_users * sessions_per_user),
		rng.normal(mean_b, std_b, size=n_users * sessions_per_user),
	)
	revenue = np.clip(revenue, 0.0, None)

	df = pd.DataFrame({
		"user_id": user_ids,
		"variant": variants,
		"session_revenue": revenue,
	})

	# ------------------------------------------------------------------
	# Optional debug prints for inspecting the synthetic revenue dataset
	# Uncomment temporarily when tuning parameters or debugging.
	#
	# filter_a = df["variant"] == "A"
	# filter_b = df["variant"] == "B"
	# print("Variant A summary (revenue scenario):")
	# print(df[filter_a].describe())
	# print("\nVariant B summary (revenue scenario):")
	# print(df[filter_b].describe())
	# ------------------------------------------------------------------

	test = ABTest(
		name="scenario2_revenue",
		data=df,
		variant_col="variant",
		unit_id="user_id",
	)

	@test.metric(metric_type="mean")
	def revenue_per_active_user(data):
		"""Revenue per user, filtered to active users (revenue > 0)."""
		user_revenue = data.groupby("user_id")["session_revenue"].sum()
		active = user_revenue[user_revenue > 0]
		return active

	results = test.analyze(["revenue_per_active_user"])
	result = results.metric_results["revenue_per_active_user"]
	assert "p_value" in result
	assert 0 <= result["p_value"] <= 1
	# We constructed B to have higher revenue; expect strong significance.
	assert result["p_value"] < 0.001
