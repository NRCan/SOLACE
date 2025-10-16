# -*- coding: utf-8 -*-
"""
Created on Thur June  27  2024

@author: egaucher
"""

import numpy as np
import TimeInDaylight
import os
import glob
from tools import spatial_toolset
import region_data
from pandas import DataFrame, Series,ExcelWriter,read_csv,concat
import os
from tools import file_handle
from scipy.optimize import fsolve
import pvlib
import warnings
import calculate_technical_potential 
import hosting_capacity_variables
import make_graphs

warnings.filterwarnings('ignore', 'The iteration is not making good progress')

class DeployedCapacity:

    def bins(self,Total_PV_capacity_GW: float|list,bin: list[float],daily_insolation: float,coefficients: list[float],PV_PR:float)-> DataFrame:
        """
        
        This function calculates the capacity and solar yield by solar resource bin.

        Parameters
        ----------
        Total_PV_capacity_GW : float|list
            capacity of PV (technical potential)
        bin : list
            list of the bins to divide the capacity into
        daily_insolation: float
            population weighted mean daily insolation
        coefficients: list
            the capaicty shaded coefficients
        PV_PR: list
            Perfomance ratio of the module
        
        Returns
        ----------
        DataFrame
            capacity and solar yield by solar resource bin

        """
        if coefficients!=[]:
            coefficients=coefficients.copy()
            coefficients.append(0)
            
            Technical_potential_above_threshold=[]
            for i in range(0,len(bin)):
                if i==0:
                    Technical_potential_above_threshold.append(Total_PV_capacity_GW)
                elif i>=len(coefficients):
                    Technical_potential_above_threshold.append(0)
                else:
                    Technical_potential_above_threshold.append(coefficients[i]/coefficients[0]*Total_PV_capacity_GW)
            ind=0
            Technical_potential=[]
            solar_yield=[]
            mid_bin=[0.0700731, 0.1659991, 0.2615420, 0.3579429, 0.4588964, 0.5557738, 0.6507723, 0.7518895, 0.8474252, 0.9233740,1.0]

            for i in bin:
                if ind>=len(bin)-1:
                    Technical_potential.append(0)
                elif ind==len(bin)-2:
                    Technical_potential.append(Technical_potential_above_threshold[ind])
                else:
                    Technical_potential.append(Technical_potential_above_threshold[ind]-Technical_potential_above_threshold[ind+1])
                
                solar_yield.append(daily_insolation*mid_bin[ind]*365*PV_PR)
                ind=ind+1
            data={'PV_capacity_GW': Technical_potential,'PV_kWh_kW': solar_yield}
        else:
            solar_yield=[]
            mid_bin=[0.0700731, 0.1659991, 0.2615420, 0.3579429, 0.4588964, 0.5557738, 0.6507723, 0.7518895, 0.8474252, 0.9233740,1.0]
            ind=0
            for i in bin:
                solar_yield.append(daily_insolation*mid_bin[ind]*365*PV_PR)
                ind=ind+1
            data={'PV_capacity_GW': Total_PV_capacity_GW,'PV_kWh_kW': solar_yield}
        technical_potential=DataFrame(data)
        return technical_potential

    def calculate_payback_bin(self,daily_insolation: float,Total_PV_capacity_GW: Series,elec_cost: Series,
                              PV_cost_years: list[float],PR:list[float],cap_coefficient_shade:list[float]=[]) -> tuple[DataFrame,list[Series],Series]:
        """
        
        This function calculates the capacity, solar yield and payback by solar resource bin.

        Parameters
        ----------
        Total_PV_capacity_GW : Series
            capacity of PV (technical potential)
        elec_cost : Series
            list of the electricity costs per year
        daily_insolation: float
            population weighted mean daily insolation
        PV_cost_years: list
            PV module cost by year
        PR: list
            Perfomance ratio of the module per year
        cap_coefficient_shade: list
            the capaicty shaded coefficients by solar resource bin
        
        Returns
        ----------
        list
            capacity and solar yield by solar resource bin and the payback by bin

        """
        bin=[round(i/10.0,2) for i in range(0,11)]
        potential_by_threshold=[]
        solar_yield_bins=[]
        ind=0
        for i in range(0,len(Total_PV_capacity_GW)):
            potential_bin=self.bins(Total_PV_capacity_GW.iloc[i],bin,daily_insolation,cap_coefficient_shade,PR[ind])
            potential_by_threshold.append(potential_bin['PV_capacity_GW'])
            solar_yield_bins.append(potential_bin['PV_kWh_kW'])
            ind=ind+1
        potential_by_threshold=DataFrame(potential_by_threshold)
        potential_by_threshold.reset_index(drop=True,inplace=True)
        payback_bins=self.payback_bin(elec_cost,solar_yield_bins,PV_cost_years)
        return potential_by_threshold,payback_bins,potential_bin['PV_kWh_kW']
    
    def payback_bin(self,elec_cost: Series,solar_yield_bins: list[Series],PV_cost_years: list[float]) -> list[Series]:
        """
        
        This function calculates the payback by solar resource bin.

        Parameters
        ----------
        elec_cost : Series
            list of the electricity costs per year
        PV_cost_years: list
            PV module cost by year
        solar_yield_bins: list
            list of series that has the solar yield by year then by solar resource bin
        
        Returns
        ----------
        list
            payback by solar resource bin

        """
        payback=[]
        elec_cost.reset_index(drop=True,inplace=True)
        for i in range(0,len(PV_cost_years)):
            payback.append((PV_cost_years[i]*1000)/(solar_yield_bins[i]*elec_cost[i]))
        return payback

    def t_equ(self,MMS1:float,MMS2:float,p:float,q:float,t:float)->tuple[float,float]:
        """
        
        This function calculates the equivalent time. 

        Parameters
        ----------
        MMS1 : float
            maximum market share from the previous year
        MMS2: float
            maximum market share from the this year
        p: float
            bass difussion model parameter 
        q: float
            bass difussion model parameter 
        t: float
            time from the previous year
        
        Returns
        ----------
        tequ
            the calculated equivalent time
        MMS2
            maximum market share from the this year
        """
        if MMS2==0:
            tequ=t
        else:
            A=(MMS1/MMS2)*((1-np.exp(-(p+q)*t))/(1+(q/p)*np.exp(-(p+q)*t)))
            if A>=1:
                tequ=t
                MMS2=MMS1
            else:
                tequ=-np.log((1-A)/(1+A*(q/p)))/(q+p)+1
        return tequ,MMS2
    
    def get_t_equ(self,time: list[float],offset:np.array,MMS:DataFrame,p:float,q:float)->tuple[DataFrame,DataFrame]:
        """
        
        This function starts the calculation the equivalent time per year and per solar resource. 

        Parameters
        ----------
        MMS : DataFrame
            maximum market share per year and solar resource bin
        offset: np.array[float]
            time offset calculated from find_time_offset, one value
        p: float
            bass difussion model parameter 
        q: float
            bass difussion model parameter 
        time: list
            time per year
        
        Returns
        ----------
        time
            updated time parameter to be used in the rest of the calculation. Includes, in some cases, the equivalent time.
        MMS
            maximum market share updated list
        """
        time=time+offset
        time=concat([Series(time)]*11,axis=1)
        for i in range(1,len(time)):
            for j in range(0,len(MMS.iloc[i])):
                time.loc[i,j],MMS.loc[i,j]=self.t_equ(MMS.loc[i-1,j],MMS.loc[i,j],p,q,time.loc[i-1,j])
        return time,MMS
    
    def find_offset_func(self,t:np.array,arg:list)->np.array:
        """
        This function has the equation used to find the offset time.

        Parameters
        ----------
        t : array
            starting guess for the time
        arg: list
            includes the historical capacity, p, q, and the market potential for the same year as the historical capacity
        
        Returns
        ----------
        ofset time

        """
        historical_capacity,p,q,market_potential=arg
        return ((1-np.exp(-(p+q)*t))/(1+(q/p)*np.exp(-(p+q)*t))*market_potential-historical_capacity)
    
    def find_time_offset(self,p:float,q:float,historical_capacity:float,MMS_res:DataFrame,MMS_com:DataFrame,
                         market_potential:Series,time:np.array)->tuple[DataFrame,DataFrame,DataFrame,DataFrame]:
        """
        This function finds the offset time then calculates the equivalent time.

        Parameters
        ----------
        MMS_res and MMS_com : DataFrame
            maximum market share per year and solar resource bin seperated by residential and commercial buildings
        historical_capacity: float
            historical capapcity from 2022
        market_potential: Series
            calculated market potential
        p: float
            bass difussion model parameter 
        q: float
            bass difussion model parameter 
        time: np.array
            time per year
        
        Returns
        ----------
        tequ_res
            new time parameter for the residential buildings
        tequ_com
            new time parameter for the commercial buildings
        MMS_res : float
            maximum market share for the residential buildings
        MMS_com: float
            maximum market share for the commercial buildings
        """
        if market_potential.iloc[0]>historical_capacity:
            init_time=fsolve(self.find_offset_func,2,[historical_capacity,p,q,market_potential.iloc[0]],factor=1)
            tequ_res,MMS_res=self.get_t_equ(time,init_time,MMS_res,p,q)
            tequ_com,MMS_com=self.get_t_equ(time,init_time,MMS_com,p,q)
        else:
            year_for_historical=market_potential[market_potential>historical_capacity].index[0]
            init_time=fsolve(self.find_offset_func,2,[historical_capacity,p,q,market_potential.iloc[year_for_historical]],factor=1)-year_for_historical
            tequ_res,MMS_res=self.get_t_equ(time,init_time,MMS_res,p,q)
            tequ_com,MMS_com=self.get_t_equ(time,init_time,MMS_com,p,q)
        return tequ_res,tequ_com,MMS_res,MMS_com

    def forecasted_technical_potential(self,cap_res: list[float],elec_res: list[float],pop_increase_res: list[float]|Series,
                                       cap_com:list[float],elec_com:list[float],pop_increase_com:list[float]|Series 
                                       )->tuple[DataFrame,DataFrame]:
        """
        Calculates the technical potential from the start of the data to the end based on historical and forecasted data.

        Parameters
        ----------
        cap_res and cap_com : list
            the technical potential capacity per year seperated by residential and commerical buildings
        elec_res and elec_com: float
            the technical potential electricity generation per year seperated by residential and commerical buildings
        pop_increase_res and pop_increase_com: Series
            the population growth (building stock growth) per year seperated by residential and commerical buildings
        
        Returns
        ----------
        technical_potential_res
            the residential technical potential by year
        technical_potential_com
            the commercial technical potential by year
        """
        pop_increase_res.reset_index(inplace=True,drop=True)
        pop_increase_com.reset_index(inplace=True,drop=True)
        technical_cap_res=[cap_res[i]*pop_increase_res[i] for i in range(0,len(pop_increase_res))]
        technical_cap_com=[cap_com[i]*pop_increase_com[i] for i in range(0,len(pop_increase_res))]

        technical_elec_res=[elec_res[i]*pop_increase_res[i] for i in range(0,len(pop_increase_res))]
        technical_elec_com=[elec_com[i]*pop_increase_com[i] for i in range(0,len(pop_increase_res))]

        technical_potential_res=DataFrame({'Capacity':technical_cap_res,'Electricity':technical_elec_res})
        technical_potential_com=DataFrame({'Capacity':technical_cap_com,'Electricity':technical_elec_com})
        return technical_potential_res,technical_potential_com

    def calculate_installed_capacity(self,p:float,q:float,market_share:DataFrame,tequ:DataFrame)->tuple[DataFrame,DataFrame]:
        """
        Calculates the predicted installed capacity from start of the data to the end

        Parameters
        ----------
        market_share: DataFrame
            calculated market potential
        p: float
            bass difussion model parameter 
        q: float
            bass difussion model parameter 
        tequ: float
            equivalent temperature
            
        Returns
        ----------
        output
            the residential technical potential by year
        rate
            the commercial technical potential by year
        """
        
        output,rate=self.installed_capacity(p,q,tequ,market_share)
        return output,rate

    def market_potential(self,capacity: DataFrame,market_share_scenario: DataFrame,payback_bins:list[Series]) -> tuple[DataFrame,DataFrame]:
        """
        Calculates the market potential which is the upper bound of the what can be installed based on the market. 

        Parameters
        ----------
        capacity: DataFrame
            calculated market potential
        market_share_scenario: DataFrame
            bass difussion model parameter 
        payback_bins: list
            payback by solar resource bin and by year
            
        Returns
        ----------
        market potential
            the market potential by year
        """
        payback_bins=DataFrame(payback_bins)
        payback_bins.reset_index(drop=True,inplace=True)
        payback_bins=payback_bins.replace(np.inf,3000)
        
        market_share=self.interpolate(payback_bins,market_share_scenario)
        return market_share.multiply(capacity,axis=0), market_share

    def interpolate(self,payback: DataFrame,data: DataFrame)->DataFrame:
        """
        This function is used to interpolate if the exact calculated payback value is not in the max market share curves.

        Parameters
        -------
        payback: DataFrame
            calculated payback
        data: DataFrame
            the maximum market share curves from the other functions in this file

        Returns
        -------
        market_share: DataFrame
            returns the actual max market share that corresponds to the calculated payback
        """
        market_share=np.interp(payback,data['Payback'],data['Market Share'])
        market_share=DataFrame(market_share)/100
        return market_share

    def installed_capacity(self,p: float,q: float,tequ: DataFrame,market: DataFrame) -> DataFrame:
        """
        Calculates the installed capacity per year by multiplying the market potential by the adoption rate

        Parameters
        ----------
        market: DataFrame
            market potential by year and solar resource
        p: float
            bass difussion model parameter 
        q: float
            bass difussion model parameter 
        tequ: DataFrame
            equivalent temperature
            
        Returns
        ----------
        output installed capacity
        """
        rate=self.adoption_rate(p,q,tequ.transpose())
        return market.transpose().multiply(rate),rate
    
    def adoption_rate(self,p: float,q: float,tequ: DataFrame) -> DataFrame:
        """
        Calculates the adoption rate from the Bass diffusion model.

        Parameters
        ----------

        p: float
            bass difussion model parameter 
        q: float
            bass difussion model parameter 
        tequ: DataFrame
            equivalent temperature
            
        Returns
        ----------
        output installed capacity
        """
        t=tequ
        return (1-np.exp(-(p+q)*t))/(1+(q/p)*np.exp(-(p+q)*t))
        
    def forecasted_electricity(self,forecasted_capacity:DataFrame, solar_yield:Series)->DataFrame:
        """
        Calculates the forecasted electricity from the solar yield and forecasted capacity.

        Parameters
        ----------
        forecasted_capacity: DataFrame
            calculated installed capacity that was forecasted to the end year ex. 2050
        solar_yield: Series
            solar yield by year and solar resource bin. Includes PR.
            
        Returns
        ----------
        output forecasted electricity generation
        """
        forecasted_capacity=forecasted_capacity.transpose()
        return forecasted_capacity*solar_yield/1000

    def calculate_ac_power(self,capacity_res:DataFrame,capacity_com:DataFrame,performance_ratio:tuple[list[float],list[float]],
                           hosting_capacity:hosting_capacity_variables,weighted_POA:DataFrame,temperature_coefficient:float,
                           temperature:Series,pv_module_efficiency:list[float],demand:DataFrame,starting_year:int)->tuple[list[float],list[float],list[float]]: 
        """
        Calculates the AC power generation to get the hourly generation and compare that to the demand for the hosting capacity limit.

        Parameters
        ----------
        capacity_res and capacity_com:DataFrame
            residential and commercial capacity 
        performance_ratio: tuple[list,list]
            performance ratio with the residential and commercial values
        hosting_capacity: hosting_capacity_variables
            object contaning the variables needed for the hosting capacity and hourly modelling
        weighted_POA:DataFrame 
            Shaded hourly POA weighted to account for the the capacity installed vs shaded POA on
            each segment (calculated and outputted from calculate_potential_city.py)
        temperature_coefficient:float 
            Temperature coefficient for the module
        temperature:Series
            Annual temperature by hour
        pv_module_efficiency: list
            Module efficiency
        demand: 
            Hourly demand by year
        starting_year:int
            The starting year of the analysis

        Returns
        ----------
        ratio_all
            Minimum ratio between the hosting_limit*demand to the generation
        num_hour_curt_all
            Number of hours curtailed per year
        pot_curt_elec_all
            Electricity curtailed per year
        
        """
        ind=0
        ratio_all=[]
        for year in range(starting_year,len(performance_ratio[0])+starting_year):
            Pac_array=[]
            mode_ind=0
            for capacity in [capacity_res,capacity_com]:
                performance_ratio_years=performance_ratio[mode_ind]
                performance_ratio_years=Series(performance_ratio_years)
                performance_ratio_years = performance_ratio_years.iloc[ind] / (1-hosting_capacity.degradation_rate.iloc[ind]*hosting_capacity.lifetime_years/2)
                for bin_number in np.arange(0,10):
                    
                    Pdc_STC_MW = capacity[ind][bin_number]*1000
                    POA = weighted_POA.iloc[:,bin_number]*1000
                    POA.index=temperature.index
                    #Cell temperature
                    Tcell = pvlib.temperature.pvsyst_cell(poa_global=POA, temp_air=temperature, wind_speed=0,
                                                           u_c=hosting_capacity.u_c, u_v=hosting_capacity.u_v, 
                                                           module_efficiency =pv_module_efficiency[ind], alpha_absorption=0.9)

                    #DC and AC power using PVWatts
                    Pdc = pvlib.pvsystem.pvwatts_dc(effective_irradiance=POA,temp_cell=Tcell,pdc0=Pdc_STC_MW,gamma_pdc=temperature_coefficient)
                    # Compute Pdc0 input for PVWatts DC model. This is rated AC power divided by nominal inverter efficiency.
                    Pdc0 = (Pdc_STC_MW/hosting_capacity.dc_to_ac_capacity_ratio)/hosting_capacity.inverter_efficiency_nominal
                    Pac = pvlib.inverter.pvwatts(Pdc, Pdc0, hosting_capacity.inverter_efficiency_nominal)

                    #Rescale to match specified performance ratio, then clip to rated inverter power (which will entail some mismatch from performance ratio)
                    PR = Pac.sum()/Pdc_STC_MW/(POA.sum()/1000)
                    Pac = Pac*performance_ratio_years/PR
                    #Apply inverter clipping
                    Pac = Pac.apply(lambda x: min(x,Pdc_STC_MW/hosting_capacity.dc_to_ac_capacity_ratio))

                    Pac_array.append(Pac.values)
                mode_ind=mode_ind+1
            Pac_array =DataFrame(Pac_array).sum()

            ratio=self.hosting_capacity(year,demand,Pac_array,hosting_capacity.hosting_limit)
            ratio_all.append(ratio)
            ind=ind+1

        return ratio_all

    def percent_electricity_demand(self,electricity_res:DataFrame,electricity_com:DataFrame,annual_demand:str,mode:str,tech_res:DataFrame=None,tech_com:DataFrame=None)->tuple[Series,Series,Series]:
        """
        Calculate the percent of demand covered by generation, whether total demand or only in the building sector.

        Parameters
        ----------
        electricity_res and electricity_com:DataFrame
            residential and commercial electricity generation 
        tech_res and tech_com:DataFrame
            residential and commercial electricity generation for the technical potential
        annual_demand: str
            location of the annual demand files.

        Returns
        ----------
        percent_demand
            percent demand for the building sector
        total_percent_demand
            percent demand for the total sector
        percent_demand_tech
            percent demand for the total sector for the technical potential
        total_demand
            Total demand found in the provided file
        """
        try:
            df=read_csv(annual_demand)
            try:
                elec_res=electricity_res.sum(axis=1)
                elec_com=electricity_com.sum(axis=1)
                all_elec=elec_res.add(elec_com,fill_value=0)
                if len(electricity_res)==len(df['Total']):
                    total_demand=df['Total']
                    total_percent_demand=all_elec/df['Total']*1000*1000
                    all_tech=tech_com.add(tech_res,fill_value=0)
                    percent_demand_tech=all_tech/df['Total']
                elif len(electricity_res)>len(df['Total']):
                    cut_length=len(electricity_res)-len(df['Total'])
                    total_demand=df['Total']
                    all_elec=all_elec[cut_length:].reset_index(drop=True)
                    total_percent_demand=all_elec/df['Total']*1000*1000
                    all_tech=tech_com.add(tech_res,fill_value=0)
                    percent_demand_tech=all_tech[cut_length:].reset_index(drop=True)/df['Total']
                else:
                    cut_length=len(df['Residential'])-len(electricity_res)
                    total_demand=df['Total'][cut_length:].reset_index(drop=True)
                    total_percent_demand=all_elec/total_demand*1000*1000
                    all_tech=tech_com.add(tech_res,fill_value=0)
                    percent_demand_tech=all_tech/total_demand
                return total_percent_demand,percent_demand_tech,total_demand
            except:
                return total_percent_demand
        except:
            # print("No electricity demand file found or it is not in the same format")
            # print("Eliminating calculation for the percent demand as a function of the electricity generated")
            if mode=='grid':
                return Series(-999)
            else:
                return Series(-999),Series(-999),Series(-999)

    def shift_hourly_demand(self,demand:DataFrame,region:str)->DataFrame:
        """
        Shift the timestep of the hourly demand to match the timestep of the other files

        Parameters
        ----------
        demand: DataFrame
            hourly demand profile
        region: str
            the acronym for the each region

        Returns
        ----------
        demand
            Hourly demand profile modified to match the timesteps, only for certain regions
        """
        if not(region=='NL' or region=='NU' or region=='NT' or region=='YK'):
            demand2=demand.copy()
            starting_row=demand.iloc[-1:]
            demand2=concat([starting_row,demand2]).reset_index(drop=True)
            demand['Total']=(demand2['Total']+demand['Total'])/2
        return demand

    def hosting_capacity(self,year:int,demand:DataFrame,generation:Series,hosting_limit:float)->tuple[float,float,float]:        
        """
        Calculate the generation curtailment needed to meet the hosting limit for the demand

        Parameters
        ----------
        year:int
            year in question for the analysis
        demand:DataFrame
            hourly demand
        generation:Series
            hourly electricity generated (AC)
        hosting_limit:float
            ratio to limit the demand based on the grid

        Returns
        ----------
        min_ratio
            Minimum ratio between the hosting_limit*demand to the generation
        """
        
        load_year_times_factor = demand.loc[demand['Year']==year,'Total'] * hosting_limit
        load_year_times_factor.reset_index(drop=True,inplace=True)
        ratio_hourly=load_year_times_factor/load_year_times_factor.combine(generation, max)
        min_ratio = ratio_hourly.min()
        return min_ratio
    
    def get_hourly_electricity_demand(self,hourly_demand:str)->DataFrame:
        """
        Extract the hourly demand from the file

        Parameters
        ----------
        hourly_demand: str
            location of the hourly demand profile

        Returns
        ----------
        df
            dataframe containing the hourly demand
            
        """
        df=read_csv(hourly_demand)
        df.drop('Scenario',axis=1,inplace=True)
        df.drop('region',axis=1,inplace = True)
        return df

    def calculate_market_capacity(self,p:float,q:float,func_eff:list,func_pr:list,func_bldg:list,func_elec:list,func_market:list,func_cost:list,region:str,
                                  region_variables:region_data,starting_year:int,time:np.array,POA_bin:DataFrame,temperature:Series,temp_coeff:float,
                                  hosting_capacity:hosting_capacity_variables,demand:DataFrame,mode:str,annual_demand:str,scaling_option=True)->list:
        """
        function to calculate all aspects for the market potential, adotpion rate, market penetratio and the results to output by scenario

        Parameters
        ----------
        func_eff,func_pr,func_bldg,func_elec,func_market, and func_cost:list
            lists containing the the different scenarios for module efficiency, performance ratio, building growth, electricity cost, max market share, and the cost of PV
        region_variables: region_data.location
            object for the region-specific variables
        hosting_capacity: hosting_capacity_variables
            object contaning the variables needed for the hosting capacity and hourly modelling
        POA_bin:DataFrame 
            Shaded hourly POA weighted to account for the the capacity installed vs shaded POA on
            each segment by bin (calculated and outputted from calculate_potential_city.py)
        temp_coeff:float 
            Temperature coefficient for the module
        temperature:Series
            Annual temperature by hour
        time: np.array
            time for the analysis
        demand: DataFrame
            Hourly demand by year
        starting_year:int
            The starting year of the analysis to be used for the hosting capacity analysis
        mode: str
            identifies what mode the analysis is in
        annul_demand:str
            location of the files for the annual demand
        scaling_option : bool
            option whether to scale the technical potential for the rest of the analysis or use them outputs as is. True to use coefficients to scale the output.

        Returns
        ----------
        list of the outputs calculated for the percent demand, output in 2050 and hosting capacity curtailment (if the option is enabled)
        
        """
        
                            
        #Calculate the payback by bin
        if scaling_option:
            technical_potential_res,technical_potential_com=self.forecasted_technical_potential(region_variables.cap_res,region_variables.elec_res,func_bldg[0][region],region_variables.cap_com,region_variables.elec_com,func_bldg[1][region])
            potential_by_threshold_res,payback_bins_res,solar_yield_res=self.calculate_payback_bin(region_variables.daily_insolation,technical_potential_res['Capacity'],func_elec[0][region],func_cost[0],func_pr[0],region_variables.cap_coefficient_shade)
            potential_by_threshold_com,payback_bins_com,solar_yield_com=self.calculate_payback_bin(region_variables.daily_insolation,technical_potential_com['Capacity'],func_elec[1][region],func_cost[1],func_pr[1],region_variables.cap_coefficient_shade)
        else:
            technical_potential_res_cap,technical_potential_res_elec=[],[]
            technical_potential_com_cap,technical_potential_com_elec=[],[]
            for i in range(0,len(region_variables.cap_res.transpose().columns)):
                temp_res,temp_com=self.forecasted_technical_potential(region_variables.cap_res.iloc[i],region_variables.elec_res.iloc[i],func_bldg[0][region],region_variables.cap_com.iloc[i],region_variables.elec_com.iloc[i],func_bldg[1][region])
                technical_potential_res_cap.append(temp_res['Capacity'])
                technical_potential_res_elec.append(temp_res['Electricity'])
                technical_potential_com_cap.append(temp_com['Capacity'])
                technical_potential_com_elec.append(temp_com['Electricity'])
            technical_potential_res_cap,technical_potential_res_elec=DataFrame(technical_potential_res_cap),DataFrame(technical_potential_res_elec)
            technical_potential_com_cap,technical_potential_com_elec=DataFrame(technical_potential_com_cap),DataFrame(technical_potential_com_elec)
            cap_res=technical_potential_res_cap.transpose()
            cap_res.columns=list(range(11))
            cap_com=technical_potential_com_cap.transpose()
            cap_com.columns=list(range(11))
            potential_by_threshold_res,payback_bins_res,solar_yield_res=self.calculate_payback_bin(region_variables.daily_insolation,cap_res,func_elec[0][region],func_cost[0],func_pr[0])
            potential_by_threshold_com,payback_bins_com,solar_yield_com=self.calculate_payback_bin(region_variables.daily_insolation,cap_com,func_elec[1][region],func_cost[1],func_pr[1])

        #Calculate the market potential
        market_res, MMS_res=self.market_potential(potential_by_threshold_res,func_market[0],payback_bins_res)
        market_com, MMS_com=self.market_potential(potential_by_threshold_com,func_market[1],payback_bins_com)

        market_all=market_res.add(market_com,fill_value=0)
        offset_res,offset_com,MMS_res,MMS_com=self.find_time_offset(p,q,region_variables.historical_capacity,MMS_res,MMS_com,market_all.sum(axis=1),time)
        
        #calculate the residential capacity
        output_res,rate_res=self.calculate_installed_capacity(p,q,market_res,offset_res)
        
        #Calculate the commercial capacity
        output_com,rate_com=self.calculate_installed_capacity(p,q,market_com,offset_com)
        output=output_res.add(output_com,fill_value=0)
        for i in range(0,len(output.sum(axis=0))):
            if output[i].sum()<region_variables.historical_capacity:
                res_temp=output_res.iloc[:,i].sum()
                com_temp=output_com.iloc[:,i].sum()
                ratio=res_temp/(com_temp+res_temp)
                output_res.iloc[:,i]=0.000000001
                output_com.iloc[:,i]=0.000000001
                output_res.iloc[-2,i]=region_variables.historical_capacity*ratio
                output_com.iloc[-2,i]=region_variables.historical_capacity*(1-ratio)
        for i in range(1,len(output_res.sum(axis=0))):
            for j in range(0,len(output_res[0])):
                if MMS_res.loc[i,j]==MMS_res.loc[i-1,j]:
                    output_res.loc[j,i]=output_res.loc[j,i-1]
                else:
                    rate_prev_tequ=self.adoption_rate(p,q,offset_res.loc[i,j]-1)
                    output_res.loc[j,i]=output_res.loc[j,i-1]+market_res.loc[i,j]*(rate_res.loc[j,i]-rate_prev_tequ)
                if MMS_com.loc[i,j]==MMS_com.loc[i-1,j]:
                    output_com.loc[j,i]=output_com.loc[j,i-1]
                else:
                    rate_prev_tequ=self.adoption_rate(p,q,offset_com.loc[i,j]-1)
                    output_com.loc[j,i]=output_com.loc[j,i-1]+market_com.loc[i,j]*(rate_com.loc[j,i]-rate_prev_tequ)

        if mode=='grid':
            ratio_all=self.calculate_ac_power(output_res,output_com,func_pr,hosting_capacity,
                                POA_bin,temp_coeff,temperature,func_eff,demand,starting_year)
            
            output_res_grid=output_res*ratio_all
            output_com_grid=output_com*ratio_all
            ratio_all=list(map(float, ratio_all))
            elec_res_grid=self.forecasted_electricity(output_res_grid,solar_yield_res)
            elec_com_grid=self.forecasted_electricity(output_com_grid,solar_yield_com)
        else:
            ratio_all=0
            output_res_grid=Series(0)
            output_com_grid=Series(0)
            elec_res_grid=Series(0)
            elec_com_grid=Series(0)
        elec_res=self.forecasted_electricity(output_res,solar_yield_res)
        elec_com=self.forecasted_electricity(output_com,solar_yield_com)

        
        if not(scaling_option) and mode=='grid':
            total_percent_demand_grid=self.percent_electricity_demand(elec_res_grid,elec_com_grid,
                                                                        annual_demand,mode)
            total_percent_demand,total_percent_tech,total_demand=self.percent_electricity_demand(elec_res,elec_com,
                                                                        annual_demand,'Market',technical_potential_res_elec.sum(),
                                                                        technical_potential_com_elec.sum())
            
            total_percent_demand_grid=total_percent_demand_grid.fillna(0)
            technical_capacity=technical_potential_res_cap.sum()+technical_potential_com_cap.sum()
            technical_electricity=technical_potential_res_elec.sum()+technical_potential_com_elec.sum() 
            output_grid=output_res_grid.add(output_com_grid,fill_value=0).sum()
            elec_grid=elec_res_grid.add(elec_com_grid,fill_value=0).sum(axis=1)
             
        else:
            if mode=='grid':
                total_percent_demand_grid=self.percent_electricity_demand(elec_res_grid,elec_com_grid,
                                                                            annual_demand,mode)
                total_percent_demand_grid=total_percent_demand_grid.fillna(0)
                output_grid=output_res_grid.add(output_com_grid,fill_value=0).sum()
                elec_grid=elec_res_grid.add(elec_com_grid,fill_value=0).sum(axis=1)
            else:
                total_percent_demand_grid=Series(0)
                output_grid=Series(0)
                elec_grid=Series(0)
            total_percent_demand,total_percent_tech,total_demand=self.percent_electricity_demand(elec_res,elec_com,
                                                                        annual_demand,'Market',technical_potential_res['Electricity'],
                                                                        technical_potential_com['Electricity'])
            technical_capacity=technical_potential_res['Capacity']+technical_potential_com['Capacity']
            technical_electricity=technical_potential_res['Electricity']+technical_potential_com['Electricity'] 

        
        elec=elec_res.add(elec_com,fill_value=0)
        output=output_res.add(output_com,fill_value=0)
    
        total_demand=total_demand.fillna(0)
        total_percent_demand=total_percent_demand.fillna(0)
        total_percent_tech=total_percent_tech.fillna(0)

        return [output,elec,ratio_all,
                technical_electricity/1000/1000,total_percent_tech,technical_capacity,
                total_percent_demand,total_demand,
                output_grid,elec_grid,total_percent_demand_grid]

