from confluent_kafka import Consumer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient
import json
from config import KafkaSettings, StorageSettings
import pandas as pd
import duckdb
import time
import os

class KafkaConsumer:
    def __init__(self, group_id: str, bootstrap_servers: str, operator_topic_prefix: str):
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers
        self.operator_topic_prefix = operator_topic_prefix
        self.consumer = Consumer({
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True
        })
        self.topics = self.discover_topics()
        self.consumer.subscribe(self.topics)
        print(f"Initializing Kafka consumer for group '{self.group_id}' with server '{self.bootstrap_servers}' and topics '{self.topics}' ...")

    def discover_topics(self):
        """Discovers and filters topics based on the given prefixes."""
        admin_client = AdminClient({'bootstrap.servers': self.bootstrap_servers})
        metadata = admin_client.list_topics(timeout=10)
        all_topics = metadata.topics.keys()
        operator_topics = [topic for topic in all_topics if topic.startswith(self.operator_topic_prefix)]
        return operator_topics

    def consume_messages(self):
        """Continuously consumes messages from the subscribed topics."""
        try:
            while True:
                msg = self.consumer.poll(timeout=1.0)
                print(msg)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        print(f"End of partition reached {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
                    elif msg.error():
                        raise KafkaException(msg.error())
                else:
                    self.process_message(msg)
                # Periodically store data to DuckDB
                self.store_periodic_data()
                
        except KeyboardInterrupt:
            pass
        finally:
            self.consumer.close()

    def process_message(self, msg):
        """Processes an incoming message."""
        try:
            data = json.loads(msg.value().decode('utf-8'))
            topic = msg.topic()
            print(f"Received message from topic '{topic}': {data}")
            self.store_to_duckdb(data, topic)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")

    

    def store_to_duckdb(self, data, topic):
        """Stores the processed data to DuckDB, creating a separate table for each user_id while keeping logs in a single table."""
        try:
            # Ensure DuckDB file and directory exist
            db_path = StorageSettings.OPERATOR_CLUSTER_FILE_PATH
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)  # Create directory if it doesn't exist

            # Convert data to DataFrame
            df = pd.DataFrame([data])

            # Connect to DuckDB
            con = duckdb.connect(db_path)


            if topic.startswith(self.operator_topic_prefix):
                table_name = "logs"  # Store all operator logs in a single table

                # Register DataFrame as a temporary table
                con.register("temp_df_op", df)
                # Create table if it doesn't exist
                con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM temp_df_op WHERE 1=0")

                # Insert data into the logs table
                con.execute(f"INSERT INTO {table_name} SELECT * FROM temp_df_op")

                print(f"Stored data in DuckDB table '{table_name}'")

            else:
                print(f"Unknown topic: {topic}")
                return

            # Close the connection
            con.close()

        except Exception as e:
            print(f"Error storing data to DuckDB: {e}")


    def store_periodic_data(self, interval=60):
        """Periodically stores data to DuckDB."""
        # This method can be expanded to include periodic storage logic if needed
        pass

    def __del__(self):
        self.consumer.close()
        print(f"Kafka consumer deleted from group '{self.group_id}'.")

if __name__ == "__main__":
    # Create and start the Kafka consumer
    consumer = KafkaConsumer(
        group_id="my_consumer_group",
        bootstrap_servers="localhost:9092",
        operator_topic_prefix=KafkaSettings.OPERATOR_TOPIC
    )
    consumer.consume_messages()