# -*- coding: utf-8 -*-
"""
Created on Tue Nov  1 08:51:08 2022

@author: egaucher
"""

import TimeInDaylight
import POA
from tools import file_handle
from pandas import ExcelWriter, DataFrame
import location
import os
from math import floor

def print_results(data: list,region:location) ->None:
    """
    Function used to print the outputted results to the console.

    Parameters
    ----------
    data : list
        list of outputs from the code
    region: location
        object containing location-specific data
    """
    print('\n**OUTPUT**\n')
    print('City:\t',region.file_classifier)
    print('Total PV capacity (MW):\t',round(data[0],2))
    print('Total PV energy (GWh):\t',round(data[1],2))

    try:
        print('Total PV capacity - IEA (MW):\t',round(data[2],2))
        print('Total PV energy - IEA (GWh):\t',round(data[3],2))
        print('Total area of segments (km2):\t',round(data[4],4))
        print('Total building footprint area (km2):\t',round(data[5],4))
        print("End of results")
    except:
        print("End of results")

def write_output_file(data: list,file_location: str,region:location) ->None:
    """
    Function used to write the results into a text file and the coefficients to an excel sheet.

    Parameters
    ----------
    data : list
        list of outputs from the code
    file_location: str
        location to write the files
    region: location
        object containing location-specific data
    """
    with open(file_location+r'\output_'+region.file_classifier+'.txt','w') as file:
        file.write('City:\t'+region.file_classifier+'\n')
        file.write('Total PV capacity (MW):\t'+str(round(data[0],2))+'\n')
        file.write('Total PV energy (GWh):\t'+str(round(data[1],2))+'\n')
        try:
            file.write('Total PV capacity - IEA (MW):\t'+str(round(data[2],2))+'\n')
            file.write('Total PV energy - IEA (GWh):\t'+str(round(data[3],2))+'\n')
            file.write('Total area of segments (km2):\t'+str(round(data[4],2))+'\n')
            file.write('Total building footprint area (km2):\t'+str(round(data[5],2))+'\n')
        except:
            print("Could not write all results")
    try:
        with ExcelWriter(file_location+r'\Coefs_'+region.file_classifier+'.xlsx') as writen:
            data[6].to_excel(writen,sheet_name="Capacity_shaded",header=True,index=None)
            data[7].to_excel(writen,sheet_name="Electricity_shaded",header=True,index=None)
    except:
        print("Could not write all results")
    return

def annual_analysis(region: location,file_location: str,performance_ratio:float,module_efficiency:float)->list[float]:
    """
    Setups and runs the  analysis on an annual basis.

    Parameters
    ----------
    region : location
        object containing location-specific data
    file_location: str
        location to write the files
        performance_ratio:float
        performance ratio of the PV system
    module_efficiency:float
        Module efficiency of the PV system
    """
    shading=TimeInDaylight.TID(region,file_location)
    TID=shading.annual()
    technical_potential=POA.calculate_technical_potential(TID,region,performance_ratio,module_efficiency)
    data=technical_potential.annual()
    return data

def rep_analysis(rep_days: int,region: location,file_location: list,performance_ratio:float,module_efficiency:float)->list[float]:
    """
    Set ups and runs the analysis for either 12 or 4 representative days during the year. 12 days will use one day per month. 4 days will use the equinox days.
    
    Parameters
    ----------
    rep_days : int
        number of representative days to use in a year, 4 (equinox) or 12 (once per month)
    region : location
        object containing location-specific data
    file_location: str
        location to write the files
    performance_ratio:float
        performance ratio of the PV system
    module_efficiency:float
        Module efficiency of the PV system
    """
    if rep_days==12:
        saved_file=file_location+r'\TimeInDaylight_rep_12_' + region.file_classifier+'.ftr'
    else:
        saved_file=file_location+r'\TimeInDaylight_rep_4_' + region.file_classifier+'.ftr'
    file_save=file_handle()    
    if not(os.path.isfile(saved_file)):
        shading=TimeInDaylight.TID(region,file_location)
        print("Starting shading")
        TID=shading.representative(rep_days)
        file_save.write_file(TID,saved_file)
        TID.set_index('index',inplace=True)
        print("Shading completed\n")
    else:
        TID=file_save.extract_data(saved_file)
    technical_potential=POA.calculate_technical_potential(TID,region,performance_ratio,module_efficiency)
    data=technical_potential.rep(rep_days)
    return data


