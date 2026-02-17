# -*- coding: utf-8 -*-

import serial
import threading
import pandas as pd
import numpy as np
import re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

class OPC:
    def __init__(self, port, message_callback=None):
        self.message_callback = message_callback

        self.ser = serial.Serial(
            port=port,
            baudrate=230400,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            parity=serial.PARITY_NONE,
            xonxoff=True,
            timeout=1
        )
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)

        self.current_df = pd.DataFrame()
        self.current_idx = 0
        
        self.bin_diams = np.array([166.4, 169.2, 172.0, 174.8, 177.8, 180.8, 
                                   183.8, 186.8, 190.0, 193.2, 196.4, 199.7, 
                                   203.0, 206.4, 209.9, 213.4, 217.0, 220.6, 
                                   224.3, 228.0, 231.8, 235.7, 239.7, 243.7, 
                                   247.7, 251.9, 256.1, 260.4, 264.8, 269.2, 
                                   273.8, 278.4, 283.2, 288.2, 293.2, 298.5, 
                                   303.9, 309.6, 315.6, 321.9, 328.6, 335.8, 
                                   343.5, 351.8, 360.9, 370.7, 381.6, 393.6, 
                                   407.0, 422.0, 438.9, 457.9, 479.5, 504.0, 
                                   532.0, 564.1, 600.9, 643.2, 692.2, 748.6, 
                                   814.0, 889.8, 977.7, 1079.8, 1198.6, 1336.8, 
                                   1497.8, 1685.4, 1904.1, 2159.3, 2456.9, 2805.2])
        
        self.current_concs = np.array([])
        self.sum_concs = np.array([])
        self.ave_concs = np.array([])

    def _reader_loop(self):
        #data to hold everything that comes in
        data = {}
        concs = np.array([])
        while not self._stop_event.is_set():
            raw = self.ser.readline().decode("utf-8", errors="ignore")
            for line in raw.split("\r"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("pmt_base_rd"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                    data[key] = value
                    
                    #check if it is one of the concentrations
                    if re.fullmatch(r'c-?\d+', key):
                        #append it to the concentrations
                        concs = np.append(concs,value)
                    
                

                if "c72=" in line:
                    # initialize sum array on first scan
                    if self.current_idx == 0:
                        self.sum_concs = concs.copy()
                    else:
                        self.sum_concs = self.sum_concs + concs
                    
                    self.current_concs = concs.copy()
                    self.current_idx += 1
                    self.ave_concs = self.sum_concs / self.current_idx
                    

            
                    
                    # prepend timestamp
                    data = {"timestamp": datetime.now(), **data}
                    row = pd.DataFrame([data])
                    row.index = [self.current_idx]
                    self.current_df = pd.concat([self.current_df, row])

                    # callback to GUI
                    if self.message_callback:
                        self.message_callback(row)

                    #reset for next scan
                    data = {}
                    concs = np.array([])

    def start_read(self):
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self._stop_event.clear()
        if not self._thread.is_alive():
            self._thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._thread.start()

    def stop_read(self):
        self._stop_event.set()

    def close(self):
        self.stop_read()
        if self.ser.is_open:
            self.ser.close()


# =======================
# GUI
# =======================
class OPC_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OPC Logger")

        self.opc = None
        self.folder_path = ""
        self.filename = ""
        self.filepath = ""
        self.file_created = False

        # Data for plotting
        self.plot_data = pd.DataFrame(columns=["timestamp", "total_conc"])
        self.plot_window = None
        self.fig = None
        self.ax = None
        self.canvas = None
        self.line = None  # Line2D object for smooth updating
        
        # Size distribution plot
        self.sd_window = None
        self.sd_fig = None
        self.sd_ax = None
        self.sd_canvas = None
        self.current_line = None
        self.ave_line = None

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        # COM Port
        port_frame = ttk.Frame(frame)
        port_frame.pack(fill="x", pady=5)
        ttk.Label(port_frame, text="COM Port:").pack(side="left")
        self.port_entry = ttk.Entry(port_frame, width=10)
        self.port_entry.insert(0, "COM5")
        self.port_entry.pack(side="left", padx=5)

        # Folder selection and filename
        file_frame = ttk.Frame(frame)
        file_frame.pack(fill="x", pady=5)

        ttk.Label(file_frame, text="Save Folder:").pack(side="left")
        self.folder_label = ttk.Label(file_frame, text="No folder selected", width=40)
        self.folder_label.pack(side="left", padx=5)
        ttk.Button(file_frame, text="Select Folder", command=self.select_folder).pack(side="left", padx=5)

        ttk.Label(file_frame, text="Filename:").pack(side="left", padx=(10,0))
        self.filename_entry = ttk.Entry(file_frame, width=15)
        self.filename_entry.insert(0, "opc_data.csv")
        self.filename_entry.pack(side="left", padx=5)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        # Output window
        self.output = scrolledtext.ScrolledText(frame, height=20)
        self.output.pack(fill="both", expand=True)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path = folder
            self.folder_label.config(text=folder)

    # =======================
    # Override start to create a new plot window each session
    # =======================
    def start(self):
        if not self.folder_path:
            self.log("Please select a folder first.")
            return
        filename = self.filename_entry.get().strip()
        if not filename:
            self.log("Please enter a filename.")
            return

        self.filename = filename
        self.filepath = os.path.join(self.folder_path, self.filename)

        # Check if file already exists
        if os.path.exists(self.filepath):
            messagebox.showwarning("File Exists", f"The file '{self.filename}' already exists in this folder.\nStart aborted.")
            self.log(f"Start aborted: {self.filepath} already exists.")
            return

        port = self.port_entry.get()
        try:
            # Reset plotting data
            self.plot_data = pd.DataFrame(columns=["timestamp", "total_conc"])
            self.plot_window = None
            self.fig = None
            self.ax = None
            self.canvas = None
            self.line = None

            self.open_plot_window()  # Create a new plot window for this session
            self.open_sd_window()

            self.opc = OPC(port, message_callback=self.handle_message)
            self.opc.start_read()
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.log(f"Started reading from {port}, saving to {self.filepath}")
        except Exception as e:
            self.log(f"Error opening port: {e}")

    # =======================
    # Override stop to just stop the session (plot window remains)
    # =======================

    def stop(self):
        if self.opc:
            self.opc.close()
            self.opc = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.file_created = False
        self.log("Stopped")

    def log(self, message):
        self.output.insert("end", message + "\n")
        self.output.see("end")

    def handle_message(self, row_df):

        # Write to CSV
        if not self.file_created:
            row_df.to_csv(self.filepath, mode="w", header=True, index=False)
            self.file_created = True
        else:
            row_df.to_csv(self.filepath, mode="a", header=False, index=False)

        # Update plot data
        if "total_conc" in row_df.columns:
            self.plot_data = pd.concat([self.plot_data, row_df[["timestamp", "total_conc"]]], ignore_index=True)
            self.update_plot(row_df.iloc[0]["timestamp"], row_df.iloc[0]["total_conc"])
            
        # Update size distribution plot if data available
        if self.opc and len(self.opc.current_concs) > 0:
            self.update_sd_plot()

    # =======================
    # Plotting functions
    # =======================
    # =======================
    # Plotting functions
    # =======================
    def open_plot_window(self):
        self.plot_window = tk.Toplevel(self.root)
        self.plot_window.title("Total Concentration Over Time")
        self.plot_window.geometry("800x400")

        self.fig, self.ax = plt.subplots(figsize=(8,4))
        self.ax.set_title("Total Concentration Over Time")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("total_conc")
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

        # Create an empty line for live updating
        self.line = Line2D([], [], color="blue", marker="o")
        self.ax.add_line(self.line)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_window)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        
    def open_sd_window(self):
        self.sd_window = tk.Toplevel(self.root)
        self.sd_window.title("Size Distribution")
        self.sd_window.geometry("700x500")

        self.sd_fig, self.sd_ax = plt.subplots(figsize=(7,5))

        self.sd_ax.set_title("Concentration vs Diameter")
        self.sd_ax.set_xlabel("Bin Diameter (nm)")
        self.sd_ax.set_ylabel("Concentration")
        self.sd_ax.set_xscale("log")

        # Empty lines for live update
        self.current_line = Line2D([], [], label="Current")
        self.ave_line = Line2D([], [], label="Average")

        self.sd_ax.add_line(self.current_line)
        self.sd_ax.add_line(self.ave_line)
        self.sd_ax.legend()

        self.sd_canvas = FigureCanvasTkAgg(self.sd_fig, master=self.sd_window)
        self.sd_canvas.get_tk_widget().pack(fill="both", expand=True)

    def update_plot(self, timestamp, total_conc):
        if self.plot_window is None or not tk.Toplevel.winfo_exists(self.plot_window):
            return  # Safety check

        # Append new data to the line
        xdata = list(self.line.get_xdata())
        ydata = list(self.line.get_ydata())
        xdata.append(timestamp)
        ydata.append(total_conc)
        self.line.set_data(xdata, ydata)

        # Update axis limits
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()

        # Redraw canvas
        self.canvas.draw()
        
    def update_sd_plot(self):
        if self.sd_window is None or not tk.Toplevel.winfo_exists(self.sd_window):
            return

        x = self.opc.bin_diams
        y_current = self.opc.current_concs
        y_ave = self.opc.ave_concs

        # Safety check for matching sizes
        if len(x) != len(y_current):
            return

        self.current_line.set_data(x, y_current)
        self.ave_line.set_data(x, y_ave)

        self.sd_ax.relim()
        self.sd_ax.autoscale_view()

        self.sd_canvas.draw()


# =======================
# Run GUI
# =======================
if __name__ == "__main__":
    root = tk.Tk()
    app = OPC_GUI(root)
    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()