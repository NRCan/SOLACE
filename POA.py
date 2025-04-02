# -*- coding: utf-8 -*-
"""
Created on Fri Apr 30 15:58:31 2021

@authors: nsalimza and egaucher
"""
from pvlib import iotools,irradiance,solarposition,atmosphere,pvsystem,temperature
from pandas import DataFrame,merge,concat
from  geopandas import read_file
from numpy import unique,zeros,arange,array,where,cos, pi,polyfit,poly1d
from rasterio import open as open_file
from math import floor
import economic_analysis
import market_analysis
import plotly.graph_objects as go
from itertools import chain
import plotly.io as pio
pio.templates.default = "simple_white"

class calculate_technical_potential:
    def __init__(self,TID_avg_by_FID: DataFrame,region: DataFrame,Performance_Ratio:float=0.75,PV_module_efficiency:float=0.225)->None:
        self.PV_module_efficiency=PV_module_efficiency
        self.Performance_Ratio= Performance_Ratio
        self.TID_avg_by_FID=TID_avg_by_FID
        self.region=region
    
    def treat_dataframe(self)->None:
        """
        Function to fill in any N/A values and reset the index to match other dataframes
        """
        self.TID_avg_by_FID=self.TID_avg_by_FID.fillna(0)
        self.TID_avg_by_FID.reset_index(drop=True,inplace=True)

    def rep(self,rep_days: int) -> list[float]:
        """
        Calculate the technical potential on a representative days.
        
        Parameters
        -------
        rep_days : int
            number of representative days to use in a year, 4 (equinox) or 12 (once per month)

        Returns
        list[float]
            returns a list of the total pv capacity and energy generation
        """
        self.treat_dataframe()

        #Change the slope and aspect for buildings with flat roofs
        unique_segments,rooftop_for_TID=self.calculate_slope(self.region.raster_file,self.region.shapefile)
        Weather_dataframe,solpos=self.get_weather(self.region.weather_file,self.region.latitude,self.region.longitude,self.region.altitude)
        # Weather_dataframe2=Weather_dataframe.copy()
        # Weather_dataframe=Weather_dataframe.iloc[total_range]
        
        #Compare the areas with all FIDs and rasterized FIDs to apply a correction at the end
        rooftop_for_TID.reset_index(drop=True,inplace=True)
        rooftop_for_TID['Area_reduction_factor']=0.971838377688576
        #All segments with slopes less than or equal to 10 degrees have had their PV slope set to 10 degrees (treated as flat roofs with PV arrays oriented at 10 degrees)
        rooftop_for_TID.loc[rooftop_for_TID['SLOPE']==10,'Area_reduction_factor']=0.66767045856285
        self.TID_avg_by_FID=where(self.TID_avg_by_FID<0,0,self.TID_avg_by_FID)
        self.TID_avg_by_FID=DataFrame(self.TID_avg_by_FID)
        #Create a new column in rooftop_for_TID with 'PV_suitable_area_m2'
        rooftop_for_TID['PV_suitable_area_m2']=rooftop_for_TID['Area_reduction_factor']*rooftop_for_TID['AREA']
        #Create a new column with 'PV_capacity_kW' giving the PV capacity
        rooftop_for_TID['PV_capacity_kW']=rooftop_for_TID['PV_suitable_area_m2']*self.PV_module_efficiency
        
        #Compute the total of PV capacity and PV energy over all segments
        Total_PV_capacity_MW= rooftop_for_TID['PV_capacity_kW'].sum()/1000
        
        #Initialize an index for POA_hourly_array
        POA_hourly_array,dni_extra=zeros((len(Weather_dataframe.index),len(unique_segments))),irradiance.get_extra_radiation(Weather_dataframe.index)
        solpos.reset_index(inplace=True)
        Weather_dataframe.reset_index(inplace=True)
        dni_extra.reset_index(inplace=True,drop=True)
        ind2=0

        if rep_days==12:
            total_range = chain(range(480,504),range(1224,1248),range(1896,1920),range(2640,2664),
                                range(3360,3384), range(4104,4128), range(4824,4848),range(5568,5592),
                                range(6312,6336), range(7032,7056),range(7776,7800),range(8496,8520))
            January=self.TID_avg_by_FID.loc[0:23]
            February=self.TID_avg_by_FID.loc[24:47]
            March=self.TID_avg_by_FID.loc[48:71]
            April=self.TID_avg_by_FID.loc[72:95]
            May=self.TID_avg_by_FID.loc[96:119]
            June=self.TID_avg_by_FID.loc[120:143]
            July=self.TID_avg_by_FID.loc[144:167]
            August=self.TID_avg_by_FID.loc[168:191]
            September=self.TID_avg_by_FID.loc[192:215]
            October=self.TID_avg_by_FID.loc[216:239]
            November=self.TID_avg_by_FID.loc[240:263]
            December=self.TID_avg_by_FID.loc[264:287]
            temp_list=[January,February,March,April,May,June,July,August,September,October,November,December]
            weights=[1,28/31,1,30/31,1,30/31,1,1,30/31,1,30/31,1]
            
        else:
            total_range = chain(range(1896,1920), range(4104,4128), range(6312,6336), range(8496,8520))
            March=self.TID_avg_by_FID.loc[0:23]
            June=self.TID_avg_by_FID.loc[24:47]
            September=self.TID_avg_by_FID.loc[48:71]
            December=self.TID_avg_by_FID.loc[72:95]
            temp_list=[December,March,March,March,June,June,June,September,September,September,December,December]

        TID_avg_by_FID2=[]
        index=1
        for month in temp_list:
            if index==1:
                for i in range(1,32):
                    if i==1:
                        TID_avg_by_FID2=month.copy()
                    else:
                        TID_avg_by_FID2=concat([TID_avg_by_FID2,month])
            elif index==3 or index==5 or index==7 or index==8 or index==10 or index==12:
                for i in range(1,32):
                    TID_avg_by_FID2=concat([TID_avg_by_FID2,month])
            elif index==2:
                for i in range(1,29):
                    TID_avg_by_FID2=concat([TID_avg_by_FID2,month])
            elif index==4 or index==6 or index==9 or index==11:
                for i in range(1,31):
                    TID_avg_by_FID2=concat([TID_avg_by_FID2,month])
            index=index+1
        self.TID_avg_by_FID=TID_avg_by_FID2.reset_index(drop=True)

        for ind in rooftop_for_TID.index: 
            total_irradiance = irradiance.get_total_irradiance(
                rooftop_for_TID['SLOPE'][ind], rooftop_for_TID['ASPECT'][ind], 
                solpos['apparent_zenith'],
                solpos['azimuth'],
                Weather_dataframe['DNI'],
                Weather_dataframe['GHI'], 
                Weather_dataframe['DHI'],
                dni_extra=dni_extra,
                model='haydavies')
            POA_hourly_array[:,ind2]=total_irradiance['poa_global'].copy()/1000
            total_irradiance=total_irradiance.reset_index()
            self.TID_avg_by_FID.iloc[:,ind2]=self.TID_avg_by_FID.iloc[:,ind2]*total_irradiance['poa_global']/1000
        
            ind2=ind2+1

        del ind,ind2
        #Next, we will want to assign the contents of POA_hourly_array to the POA_hourly dataframe
        POA_hourly = DataFrame(POA_hourly_array,index = Weather_dataframe.index, columns = arange(1,len(unique_segments)+1,1))

        del POA_hourly_array,POA_hourly
        del Weather_dataframe,dni_extra,solpos,total_irradiance,unique_segments

        self.TID_avg_by_FID=self.TID_avg_by_FID.transpose()
        self.TID_avg_by_FID.reset_index(drop=True, inplace=True)
        rooftop_for_TID.reset_index(inplace=True, drop=True)

        rooftop_for_TID.drop('Area_reduction_factor', axis=1, inplace=True)
        rooftop_for_TID.drop('PV_suitable_area_m2', axis=1, inplace=True)
        rooftop_for_TID.drop('FID',axis=1, inplace=True)
        rooftop_for_TID.drop('SLOPE',axis=1, inplace=True)
        rooftop_for_TID.drop('ASPECT',axis=1, inplace=True)
        rooftop_for_TID.drop('AREA',axis=1, inplace=True)
        rooftop_for_TID.drop('AREA_sum_by_building',axis=1, inplace=True)
        rooftop_for_TID.drop('BUILDING',axis=1, inplace=True)

        #PV_energy_kWh
        self.TID_avg_by_FID=DataFrame(self.TID_avg_by_FID.values*rooftop_for_TID.values*self.Performance_Ratio, columns=self.TID_avg_by_FID.columns, index=self.TID_avg_by_FID.index)

        del rooftop_for_TID
        
        Total_PV_energy_GWh= self.TID_avg_by_FID.sum()
        Total_PV_energy_GWh=Total_PV_energy_GWh.sum()/1e6


        return [Total_PV_capacity_MW,Total_PV_energy_GWh]

    def annual(self) -> list[float]:
        """
        Computes the annual POA and calculates the PV capacity and energy using the 
        input data from TID, the raster and shapefile.

        Returns
        -------
        list
            list of calculated statistics including the PV capacity and energy,
            the fraction of need, number of buildings, etc.

        """
        unique_segments,rooftop_for_TID=self.calculate_slope(self.region.raster_file,self.region.shapefile)
        
        Weather_dataframe,solpos=self.get_weather(self.region.weather_file,self.region.latitude,self.region.longitude,self.region.altitude)
        
        #Calculate extraterrestrial direct normal irradiance 
        dni_extra = irradiance.get_extra_radiation(Weather_dataframe.index)
        
        poa_sum=[]

        #Calculate plane-of-array irradiance for each rooftop segment
        for ind in rooftop_for_TID.index: 
            total_irradiance = irradiance.get_total_irradiance(
                rooftop_for_TID['SLOPE'][ind], rooftop_for_TID['ASPECT'][ind], 
                solpos['apparent_zenith'],
                solpos['azimuth'],
                Weather_dataframe['DNI'],
                Weather_dataframe['GHI'], 
                Weather_dataframe['DHI'],
                dni_extra=dni_extra,
                model='haydavies')
            poa_sum.append(total_irradiance["poa_global"].sum()/1000)  
        
        rooftop_for_TID.loc[:,"POA_SUM"]=array(poa_sum)
           
        #Make FID the index of the rooftop_for_TID dataframe so that the values align properly
        rooftop_for_TID=rooftop_for_TID.reset_index(drop=True)
        self.TID_avg_by_FID=self.TID_avg_by_FID.reset_index(drop=True)
        #Include the annual average shading (TID for TimeInDaylight) as a new column in the rooftop_for_TID dataframe
        rooftop_for_TID['TID']=self.TID_avg_by_FID
        print('Filterd {} points from data that are negative'.format(len(rooftop_for_TID[rooftop_for_TID['TID']<0])) )
        rooftop_for_TID=rooftop_for_TID[rooftop_for_TID['TID']>=0]
        #Multiply the POA by the TID to get annual POA (in kWh/m2) with shading. Later we will want to do a proper calculation with this multiplication performed hourly.
        rooftop_for_TID['POA_with_shading']=rooftop_for_TID['TID']*rooftop_for_TID['POA_SUM']
        Total= rooftop_for_TID.copy()
        area=Total['AREA'].sum()/1000/1000
        #Define area reduction factors to calculate the PV suitable area that will be occupied by PV modules
        
        rooftop_for_TID['Area_reduction_factor']=0.971838377688576
        #All segments with slopes less than or equal to 10 degrees have had their PV slope set to 10 degrees (treated as flat roofs with PV arrays oriented at 10 degrees)
        rooftop_for_TID.loc[rooftop_for_TID['SLOPE']==10,'Area_reduction_factor']=0.66767045856285
        
        #Create a new column in rooftop_for_TID with 'PV_suitable_area_m2'
        rooftop_for_TID['PV_suitable_area_m2']=rooftop_for_TID['Area_reduction_factor']*rooftop_for_TID['AREA']
             
        # #Create a new column with 'PV_capacity_kW' giving the PV capacity
        rooftop_for_TID['PV_capacity_kW']=rooftop_for_TID['PV_suitable_area_m2']*self.PV_module_efficiency
        
        
        #Create a new column with 'PV_energy_kWh' giving the annual energy that would be generated by this PV capacity
        rooftop_for_TID['PV_energy_kWh']=rooftop_for_TID['PV_capacity_kW']*rooftop_for_TID['POA_with_shading']*self.Performance_Ratio
    
        #Compute the total of PV capacity and PV energy over all segments
        Total_PV_capacity_MW= rooftop_for_TID['PV_capacity_kW'].sum()/1000
        
        Total_PV_energy_GWh= rooftop_for_TID['PV_energy_kWh'].sum()/1e6
        
        #Compute the total of PV capacity and PV energy over those segments that receive 80% or more of the maximum value of POA_SUM
        Total_PV_capacity_IEA_MW= rooftop_for_TID.loc[rooftop_for_TID['POA_SUM']>=rooftop_for_TID['POA_SUM'].max()*0.8,'PV_capacity_kW'].sum()/1000
        
        Total_PV_energy_IEA_GWh=rooftop_for_TID.loc[rooftop_for_TID['POA_SUM']>=rooftop_for_TID['POA_SUM'].max()*0.8,'PV_energy_kWh'].sum()/1e6
        print(Total_PV_capacity_MW)
        print(Total_PV_energy_GWh)

        return [Total_PV_capacity_MW,Total_PV_energy_GWh,Total_PV_capacity_IEA_MW,Total_PV_energy_IEA_GWh,
                area]

    def hourly(self)->list[float]:
        
        """
        Computes the hourly POA and calculates the PV capacity and energy using the 
        input data from TID and set files within the function.

         Parameters
        ----------
        None
        
        Returns
        -------
        list
            list of calculated statistics including the PV capacity and energy,
            the fraction of need, number of buildings, etc.

        """
        self.treat_dataframe()
       
        bldg=read_file(self.region.bldg_footprint)
        bldg.reset_index(inplace=True)
        bldg1=DataFrame({'BUILDING':bldg['index'],'building_area':bldg['bldgarea']})

        #Change the slope and aspect for buildings with flat roofs
        unique_segments,rooftop_for_TID=self.calculate_slope(self.region.raster_file,self.region.shapefile)
        Weather_dataframe,solpos=self.get_weather(self.region.weather_file,self.region.latitude,self.region.longitude,self.region.altitude)
        rooftop_for_TID=merge(rooftop_for_TID,bldg1,on='BUILDING')
        del bldg1, bldg
        #Compare the areas with all FIDs and rasterized FIDs to apply a correction at the end
        rooftop_for_TID.reset_index(drop=True,inplace=True)
        rooftop_for_TID['Area_reduction_factor']=0.971838377688576
        #All segments with slopes less than or equal to 10 degrees have had their PV slope set to 10 degrees (treated as flat roofs with PV arrays oriented at 10 degrees)
        rooftop_for_TID.loc[rooftop_for_TID['SLOPE']==10,'Area_reduction_factor']=0.66767045856285
        self.TID_avg_by_FID=where(self.TID_avg_by_FID<0,0,self.TID_avg_by_FID)
        self.TID_avg_by_FID=DataFrame(self.TID_avg_by_FID)
        #Create a new column in rooftop_for_TID with 'PV_suitable_area_m2'
        rooftop_for_TID['PV_suitable_area_m2']=rooftop_for_TID['Area_reduction_factor']*rooftop_for_TID['AREA']
        rooftop_for_TID['PV_suitable_area_no_MS']=rooftop_for_TID['AREA']*0.9/0.891814113607363
        #Create a new column with 'PV_capacity_kW' giving the PV capacity
        rooftop_for_TID['PV_capacity_kW']=rooftop_for_TID['PV_suitable_area_m2']*self.PV_module_efficiency
        
        #Compute the total of PV capacity and PV energy over all segments
        Total_PV_capacity_MW= rooftop_for_TID['PV_capacity_kW'].sum()/1000

        POA_hourly_array,dni_extra=zeros((8760,len(unique_segments))),irradiance.get_extra_radiation(Weather_dataframe.index)
        
        ind2=0

        for ind in rooftop_for_TID.index: 
            total_irradiance = irradiance.get_total_irradiance(
                rooftop_for_TID['SLOPE'][ind], rooftop_for_TID['ASPECT'][ind], 
                solpos['apparent_zenith'],
                solpos['azimuth'],
                Weather_dataframe['DNI'],
                Weather_dataframe['GHI'], 
                Weather_dataframe['DHI'],
                dni_extra=dni_extra,
                model='haydavies')
            POA_hourly_array[:,ind2]=total_irradiance['poa_global']/1000
            total_irradiance=total_irradiance.reset_index()
            self.TID_avg_by_FID.iloc[:,ind2]=self.TID_avg_by_FID.iloc[:,ind2]*total_irradiance['poa_global']/1000

            ind2=ind2+1

        del ind,ind2
        #Next, we will want to assign the contents of POA_hourly_array to the POA_hourly dataframe
        POA_hourly = DataFrame(POA_hourly_array,index = Weather_dataframe.index, columns = arange(1,len(unique_segments)+1,1))

        del POA_hourly_array,Weather_dataframe,dni_extra,solpos,total_irradiance,unique_segments
        POA_hourly=POA_hourly.sum(axis=0)
        
        POA_hourly.name="POA_sum"
        POA_hourly=POA_hourly.reset_index()

        self.TID_avg_by_FID=self.TID_avg_by_FID.transpose()
        self.TID_avg_by_FID.reset_index(drop=True, inplace=True)
        rooftop_for_TID.reset_index(inplace=True, drop=True)
        
        self.rooftop=rooftop_for_TID.copy()
        self.rooftop['TID']=self.TID_avg_by_FID.sum(axis=1)
        self.rooftop['POA_sum']=POA_hourly['POA_sum']

        del POA_hourly
        rooftop_for_TID.drop(['Area_reduction_factor','PV_suitable_area_m2','building_area','FID','SLOPE','ASPECT','AREA','AREA_sum_by_building','BUILDING','PV_suitable_area_no_MS'],axis=1,inplace=True)
        
        self.building_area=self.rooftop.drop_duplicates('BUILDING',keep='first')['building_area'].sum()
        print("Building footprint area (km2): ",round(self.building_area/1000/1000,2))
        #PV_energy_kWh
        self.TID_avg_by_FID=DataFrame(self.TID_avg_by_FID.values*rooftop_for_TID.values*self.Performance_Ratio, columns=self.TID_avg_by_FID.columns, index=self.TID_avg_by_FID.index)

        del rooftop_for_TID

        Total_PV_energy_GWh= self.TID_avg_by_FID.sum()
        Total_PV_energy_GWh=Total_PV_energy_GWh.sum()/1e6
        
        self.TID_avg_by_FID=self.TID_avg_by_FID.sum(axis=1)
        self.TID_avg_by_FID.name="PV_energy_kWh"
        self.rooftop['PV_energy_kWh']=self.TID_avg_by_FID
        del self.TID_avg_by_FID
        self.rooftop['Shading derate (%)']=self.rooftop['TID']/self.rooftop['POA_sum']*100
        weighted_avg_shade=((100-self.rooftop['Shading derate (%)'])*self.rooftop['AREA']/self.rooftop['AREA'].sum()).sum()
        print("Weighted average shading (%): ",round(weighted_avg_shade,2))
        median_shading_loss=self.rooftop['Shading derate (%)'].median()
        print("Median shading derate (%): ", round(median_shading_loss,2))
        
        self.rooftop['Optimal_energy']=self.rooftop['PV_capacity_kW']*self.Performance_Ratio*self.rooftop['POA_sum'].max()
        coeff_capacity,coeff_capacity_shade,coeff_elctricity,coeff_elctricity_shade=self.coefficients(self.rooftop,self.building_area)

        area=self.rooftop['AREA'].sum()/1000/1000
        print('Total area of segments (km2)', round(area,2))
        ratio_tilted=len(self.rooftop[self.rooftop['SLOPE']>10])/len(self.rooftop)
        ratio_flat=len(self.rooftop[self.rooftop['SLOPE']<=10])/len(self.rooftop)
        print('Fraction of rooftops that are tilted:',round(ratio_tilted,2))
        print('Fraction of rooftops that are flat:',round(ratio_flat,2))

        #Total segment area
        Total_segment_area=self.rooftop['AREA'].sum()

        #Compute the total of PV capacity and PV energy over those segments that receive 80% or more of the maximum value of POA_SUM
        Total_PV_capacity_IEA_MW,Total_PV_energy_IEA_GWh,IEA=self.iea_filter(self.rooftop,0.8,self.Performance_Ratio)

        del IEA

        self.rooftop.drop(['FID','SLOPE','ASPECT','AREA','AREA_sum_by_building'],axis=1, inplace=True)
        
        coeff_capacity_shade=DataFrame(coeff_capacity_shade,columns=['Capacity Coefficient - Shaded','Threshold'])
        coeff_elctricity_shade=DataFrame(coeff_elctricity_shade,columns=['Electricity Coefficient - Shaded','Threshold'])

        return [Total_PV_capacity_MW,Total_PV_energy_GWh,Total_PV_capacity_IEA_MW,Total_PV_energy_IEA_GWh,
                area,self.building_area/1000/1000,coeff_capacity_shade,coeff_elctricity_shade]
    
    def calculate_slope(self,filename: str,shapefile: str)-> tuple[DataFrame,DataFrame]:
        """
        Function to calculate and create a new dataframe that has all the parameters
        needed for the rest of the analysis (average slope/building, etc.)

        Parameters
        ----------
        filename : string
            raster file with the file extension .tif. This is the rasterized 
            vector file created in QGIS.
        shapefile : string
            shapefile created from the segmentation function.

        Returns
        -------
        unique_segments : Dataframe
            A dataframe of unique segements within the files, used to filter out
            outliers.
        rooftop_for_TID : Dataframe
            Output dataframe containing all information needed for the rest of the 
            analysis.

        """
        rooftop=read_file(shapefile)
        
        #Calculate average slope for each building
        rooftop['SLOPE*AREA']=rooftop['SLOPE']*rooftop['AREA']
        rooftop['SLOPE*AREA_sum_by_BUILDING']=rooftop.groupby('BUILDING')['SLOPE*AREA'].transform('sum')
        rooftop['AREA_sum_by_building']=rooftop.groupby('BUILDING')['AREA'].transform('sum')
        rooftop['AVG_SLOPE_BY_BUILDING']=rooftop['SLOPE*AREA_sum_by_BUILDING']/rooftop['AREA_sum_by_building']
        
        #Dropping un-needed columns
        rooftop.drop('SLOPE*AREA', axis=1, inplace=True)
        rooftop.drop('MAX_ELEV', axis=1, inplace=True)
        rooftop.drop('SLOPE*AREA_sum_by_BUILDING', axis=1, inplace=True)
        rooftop.drop('geometry', axis=1, inplace=True)
        rooftop.drop('HILLSHADE', axis=1, inplace=True)
        
        #Set slope to 10 degrees when AVG_SLOPE_BY_BUILDING is <=10
        rooftop.loc[rooftop['AVG_SLOPE_BY_BUILDING']<=10,'SLOPE']=10
        
        #Set aspect to South-facing for now. Eventually, try to find the alignment of the building and pick an aspect based on this.
        rooftop.loc[rooftop['AVG_SLOPE_BY_BUILDING']<=10,'ASPECT']=180
        
        rooftop.drop('AVG_SLOPE_BY_BUILDING', axis=1, inplace=True)
        
        #Importing rasterized segments and selecting only those FIDs
        Rasterized_segments_data = open_file(filename).read(1)
        
        #Get 2D numpy arrays 
        Rasterized_segments_ravel=Rasterized_segments_data.ravel() 
        
        #Turn arrays into 1D vectors 
        del Rasterized_segments_data

        #Find out which FIDs are in the rasterization of the shapefile
        unique_segments = unique(Rasterized_segments_ravel)
        unique_segments=unique_segments[unique_segments!=-999]
        del Rasterized_segments_ravel
        #Select only those FIDs
        rooftop_for_TID=rooftop[rooftop['FID'].isin(unique_segments)]
     
        return unique_segments,rooftop_for_TID

    def get_weather(self,weather_file: str,latitude: float,longitude: float,altitude: float,time_of_year=None,time_horizon=None,timestep=None) -> tuple[DataFrame,DataFrame]:
        """
        Function to read and output the weather data

        Parameters
        ----------
        weather_file : string
            location of the weather file
        latitude: float
            latitude of the location
        longitude: float 
            longitude of the location
        altitude: float
            altitude of the location
        
        Returns
        -------
        Weather_dataframe : Dataframe
            Dataframe of all the weather from the input weather file for an entire
            year.
        solpos : Dataframe
            Dataframe of calculated weather conditions based on the input weather data.

        """
        #Read in weather data
        if latitude>=60: #if the city an epw file from CWEC
            Weather_dataframe=iotools.read_epw(weather_file)[0]
            Weather_dataframe.rename(columns={'ghi':'GHI'},inplace=True)
            Weather_dataframe.rename(columns={'dni':'DNI'},inplace=True)
            Weather_dataframe.rename(columns={'dhi':'DHI'},inplace=True)
            Weather_dataframe.rename(columns={'temp_air':'Temperature'},inplace=True)
        else:
            Weather_dataframe=iotools.read_psm3(weather_file)[1] # https://pvlib-python.readthedocs.io/en/stable/generated/pvlib.iotools.read_psm3.html
        if timestep==60:
                Weather_dataframe=Weather_dataframe[Weather_dataframe.index.minute==0]
        
        if time_horizon=='inst':
            index=Weather_dataframe.reset_index()
            Weather_dataframe=index.loc[(index['index']>=index.iloc[int(time_of_year/timestep)]['index'])]
            del index
            Weather_dataframe.set_index('index',inplace=True)
        elif type(time_horizon)==type(15):
            index=Weather_dataframe.reset_index()
            Weather_dataframe=index.loc[(index['index']<=index.iloc[int((time_of_year+time_horizon)/timestep)]['index']) & (index['index']>=index.iloc[int(time_of_year/timestep)]['index'])]
            del index
            Weather_dataframe.set_index('index',inplace=True)
        
        #Calculate the solar position
        solpos = solarposition.get_solarposition(
                time=Weather_dataframe.index, 
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                temperature=Weather_dataframe["Temperature"],
                pressure=atmosphere.alt2pres(altitude))
        return Weather_dataframe,solpos

    
    def iea_filter(self,rooftop_for_TID: DataFrame,percent_filter:float,performance_ratio:float)-> tuple[float,float,DataFrame]:
        """
        Filters the rooftop segements based on the IEA PVPS Task 7 method by threshold of solar insolation on a rooftop segment.
        
        Parameters
        ----------
        rooftop_for_TID_filter : DataFrame
            dataframe with all the information by segement
        percent_filter : float
            the percent threshold of total annual irradiance to filter the results
        performance_ratio:float
            performance ratio of the PV system
        
        Returns
        -------
        tuple[float,float,DataFrame]
            outputs a tuple containing the capacity and energy generation after 
            filtering and the inputted dataframe after filtering
        """
        rooftop=rooftop_for_TID.copy()
        rooftop['Area_reduction_factor']=performance_ratio*0.9/0.891814114*0.96299909
        rooftop.loc[rooftop['SLOPE']==10,'Area_reduction_factor']=performance_ratio*0.9/0.891814114*0.661597709

        rooftop['PV_capacity_kW']=self.PV_module_efficiency*rooftop['AREA']*rooftop['Area_reduction_factor']
        rooftop=rooftop.sort_values(by='Shading derate (%)')
        rooftop['cummulative_sum']=rooftop['AREA'].cumsum(axis=0)

        rooftop=rooftop[rooftop['cummulative_sum']>=rooftop['AREA'].sum()*0.15]

        rooftop['PV_energy_kWh']=rooftop['PV_capacity_kW']*rooftop_for_TID['TID']*self.Performance_Ratio
        Total_PV_capacity_IEA_MW= rooftop.loc[rooftop['POA_sum']>=rooftop['POA_sum'].max()*percent_filter,'PV_capacity_kW'].sum()/1000
        
        Total_PV_energy_IEA_GWh=rooftop.loc[rooftop['POA_sum']>=rooftop['POA_sum'].max()*percent_filter,'PV_energy_kWh'].sum()/1e6

        rooftop=rooftop.loc[rooftop['POA_sum']>=rooftop['POA_sum'].max()*percent_filter]
        rooftop.drop('SLOPE',axis=1, inplace=True)
        rooftop.drop('ASPECT',axis=1, inplace=True)
        rooftop.drop('cummulative_sum',axis=1, inplace=True)
        rooftop.drop('FID',axis=1, inplace=True)

        return Total_PV_capacity_IEA_MW,Total_PV_energy_IEA_GWh,rooftop

    def coefficients(self,rooftop_for_TID: DataFrame,building_area: float)-> list[list,list,list,list]:
        """
        Calculates the coefficiencts by threshold with and without shading.

        Parameters
        ----------
        rooftop_for_TID_filter : DataFrame
            dataframe with all the information by segement
        building_area : float
            total building footprint area
        
        Returns
        -------
        list[list,list,list,list]
            outputs a list of 4 lists consistign of unshaded capacity coefficients,
            shaded capacity coefficients, unshaded energy coefficients, and
            shaded energy coefficients
        """
        coeff_capacity=[]
        coeff_elctricity=[]
        coeff_capacity_shade=[]
        coeff_elctricity_shade=[]
        threshold=[0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]
        for percent_filter in threshold:
            electricity=rooftop_for_TID.loc[rooftop_for_TID['POA_sum']>=rooftop_for_TID['POA_sum'].max()*percent_filter,'PV_energy_kWh'].sum()/1e6
            optimal_energy=rooftop_for_TID.loc[rooftop_for_TID['POA_sum']>=rooftop_for_TID['POA_sum'].max()*percent_filter,'Optimal_energy'].sum()/1e6

            temp=rooftop_for_TID.loc[rooftop_for_TID['POA_sum']>=rooftop_for_TID['POA_sum'].max()*percent_filter,'PV_suitable_area_m2'].sum()
            coeff_capacity.append([temp/building_area,percent_filter])
            coeff_elctricity.append([electricity/(optimal_energy),percent_filter])

            temp=rooftop_for_TID.loc[rooftop_for_TID['TID']>=rooftop_for_TID['POA_sum'].max()*percent_filter,'PV_suitable_area_m2'].sum()
            
            electricity_shade=rooftop_for_TID.loc[rooftop_for_TID['TID']>=rooftop_for_TID['POA_sum'].max()*percent_filter,'PV_energy_kWh'].sum()/1e6
            optimal_energy=rooftop_for_TID.loc[rooftop_for_TID['TID']>=rooftop_for_TID['POA_sum'].max()*percent_filter,'Optimal_energy'].sum()/1e6

            coeff_capacity_shade.append([temp/building_area,percent_filter])
            coeff_elctricity_shade.append([electricity_shade/(optimal_energy),percent_filter])

        return coeff_capacity,coeff_capacity_shade,coeff_elctricity,coeff_elctricity_shade
    
