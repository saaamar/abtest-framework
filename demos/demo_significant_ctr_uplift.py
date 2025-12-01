"""Example showing a statistically SIGNIFICANT result.

This demonstrates the conclusion output for a test that detects a real effect.
"""

import os
import sys

import pandas as pd

# Ensure we can import ab_framework when running directly from the repo
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ab_framework import ABTest

# Load CTR data which has a significant effect
data_path = os.path.join(REPO_ROOT, 'data', 'scenario3_ctr.csv')
df = pd.read_csv(data_path)

# Create test at impression level
test = ABTest(
    name="ad_creative_test",
    data=df,
    unit_id="impression_id",  # Event-level analysis
    variant_col="variant"
)

# Define metric
@test.metric(metric_type="proportion")
def click_through_rate(data):
    """CTR at impression level."""
    return data.set_index('impression_id')['clicked']

# Analyze
results = test.analyze(['click_through_rate'])

# Print summary
print(results.summary())

# Print statistical conclusion
print("\n" + results.conclusion('click_through_rate'))

print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)
print("""
This example shows a SIGNIFICANT result where the treatment variant
clearly outperforms the control. The framework provides:

1. Clear statement of significance and direction
2. Actual values for both groups with percentage formatting
3. Difference in percentage points (for binary metrics)
4. Relative change (lift %)
5. P-value
6. 95% confidence interval

The recommendation is implicit: since the test is significant,
you can ship the treatment variant!
""")
