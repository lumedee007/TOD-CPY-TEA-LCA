import biosteam as bst
from _compounds import *
bst.settings.set_thermo(compounds)
# Find reference for utility agents in literature 

# Gas_utility = bst.UtilityAgent('natural_gas', T=1000, P=101325, T_limit=1200, Water=1, heat_transfer_efficiency=0.85)
Gas_utility = bst.UtilityAgent(ID='steam',
            phase='g',
            T=1000,
            P= 101325.0,
            units= None, 
            thermo=None, 
            T_limit= 1200, 
            heat_transfer_price=1.32e-05, 
            regeneration_price=0, 
            heat_transfer_efficiency=0.9,
            water=1)


# liq_utility = bst.UtilityAgent('water', T=75, P=101325, T_limit=1200, Water=1, heat_transfer_efficiency=0.85)
Liq_utility = bst.UtilityAgent(ID='super_hot_water',
            phase='l',
            T=75,
            P= 101325.0 * 3,
            units= None, 
            thermo=None, 
            T_limit= 1200, 
            heat_transfer_price=1.32e-05, 
            regeneration_price=0, 
            heat_transfer_efficiency=0.9,
            water=1)

# liq_utility = bst.UtilityAgent('water', T=75, P=101325, T_limit=1200, Water=1, heat_transfer_efficiency=0.85)
NH3_utility = bst.UtilityAgent(ID='ammonia',
            phase='l',
            T=0,
            P= 101325.0 * 3,
            units= None, 
            thermo=None, 
            T_limit= 1200, 
            heat_transfer_price=1.32e-05, 
            regeneration_price=0, 
            heat_transfer_efficiency=0.9,
            water=1)
