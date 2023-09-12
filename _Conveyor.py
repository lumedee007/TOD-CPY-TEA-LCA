import numpy as np
import warnings
import biosteam as bst 
from biosteam import Unit
from biosteam.units.decorators import cost

@cost(basis='feed', ID= 'Conveyor', units='tonnes/day', S= 500, CE=567.5, cost= 297661.70, n=0.6, BM=4.28)

# %% Import necessary modules
class Conveyor(bst.Unit):
    _N_ins = 2
    _N_outs = 2
    _N_heat_utilities = 0


    _units= {'feed': 'tonnes/day',
                'Duty': 'kJ/hr'}

    def __init__(self, ID='', ins=(), outs=(), *args, **kwargs):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=bst.settings.get_thermo())
        self._multistream.T = T
        self.T = T
        self.P = P

    def _run(self):
        feed_one = self.ins[0]
        feed_two = self.ins[1]
        out_one = self.outs[0]
        out_two = self.outs[1]
        out_one.copy_like(feed_one)
        out_two.copy_like(feed_two)

        feed_one.T = out_one.T
        feed_one.P = out_one.P
        feed_two.T = out_two.T
        feed_two.P = out_two.P
    
    def _design(self):
        duty= self.H_out - self.H_in
        self.design_results['feed'] = self.ins[0].get_flow("tonnes/day","HDPE")  * self.factor # Autothermal pyrolysis requires smaller reactor 2/5 Polin et al. 2019
        # self.add_heat_utility(duty, T_in=self.ins[0].T)
        pass
