# **The-Bit-Shifters**  
This project was created using **Python 3.11.0**.

## **Installation**  
Follow these steps to set up the project environment:  

1. **Create a Python virtual environment:**  
   ```sh
   conda create --name bit-shifters python==3.11
   ```

2. **Activate the virtual environment:**  
   ```sh
   conda activate bit-shifters
   ```
3. **Install required libraries:**  
   ```sh
   pip install -r requirements.txt
   ```
4. **Ensure `TCL_LIBRARY` and `TK_LIBRARY` are set correctly:**  
   - Verify that the **`TCL_LIBRARY`** and **`TK_LIBRARY`** variables in `config.py` align with the installation folders of **TCL** and **TK**.

---

# **Kafka Installation and Setup Guide**

## **Prerequisites**
Ensure you have the following installed on your system:
- Java (JDK 8 or later)
- Apache Kafka (latest stable version)

## **Step 1: Download and Extract Kafka**
1. [Download Kafka](https://kafka.apache.org/downloads) (latest stable release, e.g., `kafka_2.13-3.2.1.tgz`).
2. Extract the downloaded file:
    ```bash
    tar -xzf kafka_2.13-3.2.1.tgz -C /path/to/install
    ```

## **Step 2: Configure Kafka Brokers Zookeepers**
1. Navigate to the Kafka config directory:
    ```bash
    cd /path/to/install/kafka_2.13-3.2.1/config
    ```
2. Locate the **server.properties** file and make two copies:
    ```bash
    cp server.properties server-9092.properties
    cp server.properties server-9093.properties
    ```
3. Locate the **zookeeper.properties** file and make two copies:
    ```bash
    cp zookeeper.properties zookeeper-9092.properties
    cp zookeeper.properties zookeeper-9093.properties
    ```
4. Modify `server-9092.properties`:
    ```properties
    broker.id=1
    listeners=PLAINTEXT://localhost:9092
    log.dir=/tmp/kafka-logs-1
    zookeeper.connect=localhost:2182
    ```
5. Modify `server-9093.properties`:
    ```properties
    broker.id=2
    listeners=PLAINTEXT://localhost:9093
    log.dir=/tmp/kafka-logs-2
    zookeeper.connect=localhost:2183
    ```

6. Modify `zookeeper-9092.properties`:
    ```properties
    clientPort=2182
    ```
7. Modify `zookeeper-9093.properties`:
    ```properties
    clientPort=2183
    ```

## **Step 3: Start Kafka and Zookeeper**
1. Open a terminal and navigate to the Kafka installation directory:
    ```bash
    cd /path/to/install/kafka_2.13-3.2.1
    ```
2. Start the Zookeeper server:
    ```bash
    bin/zookeeper-server-start.sh config/zookeeper-9092.properties
    ```
3. Open a new terminal and start another Zookeeper:
    ```bash
    bin/zookeeper-server-start.sh config/zookeeper-9093.properties
    ```
4. Open a new terminal and start Kafka broker on port 9092:
    ```bash
    bin/kafka-server-start.sh config/server-9092.properties
    ```
5. Open another terminal and start Kafka broker on port 9093:
    ```bash
    bin/kafka-server-start.sh config/server-9093.properties
    ```

## **Verification**
To verify that Kafka is running correctly, list the active brokers:
```bash
bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092
```

## **Next Steps**
- Create topics and produce/consume messages.
- Configure Kafka for production.
- Monitor and optimize Kafka performance.

For more details, visit the [official Kafka documentation](https://kafka.apache.org/documentation/).

---

## **Run the Simulator**  
To start the simulation, follow these steps:

1. **Start the cluster hypervisor:**  
   ```sh
   python clusterHypervisor.py
   ```
2. **(One-time setup)** Refresh the database to download data from **S3** and load the available cluster.
3. **Start the simulation via the UI.**
4. **Run Kafka consumer scripts to process incoming data:**
   ```sh
   python kafkaConsumer_user.py
   python kafkaConsumer_operator.py
   ```
5. **Stop the consumer scripts once data processing is complete**
6. **Start the Flask application:**
   ```sh
   flask run
   ```

## **Accessing the Dashboards**
- **Operator Dashboard:**
  - URL: `http://localhost:5000`
  - Username: `admin`
  - Password: `admin`

- **Customer Dashboard:**
  - URL: `http://localhost:5000/`
  - Username: Based on the user data received.
  - Default credentials: 
    - **User_id=0** → Username: `00`, Password: `00`
    - Additional users follow the same pattern.

Ensure that all necessary services are running before accessing the dashboards.

