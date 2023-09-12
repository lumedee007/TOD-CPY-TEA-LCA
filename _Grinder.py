import numpy as np
import warnings
import biosteam as bst 
from biosteam import Unit
from biosteam.units.decorators import cost

# REF[1]; BM =1 because it is installed cost
@cost(basis='Grinder_feed', ID= 'Grinder', units='tonnes/day',S=500, CE=550.8, cost=616710.94, n=0.6, BM=1)  
class Grinder(bst.Unit):
    """
    Calculates crushing cost based on tonnes of feed
    The Grinder electricity requirement is taken from gracida alvarez et al. 300kwh/tonne
    1kwh = 3600kj
    grinder power requirement = 300kwh * tonnes of feed/hr
    """
    _N_ins = 1
    _N_outs = 1
    _N_heat_utilities = 0

    _units= {'Grinder_feed': 'tonnes/day',
            'Power': 'kW',
            'Duty': 'kJ/hr'}
    def __init__(self, ID, ins=(), outs=(), T=298.15, P=101325):
        # this section is called first when the unit is created/simulated
        # initialize default values for the all units
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())

        # we use an internal multistream to do internal calculations 
        self._multistream = bst.MultiStream(None, thermo=self.thermo) 
        self.T = T 
        self.P = P

    # def _setup(self):
    #     # setup is called second after the unit is created
    #     pass       

    def _run(self):
        # This Grinder just allow the plastic to pass through without
        #  doing anything for now because I don't know how to work the particle sizes yet
        ins = self.ins[0]
                
        out = self.outs[0]
        out.copy_like(ins)
        out.T = self.T
        out.P = self.P  
                
    def _design(self):
        duty = self.H_out - self.H_in
        Grinder_electricity = 300 * self.ins[0].get_total_flow("tonnes/hr") # 300kwh/tonne   Gracida alvarez et al. 2019 
        
        self.design_results['Grinder_feed'] = self.ins[0].get_flow("tonnes/day","HDPE")
        self.design_results['Duty'] = duty
        self.design_results['Power'] = Grinder_electricity
        
        # self.add_heat_utility(duty, self.ins[0].T)
        self.add_power_utility(Grinder_electricity)
        pass