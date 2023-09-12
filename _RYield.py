import numpy as np
import warnings
import biosteam as bst 
from biosteam import Unit
from biosteam.units.decorators import cost

@cost(basis='Infeed', ID= 'reactor', units='tonnes/day', S= 500, CE=567.5, cost=8766341.78, n=0.6, BM=4.28)

class RYield(bst.Unit):
    _N_ins = 1
    _N_outs = 1
    _N_heat_utilities = 0

    _units= {'Infeed': 'tonnes/day',
                'Duty': 'kJ/hr'}

    def __init__(self, ID='', ins=(), outs=(), yields=None, T=600+273.15,factor = 1,wt_closure=100, *args, **kwargs):
        bst.Unit.__init__(self, ID, ins, outs, bst.settings.get_thermo())
        self._multistream = bst.MultiStream(None, thermo=bst.settings.get_thermo())
        self._multistream.T = T
        self.T = T
        self.factor = factor
        self.yields = yields
        self.wt_closure = wt_closure
        

    # def _setup(self):    This keep leading to some error about set up. Questions for mark afterwards
    #     pass

    def _run(self):
        feed = self.ins[0]
        vap = self.outs[0]
        mass = feed.get_total_flow(units='kg/hr') - feed.get_flow('kg/hr', 'N2') - feed.get_flow('kg/hr','O2') * self.wt_closure/100  # Yields are based on the mass of the feed stream, not including the mass of the fluidizing gas (N2)

        ms = bst.Stream(None, thermo=feed.thermo)
        for c, y in self.yields.items():
            if c != 'N2':
                try:
                    ms.set_flow(mass * y, "kg/hr", c)
                except:
                    print(c)
                    pass
            elif c == 'N2':
                ms.set_flow(feed.get_flow('kg/hr', 'N2'), "kg/hr", c)
        ms.set_flow(feed.get_flow('kg/hr', 'Sand'), "kg/hr", 'Sand')    # Sand is inert and does not react
        vap.copy_flow(ms)
        vap.T = self.T
        vap.P = feed.P
        vap.phase = 'g'
        ms.empty()

    def _design(self):
        duty= self.H_out - self.H_in
        self.design_results['Infeed'] = self.ins[0].get_flow("tonnes/day","HDPE")  * self.factor # Autothermal pyrolysis requires smaller reactor 2/5 Polin et al. 2019
        # self.add_heat_utility(duty, T_in=self.ins[0].T)
        pass