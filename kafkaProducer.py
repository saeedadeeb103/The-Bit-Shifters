from confluent_kafka import Producer
import pandas as pd
import json
from config import KafkaSettings

class KafkaProducer:
    def __init__(self, name: str, bootstrap_servers):
        self.name = name
        self.bootstrap_servers = bootstrap_servers
        self.producer = Producer({
            'bootstrap.servers': self.bootstrap_servers,
            'compression.type': 'gzip'  # Enable Gzip compression
        })
        print(f"Initializing Kafka producer for cluster '{self.name}' with server '{self.bootstrap_servers}' ...")

    def process_and_send(self, df: pd.DataFrame, topic):
        """ Sends logs to Kafka in real-time simulation. """
        if not df.empty:
            first_entry_time = df.iloc[0]['arrival_timestamp']
            print(f"Kafka {topic} - {first_entry_time}: size={len(df)}")
            
            # Convert DataFrame to list of dictionaries
            data = df.to_dict(orient='records')
            
            # Convert Timestamp objects to strings
            for record in data:
                for key, value in record.items():
                    if isinstance(value, pd.Timestamp):
                        record[key] = value.isoformat()
            
            # Send each record to Kafka
            for record in data:
                self.producer.produce(topic, value=json.dumps(record).encode('utf-8'))
                self.producer.poll(0)  # Serve delivery callback queue.
        else:
            print(f"Kafka {topic} - No data in batch?")

    def delivery_report(self, err, msg):
        """ Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush(). """
        if err is not None:
            print(f'Message delivery failed: {err}')
        else:
            print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

    def __del__(self):
        self.producer.flush()
        print(f"Kafka producer deleted from cluster '{self.name}'.")