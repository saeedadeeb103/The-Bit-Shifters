from clusterSimulator import ClusterSimulator
import duckdb
from config import StorageSettings, SimulationSettings
import pandas as pd # Needed for timestamps

class ClusterFactory:
    def __init__(self):
        """ Initializes the Cluster Factory. """
        self.clusters = {}


    def create_cluster(self, cluster_id: str, data_source: str):
        """ Creates a new cluster simulator if it does not exist. """
        if cluster_id in self.clusters:
            print(f"Cluster {cluster_id} already exists.")
            return self.clusters[cluster_id]
        else:
            print("Creating Cluster", cluster_id)
            cluster = ClusterSimulator(cluster_id, data_source)
            self.clusters[cluster_id] = cluster
            return cluster


    def start_clusters(self, cluster_ids: list, start_timestamp: pd.Timestamp, duration: pd.Timedelta, simulation_step: pd.Timedelta):
        """ Starts multiple clusters in parallel using the run method. """
        for cluster_id in cluster_ids:
            if cluster_id in self.clusters:
                cluster = self.clusters[cluster_id]
                cluster.start_synchronous(start_timestamp, duration, simulation_step)


    def stop_clusters(self, cluster_ids: list):
        """ Stops specific clusters given a list of cluster IDs. """
        for cluster_id in cluster_ids:
            if cluster_id in self.clusters:
                self.clusters[cluster_id].stop()


    def stop_all_clusters(self):
        """ Stops all clusters. """
        self.stop_clusters(self.clusters)


    def delete_clusters(self, cluster_id: list):
        """ Deletes specific clusters. """
        if cluster_id in self.clusters:
            if cluster_id in self.clusters:
                self.clusters[cluster_id].stop()
                del self.clusters[cluster_id]


    def delete_all_clusters(self):
        """ Stops all clusters. """
        self.delete_cluster(self.clusters)
        
        
    def get_clusters_running_any(self) -> bool:
        """Checks if one or more clusters are currently running."""
        return len(self.clusters) > 0
    
        
    def get_n_largest_tables(self, duckdb_file_path: str, n: int = None):
        """Retrieves the n largest tables by row count from the specified DuckDB file."""
        con = duckdb.connect(duckdb_file_path)

        # Get all table names
        table_names = con.execute("SELECT table_name FROM duckdb_tables()").fetchall()
        
        row_counts = []
        
        # Dynamically count rows for each table
        for (table_name,) in table_names:
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            row_count = con.execute(count_query).fetchone()[0]
            row_counts.append((table_name, row_count))
        
        con.close()

        # Sort by row count in descending order
        largest_tables = sorted(row_counts, key=lambda x: x[1], reverse=True)
        
        # If n is None, return all tables
        if n is None:
            return largest_tables
        else:
            return largest_tables[:n]


    def create_clusters_from_table(self, limit: int = None):
        # Get the largest tables up to the specified limit
        largest_tables = self.get_n_largest_tables(StorageSettings.DUCKDB_FILE_PATH, limit)
        
        # Create clusters for the largest tables
        largest_table_names = {table[0] for table in largest_tables}
        for table in largest_tables:
            cluster_id = table[0]
            self.create_cluster(cluster_id, StorageSettings.DUCKDB_FILE_PATH)
        
        # Remove clusters that are not in the largest tables
        clusters_to_remove = [cluster_id for cluster_id in self.clusters if cluster_id not in largest_table_names]
        for cluster_id in clusters_to_remove:
            self.stop_cluster(cluster_id)


if __name__ == "__main__":
    factory = ClusterFactory()
    
    # Get the top 5 largest tables
    largest_tables = factory.create_clusters_from_table(5)
    
    # Start the clusters
    cluster_ids = [table[0] for table in largest_tables]
    start_timestamp = SimulationSettings.START_TIMESTAMP
    duration = pd.Timedelta(seconds=SimulationSettings.SIMULATION_DURATION)
    simulation_step = pd.Timedelta(seconds=SimulationSettings.SIMULATION_STEP)
    factory.start_clusters(cluster_ids, start_timestamp, duration, simulation_step)
