
class hosting_capacity:
    def __init__(self,inverter_efficiency_nominal:float,dc_to_ac_capacity_ratio:float,lifetime_years:int,
                        u_v:int,u_c:int,hosting_limit:float):
        self.inverter_efficiency_nominal=inverter_efficiency_nominal
        self.dc_to_ac_capacity_ratio=dc_to_ac_capacity_ratio
        self.lifetime_years=lifetime_years
        self.u_v=u_v
        self.u_c=u_c
        self.hosting_limit=hosting_limit
    
    def set_degradation_rate(self,degradation_rate:float):
        self.degradation_rate=degradation_rate