class calculate_economic_potential(calculate_technical_potential):
    """
    Functions to set up and run the economic analysis
    """
    def __init__(self,class_technical: calculate_technical_potential)->None:
        self.region=class_technical.region
        self.rooftop=class_technical.rooftop
        self.years=30
        self.PV_cost_years=[1,1.033729269,0.997033793,0.960338317,0.923642841,
                    0.886947365,0.850251889,0.813556413,0.776860936,0.74016546,
                    0.703469984,0.666774508,0.630079032,0.593383556,0.55668808,
                    0.545992166,0.535296253,0.52460034,0.513904427,0.503208514,
                    0.4925126,0.481816687,0.471120774,0.460424861,0.449728948,
                    0.439033035,0.428337121,0.417641208,0.406945295,0.396249382]
        self.economic_potential=economic_analysis.economic(self.years,self.region.elec_cost,PV_cost_years=self.PV_cost_years)
  
    def calculate_payback_bin(self,Total_PV_capacity_MW: float) -> None:
        """
        Calculates the payback using the bin method instead of by segment.

        Parameters
        ----------
        Total_PV_capacity_MW : float
            total technical potential capacity
        
        """
        max_solar_yield= (self.rooftop['PV_energy_kWh']/self.rooftop['PV_capacity_kW']).max()
        bin=[round(i/10.0,2) for i in range(0,11)]
        self.potential_by_threshold=self.bins(Total_PV_capacity_MW,bin,max_solar_yield,self.region.cap_cofficient_shade)
        self.payback_bin=self.economic_potential.payback_bin(self.potential_by_threshold,self.years)
    
    def bins(self,Total_PV_capacity: float,bin: list[float],daily_insolation: float,coefficients: list[float],PV_PR:float)-> DataFrame:
        """
        Divide the rooftops into different bins based on the coefficients calculated in POA.py and the solar resource.
        
        Parameters
        ----------
        Total_PV_capacity : float
            total technical potential capacity
        bin : list[float]
            list of bin divisions. ex [0.1,0.2,...,1.0]
        daily_insolation : float
            total daily insolation based on the location
        coefficients : list[float]
            list of coefficients from the technical potetnial analysis
        PV_PR : float
            the performance ratio used
        
        Returns
        -------
        DataFrame
            DataFrame dividing the capacity and solar yield by bin 
        """

        coefficients=coefficients.copy()
        coefficients.append(0)
        
        Technical_potential_above_threshold=[]
        for i in range(0,len(bin)):
            if i==0:
                Technical_potential_above_threshold.append(Total_PV_capacity)
            elif i>=len(coefficients):
                Technical_potential_above_threshold.append(0)
            else:
                Technical_potential_above_threshold.append(coefficients[i]/coefficients[0]*Total_PV_capacity)
        ind=0
        Technical_potential=[]
        solar_yield=[]
        mid_bin=[0.0700731, 0.1659991, 0.2615420, 0.3579429, 0.4588964, 0.5557738, 0.6507723, 0.7518895, 0.8474252, 0.9233740,1.0]

        for i in bin:
            if ind>=len(bin)-1:
                Technical_potential.append(0)
            elif ind==len(bin)-2:
                Technical_potential.append(Technical_potential_above_threshold[ind])
            else:
                Technical_potential.append(Technical_potential_above_threshold[ind]-Technical_potential_above_threshold[ind+1])
            
            solar_yield.append(daily_insolation*mid_bin[ind]*365*PV_PR)
            ind=ind+1
        data={'PV_capacity_GW': Technical_potential,'PV_kWh_kW': solar_yield}
        technical_potential=DataFrame(data)
        return technical_potential

    def print_economic_payback(self) -> None:
        """
        Function to print the results to the console.
        """
        print('Economic potential based on payback (30 years) - MW ', round(self.rooftop.loc[self.rooftop['payback']<=30]['PV_capacity_kW'].sum()/1000,2))
        print('Economic elec. gen. based on payback (30 years) - GWh', round(self.rooftop.loc[self.rooftop['payback']<=30]['PV_energy_kWh'].sum()/1000/1000,2))
        print('Economic potential based on payback (25 years) - MW', round(self.rooftop.loc[self.rooftop['payback']<=25]['PV_capacity_kW'].sum()/1000,2))
        print('Economic elec. gen. based on payback (25 years) - GWh', round(self.rooftop.loc[self.rooftop['payback']<=25]['PV_energy_kWh'].sum()/1000/1000,2))
        print('Economic potential based on payback (20 years) - MW', round(self.rooftop.loc[self.rooftop['payback']<=20]['PV_capacity_kW'].sum()/1000,2))
        print('Economic elec. gen. based on payback (20 years) - GWh', round(self.rooftop.loc[self.rooftop['payback']<=20]['PV_energy_kWh'].sum()/1000/1000,2))
        print('Economic potential based on payback (15 years) - MW', round(self.rooftop.loc[self.rooftop['payback']<=15]['PV_capacity_kW'].sum()/1000,2))
        print('Economic elec. gen. based on payback (15 years) - GWh', round(self.rooftop.loc[self.rooftop['payback']<=15]['PV_energy_kWh'].sum()/1000/1000,2))
        print('Economic potential based on payback (10 years) - MW', round(self.rooftop.loc[self.rooftop['payback']<=10]['PV_capacity_kW'].sum()/1000,2))
        print('Economic elec. gen. based on payback (10 years) - GWh', round(self.rooftop.loc[self.rooftop['payback']<=10]['PV_energy_kWh'].sum()/1000/1000,2))

