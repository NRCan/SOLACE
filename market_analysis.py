# -*- coding: utf-8 -*-
"""
Created on Mon. April.  22  2024

@author: egaucher
"""
import numpy as np
import pandas as pd
class market_analysis:
    """
    Functions to calculate the market potential and forecasted installed capacity to 2050.
    """

    def __init__(self,capacity: pd.DataFrame,payback: list[float],p:float=0.0015,q:float=0.3) -> None:
        self.payback=pd.DataFrame(payback)
        self.payback=self.payback.transpose()
        self.p=p
        self.q=q
        self.sensitivity_factor=0.3 #f
        self.capacity=capacity
        self.time=list(range(20,50))
        self.time=np.array(self.time, dtype='float32')
        self.payback_infinity=6
        self.s=0.1

    def set_payback(self,payback:list[float]) -> None:
        """
        Set the payback if it has changed.

        Parameters
        -------
        payback: list[float]
            the payback per year
        """
        self.payback=pd.DataFrame(payback)
        self.payback=self.payback.transpose()

    def adoption_rate(self) -> list[float]:
        """
        Calculate the adoption rate from the Bass diffusion model.

        """
        return (1-np.exp(-(self.p+self.q)*self.time))/(1+(self.q/self.p)*np.exp(-(self.p+self.q)*self.time))
    
    def market_potential(self) -> pd.DataFrame:
        """
        Calculate the market potential throughout time.
        """
        return np.exp(-self.sensitivity_factor*self.payback).multiply(self.capacity,axis=0)
    
    def installed_capacity(self) -> pd.DataFrame:
        """
        Calculates the forecasted installed capacity to 2050.
        """
        output=self.market_potential().multiply(self.adoption_rate(),axis=1)
        return output
    
    