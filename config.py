import os
import pandas as pd

class StorageSettings:
    """Storage settings for the project."""
    DATABASE_FOLDER = os.path.join(os.getcwd(), "databases")
    PARQUET_FILE_PATH = os.path.join(DATABASE_FOLDER, "full.parquet")
    DUCKDB_FILE_PATH = os.path.join(DATABASE_FOLDER, "full.duckdb")

class SimulationSettings:
    """Simulation settings for the project."""
    START_TIMESTAMP = pd.to_datetime("2024-03-01 00:00:00") # Timestamp, as defined in pandas
    SIMULATION_UPDATE_FREQUENCY = 1 # Frequency in which the simulation is updated
    SIMULATION_DURATION = 600  # Time in seconds
    SIMULATION_STEP = 60  # Time in seconds
    MAX_BATCH_SIZE = 1000  # Maximum number of rows per batch