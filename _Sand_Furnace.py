import numpy as np
import warnings
import biosteam as bst 
from biosteam import Unit
from biosteam.units.decorators import cost

@cost(basis='duty', ID= 'Furnace', units='kJ/hr', S= 74588e3, CE=567.5, cost=1566589.78, n=0.6, BM=4.28)

class Combustor(bst.Unit):
    _N_ins = 4
    _N_outs = 1
#     _N_heat_utilities = 0

    _units= {'Infeed': 'tonnes/day',
                'duty': 'kJ/hr'}

    def __init__(self, ID='', ins=(), outs=(), T_out=1000+273.15, *args, **kwargs):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=bst.settings.get_thermo())
        self._multistream.T = T_out
        self.T = T_out

    # def _setup(self):    This keep leading to some error about set up. Questions for mark afterwards
    #     pass

    def _run(self):
        sand_in = self.ins[0]
        sand_out = self.outs[0] 
        sand_out.copy_like(self.ins[0])
        sand_out.T = self.T

## TODO:
# Add a stream to represent the flue gas from the furnace
# Add a stream to represent the make up-sand to the furnace


        
# Assume natural gas is used for initial heating of the reactors
# Flue gas from the process is used to maintain process heat. 
# Cost of initial natural gas needed is negligible
        


#         mass = sand_in.get_total_flow(units='kg/hr') - feed.get_flow('kg/hr', 'N2') - feed.get_flow('kg/hr','O2')    # Yields are based on the mass of the feed stream, not including the mass of the fluidizing gas (N2)



    def _design(self):
        reactor_duty= self.H_out - self.H_in
        self.design_results['duty'] = reactor_duty
        self.design_results['Infeed'] = self.ins[0].get_flow("tonnes/day","HDPE") * 0.4 # Autothermal pyrolysis requires smaller reactor 2/5 Polin et al. 2019
#         self.add_heat_utility(duty, T_in=self.ins[0].T, T_out= self.outs[0].T)
        pass