class SensitivityAnalysis(DeployedCapacity):
        
    def __init__(self,region_variables:region_data=0)->None:
        self.region_variables=region_variables

    def sensitivity_analysis(self,p_range:list,q_range:list,cost_scenarios:list,elec_cost_scenarios:list,pv_eff:list,region:str,
                             market_share_scenarios:list,pv_pr:list,bldg_scenarios:list,
                             file_location:str,starting_year:int,ending_year:int,time:np.array,mode:str,
                             annual_demand:str='',hourly_demand:str='',shading_granularity:str='hourly',
                             hosting_capacity: hosting_capacity_variables=None,scaling_option:bool=True )->None:
        
        """
        This function set ups the sensitivity analysis and runs through a region

        Parameters
        -------
        p_range and q_range: list
            list of the scenarios used for the bass diffusion paramters p and q
        cost_scenarios, elec_cost_scenarios, pv_eff, market_share_scenarios,pv_pr,bldg_scenarios
            lists containing the the different scenarios for module efficiency, performance ratio, building growth, electricity cost, max market share, and the cost of PV
        file_location:str
            location of all the files
        starting_year:int
            The starting year of the analysis
        time: np.array
            time for the analysis
        mode: str
            identifies what mode the analysis is in
        annual_demand:list[str]
            location of the files for the annual demand per region in a list
        hourly_demand:list[str]
            location of the files for the hourly demand per region in a list
        hosting_capacity: hosting_capacity_variables
            object contaning the variables needed for the hosting capacity and hourly modelling
        resolution:int|float
            resolution of the dsm files to be created (if needed)
        scaling_option : bool
            option whether to scale the technical potential for the rest of the analysis or use them outputs as is. True to use coefficients to scale the output.
        """
        all_scenarios=[]
        electicity=[]
        
        if mode=="grid":
            if shading_granularity=='representative':
                rep_days=12
                TID=self.calculate_rep_tech_potential(file_location,self.region_variables,rep_days)
                technical_potential=calculate_technical_potential.calculate_technical_potential_rep(TID,self.region_variables,0.75,0.225,rep_days,mode)
            elif shading_granularity=='hourly':
                TID=self.calculate_hourly_tech_potential(file_location,self.region_variables)
                technical_potential=calculate_technical_potential.calculate_technical_potential_hourly(TID,self.region_variables,0.75,0.225,mode)
            demand=self.get_hourly_electricity_demand(hourly_demand)
            # demand=self.shift_hourly_demand(demand,region)
        else:
            demand=[0]

        for eff in range(0,len(pv_eff[0])):
            name=pv_eff[2][eff]
            temp_coeff=pv_eff[1][eff][0][0]
            func_eff=pv_eff[0][eff][0]
            
            for pr in range(0,len(pv_pr[0])):
                func_pr=[pv_pr[0][pr][0],pv_pr[1][pr][0]] 
                if mode=="grid":
                    technical_potential.set_efficiency(func_eff[0])
                    technical_potential.set_performance_ratio(func_pr[0][0])
                    data=technical_potential.hourly_grid()
                    temperature=data[1]
                    poa=data[0].transpose()
                    POA_bin=poa.fillna(0).sort_index()
                    hosting_capacity.set_degradation_rate(pv_pr[2][pr][0])
                    
                else:
                    POA_bin=[0]
                    temperature=[0]
                if scaling_option:
                    self.region_variables.rooftop_capacity(func_eff,'res')
                    self.region_variables.rooftop_capacity(func_eff,'com') 
                    self.region_variables.rooftop_generation(func_pr[0],'res')
                    self.region_variables.rooftop_generation(func_pr[1],'com')
                else:
                    capacity=[]
                    electricity=[]
                    for i in range(0,len(func_eff)):
                        technical_potential.set_efficiency(func_eff[i])
                        technical_potential.set_performance_ratio((func_pr[0]*self.region_variables.division_res_bldgs+func_pr[1]*(1-self.region_variables.division_res_bldgs))[i])
                        data=technical_potential.hourly_grid()
                        capacity.append(data[2])
                        electricity.append(data[3])
                    capacity=DataFrame(capacity).transpose()
                    electricity=DataFrame(electricity).transpose()
                    self.region_variables.set_capacity(capacity)
                    self.region_variables.set_electricity(electricity)

                for cost in range(0,len(cost_scenarios[0])):
                    func_cost=[cost_scenarios[0][cost][0],cost_scenarios[1][cost][0]] 
                    for market in range(0,len(market_share_scenarios[0])):
                        func_market=[market_share_scenarios[0][market],market_share_scenarios[1][market]]
                        for elec in range(0,len(elec_cost_scenarios[0])):
                            func_elec=[elec_cost_scenarios[0][elec],elec_cost_scenarios[1][elec]]
                            for bldg in range(0,len(bldg_scenarios[0])):
                                func_bldg=[bldg_scenarios[0][bldg],bldg_scenarios[1][bldg]]
                                for p in p_range:
                                    for q in q_range:
                                           
                                        outputs=self.calculate_market_capacity(p,q,func_eff,func_pr,func_bldg,func_elec,func_market,func_cost,region,self.region_variables,
                                                                            starting_year,time,POA_bin,temperature,temp_coeff,hosting_capacity,demand,mode,annual_demand,scaling_option)
                                        all_scenarios.append([cost_scenarios[2][cost],bldg_scenarios[2][bldg],elec_cost_scenarios[2][elec],name,pv_pr[3][pr],market_share_scenarios[2][market],
                                                            p,q,outputs[5].to_list(),outputs[0].sum(axis=0).to_list(),outputs[8].to_list(),outputs[2]])
                                        
                                        electicity.append([cost_scenarios[2][cost],bldg_scenarios[2][bldg],elec_cost_scenarios[2][elec],name,pv_pr[3][pr],market_share_scenarios[2][market],
                                                            p,q,outputs[3].to_list(),outputs[1].sum(axis=1).to_list(),outputs[9].to_list(),outputs[4].to_list(),outputs[6].to_list(),
                                                            outputs[10].to_list(),outputs[7].to_list()])
                                

        all_scenarios=DataFrame(all_scenarios,columns=['PV cost scenario', "Building growth scenario", 'Electricity cost scenario', 'PV efficiency scenario','PR scenario', 'Market share scenario',
                                                    'p','q','Technical potential capacity by year (GW)','Installed capacity by year (GW)','Installed capacity - grid by year (GW)',
                                                'Capacity with grid constraints divided by capacity without by year'])
        electicity=DataFrame(electicity,columns=['PV cost scenario', "Building growth scenario", 'Electricity cost scenario', 'PV efficiency scenario','PR scenario', 'Market share scenario',
                                                'p','q','Technical potential - Annual electricity output by year (TWh)','Annual electricity output (TWh) from installed capacity by year',
                                                'Annual electricity output (TWh) from installed capacity with grid constraints by year','Technical potential as a fraction of total demand by year (-)',
                                                'Annual output as a fraction of total demand by year (-)','Annual output as a fraction of total demand (-) with grid constraints by year' ,'Total demand by year (MWh)'])
        self.write_excel(file_location,region,all_scenarios,electicity,mode)
        graphs=make_graphs.data(file_location,mode)
        graphs.extract_data_one(file_location+r'\output_'+mode+'_'+region+'.xlsx')
        graphs.clean_data()
        make_graphs.create_graphs_region(graphs,starting_year,ending_year)
     
    def write_excel(self,file_location:str,region:str,all_scenarios:DataFrame,electicity:DataFrame,mode:str)->None:
        """
        This function writes the outputs to an excel file

        Parameters
        -------
        file_location: str
            file location of the files
        region: str
            name of the region done for the analysis
        all_scenarios: DataFrame
            dataframe of the results for the analysis
        electicity: DataFrame
            dataframe of the results for the analysis
        """
        path=file_location+r'\output_'+mode+'_'+region+'.xlsx'
        writer=ExcelWriter(path,engine='xlsxwriter')

        all_scenarios.to_excel(writer,sheet_name='Capacity')
        electicity.to_excel(writer,sheet_name='Electricity')
        writer.close()
    
    def set_region_variables(self,region:str,mode:str,scaling_option:bool=True,cap_coefficient_shade:list=[],elec_coefficient_shade:list=[])->None:
        """
        This function gets the region specific inputs for the specific region in question

        Parameters
        -------
        region: str
            name of the region for the analysis
        mode:str
            mode of the analysis
        scaling_option : bool
            option whether to scale the technical potential for the rest of the analysis or use them outputs as is. True to use coefficients to scale the output.
        """
        self.region_variables=region_data.location(region,mode,scaling_option,cap_coefficient_shade,elec_coefficient_shade)
        

    def sensitivity_analysis_all_regions(self,p_range:list,q_range:list,cost_scenarios:list,elec_cost_scenarios:list,
                             pv_eff:list,market_share_scenarios:list,pv_pr:list,bldg_scenarios:list,file_location:str,starting_year:int,
                             ending_year:int,time:np.array,mode:str,regions:list[str],annual_demand:list[str]=[''],cap_coefficient_shade:list=[],elec_coefficient_shade:list=[],
                             hourly_demand:list[str]=[''],shading_granularity:str='hourly',hosting_capacity:hosting_capacity_variables=None,resolution:float=1,scaling_option:bool=True)->None:
        
        """
        This function set ups the sensitivity analysis and runs through each region in the batch simulation option

        Parameters
        -------
        p_range and q_range: list
            list of the scenarios used for the bass diffusion paramters p and q
        cost_scenarios, elec_cost_scenarios, pv_eff, market_share_scenarios,pv_pr,bldg_scenarios
            lists containing the the different scenarios for module efficiency, performance ratio, building growth, electricity cost, max market share, and the cost of PV
        file_location:str
            location of all the files
        starting_year:int
            The starting year of the analysis
        time: np.array
            time for the analysis
        mode: str
            identifies what mode the analysis is in
        regions:list
            list of regions in the analysis
        annual_demand:list[str]
            location of the files for the annual demand per region in a list
        hourly_demand:list[str]
            location of the files for the hourly demand per region in a list
        hosting_capacity: hosting_capacity_variables
            object contaning the variables needed for the hosting capacity and hourly modelling
        resolution:int|float
            resolution of the dsm files to be created (if needed)
        scaling_option : bool
            option whether to scale the technical potential for the rest of the analysis or use them outputs as is. True to use coefficients to scale the output.
        """
        ind=0
        for prov in regions:
            if mode=="grid":
                self.set_region_variables(prov,mode,scaling_option,cap_coefficient_shade,elec_coefficient_shade)
                self.region_variables.mosaic=file_location+r'\mosaic_'+self.region_variables.file_classifier+'.tif' #file name location of the output mosaic file
                self.region_variables.raster_file=file_location+'\\'+self.region_variables.file_classifier+'_rooftop_Raster.tif' #file name location of the output rasterized shapefile
                self.region_variables.shapefile=file_location+'\\'+self.region_variables.file_classifier+'_rooftop.shp' #file name location of the output shapefile from the segmentation
                check_calculate_technical_files(self.region_variables,resolution)
                self.sensitivity_analysis(p_range,q_range,cost_scenarios,elec_cost_scenarios,pv_eff,prov,market_share_scenarios,
                                    pv_pr,bldg_scenarios,file_location,starting_year,ending_year,time,mode,annual_demand[ind],hourly_demand[ind],shading_granularity,hosting_capacity,scaling_option)
                
            else:
                self.set_region_variables(prov,mode,True,cap_coefficient_shade,elec_coefficient_shade)
                self.sensitivity_analysis(p_range,q_range,cost_scenarios,elec_cost_scenarios,pv_eff,prov,market_share_scenarios,pv_pr,bldg_scenarios,file_location,starting_year,
                                          ending_year,time,mode,annual_demand[ind])
            ind=ind+1
        graphs=make_graphs.data(file_location,mode)
        os.chdir(file_location)
        graphs.extract_data_all()
        graphs.clean_data()
        make_graphs.create_graphs(graphs,ending_year)
    
    def calculate_hourly_tech_potential(self,file_location:str,region_variables:region_data)->DataFrame:
        """
        This function runs the shading analysis, saves it to a file and returns the result. If the saved file already exists, it loads the file and returns the output.
        saved file name format: file_location+'//TimeInDaylight_hourly_' + region.file_classifier+'.ftr'

        Parameters
        -------
        file_location: str
            file location of the files
        region_variables:region_data
            object containing file locations for lidar, DSM, segmentation files and region-specific variables

        Returns
        -------
        TID: DataFrame
            returns the time in daylight results which is the shading for each segment of the rooftop for the region in question.
        """
        file_save=file_handle()
        saved_file=file_location+'//TimeInDaylight_hourly_' + region_variables.file_classifier+'.ftr'
        #run shading if the saved_file has not been created yet. If it existes use the file to run the rst of the calculations
        if not(os.path.isfile(saved_file)):
            shading=TimeInDaylight.TID(region_variables,file_location)
            print("Starting shading")
            TID=shading.hourly()
            file_save.write_file(TID,saved_file)
            TID.set_index('index',inplace=True)
            print("Shading completed\n")
        else:
            TID=file_save.extract_data(saved_file)
        return TID
    def calculate_rep_tech_potential(self,file_location:str,region_variables:region_data,rep_days:int)->DataFrame:
        """
        This function runs the shading analysis, saves it to a file and returns the result. If the saved file already exists, it loads the file and returns the output.
        saved file name format: file_location+'//TimeInDaylight_hourly_' + region.file_classifier+'.ftr'

        Parameters
        -------
        file_location: str
            file location of the files
        region_variables:region_data
            object containing file locations for lidar, DSM, segmentation files and region-specific variables

        Returns
        -------
        TID: DataFrame
            returns the time in daylight results which is the shading for each segment of the rooftop for the region in question.
        """
        file_save=file_handle()
        saved_file=file_location+'//TimeInDaylight_rep_' +str(rep_days)+'_'+ region_variables.file_classifier+'.ftr'
        #run shading if the saved_file has not been created yet. If it existes use the file to run the rst of the calculations
        
        if not(os.path.isfile(saved_file)):
            shading=TimeInDaylight.TID(region_variables,file_location)
            print("Starting shading")
            TID=shading.representative(rep_days)
            file_save.write_file(TID,saved_file)
            TID.set_index('index',inplace=True)
            print("Shading completed\n")
        else:
            TID=file_save.extract_data(saved_file)
        return TID
    
def check_calculate_technical_files(region_variables:region_data,resolution:float|int)->None:
    """
    This function checks whether the DSM, mosaic and segmentation files exist for the region used in the analysis.

    Parameters
    -------
    region_variables: region_data
        object containing file locations for lidar, DSM, segmentation files and region-specific variables
    resolution:float
        resolution used to create the DSM files
    """

    #If the files don't already exist for the DSM files (run_lidar), combining into a mosaic (run_mosaic), and creating the segmentation files (run_seg)
    if len(glob.glob(region_variables.lidar+"/*.tif"))==0:
        print("Creating DSM files...")
        region_variables.run_lidar(resolution)
        print("Created all DSM files\n")
    if not(os.path.isfile(region_variables.mosaic)):
        print("Starting mosaic...")
        region_variables.run_mosaic()
        print("Created mosaic\n")
    if not(os.path.isfile(region_variables.shapefile)):
        print("Starting segmentation...")
        region_variables.run_seg()
        spatial=spatial_toolset()
        spatial.rasterize_polygon(region_variables.mosaic,region_variables.shapefile,region_variables.raster_file,resolution)
        print("Finished segmentation\n")                                





