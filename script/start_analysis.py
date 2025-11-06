import numpy as np
import calculate_deployed_capacity
import TimeInDaylight
import region_data
import calculate_technical_potential
from tools import file_handle
import os
import hosting_capacity_variables
import scenarios 
import glob
from tools import spatial_toolset
from writing_output import print_results, write_output_file

def calculate_one_region_grid(region:str,file_location:str,resolution:int|float,hosting_capacity:hosting_capacity_variables,
                                mode:str,p_range:list[float],q_range:list[float],hourly_demand:str,annual_demand:str,starting_year:int,
                                ending_year:int,scaling_option:bool,shading_granularity:str='hourly',
                                cap_coefficient_shade:list=[],elec_coefficient_shade:list=[])->None:
    """
    Setups and runs the detailed (Grid) analysis on an hourly basis.

    Parameters
    ----------
    file_location: str
        location to write the files
    p_range : list[float]
        list of p values from the Bass equation. These numbers should be close to zero (ex. 0.000001)
    q_range : list[float]
        list of q values from the Bass equation.
    mode : str
        'Technical', 'Market', or 'grid' mode. The input for this function should be 'grid'
    resolution : int|float
        resolution of the DSM files
    hosting_capacity : hosting_capacity_variables
        container for the variables needed in the hosting capacity analysis
    region : str
        region name to calculate the hosting capacity to 2050
    hourly_demand : str
        file name for the hourly demand profile of each region under study
    annual_demand : str
        file name for the annual demand profile of each region under study
    scaling_option : bool
        option whether to scale the technical potential for the rest of the analysis or use them outputs as is. True to use coefficients to scale the output.
    cap_coefficient_shade,elec_coefficient_shade : list
        list of the input coefficients for the capacity and energy, including the shading.
    """
    region_variables = region_data.location(region,mode,scaling_option,cap_coefficient_shade,elec_coefficient_shade)
    #output/input file locations
    #user can change to the desired location of the outputs/inputs below, if needed
    region_variables.mosaic=file_location+r'\mosaic_'+region_variables.file_classifier+'.tif' #file name location of the output mosaic file
    region_variables.raster_file=file_location+'\\'+region_variables.file_classifier+'_rooftop_Raster.tif' #file name location of the output rasterized shapefile
    region_variables.shapefile=file_location+'\\'+region_variables.file_classifier+'_rooftop.shp' #file name location of the output shapefile from the segmentation
    
    calculate_deployed_capacity.check_calculate_technical_files(file_location,region_variables)
    analysis=calculate_deployed_capacity.SensitivityAnalysis(region_variables)
    bldg_scenarios,cost_scenarios,elec_cost_scenarios,pv_eff,pv_pr,market_share_scenarios=set_up_scenarios()
    time=list(range(0,len(bldg_scenarios[0][0])))
    time=np.array(time, dtype='float32')
    
    analysis.sensitivity_analysis(p_range,q_range,cost_scenarios,elec_cost_scenarios,pv_eff,region,market_share_scenarios,
                                pv_pr,bldg_scenarios,file_location,starting_year,ending_year,time,mode,annual_demand,hourly_demand,
                                shading_granularity,hosting_capacity,scaling_option)

