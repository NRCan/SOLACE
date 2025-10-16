import time
import start_analysis
import os

if __name__=="__main__":
    st=time.time()
    BASE_DIR=os.path.dirname(os.path.abspath(__file__))
    os.chdir(BASE_DIR)
    ####################################################
    #Provide user input here
    ####################################################
    mode='Technical' #choose what model to use, use 
                #'Technical' for a more detailed analysis by region, 
                #'Market' to calculate the the potential by region (rule-of-thumb and uses inputs derived from the 'Technical' model),
                #'grid' to calculate provincial values with a consideration for the hosting capacity (uses shading data from the detailed analysis)
    
    
    ##Inputs for 'Technical' mode
    region_name=['Example1','Example2'] #should match the files names in the \batch_inputs\Technical folder
    # region_name=['Example1'] #should match the files names in the \batch_inputs\Technical folder
    file_location=r'C:\Users\user_name\Documents' #this is a pre-existing folder where outputs will be stored and read from, including shading data, mosaic files, segmentation file, and the rasterized segmentation file
    shading_granularity='hourly' #options are annual, hourly, or representative
    
    #PV specifications
    performance_ratio=0.75
    module_efficiency=0.225
    resolution=1 # resolution for the DSM files (only used when there are no DSM files already made)

    ####################################################

    start_analysis.run_detailed(file_location,mode,shading_granularity,resolution,region_name,performance_ratio,
                 module_efficiency)

    et =time.time()
    elapsed_time=round((et-st)/60,2)
    print("Run time in minutes: ",elapsed_time)



    
    