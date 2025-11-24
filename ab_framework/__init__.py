"""
AB Testing Framework
====================

A comprehensive A/B testing orchestration framework built on top of owl_ab_test.

Features:
- Metric registration with decorators
- Multi-metric orchestration with Bonferroni/FDR correction
- Sample size calculation
- SRM (Sample Ratio Mismatch) checks
- Power analysis
- Standardized reporting (JSON/DataFrame/Markdown)
- Pluggable statistical backends

Example:
    >>> from ab_framework import ABTest
    >>> test = ABTest(name="homepage_redesign", data=df)
    >>> @test.metric
    ... def conversion_rate(data):
    ...     return data.groupby('user_id')['converted'].max()
    >>> results = test.analyze(['conversion_rate'])
"""

__version__ = "0.1.0"

from .core import ABTest
from .backends import OwlBackend, StatisticalBackend
from .sample_size import SampleSizeCalculator
from .quality import QualityChecker

__all__ = [
    'ABTest',
    'OwlBackend',
    'StatisticalBackend',
    'SampleSizeCalculator',
    'QualityChecker',
]
