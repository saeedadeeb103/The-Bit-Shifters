import os
import logging
from datetime import datetime, timedelta

import duckdb
import pandas as pd
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
app = Flask(__name__)
app.secret_key = "11323424"  # change this for security

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# 1. CONFIG & GLOBALS
# --------------------------------------------------------------------
DUCKDB_PATH = "databases/user_cluster.duckdb"  # Persistent database file
OPERATOR_DUCKDB_PATH = "databases/operator_cluster.duckdb"
PARQUET_FILE = "customer_data_last_7_days.parquet"
OPERATOR_PARQUET_FILE = "operator_data_last_7_days.parquet"
DML_TYPES = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']

def _get_user_data():
    user_table = f"user_{current_user.id}"
    
    # Check if table exists
    tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
    if user_table not in tables:
        return None
    
    # fetch and clean data
    df = conn.execute(f"SELECT * FROM {user_table}").fetchdf()
    df = df.replace({np.nan: None})
    
    return find_stable_queries_for_user(df)

# initialize DuckDB
conn = duckdb.connect(database=DUCKDB_PATH, read_only=False)
conn_operator = duckdb.connect(database=OPERATOR_DUCKDB_PATH, read_only=False)

# setup Flask-Login
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# --------------------------------------------------------------------
# 2. USER AUTHENTICATION MODEL
# --------------------------------------------------------------------

@app.route("/api/check-auth")
@login_required
def check_auth():
    return jsonify({"status": "authenticated"})

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("admin")
class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id
        self.username = str(user_id)

    @staticmethod
    def get(user_id):
        """Retrieve user if they exist in DuckDB tables"""

        if user_id == "admin":  # Special case for admin
            return User(user_id)
        
        tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
        user_table = f"user_{user_id}"
        return User(user_id) if user_table in tables else None


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # check if it's the admin login
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            # create a special admin user object
            admin_user = User(user_id="admin")
            login_user(admin_user)
            flash("Admin login successful!", "success")
            return redirect(url_for("admin_dashboard"))


        elif username == password:  # password = user_id for simplicity
            user = User.get(username)
            if user:
                login_user(user)
                flash("Login successful!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid credentials or user does not exist.", "danger")
        else:
            flash("Incorrect password.", "danger")

    return render_template("login.html")


@app.route("/admin-dashboard")
@login_required
def admin_dashboard():
    if current_user.id != "admin":
        flash("Access denied. You are not authorized to view this page.", "danger")
        return redirect(url_for("dashboard"))
    
    try:
        operator_data = conn_operator.execute("SELECT * FROM logs").fetchdf()
        metrics = compute_operator_metrics(operator_data)
        return render_template("admin_dashboard.html", metrics=metrics)
    except Exception as e:
        flash(f"Error fetching operator data: {str(e)}", "danger")
        return redirect(url_for("dashboard"))