def calculate_all_regions_grid(file_location:str,resolution:int|float,mode:str,p_range:list[float],q_range:list[float],regions:list[str],
                                 hosting_capacity:hosting_capacity_variables,hourly_demand:list[str],annual_demand:list[str],starting_year:int,
                                 ending_year:int,scaling_option:bool,shading_granularity:str='hourly'
                                 ,cap_coefficient_shade:list=[],elec_coefficient_shade:list=[])->None:
    """
    Setups and runs the provincial run with hosting capacity. This method will runs all regions and territories in Canada.

    Parameters
    ----------
    starting_year : int
        starting year for the analysis ex. 2019
    file_location: str
        location to write the files
    p_range : list[float]
        list of p values from the Bass equation. These numbers should be close to zero (ex. 0.000001)
    q_range : list[float]
        list of q values from the Bass equation.
    mode : str
        'Technical', 'Market', or 'grid' mode. The input for this function should be 'grid'
    resolution : int|float
        resolution of the DSM files
    hosting_capacity : hosting_capacity_variables
        container for the variables needed in the hosting capacity analysis
    regions : list[str]
        list of region names to calculate the hosting capacity to 2050
    hourly_demand : list[str]
        list of file names for the hourly demand profile of each region under study
    annual_demand : list[str]
        list of file names for the annual demand profile of each region under study
    scaling_option : bool
        option whether to scale the technical potential for the rest of the analysis or use them outputs as is. True to use coefficients to scale the output.
    cap_coefficient_shade,elec_coefficient_shade : list
        list of the input coefficients for the capacity and energy, including the shading.
    """

    bldg_scenarios,cost_scenarios,elec_cost_scenarios,pv_eff,pv_pr,market_share_scenarios=set_up_scenarios()
    time=list(range(0,len(bldg_scenarios[0][0])))
    time=np.array(time, dtype='float32')
    analysis=calculate_deployed_capacity.SensitivityAnalysis()
    analysis.sensitivity_analysis_all_regions(p_range,q_range,cost_scenarios,elec_cost_scenarios,pv_eff,market_share_scenarios,
                                                pv_pr,bldg_scenarios,file_location,starting_year,ending_year,time,mode,regions,annual_demand,
                                                cap_coefficient_shade,elec_coefficient_shade,hourly_demand,shading_granularity,
                                                hosting_capacity,resolution,scaling_option)

def market(file_location:str,starting_year:int,p_range:list[float],q_range:list[float],mode:str,region:str,annual_demand:str,ending_year:int,
           cap_coefficient_shade:list=[],elec_coefficient_shade:list=[])->None:
    """
    Setups and runs the provincial run without hosting capacity. This method will only run for one region.

    Parameters
    ----------
    starting_year : int
        starting year for the analysis ex. 2019
    file_location: str
        location to write the files
    p_range : list[float]
        list of p values from the Bass equation. These numbers should be close to zero (ex. 0.000001)
    q_range : list[float]
        list of q values from the Bass equation.
    mode : str
        'Technical', 'Market', or 'grid' mode. The input for this function should be 'Market'
    region : str
        name of the region (ex. ON)
    cap_coefficient_shade,elec_coefficient_shade : list
        list of the input coefficients for the capacity and energy, including the shading.
    """
  
    bldg_scenarios,cost_scenarios,elec_cost_scenarios,pv_eff,pv_pr,market_share_scenarios=set_up_scenarios()
    region_variables = region_data.location(region,mode,True,cap_coefficient_shade,elec_coefficient_shade)
    time=list(range(0,len(bldg_scenarios[0][0])))
    time=np.array(time, dtype='float32')
    analysis=calculate_deployed_capacity.SensitivityAnalysis(region_variables)
    analysis.sensitivity_analysis(p_range,q_range,cost_scenarios,elec_cost_scenarios,pv_eff,region,market_share_scenarios,
                                pv_pr,bldg_scenarios,file_location,starting_year,ending_year,time,mode,annual_demand)
    
def market_all(file_location:str,starting_year:int,p_range:list[float],q_range:list[float],mode:str,regions:list[str],annual_demand:list[str],
               ending_year:int,cap_coefficient_shade:list=[],elec_coefficient_shade:list=[])->None:
    """
    Setups and runs the provincial run without hosting capacity. This method will runs all regions specified

    Parameters
    ----------
    starting_year : int
        starting year for the analysis ex. 2019
    file_location: str
        location to write the files
    p_range : list[float]
        list of p values from the Bass equation. These numbers should be close to zero (ex. 0.000001)
    q_range : list[float]
        list of q values from the Bass equation.
    mode : str
        'Technical', 'Market', or 'grid' mode. The input for this function should be 'Market'
    cap_coefficient_shade,elec_coefficient_shade : list
        list of the input coefficients for the capacity and energy, including the shading.
    """
  
    bldg_scenarios,cost_scenarios,elec_cost_scenarios,pv_eff,pv_pr,market_share_scenarios=set_up_scenarios()
    time=list(range(0,len(bldg_scenarios[0][0])))
    time=np.array(time, dtype='float32')
    analysis=calculate_deployed_capacity.SensitivityAnalysis()
    analysis.sensitivity_analysis_all_regions(p_range,q_range,cost_scenarios,elec_cost_scenarios,pv_eff,market_share_scenarios,
                                                pv_pr,bldg_scenarios,file_location,starting_year,ending_year,time,mode,regions,
                                                annual_demand,cap_coefficient_shade,elec_coefficient_shade)

