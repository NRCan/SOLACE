from pandas import read_excel
import glob

class Building_stock:
    def __init__(self)->None:
        self.df_bldg_res=[]
        self.df_bldg_com=[]
        self.file_names=[]
        self.get_files()
    
    def extract_data(self,file_location:str)->None:
        """
        This function extracts data from an input file from 'building_growth_data' folder for the residential and commerical data

        Parameters
        -------
        file_location: str
            location of the file to import
        """
        df_bldg_res=read_excel(file_location,sheet_name='Residential')
        df_bldg_com=read_excel(file_location,sheet_name='Commercial')
        df_bldg_res.drop("Unnamed: 0",inplace=True,axis=1)
        df_bldg_com.drop("Unnamed: 0",inplace=True,axis=1)
        return df_bldg_res,df_bldg_com

    def get_files(self)->None:
        """
        This function extracts data from all files in the 'building_growth_data' folder for the residential and commerical data
        """
        for file in glob.glob('scenarios/building_growth_data/'+'*.xlsx',recursive=True):
            df_bldg_res,df_bldg_com=self.extract_data(file)
            self.df_bldg_res.append(df_bldg_res)
            self.df_bldg_com.append(df_bldg_com)
            self.file_names.append(file.split('/')[-1].split('\\')[1].split('.xlsx')[0])
        