"""
Data Generator for A/B Testing Verification
Generates synthetic datasets for 4 test scenarios with known effect sizes
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple

# Set random seed for reproducibility
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)


def generate_scenario1_conversion(
    n_users: int = 1000,
    baseline_rate: float = 0.10,
    effect_size: float = 0.02,
    split: float = 0.5
) -> pd.DataFrame:
    """
    Scenario 1: Simple Conversion Rate Test
    
    Args:
        n_users: Total number of users
        baseline_rate: Baseline conversion rate for variant A
        effect_size: Absolute effect size (B rate = baseline + effect_size)
        split: Proportion of users in variant A
    
    Returns:
        DataFrame with columns: user_id, variant, converted, timestamp
    """
    n_a = int(n_users * split)
    n_b = n_users - n_a
    
    # Generate user IDs
    user_ids = [f"u{i:04d}" for i in range(1, n_users + 1)]
    
    # Assign variants
    variants = ['A'] * n_a + ['B'] * n_b
    
    # Generate conversions with known effect size
    conversions_a = np.random.binomial(1, baseline_rate, n_a)
    conversions_b = np.random.binomial(1, baseline_rate + effect_size, n_b)
    conversions = np.concatenate([conversions_a, conversions_b])
    
    # Generate timestamps (spread over 7 days)
    base_date = datetime(2024, 1, 1)
    timestamps = [base_date + timedelta(hours=np.random.randint(0, 168)) 
                  for _ in range(n_users)]
    
    df = pd.DataFrame({
        'user_id': user_ids,
        'variant': variants,
        'converted': conversions,
        'timestamp': timestamps
    })
    
    return df


def generate_scenario2_revenue(
    n_users: int = 1000,
    baseline_active_rate: float = 0.30,
    baseline_revenue_mean: float = 50.0,
    baseline_revenue_std: float = 20.0,
    effect_size_rate: float = 0.05,  # More users become active
    effect_size_revenue: float = 10.0,  # Higher revenue per active user
    split: float = 0.5
) -> pd.DataFrame:
    """
    Scenario 2: Custom Revenue Metric (Revenue per Active User)
    
    Active user = user with sessions > 0
    Effect: Both more users become active AND they spend more
    
    Returns:
        DataFrame with columns: user_id, variant, revenue, sessions, timestamp
    """
    n_a = int(n_users * split)
    n_b = n_users - n_a
    
    user_ids = [f"u{i:04d}" for i in range(1, n_users + 1)]
    variants = ['A'] * n_a + ['B'] * n_b
    
    # Generate active status (sessions > 0)
    active_a = np.random.binomial(1, baseline_active_rate, n_a)
    active_b = np.random.binomial(1, baseline_active_rate + effect_size_rate, n_b)
    
    # Generate sessions (active users have 1-10 sessions, inactive have 0)
    sessions_a = np.where(active_a, np.random.randint(1, 11, n_a), 0)
    sessions_b = np.where(active_b, np.random.randint(1, 11, n_b), 0)
    sessions = np.concatenate([sessions_a, sessions_b])
    
    # Generate revenue (only for active users)
    revenue_a = np.where(
        active_a,
        np.maximum(0, np.random.normal(baseline_revenue_mean, baseline_revenue_std, n_a)),
        0
    )
    revenue_b = np.where(
        active_b,
        np.maximum(0, np.random.normal(baseline_revenue_mean + effect_size_revenue, 
                                       baseline_revenue_std, n_b)),
        0
    )
    revenue = np.concatenate([revenue_a, revenue_b])
    
    base_date = datetime(2024, 1, 1)
    timestamps = [base_date + timedelta(hours=np.random.randint(0, 168)) 
                  for _ in range(n_users)]
    
    df = pd.DataFrame({
        'user_id': user_ids,
        'variant': variants,
        'revenue': np.round(revenue, 2),
        'sessions': sessions,
        'timestamp': timestamps
    })
    
    return df


def generate_scenario3_ctr(
    n_users: int = 1000,
    exposure_rate: float = 0.80,
    baseline_ctr: float = 0.05,
    effect_size: float = 0.01,
    split: float = 0.5
) -> pd.DataFrame:
    """
    Scenario 3: Click-Through Rate with Exposure Filtering
    
    Only users who were exposed (saw the feature) should be included in CTR calculation
    
    Returns:
        DataFrame with columns: user_id, variant, clicks, impressions, exposed, timestamp
    """
    n_a = int(n_users * split)
    n_b = n_users - n_a
    
    user_ids = [f"u{i:04d}" for i in range(1, n_users + 1)]
    variants = ['A'] * n_a + ['B'] * n_b
    
    # Generate exposure status
    exposed_a = np.random.binomial(1, exposure_rate, n_a)
    exposed_b = np.random.binomial(1, exposure_rate, n_b)
    exposed = np.concatenate([exposed_a, exposed_b])
    
    # Generate impressions (more for exposed users)
    impressions_a = np.where(exposed_a, np.random.randint(50, 200, n_a), np.random.randint(0, 10, n_a))
    impressions_b = np.where(exposed_b, np.random.randint(50, 200, n_b), np.random.randint(0, 10, n_b))
    impressions = np.concatenate([impressions_a, impressions_b])
    
    # Generate clicks based on CTR (only meaningful for exposed users)
    clicks_a = np.random.binomial(impressions_a, baseline_ctr * exposed_a)
    clicks_b = np.random.binomial(impressions_b, (baseline_ctr + effect_size) * exposed_b)
    clicks = np.concatenate([clicks_a, clicks_b])
    
    base_date = datetime(2024, 1, 1)
    timestamps = [base_date + timedelta(hours=np.random.randint(0, 168)) 
                  for _ in range(n_users)]
    
    df = pd.DataFrame({
        'user_id': user_ids,
        'variant': variants,
        'clicks': clicks,
        'impressions': impressions,
        'exposed': exposed,
        'timestamp': timestamps
    })
    
    return df


def generate_scenario4_multi_metric(
    n_users: int = 1000,
    baseline_conversion: float = 0.10,
    baseline_aov: float = 100.0,
    baseline_revenue: float = 10.0,
    baseline_time_hours: float = 48.0,
    effect_conversion: float = 0.02,
    effect_aov: float = 10.0,
    effect_revenue: float = 2.0,
    effect_time: float = -6.0,  # Negative = faster conversion
    split: float = 0.5
) -> pd.DataFrame:
    """
    Scenario 4: Multi-Metric Dashboard
    
    Multiple metrics for the same experiment:
    1. Conversion rate
    2. Average order value (AOV)
    3. Revenue per user
    4. Time to conversion (hours)
    
    Returns:
        DataFrame with columns: user_id, variant, converted, order_value, 
                               revenue, time_to_conversion, timestamp
    """
    n_a = int(n_users * split)
    n_b = n_users - n_a
    
    user_ids = [f"u{i:04d}" for i in range(1, n_users + 1)]
    variants = ['A'] * n_a + ['B'] * n_b
    
    # Metric 1: Conversion
    conversions_a = np.random.binomial(1, baseline_conversion, n_a)
    conversions_b = np.random.binomial(1, baseline_conversion + effect_conversion, n_b)
    conversions = np.concatenate([conversions_a, conversions_b])
    
    # Metric 2: Average Order Value (only for converted users)
    aov_a = np.where(
        conversions_a,
        np.maximum(0, np.random.normal(baseline_aov, 30, n_a)),
        0
    )
    aov_b = np.where(
        conversions_b,
        np.maximum(0, np.random.normal(baseline_aov + effect_aov, 30, n_b)),
        0
    )
    order_value = np.concatenate([aov_a, aov_b])
    
    # Metric 3: Revenue per user (all users, including non-converted)
    revenue_a = np.maximum(0, np.random.normal(baseline_revenue, 5, n_a))
    revenue_b = np.maximum(0, np.random.normal(baseline_revenue + effect_revenue, 5, n_b))
    revenue = np.concatenate([revenue_a, revenue_b])
    
    # Metric 4: Time to conversion (only for converted users, in hours)
    time_a = np.where(
        conversions_a,
        np.maximum(1, np.random.normal(baseline_time_hours, 24, n_a)),
        np.nan
    )
    time_b = np.where(
        conversions_b,
        np.maximum(1, np.random.normal(baseline_time_hours + effect_time, 24, n_b)),
        np.nan
    )
    time_to_conversion = np.concatenate([time_a, time_b])
    
    base_date = datetime(2024, 1, 1)
    timestamps = [base_date + timedelta(hours=np.random.randint(0, 168)) 
                  for _ in range(n_users)]
    
    df = pd.DataFrame({
        'user_id': user_ids,
        'variant': variants,
        'converted': conversions,
        'order_value': np.round(order_value, 2),
        'revenue': np.round(revenue, 2),
        'time_to_conversion': np.round(time_to_conversion, 2),
        'timestamp': timestamps
    })
    
    return df


def generate_all_scenarios(output_dir: str = "verification/data"):
    """Generate all 4 scenarios and save to CSV files"""
    
    print("Generating synthetic A/B test data...")
    print(f"Random seed: {RANDOM_SEED}")
    print()
    
    # Scenario 1: Conversion Rate
    print("Scenario 1: Simple Conversion Rate Test")
    df1 = generate_scenario1_conversion(
        n_users=2000,
        baseline_rate=0.10,
        effect_size=0.02  # 10% -> 12% conversion (20% relative increase)
    )
    df1.to_csv(f"{output_dir}/scenario1_conversion.csv", index=False)
    print(f"  Generated {len(df1)} records")
    print(f"  Variant A: {(df1[df1['variant']=='A']['converted'].mean()):.3f} conversion rate")
    print(f"  Variant B: {(df1[df1['variant']=='B']['converted'].mean()):.3f} conversion rate")
    print()
    
    # Scenario 2: Revenue per Active User
    print("Scenario 2: Custom Revenue Metric")
    df2 = generate_scenario2_revenue(
        n_users=2000,
        baseline_active_rate=0.30,
        baseline_revenue_mean=50.0,
        effect_size_rate=0.05,
        effect_size_revenue=10.0
    )
    df2.to_csv(f"{output_dir}/scenario2_revenue.csv", index=False)
    print(f"  Generated {len(df2)} records")
    
    # Calculate revenue per active user for both variants
    for variant in ['A', 'B']:
        variant_df = df2[df2['variant'] == variant]
        active_df = variant_df[variant_df['sessions'] > 0]
        if len(active_df) > 0:
            revenue_per_active = active_df['revenue'].sum() / len(active_df)
            print(f"  Variant {variant}: ${revenue_per_active:.2f} revenue/active user ({len(active_df)} active)")
    print()
    
    # Scenario 3: CTR with Exposure
    print("Scenario 3: Click-Through Rate with Exposure Filtering")
    df3 = generate_scenario3_ctr(
        n_users=2000,
        exposure_rate=0.80,
        baseline_ctr=0.05,
        effect_size=0.01
    )
    df3.to_csv(f"{output_dir}/scenario3_ctr.csv", index=False)
    print(f"  Generated {len(df3)} records")
    
    # Calculate CTR for exposed users
    for variant in ['A', 'B']:
        variant_df = df3[(df3['variant'] == variant) & (df3['exposed'] == 1)]
        if variant_df['impressions'].sum() > 0:
            ctr = variant_df['clicks'].sum() / variant_df['impressions'].sum()
            print(f"  Variant {variant}: {ctr:.4f} CTR ({len(variant_df)} exposed users)")
    print()
    
    # Scenario 4: Multi-Metric
    print("Scenario 4: Multi-Metric Dashboard")
    df4 = generate_scenario4_multi_metric(
        n_users=2000,
        baseline_conversion=0.10,
        effect_conversion=0.02,
        baseline_aov=100.0,
        effect_aov=10.0
    )
    df4.to_csv(f"{output_dir}/scenario4_multi.csv", index=False)
    print(f"  Generated {len(df4)} records")
    
    for variant in ['A', 'B']:
        variant_df = df4[df4['variant'] == variant]
        conv_rate = variant_df['converted'].mean()
        converted_df = variant_df[variant_df['converted'] == 1]
        aov = converted_df['order_value'].mean() if len(converted_df) > 0 else 0
        print(f"  Variant {variant}: {conv_rate:.3f} conv rate, ${aov:.2f} AOV")
    print()
    
    print("All scenarios generated successfully!")
    return df1, df2, df3, df4


if __name__ == "__main__":
    generate_all_scenarios()
