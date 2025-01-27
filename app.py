from flask import Flask, render_template, Response, abort, request
import pandas as pd
import gzip
import io
import duckdb
from flask_caching import Cache
from datetime import datetime, timedelta
import logging

# Initialize Flask app
app = Flask(__name__)

# Configure caching
cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to load the last 3 days of data
def load_recent_data(user_id=None, query_type=None):
    parquet_file = 'customer_data_last_two_weeks.parquet'

    # Define the time range for the last 3 days
    latest_timestamp = pd.to_datetime('2024-05-30 23:59:30.255421')  # Replace with current date when needed
    three_days_ago = latest_timestamp - timedelta(days=7)
    three_days_ago_str = three_days_ago.strftime('%Y-%m-%d %H:%M:%S.%f')

    # Log the time range being queried
    logger.info(f"Fetching data from {three_days_ago_str} to {latest_timestamp}")

    # Connect to DuckDB
    conn = duckdb.connect()

    # Base query
    query = f"""
        SELECT 
            MAX(arrival_timestamp) AS arrival_timestamp,
            COALESCE(SUBSTR(feature_fingerprint, 1, 8), 'Unknown') AS short_fingerprint,
            COUNT(*) AS query_count,
            AVG(execution_duration_ms) AS avg_execution_time,
            SUM(CASE WHEN was_aborted = 1 THEN 1 ELSE 0 END) AS failure_count,
            user_id,
            query_type
        FROM read_parquet('{parquet_file}')
        WHERE arrival_timestamp IS NOT NULL 
            AND TRY_CAST(arrival_timestamp AS TIMESTAMP) IS NOT NULL
            AND arrival_timestamp >= '{three_days_ago_str}'
    """

    # Add filters for user_id and query_type if provided
    if user_id:
        user_id = user_id.replace("'", "''")  # Escape single quotes for SQL safety
        query += f" AND user_id = '{user_id}'"
    if query_type:
        query_type = query_type.replace("'", "''")  # Escape single quotes for SQL safety
        query += f" AND query_type = '{query_type}'"

    # Group by and order by
    query += """
        GROUP BY short_fingerprint, user_id, query_type
        ORDER BY query_count DESC;
    """

    # Log the constructed query for debugging
    logger.info("Constructed SQL Query:")
    logger.info(query)

    # Log invalid timestamps for debugging
    invalid_timestamps = conn.execute(f"""
        SELECT arrival_timestamp
        FROM read_parquet('{parquet_file}')
        WHERE arrival_timestamp IS NULL OR TRY_CAST(arrival_timestamp AS TIMESTAMP) IS NULL;
    """).fetchdf()

    if not invalid_timestamps.empty:
        logger.warning(f"Found {len(invalid_timestamps)} rows with invalid or empty arrival_timestamp.")
        logger.warning("Sample invalid timestamps:")
        logger.warning(invalid_timestamps.head())

    # Fetch the grouped data
    try:
        grouped_data = conn.execute(query).fetchdf()
    except Exception as e:
        logger.error(f"Error executing query: {e}", exc_info=True)
        raise

    # Log if no data is found
    if grouped_data.empty:
        logger.warning("No valid data found for the specified time range.")

    # Compress the grouped data
    csv_data = grouped_data.to_csv(index=False)
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
        f.write(csv_data.encode('utf-8'))

    return buffer.getvalue()


@app.route('/')
def home():
    """Render the dashboard homepage."""
    return render_template('dashboard.html')


@app.route('/api/data')
@cache.cached(timeout=300)  # Cache for 5 minutes
def get_data():
    """API endpoint to fetch compressed data."""
    try:
        user_id = request.args.get('user_id')
        query_type = request.args.get('query_type')
        compressed_csv = load_recent_data(user_id=user_id, query_type=query_type)
        return Response(compressed_csv, mimetype='application/gzip')
    except Exception as e:
        logger.error(f"Error loading data: {e}", exc_info=True)
        abort(500, description="Internal Server Error")


if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True)
