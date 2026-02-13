# -*- coding: utf-8 -*-
"""
Created on Fri Feb 13 13:20:57 2026

@author: peo0005
"""

import serial

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
        ser.timeout = 1

        #open serial port
        ser.open()        
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        #save serial port 
        self.ser = ser
        
    #get T data
    def read(self):
            #buffer to start message
            buffer = []
            
            while True:
                #read in line
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                
                #disregard if line starts with pmt_base_rd
                if line.startswith("pmt_base_rd"):
                    continue
                
                #add line to buffer
                buffer.append(line)

                #if its the end of the message, stop reading
                if "c71=" in line:
                    break
                
            message = "\n".join(buffer)
            print(message)
        
        
if __name__ == "__main__":
    opc = OPC('COM5')