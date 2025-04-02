# -*- coding: utf-8 -*-
"""
Created on Fri Jan 20 09:02:22 2023

@author: egaucher
"""

import os
import glob
from pandas import read_parquet, read_feather
class file_handle:
    def rename_files(self,LAS_location):
        """
        Function rename las files to shorten the file names

        Parameters
        ----------
        LAS_location : string
            path to LAS files to rename
.
        Returns
        -------
        None

        """
        os.chdir(LAS_location)
        for file in glob.glob('*.tif',recursive=True):
            new_file=''.join([file.split('_')[7],"_",file.split('_')[8],'.tif'])
            os.rename(file,new_file)
            
    def write_file(self,TID_avg_by_FID,file):
        """
        Function save the shading data

        Parameters
        ----------
        TID_avg_by_FID : DataFrame
            dataframe with the shading data
        file : string
            location of the file to be saved
.
        Returns
        -------
        None

        """
        TID_avg_by_FID.reset_index(inplace=True)
        TID_avg_by_FID.columns=TID_avg_by_FID.columns.astype(str)
        
        TID_avg_by_FID.to_feather(file)    

    def extract_data(self,file):
        """
        Function extract the saved shading data from the write_file function

        Parameters
        ----------
        file : string
            location of the file to be extracted
.
        Returns
        -------
        None

        """
        TID_avg_by_FID=read_feather(file)
        TID_avg_by_FID.set_index('index',inplace=True)
        TID_avg_by_FID.columns=TID_avg_by_FID.columns.astype(int)
        return TID_avg_by_FID