def compute_operator_metrics(operator_data):
    """Compute metrics for the operator dashboard handling missing cluster_size."""
    metrics = {
        "idle_time_per_instance": {},
        "total_concurrency_per_instance": {},  
        "instance_utilization": {},
        "utilization_over_time": {},
        "slowdowns_due_to_concurrency": {}, 
        "oversubscribed_hours": {}
    }

    if operator_data.empty:
        return metrics

    try:
        operator_data["arrival_timestamp"] = pd.to_datetime(
            operator_data["arrival_timestamp"], 
            errors="coerce",
            format="ISO8601" 
        )
        operator_data = operator_data.dropna(subset=["arrival_timestamp"])
        operator_data["hour_bin"] = operator_data["arrival_timestamp"].dt.floor('h')
        operator_data["time_bin"] = operator_data["arrival_timestamp"].dt.floor('1s')
        
        # compute concurrency per second
        cluster_concurrency = operator_data.groupby("time_bin").size().reset_index(name="cluster_concurrency")
        operator_data = operator_data.merge(cluster_concurrency, on="time_bin", how="left")

        # estimate missing cluster_size using max observed concurrency
        operator_data["estimated_cluster_size"] = operator_data.groupby("instance_id")["cluster_concurrency"].transform("max")

        # use estimated values where cluster_size is NaN
        operator_data["effective_cluster_size"] = operator_data["cluster_size"].fillna(operator_data["estimated_cluster_size"])

        # avoid division by zero
        operator_data.loc[operator_data["effective_cluster_size"] == 0, "effective_cluster_size"] = np.nan

        # compute per-instance metrics
        instance_metrics = operator_data.groupby("instance_id").agg(
            total_concurrency=("cluster_concurrency", "sum"),
            utilization=("cluster_concurrency", lambda x: (x.mean() / operator_data.loc[x.index[0], "effective_cluster_size"]) * 100),
            idle_time=("arrival_timestamp", lambda x: x.diff().fillna(pd.Timedelta(0)).mean().total_seconds())
        ).reset_index()

        metrics["total_concurrency_per_instance"] = instance_metrics.set_index("instance_id")["total_concurrency"].to_dict()
        metrics["instance_utilization"] = instance_metrics.set_index("instance_id")["utilization"].round(2).to_dict()
        metrics["idle_time_per_instance"] = instance_metrics.set_index("instance_id")["idle_time"].to_dict()

        # compute utilization over time
        utilization = operator_data.groupby("hour_bin").size().fillna(0)
        metrics["utilization_over_time"] = {int(ts.timestamp()): count for ts, count in utilization.items()}

        # compute oversubscription using execution duration percentiles
        operator_data["total_duration"] = (
            operator_data["compile_duration_ms"] + 
            operator_data["execution_duration_ms"] + 
            operator_data["queue_duration_ms"]
        )

        peak_threshold = operator_data["total_duration"].quantile(0.95)
        operator_data["oversubscribed"] = operator_data["total_duration"] > peak_threshold

        oversubscription_trend = operator_data.groupby("hour_bin").agg(
            oversubscribed_queries=("oversubscribed", "sum"),
            total_queries=("query_id", "count")  # Count total queries per hour
        ).reset_index()

        oversubscription_trend["oversubscription_ratio"] = (
            oversubscription_trend["oversubscribed_queries"] /
            oversubscription_trend["total_queries"]
        ).fillna(0)  # Avoid division by zero

        metrics["oversubscribed_hours"] = {
            int(ts.timestamp()): round(ratio, 4)
            for ts, ratio in zip(oversubscription_trend["hour_bin"], oversubscription_trend["oversubscription_ratio"])
        }

        # Per-instance Utilization Over Time
        cluster_utilization = operator_data.groupby(["instance_id", "hour_bin"]).agg(
            query_count=("arrival_timestamp", "size"),
            effective_cluster_size=("effective_cluster_size", "max")
        ).reset_index()

        cluster_utilization["utilization"] = (
            cluster_utilization["query_count"] / cluster_utilization["effective_cluster_size"] * 100
        )

        # Store per-instance utilization over time
        metrics["utilization_over_time"] = {}
        for _, row in cluster_utilization.iterrows():
            ts = int(row["hour_bin"].timestamp())
            cluster = str(row["instance_id"])
            utilization = round(row["utilization"], 2)

            if ts not in metrics["utilization_over_time"]:
                metrics["utilization_over_time"][ts] = {}

            metrics["utilization_over_time"][ts][cluster] = utilization

        # Detect slowdowns due to concurrency
        slowdowns = operator_data.groupby("instance_id").apply(lambda group: calculate_correlation(
            group["execution_duration_ms"], group["cluster_concurrency"]
        ))

        metrics["slowdowns_due_to_concurrency"] = slowdowns.dropna().to_dict()

    except Exception as e:
        logger.error(f"Metric computation error: {str(e)}")

    return metrics




def calculate_correlation(x, y):
    """Calculate correlation safely, handling edge cases."""
    if len(x) < 2 or len(y) < 2:
        return 0  # Not enough data for correlation
    x = x.dropna()
    y = y.dropna()
    if len(x) != len(y):
        return 0  # Mismatched lengths
    std_x = x.std()
    std_y = y.std()
    if std_x == 0 or std_y == 0:
        return 0  # Avoid division by zero
    return x.corr(y)

