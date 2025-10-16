
import glob
import os
import pandas as pd

os.chdir(r'C:\Users\user_name\Documents\electricity_demand\Hourly')
for file in glob.glob('*.csv',recursive=True):
    df=pd.read_csv(file)
    filename=file.split('_')[0]+'.csv'
    df.drop('Scenario',axis=1, inplace=True)
    df.drop('region',axis=1, inplace=True)
    df.drop('LocalHour',axis=1, inplace=True)
    new_df=df.groupby('Year').sum()
    
    new_df.to_csv(filename)