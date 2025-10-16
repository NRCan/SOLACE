from pandas import DataFrame, read_excel,Series
import glob
import numpy as np
import os
import plotly.graph_objects as go
import plotly.io as pio
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import json
from math import ceil
import pint
pio.templates.default = "simple_white"
ureg = pint.UnitRegistry()
ureg.formatter.default_format = "~P"

class data:
    def __init__(self,file_location:str,mode_operational:str):
        self.file_location = file_location
        self.demand_final_year=[]
        self.tech_demand_final_year,self.percent_all_final_year,self.grid_demand_final_year=[],[],[]
        self.tech_capacity_per_region,self.installed_capacity_per_region,self.grid_capacity_per_region=[],[],[]
        self.total_demand=[]
        self.mode_operational=mode_operational

    def extract_data_one(self,file:str, ind:int=0)->None:
        """
        This function extracts the data from the output file

        Parameters
        -------
        file :str
            location of the output file desired
        ind :int
            optional input, used only with the extract_data_all function    
        """
        temp=file.split('\\')[-1].split('.')[0].replace('output_'+self.mode_operational+'_', "")
        temp=" ".join(temp.split('_'))
        self.region_name=temp.title()
        df_region=read_excel(file,'Capacity')
        electricity=read_excel(file,'Electricity')

        tech_scen,cap_scen,grid_scen=[],[],[]
        tech_scen_final_year,cap_scen_final_year,grid_scen_final_year=[],[],[]
        tech_elec_scen,elec_scen,grid_elec_scen=[],[],[]
        tech_demand_scen_final_year,total_demand_perc_final_year_scen,grid_total_demand_final_year_scen=[],[],[]
        total_demand_final_year=[]
        total_demand_scen=[]
        tech_demand_perc_scen,total_demand_perc_scen,grid_demand_perc_scen=[],[],[]

        for i in range(0,len(electricity['Total demand by year (MWh)'])):
            cap_scen.append(json.loads(df_region['Installed capacity by year (GW)'][i]))
            cap_scen_final_year.append(cap_scen[-1][-1])
            tech_scen.append(json.loads(df_region['Technical potential capacity by year (GW)'][i]))
            tech_scen_final_year.append(tech_scen[-1][-1])
            grid_scen.append(json.loads(df_region['Installed capacity - grid by year (GW)'][i]))
            grid_scen_final_year.append(grid_scen[-1][-1])
            elec_scen.append(json.loads(electricity['Annual electricity output (TWh) from installed capacity by year'][i]))
            tech_elec_scen.append(json.loads(electricity['Technical potential - Annual electricity output by year (TWh)'][i]))
            grid_elec_scen.append(json.loads(electricity['Annual electricity output (TWh) from installed capacity with grid constraints by year'][i]))
            tech_demand_perc_scen.append(json.loads(electricity['Technical potential as a fraction of total demand by year (-)'][i]))
            tech_demand_scen_final_year.append(tech_demand_perc_scen[-1][-1])
            total_demand_perc_scen.append(json.loads(electricity['Annual output as a fraction of total demand by year (-)'][i]))
            total_demand_perc_final_year_scen.append(total_demand_perc_scen[-1][-1])
            grid_demand_perc_scen.append(json.loads(electricity['Annual output as a fraction of total demand (-) with grid constraints by year'][i]))
            grid_total_demand_final_year_scen.append(grid_demand_perc_scen[-1][-1])
            total_demand_scen.append(json.loads(electricity['Total demand by year (MWh)'][i]))
            total_demand_final_year.append(total_demand_scen[-1][-1])

        self.percent_all_final_year.append(Series(total_demand_perc_final_year_scen).rename(self.region_name))
        self.demand_final_year.append(Series(total_demand_final_year).rename(self.region_name))
        self.tech_demand_final_year.append(Series(tech_demand_scen_final_year).rename(self.region_name))   
        self.grid_demand_final_year.append(Series(grid_total_demand_final_year_scen).rename(self.region_name)) 
        self.installed_capacity_per_region.append(Series(cap_scen_final_year).rename(self.region_name))   
        self.tech_capacity_per_region.append(Series(tech_scen_final_year).rename(self.region_name)) 
        self.grid_capacity_per_region.append(Series(grid_scen_final_year).rename(self.region_name)) 
        if ind==0:
            self.installed_capacity_all=DataFrame(cap_scen)
            self.tech_all=DataFrame(tech_scen)
            self.grid_cap_all=DataFrame(grid_scen)
            self.electricity_gen_all=DataFrame(elec_scen) 
            self.tech_electricity_gen_all=DataFrame(tech_elec_scen) 
            self.grid_electricity_gen_all=DataFrame(elec_scen) 
            self.total_demand=DataFrame(total_demand_scen) 
            self.percent_all=DataFrame(total_demand_perc_scen)*100
            self.grid_percent_all=DataFrame(grid_demand_perc_scen)*100
            self.tech_percent_all=DataFrame(tech_demand_perc_scen)*100
        else:
            self.installed_capacity_all=self.installed_capacity_all+DataFrame(cap_scen)
            self.tech_all=self.tech_all+DataFrame(tech_scen)
            self.grid_cap_all=self.grid_cap_all+DataFrame(grid_scen)
            self.electricity_gen_all=self.electricity_gen_all+DataFrame(elec_scen) 
            self.tech_electricity_gen_all=self.tech_electricity_gen_all+DataFrame(tech_elec_scen) 
            self.grid_electricity_gen_all=self.grid_electricity_gen_all+DataFrame(elec_scen) 
            self.total_demand=self.total_demand+DataFrame(total_demand_scen) 

    def clean_data(self)->None:    
        """
        This function cleans the extracted data and puts everything into dataframes
   
        """
        self.percent_all_final_year,self.demand_final_year=DataFrame(self.percent_all_final_year),DataFrame(self.demand_final_year)
        self.installed_capacity_per_region=DataFrame(self.installed_capacity_per_region).transpose()
        self.tech_capacity_per_region=DataFrame(self.tech_capacity_per_region).transpose()
        self.grid_capacity_per_region=DataFrame(self.grid_capacity_per_region).transpose()
        self.tech_demand_final_year=DataFrame(self.tech_demand_final_year).transpose()
        self.grid_demand_final_year=DataFrame(self.grid_demand_final_year).transpose()
        self.percent_all_final_year=self.percent_all_final_year.transpose()
        self.demand_final_year=self.demand_final_year.transpose()
        self.percent_final_year_Canada=self.electricity_gen_all/self.total_demand*1000*1000
        self.grid_percent_final_year_Canada=self.grid_electricity_gen_all/self.total_demand*1000*1000
        self.tech_percent_final_year_Canada=self.tech_electricity_gen_all/self.total_demand*1000*1000
        self.cap_norm=self.installed_capacity_per_region/self.tech_capacity_per_region
    
    def extract_data_all(self)->None:
        """
        This function extracts the data from the output files, calling on extract_data_one 
        """
        ind=0
        for file in glob.glob('output_'+self.mode_operational+'_'+'*.xlsx',recursive=True):
            self.extract_data_one(file,ind)
            ind=ind+1