from flask import session

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# --------------------------------------------------------------------
# 3. STABLE QUERIES DETECTION
# --------------------------------------------------------------------
def find_stable_queries_for_user(df_user: pd.DataFrame) -> pd.DataFrame:
    """
    Identify stable queries and add a 'stable' boolean column to the DataFrame.
    Returns the modified DataFrame with additional 'stable' column.
    """
    df_user["stable"] = False  # Initialize all as unstable
    
    if df_user.empty or "feature_fingerprint" not in df_user.columns:
        return df_user

    # Convert and sort timestamps
    df_user["arrival_timestamp"] = pd.to_datetime(df_user["arrival_timestamp"], errors="coerce")
    df_user.sort_values("arrival_timestamp", inplace=True)

    # Identify DML operations
    df_user["is_dml"] = df_user["query_type"].isin(DML_TYPES)

    # Group by query fingerprints
    grouped = df_user.groupby("feature_fingerprint", dropna=True)

    for fingerprint, group_df in grouped:
        # Skip groups with only DML operations
        if group_df["is_dml"].all():
            continue

        # Skip groups with less than 2 occurrences
        if len(group_df) < 2:
            continue

        first_time = group_df["arrival_timestamp"].iloc[0]
        last_time = group_df["arrival_timestamp"].iloc[-1]

        # Get tables read by this query pattern
        read_tables = set()
        if "read_table_ids" in group_df.columns:
            for tables in group_df["read_table_ids"].dropna():
                cleaned = [t.strip().replace("'", "") for t in str(tables).strip("[]").split(",")]
                read_tables.update(cleaned)

        # Find conflicting DML operations
        dml_in_range = df_user[
            df_user["is_dml"] &
            (df_user["arrival_timestamp"] >= first_time) &
            (df_user["arrival_timestamp"] <= last_time)
        ]

        # Check for table conflicts
        conflict_found = False
        for _, dml_row in dml_in_range.iterrows():
            dml_tables = [t.strip().replace("'", "") 
                         for t in str(dml_row.get("write_table_ids", "")).strip("[]").split(",")]
            if any(table in read_tables for table in dml_tables):
                conflict_found = True
                break

        # Mark stable queries if no conflicts found
        if not conflict_found:
            stable_indices = group_df[~group_df["is_dml"]].index
            df_user.loc[stable_indices, "stable"] = True

    return df_user


# --------------------------------------------------------------------
# 4. FLASK ROUTES
# --------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    return render_template("test.html", username=current_user.username)

import numpy as np
@app.route("/api/user-data")
@login_required
def get_user_data():
    """Fetch complete user data with stability status."""
    processed_data = _get_user_data()
    
    if processed_data is None:
        return jsonify({"error": "No data found"}), 404
        
    return jsonify({
        "user_id": current_user.id,
        "data": processed_data.to_dict(orient="records")
    })



@app.route("/api/stable-data")
@login_required
def get_stable_data():
    """Fetch only stable queries from user data."""
    processed_data = _get_user_data()
    
    if processed_data is None:
        return jsonify([])

    try:
        stable_df = processed_data[processed_data["stable"]]
        print(f"✅ Found {len(stable_df)} stable queries for user {current_user.id}")
        return jsonify(stable_df.to_dict(orient="records"))
    
    except Exception as e:
        print(f"❌ Error filtering stable queries: {str(e)}")
        return jsonify({"error": str(e)}), 500



@app.route("/api/alerts")
@login_required
def get_degradation_alerts():
    """Fetch performance degradation alerts for the logged-in user's stable queries."""
    user_table = f"user_table_{current_user.id}"

    tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
    if user_table not in tables:
        return jsonify([])

    df_stable = conn.execute(f"SELECT * FROM {user_table}").fetchdf()
    df_stable = find_stable_queries_for_user(df_stable)

    return jsonify(check_performance_degradation(df_stable) if not df_stable.empty else [])


