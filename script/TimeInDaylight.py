# -*- coding: utf-8 -*-
"""
Created on Fri Apr 16 15:24:03 2021

@author: nsalimza and egaucher
"""
from WBT.whitebox_tools import WhiteboxTools
from pandas import DataFrame
from numpy import arange,unique,column_stack,zeros 
from rasterio import open as open_file
from pvlib import iotools
from os import path
from itertools import chain

class TID:
    def __init__(self,region,file_location:str)->None:
        self.raster_file=region.raster_file
        self.latitude=region.latitude
        self.longitude=region.longitude
        self.altitude=region.altitude
        self.UTC_offset=region.UTC_offset
        self.mosaic=region.mosaic
        self.weather_file_address=region.weather_file
        self.file_location=file_location
        self.file_classifier=region.file_classifier
        if region.latitude>60:
            self.Weather_dataframe=iotools.read_epw(region.weather_file)[0]
            self.Weather_dataframe.rename(columns={'ghi':'GHI'},inplace=True)
            self.Weather_dataframe.rename(columns={'temp_air':'Temperature'},inplace=True)
        else:
            self.Weather_dataframe=iotools.read_psm3(region.weather_file)[0] # https://pvlib-python.readthedocs.io/en/stable/generated/pvlib.iotools.read_psm3.html
            self.Weather_dataframe.rename(columns={'ghi':'GHI'},inplace=True)
            self.Weather_dataframe.rename(columns={'dni':'DNI'},inplace=True)
            self.Weather_dataframe.rename(columns={'dhi':'DHI'},inplace=True)
            self.Weather_dataframe.rename(columns={'temp_air':'Temperature'},inplace=True)

        self.wbt=WhiteboxTools()
        self.wbt.set_verbose_mode(False)
            
        Rasterized_segments = open_file(self.raster_file)
        #Get 2D numpy arrays
        Rasterized_segments_array=Rasterized_segments.read(1)

        #Turn arrays into 1D vectors 
        self.Rasterized_segments_ravel=Rasterized_segments_array.ravel()

        del Rasterized_segments_array
        del Rasterized_segments

        #Create a dataframe of 0s with hours as rows and FIDs as columns
        #Rasterized_segments_ravel includes -999. We are counting the number of unique values with this, which we want to exclude. But we then wish to add 1, so this is equivalent.

        self.TID = DataFrame(index = self.Weather_dataframe.index, columns = arange(1,len(unique(self.Rasterized_segments_ravel)),1))

    def annual(self)->DataFrame:
        """
        Function used to calculate the annual time in daylight (TID) function for the
        shading analysis. 

        Returns
        -------
        TID : Dataframe
            Output containing all the TID information for each segement. Meant to be 
            an input to a POA function

        """
        
        #TimeinDaylight
        #-i, --dem	Input raster DEM file
        #-o, --output	Output raster file
        #--az_fraction	Azimuth fraction in degrees
        #--max_dist	Optional maximum search distance. Minimum value is 5 x cell size
        #--lat	Centre point latitude
        #--long	Centre point longitude
        #--utc_offset	UTC time offset, in hours (e.g. -04:00, +06:00)
        #--start_day	Start day of the year (1-365)
        #--end_day	End day of the year (1-365)
        #--start_time	Starting hour to track shadows (e.g. 5, 5:00, 05:00:00). Assumes 24-hour time: HH:MM:SS. 'sunrise' is also a valid time
        #--end_time	Starting hour to track shadows (e.g. 21, 21:00, 21:00:00). Assumes 24-hour time: HH:MM:SS. 'sunset' is also a valid time
        
        ########

        output_file=self.file_location+r'\Timeindaylight_annual_'+self.file_classifier+'.tif'


        
        self.wbt.time_in_daylight(
            self.mosaic,
            output_file,
            self.latitude, 
            self.longitude, 
            az_fraction=15.0, 
            max_dist=50.0, 
            utc_offset=self.UTC_offset, 
            start_day= 1, 
            end_day= 365, 
            start_time="00:00:00",
            end_time="23:59:59")
        self.TID=self.extract_TID(output_file)
        return self.TID

    def hourly(self)->DataFrame:
        """
        Function to calculate the hourly time in daylight for the shading analysis

        Returns
        -------
        TID : Dataframe
            Output containing all the TID information for each segement. Meant to be 
            an input to a POA function

        """
        for i in arange(0,8760,1):
            if self.Weather_dataframe.iloc[i].loc['GHI']>0:
                self.wbt.time_in_daylight(
                    self.mosaic,
                    self.file_location+r'\Timeindaylight_hourly_'+self.file_classifier+'.tif',
                    self.latitude, 
                    self.longitude, 
                    az_fraction=15.0, 
                    max_dist=50.0, 
                    utc_offset=self.UTC_offset, 
                    start_day= self.Weather_dataframe.index[i].dayofyear, 
                    end_day= self.Weather_dataframe.index[i].dayofyear, 
                    start_time= str(self.Weather_dataframe.index[i].hour)+':'+str(self.Weather_dataframe.index[i].minute),
                    end_time= str(self.Weather_dataframe.index[i+1].hour)+':'+str(self.Weather_dataframe.index[i+1].minute))
                
                if path.isfile(self.file_location+r'\Timeindaylight_hourly_'+self.file_classifier+'.tif'):
                    TID_avg_by_FID=self.extract_TID(self.file_location+r'\Timeindaylight_hourly_'+self.file_classifier+'.tif')
                    
                    #Put data into TimeInDaylight dataframe
                    self.TID.loc[self.Weather_dataframe.index[i]] = TID_avg_by_FID.values
                    print("Hour of the year: ",i)

        return self.TID

    def representative(self,rep_days:int)->DataFrame:
        """
        Function to calculate the shading using only representative days.

        Parameters
        ----------
        rep_days : int
            the number of representative days to use in the year. Either 4 (one on each equinox) or 
            12 (once per month)

        Returns
        -------
        TID : Dataframe
            Output containing all the TID information for each segement. Meant to be 
            an input to a POA function.

        """
        
        if rep_days==12:
            total_range = chain(range(480,504),range(1224,1248),range(1896,1920),range(2640,2664),
                            range(3360,3384), range(4104,4128), range(4824,4848),range(5568,5592),
                            range(6312,6336), range(7032,7056),range(7776,7800),range(8496,8520))
        else:
            total_range = chain(range(1896,1920), range(4104,4128), range(6312,6336), range(8496,8520)) #representative days of March, June, September, and december 21
        
        temp=[]
        for i in total_range:
            if self.Weather_dataframe.iloc[i].loc['GHI']>0:
                self.wbt.time_in_daylight(
                    self.mosaic,
                    self.file_location+r'\Timeindaylight_rep_'+self.file_classifier+'.tif',
                    self.latitude, 
                    self.longitude, 
                    az_fraction=15.0, 
                    max_dist=50.0, 
                    utc_offset=self.UTC_offset, 
                    start_day= self.Weather_dataframe.index[i].dayofyear, 
                    end_day= self.Weather_dataframe.index[i].dayofyear, 
                    start_time= str(self.Weather_dataframe.index[i].hour)+':'+str(self.Weather_dataframe.index[i].minute),
                    end_time= str(self.Weather_dataframe.index[i+1].hour)+':'+str(self.Weather_dataframe.index[i+1].minute))
            
                if path.isfile(self.file_location+r"\Timeindaylight_rep_"+self.file_classifier+'.tif'):
                    TID_avg_by_FID=self.extract_TID(self.file_location+r"\Timeindaylight_rep_"+self.file_classifier+'.tif')
                    print("Hour of the year: ",i)
                
                    #Put data into TimeInDaylight dataframe
                    temp.append(TID_avg_by_FID.values)
            else:
                temp.append(zeros((1,len(self.TID.iloc[1])))[0])
        TID = DataFrame(temp)
        return TID
    

    def extract_TID(self,filename:str)->DataFrame:
     """
     Function used to open and extract the TID information from the file outputted
     from the TID function.

     Parameters
     ----------
     filename : string
        TID output file name and path.
    

     Returns
     -------
     TID_avg_by_FID : Dataframe
        Output containing all the TID information for each segement. Meant to be 
        an input to a POA function.

     """
     Rasterized_segments = open_file(self.raster_file)
    #Get 2D numpy arrays
     Rasterized_segments_array=Rasterized_segments.read(1)
    
    #Turn arrays into 1D vectors 
     Rasterized_segments_ravel=Rasterized_segments_array.ravel()
    
     del Rasterized_segments_array
     del Rasterized_segments
    #######Calculating_average_TimeInDaylight_for_rasterized_FID_hourly#####
     Timeindaylight_hourly=open_file(filename)
      #Get 2D numpy arrays 
     Timeindaylight_hourly_data=Timeindaylight_hourly.read(1)
     
    #Turn arrays into 1D vectors
     Timeindaylight_hourly_ravel=Timeindaylight_hourly_data.ravel()
    
     #Group together into a matrix
     Rasterized_FID_and_Timeindaylight_hourly=column_stack((Rasterized_segments_ravel,Timeindaylight_hourly_ravel))
     
     #Get rid of data where there is no FID (-999 value, or simply FID negative), i.e. keep only positive FID 
     Rasterized_FID_and_Timeindaylight_hourly = Rasterized_FID_and_Timeindaylight_hourly[Rasterized_FID_and_Timeindaylight_hourly[:,0]>0]
     
     #Convert to dataframe
     FID_TID_df=DataFrame(data=Rasterized_FID_and_Timeindaylight_hourly,columns=['FID_raster','TID'])
     
     #Sort values in order of increasing FID
     FID_TID_df=FID_TID_df.sort_values(by=['FID_raster'])
    #  print('Filterd {} pixels from data that are negative\n'.format(len(FID_TID_df[FID_TID_df['TID']<0])) )
     FID_TID_df[FID_TID_df['TID']<0]['TID']=0
     
     #Calculate average TimeInDaylight (TID) for each FID
     TID_avg_by_FID=FID_TID_df.groupby('FID_raster')['TID'].mean()
     Timeindaylight_hourly.close()
     return TID_avg_by_FID
    
