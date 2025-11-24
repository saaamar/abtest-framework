"""
Data Generator for A/B Testing Verification
Generates synthetic datasets for 8 test scenarios with known effect sizes
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
    split: float = 0.5,
    avg_impressions_per_user: int = 5
) -> pd.DataFrame:
    """
    Scenario 1: Simple Conversion Rate Test
    
    IMPRESSION-LEVEL DATA:
    - Each row = 1 impression/exposure event
    - Variant assignment at USER level (unit of randomization)
    - Users see multiple impressions; at most ONE leads to conversion
    - Conversion can happen on any impression
    
    Returns:
        DataFrame with columns: user_id, impression_id, variant, converted, timestamp
    """
    # Step 1: Create users and assign to variants
    user_ids = [f"u{i:04d}" for i in range(1, n_users + 1)]
    n_a = int(n_users * split)
    
    # Assign variants at USER level (unit of randomization)
    user_variants = {}
    for i, uid in enumerate(user_ids):
        user_variants[uid] = 'A' if i < n_a else 'B'
    
    # Step 2: Determine which users will convert (user-level decision)
    user_converts = {}
    for uid in user_ids:
        variant = user_variants[uid]
        conv_rate = baseline_rate if variant == 'A' else baseline_rate + effect_size
        user_converts[uid] = np.random.binomial(1, conv_rate)
    
    # Step 3: Generate impressions for each user
    impression_records = []
    impression_counter = 1
    base_date = datetime(2024, 1, 1)
    
    for uid in user_ids:
        variant = user_variants[uid]
        will_convert = user_converts[uid]
        
        # Each user gets 3-8 impressions
        n_impressions = np.random.randint(3, 9)
        
        # If user will convert, pick a random impression to be the conversion impression
        conversion_impression = np.random.randint(0, n_impressions) if will_convert else -1
        
        for imp_idx in range(n_impressions):
            converted = 1 if imp_idx == conversion_impression else 0
            timestamp = base_date + timedelta(hours=np.random.randint(0, 168))
            
            impression_records.append({
                'user_id': uid,
                'impression_id': f"imp{impression_counter:07d}",
                'variant': variant,
                'converted': converted,
                'timestamp': timestamp
            })
            impression_counter += 1
    
    df = pd.DataFrame(impression_records)
    
    return df

def generate_scenario2_revenue(
    n_users: int = 1000,
    baseline_active_rate: float = 0.30,
    baseline_revenue_per_session_mean: float = 10.0,
    baseline_revenue_per_session_std: float = 5.0,
    effect_size_rate: float = 0.05,  # More users become active
    effect_size_revenue: float = 2.0,  # Higher revenue per session
    split: float = 0.5
) -> pd.DataFrame:
    """
    Scenario 2: Custom Revenue Metric (Revenue per Active User)
    
    SESSION-LEVEL DATA:
    - Each row = 1 session
    - Variant assignment at USER level (unit of randomization)
    - Active user = user with sessions > 0
    - Effect: Both more users become active AND they spend more per session
    
    Returns:
        DataFrame with columns: user_id, session_id, variant, session_revenue, timestamp
    """
    # Step 1: Create users and assign to variants
    user_ids = [f"u{i:04d}" for i in range(1, n_users + 1)]
    n_a = int(n_users * split)
    
    # Assign variants at USER level
    user_variants = {}
    for i, uid in enumerate(user_ids):
        user_variants[uid] = 'A' if i < n_a else 'B'
    
    # Step 2: Determine which users are active and how many sessions
    user_sessions = {}
    for uid in user_ids:
        variant = user_variants[uid]
        active_rate = baseline_active_rate if variant == 'A' else baseline_active_rate + effect_size_rate
        is_active = np.random.binomial(1, active_rate)
        
        if is_active:
            # Active users have 1-10 sessions
            user_sessions[uid] = np.random.randint(1, 11)
        else:
            user_sessions[uid] = 0
    
    # Step 3: Generate session-level records
    session_records = []
    session_counter = 1
    base_date = datetime(2024, 1, 1)
    
    for uid in user_ids:
        variant = user_variants[uid]
        n_sessions = user_sessions[uid]
        
        if n_sessions == 0:
            continue  # Skip inactive users (no sessions)
        
        # Determine revenue mean for this user's variant
        rev_mean = baseline_revenue_per_session_mean if variant == 'A' else baseline_revenue_per_session_mean + effect_size_revenue
        
        # Generate each session
        for _ in range(n_sessions):
            session_revenue = max(0, np.random.normal(rev_mean, baseline_revenue_per_session_std))
            timestamp = base_date + timedelta(hours=np.random.randint(0, 168))
            
            session_records.append({
                'user_id': uid,
                'session_id': f"sess{session_counter:07d}",
                'variant': variant,
                'session_revenue': round(session_revenue, 2),
                'timestamp': timestamp
            })
            session_counter += 1
    
    df = pd.DataFrame(session_records)
    
    return df

def generate_scenario3_ctr(
    n_users: int = 1000,
    exposure_rate: float = 0.80,
    baseline_ctr: float = 0.05,
    effect_size: float = 0.01,
    split: float = 0.5,
    avg_impressions_per_user: int = 100
) -> pd.DataFrame:
    """
    Scenario 3: Click-Through Rate with Exposure Filtering
    
    IMPRESSION-LEVEL DATA:
    - Each row = 1 impression
    - Variant assignment is at USER level (unit of randomization)
    - Users are assigned to A or B, then their impressions inherit that assignment
    - Only exposed users generate impressions
    
    Returns:
        DataFrame with columns: user_id, impression_id, variant, clicked, timestamp
    """
    # Step 1: Create users and assign to variants
    user_ids = [f"u{i:04d}" for i in range(1, n_users + 1)]
    n_a = int(n_users * split)
    
    # Assign variants at USER level (unit of randomization)
    user_variants = {}
    for i, uid in enumerate(user_ids):
        user_variants[uid] = 'A' if i < n_a else 'B'
    
    # Step 2: Determine which users are exposed
    user_exposed = {}
    for uid in user_ids:
        user_exposed[uid] = np.random.binomial(1, exposure_rate)
    
    # Step 3: Generate impressions for each exposed user
    impression_records = []
    impression_counter = 1
    base_date = datetime(2024, 1, 1)
    
    for uid in user_ids:
        if not user_exposed[uid]:
            continue  # Skip non-exposed users
        
        variant = user_variants[uid]
        
        # Each exposed user gets random number of impressions
        n_impressions = np.random.randint(50, 200)
        
        # Determine CTR for this user's variant
        user_ctr = baseline_ctr if variant == 'A' else baseline_ctr + effect_size
        
        # Generate clicks for each impression
        for _ in range(n_impressions):
            clicked = np.random.binomial(1, user_ctr)
            timestamp = base_date + timedelta(hours=np.random.randint(0, 168))
            
            impression_records.append({
                'user_id': uid,
                'impression_id': f"imp{impression_counter:07d}",
                'variant': variant,
                'clicked': clicked,
                'timestamp': timestamp
            })
            impression_counter += 1
    
    df = pd.DataFrame(impression_records)
    
    return df

def generate_scenario4_multi_metric(
    n_users: int = 1000,
    baseline_conversion: float = 0.10,
    baseline_aov: float = 100.0,
    baseline_revenue_per_session: float = 10.0,
    baseline_time_hours: float = 48.0,
    effect_conversion: float = 0.02,
    effect_aov: float = 10.0,
    effect_revenue: float = 2.0,
    effect_time: float = -6.0,  # Negative = faster conversion
    split: float = 0.5
) -> pd.DataFrame:
    """
    Scenario 4: Multi-Metric Dashboard
    
    SESSION-LEVEL DATA:
    - Each row = 1 session
    - Variant assignment at USER level
    - Tracks: conversions, order values, session revenue
    - User-level metrics derived by aggregation
    
    Multiple metrics for the same experiment:
    1. Conversion rate (user-level: did user convert?)
    2. Average order value (AOV) (for converted sessions)
    3. Revenue per user (sum of session revenue / user)
    4. Time to conversion (hours from first session)
    
    Returns:
        DataFrame with columns: user_id, session_id, variant, converted_this_session, 
                               order_value, session_revenue, session_number, timestamp
    """
    # Step 1: Create users and assign to variants
    user_ids = [f"u{i:04d}" for i in range(1, n_users + 1)]
    n_a = int(n_users * split)
    
    # Assign variants at USER level
    user_variants = {}
    for i, uid in enumerate(user_ids):
        user_variants[uid] = 'A' if i < n_a else 'B'
    
    # Step 2: Determine which users convert (user-level decision)
    user_converts = {}
    user_conversion_time = {}
    for uid in user_ids:
        variant = user_variants[uid]
        conv_rate = baseline_conversion if variant == 'A' else baseline_conversion + effect_conversion
        converts = np.random.binomial(1, conv_rate)
        user_converts[uid] = converts
        
        if converts:
            # Time to conversion from first session
            time_mean = baseline_time_hours if variant == 'A' else baseline_time_hours + effect_time
            user_conversion_time[uid] = max(1, np.random.normal(time_mean, 24))
        else:
            user_conversion_time[uid] = None
    
    # Step 3: Generate sessions for each user (all users have 1-5 sessions)
    session_records = []
    session_counter = 1
    base_date = datetime(2024, 1, 1)
    
    for uid in user_ids:
        variant = user_variants[uid]
        will_convert = user_converts[uid]
        
        # Each user gets 1-5 sessions
        n_sessions = np.random.randint(1, 6)
        
        # If user converts, decide which session has the conversion
        conversion_session = np.random.randint(0, n_sessions) if will_convert else -1
        
        # Generate session timestamps (spread out over time)
        session_start_time = base_date + timedelta(hours=np.random.randint(0, 24))
        
        for sess_idx in range(n_sessions):
            # Session timestamp (sessions spread over 7 days)
            hours_offset = sess_idx * np.random.randint(6, 48)  # 6-48 hours between sessions
            sess_time = session_start_time + timedelta(hours=hours_offset)
            
            # Is this the conversion session?
            converted_this_session = 1 if sess_idx == conversion_session else 0
            
            # Order value (only for conversion session)
            if converted_this_session:
                aov_mean = baseline_aov if variant == 'A' else baseline_aov + effect_aov
                order_val = max(0, np.random.normal(aov_mean, 30))
            else:
                order_val = 0
            
            # Session revenue (all sessions have some revenue, variant B slightly higher)
            rev_mean = baseline_revenue_per_session if variant == 'A' else baseline_revenue_per_session + effect_revenue
            sess_revenue = max(0, np.random.normal(rev_mean, 5))
            
            session_records.append({
                'user_id': uid,
                'session_id': f"sess{session_counter:07d}",
                'variant': variant,
                'converted_this_session': converted_this_session,
                'order_value': round(order_val, 2),
                'session_revenue': round(sess_revenue, 2),
                'session_number': sess_idx + 1,
                'timestamp': sess_time
            })
            session_counter += 1
    
    df = pd.DataFrame(session_records)
    
    return df

def generate_scenario5_resolved_rate_with_gap(
    n_users: int = 1000,
    baseline_resolved_rate: float = 0.60,
    effect_size: float = 0.08,  # 60% -> 68% resolution (significant improvement)
    split: float = 0.5,
    avg_sessions_per_user: float = 2.5
) -> pd.DataFrame:
    """
    Scenario 5: Agent Bot - Resolved Rate with Real Gap
    
    SESSION-LEVEL DATA:
    - Each row = 1 session (conversation split by some logic)
    - Variant assignment at USER level (unit of randomization)
    - Each session can be resolved (is_resolved = 1) or not (0)
    - Users can have multiple sessions over time
    
    Resolved Rate = percentage of sessions that end with user's intent fulfilled
    Calculated at session level, not conversation level
    
    Returns:
        DataFrame with columns: user_id, conversation_id, session_id, variant, 
                               is_resolved, ai_metric, timestamp
    """
    # Step 1: Create users and assign to variants
    user_ids = [f"u{i:04d}" for i in range(1, n_users + 1)]
    n_a = int(n_users * split)
    
    # Assign variants at USER level (unit of randomization)
    user_variants = {}
    for i, uid in enumerate(user_ids):
        user_variants[uid] = 'A' if i < n_a else 'B'
    
    # Step 2: Generate sessions for each user
    session_records = []
    session_counter = 1
    conversation_counter = 1
    base_date = datetime(2024, 1, 1)
    
    for uid in user_ids:
        variant = user_variants[uid]
        
        # Each user has 1-5 sessions
        n_sessions = np.random.randint(1, 6)
        
        # Determine resolved rate for this user's variant
        resolved_rate = baseline_resolved_rate if variant == 'A' else baseline_resolved_rate + effect_size
        
        # Each user typically has 1-2 conversations
        n_conversations = np.random.randint(1, 3)
        sessions_per_conv = [n_sessions // n_conversations] * n_conversations
        # Distribute remaining sessions
        for i in range(n_sessions % n_conversations):
            sessions_per_conv[i] += 1
        
        for conv_idx in range(n_conversations):
            conv_id = f"conv{conversation_counter:07d}"
            conversation_counter += 1
            
            n_sess_in_conv = sessions_per_conv[conv_idx]
            
            for sess_idx in range(n_sess_in_conv):
                # Is this session resolved?
                is_resolved = np.random.binomial(1, resolved_rate)
                
                # AI metric (0-5): correlated with resolution
                # Resolved sessions tend to have higher AI metric
                if is_resolved:
                    ai_metric = np.clip(np.random.normal(4.0, 0.7), 0, 5)
                else:
                    ai_metric = np.clip(np.random.normal(2.5, 0.8), 0, 5)
                
                # Timestamp (sessions spread over days/weeks)
                hours_offset = sess_idx * np.random.randint(12, 72)
                timestamp = base_date + timedelta(hours=hours_offset + np.random.randint(0, 168))
                
                session_records.append({
                    'user_id': uid,
                    'conversation_id': conv_id,
                    'session_id': f"sess{session_counter:07d}",
                    'variant': variant,
                    'is_resolved': is_resolved,
                    'ai_metric': round(ai_metric, 2),
                    'timestamp': timestamp
                })
                session_counter += 1
    
    df = pd.DataFrame(session_records)
    return df

def generate_scenario6_resolved_rate_no_gap(
    n_users: int = 1000,
    baseline_resolved_rate: float = 0.60,
    effect_size: float = 0.01,  # 60% -> 61% (no meaningful difference)
    split: float = 0.5
) -> pd.DataFrame:
    """
    Scenario 6: Agent Bot - Resolved Rate with NO Real Gap
    
    Same structure as Scenario 5, but effect size is negligible
    This tests ability to correctly identify when there's NO significant difference
    
    Returns:
        DataFrame with same columns as Scenario 5
    """
    # Reuse Scenario 5 logic with minimal effect size
    return generate_scenario5_resolved_rate_with_gap(
        n_users=n_users,
        baseline_resolved_rate=baseline_resolved_rate,
        effect_size=effect_size,
        split=split
    )

def generate_scenario7_ai_metric_with_gap(
    n_users: int = 1000,
    baseline_ai_mean: float = 3.2,
    baseline_ai_std: float = 1.0,
    effect_size: float = 0.4,  # 3.2 -> 3.6 (meaningful improvement)
    split: float = 0.5
) -> pd.DataFrame:
    """
    Scenario 7: Agent Bot - AI Quality Metric with Real Gap
    
    SESSION-LEVEL DATA:
    - Each row = 1 session
    - Variant assignment at USER level
    - AI metric: continuous score 0-5 measuring quality of AI responses
    - Based on completeness, relevance, groundedness
    
    This tests continuous metrics (t-test) vs binary (proportion test)
    
    Returns:
        DataFrame with columns: user_id, conversation_id, session_id, variant,
                               ai_metric, is_resolved, timestamp
    """
    # Step 1: Create users and assign to variants
    user_ids = [f"u{i:04d}" for i in range(1, n_users + 1)]
    n_a = int(n_users * split)
    
    # Assign variants at USER level
    user_variants = {}
    for i, uid in enumerate(user_ids):
        user_variants[uid] = 'A' if i < n_a else 'B'
    
    # Step 2: Generate sessions
    session_records = []
    session_counter = 1
    conversation_counter = 1
    base_date = datetime(2024, 1, 1)
    
    for uid in user_ids:
        variant = user_variants[uid]
        
        # Each user has 1-5 sessions
        n_sessions = np.random.randint(1, 6)
        
        # Determine AI metric mean for this user's variant
        ai_mean = baseline_ai_mean if variant == 'A' else baseline_ai_mean + effect_size
        
        # Each user has 1-2 conversations
        n_conversations = np.random.randint(1, 3)
        sessions_per_conv = [n_sessions // n_conversations] * n_conversations
        for i in range(n_sessions % n_conversations):
            sessions_per_conv[i] += 1
        
        for conv_idx in range(n_conversations):
            conv_id = f"conv{conversation_counter:07d}"
            conversation_counter += 1
            
            n_sess_in_conv = sessions_per_conv[conv_idx]
            
            for sess_idx in range(n_sess_in_conv):
                # Generate AI metric for this session
                ai_metric = np.clip(np.random.normal(ai_mean, baseline_ai_std), 0, 5)
                
                # Is resolved is somewhat correlated with AI metric
                resolved_prob = min(0.95, max(0.05, (ai_metric / 5.0) * 0.8))
                is_resolved = np.random.binomial(1, resolved_prob)
                
                # Timestamp
                hours_offset = sess_idx * np.random.randint(12, 72)
                timestamp = base_date + timedelta(hours=hours_offset + np.random.randint(0, 168))
                
                session_records.append({
                    'user_id': uid,
                    'conversation_id': conv_id,
                    'session_id': f"sess{session_counter:07d}",
                    'variant': variant,
                    'ai_metric': round(ai_metric, 2),
                    'is_resolved': is_resolved,
                    'timestamp': timestamp
                })
                session_counter += 1
    
    df = pd.DataFrame(session_records)
    return df

def generate_scenario8_ai_metric_no_gap(
    n_users: int = 1000,
    baseline_ai_mean: float = 3.2,
    baseline_ai_std: float = 1.0,
    effect_size: float = 0.05,  # 3.2 -> 3.25 (negligible difference)
    split: float = 0.5
) -> pd.DataFrame:
    """
    Scenario 8: Agent Bot - AI Quality Metric with NO Real Gap
    
    Same structure as Scenario 7, but effect size is negligible
    Tests ability to correctly identify when there's NO significant difference
    
    Returns:
        DataFrame with same columns as Scenario 7
    """
    # Reuse Scenario 7 logic with minimal effect size
    return generate_scenario7_ai_metric_with_gap(
        n_users=n_users,
        baseline_ai_mean=baseline_ai_mean,
        baseline_ai_std=baseline_ai_std,
        effect_size=effect_size,
        split=split
    )

def generate_all_scenarios(output_dir: str = "verification/data"):
    """Generate all 8 scenarios and save to CSV files"""
    
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
    
    # Scenario 2: Revenue per Active User (SESSION-LEVEL DATA)
    print("Scenario 2: Revenue per Active User (Session-Level Data)")
    df2 = generate_scenario2_revenue(
        n_users=2000,
        baseline_active_rate=0.30,
        baseline_revenue_per_session_mean=10.0,
        baseline_revenue_per_session_std=5.0,
        effect_size_rate=0.05,
        effect_size_revenue=2.0
    )
    df2.to_csv(f"{output_dir}/scenario2_revenue.csv", index=False)
    print(f"  Generated {len(df2)} session records")
    print(f"  Data structure: Each row = 1 session")
    print(f"  Unit of randomization: User (variant assigned at user level)")
    
    # Calculate revenue per active user for both variants
    for variant in ['A', 'B']:
        variant_df = df2[df2['variant'] == variant]
        n_users = variant_df['user_id'].nunique()
        total_revenue = variant_df['session_revenue'].sum()
        revenue_per_active = total_revenue / n_users if n_users > 0 else 0
        n_sessions = len(variant_df)
        print(f"  Variant {variant}: ${revenue_per_active:.2f} revenue/active user ({n_users} active users, {n_sessions} sessions)")
    print()
    
    # Scenario 3: CTR with Exposure (IMPRESSION-LEVEL DATA)
    print("Scenario 3: Click-Through Rate (Impression-Level Data)")
    df3 = generate_scenario3_ctr(
        n_users=2000,
        exposure_rate=0.80,
        baseline_ctr=0.05,
        effect_size=0.01
    )
    df3.to_csv(f"{output_dir}/scenario3_ctr.csv", index=False)
    print(f"  Generated {len(df3)} impression records")
    print(f"  Data structure: Each row = 1 impression")
    print(f"  Unit of randomization: User (variant assigned at user level)")
    
    # Calculate CTR at impression level
    for variant in ['A', 'B']:
        variant_df = df3[df3['variant'] == variant]
        n_impressions = len(variant_df)
        n_clicks = variant_df['clicked'].sum()
        ctr = n_clicks / n_impressions if n_impressions > 0 else 0
        n_users = variant_df['user_id'].nunique()
        print(f"  Variant {variant}: {ctr:.4f} CTR ({n_clicks}/{n_impressions} clicks, {n_users} users)")
    print()
    
    # Scenario 4: Multi-Metric Dashboard (SESSION-LEVEL DATA)
    print("Scenario 4: Multi-Metric Dashboard (Session-Level Data)")
    df4 = generate_scenario4_multi_metric(
        n_users=2000,
        baseline_conversion=0.10,
        effect_conversion=0.02,
        baseline_aov=100.0,
        effect_aov=10.0,
        baseline_revenue_per_session=10.0,
        effect_revenue=2.0
    )
    df4.to_csv(f"{output_dir}/scenario4_multi.csv", index=False)
    print(f"  Generated {len(df4)} session records")
    print(f"  Data structure: Each row = 1 session")
    print(f"  Unit of randomization: User (variant assigned at user level)")
    
    # Calculate user-level metrics from session data
    for variant in ['A', 'B']:
        variant_df = df4[df4['variant'] == variant]
        n_users = variant_df['user_id'].nunique()
        
        # User-level conversion rate (did user convert in any session?)
        user_converted = variant_df.groupby('user_id')['converted_this_session'].max()
        conv_rate = user_converted.mean()
        
        # AOV for converted sessions
        converted_sessions = variant_df[variant_df['converted_this_session'] == 1]
        aov = converted_sessions['order_value'].mean() if len(converted_sessions) > 0 else 0
        
        # Revenue per user
        total_revenue = variant_df['session_revenue'].sum()
        revenue_per_user = total_revenue / n_users if n_users > 0 else 0
        
        print(f"  Variant {variant}: {conv_rate:.3f} user conv rate, ${aov:.2f} AOV, ${revenue_per_user:.2f} rev/user ({n_users} users)")
    print()
    
    # Scenario 5: Agent Bot - Resolved Rate WITH gap
    print("Scenario 5: Agent Bot - Resolved Rate (WITH Significant Gap)")
    df5 = generate_scenario5_resolved_rate_with_gap(
        n_users=2000,
        baseline_resolved_rate=0.60,
        effect_size=0.08  # 60% -> 68% (significant)
    )
    df5.to_csv(f"{output_dir}/scenario5_resolved_with_gap.csv", index=False)
    print(f"  Generated {len(df5)} session records")
    print(f"  Data structure: Each row = 1 session")
    for variant in ['A', 'B']:
        variant_df = df5[df5['variant'] == variant]
        resolved_rate = variant_df['is_resolved'].mean()
        avg_ai = variant_df['ai_metric'].mean()
        n_sessions = len(variant_df)
        print(f"  Variant {variant}: {resolved_rate:.3f} resolved rate, {avg_ai:.2f} avg AI metric ({n_sessions} sessions)")
    print()
    
    # Scenario 6: Agent Bot - Resolved Rate NO gap
    print("Scenario 6: Agent Bot - Resolved Rate (NO Significant Gap)")
    df6 = generate_scenario6_resolved_rate_no_gap(
        n_users=2000,
        baseline_resolved_rate=0.60,
        effect_size=0.01  # 60% -> 61% (not significant)
    )
    df6.to_csv(f"{output_dir}/scenario6_resolved_no_gap.csv", index=False)
    print(f"  Generated {len(df6)} session records")
    for variant in ['A', 'B']:
        variant_df = df6[df6['variant'] == variant]
        resolved_rate = variant_df['is_resolved'].mean()
        avg_ai = variant_df['ai_metric'].mean()
        n_sessions = len(variant_df)
        print(f"  Variant {variant}: {resolved_rate:.3f} resolved rate, {avg_ai:.2f} avg AI metric ({n_sessions} sessions)")
    print()
    
    # Scenario 7: Agent Bot - AI Metric WITH gap
    print("Scenario 7: Agent Bot - AI Quality Metric (WITH Significant Gap)")
    df7 = generate_scenario7_ai_metric_with_gap(
        n_users=2000,
        baseline_ai_mean=3.2,
        effect_size=0.4  # 3.2 -> 3.6 (significant)
    )
    df7.to_csv(f"{output_dir}/scenario7_ai_metric_with_gap.csv", index=False)
    print(f"  Generated {len(df7)} session records")
    for variant in ['A', 'B']:
        variant_df = df7[df7['variant'] == variant]
        avg_ai = variant_df['ai_metric'].mean()
        resolved_rate = variant_df['is_resolved'].mean()
        n_sessions = len(variant_df)
        print(f"  Variant {variant}: {avg_ai:.2f} avg AI metric, {resolved_rate:.3f} resolved rate ({n_sessions} sessions)")
    print()
    
    # Scenario 8: Agent Bot - AI Metric NO gap
    print("Scenario 8: Agent Bot - AI Quality Metric (NO Significant Gap)")
    df8 = generate_scenario8_ai_metric_no_gap(
        n_users=2000,
        baseline_ai_mean=3.2,
        effect_size=0.05  # 3.2 -> 3.25 (not significant)
    )
    df8.to_csv(f"{output_dir}/scenario8_ai_metric_no_gap.csv", index=False)
    print(f"  Generated {len(df8)} session records")
    for variant in ['A', 'B']:
        variant_df = df8[df8['variant'] == variant]
        avg_ai = variant_df['ai_metric'].mean()
        resolved_rate = variant_df['is_resolved'].mean()
        n_sessions = len(variant_df)
        print(f"  Variant {variant}: {avg_ai:.2f} avg AI metric, {resolved_rate:.3f} resolved rate ({n_sessions} sessions)")
    print()
    
    print("="*70)
    print("All 8 scenarios generated successfully!")
    print("="*70)
    return df1, df2, df3, df4, df5, df6, df7, df8

if __name__ == "__main__":
    generate_all_scenarios()
