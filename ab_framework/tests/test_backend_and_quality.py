"""Pytest unit tests for backend utilities (sample size, SRM)."""

import pytest

from ab_framework import ABTest, QualityChecker


def test_sample_size_planning_backend():
	"""Test backend sample size planning on synthetic assumptions."""

	test = ABTest(name="dummy", variants=["A", "B"])

	# ------------------------------------------------------------------
	# Optional debug prints for inspecting the dummy planning dataset
	# Uncomment temporarily when tuning parameters or debugging.
	#
	# print("Sample-size planning dummy data:")
	# print(test.data.describe(include="all"))
	# ------------------------------------------------------------------

	result = test.backend.sample_size_proportion(
		baseline_rate=0.10,
		mde=0.05,
		power=0.80,
	)

	assert result["total_size"] > 0
	assert result["control_size"] > 0
	assert result["treatment_size"] > 0

	# Smaller MDE should require a larger sample
	result_smaller_mde = test.backend.sample_size_proportion(
		baseline_rate=0.10,
		mde=0.02,
		power=0.80,
	)
	assert result_smaller_mde["total_size"] > result["total_size"]

	result = test.backend.sample_size_mean(
		baseline_mean=50.0,
		baseline_std=25.0,
		mde=0.10,
		power=0.80,
	)
	assert result["total_size"] > 0


def test_srm_check_good_and_bad_splits():
	"""Test SRM checker on good and bad splits."""

	checker = QualityChecker()

	result = checker.check_srm({"A": 1000, "B": 1005})
	assert result["passed"]
	assert result["p_value"] > 0.01

	result = checker.check_srm({"A": 10523, "B": 9477})
	assert not result["passed"]
	assert result["p_value"] < 0.001


def test_metric_type_validation_missing_and_invalid():
	"""Metric registration should reject missing or invalid metric_type values."""

	test = ABTest(name="metric_type_validation", variants=["A", "B"])

	# Missing metric_type should raise a TypeError (required kw-only arg)
	with pytest.raises(TypeError):
		@test.metric()  # type: ignore[misc]
		def bad_metric_missing_type(data):  # pragma: no cover - body should never run
			return data["user_id"]

	# Invalid metric_type should raise a ValueError during registration
	with pytest.raises(ValueError):
		@test.metric(metric_type="not_a_valid_type")  # type: ignore[misc]
		def bad_metric_invalid_type(data):  # pragma: no cover - body should never run
			return data["user_id"]


def test_srm_requires_observed_counts_in_stateless_mode():
	"""Core should require observed_counts when SRM is enabled."""

	test = ABTest(name="srm_requires_counts", variants=["A", "B"])

	@test.metric(metric_type="proportion")
	def dummy_metric(_data):
		return {"A": {"successes": 1, "n": 10}, "B": {"successes": 2, "n": 10}}

	with pytest.raises(ValueError):
		test.analyze(data=None, metrics=["dummy_metric"], run_srm_check=True)
