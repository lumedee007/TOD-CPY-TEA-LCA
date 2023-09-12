import numpy as np
import warnings
import biosteam as bst 
from biosteam import Unit
from biosteam.units.decorators import cost

# REF[1]; BM =1 because it is installed cost from ref [Gracida Alvarez, 2019]
@cost(basis='feed', ID= 'Conveyor_hopper', units='tonnes/day',S=500, CE=596.2, cost=236452.39 + 297661.70, n=0.6, BM=1)  #297,661.70 is for the hopper and 236,452.39 is for the conveyor
class Feed_handling(bst.Unit):
    """
    Calculates cost of conveyors and hoppers based on tonnes of feed
    """
    _N_ins = 1
    _N_outs = 1
    _N_heat_utilities = 0

    _units= {'feed': 'tonnes/day',
                'Duty': 'kJ/hr',
                'Power': 'kW'}
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
        # This crusher just allow the plastic to pass through without
        #  doing anything for now because I don't know how to work the particle sizes yet
        ins = self.ins[0]
                
        out = self.outs[0]
        out.copy_like(ins)
        out.T = self.T 
        out.P = self.P  
                
    def _design(self):
        duty = self.H_out - self.H_in
        feed_handling_electricity = 0 # Assuming no electricity for feed handling for now. Electrity for conveyor and 
        
        self.design_results['feed'] = self.ins[0].get_flow("tonnes/day","HDPE")
        self.design_results['Duty'] = duty
        self.design_results['Power'] = feed_handling_electricity
        
        self.add_heat_utility(duty, self.ins[0].T)
        self.add_power_utility(feed_handling_electricity)
        # We should probably do something here to calculate the operating cost of the crusher
        pass