# -*- coding: utf-8 -*-
"""
Created on Fri Apr 30 15:58:31 2021

@authors: nsalimza and egaucher
"""
from pvlib import iotools,irradiance,solarposition,atmosphere
from pandas import DataFrame,merge,concat, read_csv,to_datetime,DateOffset, Series
from  geopandas import read_file
from numpy import unique,zeros,arange,array,where
import numpy as np
from rasterio import open as open_file
from itertools import chain
import re


class calculate_technical_potential_hourly:
    def __init__(self,TID_avg_by_FID: DataFrame,region: DataFrame,PR:float,PV_module_efficiency:float,mode)->None:
        self.PV_module_efficiency=PV_module_efficiency
        self.Performance_Ratio= PR
        self.TID=TID_avg_by_FID
        self.region=region
        self.treat_dataframe()

        #Change the slope and aspect for buildings with flat roofs
        self.unique_segments,self.rooftop_save=self.calculate_slope(region.raster_file,region.shapefile)
        
        #Compare the areas with all FIDs and rasterized FIDs to apply a correction at the end
        self.rooftop_save.reset_index(drop=True,inplace=True)
        self.rooftop_save['Area_reduction_factor']=0.971838377688576

        #All segments with slopes less than or equal to 10 degrees have had their PV slope set to 10 degrees (treated as flat roofs with PV arrays oriented at 10 degrees)
        self.rooftop_save.loc[self.rooftop_save['SLOPE']==10,'Area_reduction_factor']=0.66767045856285
        self.TID=where(self.TID<0,0,self.TID)
        self.TID=DataFrame(self.TID)
        #Create a new column in rooftop_for_TID with 'PV_suitable_area_m2'
        self.rooftop_save['PV_suitable_area_m2']=self.rooftop_save['Area_reduction_factor']*self.rooftop_save['AREA']

        self.Weather,solarposition=self.get_weather(region.weather_file,region.latitude,region.longitude,region.altitude,region.timezone,mode)
        #Initialize an index for POA_hourly_array
        POA_hourly_array,dni_extra=zeros((8760,len(self.unique_segments))),irradiance.get_extra_radiation(self.Weather.index)
        
        ind2=0
        for ind in self.rooftop_save.index: 
            total_irradiance = irradiance.get_total_irradiance(
                surface_tilt=self.rooftop_save['SLOPE'][ind], surface_azimuth=self.rooftop_save['ASPECT'][ind], 
                solar_zenith=solarposition['apparent_zenith'],
                solar_azimuth=solarposition['azimuth'],
                dni=self.Weather['DNI'],
                ghi=self.Weather['GHI'], 
                dhi=self.Weather['DHI'],
                dni_extra=dni_extra,
                model='haydavies')
            POA_hourly_array[:,ind2]=total_irradiance['poa_global']/1000
            total_irradiance=total_irradiance.reset_index()
            self.TID.iloc[:,ind2]=self.TID.iloc[:,ind2]*total_irradiance['poa_global']/1000

            ind2=ind2+1

        del ind,ind2
        #Next, we will want to assign the contents of POA_hourly_array to the POA_hourly dataframe
        self.POA_hourly = DataFrame(POA_hourly_array,index = self.Weather.index, columns = arange(1,len(self.unique_segments)+1,1))

        del POA_hourly_array,dni_extra,total_irradiance,solarposition
        self.POA_hourly=self.POA_hourly.reset_index(drop=True)
        self.POA_hourly_energy=self.TID.copy()
        self.POA_hourly=self.POA_hourly.sum(axis=0)
        
        self.POA_hourly.name="POA_sum"

        self.TID=self.TID.transpose()
        self.TID.reset_index(drop=True, inplace=True)
        self.POA_hourly_energy=self.POA_hourly_energy.transpose()
        self.rooftop_save.reset_index(inplace=True, drop=True)
        self.rooftop_save.drop(['Area_reduction_factor','FID','AREA_sum_by_building'],axis=1,inplace=True)
        
    def set_performance_ratio(self,PR:float)->None:
        """
        Sets the performance ratio in the event that the performance ratio changes between runs
        
        Parameters
        -------
        PR: float
            PV performance ratio
        """
        self.Performance_Ratio=PR

    def set_efficiency(self,PV_module_efficiency:float)->None:
        """
        Sets the PV module efficiency in the event that the PV module efficiency changes between runs
        
        Parameters
        -------
        PV_module_efficiency: float
            PV module efficiency
        """
        self.PV_module_efficiency=PV_module_efficiency

    def treat_dataframe(self)->None:
        """
        Function to fill in any N/A values and reset the index to match other dataframes
        """
        self.TID=self.TID.fillna(0)
        self.TID.reset_index(drop=True,inplace=True)

    def hourly_grid(self)->list[float]:
        
        """
        Computes the hourly POA and calculates the PV capacity and energy using the 
        input data from TID and set files within the function.

        Returns
        -------
        list
            list of calculated statistics including the PV capacity and energy,
            the fraction of need, number of buildings, etc.

        """
        #Create a new column with 'PV_capacity_kW' giving the PV capacity
        
        self.rooftop_save['PV_capacity_kW']=self.rooftop_save['PV_suitable_area_m2']*self.PV_module_efficiency

        #PV_energy_kWh
        TID_avg_by_FID=DataFrame(self.TID.values*self.rooftop_save['PV_capacity_kW'].to_frame().values*self.Performance_Ratio, columns=self.TID.columns, index=self.TID.index)

        self.rooftop_save['PV_energy_kWh']=TID_avg_by_FID.sum(axis=1)
        del TID_avg_by_FID
        self.rooftop_save['TID']=self.TID.sum(axis=1)
        self.rooftop_save['POA_sum']=self.POA_hourly
        
        hourly_poa_bin_weighted,PV_capacity_GW,PV_energy_MWh=self.potential_bin(self.rooftop_save,self.POA_hourly_energy)
        self.rooftop_save.drop(['TID','PV_energy_kWh','POA_sum'],axis=1,inplace=True)

        hourly_poa_bin_weighted=DataFrame(hourly_poa_bin_weighted).reset_index(drop=True)
        PV_capacity_GW.append(0.0)
        PV_energy_MWh.append(0.0)

        return hourly_poa_bin_weighted, self.Weather["Temperature"],Series(PV_capacity_GW),Series(PV_energy_MWh)
    
    def hourly_region(self,)->list[float]:
        """
        Computes the hourly POA and calculates the PV capacity and energy using the 
        input data from TID, the raster and shapefile.

        Parameters
        -------
        file_location: str
            location of all the files

        Returns
        -------
        list
            list of calculated statistics including the PV capacity and energy,
            the fraction of need, number of buildings, etc.

        """
        rooftop_for_TID=self.rooftop_save.copy()
        rooftop_for_TID=self.get_building_footprint(rooftop_for_TID)
        rooftop_for_TID['PV_capacity_kW']=rooftop_for_TID['PV_suitable_area_m2']*self.PV_module_efficiency
        Total_PV_capacity_MW= rooftop_for_TID['PV_capacity_kW'].sum()/1000

        rooftop=rooftop_for_TID.copy()
        self.building_area=rooftop_for_TID.drop_duplicates('BUILDING',keep='first')['building_area'].sum()

        rooftop_for_TID.drop(['PV_suitable_area_m2','building_area','BUILDING','AREA','SLOPE','ASPECT'],axis=1,inplace=True)
        
        print("Building footprint area (analysis region) in km2: ",round(self.building_area/1000/1000,2))
        #PV_energy_kWh
        TID_avg_by_FID=DataFrame(self.TID.values*rooftop_for_TID.values*self.Performance_Ratio, columns=self.TID.columns, index=self.TID.index)

        Total_PV_energy_GWh= TID_avg_by_FID.sum()
        Total_PV_energy_GWh=Total_PV_energy_GWh.sum()/1e6
        
        TID_avg_by_FID=TID_avg_by_FID.sum(axis=1)
        TID_avg_by_FID.name="PV_energy_kWh"
        rooftop['PV_energy_kWh']=TID_avg_by_FID.copy()
        rooftop['TID']=self.TID.sum(axis=1)
        rooftop['POA_sum']=self.POA_hourly
        del TID_avg_by_FID
        rooftop['Shading derate (%)']=rooftop['TID']/rooftop['POA_sum']*100
        weighted_avg_shade=((100-rooftop['Shading derate (%)'])*rooftop['AREA']/rooftop['AREA'].sum()).sum()
        print("Weighted average shading: ",round(weighted_avg_shade,2))
        median_shading_loss=rooftop['Shading derate (%)'].median()
        print("Median shading derate: ", round(median_shading_loss,2))
        rooftop['Optimal_energy']=rooftop['PV_capacity_kW']*self.Performance_Ratio*rooftop['POA_sum'].max()
        coeff_capacity_shade,coeff_elctricity_shade=self.coefficients(rooftop,self.building_area)

        area=rooftop['AREA'].sum()/1000/1000
        print('Total rooftop area', round(area,2))
        ratio_tilted=len(rooftop[rooftop['SLOPE']>10])/len(rooftop)
        ratio_flat=len(rooftop[rooftop['SLOPE']<=10])/len(rooftop)
        print('Fraction of rooftops that are tilted:',round(ratio_tilted,2))
        print('Fraction of rooftops that are flat:',round(ratio_flat,2))

        rooftop.drop(['SLOPE','ASPECT','AREA'],axis=1, inplace=True)

        coeff_capacity_shade=DataFrame(coeff_capacity_shade,columns=['Capacity Coefficient - Shaded','Threshold'])
        coeff_elctricity_shade=DataFrame(coeff_elctricity_shade,columns=['Electricity Coefficient - Shaded','Threshold'])

        return [Total_PV_capacity_MW,Total_PV_energy_GWh,rooftop['BUILDING'].nunique(),
                area,self.building_area/1000/1000,coeff_capacity_shade,coeff_elctricity_shade]

    def get_building_footprint(self,rooftop:DataFrame)->DataFrame:
        """
        Function to get the building footprint area per building and merge it into the input dataframe.

        Parameters
        ----------
        rooftop : DataFrame
            raster file with the file extension .tif. This is the rasterized 
            vector file created in QGIS.

        Returns
        -------
        rooftop : Dataframe
            A input dataframe with the building footprint area

        """
        bldg=read_file(self.region.bldg_footprint)
        bldg.reset_index(inplace=True)
        if "bldgarea" not in bldg.columns:
            # look for a column that contains "area" (case-insensitive)
            matches = [col for col in bldg.columns if re.search("area", col, re.IGNORECASE)]
            if matches:
                # rename the first match
                bldg.rename(columns={matches[0]: "bldgarea"}, inplace=True)
        bldg1=DataFrame({'BUILDING':bldg['index'],'building_area':bldg['bldgarea']})
        rooftop=merge(rooftop,bldg1,on='BUILDING')
        return rooftop

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
        # Rasterized_segments_ravel=Rasterized_segments_array.ravel() 
        del Rasterized_segments_data
        # del Rasterized_segments_array
        #Find out which FIDs are in the rasterization of the shapefile
        unique_segments = unique(Rasterized_segments_ravel)
        unique_segments=unique_segments[unique_segments!=-999]
        del Rasterized_segments_ravel
        #Select only those FIDs
        rooftop_for_TID=rooftop[rooftop['FID'].isin(unique_segments)]
        
        Area_correction_factor=rooftop['AREA'].sum()/rooftop_for_TID['AREA'].sum()
        # print('Correction factor:',Area_correction_factor)
        
        return unique_segments,rooftop_for_TID

    def get_weather(self,weather_file: str,latitude: float,longitude: float,altitude: float,timezone:str,mode:str) -> tuple[DataFrame,DataFrame]:
        """
        Function to read and output the weather data

        Parameters
        ----------
        weather_file : str
            location of the weather file
        latitude : float
            latitude of the region
        longitude : float
            longitude of the region
        altitude : float
            altitude of the region


        Returns
        -------
        Weather_dataframe : Dataframe
            Dataframe of all the weather from the input weather file for an entire
            year.
        solpos : Dataframe
            Dataframe of calculated weather conditions based on the input weather data.

        """
        #Read in weather data
        if latitude>=60 and (mode=="Market" or mode=='grid'): 
            Weather_dataframe=read_csv(weather_file,skiprows=16)
            Weather_dataframe.rename(columns={'ALLSKY_SFC_SW_DWN':'GHI'},inplace=True)
            Weather_dataframe.rename(columns={'ALLSKY_SFC_SW_DNI':'DNI'},inplace=True)
            Weather_dataframe.rename(columns={'ALLSKY_SFC_SW_DIFF':'DHI'},inplace=True)
            Weather_dataframe.rename(columns={'T2M':'Temperature'},inplace=True)
            Weather_dataframe['Timestamp']=to_datetime(Weather_dataframe[['YEAR','MO','DY','HR']].astype(str).agg('-'.join,axis=1),format='%Y-%m-%d-%H')
            Weather_dataframe["Timestamp"] = Weather_dataframe["Timestamp"].dt.tz_localize(timezone)
            Weather_dataframe["Timestamp"] += DateOffset(minutes=30)
            # Set as index 
            Weather_dataframe = Weather_dataframe.set_index('Timestamp')
        
        elif latitude>=60 and mode=="Technical": 
            Weather_dataframe=iotools.read_epw(weather_file)[0]
            Weather_dataframe.rename(columns={'ghi':'GHI'},inplace=True)
            Weather_dataframe.rename(columns={'dni':'DNI'},inplace=True)
            Weather_dataframe.rename(columns={'dhi':'DHI'},inplace=True)
            Weather_dataframe.rename(columns={'temp_air':'Temperature'},inplace=True)
        else:
            Weather_dataframe=iotools.read_psm3(weather_file)[0] 
            Weather_dataframe.rename(columns={'ghi':'GHI'},inplace=True)
            Weather_dataframe.rename(columns={'dni':'DNI'},inplace=True)
            Weather_dataframe.rename(columns={'dhi':'DHI'},inplace=True)
            Weather_dataframe.rename(columns={'temp_air':'Temperature'},inplace=True)
        
        #Calculate the solar position
        solpos = solarposition.get_solarposition(
                time=Weather_dataframe.index, 
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                temperature=Weather_dataframe["Temperature"],
                pressure=atmosphere.alt2pres(altitude))
        
        return Weather_dataframe,solpos

    def potential_bin(self,rooftop_for_TID: DataFrame,hourly_POA:DataFrame)-> list[list[float]]:
        """
        Calculates weighted POA, weighted by the capacity to POA on each segment and summed.

        Parameters
        ----------
        rooftop_for_TID : DataFrame
            DataFrame of all the results for each segment
        hourly_POA : DataFrame
            DataFrame of the hourly shaded POA by segment

        Returns
        -------
        capacity_bin : list[float]
            list of the capacity by solar resource bin
        elctricity_bin : list[float]
            list of the electricity generation by solar resource bin
        poa_sum : list[list[float]]
            output list with the hourly shaded POA split into bins
        """
        

        weighted_poa_sum=[]
        threshold=[0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]
        electricity=[]
        capacity=[]
        for percent_filter in threshold:

            poa_temp=hourly_POA.loc[(hourly_POA.sum(axis=1)>=hourly_POA.sum(axis=1).max()*percent_filter)&(hourly_POA.sum(axis=1)<hourly_POA.sum(axis=1).max()*(percent_filter+0.1))]
            capacity_temp=rooftop_for_TID.loc[(rooftop_for_TID['TID']>=rooftop_for_TID['POA_sum'].max()*percent_filter)&(rooftop_for_TID['TID']<rooftop_for_TID['POA_sum'].max()*(percent_filter+0.1)),'PV_capacity_kW'].sum()/1000/1000
            electricity_temp=rooftop_for_TID.loc[(rooftop_for_TID['TID']>=rooftop_for_TID['POA_sum'].max()*percent_filter)&(rooftop_for_TID['TID']<rooftop_for_TID['POA_sum'].max()*(percent_filter+0.1)),'PV_energy_kWh'].sum()/1000
            poa_temp=hourly_POA.align(poa_temp,join='inner')[0]
            cap_temp=rooftop_for_TID['PV_capacity_kW'].align(poa_temp,join='inner')[0]
            weighted_poa=(poa_temp.mul(cap_temp,axis=0)).sum().div(cap_temp.sum())
            weighted_poa.replace(np.nan,0,inplace=True)
            capacity.append(capacity_temp)
            electricity.append(electricity_temp)
            weighted_poa_sum.append(weighted_poa)

        return weighted_poa_sum,capacity,electricity
    
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
        coeff_capacity_shade=[]
        coeff_elctricity_shade=[]
        threshold=[0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]
        for percent_filter in threshold:
            optimal_energy=rooftop_for_TID.loc[rooftop_for_TID['POA_sum']>=rooftop_for_TID['POA_sum'].max()*percent_filter,'Optimal_energy'].sum()/1e6
            temp=rooftop_for_TID.loc[rooftop_for_TID['TID']>=rooftop_for_TID['POA_sum'].max()*percent_filter,'PV_suitable_area_m2'].sum()

            electricity_shade=rooftop_for_TID.loc[rooftop_for_TID['TID']>=rooftop_for_TID['POA_sum'].max()*percent_filter,'PV_energy_kWh'].sum()/1e6
            optimal_energy=rooftop_for_TID.loc[rooftop_for_TID['TID']>=rooftop_for_TID['POA_sum'].max()*percent_filter,'Optimal_energy'].sum()/1e6

            coeff_capacity_shade.append([temp/building_area,percent_filter])
            coeff_elctricity_shade.append([electricity_shade/(optimal_energy),percent_filter])

        return coeff_capacity_shade,coeff_elctricity_shade
    
    def gagnon_filter(self,rooftop_for_TID_filter: DataFrame)-> tuple[float,float,DataFrame]:
        """
        Filter the rooftops and calculate the technical potential based on the method from Gagnon et al. 2016 method

        Parameters
        ----------
        rooftop_for_TID_filter : DataFrame
            dataframe with all the information by segement
        
        Returns
        -------
        tuple[float,float,DataFrame]
            outputs a tuple containing the capacity and energy generation after 
            filtering and the inputted dataframe after filtering
        """
        rooftop_for_TID_filter['Area_reduction_factor']=0.98/0.891814114
        rooftop_for_TID_filter.loc[rooftop_for_TID_filter['SLOPE']==10,'Area_reduction_factor']=0.7/0.891814114

        east=rooftop_for_TID_filter.loc[rooftop_for_TID_filter['TID']/rooftop_for_TID_filter['POA_sum']>=0.8]
        south_east=rooftop_for_TID_filter.loc[rooftop_for_TID_filter['TID']/rooftop_for_TID_filter['POA_sum']>=0.8]
        south=rooftop_for_TID_filter.loc[rooftop_for_TID_filter['TID']/rooftop_for_TID_filter['POA_sum']>=0.8]
        south_west=rooftop_for_TID_filter.loc[rooftop_for_TID_filter['TID']/rooftop_for_TID_filter['POA_sum']>=0.8]
        west=rooftop_for_TID_filter.loc[rooftop_for_TID_filter['TID']/rooftop_for_TID_filter['POA_sum']>=0.8]
        
        east=east[east['ASPECT']>67.5]
        east=east[east['ASPECT']<112.5]
        south_east=south_east[south_east['ASPECT']>112.5] 
        south_east=south_east[south_east['ASPECT']<157.5]
        
        south=south[south['ASPECT']>157.5]
        south=south[south['ASPECT']<202.5]
        south_west=south_west[south_west['ASPECT']>202.5]
        south_west=south_west[south_west['ASPECT']<247.5]
        west=west[west['ASPECT']>247.5]
        west=west[west['ASPECT']<292.5]

        east['AREA_sum_by_building']=east.groupby('BUILDING')['AREA'].transform('sum')
        south_east['AREA_sum_by_building']=south_east.groupby('BUILDING')['AREA'].transform('sum')
        south['AREA_sum_by_building']=south.groupby('BUILDING')['AREA'].transform('sum')
        south_west['AREA_sum_by_building']=south_west.groupby('BUILDING')['AREA'].transform('sum')
        west['AREA_sum_by_building']=west.groupby('BUILDING')['AREA'].transform('sum')
        
        east['PV_capacity_kW']=self.PV_module_efficiency*east['AREA']*east['Area_reduction_factor']
        south_east['PV_capacity_kW']=self.PV_module_efficiency*south_east['AREA']*south_east['Area_reduction_factor']
        south['PV_capacity_kW']=self.PV_module_efficiency*south['AREA']*south['Area_reduction_factor']
        south_west['PV_capacity_kW']=self.PV_module_efficiency*south_west['AREA']*south_west['Area_reduction_factor']
        west['PV_capacity_kW']=self.PV_module_efficiency*west['AREA']*west['Area_reduction_factor']

        east['PV_energy_kWh']=east['PV_capacity_kW']*east['TID']*self.Performance_Ratio
        south_east['PV_energy_kWh']=south_east['PV_capacity_kW']*south_east['TID']*self.Performance_Ratio
        south['PV_energy_kWh']=south['PV_capacity_kW']*south['TID']*self.Performance_Ratio
        south_west['PV_energy_kWh']=south_west['PV_capacity_kW']*south_west['TID']*self.Performance_Ratio
        west['PV_energy_kWh']=west['PV_capacity_kW']*west['TID']*self.Performance_Ratio

        east=east[east['AREA_sum_by_building']>=10]
        south_east=south_east[south_east['AREA_sum_by_building']>=10]
        south=south[south['AREA_sum_by_building']>=10]
        south_west=south_west[south_west['AREA_sum_by_building']>=10]
        west=west[west['AREA_sum_by_building']>=10]
        
        Total_PV_energy_Gagnon_GWh_orientation= (east['PV_energy_kWh'].sum()/1e6)+(south_east['PV_energy_kWh'].sum()/1e6)+(south['PV_energy_kWh'].sum()/1e6)+(south_west['PV_energy_kWh'].sum()/1e6)+(west['PV_energy_kWh'].sum()/1e6)
        
        Total_PV_capacity_Gagnon_MW_orientation= (east['PV_capacity_kW'].sum()/1000)+(south_east['PV_capacity_kW'].sum()/1000)+(south['PV_capacity_kW'].sum()/1000)+(south_west['PV_capacity_kW'].sum()/1000)+(west['PV_capacity_kW'].sum()/1000)

        rooftop_for_TID_filter=concat([east,south_east,south,south_west,west])

        area=rooftop_for_TID_filter['PV_suitable_area_m2'].sum()/1000/1000
        print('Gagnon rooftop area', round(area,4))
        sizes=self.classify_bld_size(rooftop_for_TID_filter)
        return Total_PV_energy_Gagnon_GWh_orientation,Total_PV_capacity_Gagnon_MW_orientation,rooftop_for_TID_filter

    def classify_bld_size(self,rooftop: DataFrame)->list[int]:
        """
        categorize and count the number of buildings for Gagnon et al. 2016 method

        Parameters
        ----------
        rooftop : DataFrame
            dataframe with all the information by segement

        Returns
        ----------
        list
            returns a list of the number of small, medium, and large buildings within the rooftop dataframe
        """
        small_blds=rooftop[rooftop['building_area']<465]
        small_num=small_blds['BUILDING'].nunique()
        area_small=small_blds['PV_suitable_area_m2'].sum()/1000/1000
        
        medium_blds=rooftop[rooftop['building_area']>=465]
        medium_blds=medium_blds[medium_blds['building_area']<4645]
        medium_num=medium_blds['BUILDING'].nunique()
        area_medium=medium_blds['PV_suitable_area_m2'].sum()/1000/1000
        
        large_blgs=rooftop[rooftop['building_area']>=4645]
        large_num=large_blgs['BUILDING'].nunique()
        area_large=large_blgs['PV_suitable_area_m2'].sum()/1000/1000
        print('Number of small, medium, and large buildings:\t',small_num,medium_num,large_num)
        print('Area of small, medium, and large buildings:\t',area_small,area_medium,area_large)
        return [small_num,medium_num,large_num]
    
    def iea_filter(self,rooftop_for_TID: DataFrame,percent_filter:float)-> tuple[float,float,DataFrame]:
        """
        Filters the rooftop segements based on the IEA PVPS Task 7 method by threshold of solar insolation on a rooftop segment.
        
        Parameters
        ----------
        rooftop_for_TID_filter : DataFrame
            dataframe with all the information by segement
        percent_filter : float
            the percent threshold of total annual irradiance to filter the results
        
        Returns
        -------
        tuple[float,float,DataFrame]
            outputs a tuple containing the capacity and energy generation after 
            filtering and the inputted dataframe after filtering
        """
        rooftop=rooftop_for_TID.copy()
        rooftop['Area_reduction_factor']=0.75*0.9/0.891814114*0.96299909
        rooftop.loc[rooftop['SLOPE']==10,'Area_reduction_factor']=0.75*0.9/0.891814114*0.661597709

        rooftop['PV_capacity_kW']=self.PV_module_efficiency*rooftop['AREA']*rooftop['Area_reduction_factor']
        rooftop=rooftop.sort_values(by='Shading derate (%)')
        rooftop['cummulative_sum']=rooftop['AREA'].cumsum(axis=0)

        rooftop=rooftop[rooftop['cummulative_sum']>=rooftop['AREA'].sum()*0.15]

        rooftop['PV_energy_kWh']=rooftop['PV_capacity_kW']*rooftop_for_TID['TID']*self.Performance_Ratio
        Total_PV_capacity_IEA_MW= rooftop.loc[rooftop['POA_sum']>=rooftop['POA_sum'].max()*percent_filter,'PV_capacity_kW'].sum()/1000
        
        Total_PV_energy_IEA_GWh=rooftop.loc[rooftop['POA_sum']>=rooftop['POA_sum'].max()*percent_filter,'PV_energy_kWh'].sum()/1e6

        rooftop=rooftop.loc[rooftop['POA_sum']>=rooftop['POA_sum'].max()*percent_filter]
        rooftop.drop('SLOPE',axis=1, inplace=True)
        rooftop.drop('cummulative_sum',axis=1, inplace=True)


        return Total_PV_capacity_IEA_MW,Total_PV_energy_IEA_GWh,rooftop

