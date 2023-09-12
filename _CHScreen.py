import numpy as np
import warnings
import biosteam as bst 
from biosteam import Unit
from biosteam.units.decorators import cost

@cost(basis='screenfeed', ID= 'Screen', units='tonnes/day',S=500, CE=550.8, cost=39934.31  , n=0.6, BM=1)  # REF[1]; BM =1 because it is installed cost
class Screen(bst.Unit):
    """
    Screens the input feed
    """
    _N_ins = 1
    _N_outs = 2
    _N_heat_utilities = 0

    _units= {'screenfeed': 'tonnes/day',
                'Duty': 'kJ/hr'}

    def __init__(self, ID, ins=(), outs=(), T=298.15, P=101325, screen_size=0.01):
        # this section is called first when the unit is created/simulated
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo()) # initialize default values for the all units
        self._multistream = bst.MultiStream(None, thermo=self.thermo) # we use an internal multistream to do internal calculations
        self.T = T 
        self.P = P
        self.screen_size = screen_size

    # def _setup(self):
    #     # setup is called second after the unit is created
    #     pass       

    def _run(self):
        # This crusher just allow the plastic to pass through without doing anything for now because I don't know how to work the particle sizes yet
        ins = self.ins[0]
                
        finely_crushed, recycled_feed  = self.outs
        finely_crushed.copy_like(ins)
        recycled_feed.copy_like(ins)
        finely_crushed.T = self.T
        recycled_feed.T = self.T
        finely_crushed.P = self.P
        recycled_feed.P = self.P

        # TODO: Add the screening here when PSD is available
        # This is where we would do the screening but no PSD yet so we just use percentages here; to work on later.

        screened_total_flow = ins.get_total_flow('kg/hr') * 99/100  # Assuming 99% efficiency of crusher
        finely_crushed.set_total_flow(screened_total_flow, 'kg/hr')
        recycled_feed.set_total_flow(ins.get_total_flow('kg/hr') - screened_total_flow, 'kg/hr')
                
    def _design(self):
        self.design_results['screenfeed'] = self.ins[0].get_flow("tonnes/day","HDPE")
        pass