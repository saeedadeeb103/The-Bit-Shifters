import s3fs
import pyarrow.parquet as pq
import duckdb
import pandas as pd
from sqlalchemy import create_engine
import os
from config import StorageSettings

class ClusterDatabase:
    def __init__(self, bucket: str, file_path: str, db_type: str = "duckdb"):
        """
        Initializes the downloader.
        :param bucket: S3 bucket name.
        :param file_path: S3 file path to Redset dataset.
        :param db_type: Storage choice ("duckdb", "postgres", "parquet").
        """
        self.s3_bucket = bucket
        self.file_path = file_path
        self.local_parquet_path = StorageSettings.PARQUET_FILE_PATH


    def download_redset_from_s3(self, force: bool = False):
        """Downloads the full Redset Parquet file from S3."""
        print("Fetching Redset Parquet file from S3...")
        if not os.path.exists(self.local_parquet_path) or force:  
            print("Starting download: ...")         
            s3 = s3fs.S3FileSystem(anon=True)
            s3_path = f"s3://{self.s3_bucket}/{self.file_path}"
            s3.get(s3_path, self.local_parquet_path)
            print("Download completed: ", self.local_parquet_path)
        else:
            print("Parquet file already exists locally: ", self.local_parquet_path)


    def convert_parquet_to_duckdb(self, force: bool = False):
        """Converts the redset parquet file to a DuckDB file."""
        print("Converting Parquet file to DuckDB...")
        
        # Exit function immediately if DuckDB file already exists
        if os.path.exists(StorageSettings.DUCKDB_FILE_PATH) and not force:
            print("DuckDB file already exists. Skipping conversion.")
            return
        
        # Convert Parquet to DuckDB     
        table = pq.ParquetDataset(self.local_parquet_path)
        df = table.read().to_pandas()
        cluster_dfs = self.extract_cluster_logs(df)
        self.store_to_duckdb(cluster_dfs)


    def extract_cluster_logs(self, df: pd.DataFrame):
        """
        Extracts log entries for a specific cluster and sorts them by arrival_timestamp.
        :param cluster_id: The cluster ID to filter logs.
        :return: Filtered and sorted DataFrame
        """
        cluster_dfs = {}  # Dictionary to hold dataframes per cluster
        
        for cluster_id in df["instance_id"].unique():
            cluster_df = df[df["instance_id"] == cluster_id].sort_values(by="arrival_timestamp")
            cluster_dfs[cluster_id] = cluster_df
        
        return cluster_dfs


    def store_to_duckdb(self, cluster_dfs: dict):
        """Stores all extracted logs in a single DuckDB file, using one connection."""

        os.makedirs(StorageSettings.DATABASE_FOLDER, exist_ok=True)

        try:
            # Open a single connection for all writes
            con = duckdb.connect(StorageSettings.DUCKDB_FILE_PATH, read_only=False)

            for instance_id, df in cluster_dfs.items():
                if df is not None:
                    #df = df.drop(columns=["instance_id"], errors="ignore")
                    table_name = f"logs_instance_{instance_id}"

                    # Register DataFrame to DuckDB
                    con.register("temp_df", df)

                    # Create or update logs table for the instance
                    con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM temp_df")

                    print(f"Instance {instance_id} logs stored in DuckDB (Table: {table_name}).")

            con.close()  # Ensure connection is closed once all tables are created

        except duckdb.IOException as e:
            print(f"Error accessing DuckDB file: {e}")

        finally:
            if con:
                con.close()

        
    def view_duckdb_tables():
        """View all tables in the DuckDB file."""
        con = duckdb.connect(StorageSettings.DUCKDB_FILE_PATH)
        tables = con.execute("SHOW TABLES").fetchall()
        for table in tables:
            table_name = table[0]           
            row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"Table: {table_name} ({row_count} rows)")
            # print(f"Contents of table {table_name}:")
            # result = con.execute(f"SELECT * FROM {table_name}").fetchdf()
            # print(result)
            print("\n")
        con.close()


# Example Usage
if __name__ == "__main__":
    clusterDatabase = ClusterDatabase(bucket="redshift-downloads", file_path="redset/serverless/full.parquet", db_type="duckdb")
    clusterDatabase.download_redset_from_s3()
    clusterDatabase.convert_parquet_to_duckdb()