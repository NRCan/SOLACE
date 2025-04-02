# -*- coding: utf-8 -*-
"""
Created on Tue Nov  1 08:51:08 2022

@author: egaucher
"""
import Lidar
import Segmentation

class location:
    """
    Contains location specific data inlcuding file locations for the different cities,
    latitude/longitude, timezone, etc.

    """
    def __init__(self,city:str,file_location:str,*args)->None:
        """
        Lists the inputs for a city. The variables included in this are the:
        Building footprint file, lidar files, raster (rasterized shapefile) and shapefiles,
        weather file, latitude, longitude, electricity cost for the the lifetime of the PV,
        the timezone (UTC offset), altitude, and unique name of the set of files for that city

        Parameters
        ----------
        city: str
            name of a city that is in this list
        file_location: str
            the file location (path) to the folder with all the inputs and outputs for the analysis
        args: any
            only used if the user wants to use a city not listed in the file. This is where the user will list the location of the city's datafiles and location specifications.
            order should be: 
                1. building footprint file location and name, (ex. 'Calgary\building_footprint\Calgary.shp')
                2. lidar data folder location, (ex. 'Calgary\LAS files')
                3. the location to put the mosaic file and name of the file, (ex. 'Calgary\Inputs\mosaic_calgary.tif')
                4. the location to put the rasterized vector file and name of the file (ex. 'Calgary\Inputs\shape_calgary.tif')
                5. Location to generate the shapefile after segmentation (ex. 'Calgary\Inputs\shape_calgary.shp')
                6. location of the weather file in file format SAM CSV from NSRDB PSM3 weather files (ex. 'Calgary\Inputs\weather_calgary.csv')
                7. city's latitude (ex. 51.0447)
                8. city's longitude (ex. -114.0719)
                9. UTC offset as a string (ex. "-07:00")
                10. city's altitude (ex. 1045)
                11. file classifier, what city to add to each of the outputted files (ex. 'calgary')
                
                For the economic and market part of the code input the:
                12. city's electricity cost, list floats of length 30 in $/kwh
                13. capacity coefficiency (generated from the file POA.py)
                14. electricity coefficiency (generated from the file POA.py)
        
        """
        
        if args==None:
            raise Exception("Misspelt city name or city not implemented in code")
        else:
            self.bldg_footprint=args[0]
            self.lidar=args[1]
            self.mosaic=args[2]
            self.raster_file=args[3]
            self.shapefile=args[4]
            self.weather_file=args[5]
            self.latitude=args[6]
            self.longitude=args[7]
            
            self.UTC_offset=args[8]
            self.altitude=args[9]
            self.file_classifier=args[10]
            try:
                self.elec_cost=args[11]
                self.cap_cofficient_shade=args[12]
                self.elec_coefficient_shade=args[13]
            except:
                self.elec_cost=[0]
                self.cap_cofficient_shade=[0]
                self.elec_coefficient_shade=[0]
        self.construct_files=Lidar.DSM_files()
        
    
    def run_lidar(self,resolution: float|int=1,onefile:bool=False,file=None,out=None)->None:
        """
        Function used to create the digital surface models (DSM) files from las files
        either from only one file or all files within a folder.

        Parameters
        ----------
        resolution : float or int
            Resolution of the output DSM files
        onefile: bool
            Check if only one file is needed to be converted. Default is False.
        file: string
            file location for the output DSM files. File location is required if onefile is True or if the
            required folder is not the same as definied for the location.
        """
        
        if onefile:
            self.construct_files.DSM_one(file,resolution,out)
        else:
            file = self.lidar
            self.construct_files.DSM(file,resolution)
            
    def run_seg(self,onefile:bool=False,input_file:bool=False)->None:
            """
            
            Function used to create the rooftop segmentation files for either a folder of .tif files or
            only one file

            Parameters
            ----------

            onefile: bool
                Check if only one file is needed to be converted. Default is False.
            input_file: string
                file location for the output files. File location is required if onefile is True or if the
                required folder is not the same as definied for the location.
            """
            bldg_footprint=self.bldg_footprint
            shapefile=self.shapefile
            if onefile:
                Segmentation.one_tile(input_file,bldg_footprint,shapefile)
            else:
                directory= self.lidar
                Segmentation.all_tiles(directory,bldg_footprint,shapefile)


    def run_mosaic(self)->None:
        """
        Combines all raster files (.tif) into one file, creating a "mosaic" file of the different tiles.
        """
        directory= self.lidar
        output_file=self.mosaic
        self.construct_files.mosaic(directory,output_file)
    
    def run_lidar_thin(self,resolution_thin:float|int=1/5)->None:
        """
        Reduce the resolution of the lidar files (.las) within a grid pattern.
        """
        self.construct_files.modify_lidar_density(resolution_thin,self.lidar)
        # file=''.join([self.lidar,'/Point_Cloud_Density'])
        # self.construct_files.DSM(file,resolution)
