import biosteam as bst 
import thermosteam as tmo
from biosteam.units.decorators import cost

@cost(basis= 'flow_in', ID= 'Compressor', units='kmol/hr',S=521.9, CE=567.5, cost=17264.08, n=0.6, BM=3.3) #CE 2017

# @cost(basis='Total flow', ID='Compressor', units='kmol/hr',
#       # 17264.08 for (613+39.5) metric tonne/hr CO2
#       kW=17264.08/((613+39.5)*1000/44)*(24123*0.1186),
#       cost=5.08e6, S=24123, CE=CEPCI_by_year[2009], n=0.6, BM=3.3)
class Compressor(bst.Unit):
    
    _N_ins = 1
    _N_outs = 1
    _N_heat_utilities = 0

    _units= {'flow_in': 'kmol/hr',
                'Duty': 'kJ/hr'}

    def __init__(self, ID='', ins=(), outs=(), phase= 'g', thermo=None, *,
                 P=101325, Q=0, eta=0.8, isentropic=False):
        bst.Unit.__init__(self, ID, ins, outs, thermo)
        self.P = P
        self.Q = Q
        self.eta = eta
        self.isentropic = isentropic
        self.phase = phase

    def _run(self):
        self.outs[0].copy_like(self.ins[0])
        self.outs[0].T = 273.15 + 30
        self.outs[0].P = self.P
        self.outs[0].phase = self.phase
    
    def _design(self):
        self.design_results['flow_in'] = self.outs[0].F_mol
        
