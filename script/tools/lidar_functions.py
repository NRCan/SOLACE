# -*- coding: utf-8 -*-
"""
Created on Fri Jul 7 08:46 2023

@author: egaucher

This code is derived from the Whitebox Tools examples page here: https://www.whiteboxgeo.com/manual/wbt_book/tutorials/lidar.html 
for functions total_num_files, find_laz_files, laz2las and parallelize_zip
"""

import os, subprocess
import multiprocessing as mp 
from pandas import DataFrame
from bs4 import BeautifulSoup as bs
import glob
from WBT.whitebox_tools import WhiteboxTools
wbt = WhiteboxTools()
wbt.set_verbose_mode(False)


class lidar_functions:
    def __init__(self, city:str,directory:str,laszip_location:str)->None:
        self.city=city
        self.directory=directory
        self.laszip_location=laszip_location

    def total_num_files(self,input_dir:str)->str: # Gets the number of laz files in an input directory
        """
        Function to find laz files to las files in a specified directory
        and return the list of names with extention .laz in the diectory

        Parameters
        ----------
        input_dir : string
            input directory path
.       processed_files : string
            list of LAZ files already converted
        max_num  : int
            maximum number of files to convert in parallel

        Returns
        -------
        file_names  :  string
            list of laz file names 

        """
        files = os.listdir(input_dir)
        file_names = []
        for f in files:
            if f.endswith(".laz"): # Only count file names that end with .laz
                file_names.append(f)
        return file_names

    def find_laz_files(self,input_dir:str, processed_files:str, max_num:int = 1)->str: # Finds a specific number of laz files in an input directory
        """
        Function to find laz files to las files in a specified directory
        and return the list of names with extention .laz in the diectory

        Parameters
        ----------
        input_dir : string
            input directory path
.       processed_files : string
            list of LAZ files already converted
        max_num  : int
            maximum number of files to convert in parallel

        Returns
        -------
        file_names : string
            list of file names to convert 

        """
        files = os.listdir(input_dir)
        file_names = []
        for f in files:
            if f.endswith(".laz") and f not in processed_files: # Only select file names that end with .laz and have not already been selected
                if len(file_names) < max_num:
                    file_names.append(f)
                else:
                    break
        return file_names

    def parallelize_zip(self,in_files_list:str): # Converts laz to las using the laszip tool in LAStools 
        """
        Function to convert laz files to las files in a specified directory

        Parameters
        ----------
        in_files_list : string
            list of input LAZ files to convert
.
        Returns
        -------
        output_las_file  :  output_las_file
            output las file name to be converted

        """
        laszip_exe = self.laszip_location# Where lazsip executable exists 
        input_dir = self.directory+self.city+ "/LAZ files"  
        out_dir = self.directory+self.city+ "/LAS files" 

        Tile_name = os.path.join(input_dir, in_files_list) # Creates the full path name  of the .laz tile of interest
        LAZ_tile_name = in_files_list
        output_las_file = out_dir + '/'+ LAZ_tile_name.replace(".laz", ".las") # Creates the output file ending with .las
        print("Processing LAZ to LAS for {}".format(LAZ_tile_name))
        args = [laszip_exe, Tile_name, "-o", output_las_file] # Execute laszip tool
        proc = subprocess.Popen(args, shell=False)
        proc.communicate() # Wait for las zip to finish executing
        return output_las_file

    def laz2las(self)->None:
        """
        Function to convert laz files to las files in a specified directory

        """
        input_LAZ_dir = self.directory+self.city+ "/LAZ files"  
        num_batch_file = 8 # Number of laz files to be used at a time: change this to how many files you want per batch (make sure it is less than or equal to the total number of .las files to be converted) 
        pool = mp.Pool(mp.cpu_count()) # Multi-threaded command, counts number of cores user's CPU has

        processed_files = [] 
        
        total_files = self.total_num_files(input_LAZ_dir) # Gets the total number of files 
        flag = True # flag argument, this block of code will execute as long as true
        while flag:
            laz_file_names = self.find_laz_files(input_LAZ_dir, processed_files, num_batch_file) # Call function to get laz files
            if len(laz_file_names) >= 1: # Has to be zero or less than/equal to 1 in order to account for when only 1 file left 
                in_list = ""
                for i in range(len(laz_file_names)): # Go through files in directory to be used as the input files
                    if i < len(laz_file_names)-1:
                        in_list += f"{laz_file_names[i]};"
                    else:
                        in_list += f"{laz_file_names[i]}"
                    processed_files.append(laz_file_names[i])

                pool.map(self.parallelize_zip, laz_file_names) # Calls the parallelizing function on .LAZ to convert to .LAS
                print("Number of completed files {} of {}\n".format(len(processed_files), len(total_files)))
            
            else:
                flag = False

    def fix_las_QGIS(self,filename:str)->None:
        """
        File to correct the .las header when the following error appears in QGIS when adding a point cloud file (.las)

        "readers.las: Global encoding WKT flag not set for point format 6 - 10. qgis"
        Parameters
            ----------
            filename : string
                input LAS file  to fix.
        """

        f=open(filename,'rb+')
        f.seek(6)
        f.write(bytes([17,0,0,0]))
        f.close()
    
    def lidar_info(self,input_file:str,output_file:str)->None:
        """
            Calls the Whitebox tools function lidar_info. This function outputs a HTML file that summarizes the details of the LAS (LiDAR) files
            and, with the density input enabled, it can calculate and output the LAS average point cloud density (resolution)

            Parameters
            ----------
            input_file : string
                input LAS file for finding the data specifications.
            output_file : string
                output file for the data summary. With extension of HTML.
            Returns
            -------
            None 

            """
        wbt.lidar_info(
            input_file,
            output_file,
            density=True,
            vlr=True,
            geokeys=True)
    
    def run_lidar_info(self,output_density:str)->None:
        """
        This function exctracts the information ina lidar file
        and outputs into htlm files. The point cloud density is
        extracted and summarized in an output excel file.

        Parameters
        ----------
        output_density : string
            output file directory

        """

        #get al las files in the specified directory and get the output file name and directory with the format of E###-N#####.html
        for input_file in glob.glob(self.directory+self.city+ '/LAS files/*.las',recursive=True):
            output_file=''.join([self.directory+self.city+ '/',
                                input_file.split('/')[-1].split('\\')[-1].split('.')[0],'.html'] 
                                )
            self.lidar_info(input_file,output_file)
        html_location=self.directory+self.city+'/*.html'
        self.extract(html_location,output_density)
    
    def extract(self,html_location:str,output_location:str)->None:
        """
        This function exctract data from htmls, specifically it extracts 
        the point cloud density from the html files outputted by the 
        run_lidar_info function from the lidar_functions.py file. The 
        values are saved into an excel file 

        Parameters
        ----------
        html_location : string
            input files directory path.
        output_location : string
            output file directory

        """
        output=[]

        for filename in glob.glob(html_location,recursive=True):
            html=open(filename,"r")
            contents = html.read()
            text=bs(contents,'lxml')
            elem=text.findAll('p')[4].prettify()
            string=elem.split(' ')
            density = float(string[4])

            output.append([filename.split('\\')[1],density])
            html.close()

        dataframe=DataFrame(output)

        dataframe.to_excel(output_location,header=True, index=None)

if __name__=="__main__":
    #Please read the README for the use and folder format required for this function
    city='Calgary'
    directories='C:/Users/username/'
    laszip_location=r"C:\Users\username\Laz2Las\laszip.exe" #should be downloaded from https://rapidlasso.com/lastools/
    output_density=r'C:\Users\username\density.xlsx' #output file only
    converter=lidar_functions(city,directories,laszip_location)
    converter.laz2las()
    converter.run_lidar_info(output_density)
