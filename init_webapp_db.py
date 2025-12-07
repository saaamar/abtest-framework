"""Initialize the webapp database with required tables."""
import sqlite3
import os

DB_PATH = os.path.join("webapp", "ab_demo.db")

def init_db():
    """Create database tables if they don't exist."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        print(f"Creating tables in: {DB_PATH}")
        
        # Create experiments table
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
        print("✓ Created experiments table")
        
        # Create experiment_metrics table
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
        print("✓ Created experiment_metrics table")
        
        conn.commit()
        
        # Verify tables were created
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        print(f"\nTables in database: {tables}")
        
        if 'experiments' in tables and 'experiment_metrics' in tables:
            print("\n✅ Database initialized successfully!")
        else:
            print("\n❌ Some tables are missing!")
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
