import pandas as pd

class KafkaProducer:
    def __init__(self, name: str, bootstrap_servers):
        self.name = name
        print(f"Initializing Kafka producer for cluster '{self.name}' ...")

    def process_and_send(self, df: pd.DataFrame, topic):
        """ Sends logs to Kafka in real-time simulation. """
        # Debugging: Print the batch size and first entry time
        if not df.empty:
            first_entry_time = df.iloc[0]['arrival_timestamp']
            # user_id_count = df['user_id'].nunique()
            print(f"Kafka {topic} - {first_entry_time}: size={len(df)}")
        else:
            print(f"Kafka {topic} - No data in batch?")
            return
            
        # Your Kafka producer implementation would go here
        # ...

    def __del__(self):
        print(f"Kafka producer deleted from cluster '{self.name}'.")