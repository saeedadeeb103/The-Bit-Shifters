import os
import pandas as pd

class EnvironmentSettings:
    """Environment variables for libraries"""
    TCL_LIBRARY = r'C:\Users\Wilhelm Tharandt\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
    TK_LIBRARY = r'C:\Users\Wilhelm Tharandt\AppData\Local\Programs\Python\Python313\tcl\tk8.6'

class StorageSettings:
    """Storage settings for the project."""
    DATABASE_FOLDER = os.path.join(os.getcwd(), "databases")
    PARQUET_FILE_PATH = os.path.join(DATABASE_FOLDER, "full.parquet")
    DUCKDB_FILE_PATH = os.path.join(DATABASE_FOLDER, "full.duckdb")

class HypervisorSettings:
    """Settings for the hypervisor."""
    DATA_UPDATE_FREQUENCY = 1 # Frequency in Hertz
    MAX_CLUSTER_COUNT = 100

class SimulationSettings:
    """Simulation settings for the project."""
    START_TIMESTAMP = pd.to_datetime("2024-03-01 00:00:00") # Timestamp, as defined in pandas
    SIMULATION_UPDATE_FREQUENCY = 1 # Frequency in which the simulation is updated
    SIMULATION_DURATION = 600  # Time in seconds
    SIMULATION_STEP = 60  # Time in seconds
    MAX_BATCH_SIZE = 1000  # Maximum number of rows per batch

class KafkaSettings:
    """Settings for Kafka."""
    OPERATOR_BOOTSTRAP_SERVERS = "localhost:9092"
    OPERATOR_TOPIC = "operator_data"
    OPERATOR_COLUMNS = ['instance_id', 'cluster_size', 'database_id', 'arrival_timestamp', 'compile_duration_ms', 'execution_duration_ms', 'was_cached']
    USER_BOOTSTRAP_SERVERS = "localhost:9093"
    USER_TOPIC = "user_data"
    USER_COLUMNS = ['instance_id', 'database_id', 'query_id', 'arrival_timestamp', 'feature_fingerprint', 'query_type']