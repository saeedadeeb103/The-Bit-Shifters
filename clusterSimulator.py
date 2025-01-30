import threading
import time
import os
import duckdb
import pandas as pd # Needed to handle timestamps
from config import SimulationSettings
from kafkaProducer import KafkaProducer

class ClusterSimulator:
    def __init__(self, cluster_id: str, data_source: str, kafka_broker="localhost:9092"):
        """ Initializes a simulated Redshift cluster. """
        self.cluster_id = cluster_id
        self.data_source = data_source
        self.kafka_broker = kafka_broker
        self.kafka_producer_operator_data = KafkaProducer(bootstrap_servers=self.kafka_broker, topic=f"operator_data_{cluster_id}")
        self.load_data()
        self.thread = None
        self.current_execution_time = 0.0
        self.running = threading.Event()
        self._parent_pid = os.getpid()

    def get_execution_time(self) -> float:
        """ 
        Returns the current execution time of the cluster simulator in seconds.
        """
        return self.current_execution_time

    def is_running(self):
        """ Returns whether the cluster simulator is currently running. """
        return self.running.is_set()

    def run(self, start_timestamp: pd.Timestamp, duration: pd.Timedelta, simulation_step: pd.Timedelta):
        """ 
        Runs the cluster simulator with the given playback speed and time
        range.
        """
        print(f"Starting cluster simulation for cluster_id '{self.cluster_id}' ...")
        if self.df.empty:
            print("No data available to simulate.")
            return

        first_entry_time = pd.to_datetime(self.df.iloc[0]['arrival_timestamp'])
        if start_timestamp < first_entry_time:
            print(f"Debug: start_timestamp {start_timestamp} is smaller than the arrival_timestamp of the first entry {first_entry_time}.")     

        current_simulated_timestamp = start_timestamp
        user_producers = {}

        self.running.set()

        while self.running.is_set() and current_simulated_timestamp < start_timestamp + duration:
            start_time = time.time()
            
            batch = self.fetch_batch(current_simulated_timestamp, simulation_step)
            operator_batch, user_batches = self.segment_batch(batch, SimulationSettings.MAX_BATCH_SIZE)

            # Send operator batch to Kafka
            for operator_data in operator_batch:
                self.kafka_producer_operator_data.process_and_send(operator_data)

            # Send user batches to Kafka
            for user_id, user_batch_list in user_batches.items():
                if user_id not in user_producers:
                    user_producers[user_id] = KafkaProducer(bootstrap_servers=self.kafka_broker, topic=f"user_data_{user_id}")
                for user_batch in user_batch_list:
                    user_producers[user_id].process_and_send(user_batch)
            
            # Calculate elapsed time and adjust sleep time accordingly
            current_execution_time = time.time() - start_time
            self.current_execution_time = current_execution_time
            sleep_time = max(0, (1.0 / SimulationSettings.SIMULATION_UPDATE_FREQUENCY) - current_execution_time)
            time.sleep(sleep_time)
            
            current_simulated_timestamp += simulation_step
                
        self.running.clear()
        print(f"Finished cluster simulation for cluster_id '{self.cluster_id}' ...")

    def start_synchronous(self, start_timestamp: pd.Timestamp, duration: pd.Timedelta, simulation_step: pd.Timedelta):
        """ Starts the cluster simulator in a separate thread. """
        self.thread = threading.Thread(target=self.run, args=(start_timestamp, duration, simulation_step))
        self.thread.start()

    def stop(self):
        """ Stops the cluster simulator. """
        self.running.clear()
        if self.thread is not None and self.thread.is_alive() and os.getpid() == self._parent_pid and threading.current_thread() != self.thread:
            self.thread.join()
            self.thread = None  # Ensure the thread reference is cleared

    def load_data(self):
        """ Loads cluster log data from DuckDB. """
        print(f"Loading data for cluster {self.cluster_id} from DuckDB...")
        con = duckdb.connect(self.data_source)
        self.df = con.execute(f"SELECT * FROM {self.cluster_id}").fetchdf()
        con.close()

    def fetch_batch(self, start_timestamp: pd.Timestamp, duration: pd.Timedelta):
        """ Fetches a batch of data from the dataframe based on the given start timestamp and duration.
            Returns a dictionary of dataframes for each user_id and the full batch dataframe. """
        # Fetch all data based on the given timestamp range
        end_timestamp = start_timestamp + duration
        batch_df = self.df[(self.df['arrival_timestamp'] >= start_timestamp) & (self.df['arrival_timestamp'] < end_timestamp)]
        return batch_df

    def segment_batch(self, batch_df, max_rows_per_batch):
        """ Segments the batch into operator and user batches based on the user_id. 
            Batches are limited to a maximum size. """
        operator_batch = []
        user_batches = {}

        for start in range(0, len(batch_df), max_rows_per_batch):
            end = start + max_rows_per_batch
            operator_batch.append(batch_df.iloc[start:end])

        for user_id, user_df in batch_df.groupby('user_id'):
            user_batches[user_id] = []
            for start in range(0, len(user_df), max_rows_per_batch):
                end = start + max_rows_per_batch
                user_batches[user_id].append(user_df.iloc[start:end])
        
        return operator_batch, user_batches
