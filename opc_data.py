#works with Brechtel datafiles from SEMS v5.3.0
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


class OPCdata():
    def __init__(self,path):
        self.path = path
        #import raw dataframe and stored as self.df
        self.df = pd.read_csv(path)
        self.df_proc = self.df[[f"c{i}" for i in range(1, 73)]]
        
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
        
        self.mean_distribution = self.df_proc.mean(axis=0)
        
        
    def plot_mean_distribution(self):
        plt.plot(self.bin_diams,self.mean_distribution)
        plt.xscale("log")
        plt.ylabel("dN/dlogD")
        plt.xlabel("Diameter [nm]")

    
