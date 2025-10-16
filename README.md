# SOLACE: Solar Open-source for Location-based Assessment of Capacity and Energy

## Project Description
This project enables modelling of rooftop photovoltaic (RPV) potential of different regions using Light Dectection and Ranging (lidar) and building footprint data. It has three modes of operation: Technical, Market, and Grid with or without scaling. The Technical mode (necessary first step) calculates RPV technical potential for each year in a time period of interest, i.e. the capacity and electricity generation potential of all viable rooftop surfaces in a region of interest (see the report [published by CanmetENERGY in Varennes](https://natural-resources.canada.ca/science-data/science-research/research-centres/assessing-photovoltaic-potential-canadian-building-stock) for a description of the approach). The (optional) Market mode estimates deployed RPV capacity, and associated electricity generation, for each year in a chosen time period, without taking into account grid hosting capacity constraints. The (optional) Grid mode provides the same estimates, this time taking into account grid constraints. A description of the process for each of these modes is available in the [Usage section](#usage). For the technical and grid modes, building footprints and lidar data are required as inputs. The market mode only requires as input the total ground floor surface area for the region(s) of interest.

Different free, open source platforms have been used in the process. Various packages from [WhiteboxTools Open Core](https://www.whiteboxgeo.com/geospatial-software/) in Python are used for lidar data analysis. For solar resource and PV modeling, [pvlib](https://pvlib-python.readthedocs.io/en/stable/) is used on the Python platform. [QGIS](https://qgis.org/) was used primarily for visualization, but also for rasterization, in the event that there were errors with the code to change data projections and clip shapefiles.

The authors used the code with Canadian municipalities, but it can be used in any region with the required inputs. Users should acquire lidar data and building footprints to use with the code. Regarding meteorological data, suitable modifications to the parts of the code that read these data will need to be performed if their format differs from those used in the Canadian case (see below).

For the case of Canada, [lidar](https://open.canada.ca/data/en/dataset/7069387e-9986-4297-9f55-0288e9676947) and [building footprints](https://open.canada.ca/data/en/dataset/7a5cda52-c7df-427f-9ced-26f19a8a64d6)  can be downloaded for free from databases created by the Canada Centre for Mapping and Earth Observation (CCMEO). The Technical mode was applied to Canada and its provinces and territories for the year 2019 to generate the results described in a report [published by CanmetENERGY in Varennes](https://natural-resources.canada.ca/science-data/science-research/research-centres/assessing-photovoltaic-potential-canadian-building-stock). The National Renewable Energy Laboratory (NREL) National Solar Radiation Database [(NSRDB)](https://nsrdb.nrel.gov/) should be used for all Canadian meteorological data except those above a latitude of 60°, in which case [Canadian Weather Year for Energy Calculation (CWEC)](https://open.canada.ca/data/en/dataset/55438acb-aa67-407a-9fdb-1cb21eb24e28) can be used in epw format for the Technical mode. For the Grid mode, [NASA POWER](https://power.larc.nasa.gov/data-access-viewer/) should be used for all regions with latitudes above 60°. 

## Usage

The code and outputs are split into 3 different modes of operations that will be explained below. In general, reusable functions for this project are contained in the \tools directory. Each function's header contains a function description. This code requires that the building footprint and lidar data have matching coordinate systems. If this is not the case for the user's data, or if it unknown whether this is the case or not, please follow the steps listed in [Reprojecting Shapefiles](#reprojecting-shapefiles) 

IMPORTANT NOTE: the file_location variable in the example_script files refers to the location where all the output files will the located. In the case of saved files (ex. saved shading files with file extension ftr), these will also be read from this location. This will happen when re-running the same code, or when running the Technical, Grid, or Grid_scale modes (interchangebly). 

A full listing of the contents of each directory is contained below in the [Brief description of directories and files](#brief-description-of-directories-and-files) section.

### **Technical**
The flowchart below explains the process used within the code.

![Code flowchart](images\Code_diagram_technical.drawio.png)  


The script [Example_script_technical.py](script\Example_script_technical.py) provides an example of how the code can be run. 
Use the file [Example_script_technical_coeff.py](script\Example_script_technical_coeff.py) to calculate the technical potential with inputted coefficients

#### Inputs:
**In the example_script file**
1. region_name: List of names for regions in the study (name must match with the file names in the script\batch_inputs folders) 
2. file_location: Path to the directory for all output files (needs to be created prior to running)
3. shading_granularity: The method used to compute shading losses. Options are annual, hourly, or representative. In the annual case, the script computes the annual average shading loss. In the hourly case, shading is computed for each hour of the year. In the representative case, shding is computed for each hour of 12 representative days (one per month), and these hourly shadings are applied to other days in the corresponding month.
4. performance_ratio: PV system annual performance ratio
5. module_efficiency: PV module efficiency 
6. resolution: Resolution for the Digital Surface Model (DSM) files that will be created (represents the pixel size, so an input of 1 is 1 m2 pixel area)

**In the script\batch_inputs\Technical folder**
One file ([Example1.txt](script\batch_inputs\Technical\Example1.txt)) to modify/create in this folder per region in the analysis with inputs of
1. bldg_footprint_shapefile: Location for the building footprint file for that region (file format (.shp))
2. lidar_LAS_folder: Location (folder) for the lidar files for that region (file format: LAS)
3. weather_file: path to the file for the region. The code currently takes input with format consistent with [NREL NSRDB](https://nsrdb.nrel.gov/) for locations below 60°, and [CWEC](https://open.canada.ca/data/en/dataset/55438acb-aa67-407a-9fdb-1cb21eb24e28) for above
4. latitude_degrees: Latitude of the region in decimal degrees
5. longitude_degrees: Longitude of the region in decimal degrees
6. UTC_offset: UTC offset for the region (format example '-06:00')
7. altitude_m: Elevation of the region in meters
8. file_classifier: name of the region separated by '_' between words. Used to name the output files

### **Market**
The flowchart below explains the process used within the code.

![Code flowchart](images\Code_diagram_market.drawio.png)  


The script [Example_script_market.py](script\Example_script_market.py) provides an example of how the code can be run. 

#### Inputs:
**In the example_script file**
1. file_location: Path to the directory for all output files (needs to be created prior to running). Should be distinct from location for Technical mode, or that will get overwritten.
2. p_range: List of values to consider for Bass diffusion model parameter p (or use defaults that are currently available)
3. q_range: List of values to consider for Bass diffusion model parameter q (or use defaults that are currently available)
4. starting_year: Starting year for the analysis
5. ending_year: Ending year for the analysis
6. cap_coefficient_shade: Coefficient Uf2 used to calculate the capacity by resource bin (can be calculated from mode 'Technical')
7. elec_coefficient_shade: Coefficient Yr used to calculate energy generation by resource bin (can be calculated from mode 'Technical')
8. region_names: List of names for regions in the study (name must match with the file names in the script\batch_inputs folders) 


**In the electricity_demand folder**
Input the annual electricity demand per region in the analysis (annual values in MWh, hourly values in MW). NOTE: make sure the name of the files is the same as the region name inputted into the example script file. If no annual data is provided, the code will still run, but the data for the percentage of the demand will return -999 instead.
See template within folder for the format

**In the scenarios folder**
Leave as is or change the scenario files to add or remove scenarios or modify the numbers within. If not using the different provinces in Canada as input, change the files within the elec_cost_data and building_growth_data as these files are location based. For more information on the scenario files, see section [Brief description of directories and files](#brief-description-of-directories-and-files).

**In the script\batch_inputs\Market folder**
One file ([Example1.txt](script\batch_inputs\Market\Example1.txt)) to modify/create in this folder per region in the analysis, containing:
1. ground_floor_res_km2: Total ground floor area in km2 for residential buildings
2. ground_floor_com_km2: Total ground floor area in km2 for commercial and institutional buildings
3. daily_insolation_kWh/m2: Daily mean insolation (in kWh/m2) for the region in the plane of an unshaded, optimally oriented fixed surface
4. historical_capacity_MW_DC: Historical installed RPV capacity at the starting year in MW


### **Grid**
The flowchart below explains the process used within the code.

![Code flowchart](images\Code_diagram_Grid.drawio.png)  


The script [Example_script_grid.py](script\Example_script_grid.py) provides an example of how the code can be run. 

**In the example_script file**
1. scaling_option: set to False if coefficients should be used to calculate the technical potential instead of the results from the inputted region, i.e. if  scaling up the results from the region used with lidar data to calculate a larger area. Example: scaling up from the shaded POA calculated for Toronto,CA to calculate the province-wide results for Ontario
2. region_names: List of names for regions in the study (name must match with the file names in the script\batch_inputs folders) 
3. starting_year: Starting year for the analysis
4. ending_year: Ending year for the analysis
5. file_location: Path to the directory for all output files (needs to be created prior to running). Should use the same file_location as for the Technical mode in order to use outputs from that mode.
6. u_c: PVsyst Fayman temperature coefficient constant, Uc
7. u_v: PVsyst Fayman temperature coefficient multiplying wind speed, Uv
8. lifetime_years: PV module lifetime in years
9. dc_to_ac_capacity_ratio: DC to AC capacity ratio, ratio of the total DC power capacity of the PV arrays to the total AC power capacity of the inverters
10. inverter_efficiency_nominal: efficiency rating when inverters operate at their maximum capacity or 100% load
11. hosting_limit: cap on RPV output as a fraction of demand applied at each hour
12. p_range: List of values to consider for Bass diffusion model parameter p (or use defaults that are currently available)
13. q_range: List of values to consider for Bass diffusion model parameter q (or use defaults that are currently available)

**In the electricity_demand and electricity_demand\hourly folders**
Input the demand profiles (annual and hourly) per region in the analysis (annual values in MWh, hourly values in MW). NOTE: make sure the name of the files is the same as the region name inputted into the example script file. See template within folder for the format

**In the scenarios folder**
Leave as is or change the scenario files to add or remove scenarios or modify the numbers within. If not using the different provinces in Canada as input, change the files within the elec_cost_data and building_growth_data as these files are location based. For more information on the scenario files, see section [Brief description of directories and files](#brief-description-of-directories-and-files).

**In the batch_inputs\Grid folder**
One file ([Example1.txt](script\batch_inputs\Grid\Example1.txt)) to modify/create in this folder per region in the analysis with inputs of
1. bldg_footprint_shapefile: Path to the building footprint file for that region (file format (.shp))
2. lidar_LAS_folder: Path to the lidar files for that region (file format: LAS)
3. weather_file: Path to the weather file for the region. The code currently takes input with format consistent with [NREL NSRDB](https://nsrdb.nrel.gov/) for locations below 60°, and [NASA Power](https://power.larc.nasa.gov/data-access-viewer/) 
4. latitude_degrees: Latitude of the region in decimal degrees
5. longitude_degrees: Longitude of the region in decimal degrees
6. UTC_offset: UTC offset, format example '-06:00'
7. altitude_m: Elevation of the region in meters
8. file_classifier: File classifier, name of the region separated by '_' between words. Used to name the output files
9. historical_capacity_MW_DC: Historical installed RPV capacity at the starting year, in MW
10. daily_insolation_kWh/m2: Daily mean insolation (in kWh/m2) for the region in the plane of an unshaded, optimally oriented fixed surface
11. division_res_bldgs: Fraction of buildings within the region that are residential


### **Grid with Scaling option enabled**
The flowchart below explains the process used within the code.

![Code flowchart](images\Code_diagram_Grid_scale.drawio.png)  


The script [Example_script_grid_scale.py](script\Example_script_grid_scale.py) provides an example of how the code can be run. 

**In the example_script file**
1. scaling_option: set to True if coefficients should be used to calculate the technical potential instead of the results from the inputted region, i.e. if scaling up the results from the region used with lidar data to calculate a larger area. Example: scaling up from the shaded POA calculated for Toronto, CA to calculate the province-wide results for Ontario.
2. region_names: List of names for regions in the study (name must match with the file names in the script\batch_inputs folders) 
3. starting_year: Starting year for the analysis
4. ending_year: Ending year for the analysis
5. cap_coefficient_shade: Coefficient Uf2 used to calculate the capacity by resource bin (can be calculated from mode 'Technical')
6. elec_coefficient_shade: Coefficient Yr used to calculate energy generation by resource bin (can be calculated from mode 'Technical')
7. file_location: Path to the directory for all output files (needs to be created prior to running). Should use the same file_location as for the Technical mode in order to use outputs from that mode.
8. u_c: PVsyst Fayman temperature coefficient constant, Uc
9. u_v: PVsyst Fayman temperature coefficient multiplying wind speed, Uv
10. lifetime_years: PV module lifetime in years
11. dc_to_ac_capacity_ratio: DC to AC capacity ratio, ratio of the total DC power capacity of the PV arrays to the total AC power capacity of the inverters
12. inverter_efficiency_nominal: efficiency rating when inverters operate at their maximum capacity or 100% load
13. hosting_limit: cap on RPV output as a fraction of demand applied at each hour
14. p_range: List of values to consider for Bass diffusion model parameter p (or use defaults that are currently available)
15. q_range: List of values to consider for Bass diffusion model parameter q (or use defaults that are currently available)


**In the electricity_demand and electricity_demand\hourly folders**
Input the demand profiles (annual and hourly) per region in the analysis (annual values in MWh, hourly values in MW). NOTE make sure the name of the files is the same as the region name inputted into the example script file. See template within folder for the format.

**In the scenarios folder**
Leave as is or change the scenario files to add or remove scenarios or modify the numbers within. If not using the different provinces in Canada as input, change the files within the elec_cost_data and building_growth_data as these files are location based. For more information on the scenario files, see section [Brief description of directories and files](#brief-description-of-directories-and-files).

**In the batch_inputs\Grid folder**
One file ([Example1_scale.txt](script\batch_inputs\Grid_scale\Example1_scale.txt)) to modify/create in this folder per region in the analysis with inputs of
1. bldg_footprint_shapefile: Path to the building footprint file for that region (file format (.shp))
2. lidar_LAS_folder: Path to the lidar files for that region (file format: LAS)
3. weather_file: Path to the weather file for the region. The code currently takes input with format consistent with [NREL NSRDB](https://nsrdb.nrel.gov/) for locations below 60°, and [NASA Power]() 
4. latitude_degrees: Latitude of the region in decimal degrees
5. longitude_degrees: Longitude of the region in decimal degrees
6. UTC_offset: UTC offset, format example '-06:00'
7. altitude_m: Elevation of the region in meters
8. file_classifier: File classifier, name of the region separated by '_' between words. Used to name the output files
9. historical_capacity_MW_DC: Historical installed RPV capacity at the starting year, in MW
10. daily_insolation_kWh/m2: Daily mean insolation (in kWh/m2) for the region in the plane of an unshaded, optimally oriented fixed surface
11. ground_floor_res_km2: Total ground floor area in km2 for residential buildings
12. ground_floor_com_km2: Total ground floor area in km2 for commercial and institutional buildings


## Runtime Dependencies

Code was run with python 3.13.7

The requirements.txt file can be used to re-create the Python environment that was used to run the scripts. 
The package GDAL needs to be installed separately with either 'pip install gdal' or with a pre-compiled wheel found [here](https://github.com/cgohlke/geospatial-wheels). The file to install for Python 3.13 is under the folder env.

## Brief description of directories and files

All python files are listed below by directory with a short description.

**Main Directory**

**Directory: \script**

*Example_script_mode.py:* there are 4 versions of this file for each option available. The ending of the file indicates what mode it runs. Run this file to complete the analysis. The user must specify some input parameters in the file and in the folder called "batch_inputs". The folder in 'batch_inputs' indicates the mode these inputs are for.

*writing_output.py:*  This file also contains methods to print to console and write to an excel file and text file a summary of the results for the Technical mode.

*region_data.py:* this contains user-supplied paths for all the files needed for the analysis and all the files generated by the analysis. These include the mosaic digital surface model (DSM) file, the building footprint shapefile, the segmentation shapefile, the rasterized segmentation file, the lidar files and the weather file (based on the municipality). This file also includes functions to run the Lidar.py and Segmentation.py files. Other input parameters are the latitude, longitude and time zone (UTC offset) for each municipality. 

*Lidar.py:* This creates a DSM from a lidar point cloud. 
A DSM reflects the elevation of the tops of all off-terrain objects (i.e. non-ground features) contained within the data set.
The user must specify some input parameters based on the lidar datasets. There is also a function used to combine multiple images created by the DSM method, to make a single raster file.

*TimeInDaylight.py:* This calculates the proportion of time each grid cell in the DSM is unshaded on an hourly and annual basis. It includes functions to validate the code and different methodologies for calculating the shading. The generated DSM file from Lidar.py is used as an input for this tool.

*calculate_technical_potential.py:* Calculates the hourly and annual sum of the plane of array (POA) irradiance for each rooftop segment including the impact of shading. It also calculates the technical potential for the more detailed analyses. 

*Segmentation.py:* This is used to identify rooftop segments from the lidar point cloud. In addition to lidar data, the building footprints (vector) file is required for this tool. (In this project the building footprint data were generated by CCMEO from the associated lidar data).

Note: To be able to run this tool, the coordinate system of the building footprints should be reprojected to match that of the lidar data. The reprojected building footprints shapefile should be in the same folder as the lidar data. The loop in this file generates segments using different input parameters. (Eventually, we selected threshold=0.4 and norm_diff=5.0 for subsequent analysis.)

*calculate_deployed_capacity.py:* used to calculate the deployed capacity and electricity with and without grid constraints. 

*hosting_capacity_variables.py:* used as a container for the input variables needed to calculate the grid hosting capacity limits (used only for mode 'Grid')

**Directory: \script\tools**

*file_handle.py:* used to read and write the shading data.

*lidar_functions.py:* used to get the info for each lidar file, including the average point cloud density (outputted and summarized into an excel sheet) and used to convert the .laz format (compressed lidar files) to .las files (can then be used for the analysis). The converter from laz to las requires the use of the laszip.exe file. This is available within LAStools and can be dowloaded from https://rapidlasso.com/lastools/. Once this is downloaded, add the file location to the inputs. This function also works with a distinct file format with a directory that looks like:
/path/region_name
    /LAS files
    /LAZ files
It has three inputs, the file location for laszip, the region name (used in the file path), directory where the files and subfolders are located. A fourth input is used if using the lidar info function to define the path where the output file for the summary of the point cloud densities should be created and what it is called.

*spatial_toolset.py:* used to convert the segmentation vector file to a raster file without the need of another program such as QGIS or ArcGIS.

**Directory: \script\WBT**

This directory was downloaded from [WhiteboxTools Open Core](https://www.whiteboxgeo.com/) and is used to perform specific functionality within the code to generate the DSM files and assemble them into a mosaic, create rooftop segments, and calculate the shading on each segment. The code has only been tested with version 1.4, if the linux or other version of the package is required, please download the necessary files from the [WBT github](https://github.com/jblindsay/whitebox-tools/releases/tag/1.4.0).

**Directory: \script\electricity_demand**

This directory contains the annual and hourly electricity demand from 2020 to 2050 for the use case, but this can be changed. The annual demand is in \script\electricity_demand while the hourly is within \script\electricity_demand\hourly.  A template is provided in both of those folders. The original files used by the authors were provided by the Canada Energy Regulator (CER).

**Directory: \script\scenarios**

This directory contains the files for the scenarios used in Market and Grid modes. The python files located in this directory extract the data from the excel files in the sub-folders. The analysis conducted  with this code (done for Canada) used the following variables for scenarios: building stock growth, electricity cost evolution, maximum market share vs. payback period, PV cost evolution, evolution in PV module efficiency and RPV system performance ratio. The files contain data from 2022 to 2050 and can be modified for the specific use. 
The variables for the building stock and electricity cost are region specific. Use a different column in these files for each region in the analysis (currently has values for each province and territory in Canada) and use the same name as what is inputted in to the example script.
To add in more scenarios, add in files of a similar format to the folders in question (i.e. to add in a scenario for the electricity cost, simply add in a file with the same format to the elec_cost_data folder). Conversely, to remove a scenario, delete the file for the scenario you would like to remove. NOTE: The data provided and used by the authors was provided by the Canada Energy Regulator (CER).The  maximum market share vs. payback period data was from R. W. Beck, Inc., “Distributed renewable energy operating impacts and valuation study,” Prepared for: Arizona Public Service, Technical Report, Jan. 2009.

**Directory: \script\batch_inputs**

This directory has four folders: Technical, Market, Grid, and Grid Scaling. Each folder contains the region-specific inputs for each of the modes. The user should fill in one txt file with the required inputs for each region that the user would like to include in the analysis and place the files into the folder labelled the same as the mode used.


## Reprojecting shapefiles
It is important to note that the building footprint files need to have the same coordinate system as the LAS files, which is not always the case by default. This can be done in any GIS software. For example, in QGIS follow the steps below:
1. In order to install the LAS plugin on QGIS on top menu -> plugin ->install->processing->toolbox. There are three options you can use to get the coordinate information needed
   **Option 1**: Using QGIS and importing the LAS/LAZ files
    1. Add the LAS/LAZ file to a project
    2. Right click layer and open properties
    3. Under tab for information, the coordinate system will be under the section for "Coordinate Reference System (CRS)"
   **Option 2**: Using las info tool in QGIS
    1. Now that you have access to LAS tool, you can go to: LASTools ->file-checking quality->las info (can also be done with the lidar_info function from lidar_functions.py in the tools subdirectory)
    2. You can see the output as a text file by defining a directory name in .asci format and save the output there. All information related to the LiDAR file is shown in this text file including the projection system info. Example: EPSG:2950 - NAD83(CSRS) / MTM zone 8 
   **Option 3**: use lidar_functions.py file to create htmls with the data in them
2. By having this information now we can select our footprint file-> right click -> Export -> Save Vector Layer as the same CRS system that we have for Lidar data.


## Output file format

### Technical Mode Outputs
Coef_region_name.xlsx contains the coefficients used in the market and grid modes of this code. This output gives the coefficients for bins representing all rooftop segments with an annual plane-of-array insolation (including shading) greater than or equal to a given percentage of the maximum annual solar resource. For example, there are bins 0 through 9, bin zero corresponds to the surfaces with annual plane-of-array insolation  greater than or equal to 0% of the maximum annual solar resource, bin 3 is greater than or equal to 30% of the maximum annual solar resource.


### Grid and Market Mode Outputs
All outputs in the output_region_name.xlsx are listed by year within the brackets. I.e. the first value in the list is for the starting year provided and the last value for the ending year also provided as an input. 

## Authors
Erin Gaucher-Loksts: (erin.gaucher-loksts@nrcan-rncan.gc.ca)

Sophie Pelland: (sophie.pelland@nrcan-rncan.gc.ca)

The work built on code developed by Negar Salimzadeh (negar_dooman@yahoo.com) under the same project.
