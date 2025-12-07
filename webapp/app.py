from flask import Flask, render_template, request, redirect, url_for
import os
import sqlite3
from datetime import datetime, date
import math
import pandas as pd
from ab_framework.core import ABTest
from .agent_data_service import get_recent_baseline_and_volume, get_recent_user_variant_df
import traceback

DB_PATH = os.path.join(os.path.dirname(__file__), "ab_demo.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY,
                name TEXT,
                created_at TEXT,
                status TEXT CHECK(status IN ('planned','running','completed')) NOT NULL,
                agent_a_id TEXT,
                agent_b_id TEXT,
                primary_metric TEXT,
                alpha REAL,
                power REAL,
                mde_relative REAL,
                allocation_ratio REAL,
                planned_per_variant INTEGER,
                planned_days INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS experiment_metrics (
                id INTEGER PRIMARY KEY,
                experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
                name TEXT,
                role TEXT CHECK(role IN ('primary','soft_monitoring','guardrail')) NOT NULL
            )
            """
        )
        conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
        traceback.print_exc()
    finally:
        conn.close()

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    
    # Initialize database - force it to run every time
    print(f"Initializing database at: {DB_PATH}")
    init_db()
    
    # Verify tables exist
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='experiments'")
        if not cur.fetchone():
            print("❌ WARNING: experiments table not found after init_db()")
            print("Attempting to recreate database...")
            conn.close()
            # Try deleting and recreating
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            init_db()
        else:
            print(f"✅ Database verified successfully at: {DB_PATH}")
        conn.close()
    except Exception as e:
        print(f"❌ Error during database verification: {e}")
        traceback.print_exc()


    @app.route("/")
    def starter():
        # Render starter page standalone (without base layout) for testing
        return render_template("overview.html")

    @app.route("/setup_experiment", methods=["GET", "POST"])
    def setup_experiment():
        if request.method == "POST":
            action = request.form.get("action")
            primary_metric = request.form.get("primary_metric") or "quality_ratio"
            selected_metrics = request.form.getlist("metrics")
            alpha = float(request.form.get("alpha") or 0.05)
            power = float(request.form.get("power") or 0.8)
            mde_percent = float(request.form.get("mde_percent") or 5.0)
            mde_relative = mde_percent / 100.0
            allocation_ratio = float(request.form.get("allocation_ratio") or 0.5)
            daily_per_variant_input = request.form.get("daily_per_variant")

            # Use A/A-style history to estimate baseline and traffic (aligned with demo)
            baseline_rate, aa_daily_per_variant = get_recent_baseline_and_volume(primary_metric, days=7)

            # If user leaves field empty, use A/A-derived value; otherwise trust user input
            if daily_per_variant_input:
                daily_per_variant = float(daily_per_variant_input)
            else:
                daily_per_variant = aa_daily_per_variant

            # Use ABTest backend like the demo for sample size planning
            # Initialize with recent 7-day mapping (unit = conversation_id)
            df_conv = get_recent_user_variant_df(days=7)
            if df_conv.empty:
                # Fallback minimal data to avoid crash; planning still uses baseline_rate
                df_conv = pd.DataFrame({
                    "conversation_id": ["fallback-a", "fallback-b"],
                    "variant": ["A", "B"],
                })
            ab = ABTest(
                name="planning_demo",
                data=df_conv,
                variant_col="variant",
                unit_id="conversation_id",
                alpha=alpha,
            )

            ssz = ab.backend.sample_size_proportion(
                baseline_rate=baseline_rate,
                mde=mde_relative,
                alpha=alpha,
                power=power,
                ratio=1.0,
            )

            # backend returns total_size / control_size; mirror demo semantics
            required_per_variant = int(ssz.get("control_size", 0))
            estimated_days = int(math.ceil(required_per_variant / max(1.0, daily_per_variant)))

            plan_summary = {
                "primary_metric": primary_metric,
                "baseline_rate": baseline_rate,
                "target_uplift_percent": mde_percent,
                "required_per_variant": required_per_variant,
                "estimated_days": estimated_days,
                "alpha": alpha,
                "power": power,
                "daily_per_variant": daily_per_variant,
                "allocation_ratio": allocation_ratio,
            }

            # Logging similar to demos: planning details
            try:
                print("\n" + "-" * 70)
                print("SAMPLE SIZE PLANNING (webapp)")
                print("-" * 70)
                print(f"Primary metric: {primary_metric}")
                print(f"Baseline rate (7-day): {baseline_rate:.3f}")
                print(f"Target uplift (MDE): {mde_percent:.1f}% -> target rate {(baseline_rate * (1 + mde_relative)):.3f}")
                print(f"Alpha: {alpha}, Power: {power}")
                print(f"Required sample size per variant: {required_per_variant}")
                print(f"Daily per variant (approx.): {daily_per_variant}")
                print(f"Estimated duration: {estimated_days} days")
            except Exception:
                pass

            if action == "start":
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO experiments (
                        name, created_at, status,
                        agent_a_id, agent_b_id,
                        primary_metric, alpha, power,
                        mde_relative, allocation_ratio,
                        planned_per_variant, planned_days
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "Demo experiment",
                        datetime.utcnow().isoformat(),
                        "running",
                        "original",
                        "b_agent",
                        primary_metric,
                        alpha,
                        power,
                        mde_relative,
                        allocation_ratio,
                        required_per_variant,
                        estimated_days,
                    ),
                )
                exp_id = cur.lastrowid
                for m in selected_metrics:
                    role = "primary" if m == primary_metric else "soft_monitoring"
                    cur.execute(
                        """
                        INSERT INTO experiment_metrics (experiment_id, name, role)
                        VALUES (?, ?, ?)
                        """,
                        (exp_id, m, role),
                    )
                conn.commit()
                conn.close()
                return redirect(url_for("results"))

            # For action=plan, just re-render setup with plan summary
            return render_template(
                "configure_experiment.html",
                content_template="form.html",
                plan_summary=plan_summary,
                primary_metric=primary_metric,
                selected_metrics=selected_metrics,
                alpha=alpha,
                power=power,
                mde_percent=mde_percent,
                allocation_ratio=allocation_ratio,
                daily_per_variant=daily_per_variant,
                show_agents=True,
            )

        # GET: initial load with defaults
        # Pre-fill baseline traffic using A/A-derived estimate so duration matches demo by default
        baseline_rate, aa_daily_per_variant = get_recent_baseline_and_volume("quality_ratio", days=7)
        return render_template(
            "configure_experiment.html",
            content_template="form.html",
            plan_summary=None,
            primary_metric="quality_ratio",
            selected_metrics=["quality_ratio", "resolved_ratio"],
            alpha=0.05,
            power=0.8,
            mde_percent=5.0,
            allocation_ratio=0.5,
            daily_per_variant=aa_daily_per_variant,
            show_agents=True,
        )

    @app.route("/results")
    def results():
        # Experiment days start from day 1 (which is data day 8, after 7-day A/A warmup)
        # User navigates by experiment day (1, 2, 3...), internally we map to data days (8, 9, 10...)
        from demos.agent_sessions.agent_sessions_loader import load_agent_sessions

        df_sessions_all = load_agent_sessions()
        unique_days = sorted(df_sessions_all["day"].unique()) if not df_sessions_all.empty else []

        day_param = request.args.get("day")
        date_param = request.args.get("date")
        
        # A/A warmup is 7 days (data days 1-7), experiment starts at data day 8
        AA_WARMUP_DAYS = 7

        # If a specific date is provided, map it to the closest experiment day
        if date_param:
            try:
                from datetime import date as _date

                target = _date.fromisoformat(date_param)
                # Find the first data day >= target; if none, use last day.
                if unique_days:
                    chosen = None
                    for d in unique_days:
                        if d >= target:
                            chosen = d
                            break
                    if chosen is None:
                        chosen = unique_days[-1]
                    data_day_index = unique_days.index(chosen) + 1
                    # Convert to experiment day (data_day 8 = experiment day 1)
                    experiment_day_index = max(1, data_day_index - AA_WARMUP_DAYS)
                else:
                    experiment_day_index = 1
            except Exception:
                # Default to last experiment day
                experiment_day_index = max(1, len(unique_days) - AA_WARMUP_DAYS)
        else:
            # Fall back to explicit experiment day if provided
            if day_param is None:
                # Default to experiment day 1 (data day 8)
                experiment_day_index = 1
            else:
                try:
                    experiment_day_index = int(day_param)
                except ValueError:
                    experiment_day_index = 1

        # Calculate total experiment days (total data days - warmup days)
        total_experiment_days = max(0, len(unique_days) - AA_WARMUP_DAYS)
        
        # Clamp experiment_day_index to valid range [1, total_experiment_days]
        if total_experiment_days > 0:
            experiment_day_index = max(1, min(experiment_day_index, total_experiment_days))
        else:
            experiment_day_index = 1
        
        # Convert experiment day back to data day for actual data lookup
        data_day_index = experiment_day_index + AA_WARMUP_DAYS
        
        if not unique_days:
            selected_day = None
            today_str = "N/A"
        else:
            # Ensure data_day_index is within bounds
            data_day_index = max(1, min(data_day_index, len(unique_days)))
            selected_day = unique_days[data_day_index - 1]
            today_str = selected_day.isoformat()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM experiments WHERE status = 'running' ORDER BY created_at DESC LIMIT 1"
        )
        exp = cur.fetchone()
        metrics = []
        if exp:
            cur.execute(
                "SELECT * FROM experiment_metrics WHERE experiment_id = ?",
                (exp["id"],),
            )
            metrics = cur.fetchall()
        conn.close()

        # Build ABTest on recent agent sessions similar to demo_agent_quality_vs_resolution
        metric_cards = []
        abtest_results = None
        current_total_n = None
        sample_ok = None
        days_ok = None
        stop_recommended = False
        # Human-readable label for the randomization unit (e.g. "conversations").
        primary_unit_label = "conversations"
        
        # Historical data for graphs: compute metrics for each day from 8 to current
        historical_data = []
        srm_history = []  # Track SRM over time for visualization
        if exp and metrics:
            # Load user/variant mapping using a 7-day window ending at selected_day
            df_conv = get_recent_user_variant_df(days=7, end_day=selected_day)
            if not df_conv.empty:
                # Join with full session data to bring metric columns
                df_sessions = df_sessions_all.copy()
                if not df_sessions.empty:
                    # Filter sessions up to selected_day (cumulative experiment timeline)
                    if selected_day is not None and "day" in df_sessions.columns:
                        df_sessions = df_sessions[df_sessions["day"] <= selected_day]

                    df = df_sessions.merge(df_conv, on="conversation_id", how="inner")
                    df["user_id"] = df["conversation_id"]

                    print("\n" + "-" * 70)
                    print("WEBAPP RESULTS - BUILDING ABTEST FROM RECENT SESSIONS")
                    print("Primary metric:", exp["primary_metric"])
                    print("Metrics:", [m["name"] for m in metrics])
                    print("Sample size (rows):", len(df))
                    print("-" * 70)

                    test = ABTest(
                        name="webapp_agent_quality_vs_resolution",
                        data=df,
                        variant_col="variant",
                        unit_id="user_id",
                        alpha=exp["alpha"],
                        timestamp=today_str,
                    )

                    # Define metrics like in demo: quality_rate (primary), resolved_rate (monitor)
                    @test.metric(
                        metric_type="proportion",
                        is_primary=True,
                        monitor_alpha=exp["alpha"],
                        monitor_power=exp["power"],
                    )
                    def quality_ratio(data):
                        return data.groupby("user_id")["quality"].max()

                    @test.metric(
                        metric_type="proportion",
                        inferiority_margin=0.02,
                        monitor_alpha=exp["alpha"],
                        monitor_power=exp["power"],
                    )
                    def resolved_ratio(data):
                        return data.groupby("user_id")["resolved"].max()

                    abtest_results = test.analyze(run_srm_check=True, correction=None)

                    print(abtest_results.summary())
                    print("\nSOFT MONITORING DECISION:")
                    print(abtest_results.decision_soft_monitoring())
                    
                    # Extract SRM results and convert numpy types for JSON serialization
                    srm_result = abtest_results.srm_result if hasattr(abtest_results, 'srm_result') else None
                    if srm_result:
                        # Convert numpy types to Python native types
                        srm_result = {
                            "passed": bool(srm_result.get("passed", True)),
                            "p_value": float(srm_result.get("p_value", 1.0)) if srm_result.get("p_value") is not None else None,
                            "chi2_stat": float(srm_result.get("chi2_stat", 0.0)) if srm_result.get("chi2_stat") is not None else None,
                            "observed": {k: int(v) for k, v in srm_result.get("observed", {}).items()},
                            "expected": {k: float(v) for k, v in srm_result.get("expected", {}).items()}
                        }

                    # Map ABTest metric_results into metric_cards for UI.
                    # ABTest uses metric IDs based on the function names defined above:
                    #   quality_ratio -> "quality_ratio"
                    #   resolved_ratio -> "resolved_ratio"
                    for m in metrics:
                        metric_id = m["name"]
                        role = m["role"]

                        res = abtest_results.metric_results[metric_id]
                        control_value = res["control_value"]
                        treatment_value = res["treatment_value"]
                        lift = treatment_value - control_value
                        p_value = res["p_value"]
                        std_control = res.get("std_control")
                        std_treatment = res.get("std_treatment")
                        # CI-like half-widths for visualization.
                        # Prefer 95% CI using n when available; otherwise fall back to 1*std.
                        control_n = res.get("sample_size_control")
                        treatment_n = res.get("sample_size_treatment")
                        ci95_control = None
                        ci95_treatment = None
                        z = 1.96
                        if std_control is not None:
                            if control_n and control_n > 0:
                                ci95_control = z * std_control / (control_n ** 0.5)
                            else:
                                ci95_control = std_control
                        if std_treatment is not None:
                            if treatment_n and treatment_n > 0:
                                ci95_treatment = z * std_treatment / (treatment_n ** 0.5)
                            else:
                                ci95_treatment = std_treatment
                        # 95% CI for the difference in means/proportions (treatment - control)
                        ci_diff_lower = res.get("ci_lower_diff")
                        ci_diff_upper = res.get("ci_upper_diff")
                        if ci_diff_lower is None or ci_diff_upper is None:
                            # Fallback: symmetric CI using std errors if backend didn't provide bounds
                            se_diff = None
                            if std_control is not None and std_treatment is not None and control_n and treatment_n and control_n > 0 and treatment_n > 0:
                                se_diff = (std_control**2 / control_n + std_treatment**2 / treatment_n) ** 0.5
                            if se_diff is not None:
                                ci_diff_lower = lift - z * se_diff
                                ci_diff_upper = lift + z * se_diff
                        alpha = res.get("alpha", exp["alpha"] if exp else 0.05)
                        significant = res["significant"]
                        status = "green" if significant and lift >= 0 else "red" if significant and lift < 0 else "grey"

                        metric_cards.append(
                            {
                                "name": metric_id,
                                "role": role,
                                "control_value": control_value,
                                "treatment_value": treatment_value,
                                "lift": lift,
                                "p_value": p_value,
                                "std_control": std_control,
                                "std_treatment": std_treatment,
                                "ci95_control": ci95_control,
                                "ci95_treatment": ci95_treatment,
                                "ci_diff_lower": ci_diff_lower,
                                "ci_diff_upper": ci_diff_upper,
                                "alpha": alpha,
                                "status": status,
                            }
                        )
                        print(metric_id, "ci95_control", ci95_control, "ci95_treatment", ci95_treatment)

        # Compute historical metrics for graphing (experiment days 1 through current)
        if exp and metrics and experiment_day_index and experiment_day_index >= 1:
            print(f"\n🔄 Computing historical data for days 1 to {experiment_day_index}")
            for exp_day_idx in range(1, experiment_day_index + 1):
                hist_data_day_idx = exp_day_idx + AA_WARMUP_DAYS
                if hist_data_day_idx > len(unique_days):
                    print(f"  ⏭️ Skipping day {exp_day_idx}: data day {hist_data_day_idx} > {len(unique_days)} total days")
                    break
                hist_day = unique_days[hist_data_day_idx - 1]
                print(f"  📅 Processing day {exp_day_idx} (data day {hist_data_day_idx}, date {hist_day})")
                
                # Load data for this specific day
                df_conv_hist = get_recent_user_variant_df(days=7, end_day=hist_day)
                print(f"    📊 Loaded {len(df_conv_hist)} conversations from variant mapping")
                if not df_conv_hist.empty:
                    df_sessions_hist = df_sessions_all.copy()
                    if not df_sessions_hist.empty and "day" in df_sessions_hist.columns:
                        df_sessions_hist = df_sessions_hist[df_sessions_hist["day"] <= hist_day]
                        df_hist = df_sessions_hist.merge(df_conv_hist, on="conversation_id", how="inner")
                        df_hist["user_id"] = df_hist["conversation_id"]
                        print(f"    ✅ Merged data: {len(df_hist)} rows, {len(df_hist['user_id'].unique())} unique users")
                        
                        test_hist = ABTest(
                            name="webapp_historical",
                            data=df_hist,
                            variant_col="variant",
                            unit_id="user_id",
                            alpha=exp["alpha"],
                            timestamp=hist_day.isoformat(),
                        )
                        
                        @test_hist.metric(metric_type="proportion", is_primary=True)
                        def quality_ratio(data):
                            return data.groupby("user_id")["quality"].max()
                        
                        @test_hist.metric(metric_type="proportion")
                        def resolved_ratio(data):
                            return data.groupby("user_id")["resolved"].max()
                        
                        try:
                            results_hist = test_hist.analyze(run_srm_check=False, correction=None)
                            day_data = {"day": exp_day_idx, "experiment_day": exp_day_idx, "metrics": {}}
                            
                            for m in metrics:
                                metric_id = m["name"]
                                if metric_id in results_hist.metric_results:
                                    res_hist = results_hist.metric_results[metric_id]
                                    # Convert numpy types to Python native types for JSON serialization
                                    day_data["metrics"][metric_id] = {
                                        "control": float(res_hist["control_value"]) if res_hist["control_value"] is not None else None,
                                        "treatment": float(res_hist["treatment_value"]) if res_hist["treatment_value"] is not None else None,
                                        "p_value": float(res_hist["p_value"]) if res_hist["p_value"] is not None else None,
                                        "significant": bool(res_hist["significant"]) if res_hist["significant"] is not None else False
                                    }
                            
                            historical_data.append(day_data)
                            
                            # Calculate SRM statistics for this day
                            # Debug: Check what variant values exist
                            variant_counts = df_hist["variant"].value_counts()
                            print(f"    🔍 Variant distribution: {dict(variant_counts)}")
                            
                            # The variant column might use different naming (A/B, control/treatment, original/b_agent)
                            # Map to control/treatment based on actual values
                            unique_variants = df_hist["variant"].unique()
                            if len(unique_variants) == 2:
                                # Assume alphabetical order: first is control, second is treatment
                                variant_list = sorted(unique_variants)
                                control_variant = variant_list[0]
                                treatment_variant = variant_list[1]
                                print(f"    🏷️ Mapping: '{control_variant}' -> Control, '{treatment_variant}' -> Treatment")
                                
                                n_control = len(df_hist[df_hist["variant"] == control_variant]["user_id"].unique())
                                n_treatment = len(df_hist[df_hist["variant"] == treatment_variant]["user_id"].unique())
                            else:
                                # Fallback to looking for known variant names
                                n_control = len(df_hist[df_hist["variant"].isin(["control", "A", "original"])]["user_id"].unique())
                                n_treatment = len(df_hist[df_hist["variant"].isin(["treatment", "B", "b_agent"])]["user_id"].unique())
                            
                            n_total = n_control + n_treatment
                            print(f"    👥 Sample sizes: Control={n_control}, Treatment={n_treatment}, Total={n_total}")
                            
                            if n_total > 0 and n_control > 0:
                                # Observed treatment-to-control ratio
                                observed_tc = n_treatment / n_control
                                
                                # Expected allocation (from experiment config)
                                allocation_ratio = exp["allocation_ratio"] if exp["allocation_ratio"] is not None else 0.5
                                expected_tc = allocation_ratio / (1 - allocation_ratio)
                                
                                # Calculate confidence interval for T/C ratio
                                # Using formula from SRM tool: CI = (x/(n-x)) ± z * sqrt(p / (n*(1-p)^3))
                                alpha_srm = 0.0005  # Conservative alpha for SRM
                                z = 3.481  # z_{1-α/2} for α=0.0005
                                p = allocation_ratio
                                std_err = math.sqrt(p / (n_total * (1 - p)**3))
                                ci_lower = observed_tc - z * std_err
                                ci_upper = observed_tc + z * std_err
                                
                                # SRM detected if expected ratio not in CI
                                srm_detected = not (ci_lower <= expected_tc <= ci_upper)
                                
                                srm_history.append({
                                    "day": exp_day_idx,
                                    "observed_tc": float(observed_tc),
                                    "expected_tc": float(expected_tc),
                                    "ci_lower": float(ci_lower),
                                    "ci_upper": float(ci_upper),
                                    "srm_detected": bool(srm_detected),
                                    "n_control": int(n_control),
                                    "n_treatment": int(n_treatment),
                                    "n_total": int(n_total)
                                })
                                print(f"    📈 SRM data added: T/C={observed_tc:.3f}, expected={expected_tc:.3f}, SRM={'YES' if srm_detected else 'NO'}")
                            else:
                                print(f"    ⚠️ Skipping SRM calculation: n_total={n_total}, n_control={n_control}")
                        except Exception as e:
                            print(f"    ❌ Error computing historical data for day {exp_day_idx}: {e}")
                            traceback.print_exc()
                else:
                    print(f"    ⚠️ No variant mapping data for day {exp_day_idx}")
        
        # Debug: Print SRM history
        if srm_history:
            print(f"\n📊 SRM History generated: {len(srm_history)} days")
            for srm_day in srm_history:
                status = "❌ SRM" if srm_day['srm_detected'] else "✅ OK"
                print(f"  Day {srm_day['day']}: T/C={srm_day['observed_tc']:.3f} (expected={srm_day['expected_tc']:.3f}) {status}")
        else:
            print("\n⚠️ No SRM history data generated")

        # Logging similar to demos: results route summary
        try:
            print("\n" + "=" * 70)
            print("RESULTS SUMMARY (webapp)")
            print("=" * 70)
            if exp:
                print(
                    f"Experiment: {exp['name']} | Status: {exp['status']} | Primary: {exp['primary_metric']}"
                )
                print(f"Alpha: {exp['alpha']} | Power: {exp['power']}")
            print(f"Today: {today_str}")
            if abtest_results is not None and "quality_ratio" in abtest_results.metric_results:
                q_res = abtest_results.metric_results["quality_ratio"]
                total_n = q_res.get("sample_size_control", 0) + q_res.get("sample_size_treatment", 0)
                current_total_n = total_n
                primary_unit_label = getattr(abtest_results, "unit_id", "conversations")
                print(
                    f"Sample size used (primary): total={total_n}, "
                    f"control={q_res.get('sample_size_control', 0)}, treatment={q_res.get('sample_size_treatment', 0)}"
                )

                # Compare against planned sample size if available (per variant)
                if exp and exp["planned_per_variant"]:
                    planned_per_variant = exp["planned_per_variant"]
                    sample_ok = total_n >= 2 * planned_per_variant

            # Compare current experiment day against planned duration (in days)
            if exp and exp["planned_days"] and experiment_day_index:
                planned_days = exp["planned_days"]
                days_ok = experiment_day_index >= planned_days
            # Overall stop recommendation: default is to continue; only
            # recommend stop when all available plans are satisfied.
            if exp:
                has_sample_plan = exp["planned_per_variant"] is not None
                has_days_plan = exp["planned_days"] is not None
                if has_sample_plan and has_days_plan:
                    stop_recommended = bool(sample_ok and days_ok)
                elif has_sample_plan:
                    stop_recommended = bool(sample_ok)
                elif has_days_plan:
                    stop_recommended = bool(days_ok)
            for card in metric_cards:
                sig = (
                    "SIG"
                    if card.get("p_value", 1.0) < card.get("alpha", 0.05)
                    else "NOT-SIG"
                )
                print(
                    f"- {card['name']} ({card['role']}): control={card['control_value']:.3f}, "
                    f"treatment={card['treatment_value']:.3f}, lift={card['lift']*100:.1f}%, "
                    f"p={card['p_value']:.3f} [{sig}]"
                )
        except Exception as e:
            traceback.print_exc()
            pass

        # Sort metric_cards to show primary metric first
        metric_cards_sorted = sorted(metric_cards, key=lambda x: (x["role"] != "primary", x["name"]))

        return render_template(
            "results.html",
            experiment=exp,
            metric_cards=metric_cards_sorted,
            today=today_str,
            today_str=today_str,  # Add today_str for navigator
            day_index=experiment_day_index,  # Now using experiment days (1, 2, 3...)
            total_days=total_experiment_days,  # Total experiment days, not data days
            current_total_n=current_total_n,
            primary_unit_label=primary_unit_label,
            sample_ok=sample_ok,
            days_ok=days_ok,
            show_agents=True,
            stop_recommended=stop_recommended,
            historical_data=historical_data,  # Pass historical data for graphs
            srm_result=srm_result if 'srm_result' in locals() else None,  # Pass SRM check result
            srm_history=srm_history,  # Pass SRM history for time-series visualization
        )

    @app.route("/stop_experiment", methods=["POST"])
    def stop_experiment():
        """Allow the user to manually stop the latest running experiment."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM experiments WHERE status = 'running' ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE experiments SET status = 'completed' WHERE id = ?",
                (row["id"],),
            )
            conn.commit()
        conn.close()
        return redirect(url_for("results"))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