def hourly_region(file_location:str,region: region_data,PR:float,eff:float,mode:str)->list[float]:
    """
    Setups and runs the detailed (Technical) analysis on an hourly basis.

    Parameters
    ----------
    region : municipalities
        object containing location-specific data
    file_location: str
        location to write the files
    PR : float
        performance ratio of the PV system
    eff : float
        module electrical effciency of the PV system
    mode : str
        'Technical', 'Market', or 'grid' mode. The input for this function should be 'Technical'
    
    Returns
    ----------
    data : list
        list of the results
    """
    file_save=file_handle()
    saved_file=file_location+r'\TimeInDaylight_hourly_' + region.file_classifier+'.ftr'
    #run shading if the saved_file has not been created yet. If it existes use the file to run the rst of the calculations
    if not(os.path.isfile(saved_file)):
        shading=TimeInDaylight.TID(region,file_location)
        print("Starting shading")
        TID=shading.hourly()
        file_save.write_file(TID,saved_file)
        TID.set_index('index',inplace=True)
        print("Shading completed\n")
    else:
        TID=file_save.extract_data(saved_file)
    
    technical_potential=calculate_technical_potential.calculate_technical_potential_hourly(TID,region,PR,eff,mode)
    data=technical_potential.hourly_region(file_location)

    return data
   
def annual_analysis(region: region_data,file_location: str,performance_ratio,module_efficiency)->list[float]:
    """
    Setups and runs the detailed (Technical) analysis on an annual basis.

    Parameters
    ----------
    region : municipalities
        object containing location-specific data
    file_location: str
        location to write the files
    performance_ratio:float
        inputted performance ratio for the module
    module_efficiency:float
        inputted module efficiency

    Returns
    ----------
    data : list
        list of the results
    """
    shading=TimeInDaylight.TID(region,file_location)
    TID=shading.annual()
    technical_potential=calculate_technical_potential.calculate_technical_potential_annual(TID,region,performance_ratio,module_efficiency)
    data=technical_potential.annual()
    return data

def rep_analysis(rep_days: int,region: region_data,file_location: list,performance_ratio,module_efficiency)->list[float]:
    """
    Set ups and runs the detailed (Technical) analysis for either 12 or 4 representative days during the year. 12 days will use one day per month. 4 days will use the equinox days.
    
    Parameters
    ----------
    rep_days : int
        number of representative days to use in a year, 4 (equinox) or 12 (once per month)
    region : municipalities
        object containing location-specific data
    file_location: str
        location to write the files
    performance_ratio:float
        inputted performance ratio for the module
    module_efficiency:float
        inputted module efficiency

    Returns
    ----------
    data : list
        list of the results
    """
    file_save=file_handle()
    if rep_days==12:
        saved_file=file_location+r'\TimeInDaylight_rep_12_' + region.file_classifier+'.ftr'
    else:
        saved_file=file_location+r'\TimeInDaylight_rep_4_' + region.file_classifier+'.ftr'
        
    if not(os.path.isfile(saved_file)):
        shading=TimeInDaylight.TID(region,file_location)
        print("Starting shading")
        TID=shading.representative(rep_days)
        file_save.write_file(TID,saved_file)
        TID.set_index('index',inplace=True)
        print("Shading completed\n")
    else:
        TID=file_save.extract_data(saved_file)
    technical_potential=calculate_technical_potential.calculate_technical_potential_rep(TID,region,performance_ratio,module_efficiency)
    data=technical_potential.rep(rep_days)
    return data