def auto_scale_series(values, unit="GW"):
    """Scale a list/Series/DataFrame column to the best SI prefix."""
    # attach units
    q = [v * ureg(unit) for v in values]
    # pick compact form for the largest value
    largest = max(q, key=lambda x: abs(x.magnitude))
    target_unit = str(largest.to_compact().units)
    
    # convert everything to that unit
    q_scaled = [v.to(target_unit) for v in q]
    unit_label = f"{q_scaled[0].units:~}"
    return Series([v.magnitude for v in q_scaled]), unit_label

def distribution_plot(data:DataFrame,mode:str,file_location:str,ending_year:int)->None:
    """
    This function creates a distribution box plot with all the regions in the analysis

    Parameters
    -------
    df:DataFrame
        data outputted by the simulation
    mode :str
        what output is to be displayed, capacity, annual percent of building demand to generation or annual percent of total demand to generation
    file_location :int
        location to place the output file  
    ending_year:int
        year that the analysis ends
     """
    
    if mode=='capacity':
        df_market=DataFrame(data.installed_capacity_per_region)
        df_tech=DataFrame(data.tech_capacity_per_region)
        df_grid=DataFrame(data.grid_capacity_per_region)
        title='Installed capacity in '+str(ending_year)+' (GW)'
    elif mode=='percent_total_demand':
        df_market=DataFrame(data.percent_all_final_year)*100
        df_tech=DataFrame(data.tech_demand_final_year)*100
        df_grid=DataFrame(data.grid_demand_final_year)*100
        title='Rooftop PV generation as a percentage <br>of total demand in '+str(ending_year)+' (%)'
    elif mode=='capacity_norm':
        df_market=DataFrame(data.cap_norm)*100
        title='Installed capacity as a percentage of <br>the technical potential in '+str(ending_year)+' (%)'
    ind=0
    mode_name=['Technical','Market','Grid']
    if mode=='capacity_norm':
        graphs=[df_market]
        mode_name=['Market']
    elif data.mode_operational=='grid':
        graphs=[df_tech,df_market,df_grid]
    
    else:
        graphs=[df_tech,df_market]
    
    for df in graphs:
        fig=go.Figure()
        for name in df.columns:
            fig.add_trace(go.Box(y=df[name].to_list(),name=name))

        fig.update_layout(plot_bgcolor='rgba(0, 0, 0, 0)',
                            paper_bgcolor='rgba(0, 0, 0, 0)',
                    yaxis_title=title,
                    showlegend=False,
                    font=dict(size=18),
                    # yaxis_range=[0, ceil(df.max().max()*1.1)],
                    title_text='Mode: '+mode_name[ind])
        filename=file_location+r'\box_plot_'+mode_name[ind]+'_'+mode+'_final_year.html'
        fig.write_html(file=filename)
        ind=ind+1