class calculate_market_potential(calculate_economic_potential):
    """
    Functions to set up the market potential calculation.
    """
    def __init__(self,class_technical: calculate_technical_potential)->None:
        super().__init__(class_technical)

    def calculate_market(self,file_location:str) -> None:
        """
        Set up and calculate the forecasted installed capapcity for each rooftop

        Parameters
        ----------
        file_location : str
            location of the files to read or write
        """
        self.calculate_payback(file_location)
        self.print_economic_payback()
        self.market_potential=market_analysis.market_analysis(capacity=self.rooftop['PV_capacity_kW'],payback=self.payback)
        out=self.market_potential.Y_t()
        print('Installed capacity at 30 years - MW', round(out.iloc[:,29].sum()/1000,2))
    
    def calculate_market_bin(self,PV_capacity_MW: float) -> None:
        """
        Set up and calculate the forecasted installed capapcity by using the bin method instead of by rooftop segment
        
        Parameters
        ----------
        PV_capacity_MW : float
            total technical potential capacity
        """
        self.calculate_payback_bin(PV_capacity_MW)
        market_potential=market_analysis.market_analysis(capacity=self.potential_by_threshold['PV_capacity_kW'],payback=self.payback_bin)
        out=market_potential.installed_capacity()        
        print('Installed capacity at 30 years (Threshhold) ', round(out.iloc[:,29].sum(),2))
        