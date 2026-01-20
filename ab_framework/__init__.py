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
    >>> test = ABTest(name="homepage_redesign", variants=["A", "B"])
    >>> @test.metric(metric_type="proportion")
    ... def conversion_rate(data):
    ...     per_user = data.groupby(['variant', 'user_id'])['converted'].max().reset_index()
    ...     summary = per_user.groupby('variant')['converted'].agg(['sum', 'count']).to_dict('index')
    ...     return {v: {'successes': int(d['sum']), 'n': int(d['count'])} for v, d in summary.items()}
    >>> results = test.analyze(df, metrics=['conversion_rate'], run_srm_check=False)
"""

__version__ = "0.1.0"

from .core import ABTest
from .backends import ScipyBackend, OwlBackend, StatisticalBackend
from .quality import QualityChecker

__all__ = [
    'ABTest',
    'ScipyBackend',
    'OwlBackend', 
    'StatisticalBackend',
    'QualityChecker',
]
