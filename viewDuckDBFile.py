import duckdb
import os
from config import DATABASE_FOLDER, DUCKDB_FILE_PATH
from clusterDatabase import ClusterDatabase

if __name__ == "__main__":
    ClusterDatabase.view_duckdb_tables()