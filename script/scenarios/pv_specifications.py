from pandas import read_excel
import glob

class PV_specifications:
    """
    PV performance ratio and efficinecy scenarios. 
    """
    def __init__(self)->None:

        self.df_pv_pr_res=[]
        self.df_pv_pr_com=[]
        self.df_pv_eff=[]
        self.df_pv_deg=[]
        self.df_pv_temp=[]
        self.file_names_PR=[]
        self.file_names_eff=[]
        self.get_files_PR()
        self.get_files_eff()
    
    def extract_data_PR(self,file_location:str)->None:
        """
        This function extracts data from an input file from 'PV_PR_data' folder for the residential and commerical data
        
        Parameters
        -------
        file_location: str
            location of the file to import
        """
        df_pv_res=read_excel(file_location,sheet_name='Residential')
        df_pv_com=read_excel(file_location,sheet_name='Commercial')
        df_pv_deg=read_excel(file_location,sheet_name='Degradation_rate')
        df_pv_res.drop("Unnamed: 0",inplace=True,axis=1)
        df_pv_com.drop("Unnamed: 0",inplace=True,axis=1)
        df_pv_deg.drop("Unnamed: 0",inplace=True,axis=1)
        return df_pv_res,df_pv_com,df_pv_deg

    def get_files_PR(self)->None:
        """
        This function extracts data from all files in the 'PV_PR_data' folder for the residential and commerical data
        """
        for file in glob.glob('scenarios/PV_PR_data/'+'*.xlsx',recursive=True):
            df_pv_res,df_pv_com,df_pv_deg=self.extract_data_PR(file)
            self.df_pv_pr_res.append(df_pv_res)
            self.df_pv_pr_com.append(df_pv_com)
            self.df_pv_deg.append(df_pv_deg)
            self.file_names_PR.append(file.split('/')[-1].split('\\')[1].split('.xlsx')[0])
    
    def get_files_eff(self)->None:
        """
        This function extracts data from all files in the 'PV_efficiency_data' folder for the efficiency and temperature coefficient
        """
        for file in glob.glob('scenarios/PV_efficiency_data/'+'*.xlsx',recursive=True):
            df_pv_eff,df_pv_temp=self.extract_data_eff(file)
            self.df_pv_eff.append(df_pv_eff)
            self.df_pv_temp.append(df_pv_temp)
            self.file_names_eff.append(file.split('/')[-1].split('\\')[1].split('.xlsx')[0])

    def extract_data_eff(self,file_location:str)->None:
        """
        This function extracts data from an input file from 'PV_efficiency_data' folder for 
        
        Parameters
        -------
        file_location: str
            location of the file to import
        """
        df_pv_eff=read_excel(file_location,sheet_name='Efficiency')
        df_pv_temp=read_excel(file_location,sheet_name='Temperature coefficient')
        df_pv_eff.drop("Unnamed: 0",inplace=True,axis=1)
        df_pv_temp.drop("Unnamed: 0",inplace=True,axis=1)
        return df_pv_eff,df_pv_temp