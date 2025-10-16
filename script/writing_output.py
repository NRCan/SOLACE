# -*- coding: utf-8 -*-
"""
Created on Tue Nov  1 08:51:08 2022

@author: egaucher
"""

from pandas import ExcelWriter
import region_data

def print_results(data: list,region:region_data) ->None:
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
    print('region:\t',region.file_classifier)
    print('Total PV capacity (MW):\t',round(data[0],2))
    print('Total PV energy (GWh):\t',round(data[1],2))

    try:
        print('Number of buildings:\t',data[2])
        print('Total area of segments (km2):\t',round(data[3],4))
        print('Total building footprint area (km2):\t',round(data[4],4))
        print("End of results")
    except:
        print("End of results")

def write_output_file(data: list,file_location: str,region:region_data) ->None:
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
        file.write('region:\t'+region.file_classifier+'\n')
        file.write('Total PV capacity (MW):\t'+str(data[0])+'\n')
        file.write('Total PV energy (GWh):\t'+str(data[1])+'\n')
        try:
            file.write('Number of buildings:\t'+str(round(data[2],0))+'\n')
            file.write('Total area of segments (km2):\t'+str(data[3])+'\n')
            file.write('Total building footprint area (km2):\t'+str(data[4])+'\n')
        except:
            print("Could not write all results")
    try:
        with ExcelWriter(file_location+r'\Coefs_'+region.file_classifier+'.xlsx') as writen:
            data[5].to_excel(writen,sheet_name="Capacity",header=True,index=None)
            data[6].to_excel(writen,sheet_name="Electricity",header=True,index=None)
    except:
        print("Could not write all results")
    return