def histogram(df:DataFrame,mode:str,file_location:str,region_name:str,ending_year:int)->None:
    """
    This function creates a histogram of the resulting capacity and percent total of the demand.

    Parameters
    -------
    file_location: str
        file location of the files
    df:DataFrame
        dataframe containing only the capacity or percent toal demand for each scenario
    mode:str
        two modes for 'capacity' or 'percent_total_demand'
    region_name:str
        name of the region    
    ending_year:int
        year that the analysis ends
    """
    if mode=='capacity':
        title='Installed capacity in '+str(ending_year)+' (GW)'
    elif mode=='percent_total_demand':
        title='Rooftop PV generation as a percentage of total demand in the '+str(ending_year)+' (%)'

    fig=go.Figure(data=[go.Histogram(x=df.to_list(),nbinsx=20)])
    fig.add_vline(x=df.median(),line_dash ='dash', line_color='firebrick')
    fig.update_layout(plot_bgcolor='rgba(0, 0, 0, 0)',
                        paper_bgcolor='rgba(0, 0, 0, 0)',
                xaxis_title=title,
                yaxis_title='Number of scenarios',
                showlegend=False,
                font=dict(size=18))
    filename=file_location+r'\Histogram_'+region_name+'_'+mode+'_end_year.html'
    fig.write_html(file=filename)

