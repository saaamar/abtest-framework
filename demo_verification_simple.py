"""
Simple verification demo showing framework accuracy
"""
import sys
import pandas as pd
from ab_framework import ABTest

print("=" * 70)
print("AB FRAMEWORK - ACCURACY VERIFICATION")
print("=" * 70)
print()

# Create sample data with known ground truth
print("Creating test data with known properties...")
print()

# Scenario: 10% vs 12% conversion rate
import numpy as np
np.random.seed(42)

n_per_group = 1000
data = []

# Control group: 10% conversion
for i in range(n_per_group):
    converted = 1 if np.random.random() < 0.10 else 0
    data.append({'user_id': f'A_{i}', 'variant': 'A', 'converted': converted})

# Treatment group: 12% conversion  
for i in range(n_per_group):
    converted = 1 if np.random.random() < 0.12 else 0
    data.append({'user_id': f'B_{i}', 'variant': 'B', 'converted': converted})

df = pd.DataFrame(data)

print(f"Total observations: {len(df):,}")
print(f"Control (A): {len(df[df['variant']=='A']):,}")
print(f"Treatment (B): {len(df[df['variant']=='B']):,}")
print()

# Create test and analyze
test = ABTest(
    name="verification_test",
    data=df,
    variant_col='variant',
    unit_id='user_id'
)

@test.metric
def conversion_rate(data):
    return data.groupby('user_id')['converted'].max()

results = test.analyze(['conversion_rate'])

print("=" * 70)
print("RESULTS")
print("=" * 70)
print(results.summary())
print()

print("=" * 70)
print("VERIFICATION")
print("=" * 70)
print()

# Calculate actual conversion rates
actual_control = df[df['variant']=='A']['converted'].mean()
actual_treatment = df[df['variant']=='B']['converted'].mean()

print(f"Actual Control Rate: {actual_control:.4f}")
print(f"Actual Treatment Rate: {actual_treatment:.4f}")
print(f"Actual Difference: {(actual_treatment - actual_control):.4f}")
print()

metric_result = results.metric_results['conversion_rate']
print(f"Framework Control Rate: {metric_result['control_value']:.4f}")
print(f"Framework Treatment Rate: {metric_result['treatment_value']:.4f}")
print(f"Framework P-value: {metric_result['p_value']:.6f}")
print()

if abs(actual_control - metric_result['control_value']) < 0.0001:
    print("[OK] Control rate matches")
else:
    print("[ERROR] Control rate mismatch")

if abs(actual_treatment - metric_result['treatment_value']) < 0.0001:
    print("[OK] Treatment rate matches")
else:
    print("[ERROR] Treatment rate mismatch")

print()
print("=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
