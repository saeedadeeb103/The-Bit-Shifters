import tkinter as tk
import pandas as pd
from tkinter import ttk
from config import SimulationSettings

def create_frame(parent, row, column, rowconfigure, columnconfigure, title):
    """Function to create a frame with a title."""        
    frame = ttk.LabelFrame(parent, text=title)
    frame.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")
    frame.rowconfigure(rowconfigure, weight=1)
    frame.columnconfigure(columnconfigure, weight=1)
    return frame


def create_widgets(ui):
    # Create a frame for the cluster table
    ui.cluster_frame = ttk.LabelFrame(ui.root, text="Available Clusters")
    ui.cluster_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    ui.cluster_frame.rowconfigure(0, weight=1)
    ui.cluster_frame.columnconfigure(0, weight=1)
    
    # Create a treeview for the clusters
    ui.cluster_tree = ttk.Treeview(ui.cluster_frame, columns=("Select", "Cluster ID", "Size", "Status", "Utilization"), show="headings")
    ui.cluster_tree.heading("Select", text="Select", command=lambda: sort_table(ui, "Select"))
    ui.cluster_tree.heading("Cluster ID", text="Cluster ID", command=lambda: sort_table(ui, "Cluster ID"))
    ui.cluster_tree.heading("Size", text="Size", command=lambda: sort_table(ui, "Size"))
    ui.cluster_tree.heading("Status", text="Status", command=lambda: sort_table(ui, "Status"))
    ui.cluster_tree.heading("Utilization", text="Utilization", command=lambda: sort_table(ui, "Utilization"))
    ui.cluster_tree.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    # Add checkboxes to the treeview
    # Add a column for checkboxes
    for child in ui.cluster_tree.get_children():
        ui.cluster_tree.item(child, tags=("enabled",))
    ui.cluster_tree.tag_bind("enabled", "<Double-1>", lambda event: apply_checkbox(event, ui))
    ui.cluster_tree.tag_bind("disabled", "<Double-1>", lambda _: "break")
    
    # Create a frame for the simulation settings and buttons
    ui.settings_frame = create_frame(ui.root, row=1, column=0, 
                                     rowconfigure=6, columnconfigure=1,
                                     title="Simulation Settings")
    
    # Create fields for start and end time
    ui.start_time_label = ttk.Label(ui.settings_frame, text="Start Time (YYYY-MM-DD HH:MM:SS):")
    ui.start_time_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
    
    ui.start_time_entry = ttk.Entry(ui.settings_frame)
    ui.start_time_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    ui.start_time_entry.insert(0, SimulationSettings.START_TIMESTAMP.strftime("%Y-%m-%d %H:%M:%S"))
    
    ui.end_time_label = ttk.Label(ui.settings_frame, text="End Time (YYYY-MM-DD HH:MM:SS):")
    ui.end_time_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    
    ui.end_time_entry = ttk.Entry(ui.settings_frame)
    ui.end_time_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
    end_time = SimulationSettings.START_TIMESTAMP + pd.Timedelta(seconds=SimulationSettings.SIMULATION_DURATION)
    ui.end_time_entry.insert(0, end_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Create a label for the communication mode
    ui.communication_mode_label = ttk.Label(ui.settings_frame, text="Communication Mode:")
    ui.communication_mode_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
    
    # Create radio buttons to select between synchronous and asynchronous mode
    ui.simulation_mode_var = tk.StringVar(value="async" if ui.action_preselection["async"] else "sync")
    
    ui.async_radio = ttk.Radiobutton(ui.settings_frame, text="Asynchronous", variable=ui.simulation_mode_var, value="async", command=lambda: update_preselection(ui))
    ui.async_radio.grid(row=2, column=1, padx=10, pady=5, sticky="w")
    
    ui.sync_radio = ttk.Radiobutton(ui.settings_frame, text="Synchronous", variable=ui.simulation_mode_var, value="sync", command=lambda: update_preselection(ui))
    ui.sync_radio.grid(row=3, column=1, padx=10, pady=5, sticky="w")
    
    # Create fields for simulation step and update frequency
    ui.simulation_step_label = ttk.Label(ui.settings_frame, text="Simulation Step (seconds):")
    ui.simulation_step_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
    
    ui.simulation_step_entry = ttk.Entry(ui.settings_frame)
    ui.simulation_step_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
    ui.simulation_step_entry.insert(0, str(SimulationSettings.SIMULATION_STEP))
    ui.simulation_step_entry.bind("<FocusOut>", lambda _: set_project_step_size(ui.simulation_step_entry))
    
    ui.update_frequency_label = ttk.Label(ui.settings_frame, text="Project cyclic time (seconds):")
    ui.update_frequency_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
    
    ui.cycle_time_entry = ttk.Entry(ui.settings_frame)
    ui.cycle_time_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
    ui.cycle_time_entry.insert(0, str(1.0 / SimulationSettings.SIMULATION_UPDATE_FREQUENCY))
    ui.cycle_time_entry.bind("<FocusOut>", lambda _: set_project_cycle_time(ui.cycle_time_entry))

    # Create buttons to start the simulation based on the selected mode
    ui.start_simulation_button = ttk.Button(ui.settings_frame, text="Start Run", command=lambda: ui.start_simulation())
    ui.start_simulation_button.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
    
    # Database ____________________________________________________________
    # Create section for database (operations, status, ...)
    ui.database_frame = create_frame(ui.root, row=2, column=0, 
                                     rowconfigure=5, columnconfigure=1, 
                                     title="Database")
    
    # Create checkboxes for force download and force update
    ui.force_download_var = tk.BooleanVar()
    ui.force_download_checkbox = ttk.Checkbutton(
        ui.database_frame, 
        text="Force Download of Parquet file", 
        variable=ui.force_download_var,
        command=lambda: 
            ui.force_update_var.set(True) 
            if ui.force_download_var.get() else None
    )
    ui.force_download_checkbox.grid(row=0, column=0, padx=10, pady=5, sticky="w")

    ui.force_update_var = tk.BooleanVar()
    ui.force_update_checkbox = ttk.Checkbutton(
        ui.database_frame, 
        text="Force Update of DuckDB file", 
        variable=ui.force_update_var,
        command=lambda: 
            ui.force_download_var.set(False) 
            if not ui.force_update_var.get() else None
    )
    ui.force_update_checkbox.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    
    # Create button to reinitialize the database
    ui.reinitialize_button = ttk.Button(
        ui.database_frame, 
        text="Refresh Database", 
        command=lambda: 
            ui.root.after(0, ui.update_database, ui.force_download_var.get(), ui.force_update_var.get())
    )
    ui.reinitialize_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
    
    # Footer ______________________________________________________________
    # Create a frame for the footer
    ui.footer_frame = ttk.Frame(ui.root)
    ui.footer_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
    ui.footer_frame.columnconfigure(0, weight=1)
    
    # Create a label for the progress text
    ui.progress_label = ttk.Label(ui.footer_frame, text="No task running")
    ui.progress_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")
    
    # Create a progress bar with a maximum width
    ui.progress_bar = ttk.Progressbar(ui.footer_frame, mode='indeterminate', maximum=100)
    ui.progress_bar.grid(row=0, column=1, padx=10, pady=10, sticky="e")
    ui.progress_bar.config(length=200)  # Set the maximum width of the progress bar
    
    # Hide the progress bar by default
    ui.progress_bar.grid_remove()
    
    # Final updates for UI
    update_preselection(ui)
    update_ui_availability(ui)


def set_project_cycle_time(element):
    try:
        project_cycle_time = float(element.get())
        if project_cycle_time > 0:
            SimulationSettings.SIMULATION_UPDATE_FREQUENCY = 1.0 / project_cycle_time
        else:
            raise ValueError("Cycle time must be greater than 0")
    except ValueError as e:
        tk.messagebox.showerror("Invalid Input", str(e))


def set_project_step_size(element):
    try:
        step_size = float(element.get())
        if step_size > 0:
            SimulationSettings.SIMULATION_STEP = step_size
        else:
            raise ValueError("Step size must be greater than 0")
    except ValueError as e:
        tk.messagebox.showerror("Invalid Input", str(e))


def sort_table(ui, col):
    """Sorting behavior for the table's columns."""
    if ui.sort_column == col:
        ui.sort_order = not ui.sort_order
    else:
        ui.sort_column = col
        ui.sort_order = True
    
    data = [(ui.cluster_tree.set(child, col), child) for child in ui.cluster_tree.get_children('')]
    
    if col == "Size":
        data.sort(key=lambda x: float(x[0]), reverse=ui.sort_order)
    else:
        data.sort(reverse=ui.sort_order)
    
    for index, (_, child) in enumerate(data):
        ui.cluster_tree.move(child, '', index)
    
    ui.cluster_tree.heading(col, command=lambda: sort_table(ui, col))
    
    
def apply_checkbox(event, ui):
    """Function to apply checkboxes to the treeview."""
    region = ui.cluster_tree.identify("region", event.x, event.y)
    if region == "cell":
        column = ui.cluster_tree.identify_column(event.x)
        if column == "#1":  # Checkbox column
            selected_items = ui.cluster_tree.selection()
        for row in selected_items:
            current_value = ui.cluster_tree.set(row, "Select")
            new_value = "" if current_value == "✔" else "✔"
            ui.cluster_tree.set(row, "Select", new_value)
      
      
def set_ui_element_allowance(element, allow: bool):
    """
    Function to enable or disable a specific UI element.
    
    Args:
        element (tk.Widget): The UI element to enable or disable.
        allow (bool): Whether to enable or disable the element.
    """
    element.config(state="normal" if allow else "disabled")
      
      
def update_preselection(ui):
    ui.action_preselection["async"] = ui.simulation_mode_var.get() == "async"
    ui.action_preselection["sync"] = ui.simulation_mode_var.get() == "sync"
    update_ui_availability(ui)
            
            
def update_ui_availability(ui):
    """Function to set the availability of fields based on the simulation mode."""
    active_task = ui.running_action
    preselection = ui.action_preselection

    # Behavior of the progress bar and label
    if active_task:
        ui.progress_bar.grid()
        ui.progress_bar.start()
        ui.progress_label.config(text=f"Running {active_task} task...")
    else:
        ui.progress_bar.stop()
        ui.progress_bar.grid_remove()
        ui.progress_label.config(text="No task running")
    
    # Lock or unlock UI elements
    no_action = active_task is None
    set_ui_element_allowance(ui.start_time_entry, no_action)
    set_ui_element_allowance(ui.end_time_entry, no_action)
    set_ui_element_allowance(ui.simulation_step_entry, no_action and preselection["sync"])
    set_ui_element_allowance(ui.cycle_time_entry, no_action and preselection["sync"])
    set_ui_element_allowance(ui.force_download_checkbox, no_action)
    set_ui_element_allowance(ui.force_update_checkbox, no_action)
    set_ui_element_allowance(ui.reinitialize_button, no_action)
    set_ui_element_allowance(ui.async_radio, no_action)
    set_ui_element_allowance(ui.sync_radio, no_action)
    set_ui_element_allowance(ui.start_simulation_button, no_action or active_task == "async" or active_task == "sync")
    
    # Update UI elements based on the action
    if active_task == "async" or active_task == "sync":
        ui.start_simulation_button.config(text="Stop Simulation", command=ui.stop_simulation)      
        for child in ui.cluster_tree.get_children():
            ui.cluster_tree.item(child, tags=("disabled",))
    else:
        ui.start_simulation_button.config(text="Start Simulation", command=ui.start_simulation)
        for child in ui.cluster_tree.get_children():
            ui.cluster_tree.item(child, tags=("enabled",))