class calculate_technical_potential_annual(calculate_technical_potential_hourly):
    def __init__(self,TID_avg_by_FID: DataFrame,region: DataFrame,PR:float,PV_module_efficiency:float)->None:
        self.PV_module_efficiency=PV_module_efficiency
        self.Performance_Ratio= PR
        self.TID=TID_avg_by_FID
        self.region=region
    
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
        
        Weather_dataframe,solpos=self.get_weather(self.region.weather_file,self.region.latitude,self.region.longitude,self.region.altitude,self.region.timezone,'Technical')
        
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
        
        #Inputs for analysis
        #Set values for PV_module_efficiency, Performance_Ratio and Electricity_Consumption that will be used to calculate PV potential in terms of power (PV capacity) and energy
        
        #Make FID the index of the rooftop_for_TID dataframe so that the values align properly
        # rooftop_for_TID.set_index('FID',inplace=True)
        rooftop_for_TID=rooftop_for_TID.reset_index(drop=True)
        self.TID=self.TID.reset_index(drop=True)
        #Include the annual average shading (TID for TimeInDaylight) as a new column in the rooftop_for_TID dataframe
        rooftop_for_TID['TID']=self.TID
        print('Filterd {} points from data that are negative'.format(len(rooftop_for_TID[rooftop_for_TID['TID']<0])) )
        rooftop_for_TID=rooftop_for_TID[rooftop_for_TID['TID']>=0]
        #Multiply the POA by the TID to get annual POA (in kWh/m2) with shading. Later we will want to do a proper calculation with this multiplication performed hourly.
        rooftop_for_TID['POA_with_shading']=rooftop_for_TID['TID']*rooftop_for_TID['POA_SUM']
        Total= rooftop_for_TID.copy()
        area=Total['AREA'].sum()/1000/1000
        #Define area reduction factors to calculate the PV suitable area that will be occupied by PV module        
        rooftop_for_TID['Area_reduction_factor']=0.971838377688576
        #All segments with slopes less than or equal to 10 degrees have had their PV slope set to 10 degrees (treated as flat roofs with PV arrays oriented at 10 degrees)
        rooftop_for_TID.loc[rooftop_for_TID['SLOPE']==10,'Area_reduction_factor']=0.66767045856285
        
        #Create a new column in rooftop_for_TID with 'PV_suitable_area_m2'
        rooftop_for_TID['PV_suitable_area_m2']=rooftop_for_TID['Area_reduction_factor']*rooftop_for_TID['AREA']
        
        # #Critiria used for Gagnon's conditions
        
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
    
