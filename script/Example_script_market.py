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
    mode='Market' #choose what model to use, use 
                #'Technical' for a more detailed analysis by region, 
                #'Market' to calculate the the potential by region (rule-of-thumb and uses inputs derived from the 'Technical' model),
                #'grid' to calculate provincial values with a consideration for the hosting capacity (uses shading data from the detailed analysis)
    
    
    ##Inputs for 'Market' mode
    file_location=r'C:\Users\user_name\Documents' #this is a pre-existing folder where outputs will be stored, output files (output data) as excel files with structure output_region_name.xlsx (same as the grid modes)
    p_range=[10**(-6)]
    q_range=[0.1,0.3,0.5,0.7]
    starting_year=2022 
    ending_year=2050

    cap_coefficient_shade=[0.811057181818182,0.810270545454545,0.806866454545455,0.795339909090909,
                                0.766200545454546,0.704058090909091,0.585788818181818,0.444060636363636,
                                0.280134272727273,0.0521188181818182] # Canada average by resource bin
    elec_coefficient_shade=[0.696808455,0.697416909,0.699658909,0.706008364,0.719245636,0.742224909,
                                    0.779868909,0.821071909,0.861555455,0.923374000]# Canada average by resource bin 

    region_names=['Example1','Example2'] #should match the files names in the \batch_inputs\Market folder
    # region_names=['Example1'] #should match the files names in the \batch_inputs\Market folder
    
    
    ##########################################################
    annual_demand=[]
    current_directory=os.getcwd()

    for region in region_names:
        file_path=current_directory+'//electricity_demand//'
        annual_demand.append(file_path+region+'.csv')
    
    if len(region_names)>1:
        start_analysis.market_all(file_location,starting_year,p_range,q_range,mode,region_names,annual_demand,ending_year,cap_coefficient_shade,elec_coefficient_shade)
    else:
        start_analysis.market(file_location,starting_year,p_range,q_range,mode,region_names[0],annual_demand[0],ending_year,cap_coefficient_shade,elec_coefficient_shade)
    

    et =time.time()
    elapsed_time=round((et-st)/60,2)
    print("Run time in minutes: ",elapsed_time)



    
    