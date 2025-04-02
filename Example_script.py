import time
import glob
from tools import spatial_toolset
import location
from tools import file_handle
import POA
import TimeInDaylight
import os
from run_methods import annual_analysis, rep_analysis, print_results, write_output_file


if __name__=="__main__":
    st=time.time()

    ####################################################
    #Provide user input here
    ####################################################
    city='Calgary' #city name with the first letter in each word capitalized
    file_location=r'C:\Users\Username\Documents' #desired location for saving output data
    lidar_thin=False #set to True if you want to thin the lidar point cloud density, NOTE it will be generated into a seperate folder
    shading_granularity='hourly' #This variable determines whether the output of the shading analysis is saved for each hour of the year (hourly), for each hour of a set of representative days (representative), or as an average over all hours of the year (annual)

    bldg_footprint=r'\building_footprint_file.shp' #location and name of the file
    lidar= r'\LAS files' # location of the lidar files in file format LAS
    weather_file=file_location+r"\weather_file.csv" #name and location of the weather file (from NSRDB in csv format or CWEC for above 60° inepw format)
    
    file_classifier='calgary' # name of the the city with underscores

    #Variable for region specific inputs
    latitude=64.3176
    longitude=-96.0220
    UTC_offset="-06:00"
    altitude=18

    #PV specifications
    performance_ratio=0.75
    module_efficiency=0.225

    ####################################################
    #output/input file locations
    #user can change to the desired location of the outputs/inputs below, if needed
    mosaic=file_location+r'\mosaic_'+file_classifier+'.tif' #file name location of the output mosaic file
    raster_file=file_location+'\\'+file_classifier+'_rooftop_Raster.tif' #file name location of the output rasterized shapefile
    shapefile=file_location+'\\'+file_classifier+'_rooftop.shp' #file name location of the output shapefile from the segmentation

    ####################################################
    region = location.location(city,file_location,bldg_footprint,lidar,mosaic,raster_file,shapefile,
                               weather_file,latitude,longitude,UTC_offset,altitude,file_classifier)
    resolution=1
    if lidar_thin:
        resolution_thin=1/5
        region.run_lidar_thin(resolution_thin)
    
    file_save=file_handle()
    #If the files don't already exist for the DSM files (run_lidar), combining into a mosaic (run_mosaic), and creating the segmentation files (run_seg)
    if len(glob.glob(region.lidar+"/*.tif"))==0:
        print("Creating DSM files...")
        region.run_lidar(resolution)
        print("Created all DSM files\n")
    if not(os.path.isfile(region.mosaic)):
        print("Starting mosaic...")
        region.run_mosaic()
        print("Created mosaic\n")
    if not(os.path.isfile(region.shapefile)):
        print("Starting segmentation...")
        region.run_seg()
        spatial=spatial_toolset()
        spatial.rasterize_polygon(region.mosaic,region.shapefile,region.raster_file,resolution)
        print("Finished segmentation\n")

    if shading_granularity=='annual':
        data=annual_analysis(region,file_location,performance_ratio,module_efficiency)
        
    elif shading_granularity=='representative':
        rep_days=4 #options available: 4 or 12
        data=rep_analysis(rep_days,region,file_location,performance_ratio,module_efficiency)
    elif shading_granularity=='hourly':
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
        
        technical_potential=POA.calculate_technical_potential(TID,region,performance_ratio,module_efficiency)
        data=technical_potential.hourly()
        # if len(region.elec_cost)==30:
        #     market_potential=POA.calculate_market_potential(technical_potential)
        #     market_potential.calculate_market_bin(data[0])
    else: 
        raise Exception("Option not available to run, please input either 'annual', 'hourly', or 'representative'")
    print_results(data,region) 
    write_output_file(data,file_location,region)
    et =time.time()
    elapsed_time=round((et-st)/60,2)
    print("Run time: ",elapsed_time)