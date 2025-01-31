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

### **Contributing**  
Feel free to submit **issues** or **pull requests** if you'd like to contribute! 🚀  
