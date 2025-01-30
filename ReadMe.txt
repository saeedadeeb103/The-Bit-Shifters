To start a simulation, perform the following actions:
1.) Run the script clusterDatabase.py to download and setup the databases.
    This will download the parquet file from github, and instantiate a databse
    (DuckDB) from it. This script must be executed once after setup, or when
    the databse is updated.
2.) Run the script clusterEmulatorFactory.py to start a simulation run

Use the file 'config.py', to change the storage and simulation settings.