def violin_plot(file_location:str,data:DataFrame,region_name:str,ending_year:int,mode:str)->None:
    """
    This function creates a violin of the percent total of the demand.

    Parameters
    -------
    file_location: str
        file location of the files
    data:DataFrame
        dataframe containing the data for each scenario
    region_name:str
        name of the region
    ending_year:int
        year that the analysis ends
    mode :str
        what output is to be displayed, capacity, annual percent of building demand to generation or annual percent of total demand to generation
    
    """
    if mode=='capacity':
        df_market=data.installed_capacity_per_region
        df_tech=data.tech_capacity_per_region
        df_grid=data.grid_capacity_per_region
        title='Installed capacity in '+str(ending_year)+' (GW)'
    elif mode=='percent_total_demand':
        df_market=data.percent_all_final_year*100
        df_tech=data.tech_demand_final_year*100
        df_grid=data.grid_demand_final_year*100
        title='Rooftop PV generation as a percentage <br>of total demand in '+str(ending_year)+' (%)'
    ind=0
    mode_name=['Technical','Market','Grid']
    if data.mode_operational=='grid':
        graphs=[df_tech,df_market,df_grid]
    else:
        graphs=[df_tech,df_market]
    fig = go.Figure()
    for df in graphs:
        fig.add_trace(go.Violin(x=np.repeat([mode_name[ind]],len(df.iloc[:,0])),y=df.iloc[:,0],box_visible=True,meanline_visible=True,opacity=0.6))
        fig.update_layout(
            yaxis_title=title,
            showlegend=False
            )
        ind=ind+1
    filename=file_location+r'\violin_'+region_name+'_'+'_'+mode+'_final_year.html'
    fig.write_html(file=filename)   
                            
def create_graphs_region(data:data,starting_year:int,ending_year:int)->None:
    """
    This function creates the graphs based on the inputted data for a given region.

    Parameters
    -------
    data:data
        object 'data' containing all the data for the different scenarios
    """
    val, unit = auto_scale_series(data.installed_capacity_per_region.iloc[:,0], "GW")

    print('Min installed capacity in '+str(ending_year)+' for '+data.region_name+' ('+unit+'): ',round(val.min(),2) )
    print('Max installed capacity in '+str(ending_year)+' for '+data.region_name+' ('+unit+'): ',round(val.max(),2) )
    print('Median installed capacity in '+str(ending_year)+' for '+data.region_name+' ('+unit+'): ',round(val.median(),2) )

    violin_plot(data.file_location,data,data.region_name,ending_year,'capacity')
    violin_plot(data.file_location,data,data.region_name,ending_year,'percent_total_demand')
    

    x=list(range(starting_year,ending_year+1))
    y1_min=data.tech_all.min()
    y1_max=data.tech_all.max()
    y1=data.tech_all.median()
    line2=[x,list(y1),list(y1_max),list(y1_min)]

    y1_min=data.grid_cap_all.min()
    y1_max=data.grid_cap_all.max()
    y1=data.grid_cap_all.median()
    line3=[x,list(y1),list(y1_max),list(y1_min)]

    y1_min=data.installed_capacity_all.min()
    y1_max=data.installed_capacity_all.max()
    y1=data.installed_capacity_all.median()
    line1=[x,list(y1),list(y1_max),list(y1_min)]
    line_filled(line1,data.file_location,data.region_name,'capacity',ending_year,line2,line3,data.mode_operational)

    y1_min=data.percent_all.min()
    y1_max=data.percent_all.max()
    y1=data.percent_all.median()
    line1=[x,list(y1),list(y1_max),list(y1_min)]

    y1_min=data.grid_percent_all.min()
    y1_max=data.grid_percent_all.max()
    y1=data.grid_percent_all.median()
    line3=[x,list(y1),list(y1_max),list(y1_min)]

    y1_min=data.tech_percent_all.min()
    y1_max=data.tech_percent_all.max()
    y1=data.tech_percent_all.median()
    line2=[x,list(y1),list(y1_max),list(y1_min)]

    line_filled(line1,data.file_location,data.region_name,'percent_total_demand',ending_year,line2,line3,data.mode_operational)

    val, unit = auto_scale_series(data.installed_capacity_all.iloc[-1], "GW")
    Capacity=np.array(val.transpose().to_list())

    distplot(Capacity,data,ending_year,unit)

