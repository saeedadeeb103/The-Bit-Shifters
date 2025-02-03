# **The-Bit-Shifters**  
This project was created using **Python 3.13.0**.

## **Installation**  
Follow these steps to set up the project environment:  

1. **Create a Python virtual environment:**  
   ```sh
   py -m venv venv
   ```
2. **Activate the virtual environment:**  
   ```sh
   .\venv\Scripts\activate
   ```
3. **Install required libraries:**  
   ```sh
   pip install -r requirements.txt
   ```
4. **Ensure `TCL_LIBRARY` and `TK_LIBRARY` are set correctly:**  
   - Verify that the **`TCL_LIBRARY`** and **`TK_LIBRARY`** variables in `config.py` align with the installation folders of **TCL** and **TK**.

---

## **Run the Simulator**  
To start the simulation, follow these steps:

1. **Start the cluster hypervisor:**  
   ```sh
   python clusterHypervisor.py
   ```
2. **(One-time requirement)** Refresh the database:  
   - This will download data from **S3** and load the available cluster.
3. **Start the simulation via the UI.**

---

## **Kafka Installation Setup**
Setup kafka
1. [Download](https://kafka.apache.org/downloads?spm=5aebb161.5bb182e5.0.0.238616f5ATQWi7) the latest stable release (e.g., kafka_2.13-3.2.1.tgz) 
2. Extract the file 
```bash
tar -xzf kafka_2.13-3.2.1.tgz -C /path/to/install
```
3. Navigate to kafka_2.13-3.2.1/config and locate  **server.properties** file
4. Make 2 copies of **server.properties** and name them as **server-9092.properties and server-9093.properties**
5. Inside server-9092.properties, edit or add the following lines:
```server-9092.properties
broker.id=1
listeners=PLAINTEXT://localhost:9092
log.dir=/tmp/kafka-logs-1
```
6. Inside server-9093.properties, edit or add the following lines:
broker.id=2
listeners=PLAINTEXT://localhost:9093
log.dir=/tmp/kafka-logs-2

Run Kafka and zookeeper servers
1. Open a terminal, navigate to the kafka_2.13-3.2.1
2. run 'bin/zookeeper-server-start.sh config/zookeeper.properties'
3. In a new terminal window run 'bin/kafka-server-start.sh config/server-9092.properties' for port 9092
4. In a new window also run 'bin/kafka-server-start.sh config/server-9093.properties' for port 9093


### **Contributing**  
Feel free to submit **issues** or **pull requests** if you'd like to contribute! 🚀  
