# -*- coding: utf-8 -*-
"""
Created on Tue. July 25 8:56 2023

@authors: egaucher
"""

import numpy_financial as np
from numpy import isnan,isinf
from matplotlib import pyplot as plt
from pandas import DataFrame
import multiprocessing as mp 
import plotly.graph_objects as go
import plotly.io as pio
pio.templates.default = "simple_white"

class economic:
    """
    Class with functions to calculate the payback or internal rate of each rooftop segement

    """
    def __init__(self,years:int=30,elec_cost:list[float]=[],incentives:float|int=0,PV_cost_years:list[float]=[],PV_cost:float=2.62)->None:
        self.years=years
        self.elec_cost=elec_cost
        self.incentives=incentives
        self.PV_cost_years=[i * PV_cost for i in PV_cost_years]
    
    def set_PV_cost(self,PV_cost: list[float],PV_cost_years: list[float])->None:
        """
        Calculates what the future cost of PV based on ratios found from NREL ATB to 2050.

        Parameters
        ----------
        PV_cost : list[float] | float
            fixed cost of PV
        PV_cost_years : list[float]
            increase in PV cost over x number of years
        
        Returns
        -------
        None.
        """
        self.PV_cost_years=[i * PV_cost for i in PV_cost_years]
    
    def payback_bin(self,rooftop: DataFrame,years: int)->list[float]:
        """
        Calculates the payback based on the bin the rooftop segments are in.

        Parameters
        ----------
        rooftop : DataFrame
            dataframe of the rooftop specifications
        years : int
            the number of years to calculate the payback
        
        Returns
        -------
        payback: list[float]
            payback of each solar resource bin
        """
        payback=[]
        for i in range(0,years):
            payback.append((self.PV_cost_years[i]*1000-self.incentives)/(rooftop['PV_energy_kWh']*self.elec_cost[i]))
        return payback