def create_graphs(data:data,ending_year:int)->None:
    """
    This function creates the graphs based on the inputted data.

    Parameters
    -------
    data:data
        object 'data' containing all the data for the different scenarios
    """
    
    distribution_plot(data,'capacity',data.file_location,ending_year)
    distribution_plot(data,'percent_total_demand',data.file_location,ending_year)

    
def distplot(Capacity:DataFrame,data,ending_year:int,unit:str)->None:
    """
    This function creates a KDE probability density graph
    
    Parameters
    -------

    Capacity:DataFrame
        dataframe containing only the capacity for each scenario

    """
    kde = gaussian_kde(Capacity,bw_method='scott')
    x_grid = np.linspace(Capacity.min(), Capacity.max(), 500)
    f0 = kde(x_grid)

    plt.figure(figsize=(6, 4))

    # Plot KDE with filled area
    plt.fill_between(x_grid, f0, color=(0.9, 0.9, 1.0))
    plt.plot(x_grid, f0, color='b')
    plt.ylim(bottom=0)

    plt.axvline(x=np.median(Capacity), linestyle='--', color='black', label='Median')
    # Labels
    plt.xlabel('Installed capacity in '+str(ending_year)+' ('+unit+')')
    plt.ylabel('Density')
    plt.title("Mode: Market")
    plt.savefig(data.file_location+r'\KDE_final_year_'+data.region_name+'.png') 

def line_filled(line2:list,file_location:str,region_name:str,mode:str,ending_year:int,line1:list,line3:list,mode_operational:str):
    """
    This function creates a line plot with the median, min and max of the region
    
    Parameters
    -------
    file_location: str
        file location of the files
    line1:list
        list of the attributes for making the line plot
    region_name:str
        name of the region
    """
    if mode=='capacity':
        title='Installed capacity in '+str(ending_year)+' (GW)'
    elif mode=='percent_total_demand':
        title='Rooftop PV generation as a percentage of <br>total demand in '+str(ending_year)+' (%)'
    x1=line1[0]
    x1_rev=x1[::-1]
    y1=line1[1]
    y1_max=line1[2]
    y1_min=line1[3]
    y1_min=y1_min[::-1]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x1+x1_rev,
        y=y1_max+y1_min,
        fill='toself',
        fillcolor='rgba(0,100,80,0.2)',
        line_color='rgba(255,255,255,0)',
        name='Technical',
        showlegend=False,
    ))

    fig.add_trace(go.Scatter(
        x=x1, y=y1,
        line_color='rgb(0,100,80)',
        name='Technical',
    ))

    x2=line2[0]
    x2_rev=x2[::-1]
    y2=line2[1]
    y2_max=line2[2]
    y2_min=line2[3]
    y2_min=y2_min[::-1]
    
    fig.add_trace(go.Scatter(
        x=x2+x2_rev,
        y=y2_max+y2_min,
        fill='toself',
        fillcolor='rgba(0,176,246,0.2)',
        line_color='rgba(255,255,255,0)',
        name='Market',
        showlegend=False,
    ))
    
    
    fig.add_trace(go.Scatter(
        x=x2, y=y2,
        line_color='rgb(0,176,246)',
        name='Market',
    ))
    if mode_operational=='grid':
        x3=line3[0]
        x3_rev=x3[::-1]
        y3=line3[1]
        y3_max=line3[2]
        y3_min=line3[3]
        y3_min=y3_min[::-1]
        fig.add_trace(go.Scatter(
            x=x3, y=y3,
            line_color='rgb(231,107,243)',
            name='Grid',
        ))
        fig.add_trace(go.Scatter(
            x=x3+x3_rev,
            y=y3_max+y3_min,
            fill='toself',
            fillcolor='rgba(231,107,243,0.2)',
            line_color='rgba(255,255,255,0)',
            showlegend=False,
            name='Grid',
            ))
    fig.update_traces(mode='lines')
    fig.update_layout(
        xaxis_title='Year',
        yaxis_title=title,
        font=dict(size=18),
        showlegend=True, # Hide legend if not needed
        legend=dict(
            yanchor="top",  # Anchor the legend to its top edge
            y=0.99,         # Position the legend near the top of the plot
            xanchor="left", # Anchor the legend to its right edge
            x=0.01          # Position the legend near the right of the plot
        )
    ) 
    filename=file_location+r'\Filled_line_plot_'+region_name+'_'+mode+'.html'
    fig.write_html(file=filename)