def set_up_scenarios()->list:
    """
    This function set ups the different scenarios for the sensitivity analysis.

    Returns
    -------
    list
        list contaning a list of the scenarios set up in the function
    """
    bldg=scenarios.Building_stock()
    cost=scenarios.PV_cost()
    electricity_cost=scenarios.elec_cost()
    maximum_market_share=scenarios.max_market_share()
    pv_specs=scenarios.PV_specifications()

    bldg_scenarios=[bldg.df_bldg_res,bldg.df_bldg_com,bldg.file_names]
    elec_cost_scenarios=[electricity_cost.df_elec_res,electricity_cost.df_elec_com,electricity_cost.file_names]
    cost_scenarios=[cost.df_pv_cost_res,cost.df_pv_cost_com,cost.file_names]
   
    pv_eff=[pv_specs.df_pv_eff,pv_specs.df_pv_temp,pv_specs.file_names_eff]
    pv_pr=[pv_specs.df_pv_pr_res,pv_specs.df_pv_pr_com,pv_specs.df_pv_deg,pv_specs.file_names_PR]
    market_share_scenarios=[maximum_market_share.df_market_res,maximum_market_share.df_market_com,maximum_market_share.file_names]

    return bldg_scenarios,cost_scenarios,elec_cost_scenarios,pv_eff,pv_pr,market_share_scenarios

def run_detailed(file_location:str,mode:str,shading_granularity:str,resolution:int|float,region_name:list[str],performance_ratio:float,
                 module_efficiency:float):
    """
    This function starts the analysis for the detailed, technical potential, option and outputs the results.

    Parameters
    -------
    file_location: str
        location of the files to output
    mode: str
        operational mode
    shading_granilarity: str
        option for the shading granularity
    resolution:int|float
        resolution used to create the DSM files
    region_name:list[str]
        list of the region names used in the analysis
    performance_ratio:float
        inputted performance ratio for the module
    module_efficiency:float
        inputted module efficiency
    """

    for name in region_name:
        region_variables = region_data.location(name,mode)
        region_variables.mosaic=file_location+r'\mosaic_'+region_variables.file_classifier+'.tif' #file name location of the output mosaic file
        region_variables.raster_file=file_location+'\\'+region_variables.file_classifier+'_rooftop_Raster.tif' #file name location of the output rasterized shapefile
        region_variables.shapefile=file_location+'\\'+region_variables.file_classifier+'_rooftop.shp' #file name location of the output shapefile from the segmentation

        check_calculate_technical_files(region_variables,resolution)
        
        if shading_granularity=='annual':
            data=annual_analysis(region_variables,file_location,performance_ratio,module_efficiency)
            
        elif shading_granularity=='representative':
            rep_days=12
            data=rep_analysis(rep_days,region_variables,file_location,performance_ratio,module_efficiency)
        elif shading_granularity=='hourly':
            data=hourly_region(file_location,region_variables,performance_ratio,module_efficiency,mode)

        print_results(data,region_variables) 
        write_output_file(data,file_location,region_variables)


def check_calculate_technical_files(region_variables:region_data,resolution:float|int)->None:
    """
    This function checks whether the DSM, mosaic and segmentation files exist for the region used in the analysis.

    Parameters
    -------
    region_variables: region_data
        object containing file locations for lidar, DSM, segmentation files and region-specific variables
    resolution:float
        resolution used to create the DSM files
    """

    #If the files don't already exist for the DSM files (run_lidar), combining into a mosaic (run_mosaic), and creating the segmentation files (run_seg)
    if len(glob.glob(region_variables.lidar+"/*.tif"))==0:
        print("Creating DSM files...")
        region_variables.run_lidar(resolution)
        print("Created all DSM files\n")
    if not(os.path.isfile(region_variables.mosaic)):
        print("Starting mosaic...")
        region_variables.run_mosaic()
        print("Created mosaic\n")
    if not(os.path.isfile(region_variables.shapefile)):
        print("Starting segmentation...")
        region_variables.run_seg()
        spatial=spatial_toolset()
        spatial.rasterize_polygon(region_variables.mosaic,region_variables.shapefile,region_variables.raster_file,resolution)
        print("Finished segmentation\n")                                

