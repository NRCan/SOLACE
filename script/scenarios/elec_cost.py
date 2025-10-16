from pandas import read_excel
import glob

class elec_cost:
    def __init__(self)->None:
        self.df_elec_res=[]
        self.df_elec_com=[]
        self.file_names=[]
        self.get_files()
    
    def extract_data(self,file_location:str)->None:
        """
        This function extracts data from an input file from 'elec_cost_data' folder for the residential and commerical data
        
        Parameters
        -------
        file_location: str
            location of the file to import
        """
        df_elec_res=read_excel(file_location,sheet_name='Residential')
        df_elec_com=read_excel(file_location,sheet_name='Commercial')
        df_elec_res.drop("Unnamed: 0",inplace=True,axis=1)
        df_elec_com.drop("Unnamed: 0",inplace=True,axis=1)
        return df_elec_res,df_elec_com

    def get_files(self)->None:
        """
        This function extracts data from all files in the 'elec_cost_data' folder for the residential and commerical data
        """
        for file in glob.glob('scenarios/elec_cost_data/'+'*.xlsx',recursive=True):
            df_elec_res,df_elec_com=self.extract_data(file)
            self.df_elec_res.append(df_elec_res)
            self.df_elec_com.append(df_elec_com)
            self.file_names.append(file.split('/')[-1].split('\\')[1].split('.xlsx')[0])
        
        
