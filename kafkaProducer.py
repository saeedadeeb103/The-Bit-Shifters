import pandas as pd

class KafkaProducer:
    def __init__(self, bootstrap_servers, topic):
        print(f"Initializing Kafka producer for topic '{topic}'...")
        self.topic = topic

    def process_and_send(self, df: pd.DataFrame):
        """ Sends logs to Kafka in real-time simulation. """
        # Debugging: Print the batch size and first entry time
        if not df.empty:
            first_entry_time = df.iloc[0]['arrival_timestamp']
            # user_id_count = df['user_id'].nunique()
            print(f"Kafka {self.topic} - {first_entry_time}: size={len(df)}")
        else:
            print(f"Kafka {self.topic} - No data in batch")
            return
            
        # Your Kafka producer implementation would go here
        # ...