# --------------------------------------------------------------------
# 5. PERFORMANCE CHECK
# --------------------------------------------------------------------
def check_performance_degradation(df_stable: pd.DataFrame):
    """Detects performance degradation using execution time trends."""
    if df_stable.empty:
        return []

    df_stable["arrival_timestamp"] = pd.to_datetime(df_stable["arrival_timestamp"], errors="coerce")
    latest_time = df_stable["arrival_timestamp"].max()

    recent_start = latest_time - timedelta(hours=24)
    historical_start = recent_start - timedelta(days=7)

    alerts = []
    grouped = df_stable.groupby("feature_fingerprint")

    for fingerprint, group in grouped:
        recent = group[group["arrival_timestamp"] >= recent_start]
        historical = group[
            (group["arrival_timestamp"] >= historical_start) & (group["arrival_timestamp"] < recent_start)
        ]

        if len(recent) < 5 or len(historical) < 20:
            continue

        hist_mean, hist_std = historical["execution_duration_ms"].mean(), historical["execution_duration_ms"].std()
        recent_mean = recent["execution_duration_ms"].mean()

        zscore = (recent_mean - hist_mean) / hist_std
        if zscore > 2:
            alerts.append({
                "fingerprint": fingerprint,
                "degradation_percentage": round((recent_mean - hist_mean) / hist_mean * 100, 2)
            })

    return alerts

def setup_db():
    """Loads data from Parquet and creates user-specific tables and operator_data table if they don't already exist."""
    if not os.path.exists(DUCKDB_PATH):
        logger.warning(f"DuckDB database file '{DUCKDB_PATH}' not found. Skipping setup.")
        return

    # Load customer data
    if not os.path.exists(PARQUET_FILE):
        logger.warning(f"Parquet file '{PARQUET_FILE}' not found. No customer data to load.")
    else:
        df_all = pd.read_parquet(PARQUET_FILE, engine="pyarrow")  # Ensure Parquet compatibility
        if df_all.empty:
            logger.warning("Customer Parquet file is empty, skipping table creation.")
        else:
            if "user_id" not in df_all.columns:
                logger.warning("No 'user_id' column found in customer Parquet file.")
            else:
                # Fetch existing tables in the database
                existing_tables = {t[0] for t in conn.execute("SHOW TABLES").fetchall()}

                for uid in df_all["user_id"].dropna().unique():
                    uid = int(uid)  # Convert numpy.int64 to Python int
                    user_table = f"user_table_{uid}"

                    if user_table in existing_tables:
                        logger.info(f"Table '{user_table}' already exists. Skipping creation.")
                        continue  # Skip if the table is already present

                    conn.execute(f"CREATE TABLE {user_table} AS SELECT * FROM df_all WHERE user_id = {uid}")
                    logger.info(f"Created table '{user_table}' for user_id {uid}")

    # Load operator data
    if not os.path.exists(OPERATOR_PARQUET_FILE):
        logger.warning(f"Parquet file '{OPERATOR_PARQUET_FILE}' not found. No operator data to load.")
    else:
        df_operator = pd.read_parquet(OPERATOR_PARQUET_FILE, engine="pyarrow")
        if df_operator.empty:
            logger.warning("Operator Parquet file is empty, skipping table creation.")
        else:
            # Re-fetch existing tables to include any new ones created above (optional, based on needs)
            existing_tables = {t[0] for t in conn.execute("SHOW TABLES").fetchall()}
            operator_table = "operator_data"
            
            if operator_table in existing_tables:
                logger.info(f"Table '{operator_table}' already exists. Skipping creation.")
            else:
                conn.execute(f"CREATE TABLE {operator_table} AS SELECT * FROM df_operator")
                logger.info(f"Created table '{operator_table}'")


# --------------------------------------------------------------------
# 6. MAIN
# --------------------------------------------------------------------

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)  # Sessions last 1 day
if __name__ == "__main__":
    # setup_db()
    app.run(debug=True)
