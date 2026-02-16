# -*- coding: utf-8 -*-
"""
Created on Fri Feb 13 13:20:57 2026

@author: peo0005
"""

import serial
import threading
import pandas as pd
from datetime import datetime


class OPC():
       
    def __init__(self,port):      
        #initialize the serial port
        ser = serial.Serial()
        ser.port = port

        #serial settings
        ser.bytesize = serial.EIGHTBITS
        ser.stopbits = serial.STOPBITS_ONE
        ser.parity = serial.PARITY_NONE
        ser.xonxoff = True
        ser.baudrate = 230400

        #timeout so don't wait forever
        ser.timeout = 5

        #open serial port
        ser.open()        
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        #save serial port 
        self.ser = ser
        
        self._stop_event = threading.Event()

        self._thread = threading.Thread(
                target=self._reader_loop, daemon=True)
        
        
    def _reader_loop(self):
        #this thread blocks while getting data
        
        #empty data set
        data = {}
        
        #continue to readlines unless stopped
        while not self._stop_event.is_set():
            
            #read in line
            raw = self.ser.readline().decode("utf-8", errors="ignore")
            
            #split on \r since last line doesn't have a \n
            for line in raw.split("\r"):
                line = line.strip()

                # if line is none continue
                if not line:
                    continue
            
                #disregard if line starts with pmt_base_rd
                if line.startswith("pmt_base_rd"):
                    continue
                    
                #create library
                if "=" in line:
                    key, value = line.split("=",1)
                    key = key.strip()
                    value = value.strip()
                    
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                    
                    data[key] = value
                    
                #for message that has ended          
                if "c72=" in line:
                    #add the timestamp as the first column
                    data = {"timestamp": datetime.now(), **data}
                    
                    
                    
                    row = pd.DataFrame([data])
                    
                    #add the index and then increment it
                    row.index = [self.current_idx]
                    self.current_idx = self.current_idx + 1
                    
                    self.current_df = pd.concat([self.current_df,row])
                    #print(self.current_df)

        
                    #reset data
                    data = {}

    
    def start_read(self):
        #clear both buffers before starting a new read
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
        #start the thread that will read the serial
        self._thread.start()
        
        self.current_idx = 0
        self.current_df = pd.DataFrame()
        
    def stop_read(self):
        self._stop_event.set()
        self._thread.join()
        
    def close(self):
        self.stop_read()
        self.ser.close()
    
        
if __name__ == "__main__":
    opc = OPC('COM5')