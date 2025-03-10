import threading
import time
import os
import duckdb
import pandas as pd # Needed to handle timestamps
from config import SimulationSettings, KafkaSettings
from kafkaProducer import KafkaProducer

class ClusterSimulator:
    def __init__(self, cluster_id: str, data_source: str, factory = None):
        """ Initializes a simulated Redshift cluster. """
        self.cluster_id = cluster_id
        self.data_source = data_source
        self.load_data()
        self.thread = None
        self.factory = factory
        self.simulation_time = pd.Timestamp.now()
        self.step_size = None
        self.current_read_time = 0.0
        self.current_send_time = 0.0

        # Producers for Kafka
        self.kafka_producer_operator_data = None
        self.kafka_producer_user_data = None
        
        # Variables for threading and simulation control
        self.runtime_stop_event = threading.Event()
        self.runtime_step_event = threading.Event()
        self.runtime_event = threading.Event()
        self.runtime_running = threading.Event()
        self._parent_pid = os.getpid()


    def get_execution_times(self):
        """ 
        Returns a tuple with the current read_time and send_time of the cluster simulator in seconds.
        """
        return self.current_read_time, self.current_send_time


    def is_running(self):
        """ Returns whether the cluster simulator is currently running. """
        return self.runtime_running.is_set()
    
    
    def step(self, timestamp_begin: pd.Timestamp = pd.Timestamp.now(), duration: pd.Timedelta = pd.Timedelta(seconds=1.0)):
        """ 
        Executes a single step of the cluster simulator with the given playback speed and time range.
        """       
        if self.df.empty:
            return 0, 0
        
        # print(f"Taking simulation step for cluster_id '{self.cluster_id}' at timestamp '{timestamp_begin}' ...")
        # Fetch batch of data (read) ------------------------------------------
        time_on_read_start = time.time()       
        batch = self.fetch_batch(timestamp_begin, duration)
        operator_data_batches, user_data_batcheses = self.segment_batch(batch, SimulationSettings.MAX_BATCH_SIZE)
        read_time = time.time() - time_on_read_start

        # Send data to Kafka (write) ------------------------------------------
        # Start timer for performance insights
        time_on_send_start = time.time()

        # Send data of one cluster to Kafka producer
        for operator_data_batch in operator_data_batches:
            operator_data_batch = self.keep_columns(operator_data_batch, KafkaSettings.OPERATOR_COLUMNS)
            self.kafka_producer_operator_data.process_and_send(operator_data_batch, f"{KafkaSettings.OPERATOR_TOPIC}_{self.cluster_id}")

        # Send data of individual users to Kafka producer
        for user_id, user_batch_list in user_data_batcheses.items():
            for user_data_batch in user_batch_list:
              user_data_batch = self.keep_columns(user_data_batch, KafkaSettings.USER_COLUMNS)
              self.kafka_producer_user_data.process_and_send(user_data_batch, f"{KafkaSettings.USER_TOPIC}_{self.cluster_id}_{user_id}")

        # Stop timer
        send_time = time.time() - time_on_send_start

        # Finally -------------------------------------------------------------        
        # print(f"Complete simulation step for cluster_id '{self.cluster_id}' at timestamp '{timestamp_begin}' ...")
        return read_time, send_time


    def start(self):
        """ 
        Runs the cluster simulator with the given playback speed and time
        range.
        """
        def async_run():
            # Set the runtime events
            self.runtime_running.set()
            self.runtime_event.clear()

            # Initialize the operators Kafka producer
            self.kafka_producer_operator_data = KafkaProducer(
                f"kafka_producer_operator_data_{self.cluster_id}",
                bootstrap_servers=KafkaSettings.OPERATOR_BOOTSTRAP_SERVERS
            )
            self.kafka_producer_user_data = KafkaProducer(
                f"kafka_producer_user_data_{self.cluster_id}",
                bootstrap_servers=KafkaSettings.USER_BOOTSTRAP_SERVERS
            )

            # Run the cluster simulator (main loop)
            while self.runtime_running.is_set() and not self.runtime_stop_event.is_set():
                if self.runtime_event.wait():  
                    if self.runtime_step_event.is_set():      
                        if self.factory is None:
                            break
                        self.current_read_time, self.current_send_time = self.step(self.simulation_time, self.step_size)
                        self.runtime_step_event.clear()                     
                    self.runtime_event.clear()
                    
            # Debug
            print(f"Terminating thread (main loop) for cluster_id '{self.cluster_id}' ...")
            
            # Cleanup
            self.cleanup_on_stop()
            
        # Debug
        print(f"Starting thread (main loop) for cluster_id '{self.cluster_id}' ...")
           
        # Start runtime (thread)    
        self.thread = threading.Thread(target=async_run)
        self.thread.start()


    def stop(self):
        """ Stops the cluster simulator. """     
        # Debug message
        print(f"Stopping cluster simulator for cluster_id '{self.cluster_id}' ...")
        
        # Terminate the thread if it is still running  
        if self.thread is not None and self.thread.is_alive():
            if os.getpid() == self._parent_pid and threading.current_thread() != self.thread:
                # Signal the thread to stop and wait for it to finish
                self.runtime_stop_event.set()
                self.runtime_event.set()
                print(f"Waiting for thread to join...")
                self.thread.join()
                self.thread = None  # Ensure the thread reference is cleared
                
        # Cleanup
        self.cleanup_on_stop()
        
        # Debug message
        print(f"Stopped cluster simulator for cluster_id '{self.cluster_id}' ...")


    def cleanup_on_stop(self):
        # Remove the Kafka producers
        self.kafka_producer_operator_data = None
        self.kafka_producer_user_data = None

        # Reset the running and take_step events
        self.runtime_running.clear()
        self.runtime_event.clear()
        self.runtime_step_event.clear()
        self.runtime_stop_event.clear()


    def load_data(self):
        """ Loads cluster log data from DuckDB. """
        print(f"Loading data for cluster {self.cluster_id} from DuckDB...")
        con = duckdb.connect(self.data_source)
        self.df = con.execute(f"SELECT * FROM {self.cluster_id}").fetchdf()
        con.close()


    def fetch_batch(self, start_timestamp: pd.Timestamp, duration: pd.Timedelta):
        """ Fetches a batch of data from the dataframe based on the given start timestamp and duration.
            Returns a dictionary of dataframes for each user_id and the full batch dataframe. """
        # Use boolean indexing for better performance
        end_timestamp = start_timestamp + duration
        mask = (self.df['arrival_timestamp'] >= start_timestamp) & (self.df['arrival_timestamp'] < end_timestamp)
        batch_df = self.df.loc[mask]
        return batch_df


    def segment_batch(self, batch_df, max_rows_per_batch):
        """ Segments the batch into operator and user batches based on the user_id. 
            Batches are limited to a maximum size. """
        operator_batch = [batch_df.iloc[i:i + max_rows_per_batch] for i in range(0, len(batch_df), max_rows_per_batch)]
        
        user_batches = {}
        for user_id, user_df in batch_df.groupby('user_id'):
            user_batches[user_id] = [user_df.iloc[i:i + max_rows_per_batch] for i in range(0, len(user_df), max_rows_per_batch)]
        
        return operator_batch, user_batches
    

    def keep_columns(self, batch_df, columns_to_keep: list):
        """ Keeps only the specified columns in the given dataframe batch. """
        return batch_df[columns_to_keep]
