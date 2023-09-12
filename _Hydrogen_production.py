# %%
import numpy as np
import warnings
import biosteam as bst 
import thermosteam as tmo
from biosteam import Unit
from biosteam.units.decorators import cost



# Cost basis from Jones et al 2009 24.5MMScfd is 70.1M USD, 33.4 MMScfd == 7620 lbs == 3456.5 kg/hr. 
# Hence 1MMscfd == 100.48 kg/hr at hydrocracking conditions. for costing; base 24.5MMscfd == 2461.66 kg/hr

@cost(basis='Infeed', ID= 'reactor', units='kg/hr', S= 2461.66, CE=525.4, cost=70100000, n=0.6)
# smr.purchase_costs = {"Hydrogen_production": (70100000 * (hydrogenPSA.outs[0].get_total_flow("m3/day")/283168.466)**0.6) * (bst.CE/525.4)} 

class SteamReformer(bst.Unit):
    _N_ins = 3
    _N_outs = 3
#     _N_heat_utilities = 0

    _units= {'Infeed': 'kg/hr',
                'Duty': 'kJ/hr',
                'Power': 'kW'}   
    def __init__(self, ID='', ins=(), outs=(), T=300+273.15, *args, **kwargs):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=bst.settings.get_thermo())
        self._multistream.T = T
        self.T = T

    def _run(self):
        natural_gas = self.ins[0]
        water = self.ins[1]
        smr_catalyst = self.ins[2]

        natural_gas_out = self.outs[0]
        water_out = self.outs[1]
        smr_catalyst_out = self.outs[2]

        natural_gas_out.copy_like(self.ins[0])
        water_out.copy_like(self.ins[1])
        smr_catalyst_out.copy_like(self.ins[2])

        natural_gas_out.T,water_out.T,smr_catalyst_out.T = self.ins[0].T,self.ins[1].T,self.ins[2].T
        natural_gas_out.P,water_out.P,smr_catalyst_out.P = 30*self.ins[0].P,30*self.ins[1].P,self.ins[2].P



    def _design(self):
        duty = self.H_out - self.H_in
#   hyd_prod = 27420512.8   #MM scfd      hyd_prod_power = 5875,rate = 0.00021425565753824998 per 1MM Scf per 28316.8466 m3/
# 28316.8466 cubic meter == 1MM scf requires 12 KWh of electricity 

        rate = 12  # 12KW per MMscfd of H2 produced 
        hyd_req = bst.Stream('Hydrogen',H2=1, P = 30*self.ins[1].P, phase = 'l')
        hyd_req.set_total_flow(self.ins[1].get_total_flow(units = "kg/hr")/2, units = "kg/hr")
        hyd_required = hyd_req.get_total_flow(units = "kg/hr")  # 0.0475800032291919 kwh/gal of product from Wenqin spreadsheet   Gracida alvarez et al. 2019 
        smr_power = rate  * hyd_required/28316.8466 
        
        self.design_results['Power'] = smr_power
        self.design_results['Infeed'] = hyd_req.get_total_flow(units = "kg/hr")
        
        self.add_power_utility(smr_power)
        pass
