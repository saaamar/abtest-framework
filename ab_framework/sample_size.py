"""Sample size planning now lives on StatisticalBackend.

This module is kept only to provide a clear error message if it is imported
directly. Use :mod:`ab_framework.backends` and call the planning methods on
your chosen backend instead.
"""

raise RuntimeError(
    "ab_framework.sample_size no longer provides sample size utilities. "
    "Use a StatisticalBackend implementation's sample_size_proportion/"
    "sample_size_mean methods instead."
)
