import numpy as np
import warnings
import biosteam as bst 
import thermosteam as tmo
from biosteam import Unit
from biosteam.units.decorators import cost

@cost(basis='Infeed', ID= 'reactor', units='bbl/day', S= 2250, CE=468.2, cost=30e6, n=0.65, BM=1)

class Hydrocrack(bst.Unit):
    _N_ins = 3
    _N_outs = 3

    _units= {'Infeed': 'bbl/day',
                'Duty': 'kJ/hr',
                'Power': 'kW'}   
    def __init__(self, ID='', ins=(), outs=(),reaction = None, T=300+273.15, *args, **kwargs):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=bst.settings.get_thermo())
        self._multistream.T = T
        self.T = T
        self.reaction = reaction

    def _run(self):
        feed = self.ins[0]
        hydrogen = self.ins[1]
        catalyst = self.ins[2]
        self.outs[0].copy_like(self.ins[0])
        self.outs[1].copy_like(self.ins[1])
        self.outs[2].copy_like(self.ins[2])
        self.outs[0].T,self.outs[1].T,self.outs[2].T = self.ins[0].T,self.ins[1].T,self.ins[2].T
        self.outs[0].P,self.outs[1].P,self.outs[2].P = self.ins[0].P,self.ins[1].P,self.ins[2].P


    def _design(self):
        duty = self.H_out - self.H_in
        hydrocracking_power = 6.9* self.ins[0].get_total_flow(units = "bbl/hr") # 6.9KWh/bbl input Refinning Processes, Conoco Phillips
        
        self.design_results['Power'] = hydrocracking_power
        self.design_results['Infeed'] = self.ins[0].get_total_flow(units = "bbl/day")
        
        self.add_power_utility(hydrocracking_power)
        # self.add_heat_utility(unit_duty, T_in)
        pass