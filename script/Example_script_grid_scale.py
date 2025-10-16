import time
import start_analysis
import hosting_capacity_variables
import os

if __name__=="__main__":
    st=time.time()
    BASE_DIR=os.path.dirname(os.path.abspath(__file__))
    os.chdir(BASE_DIR)
    ####################################################
    #Provide user input here
    ####################################################
    mode='grid' #choose what model to use, use 
                #'Technical' for a more detailed analysis by region, 
                #'Market' to calculate the the potential by region (rule-of-thumb and uses inputs derived from the 'Technical' model),
                #'grid' to calculate provincial values with a consideration for the hosting capacity (uses shading data from the detailed analysis)
    
    scaling_option=True #set to True if coefficients should be used to calculate the technical potential instead of the results from the inputted region 
                        #  i.e. if scaling up the results from the region used with lidar data to calculate a larger area
                        # Example: scaling up from the shaded POA calculated for Toronto,CA to calculate the province-wide results for Ontario
    shading_granularity='hourly' #options are hourly, or representative

    region_names=['Example1_scale','Example2_scale'] #should match the files names in the \batch_inputs\Grid_scale folder
    # region_names=['Example1_scale'] #should match the files names in the \batch_inputs\Grid_scale folder
    starting_year=2022 
    ending_year=2050
    cap_coefficient_shade=[0.811057181818182,0.810270545454545,0.806866454545455,0.795339909090909,
                                0.766200545454546,0.704058090909091,0.585788818181818,0.444060636363636,
                                0.280134272727273,0.0521188181818182] # Canada average by resource bin
    elec_coefficient_shade=[0.696808455,0.697416909,0.699658909,0.706008364,0.719245636,0.742224909,
                                    0.779868909,0.821071909,0.861555455,0.923374000]# Canada average by resource bin 
    
    file_location=r'C:\Users\user_name\Documents' #this is a pre-existing folder where outputs will be stored and read from, including shading data, mosaic files, segmentation file, and the rasterized segmentation file and output files (output data) as excel files with structure output_region_name.xlsx (same as the market mode) 

    u_c=20 #PVsyst Fayman temperature coefficient constant
    u_v=0 #PVsyst Fayman temperature coefficient multiplying wind speed
    lifetime_years=30
    dc_to_ac_capacity_ratio = 1.25 #ratio of the total DC power capacity of the solar panels to the total AC power capacity of the inverters
    inverter_efficiency_nominal = 0.99 #efficiency rating when operating at its maximum capacity or 100% load
    hosting_limit=0.67 #limit of the hourly demand to compare to the generation to calculate the hosting capacity. Example: the generation should never exceed 67% of the demand on an hourly basis.

    #parameters for the Bass Diffusion model
    p_range=[10**(-6)]
    q_range=[0.1,0.3,0.5,0.7]

    ####################################################
    hourly_demand=[]
    annual_demand=[]
    current_directory=os.getcwd()
    for region in region_names:
        hourly_demand.append(os.path.join(BASE_DIR,"electricity_demand","Hourly", region+'.csv'))
        annual_demand.append(os.path.join(BASE_DIR,"electricity_demand", region+'.csv'))
        
    resolution=1
    hosting_capacity=hosting_capacity_variables.hosting_capacity(inverter_efficiency_nominal,dc_to_ac_capacity_ratio,lifetime_years,
                                                    u_v,u_c,hosting_limit)
    if len(region_names)>1:
        start_analysis.calculate_all_regions_grid(file_location,resolution,mode,p_range,q_range,region_names,hosting_capacity,hourly_demand,annual_demand,starting_year,ending_year,scaling_option,shading_granularity,cap_coefficient_shade,elec_coefficient_shade)
    else:
        start_analysis.calculate_one_region_grid(region_names[0],file_location,resolution,hosting_capacity,mode,p_range,q_range,hourly_demand[0],annual_demand[0],starting_year,ending_year,scaling_option,shading_granularity,cap_coefficient_shade,elec_coefficient_shade)
    
    et =time.time()
    elapsed_time=round((et-st)/60,2)
    print("Run time in minutes: ",elapsed_time)

    
    



    
    