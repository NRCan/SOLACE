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
from math import floor
from itertools import chain

class TID:
    def __init__(self,region,file_location:str,timestep:int|float=None,time_horizon:str=None,time_of_year:float|int=None)->None:
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
        # self.wbt.set_working_dir(r'C:\Users\egaucher\Documents\Output')
        if timestep==60 and time_horizon=='year':
            self.Weather_dataframe=self.Weather_dataframe[self.Weather_dataframe.index.minute==0]
            
    
        Rasterized_segments = open_file(self.raster_file)
        #Get 2D numpy arrays
        Rasterized_segments_array=Rasterized_segments.read(1)

        #Turn arrays into 1D vectors 
        self.Rasterized_segments_ravel=Rasterized_segments_array.ravel()

        del Rasterized_segments_array
        del Rasterized_segments

        #Create a dataframe of 0s with hours as rows and FIDs as columns
        #Rasterized_segments_ravel includes -999. We are counting the number of unique values with this, which we want to exclude. But we then wish to add 1, so this is equivalent.
        if time_horizon=='year':
            self.TID = DataFrame(index = range(int(8760*60/timestep)), columns = arange(1,len(unique(self.Rasterized_segments_ravel)),1))
        elif time_horizon=='inst':
            index=self.Weather_dataframe.reset_index()
            self.TID = DataFrame(index = index[index==index.iloc[int(time_of_year/timestep)]], columns = arange(1,len(unique(self.Rasterized_segments_ravel)),1))
        elif type(time_horizon)==type(15):
            index=self.Weather_dataframe.reset_index()
            self.TID = DataFrame(index = index.loc[(index['index']<=index.iloc[int((time_of_year+time_horizon)/timestep)]['index']) & (index['index']>=index.iloc[int(time_of_year/timestep)]['index'])]['index'], columns = arange(1,len(unique(self.Rasterized_segments_ravel)),1))
        else:
            self.TID = DataFrame(index = self.Weather_dataframe.index, columns = arange(1,len(unique(self.Rasterized_segments_ravel)),1))

    def timestep(self,i:int|float,timestep:int|float)->DataFrame:
        """
        Function to calculate the hourly time in daylight for the shading analysis
        Parameters
        -------
        i : int|float
            current time step
        timestep: int|float
            the duration between timesteps
        
        Returns
        -------
        TID : Dataframe
            Output containing all the TID information for each segement. Meant to be 
            an input to a POA function

        """
        
        if self.Weather_dataframe['GHI'][floor(i/timestep)]>0:
            self.wbt.time_in_daylight(
                self.mosaic,
                self.file_location+r'\Timeindaylight_timestep_'+self.file_classifier+'.tif',
                self.latitude, 
                self.longitude, 
                az_fraction=0.5, 
                max_dist=50.0, 
                utc_offset=self.UTC_offset, 
                start_day= self.Weather_dataframe.index[int(floor(i/timestep))].dayofyear, 
                end_day= self.Weather_dataframe.index[floor((i+timestep)/timestep)].dayofyear, 
                start_time= str(self.Weather_dataframe.index[floor(i/timestep)].hour)+':'+str(self.Weather_dataframe.index[floor(i/timestep)].minute)+':'+'0',
                end_time= str(self.Weather_dataframe.index[floor((i+timestep)/timestep)].hour)+':'+str(self.Weather_dataframe.index[floor((i+timestep)/timestep)].minute)+':'+'0')
            # print(str(self.Weather_dataframe.index[floor((i+timestep)/timestep)].hour)+':'+str(self.Weather_dataframe.index[floor((i+timestep)/timestep)].minute)+':'+'0')
            if path.isfile(self.file_location+r'\Timeindaylight_timestep_'+self.file_classifier+'.tif'):
                TID_avg_by_FID=self.extract_TID(self.file_location+r'\Timeindaylight_timestep_'+self.file_classifier+'.tif')
                # print(TID_avg_by_FID.values)
                #Put data into TimeInDaylight dataframe
                if timestep==60:
                    self.TID.iloc[int(i/timestep)] = TID_avg_by_FID.values
                else:
                    self.TID.loc[self.Weather_dataframe.index[int(i/timestep)]] = TID_avg_by_FID.values
                print("Hour of the year: ",round(i/60,2))
                # del TID_avg_by_FID
        return self.TID
        
    def hourly_validation(self,file:str)->DataFrame:
        """
        Function used to validate the use of time in daylight (TID) function for the
        shading analysis. The function has the coordinates and positions of the 
        measurement locations on the two SunEYE houses, commented out (Alex's and
        Louis-Phillipe's houses)

        Parameters
        ----------
        file : string
            The input file name and path, used to create the shading file. File format
            is .tif

        Returns
        -------
        TID : Dataframe
            Output containing all the TID information for each segement. Meant to be 
            an input to a POA function

        """
        ### setting up rasterized segments ####
        Rasterized_segments = open_file(r'C:\Users\egaucher\Documents\LP_SunEYE_crop.tif')
        Rasterized_segments_data=Rasterized_segments.read(1)

        
        #Turn arrays into 1D vectors 
        Rasterized_segments_ravel=Rasterized_segments_data.ravel()
        
        #Create a dataframe of 0s with hours as rows and FIDs as columns
        #Rasterized_segments_ravel includes -999. We are counting the number of unique values with this, which we want to exclude. But we then wish to add 1, so this is equivalent.
        
        #Alex'h house, size = 11 (with pixel 4 neighbors, 9 without)
        #LP's house, size = 8
        self.TID = DataFrame(index = arange(0,8760,0.25), columns = arange(1,8,1))

        # TID = pd.DataFrame(index = Weather_dataframe.index, columns = np.arange(1,9,1))
        
        # for i in arange(0,8760,1):
        for i in arange(0,8760,0.25):
            j=floor(i)
            if (round(i%1,2))==0:
                minute=30
                hour=self.Weather_dataframe.index[j].hour
                minute1=45
                hour1=self.Weather_dataframe.index[j].hour
            elif (round(i%1,2))==0.25:
                minute=45
                hour=self.Weather_dataframe.index[j].hour
                minute1=0
                hour1=self.Weather_dataframe.index[j].hour+1
            elif (round(i%1,2))==0.50:   
                minute=0
                hour=self.Weather_dataframe.index[j].hour+1
                minute1=15
                hour1=self.Weather_dataframe.index[j].hour+1
            else:   
                minute=15
                hour=self.Weather_dataframe.index[j].hour+1
                minute1=30
                hour1=self.Weather_dataframe.index[j].hour+1
            
            
            if self.Weather_dataframe['GHI'][j]>0:
                # hour=Weather_dataframe.index[i].hour
                # hour1=Weather_dataframe.index[i+1].hour
                
                # minute=Weather_dataframe.index[i].minute
                # minute1=Weather_dataframe.index[i+1].minute
                self.wbt.time_in_daylight(
                    file,
                    # r'\\w-var-200105\D\scidata\REN1\Varennes_PV_potential_buildings\Python_and_QGIS_outputs\Timeindaylight_hourly.tif',
                    r'C:\Users\egaucher\Documents\Suneye_TID_crop_LP.tif',
                    45.6288, 
                    -73.3840, 
                    az_fraction=8.0, 
                    max_dist=50.0, 
                    utc_offset="-05:00", 
                    start_day= self.Weather_dataframe.index[j].dayofyear, 
                    end_day= self.Weather_dataframe.index[j].dayofyear, 
                    start_time= str(hour)+':'+str(minute),
                    end_time= str(hour1)+':'+str(minute1))
            
                #######Calculating_average_TimeInDaylight_for_rasterized_FID_hourly#####
                # Timeindaylight_hourly=open_file("//w-var-200105/D/scidata/REN1/Varennes_PV_potential_buildings/Python_and_QGIS_outputs/Timeindaylight_hourly.tif")
                Timeindaylight_hourly=open_file(r'C:\Users\egaucher\Documents\Suneye_TID_crop_LP.tif')
                
                #Get 2D numpy arrays 
                Timeindaylight_hourly_data=Timeindaylight_hourly.read(1)
                # 
                Timeindaylight_hourly_ravel=Timeindaylight_hourly_data.ravel()
                
                
                #Group together into a matrix
                Rasterized_FID_and_Timeindaylight_hourly=column_stack((Rasterized_segments_ravel,Timeindaylight_hourly_ravel))
                
                #Get rid of data where there is no FID (-999 value, or simply FID negative), i.e. keep only positive FID 
                # Rasterized_FID_and_Timeindaylight_hourly = Rasterized_FID_and_Timeindaylight_hourly[Rasterized_FID_and_Timeindaylight_hourly[:,0]>0]
                
                #Convert to dataframe
                FID_TID_df=DataFrame(data=Rasterized_FID_and_Timeindaylight_hourly,columns=['FID_raster','TID'])
                FID_TID_df=FID_TID_df[FID_TID_df['FID_raster']>0]
                #Sort values in order of increasing FID
                FID_TID_df=FID_TID_df.sort_values(by=['FID_raster'])
                
                #Alex's House
                # upper_left_corner=[311331.18,5061072.86] #is index (1,12) or 34 (row*(matrix_col#)+col)
                # upper_mid=[311327.47,5061068.62] #is index (5,8) or 118
                # lower_left_corner=[311326.61,5061067.60] #is index (6,7) or 139
                # mid_point=[311333.81,5061070.37] #is index (3,14) or 80
                #mid_neighbor1=[311334.74,5061070.49] #is index (3,15) or 81
                
                #mid_neighbor1=[311333.47,5061069.88] #is index (4,14) or 102
                # upper_right_corner=[311337.75,5061067.32] #is index (6,18) or 150
                # right_mid=[311335.75,5061064.47] #is index (9,16) or 214
                # lower_right_corner=[311333.60,5061061.55] #is index (12,14) or 278
                # lower_mid=[311330.16,5061064.83] #is index (9,11) or 209
                # TID_suneye=FID_TID_df[FID_TID_df['FID_raster'].isin([663,664])]
                #[upper_left corner(1), upper_mid(2),lower_left corner(3),mid_point(4),upper_right_corner(5),right_mid(6),lower_right_corner(7),lower_mid(8)
                # TID_out=TID_suneye.loc[[34,118,139,80,150,214,278,209,81,102]]['TID']
                #Calculate average TimeInDaylight (TID) for each FID
                # TID_avg_by_FID=FID_TID_df.groupby('FID_raster')['TID'].mean()
                # del FID_TID_df
                
                #[lower_left corner(2), lower_mid(3),right mid(4),upper_right_corner(5),upper_mid(6),upper_left_corner(7),left_mid(9)
                #lower_left corner=[309436.92,5060807.72] 2778 (192,436) or 192436
                # lower_mid=[309441.31,5060804.49] 2780 (195,441) or 195441
                # right mid=[309449.47,5060809.24] 2777 (190,449) or 190449
                # upper_right_corner=[309452.90,5060814.74] 2779 (185, 452) or 185452
                # upper_mid=[309448.62,5060817.76] 2779 (182, 448) or 182448
                # upper_left_corner=[309444.82,5060819.98] 2786 (180,444) or 180444
                # left_mid=[309440.31,5060814.26] 2781 (185,440) or 185440
                TID_suneye=FID_TID_df[FID_TID_df['FID_raster'].isin([91083,91084,91085,91086,91087,91088,91089,91090,91091,91092,91082])]
                TID_out=TID_suneye.loc[[192436,195441,190449,185452,182448,180444,185440]]['TID']
                # #Put data into TimeInDaylight dataframe
                self.TID.loc[i] = TID_out.values
                # TID.loc[Weather_dataframe.index[i]] = TID_out.values

        return self.TID

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

        output_file=self.file_location+r'\Timeindaylight_annual.tif'


        
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
            if self.Weather_dataframe['GHI'][i]>0:
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
                    # del TID_avg_by_FID

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
        #Not implemented yet, but in Gagnon (2016):
        #"The hours of sunlight for the four days were averaged to determine an average number of hours 
        #of daily sunlight for each square meter"
        #"For each month, we determined a different threshold of illumination required to classify a cell as 
        #being in sunlight; March requires 60% illumination (values > 152), June requires 70% illumination 
        #(values > 178), September requires 60% illumination (values > 152), and December requires 50% 
        #illumination (values > 127)."
        
        if rep_days==12:
            total_range = chain(range(480,504),range(1224,1248),range(1896,1920),range(2640,2664),
                            range(3360,3384), range(4104,4128), range(4824,4848),range(5568,5592),
                            range(6312,6336), range(7032,7056),range(7776,7800),range(8496,8520))
        else:
            total_range = chain(range(1896,1920), range(4104,4128), range(6312,6336), range(8496,8520)) #representative days of March, June, September, and december 21
        
        temp=[]
        for i in total_range:
            if self.Weather_dataframe['GHI'][i]>0:
                self.wbt.time_in_daylight(
                    self.mosaic,
                    self.file_location+r'\Timeindaylight_rep.tif',
                    self.latitude, 
                    self.longitude, 
                    az_fraction=15.0, 
                    max_dist=50.0, 
                    utc_offset=self.UTC_offset, 
                    start_day= self.Weather_dataframe.index[i].dayofyear, 
                    end_day= self.Weather_dataframe.index[i].dayofyear, 
                    start_time= str(self.Weather_dataframe.index[i].hour)+':'+str(self.Weather_dataframe.index[i].minute),
                    end_time= str(self.Weather_dataframe.index[i+1].hour)+':'+str(self.Weather_dataframe.index[i+1].minute))
            
                if path.isfile(self.file_location+r"\Timeindaylight_rep.tif"):
                    TID_avg_by_FID=self.extract_TID(self.file_location+r"\Timeindaylight_rep.tif")
                    print("Hour of the year: ",i)
                
                #Put data into TimeInDaylight dataframe
                temp.append(TID_avg_by_FID.values)
            else:
                temp.append(zeros((1,len(self.TID.iloc[1])))[0])
        # TID_avg_area=mean(temp)
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
    # Timeindaylight_hourly=open_file("//w-var-200105/D/scidata/REN1/Varennes_PV_potential_buildings/Python_and_QGIS_outputs/Timeindaylight_hourly.tif")
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
