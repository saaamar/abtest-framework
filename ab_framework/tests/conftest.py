"""Pytest configuration for ab_framework tests.

Ensures the project root is on sys.path so that `import ab_framework`
works when running tests from the repository root.
"""

import os
import sys
from pathlib import Path

# Add project root (one level above `ab_framework/`) to sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