def create_graphs_all(grid_data,ending_year,mode_operational):
    x=list(range(2022,2051))
    y1_min=grid_data.tech_all.min()
    y1_max=grid_data.tech_all.max()
    y1=grid_data.tech_all.median()

    y2_min=grid_data.installed_capacity_all.min()
    y2_max=grid_data.installed_capacity_all.max()
    y2=grid_data.installed_capacity_all.median()

    y3_min=grid_data.grid_cap_all.min()
    y3_max=grid_data.grid_cap_all.max()
    y3=grid_data.grid_cap_all.median()

    line1=[x,list(y1),list(y1_max),list(y1_min)]
    line2=[x,list(y2),list(y2_max),list(y2_min)]
    line3=[x,list(y3),list(y3_max),list(y3_min)]

    line_filled(line2,grid_data.file_location,'Canada','capacity',ending_year,line1,line3,mode_operational)
    Capacity=np.array(grid_data.installed_capacity_all.transpose().iloc[-1].to_list())
    distplot(Capacity,grid_data,ending_year)

    distribution_plot(grid_data,'capacity',grid_data.file_location,ending_year)
    distribution_plot(grid_data,'capacity_norm',grid_data.file_location,ending_year)
    distribution_plot(grid_data,'percent_total_demand',grid_data.file_location,ending_year)

    fig=go.Figure()

    fig.add_trace(go.Violin(x=np.repeat(['Technical'],len(grid_data.tech_percent_final_year_Canada.iloc[:,-1])),y=grid_data.tech_percent_final_year_Canada.iloc[:,-1]*100,box_visible=True,meanline_visible=True,opacity=0.6))
    fig.add_trace(go.Violin(x=np.repeat(['Market'],len(grid_data.percent_final_year_Canada.iloc[:,-1])),y=grid_data.percent_final_year_Canada.iloc[:,-1]*100,box_visible=True,meanline_visible=True,opacity=0.6))
    fig.add_trace(go.Violin(x=np.repeat(['Grid'],len(grid_data.grid_percent_final_year_Canada.iloc[:,-1])),y=grid_data.grid_percent_final_year_Canada.iloc[:,-1]*100,box_visible=True,meanline_visible=True,opacity=0.6))
    fig.update_layout(
        yaxis_title='Rooftop PV generation as a percentage <br>of total demand in '+str(ending_year)+' (%)',
        font=dict(size=18),
        showlegend=False, # Hide legend if not needed
        legend=dict(
            yanchor="top",  # Anchor the legend to its top edge
            y=0.99,         # Position the legend near the top of the plot
            xanchor="right", # Anchor the legend to its right edge
            x=0.99          # Position the legend near the right of the plot
        )
    ) 
    filename=grid_data.file_location+r'\violin_all_'+str(ending_year)+'_report.html'
    fig.write_html(file=filename)

if __name__=="__main__":
    file_location=r'C:\Users\user_name\Documents'
    mode='grid'
    ending_year=2050
    provincial_data=data(file_location,mode)
    os.chdir(file_location)
    provincial_data.extract_data_all()
    provincial_data.clean_data()

    create_graphs_all(provincial_data,ending_year,mode)