"""Pytest unit tests for multi-metric behavior using synthetic data."""

import numpy as np
import pandas as pd
from ab_framework import ABTest


def test_multi_metric_bonferroni_synthetic():
	"""Multi-metric test with Bonferroni correction on synthetic data."""

	# ------------------------------------------------------------------
	# Synthetic user-level dataset
	# ------------------------------------------------------------------
	# We generate a simple two-variant experiment with:
	# - user_id: one row per user
	# - variant: "A" or "B" with ~50/50 split
	# - converted_this_session: binary outcome, higher rate in B
	# - order_value: revenue per user, higher mean in B among converters

	rng = np.random.default_rng(99)
	n_users = 600
	users = np.arange(n_users)
	# Randomly assign users to variants A/B
	variants = np.where(rng.random(n_users) < 0.5, "A", "B")

	# Conversion probability is larger for B so that the backend
	# sees a multi-metric improvement under the treatment.
	conv_a = 0.12
	conv_b = 0.16
	converted = np.where(
		variants == "A",
		rng.random(n_users) < conv_a,
		rng.random(n_users) < conv_b,
	).astype(int)

	# Revenue model: only converters have positive order_value.
	# Among converters, B has higher average order_value than A.
	order_value = np.where(
		converted == 1,
		np.where(
			variants == "A",
				rng.normal(40.0, 10.0, size=n_users),
				rng.normal(45.0, 10.0, size=n_users),
		),
		0.0,
	)

	df = pd.DataFrame({
		"user_id": users,
		"variant": variants,
		"converted_this_session": converted,
		"order_value": order_value,
	})

	# ------------------------------------------------------------------
	# Optional debug prints for inspecting the multi-metric dataset
	# Uncomment temporarily when tuning parameters or debugging.
	#
	# filter_a = df["variant"] == "A"
	# filter_b = df["variant"] == "B"
	# print("Variant A summary (multi-metric scenario):")
	# print(df[filter_a].describe())
	# print("\nVariant B summary (multi-metric scenario):")
	# print(df[filter_b].describe())
	# ------------------------------------------------------------------

	test = ABTest(
		name="multi_metric_test",
		data=df,
		variant_col="variant",
		unit_id="user_id",
	)

	# ------------------------------------------------------------------
	# Metric definitions
	# ------------------------------------------------------------------
	# Three metrics share the same underlying synthetic data:
	# - conversion_rate: binary conversion outcome per user
	# - avg_order_value: mean order_value among converters only
	# - revenue_per_user: total revenue per user (zero for non-converters)

	@test.metric(metric_type="proportion")
	def conversion_rate(data):
		"""User-level conversion (converted in any session)."""
		return data.groupby("user_id")["converted_this_session"].max()

	@test.metric(metric_type="mean")
	def avg_order_value(data):
		"""AOV among converters only."""
		converters = data[data["converted_this_session"] == 1]
		if len(converters) == 0:
			return pd.Series(dtype=float)
		return converters.groupby("user_id")["order_value"].mean()

	@test.metric(metric_type="mean")
	def revenue_per_user(data):
		"""Total revenue per user."""
		return data.groupby("user_id")["order_value"].sum()

	# ------------------------------------------------------------------
	# Analysis with Bonferroni correction
	# ------------------------------------------------------------------
	results = test.analyze(
		metrics=["conversion_rate", "avg_order_value", "revenue_per_user"],
		correction="bonferroni",
	)
	for metric_name in ["conversion_rate", "avg_order_value", "revenue_per_user"]:
		result = results.metric_results[metric_name]
		assert "adjusted_alpha" in result
		assert abs(result["adjusted_alpha"] - (0.05 / 3)) < 1e-8
