from pandas import read_excel
import glob

class max_market_share:
    """
    Maximum market share curves. from the dGen report and Easan Drury, Paul Denholm and Robert Margolis (2010) 'Modeling the U.S. Rooftop Photovoltaics Market'

    """
    def __init__(self)->None:
        self.df_market_res=[]
        self.df_market_com=[]
        self.file_names=[]
        self.get_files()
    
    def extract_data(self,file_location:str)->None:
        """
        This function extracts data from an input file from 'Maximum_market_share_data' folder for the residential and commerical data
        
        Parameters
        -------
        file_location: str
            location of the file to import
        """
        df_market_res=read_excel(file_location,sheet_name='Residential')
        df_market_com=read_excel(file_location,sheet_name='Commercial')
        df_market_res.drop("Unnamed: 0",inplace=True,axis=1)
        df_market_com.drop("Unnamed: 0",inplace=True,axis=1)
        return df_market_res,df_market_com

    def get_files(self)->None:
        """
        This function extracts data from all files in the 'Maximum_market_share_data' folder for the residential and commerical data
        """
        for file in glob.glob('scenarios/Maximum_market_share_data/'+'*.xlsx',recursive=True):
            df_market_res,df_market_com=self.extract_data(file)
            self.df_market_res.append(df_market_res)
            self.df_market_com.append(df_market_com)
            self.file_names.append(file.split('/')[-1].split('\\')[1].split('.xlsx')[0])
