import numpy as np
import warnings
import biosteam as bst 
from biosteam import Unit
import thermosteam as tmo
from biosteam.units.decorators import cost

# REF[1]; BM =1 because it is installed cost
@cost(basis= 'flowrate', ID= 'Cyclone', units='tonnes/day',S=500, CE=567.5, cost=982510.7, n=0.6, BM=4.28) #CE 2017
class Cyclone(Unit):
    _N_ins = 1
    _N_outs = 2
    _N_heat_utilities = 0

    _units= {'flowrate': 'tonnes/day',
                'Duty': 'kJ/hr'}

    def __init__(self, ID, ins=(), outs=(), T=298.15, P=101325,efficiency=0.99):
        Unit.__init__(self,ID,ins,outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=self.thermo, phases=['g', 'l', 's'])
        self.T = T
        self.P = P
        self.efficiency = efficiency

    #  Comment out the set up aspect as vapor and solid outputs are not taking the correct phase   
    # def _setup(self):
    #     vapor,solid = self.outs
    #     vapor.phase = 'g'
    #     solid.phase = 's'

    def _run(self):
        feed = self.ins[0]
        vapor,solid = self.outs

        e = self.efficiency
        # vapor.copy_like(feed)
        # solid.copy_like(feed)

        ms=self._multistream
        ms.imol['g'] = feed.mol
        # ms.copy_like(feed)

        for k in ms.available_chemicals:
            # if k in chemical_groups['InsolubleSolids']:  
            if str(k) in ['Ash','Sand','Char']:
                solid.imol[ str(k)] = ms.imol['g', str(k)]* 1    #self.efficiency
                vapor.imol[ str(k)] = ms.imol['g',  str(k)]* 0    #(1-self.efficiency)
            else:
                vapor.imol[ str(k)] = ms.imol['g',  str(k)]

        vapor.phase = 'g'
        solid.phase = 's'

        vapor.T = self.ins[0].T
        vapor.P = self.ins[0].P
        solid.T = self.ins[0].T
        solid.P = self.ins[0].P
        ms.empty()
    
    def _design(self):
        self.design_results['flowrate'] = self.ins[0].get_total_flow("tonnes/day")
        pass





    


