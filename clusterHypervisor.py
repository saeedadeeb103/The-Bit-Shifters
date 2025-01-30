import os

# Set the TCL and TK library paths
os.environ['TCL_LIBRARY'] = r'C:\Users\willi\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\willi\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import pandas as pd
import threading
from clusterEmulatorFactory import ClusterFactory
from clusterDatabase import ClusterDatabase
from config import SimulationSettings
from clusterHypervisorUI import create_widgets, update_ui_availability

class ClusterHypervisor:
    def __init__(self, root):
        self.root = root
        self.root.title("Cluster Simulator UI")
        self.root.state('zoomed')
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        
        self.database = ClusterDatabase(bucket="redshift-downloads", file_path="redset/serverless/full.parquet", db_type="duckdb")
        self.factory = ClusterFactory()
        self.cluster_data = self.get_cluster_data()
        self.sort_column = None
        self.sort_order = None
        self.actions_allowed = {
            "async": True,
            "sync": True,
            "reinitialize": True
        }
        self.action_preselection = {
            "async": False,
            "sync": False
        }
        self.running_action = None
        self.threading_lock = threading.Lock()
        
        create_widgets(self)
        self.update_table()
        self.schedule_logic_update()
        
        
    def get_cluster_data(self):
        # Get the current clusters from the factory
        cluster_data = []
        for cluster_id, cluster in self.factory.clusters.items():
            isRunning = cluster.is_running()                 
            execution_time = cluster.get_execution_time()     
            size = len(cluster.df) if hasattr(cluster, 'df') else "N/A"
            status = "Running" if isRunning else "Stopped"
            utilization = f"{max(0, (execution_time * SimulationSettings.SIMULATION_UPDATE_FREQUENCY) * 100):.2f}%" if isRunning and SimulationSettings.SIMULATION_UPDATE_FREQUENCY != 0 else "N/A"
            cluster_data.append((cluster_id, size, status, utilization))
        return cluster_data
    
    
    def update_table(self):
        # Update the cluster data
        new_cluster_data = self.get_cluster_data()
        
        # Create a set of current cluster IDs in the table
        current_cluster_ids = {self.cluster_tree.set(item, "Cluster ID") for item in self.cluster_tree.get_children()}
        
        # Create a set of new cluster IDs
        new_cluster_ids = {cluster[0] for cluster in new_cluster_data}
        
        # Remove clusters that are no longer present
        for item in self.cluster_tree.get_children():
            cluster_id = self.cluster_tree.set(item, "Cluster ID")
            if cluster_id not in new_cluster_ids:
                self.cluster_tree.delete(item)
        
        # Add new clusters that are not currently in the table
        for cluster in new_cluster_data:
            if cluster[0] not in current_cluster_ids:
                self.cluster_tree.insert("", tk.END, values=("", *cluster))
        
        # Update existing clusters
        for item in self.cluster_tree.get_children():
            cluster_id = self.cluster_tree.set(item, "Cluster ID")
            for cluster in new_cluster_data:
                if cluster[0] == cluster_id:
                    self.cluster_tree.set(item, column="Size", value=cluster[1])
                    self.cluster_tree.set(item, column="Status", value=cluster[2])
                    self.cluster_tree.set(item, column="Utilization", value=cluster[3])
    
    
    def schedule_logic_update(self):
        CYCLE_TIME_MILLIS = 1000
        
        # Schedule the update_table method to run periodically
        self.update_table()
             
        self.root.after(CYCLE_TIME_MILLIS, self.schedule_logic_update)  # Update every 1 second
        
        
    def start_async_simulation(self):
        self.start_simulation(async_mode=True)
        
        
    def start_sync_simulation(self):
        self.start_simulation(async_mode=False)
        
        
    def get_selected_cluster_ids(self):
        """
        Retrieves the IDs of all selected clusters from the cluster tree.

        This function iterates through all items in the cluster tree and checks if they are selected
        (indicated by a "✔" in the "Select" column). It then collects the cluster IDs of the selected
        items and returns them as a list.

        Returns:
            list: A list of cluster IDs for the selected clusters.
        """
        selected_items = [item for item in self.cluster_tree.get_children() if self.cluster_tree.set(item, "Select") == "✔"]
        selected_clusters = [self.cluster_tree.item(item, "values")[1] for item in selected_items]
        return selected_clusters
        
        
    def set_active_action(self, action):    
        """
        Update the UI based on the active action, but also forwards the action
        to the base class.
        """         
        # Set flag for active action       
        self.running_action = action
        update_ui_availability(self)
        
        
    def start_simulation(self):
        # Fetch clusters to perform operation on
        selected_clusters = self.get_selected_cluster_ids()       
        if not selected_clusters:
            messagebox.showwarning("No Clusters Selected", "Please select at least one cluster to start the simulation.")
            return
        
        # Set simulation type
        self.set_active_action(self.simulation_mode_var.get())      
        
        # Function to run the simulation
        def async_fnc(simulation_mode: str = "async"):
            try:
                # Fetch simulation settings
                start_timestamp = pd.to_datetime(self.start_time_entry.get())
                end_timestamp = pd.to_datetime(self.end_time_entry.get())
                duration = (end_timestamp - start_timestamp).total_seconds()
                simulation_step = pd.Timedelta(seconds=int(self.simulation_step_entry.get()))
                update_frequency = 1.0 / float(self.cycle_time_entry.get())
                
                SimulationSettings.SIMULATION_STEP = int(self.simulation_step_entry.get())
                SimulationSettings.SIMULATION_UPDATE_FREQUENCY = update_frequency
                
                # Perform the simulation
                if simulation_mode == "sync":
                    self.factory.start_clusters(selected_clusters, start_timestamp, pd.Timedelta(seconds=duration), simulation_step)
                else:
                    self.factory.start_clusters(selected_clusters, start_timestamp, pd.Timedelta(seconds=duration), simulation_step)      
                messagebox.showinfo("Simulation Started", "The simulation has been started successfully.")
                
                # Wait for the simulation to finish
                while any(cluster.is_running() for cluster in self.factory.clusters.values()):
                    self.root.after(1000, lambda: None)  # Wait for 1 second before checking again
                   
                # Notify user when simulation is complete 
                if(self.running_action == "sync"):
                    messagebox.showinfo("Simulation Completed", "The simulation has completed successfully.")
                
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred while starting the simulation: {e}")
               
            finally:
                self.set_active_action(None)
                if self.threading_lock.locked():
                    self.threading_lock.release()
                
        # Asynchronous call, to keep the UI responsive
        if self.threading_lock.locked():
            return
        self.threading_lock.acquire()
        threading.Thread(target=async_fnc, args=(self.simulation_mode_var.get(),)).start()
    
    
    def stop_simulation(self):
        # Fetch selected clusters
        selected_clusters = self.get_selected_cluster_ids()      
        if not selected_clusters:
            messagebox.showwarning("No Clusters Selected", "Please select at least one cluster to stop the simulation.")
            return
        
        try:
            self.factory.stop_clusters(selected_clusters)          
            messagebox.showinfo("Simulation Stopped", "The simulation has been stopped successfully.")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while stopping the simulation: {e}")
            
        finally:
            # Reset UI elements
            self.set_active_action(None)
    
    
    def update_database(self, force_parquet_update: bool, force_duckdb_update: bool):
        """ Function to reinitialize the database by downloading the latest
        data from S3 and storing it in DuckDB. """
        # Function to reinitialize the database by downloading the latest data
        # from S3 and storing it in DuckDB
        def async_fnc():
            try:
                self.database.download_redset_from_s3(force_parquet_update)
                self.database.convert_parquet_to_duckdb(force_duckdb_update or
                                                        force_parquet_update)
                self.factory.create_clusters_from_table(100)
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred while reinitializing the database: {e}")
            self.set_active_action(None)

        # Asynchronous call, to keep the UI responsive
        if self.threading_lock.locked() or self.running_action:
            return
        self.set_active_action(action="reinitialize")
        threading.Thread(target=async_fnc).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = ClusterHypervisor(root)
    root.mainloop()