class calculate_technical_potential_rep(calculate_technical_potential_hourly):
    def __init__(self,TID_avg_by_FID: DataFrame,region: DataFrame,PR:float,PV_module_efficiency:float,rep_days: int,mode:str)->None:
        self.PV_module_efficiency=PV_module_efficiency
        self.Performance_Ratio= PR
        self.TID=TID_avg_by_FID
        self.region=region
        self.treat_dataframe()

        #Change the slope and aspect for buildings with flat roofs
        self.unique_segments,self.rooftop_save=self.calculate_slope(region.raster_file,region.shapefile)
        
        #Compare the areas with all FIDs and rasterized FIDs to apply a correction at the end
        self.rooftop_save.reset_index(drop=True,inplace=True)
        self.rooftop_save['Area_reduction_factor']=0.971838377688576

        #All segments with slopes less than or equal to 10 degrees have had their PV slope set to 10 degrees (treated as flat roofs with PV arrays oriented at 10 degrees)
        self.rooftop_save.loc[self.rooftop_save['SLOPE']==10,'Area_reduction_factor']=0.66767045856285
        self.TID=where(self.TID<0,0,self.TID)
        self.TID=DataFrame(self.TID)
        #Create a new column in rooftop_for_TID with 'PV_suitable_area_m2'
        self.rooftop_save['PV_suitable_area_m2']=self.rooftop_save['Area_reduction_factor']*self.rooftop_save['AREA']
        self.Weather,solarposition=self.get_weather(region.weather_file,region.latitude,region.longitude,region.altitude,region.timezone,mode)
        
        #Initialize an index for POA_hourly_array
        POA_hourly_array,dni_extra=zeros((len(self.Weather.index),len(self.unique_segments))),irradiance.get_extra_radiation(self.Weather.index)
        solarposition.reset_index(inplace=True)

        self.Weather.reset_index(inplace=True)
        # solpos.reset_index(inplace=True, drop=True)
        dni_extra.reset_index(inplace=True,drop=True)
        ind2=0
        if rep_days==12:
            total_range = chain(range(480,504),range(1224,1248),range(1896,1920),range(2640,2664),
                                range(3360,3384), range(4104,4128), range(4824,4848),range(5568,5592),
                                range(6312,6336), range(7032,7056),range(7776,7800),range(8496,8520))
            January=self.TID.loc[0:23]
            February=self.TID.loc[24:47]
            March=self.TID.loc[48:71]
            April=self.TID.loc[72:95]
            May=self.TID.loc[96:119]
            June=self.TID.loc[120:143]
            July=self.TID.loc[144:167]
            August=self.TID.loc[168:191]
            September=self.TID.loc[192:215]
            October=self.TID.loc[216:239]
            November=self.TID.loc[240:263]
            December=self.TID.loc[264:287]
            temp_list=[January,February,March,April,May,June,July,August,September,October,November,December]
            weights=[1,28/31,1,30/31,1,30/31,1,1,30/31,1,30/31,1]
            
        else:
            total_range = chain(range(1896,1920), range(4104,4128), range(6312,6336), range(8496,8520))
            March=self.TID.loc[0:23]
            June=self.TID.loc[24:47]
            September=self.TID.loc[48:71]
            December=self.TID.loc[72:95]
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
        self.TID=TID_avg_by_FID2.reset_index(drop=True)

        for ind in self.rooftop_save.index: 
            total_irradiance = irradiance.get_total_irradiance(
                self.rooftop_save['SLOPE'][ind], self.rooftop_save['ASPECT'][ind], 
                solarposition['apparent_zenith'],
                solarposition['azimuth'],
                self.Weather['DNI'],
                self.Weather['GHI'], 
                self.Weather['DHI'],
                dni_extra=dni_extra,
                model='haydavies')
            POA_hourly_array[:,ind2]=total_irradiance['poa_global'].copy()/1000
            total_irradiance=total_irradiance.reset_index()
            self.TID.iloc[:,ind2]=self.TID.iloc[:,ind2]*total_irradiance['poa_global']/1000
        
            ind2=ind2+1

        del ind,ind2
        #Next, we will want to assign the contents of POA_hourly_array to the POA_hourly dataframe
        self.POA_hourly = DataFrame(POA_hourly_array,index = self.Weather.index, columns = arange(1,len(self.unique_segments)+1,1))
        self.POA_hourly=self.POA_hourly.reset_index(drop=True)
        self.POA_hourly_energy=self.TID.copy()
        self.POA_hourly=self.POA_hourly.sum(axis=0)
        
        self.POA_hourly.name="POA_sum"
        del POA_hourly_array

        self.TID=self.TID.transpose()
        self.TID.reset_index(drop=True, inplace=True)
        self.POA_hourly_energy=self.POA_hourly_energy.transpose()
        self.rooftop_save.reset_index(inplace=True, drop=True)
        self.rooftop_save.drop(['Area_reduction_factor','FID','AREA_sum_by_building'],axis=1,inplace=True)

    def rep(self) -> list[float]:
        """
        Calculate the technical potential on a representative days.
        
        Returns
        list[float]
            returns a list of the total pv capacity and energy generation
        """
        rooftop_for_TID=self.rooftop_save.copy()
        rooftop_for_TID=self.get_building_footprint(rooftop_for_TID)
        rooftop_for_TID['PV_capacity_kW']=rooftop_for_TID['PV_suitable_area_m2']*self.PV_module_efficiency
        Total_PV_capacity_MW= rooftop_for_TID['PV_capacity_kW'].sum()/1000

        rooftop=rooftop_for_TID.copy()
        self.building_area=rooftop_for_TID.drop_duplicates('BUILDING',keep='first')['building_area'].sum()

        rooftop_for_TID.drop(['PV_suitable_area_m2','building_area','BUILDING','AREA','SLOPE','ASPECT'],axis=1,inplace=True)
        
        print("Building footprint area (analysis region) in km2: ",round(self.building_area/1000/1000,2))
        #PV_energy_kWh
        TID_avg_by_FID=DataFrame(self.TID.values*rooftop_for_TID.values*self.Performance_Ratio, columns=self.TID.columns, index=self.TID.index)

        Total_PV_energy_GWh= TID_avg_by_FID.sum()
        Total_PV_energy_GWh=Total_PV_energy_GWh.sum()/1e6
        
        TID_avg_by_FID=TID_avg_by_FID.sum(axis=1)
        TID_avg_by_FID.name="PV_energy_kWh"
        rooftop['PV_energy_kWh']=TID_avg_by_FID.copy()
        rooftop['TID']=self.TID.sum(axis=1)
        rooftop['POA_sum']=self.POA_hourly
        del TID_avg_by_FID
        rooftop['Shading derate (%)']=rooftop['TID']/rooftop['POA_sum']*100
        weighted_avg_shade=((100-rooftop['Shading derate (%)'])*rooftop['AREA']/rooftop['AREA'].sum()).sum()
        print("Weighted average shading: ",round(weighted_avg_shade,2))
        median_shading_loss=rooftop['Shading derate (%)'].median()
        print("Median shading derate: ", round(median_shading_loss,2))
        rooftop['Optimal_energy']=rooftop['PV_capacity_kW']*self.Performance_Ratio*rooftop['POA_sum'].max()
        coeff_capacity_shade,coeff_elctricity_shade=self.coefficients(rooftop,self.building_area)

        area=rooftop['AREA'].sum()/1000/1000
        print('Total rooftop area', round(area,2))
        ratio_tilted=len(rooftop[rooftop['SLOPE']>10])/len(rooftop)
        ratio_flat=len(rooftop[rooftop['SLOPE']<=10])/len(rooftop)
        print('Fraction of rooftops that are tilted:',round(ratio_tilted,2))
        print('Fraction of rooftops that are flat:',round(ratio_flat,2))

        rooftop.drop(['SLOPE','ASPECT','AREA'],axis=1, inplace=True)

        coeff_capacity_shade=DataFrame(coeff_capacity_shade,columns=['Capacity Coefficient - Shaded','Threshold'])
        coeff_elctricity_shade=DataFrame(coeff_elctricity_shade,columns=['Electricity Coefficient - Shaded','Threshold'])

        return [Total_PV_capacity_MW,Total_PV_energy_GWh,rooftop['BUILDING'].nunique(),
                area,self.building_area/1000/1000,coeff_capacity_shade,coeff_elctricity_shade]
    
    def rep_grid(self) -> list[float]:
        """
        Calculate the technical potential on a representative days.
        
        Returns
        list[float]
            returns a list of the total pv capacity and energy generation
        """
        self.rooftop_save['PV_capacity_kW']=self.rooftop_save['PV_suitable_area_m2']*self.PV_module_efficiency

        #PV_energy_kWh
        TID_avg_by_FID=DataFrame(self.TID.values*self.rooftop_save['PV_capacity_kW'].to_frame().values*self.Performance_Ratio, columns=self.TID.columns, index=self.TID.index)

        self.rooftop_save['PV_energy_kWh']=TID_avg_by_FID.sum(axis=1)
        del TID_avg_by_FID
        self.rooftop_save['TID']=self.TID.sum(axis=1)
        self.rooftop_save['POA_sum']=self.POA_hourly
        
        hourly_poa_bin_weighted,PV_capacity_GW,PV_energy_MWh=self.potential_bin(self.rooftop_save,self.POA_hourly_energy)
        self.rooftop_save.drop(['TID','PV_energy_kWh','POA_sum'],axis=1,inplace=True)

        hourly_poa_bin_weighted=DataFrame(hourly_poa_bin_weighted).reset_index(drop=True)
        PV_capacity_GW.append(0.0)
        PV_energy_MWh.append(0.0)

        return hourly_poa_bin_weighted, self.Weather["Temperature"],Series(PV_capacity_GW),Series(PV_energy_MWh)