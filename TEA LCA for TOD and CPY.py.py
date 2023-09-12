# %% Import necessary modules
import time
import math
import pandas as pd
import numpy as np

import biosteam as bst 
import thermosteam as tmo
from thermo import SRK
#  import compounds and set thermo  
from _compounds import *
from _Hydrocracking_Unit import *
from _Hydrogen_production import *



from _Grinder import *
from _CHScreen import *
from _RYield import *
from _Cyclone import *
from _Sand_Furnace import *
from _UtilityAgents import *    # Created heat utilities that can heat to high temperatures and cool to sub zero temperatures 
from _process_yields import *
from _Compressor import *
from _feed_handling import *
from _teapyrolysis import *
from _tea_wax_mfsp import *
from _pass_unit import *
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.size': 14})

bst.nbtutorial() # Light-mode html diagrams and filter warnings

# Set CEPCI to year of analysis to be 2020
bst.settings.CEPCI = 596.2 # CEPCI 2021 = 708, 2020 = 596.2, 2019	= 607.5

for c in compounds:
    c.default()

# compounds["CO2"].Cn.l.add_method(71, Tmin=-700, Tmax=120)

bst.HeatUtility().cooling_agents.append(NH3_utility)
bst.HeatUtility().heating_agents.append(Liq_utility)
bst.HeatUtility().heating_agents.append(Gas_utility)


# PREFERENCES
bst.preferences.update(flow='kg/hr', T='degK', P='Pa', N=100, composition=True)
 
#  Prices 
actual_prices = {
"HDPE": 25.05/1000, # $/kg from 22 per MT, because feed is defined per MT
"Ethylene": 0.61, # Gracida Al
"Propylene":0.97, # $/kg
"Butene": 1.27,# Butene 1.27 $/kg from Yadav et al. 2023
"Naphtha": 0.86,  # Gracida Alvarez et al
"Diesel": 0.84,  # Gracida Alvarez et al
"Wax": 0.3, #   1989 USD/MT   source: https://www.chemanalyst.com/Pricing-data/paraffin-wax-1205
"NG": 7.40 * 1000 * 1.525/28316.8, 
"Hydrocracking catalyst": 15.5 * 2.20462262,      #15.5 $/lb 2.20462262 is factor to convert to $/kg from Jones et al. 2009 PNNL report SRI international 2007
"Hydrotreating catalyst": 15.5 * 2.20462262,      #15.5 $/lb from Jones et al. 2009 PNNL report SRI international 2007
"Hydrogen plant catalyst": 3.6/885.7,      #3.6 /1000scf/28.317m3/885.71kg 2007 quote from Jones et al. 2009 PNNL report SRI international 2007
"Hydrogen": 2.83      #2.83 USD/kg from Gracida Alvarez et al. 2.1 from Borja Hernandez et al. 2019
}
bst.settings.electricity_price = 0.065 # Gracida Alvarez et al

#  Create dictionaries to store various technologies information
#  NAtural gas required for furnace activity = 2.2 GJ/tonne of HDPE from Gracida Alvarez
#  44.1 MJ/kg of natural gas; 1 GJ =  MJ; 1 tonne = 1000 kg;2.2 GJ/49.887 kg of natural gas
# Jessica report %wt closure 92.7% for CPY, 97% for TOD.
# Jessica assumes equivalent ratio of 7% Oxygen by volume, Means mass closure for TOD in products would be97.231*93/100 assuming oxygen is fully used up and ends up in pyrolysis products 
cpy = {"Technology":"CPY","Hydrocracking": "No", "Yield": cpy_comp_yield,"Reactor size" : 1,"wt_closure": 92.5, "NG_req":2.0,"residence_time" :"low"}
cpy_hc = {"Technology":"CPY","Hydrocracking": "Yes", "Yield": cpy_comp_yield,"Reactor size" : 1,"wt_closure": 92.5, "NG_req":2.0,"residence_time" : "low"}
tod = {"Technology":"TOD","Hydrocracking": "No", "Yield": tod_comp_yield, "Reactor size" : 0.4,"wt_closure":90.4, "NG_req":0.0,"residence_time" :"low"}
tod_hc = {"Technology":"TOD","Hydrocracking": "Yes", "Yield": tod_comp_yield,"Reactor size" : 0.4,"wt_closure":90.4, "NG_req":0.0,"residence_time" :"low"}
hrt = {"Technology":"CPY","Hydrocracking": "No", "Yield": hrt_comp_yield, "Reactor size" : 1, "wt_closure": 92.5, "NG_req":2.0,"residence_time" :"high"}
hrt_hc = {"Technology":"CPY","Hydrocracking": "Yes", "Yield": hrt_comp_yield,"Reactor size" : 1,"wt_closure": 92.5, "NG_req":2.0,"residence_time" :"high"}

scenarios = [cpy,cpy_hc,tod,tod_hc,hrt,hrt_hc]
scenarios_labels = ["CPY","CPY-HC","TOD","TOD-HC","HRT","HRT-HC"]
plant_capacity = 250 # tonnes per day
capacity = plant_capacity
scenario = scenarios[4]
irr = 0.1


#  %% Create streams
def run_scenario(scenario = cpy,capacity=plant_capacity,prices=actual_prices):
    bst.main_flowsheet.set_flowsheet("Plastic Pyrolysis" + time.strftime("%Y%m%d-%H%M%S"))
    # Feed stream, HDPE plastic 
    feed = bst.Stream('HDPE_Feed',
                        HDPE=1,
                        units='kg/hr',
                        T = 298,
                            price = prices['HDPE']/1000  # 22 $/MT; divide by 1000 to get $/kg 
                            )

    feed_mass = capacity             # 250 tonnes per dat    test was 143.435 # kg/hr
    feed.set_total_flow(feed_mass, 'tonnes/day')
    feed.price = prices['HDPE']  # 22 $/MT; divide by 1000 to get $/kg

    # Natural gas and water for hydrogen production and furnace 
    sand_stream = bst.Stream('sand', Sand=100, T=25 + 273.15, P=101325, phase='s')
    natural_gas = bst.Stream('natural_gas', CH4=100, T=25 + 273.15, P=101325, phase='g')
    comb_nat_gas = bst.Stream('comb_nat_gas', CH4=100, T=25 + 273.15, P=101325, phase='g')
    natural_gas.price = prices["NG"]
    comb_nat_gas.price = prices["NG"]
    water = bst.Stream('water',H2O = 100, T=25 + 273.15, P=101325, phase='l')

    # Oxygen for autothermal pyrolysis at 7% equivalence ratio
    pyrolysis_oxygen = bst.Stream('pyrolysis_oxygen',O2=1,units='kg/hr',T=298,price=0.000)
    oxygen_mass = 0.07 * feed_mass * 100/93   # 7% equivalence ratio from Polin et al. 2019
    pyrolysis_oxygen.set_total_flow(oxygen_mass, 'kg/hr')

    # fluidizing gas for the reactor
    fluidizing_gas = bst.Stream('fluidizing_gas',N2=1,units='kg/hr',T=298,price=0.000)
    fluidizing_gas_mass = 15   # fluidizing gas is 20kg/hr for now
    fluidizing_gas.set_total_flow(fluidizing_gas_mass, 'kg/hr')



    recycle = bst.Stream('recycle')
    char_sand = bst.Stream('S108')
    CRHDPE = bst.Stream('S104')
    rec_NCG = bst.Stream('S235')
    hydrocracked = bst.Stream('Cracked_HC')

    ref_Methane = bst.Stream('Methane_ref',Methane=1,units='kg/hr',T= 298,price=0.000)
    ref_Methane.set_total_flow(911*2,units="kg/hr")
    ref_Methane.T = 273.15 - 90

    ref_Methane2 = bst.Stream('Methane_ref2',Methane=1,units='kg/hr',T= 298,price=0.000)
    ref_Methane2.set_total_flow(911*2,units="kg/hr")
    ref_Methane2.T = 273.15 - 90

    ref_ethane = bst.Stream('ethane_ref',Ethane=1,units='kg/hr',T= 298,price=0.000)
    ref_ethane.set_total_flow(911,units="kg/hr")
    ref_ethane.T = 273.15 - 50



    ref_Tetrafluoroethane = bst.Stream('Tetrafluoroethane_ref',Tetrafluoroethane=1,units='kg/hr',T= 298,price=0.000)
    ref_Tetrafluoroethane.set_total_flow(250,units="kg/hr")
    ref_Tetrafluoroethane.T = 273.15 - 50

    ref_Propane = bst.Stream('Propane_ref',Propane=1,units='kg/hr',price=0.000)
    ref_Propane.set_total_flow(250,units="kg/hr")
    ref_Propane.T = 273.15 - 50

    ref_Propene = bst.Stream('Propene_ref',Propene=1,units='kg/hr',T= 298,price=0.000)
    ref_Propene.set_total_flow(1402,units="kg/hr")
    ref_Propene.T = 273.15 - 50
    ref_Propene.P = 1 * 101325
    ref_Propene.phase = 'g'


    HC_hydrogen = bst.Stream('Hydrogen',H2=1,units='kg/hr',T= 298,price=prices["Hydrogen"])


# 2.2 GJ of natural gas per tonne of HDPE needed for combustion
# 49.88 kg of NG need for 1 GJ of energy assuming 44.1 MJ/kg of NG

    #--------------------------------------------------------------------------------------------------------------
    # Pretreatment & Pyrolysis
    #--------------------------------------------------------------------------------------------------------------
    with bst.System('sys_pretreatment') as sys_pretreatment:
        # Pretreatment
        handling = Feed_handling('Handling',ins=feed,outs=("S102"))
        M1 = bst.units.Mixer('Mixer',ins = [handling-0,recycle])     # Mix for feed and recycled NCG stream
        grinder = Grinder('Grinder',ins=[M1-0],outs="S103")       #crush the feed
        CHscreen = Screen("CHScreen",ins=grinder-0,outs=[CRHDPE,recycle]) # screen the feed
        if scenario['Technology'] == "CPY":

            comb_nat_gas.set_total_flow(scenario["NG_req"] * 26.68 * feed.get_total_flow("tonne/hr"),units="m3/hr")
            # comb_nat_gas.set_total_flow(scenario["NG_req"] *49.88* feed.get_total_flow("tonne/hr"),units="kg/hr")
            furnace = Combustor("furnace", ins=[comb_nat_gas,sand_stream,rec_NCG,char_sand],outs=('S105'))
            M2 = bst.units.Mixer('Mixer2',ins = [CRHDPE,pyrolysis_oxygen,fluidizing_gas,furnace-0]) #mix oxygen, fluidizing gas and feed

            reactor = RYield('CFB_Reactor',ins=M2-0,outs=("S106"),yields=scenario["Yield"],factor= scenario["Reactor size"],wt_closure=scenario["wt_closure"])
            # separate the gas and solids in products stream
            Cyclone1 = Cyclone('Cyclone1',ins= reactor-0,outs=['S107',char_sand],efficiency=0.99)
        elif scenario["Technology"] == "TOD":
            M2 = bst.units.Mixer('Mixer2',ins = [CRHDPE,pyrolysis_oxygen,fluidizing_gas,rec_NCG]) #mix oxygen, fluidizing gas and feed

            reactor = RYield('CFB_Reactor',ins=M2-0,outs=("S106"),yields=scenario["Yield"],factor= scenario["Reactor size"],wt_closure=scenario["wt_closure"])
            # separate the gas and solids in products stream
            Cyclone1 = Cyclone('Cyclone1',ins= reactor-0,outs=['S107',"S108"],efficiency=0.99)
        cooler1 = bst.units.HXutility('cooler', ins=Cyclone1-0, outs='S109', T=273.15 +10, rigorous=False) # rigorous = False ignores VLE calculations


    #--------------------------------------------------------------------------------------------------------------
    # product fractionation 
    #--------------------------------------------------------------------------------------------------------------

    with bst.System('sys_Product_Fractionation') as sys_product_fractionation:
        F1 = bst.units.Flash('Condenser', ins=cooler1-0, outs=('S201','S239'), P=101325, T = (cooler1-0).T)     

        H7 = bst.HXutility('Heater7',ins = F1-1, outs=("S232"),T = 273.15 + 150, rigorous=False)
        F3 = bst.units.Flash('FlashSeparator', ins= H7-0, outs=("S233","S234"), P= 1.01*101.325 ,T=273.15) # T = (heater4-0).T)
        K1 = bst.units.IsentropicCompressor('Compressor1',ins=F1-0,outs=("S202"),P = 2 * 101325, eta=0.8)

#         # # Reduce temperature of gas stream to 30C and then use refrigeration cycle to reduce to -40 C
        H2 = bst.units.HXutility('Heater2',ins=K1-0,outs=("S203"),T=273.15 + 30, rigorous=False)
 
        H3 = bst.HXprocess('evaporator_ref', ins = (ref_Propane,H2-0),outs=("","S204"), U=1000, phase0='g')
        H3_K = bst.units.IsentropicCompressor('compressor_ref',ins = H3-0,P=2 * 101325)
        H3_Con = bst.units.HXutility('condenser_ref', H3_K-0,T=273.15 - 50, V=1)
        H3_Exp = bst.units.IsenthalpicValve('expansion_device', H3_Con-0,outs=ref_Propane,P=1 * 101325)

#         # Compress the gaseous stream to 7 bars
        K2 = bst.units.IsentropicCompressor('Compressor2',ins=H3-1,outs=("S205"),P = 7 * 101325, eta=0.8) # originally 7 

        H4 = bst.HXprocess('evaporator_ref2', ins = (ref_ethane,K2-0),outs = ("","S206"), U=1000, phase0='g',T_lim1=273.15-50)
        # H3 = bst.HXprocess('evaporator_ref', ins = (ref_Propene,olu), U=1000, phase0='g',T_lim0=273.15-40)
        H4_K = bst.units.IsentropicCompressor('compressor_ref2',ins = H4-0,P=2 * 101325)
        H4_Con = bst.units.HXutility('condenser_ref2', H4_K-0,T=273.15 - 50, V=1)
        H4_Exp = bst.units.IsenthalpicValve('expansion_device2', H4_Con-0,outs=ref_ethane,P=1 * 101325) 


        H5 = bst.HXprocess('evaporator_ref3', ins = (ref_Methane,H4-1),outs=("","S207"), U=1000, phase0='g',T_lim1=273.15-80)
        # # H3 = bst.HXprocess('evaporator_ref', ins = (ref_Propene,olu), U=1000, phase0='g',T_lim0=273.15-40)
        H5_K = bst.units.IsentropicCompressor('compressor_ref3',ins = H5-0,P=2 * 101325)
        H5_Con = bst.units.HXutility('condenser_ref3', H5_K-0,T=273.15 - 50, V=1)
        H5_Exp = bst.units.IsenthalpicValve('expansion_device3', H5_Con-0,outs=ref_Methane,P=1 * 101325) 

        H5_2 = bst.HXprocess('evaporator_ref4', ins = (ref_Methane2,H5-1),outs=("","S208"), U=1000, phase0='g',T_lim1=273.15-90)
        H5_K2 = bst.units.IsentropicCompressor('compressor_ref3',ins = H5_2-0,P=2 * 101325)
        H5_Con2 = bst.units.HXutility('condenser_ref3', H5_K2-0,T=273.15 - 50, V=1)
        H5_Exp2 = bst.units.IsenthalpicValve('expansion_device3', H5_Con2-0,outs=ref_Methane2,P=1 * 101325) 


        F2 = bst.units.Flash('Condenser2', ins=H5_2-1, outs=("S210","S209"), P= (H5_2-1).P,T=273.15 - 110) # T = (heater4-0).T)

        P1 = bst.units.Pump('Pump',ins=F2-1,outs=("S211"),P = 25 * 101325) # 25 bars
        H6 = bst.HXutility('Heater6',ins = P1-0, outs=("S212"),T = 273.15 +2, rigorous=False)


        D1 = bst.units.BinaryDistillation('De_ethanizer', ins=H6-0,
                                outs=('S213',"S214"),   # ethylene
                                LHK=('C2H4', 'C3H8'),
                                y_top=0.99, x_bot=0.01, k=2,
                                is_divided=True)     #  (97.2% purity)
        D1.check_LHK = False

        D1_spl = bst.units.Splitter("EthyleneFractionator",ins=(D1-0),outs=("S215","S216"), split={'C2H4':0.99,'CO2':0.10,'C3H8':0.05,'O2':1,'CO':1,'H2':1})
        D1_spllMx = bst.Mixer('D1_spplMX', ins = D1_spl-0,outs= ("Ethylene"))
        ethyleneOut = (D1_spl-0)


        ethyleneOut = (D1-0)
        H8 = bst.HXutility('Heater8',ins = D1-1, outs=("S217"),T = 273.15 +100, rigorous=False)
        D2 = bst.units.BinaryDistillation('Depropanizer', ins=H8-0,
                                outs=('S218','S219'),   # propylene
                                LHK=('C3H8', 'C4H8'),
                                y_top=0.99, x_bot=0.01, k=2,
                                is_divided=True)
        H9 = bst.HXutility('Heater9',ins = D2-0, outs=("S220"),T = 273.15 +70, rigorous=False)
        KD2 = bst.units.IsentropicCompressor('CompressorD2',ins=H9-0,outs=("S221"),P = 22 * 101325, eta=0.8) # 25 bars
        D2_spl = bst.units.Splitter("PropyleneFractionator",ins=(KD2-0),outs=("S222","S223"), split={'C3H8':0.99,'C2H4':1,'C3H8':0.05,'O2':1,'CO':1,'H2':1})
        D2_spllMx = bst.Mixer('D2_spplMX', ins = D2_spl-0,outs= ("Propylene"))
        propyleneOut = (D2_spl-0)  

        M3 = bst.Mixer('Mixer3',ins = [F3-0,D2-1],outs=("S224"))    #,D2_spl-1,D1_spl-1])
        Mrec = bst.Mixer('Mixer_rec',ins = [D2_spl-1,F2-0,D1_spl-1],outs=rec_NCG)    #,D2_spl-1,D1_spl-1])
        D3 = bst.units.BinaryDistillation('Debutanizer', ins=M3-0,
                                outs=('S225','S226'),
                                LHK =('C4H8','C10H22'),      #=('C10H22', 'C14H30'),
                                y_top=0.99, x_bot=0.01, k=2,
                                is_divided=True)
        D3_mx = bst.Mixer('D3_MX',ins = D3-0,outs=("Butene"))
        buteneOut = (D3-0)


        if scenario['Hydrocracking'] == "No":          
            if scenario['residence_time'] == "high":
                D4 = bst.units.BinaryDistillation('NaphthaSplitter', ins=D3-1,
                                        outs=('S227','S228'),
                                        LHK =('C10H22','C14H30'),      #=('C10H22', 'C14H30'),
                                        y_top=0.99, x_bot=0.01, k=2,
                                        is_divided=True)
                D4_mx = bst.Mixer('D4_MX',ins = D4-0,outs=("Naphtha"))
                Mdiesel = bst.Mixer('MixerDiesel',ins = D4-1,outs=("S229"))     #,D2_spl-1,D1_spl-1]) 
                Md_mx = bst.Mixer('MixerDiesel_mx',ins = Mdiesel-0,outs=("Diesel"))   
                Mwax = bst.Mixer('Mwax',ins = F3-1, outs = ("S236"))
                Mwax_mx = bst.Mixer('Mwax_mx',ins = Mwax-0, outs = ("Wax"))

                naphthaOut1 = (D4-0)                  
                dieselOut = (Mdiesel-0)
                waxOut = Mwax-0
            else:   
                D4 = bst.units.BinaryDistillation('NaphthaSplitter', ins=D3-1,
                                        outs=('S227',"S228"),
                                        LHK =('C10H22','C14H30'),      #=('C10H22', 'C14H30'),
                                        y_top=0.99, x_bot=0.01, k=2,
                                        is_divided=True)
                D4_mx = bst.Mixer('D4_MX',ins = D4-0,outs=("Naphtha"))
                naphthaOut1 = (D4-0)   

                D5 = bst.units.BinaryDistillation('DieselSplitter', ins=D4-1,
                                    outs=('S229','S230'),
                                    LHK =('C14H30','C24H50'),      #=('C10H22', 'C14H30'),
                                    y_top=0.99, x_bot=0.01, k=2,
                                    is_divided=True)
                D5_mx = bst.Mixer('D5_MX',ins = D5-0,outs=("Diesel"))
                dieselOut1 = (D5-0)
                M4 = bst.Mixer('Mixer4',ins = [F3-1,D5-1], outs = ("S236"))
                M4_mx = bst.Mixer('Mixer4_mx',ins = M4-0, outs = ("Wax"))
                waxOut = (M4-0)

        elif scenario['Hydrocracking'] == "Yes":
            D4 = bst.units.BinaryDistillation('NaphthaSplitter', ins=D3-1,
                        outs=('S227',"S228"),
                        LHK =('C10H22','C14H30'),      #=('C10H22', 'C14H30'),
                        y_top=0.99, x_bot=0.01, k=2,
                        is_divided=True)  
            if scenario['residence_time'] == "low":
                D5 = bst.units.BinaryDistillation('DieselSplitter', ins=D4-1,
                                        outs=('S229','S230'),
                                        LHK =('C14H30','C24H50'),      #=('C10H22', 'C14H30'),
                                        y_top=0.99, x_bot=0.01, k=2,
                                        is_divided=True)
                M4 = bst.Mixer('Mixer4',ins = [F3-1,D5-1],outs=())

    #--------------------------------------------------------------------------------------------------------------
    # Hydrogen production 
    #--------------------------------------------------------------------------------------------------------------
    if scenario['Hydrocracking'] == "Yes":
        # with bst.System('sys_Hydrogen_Production') as sys_hydrogen_production:
        #     smr_catalyst = bst.Stream('H2_production_catalyst',Nickel_catalyst = 1 , units='kg/hr')
        #     smr_catalyst.price = prices["Hydrogen plant catalyst"]

        #     smr_pre = SteamReformer("Steam_Reformer", ins = (natural_gas,water,smr_catalyst),outs=())
        #     M5 = bst.units.Mixer('Mixer5',ins=(smr_pre-0,smr_pre-1),outs=())
        #     smr = bst.units.MixTank('Hydrogen_production', ins=(M5-0),outs=('H2andCO2'))
        #     hydrogenPSA = bst.units.Splitter("PSA",ins=(smr-0),outs=("","Other_Gases"), split={'H2':0.99,})  
    #     ["","Other gases"]
    #--------------------------------------------------------------------------------------------------------------
    # Hydrocracking Unit 
    #--------------------------------------------------------------------------------------------------------------
    # Hydrocracking catalyst calculation (reactor 1  + reactor 2)/(catalyst life year * feed (MT/day) * 365 * stream factor)
    # Hydrocracker details from Dutta et al. 2015. Liquid feed = 16,654 lb/hr;Total H2 feed = 2109 lb/hr; H2 purity = 90%, Make up H2 pure = 647 lb/hr,
    # Power in KW/hr for hydroprocessing 1811, hydrocracking electrucak cpnsumption 369kw, recycle compressor = 31
   
        with bst.System('sys_Hydrocracking') as sys_Hydrocracking:
            K3 = Compressor('Compressor3',ins=HC_hydrogen,outs=("S301"),P = 89.7 * 101325, eta=0.8) # 25 bars            
            hydrocracking_catalyst = bst.Stream('hydrocracking_catalyst',Zeolite = 1 , units='lb/hr')
            hydrocracking_catalyst.set_total_flow(200,"kg/hr")
            hydrocracking_catalyst.price = prices["Hydrocracking catalyst"]            
            
            if scenario['residence_time'] == "low":
                hydro_crack = Hydrocrack("Hydrocracking",ins=(M4-0,K3-0,hydrocracking_catalyst))
            else:
                hydro_crack = Hydrocrack("Hydrocracking",ins=(F3-1,K3-0,hydrocracking_catalyst))

            hydrocrack = bst.units.MixTank('Hydrocracking_Unit', ins=(hydro_crack-0,hydro_crack-1),outs=()) #hydrocracking_catalyst),outs=())
            splitter1 = bst.units.Splitter("H2split",ins=(hydrocrack-0),outs=("ExcessH2"), split={'H2':0.99,})
            H2excess = (splitter1-0)
            # cat_monitor = bst.units.Mixer('cat_monitor',ins=(hydrocracking_catalyst-0),outs=('outlet'))

            D6 = bst.units.BinaryDistillation('NaphthaSplitter2', ins=splitter1-1,
                                    outs=("S302",""),
                                    LHK =('C10H22','C14H30'),      #=('C10H22', 'C14H30'),
                                    y_top=0.99, x_bot=0.01, k=2,
                                    is_divided=True)
        
            D7 = bst.units.BinaryDistillation('DieselSplitter2', ins=D6-1,
                                    outs=("S303","S304"),
                                    LHK =('C14H30','C24H50'),      #=('C10H22', 'C14H30'),
                                    y_top=0.99, x_bot=0.01, k=2,
                                    is_divided=True)
            D7_mx = bst.Mixer('D7_MX',ins = D7-1,outs=("Wax"))

            waxOut = (D7-1)

# Consolidate product streams
        M6 = bst.units.Mixer('mix_Naphtha_out',ins=(D4-0,D6-0),outs=("Naphtha"))
        naphthaOut = (M6-0)

        if scenario['residence_time'] == "low":
            M7 = bst.units.Mixer('mix_Diesel_out',ins=(D5-0,D7-0),outs=("Diesel"))
            dieselOut = (M7-0)
        else:
            M7 = bst.units.Mixer('mix_Diesel_out',ins=(D4-1,D7-0),outs=("Diesel"))
            dieselOut = (M7-0)

    #  Create system
    sys = bst.main_flowsheet.create_system('sys')

    #  Include specifications
    def check_flash1():
        try:
            F1._run()
            # print("flash1 run successful")    
        except:
            # print("flash1 failed")
            pass
        top = F1.outs[0].copy()
        bottom = F1.outs[1].copy()
        flash_in = F1.ins[0].copy()
        for chem in top.available_chemicals:
            if str(chem) in ["O2","CO", "H2","CH4"] and chem.Tb < 273.15 + 10:
                F1.outs[0].imass[chem.ID] = flash_in.imass[chem.ID] * 0.999
                F1.outs[1].imass[chem.ID] = flash_in.imass[chem.ID] * (1-0.999)

            elif str(chem) in ["C2H4"] and chem.Tb < 273.15 + 10:
                F1.outs[0].imass[chem.ID] = flash_in.imass[chem.ID] * 0.989
                F1.outs[1].imass[chem.ID] = flash_in.imass[chem.ID] * (1-0.989)

            elif str(chem) in ["CO2"] and chem.Tb < 273.15 + 10:
                F1.outs[0].imass[chem.ID] = flash_in.imass[chem.ID] * 0.9877
                F1.outs[1].imass[chem.ID] = flash_in.imass[chem.ID] * (1-0.9877)

            elif str(chem) in ["C3H8"] and chem.Tb < 273.15 + 10:
                F1.outs[0].imass[chem.ID] = flash_in.imass[chem.ID] * 0.92
                F1.outs[1].imass[chem.ID] = flash_in.imass[chem.ID] * (1-0.92)
            
            elif str(chem) in ["C4H8"] and chem.Tb < 273.15 + 10:
                F1.outs[0].imass[chem.ID] = flash_in.imass[chem.ID] * 0.69
                F1.outs[1].imass[chem.ID] = flash_in.imass[chem.ID] * (1-0.69)

            elif str(chem) in ["C10H22"] and chem.Tb > 273.15 + 10:
                F1.outs[0].imass[chem.ID] = flash_in.imass[chem.ID] * (1-0.9964)
                F1.outs[1].imass[chem.ID] = flash_in.imass[chem.ID] * 0.9964

            elif str(chem) in ["C14H30","C24H50", "C40H82"] and chem.Tb >= 273.15 + 10:
                F1.outs[0].imass[str(chem)] = flash_in.imass[str(chem)] * 0.00
                F1.outs[1].imass[str(chem)] = flash_in.imass[str(chem)] * 1
            else:
                F1.outs[0].imass[str(chem)] = flash_in.imass[str(chem)] * 0.00
                F1.outs[1].imass[str(chem)] = flash_in.imass[str(chem)] * 1            
        F1.outs[0].P = F1.outs[1].P = flash_in.P
        F1.outs[0].T = F1.outs[1].T = 273.15 + 15     #  flash_in.T
        F1.outs[0].phase = 'g'
        F1.outs[1].phase = 'l'

    F1.add_specification(check_flash1)

    def check_flash2():
        try:
            for x in range(0,5):
                F2._run()    
        except:
            # print("flash2 failed")
            top = F2.outs[0].copy()
            bottom = F2.outs[1].copy()
            flash_in = F2.ins[0].copy()
            for chem in top.chemicals:
                if chem.Tb < (heater4-0).T: # 273.15 - 136:
                    F2.outs[0].imass[str(chem)] = flash_in.imass[str(chem)] * 0.99
                    F2.outs[1].imass[str(chem)] = flash_in.imass[str(chem)] * 0.01
                else:
                    F2.outs[0].imass[str(chem)] = flash_in.imass[str(chem)] * 0.01
                    F2.outs[1].imass[str(chem)] = flash_in.imass[str(chem)] * 0.99
            F2.outs[0].P = F2.outs[1].P = flash_in.P
            F2.outs[0].T = F2.outs[1].T = flash_in.T
            F2.outs[0].phase = 'g'
            F2.outs[1].phase = 'l'
    F2.add_specification(check_flash2)


    def check_flash3():
        try:
            F3._run()
            # print("F3 run successfully")
        except:
            # print ("F3 failed")
            pass
        # print("flash3 fixing outs")
        top = F3.outs[0].copy()
        bottom = F3.outs[1].copy()
        flash_in = F3.ins[0].copy()
        # F3.T = flash_in.T
        for chem in top.available_chemicals:
            if str(chem) in ["O2","CO","CO2","H2","CH4","C2H4", "C3H8","C4H8"] and chem.Tb < 580:
                F3.outs[0].imass[chem.ID] = flash_in.imass[chem.ID] * 1
                F3.outs[1].imass[chem.ID] = flash_in.imass[chem.ID] * 0

            elif str(chem) in ["C10H22","C14H30"] and chem.Tb < 580:
                F3.outs[0].imass[chem.ID] = flash_in.imass[chem.ID] * 0.95
                F3.outs[1].imass[chem.ID] = flash_in.imass[chem.ID] * 0.05

            else:
                F3.outs[0].imass[chem.ID] = flash_in.imass[chem.ID] * 0.05
                F3.outs[1].imass[chem.ID] = flash_in.imass[chem.ID] * 0.95
        F3.outs[0].P = F3.outs[1].P = flash_in.P
        F3.outs[0].T = F3.outs[1].T = flash_in.T
        F3.outs[0].phase = 'g'
        F3.outs[1].phase = 'l'
    F3.add_specification(check_flash3)
    #--------------------------------------------------------------------------------------------------------------
    # Hydrogen production
    #--------------------------------------------------------------------------------------------------------------
    if scenario['Hydrocracking'] == "Yes":

        hydrocracking_reaction = tmo.ParallelReaction([
        tmo.Reaction('C24H50 + 1.4H2 -> 2.4C10H22',  reactant='C24H50',  X=0.49),
        tmo.Reaction('C24H50 + 2.858H2 -> 2.4C14H30',  reactant='C24H50',  X=0.49),
        tmo.Reaction('C40H82 + 3H2 -> 4C10H22',  reactant='C40H82',  X=0.49),
        tmo.Reaction('C40H82 + 1.857H2 -> C14H30',  reactant='C40H82',  X=0.49),  
        ])  
        def hc_reaction():
            rxn=hydrocracking_reaction
            hydrocrack._run()
            rxn(hydrocrack.outs[0])
        hydrocrack.add_specification(hc_reaction)

        # def smr_reaction():
        #     rxn=tmo.Reaction('CH4 + H2O -> CO + 3H2',reactant = 'CH4',X=0.6)
        #     smr.run()
        #     rxn(smr.outs[0])

        # smr.add_specification(smr_reaction)

        def K3_ins():
            H2_req = 2*((0.0252 * hydro_crack.ins[0].get_flow("kg/hr", "C24H50")) +  (0.025 * hydro_crack.ins[0].get_flow("kg/hr", "C40H82")))   # from  Production of gasoline and diesel from biomass via fast pyrolysis, hydrotreating and hydrocracking: a design case... Jones et al 2009
            K3.ins[0].set_flow(H2_req,"kg/hr","H2")
            # water.set_flow(2*3 * H2_req *1/0.6 ,"kg/hr","H2O")    #= water_req multiply by 3 to produce excess H2
            # natural_gas.set_flow(2.67 * H2_req * 1/0.6,"kg/hr","CH4")  # multiply by 2.67 to produce excess H2
            # Ni_catalyst_req = H2_req   # catalyst cost Jones et al. 2009 3.6 $/1000 scf/28.3168466m3/885.71 kg of H2 {1scf = 0.0283168466 m3; 1000scf = 28.3168466 }
            # H2_req = 450 * D5.outs[1].get_total_flow("bbl/hr")* 0.18  #0.18 bbl = 1 scf  this is in barrels/hr
            # water.set_flow(3/3 * H2_req * 3.72965 * 1 ,"kg/hr","H2O")    #= water_req 0.6 representing 60% conversion
            # # natural_gas.set_flow(2.67/3 * H2_req * 3.72965 * 1,"kg/hr","CH4")     
            # Ni_catalyst_req = H2_req   # Confirm catalyst makeup
            # smr_catalyst.set_flow(Ni_catalyst_req,"kg/hr","Nickel_catalyst")
            K3._run()
        K3.add_specification(K3_ins)

    #--------------------------------------------------------------------------------------------------------------
    # Hydrocracking 
    #--------------------------------------------------------------------------------------------------------------
        #calculate the amount of catalyst needed for hydrocracking and hydrogen production

        # (12*Chemical("H2").MW)/(5*Chemical("C24H50").MW) = 0.07100591715976332
        # 1kg of C24H50 requires 0.07100591715976332 of H2
        # (4*Chemical("H2").MW)/(Chemical("C40H82").MW) = 0.014319973858809155
        # 1kg of C40H82 requires 0.014319973858809155 of H2
        #  Excess hydrogen is needed in the hydrocracking unit ina ratio of like 1 mole of HC to about 2-4 mole of H2. I will 
        # assume 3 moles of H2 for this study
        # mass of H2 needed for hydrocracking = 3 * (hydrocrack.ins[0].get_flow("kg/hr","C24H50")*0.07100591715976332 + hydrocrack.ins[0].get_flow("kg/hr","C40H82")*0.014319973858809155) =1025.2906444333576
        # 
        def catalyst_calc():
            catalyst_density = 420 # lb/ft3
            reactor_volume = 0.65 # LHSV
            stream_flow = hydro_crack.ins[0].get_total_flow("gal/hr")
            catalyst_life = 1    # catalyst lifetime years
            stream_factor = 0.9  # stream factor
            reactor_one = catalyst_density/(reactor_volume * 7.4802) * stream_flow       # reactor 1 volume m
            reactor_two = 0
            # print (f"{feed_mass}")
            # hydrocracking_catalyst_req = (reactor_one +reactor_two)/(catalyst_life * feed_mass * 365 * stream_factor) # lb/MT of feed
            # hydrocracking_catalyst.set_flow(hydrocracking_catalyst_req * feed.get_total_flow("tonnes/hr"),"lb/hr","Zeolite")

            hydrocracking_catalyst_req = (reactor_one +reactor_two)/(catalyst_life * feed_mass * 365 * stream_factor) # lb/MT of feed
            # hydrocracking_catalyst_req = 6.7
            hydrocracking_catalyst.set_flow(hydrocracking_catalyst_req * feed.get_total_flow("tonnes/hr"),"lb/hr","Zeolite")
            #             
            # hydrocracking_catalyst.set_flow(25,"lb/hr","Zeolite")
            #    # catalyst requirement in lb/hr
            hydro_crack.run()
        hydro_crack.add_specification(catalyst_calc)            

        # print (f"{hydrocracking_catalyst.get_total_flow('lb/hr')} is the catalyst flow rate")
        #--------------------------------------------------------------------------------------------------------------
 


    for stream in sys.products:
        try:
            stream.price = prices[str(stream)]
        except:
            pass

    sys.simulate()
    #  Set the price of hydrocracking and hydrogen production
    if scenario['Hydrocracking'] == "Yes":

        # D6.purchase_costs = {"NaphthaSplitter2": 0}
        # D6.installed_costs = {"NaphthaSplitter2":0}
        # D7.purchase_costs = {"DieselSplitter2": 0}
        # D7.installed_costs = {"DieselSplitter2":0}

        hydrocrack.purchase_costs = {"Hydrocrackng_Unit_mix":0} 
        hydrocrack.installed_costs = {'Tank':0}

    # Check if the two flash units are unable to set the price of Heat exchanger - Floating head unit in the flash. I am scaling the cost based on the input   
    flash_probs = [F1,F2]
    for unit in flash_probs:
        if math.isnan(unit.purchase_cost):
            unit.purchase_costs['Heat exchanger - Floating head'] = 4698.2 * (unit.ins[0].get_total_flow("kmol/hr")/22)**0.65    
            unit.installed_costs['Heat exchanger - Floating head'] = unit.F_BM['Heat exchanger - Floating head'] * unit.purchase_costs['Heat exchanger - Floating head']
    #   Heat exchanger units also have issues estimating the floating head price so i approximate 
    prob_units = [cooler1, H3, H4, H5]
    for unit in prob_units:
        if math.isnan(unit.purchase_cost):
            unit.purchase_costs['Floating head'] = 4698.2 * (unit.ins[0].get_total_flow("kmol/hr")/22)**0.65    
    if math.isnan(D3.installed_cost):
        D3.installed_costs = {}
        D3.installed_costs = {"Distillation_column":324295 * (D3.ins[0].get_total_flow("kg/hr")/685)**0.65}
        D3.purchase_costs = {}
        D3.purchase_costs = {"Distillation_column":324295 * (D3.ins[0].get_total_flow("kg/hr")/685)**0.65}

    return sys

run_scenario(scenarios[1])
#  %% 
# all_scen = []
# for i, scen in enumerate(scenarios):
#     try:
#         print(f"trying {scenarios_labels[i]}")
#         system = run_scenario(scen)
#         # system.save_report(f"Scenario_{scenarios_labels[i]}_report.xlsx")
#         print(f"***********************************\n {scenarios_labels[i]} ran succesfully \n ***********************************")
#         all_scen.append(system)
#     except:
#         print(f"***********************************\n {scenarios_labels[i]} failed \n {scenarios_labels[i]} failed \n {scenarios_labels[i]} failed \n ***********************************")
#     print("-------------------------------")
#     print("-------------------------------")
# %%


# %%
#--------------------------------------------------------------------------------------------------------------
# Economic Analysis
#----------------------------------------------------------------------------------------------------------------
employee_costs = {
    "Plant Manager":[ 159000,  1],
    "Plant Engineer":[ 94000,  1],
    "Maintenance Supr":[ 87000,  1],
    "Maintenance Tech":[ 62000,  6],
    "Lab Manager":[ 80000,  1],
    "Lab Technician":[ 58000,  1],
    "Shift Supervisor":[ 80000,  3],
    "Shift Operators":[ 62000,  12],
    "Yard Employees":[ 36000,  4],
    "Clerks & Secretaries":[ 43000,  1],
    "General Manager":[188000, 0]
} # Labor cost taken from Dutta 2002 and adjusted using the U.S. Bureau of Labor Statistics. Number of staff required gotten from Yadav et al.  
#  US BLS (http://data.bls.gov/cgi-bin/srgateCEU3232500008)

labor_costs = sum([
    employee_costs[v][0]* employee_costs[v][1]  for v in employee_costs
            ])
print(f"Labor cost: {labor_costs}")
# %%
# %% TEA component

#--------------------------------------------------------------------------------------------------------------
# Economic Analysis: TEA code for MSP
#----------------------------------------------------------------------------------------------------------------

facility_outputs = ["Ethylene","Propylene","Butene","Naphtha","Diesel","Wax"]

all_systems = []
for scen_label, scenario in enumerate(scenarios):
    print(f"Running scenario {scen_label+1}: {scenarios_labels[scen_label]} of {len(scenarios)} scenarios")
    system = run_scenario(scenario)
    system.save_report(f"Scenario_{scenarios_labels[scen_label]}_report.xlsx")
    all_systems.append(system)

tea_msp = TEA_MFSP(
    system=all_systems[0],
    IRR=0.1,
    duration=(2020, 2040),
    depreciation="MACRS7",
    income_tax=0.21,
    operating_days=333,
    lang_factor=5.05,  # ratio of total fixed capital cost to equipment cost
    construction_schedule=(0.4, 0.6),
    WC_over_FCI=0.05,  # working capital / fixed capital investment
    labor_cost=labor_costs,
    fringe_benefits=0.4,  # percent of salary for misc things
    property_tax=0.001,
    property_insurance=0.005,
    supplies=0.20,
    maintenance=0.003,
    administration=0.005,
    finance_fraction=0.4,
    finance_years=10,
    finance_interest=0.07,
)
# # %%
# msp = tea_msp.solve_price(all_systems[0].flowsheet.unit.data["Mixer4"].outs[0])
# msp
# print(f"Minimum selling price of Wax for Conventional Pyrolysis: {msp:.3f} USD/kg")
# # %%
# print(tea_msp.installed_equipment_cost)
# %% Conventional pyrolysis and hydrocracking 
msp_cpy = tea_msp.solve_price(all_systems[0].flowsheet.stream.data["Wax"])
msp_cpy
print(f"Minimum selling price of Wax for Conventional Pyrolysis: {msp_cpy:.3f} USD/kg")

#  Conventional pyrolysis and hydrocracking
msp_cpy_hc = tea_msp.solve_price(all_systems[1].flowsheet.stream.data["Naphtha"])
msp_cpy_hc
print(f"Minimum selling price of Naphtha for Conventional Pyrolysis: {msp_cpy_hc:.3f} USD/kg")
#  Thermal-oxodegradation 
msp_oxo = tea_msp.solve_price(all_systems[2].flowsheet.stream.data["Wax"])
msp_oxo
print(f"Minimum selling price of Wax for Thermal-oxodegradation: {msp_oxo:.3f} USD/kg")
#  Thermal-oxodegradation and hydrocracking
msp_oxo_hc = tea_msp.solve_price(all_systems[3].flowsheet.stream.data["Naphtha"])
msp_oxo_hc  
print(f"Minimum selling price of Naphtha for Thermal-oxodegradation: {msp_oxo_hc:.3f} USD/kg")

#  High residence time
msp_hrt = tea_msp.solve_price(all_systems[4].flowsheet.stream.data["Naphtha"])
msp_hrt
print(f"Minimum selling price of Naphtha for High residence time: {msp_hrt:.3f} USD/kg")

#  High residence time and hydrocracking
msp_hrt_hc = tea_msp.solve_price(all_systems[5].flowsheet.stream.data["Naphtha"])
msp_hrt_hc
print(f"Minimum selling price of Naphtha for High residence time: {msp_hrt_hc:.3f} USD/kg")

# %% plot the minimum selling price of the different scenarios against the same products from fossil products

labels = ["CPY\nWax", "TOD\nwax", "CPY-HC\nNaphtha", "TOD-HC\nNaphtha", "HRT\nNaphtha", "HRT-HC\nNaphtha", "Fossil\nNaphtha"]
values = [msp_cpy, msp_oxo, msp_cpy_hc, msp_oxo_hc, msp_hrt, msp_hrt_hc,actual_prices['Naphtha']]
# %%
df_msp = pd.DataFrame({"labels":labels,"values":values})
df_msp.to_excel("Results/Minimum selling price.xlsx")

# %%
colors = ['blue'] * (len(labels) - 1) + ['red']  # Set last bar to red

# Create a bar chart
plt.figure(figsize=(9, 7))
plt.bar(labels, values, color=colors)

# Add labels and title
plt.xlabel("Products")
plt.ylabel("Prices($/kg)")
plt.title("Minimum selling price of products from different scenarios")

# Show the plot
plt.xticks(rotation= 0)  # Rotate x-axis labels for better readability
plt.tight_layout()

plt.savefig("Results/Images/MSP_all_scenarios.png",dpi=300,bbox_inches="tight")

plt.show()
# %%

# **********************************************************************************************************************
# Economic Analysis: TEA code for NPV
# **********************************************************************************************************************


facility_outputs = ["Ethylene","Propylene","Butene","Naphtha","Diesel","Wax"]
products_streams ={ "Ethylene": "Ethylene",
                    "Propylene": "Propylene",
                    "Butene": "Butene",
                    "Naphtha": "Naphtha",
                    "Diesel": "Diesel",
                    "Wax": "Wax",
}

def run_TEA(system,products = facility_outputs,irr = 0.1, lf = 5.05,prices= actual_prices, duration = (2020, 2040)):
    tea = TEA(system=system,
             IRR= irr,
             duration= duration,
             depreciation='MACRS7',
             income_tax=0.21,
             operating_days=333,
             lang_factor= lf, # ratio of total fixed capital cost to equipment cost
             construction_schedule=(0.4, 0.6),
             WC_over_FCI=0.05, #working capital / fixed capital investment
             labor_cost=labor_costs,
             fringe_benefits=0.4,# percent of salary for misc things
             property_tax=0.001,
             property_insurance=0.005,
             supplies=0.20,
             maintenance=0.003,
             administration=0.005,
             finance_fraction = 0.4,
             finance_years=10,
             finance_interest=0.07)

    sorted_equipment = sorted(system.units, key=lambda x: x.installed_cost)

    equipment_costs = []
    purchase_costs = []
    for unit in sorted_equipment:
        
        equipment_costs.append([unit.ID, unit.installed_cost])
        purchase_costs.append([unit.ID, unit.purchase_cost])
    
    annual_yield = [system.flowsheet.stream[prod].get_total_flow("kg/year") for prod in products]
    annual_revenue = [system.flowsheet.stream[prod].get_total_flow("kg/year") * prices[prod] for prod in products]
    npv = tea.NPV
    mfsp_table = tea.mfsp_table()
    return (purchase_costs,equipment_costs,mfsp_table,tea,annual_revenue,annual_yield)
# **********************************************************************************************************************
# LCA
# **********************************************************************************************************************

EF = {'Diesel' :4423.19681,    # for 1 cubic meter of diesel
'Electricity':0.65228,
'Gasoline':2339.06178,         # for 1 cubic meter of gasoline
'Natural Gas':0.241,
'Heat_NG': 0.069,
'Steam Production':0.12,
'Transport':0.165,
'Water for cooling':0.00018,
'Hydrogen': 9.34445 #EF for 1 kg H2 used for hydrocracking
}

def run_GWP(syst,df_emi = EF):
    sys_labels = ["Feedstock Collection","Pretreatment & Pyrolysis","Product Fractionation", "Hydrocracking"]
    system_emissions = dict(zip(sys_labels,np.zeros(len(sys_labels))))

    waste_coll_diesel =  248.48/(500/24)/850 # 1. waste collection fuel = 248.48/500 kg/tonne REF Gracida Alvarez et al. 2019; EF is in m3, divide by 850 to convert kg to m3
    MRF_electricity = 286.67/(500/24) # 2. HDPE MRF electricity = 286.67/500 kwh per tonne REF Gracida Alvarez et al. 2019 
    MRF_heat = 541.67/(500/24) # 3. HDPE MRF heat = 541.67/500 MJ/tonne REF Gracida Alvarez et al. 2019
    MRF_diesel = 12.38/(500/24)/850 # 4. HDPE MRF diesel = 12.38/500 kg/tonne REF Gracida Alvarez et al. 2019
    MRF_gasoline = 2.02/(500/24)/748.9 # 5. HDPE MRF gasoline = 2.02/500 kg/tonne REF Gracida Alvarez et al. 2019 
    HDPE_transportation= 1041.67/(500/24) # 6. HDPE transport to facility = 1041.67/500tkm REF Gracida Alvarez et al. 2019
    feed_hr = syst.flowsheet.stream.data["HDPE_Feed"].get_total_flow("tonnes/hr")
    system_emissions["Feedstock Collection"] = (waste_coll_diesel*df_emi["Diesel"] + MRF_electricity*df_emi["Electricity"] + MRF_heat*df_emi["Heat_NG"] + MRF_diesel*df_emi["Diesel"] + MRF_gasoline*df_emi["Gasoline"] + HDPE_transportation*df_emi["Transport"]) * feed_hr # tonnes per day
    
    waste_processing = (waste_coll_diesel*df_emi["Diesel"] + MRF_electricity*df_emi["Electricity"] + MRF_heat*df_emi["Heat_NG"] + MRF_diesel*df_emi["Diesel"] + MRF_gasoline*df_emi["Gasoline"]) * feed_hr
    #  Hydrogen production (per MMscfd H2 produced) and Hydrocracking (per bbl feed)
    
    if scenario['Hydrocracking'] == "No":
        system_emissions["Hydrocracking"] = 0
        H2_prod = 0
        # HP_nat_gas = 0
        HC_diesel = 0
        HC_electricity = 0
        # HP_electricity = 0
        # HP_electricity_hr = HP_electricity*H2_prod # electricity required per hour

    else:
        HC_feed = syst.flowsheet.unit.data["Hydrocracking"].ins[0].get_total_flow("bbl/hr")
        hydrogen_feed = syst.flowsheet.unit.data["Hydrocracking"].ins[1].get_total_flow("kg/hr")
        HC_diesel = 5.3 * HC_feed #Fuel oil, kg 5.3 kg per barrel feed REF Refining Processes 2004 pg 94
        HC_electricity = 6.9 * HC_feed # HC_electricity = 6.9kWh per barrel
        # HC_cooling_water = 0.64 # HC_cooling_water = 0.64 m3 per barrel
        system_emissions["Hydrocracking"] = HC_diesel/850 * df_emi["Diesel"] + HC_electricity * df_emi["Electricity"] + hydrogen_feed * df_emi["Hydrogen"] #+ HC_cooling_water * df_emi["Water for cooling"]

    #  Pyrolysis and pretreatment
    PY_elect = sum([unit.net_power for unit in syst.flowsheet.system.data["sys_pretreatment"].units])
    
    if scenario['Technology'] == "CPY":
        sand_heat = syst.flowsheet.unit.data["furnace"].ins[0].get_total_flow("kg/hr") 
    else:
        sand_heat = 0
    purge_comb = syst.flowsheet.unit.data["Condenser2"].outs[0].get_total_flow("kg/hr")
    system_emissions["Pretreatment & Pyrolysis"] =  PY_elect*df_emi["Electricity"] + sand_heat*df_emi["Heat_NG"] + purge_comb*df_emi["Heat_NG"]
    
    # Product fractionation
    PF_elect = sum([unit.net_power for unit in syst.flowsheet.system.data["sys_Product_Fractionation"].units])
    system_emissions["Product Fractionation"] = PF_elect*df_emi["Electricity"]

# Sensitivity analysis
    waste_processing = (waste_coll_diesel*df_emi["Diesel"] + MRF_electricity*df_emi["Electricity"] + MRF_heat*df_emi["Heat_NG"] + MRF_diesel*df_emi["Diesel"] + MRF_gasoline*df_emi["Gasoline"])
    purge = (purge_comb*df_emi["Heat_NG"])/feed_hr
    other_emission = waste_processing + purge
    #  Hydrogen production (per MMscfd H2 produced) and Hydrocracking (per bbl feed)

    waste_transport = HDPE_transportation 
    electricity_req = (PY_elect + PF_elect)/feed_hr    # + HP_electricity_hr 
    diesel_req = (HC_diesel)/feed_hr
    # natural_gas_req = HP_nat_gas/feed_hr
    nat_gas_for_sand = sand_heat/feed_hr


    sensitivity_factors = {"Waste Transport":waste_transport,"Electricity":electricity_req,"Diesel":diesel_req,"Natural Gas for Sand":nat_gas_for_sand} 
    return (system_emissions, sensitivity_factors,other_emission)

# **********************************************************************************************************************
# Sensitivity Analysis
# **********************************************************************************************************************

sensitivity_analysis_variables = [ "Fixed Capital Investment","Internal rate of return","Feedstock cost","Hydrocracking catalyst cost",
                                    "Electricity cost","Facility capacity","Ethylene price","Propylene price",
                                    "Butene price","Diesel price","Naphtha price","Wax price","hydrogen price"
                                    ]

def get_NPV(lang_factor,IRR,feedstock_cost,hydrocracking_catalyst,
            electricity_cost,facility_capacity,ethylene_price,propylene_price,
            butene_price,diesel_price,naphtha_price,wax_price,hydrogen_price):
    new_price = {"HDPE": feedstock_cost,
            "Ethylene": ethylene_price,
            "Propylene": propylene_price,
            "Butene": butene_price,
            "Naphtha": naphtha_price,
            "Diesel": diesel_price,
            "Wax": wax_price,
            "NG": 7.40 * 1000 * 1.525/28316.8,
            "Hydrocracking catalyst": hydrocracking_catalyst,
            "Hydrogen": hydrogen_price
            }
    capacity = facility_capacity
    bst.settings.electricity_price = electricity_cost
    sys = run_scenario(scenario,capacity=capacity,prices=new_price)
    tonnes = sys.flowsheet.stream.data['HDPE_Feed'].get_total_flow('tonnes/day')
    # print (f"purchase cost: {sys.purchase_cost} at {capacity} tonnes/day for {tonnes}")
    # print(f"electricity cost: {bst.settings.electricity_price}")
    purchase_cost,equipment_cost,mfsp_table,tea,annual_revenue,annual_yield=run_TEA(sys, lf= lang_factor,irr=IRR,prices=new_price)
    return tea.NPV

def create_df(label, l1, l2, l3, cols):
    data = {'Column 1': l1, 'Column 2': l2, 'Column 3': l3}
    df = pd.DataFrame(data, index=label)
    df.columns = cols
    return df
# %%
actual_IRR = 0.1
actual_lf = 5.05
electricity_cost = 0.069
base = np.array([actual_lf,actual_IRR,actual_prices['HDPE'],actual_prices["Hydrocracking catalyst"],
                electricity_cost,plant_capacity,actual_prices["Ethylene"],actual_prices["Propylene"],
                actual_prices["Butene"],actual_prices["Diesel"],actual_prices["Naphtha"],actual_prices["Wax"],
                actual_prices["Hydrogen"]
                ])                
lower_b = 0.8 * base
upper_b = 1.2 * base
# upper_b = np.array([actual_lf * 1.2,
#                 actual_IRR * 1.2,
#                 actual_prices['HDPE'] * 1.2,
#                 actual_prices["Hydrocracking catalyst"] * 1.2,
#                 electricity_cost *1.2,
#                 295,  #300 capacity is throwing error. using 297 instead 
#                 actual_prices["Ethylene"] * 1.2,
#                 actual_prices["Propylene"]* 1.2,
#                 actual_prices["Butene"]* 1.2,
#                 actual_prices["Diesel"]* 1.2,
#                 actual_prices["Naphtha"]* 1.2,
#                 actual_prices["Wax"]* 1.2,
#                 actual_prices["Hydrogen"]* 1.2
#                 ])

# **********************************************************************************************************************
#  
# **********************************************************************************************************************

# Extract the annual yield of each product and save in a dataframe
sys_labels = ["Feedstock Collection","Pretreatment & Pyrolysis","Product Fractionation","Hydrocracking"]
system_emissions = dict(zip(sys_labels,np.zeros(len(sys_labels))))

products = ["Ethylene","Propylene","Butene","Naphtha","Diesel","Wax"]
df_annual_yield = pd.DataFrame(columns=products)
df_annual_revenue = pd.DataFrame(columns=products)
all_systems = []
all_operating_cost = []
all_capital_cost = []
all_purchase_cost = []
all_FCIs = []
all_NPV = []
all_30_years_NPV = []
all_utility_cost = []
all_teas = []
all_GWP = []



# %% 
# olu = 0
for scen_label, scenario in enumerate(scenarios):
    print(f"Running scenario {scen_label+1}: {scenarios_labels[scen_label]} of {len(scenarios)} scenarios")
    system = run_scenario(scenario)
    system.save_report("Results/Reports/"+ scenarios_labels[scen_label] + ".xlsx")
    all_systems.append(system)
    purchase_cost,equipment_cost,mfsp_table,tea,annual_revenue,annual_yield = run_TEA(system)
    all_capital_cost.append(equipment_cost)
    all_purchase_cost.append(purchase_cost)
    all_operating_cost.append(mfsp_table)
    all_FCIs.append(tea.FCI)
    all_NPV.append(tea.NPV)
    df_annual_yield.loc[scenarios_labels[scen_label]] = annual_yield
    df_annual_revenue.loc[scenarios_labels[scen_label]] = annual_revenue
    all_utility_cost.append(tea.utility_cost)
    all_teas.append(tea)

    tea_30 = run_TEA(system, duration= (2020,2050))[3]
    all_30_years_NPV.append(tea_30.NPV)

    GWP = run_GWP(system)
    all_GWP.append(GWP[0])

# **********************************************************************************************************************
# Conduct NPV Sensitivity Analysis for all scenarios
# **********************************************************************************************************************

    npv_mean_case = get_NPV(*(tuple(base)))/1e6
    print(f"npv baseline: ${npv_mean_case:,.2f} MM")
    npv_actual = npv_mean_case * np.ones(len(sensitivity_analysis_variables))

    npv_lowerb = []
    npv_upperb = []
    for i in range(len(sensitivity_analysis_variables)):
        print(f"Working on {sensitivity_analysis_variables[i]}")
        new = base.copy() 
        new[i] = upper_b[i]
        npv_u = get_NPV(*tuple(new))/1e6
        npv_upperb.append(npv_u)

        new = base.copy() 
        new[i] = lower_b[i]
        npv_l = get_NPV(*tuple(new))/1e6
        npv_lowerb.append(npv_l)
        print(f"Worked on {sensitivity_analysis_variables[i]} with upper NPV = {npv_u:,.2f} MM and lower NPV = {npv_l:,.2f} MM and actual NPV = {npv_mean_case:,.2f} MM")
        print("****************************************************************************************")
        print("****************************************************************************************")

    npv_lowerb = np.array(npv_lowerb)
    npv_upperb = np.array(npv_upperb)
    df_sen = create_df(sensitivity_analysis_variables,npv_lowerb,npv_actual,npv_upperb,["Lower","actual","Upper"])
    df_title = "Results/Sensitivity Tables/NPV_sensitivity"+ scenarios_labels[scen_label] + ".xlsx"
    df_sen.to_excel(df_title)

    pairs = zip(np.abs(npv_upperb-npv_actual),npv_lowerb,npv_upperb,npv_actual,sensitivity_analysis_variables)
    sorted_pairs = sorted(pairs)

    tuples = zip(*sorted_pairs)
    l1,l2,l3,l4,l5 = [ list(tuple) for tuple in  tuples]

    plt.figure(figsize=(7,5))
    plt.rcParams['font.size'] = 12
    for row in zip(l2, l3, l4, l5, range(len(sensitivity_analysis_variables))):
        plt.broken_barh([
            (row[0], row[2]-row[0]), 
            (row[2], row[1]-row[2])], 
            (row[4]*6+1, 5), 
            facecolors=('blue','red'))
    plt.xlabel("NPV(MM USD)")
    plt.yticks(ticks = [3.5 + 6*i for i in range(len(l5))],labels = l5)
    plt.title(scenarios_labels[scen_label] + " NPV Sensitivity to Key Parameters")
    plt.grid(True)

    title = "Results/Sensitivity Images/Sensitivity Analysis NPV " + scenarios_labels[scen_label] + ".png" 
    plt.savefig(title,dpi=300,bbox_inches="tight")
    plt.show()

# **********************************************************************************************************************
# Conduct LCA Sensitivity Analysis for all scenarios
# **********************************************************************************************************************
    # sensitivity_factors = {"Waste Transport":waste_transport,"Electricity":electricity_req,"Diesel":diesel_req,"Gasoline":gasoline_req,"Natural Gas":natural_gas_req} 
    
    # waste_transport = HDPE_transportation 
    # electricity_req = HP_electricity_hr + (PY_elect + PF_elect)/feed_hr
    # diesel_req = (HC_diesel)/feed_hr
    # gasoline_req = MRF_gasoline/feed_hr
    # natural_gas_req = HP_nat_gas/feed_hr
    # nat_gas_for_sand = sand_heat/feed_hr
    
    
    sensitivity_var = ["MRF Distance to refinery", "Electricity", "Diesel for product upgrading","Natural gas for process heat"]
    sensitivity_factors = GWP[1]
    base_g = np.array([x for x in sensitivity_factors.values()])
    upper_bg = 0.8 * base_g
    lower_bg = 1.2 * base_g
    other_emissions = GWP[2]
    def sens_GWP(factors,EF):
        return other_emissions + factors[0] * EF["Transport"] + factors[1] * EF["Electricity"]+ factors[2] * EF["Diesel"]/850  + factors[3] *  EF["Heat_NG"]
    
    
    GWP_mean_case = sens_GWP(base_g,EF)
    print(f"GWP baseline: {GWP_mean_case:,.2f} kg CO2-eq")
    GWP_actual = GWP_mean_case * np.ones(len(sensitivity_var))

    GWP_lowerb = []
    GWP_upperb = []

    for i in range(len(sensitivity_var)):
        print(f"Worked on {sensitivity_var[i]}")

        new_g = base_g.copy() 
        new_g[i] = upper_bg[i]
        GWP_u = sens_GWP(new_g,EF)
        GWP_upperb.append(GWP_u)

        new_g = base_g.copy() 
        new_g[i] = lower_bg[i]
        GWP_l = sens_GWP(new_g,EF)
        GWP_lowerb.append(GWP_l)
        print(f"Worked on {sensitivity_var[i]} with upper GWP = {GWP_u:,.2f} kg CO2-eq and lower GWP = {GWP_l:,.2f} kg CO2-eq and actual GWP = {GWP_mean_case:,.2f} kg CO2-eq")
        print("****************************************************************************************")
        print("****************************************************************************************")

    GWPlowerb = np.array(GWP_lowerb)
    GWPupperb = np.array(GWP_upperb)
    df_sen_g = create_df(sensitivity_var,GWPlowerb,GWP_actual,GWPupperb,["Lower","actual","Upper"])
    df_title = "Results/Sensitivity Tables/GWP_sensitivity"+ scenarios_labels[scen_label] + ".xlsx"
    df_sen_g.to_excel(df_title)

    pairs = zip(np.abs(GWPupperb-GWP_actual),GWP_lowerb,GWP_upperb,GWP_actual,sensitivity_var)
    sorted_pairs = sorted(pairs)

    tuples = zip(*sorted_pairs)
    l1,l2,l3,l4,l5 = [ list(tuple) for tuple in  tuples]
    plt.figure(figsize=(7,5))
    plt.rcParams['font.size'] = 12
    for row in zip(l2, l3, l4, l5, range(len(sensitivity_var))):
        plt.broken_barh([
            (row[0], row[2]-row[0]), 
            (row[2], row[1]-row[2])], 
            (row[4]*6+1, 5), 
            facecolors=('blue','red'))
    plt.xlabel("GWP(kg CO2-eq)")
    plt.yticks(ticks = [3.5 + 6*i for i in range(len(l5))],labels = l5)
    plt.title(scenarios_labels[scen_label] + " GWP Sensitivity to Key Parameters")
    plt.grid(True)

    title = "Results/Sensitivity Images/SensitivitySensitivity Analysis GWP " + scenarios_labels[scen_label] + ".png"
    plt.savefig(title,dpi=300,bbox_inches="tight")
    plt.show()
    # olu += 1
    # if olu == 2:
    #     break
# **********************************************************************************************************************

# **********************************************************************************************************************

# %% 
fig, ax = plt.subplots(figsize=(8, 6))
plt.bar(scenarios_labels,[x/1e6 for x in all_NPV],width=0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")#,fontweight ="bold")
plt.ylabel("Net Present Value (MM USD)",fontsize="large",color = "black")#,fontweight ="bold")
plt.savefig("Results/Images/Net Present Value.png",dpi=300,bbox_inches="tight")


# %%
x = np.arange(len(scenarios_labels))
width = 0.4  # Width of the bars

fig, ax = plt.subplots(figsize=(8, 6))

rects1 = ax.bar(x - width/2, [x/1e6 for x in all_NPV], width, label='20 years Facility Lifetime')
rects2 = ax.bar(x + width/2, [x/1e6 for x in all_30_years_NPV], width, label='30 years Facility Lifetime')

ax.set_xlabel("Scenarios", color="black")
ax.set_ylabel("Net Present Value (MM USD)", color="black")

ax.set_xticks(x)
ax.set_xticklabels(scenarios_labels) #, rotation='horizontal')
ax.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.) # (title="Legend")

plt.title("(C) Net Present Value of all Scenarios \n (20 & 30 Years Facility Lifetime)")
plt.savefig("Results/Images/Net Present Value 20 30 years.png",dpi=300,bbox_inches="tight")

plt.show()
# %%
df_NPV = pd.DataFrame({'20-years NPV': [x/1e6 for x in all_NPV],'30-years NPV': [x/1e6 for x in all_30_years_NPV] })
df_NPV.index = scenarios_labels
df_NPV.to_excel("Results/NPV table.xlsx")



# %% 
fig, ax = plt.subplots(figsize=(8, 6))
plt.bar(scenarios_labels,[x/1e6 for x in all_NPV],width=0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")#,fontweight ="bold")
plt.ylabel("Net Present Value (MM USD)",fontsize="large",color = "black")#,fontweight ="bold")
plt.title("(C) Net Present Value of all Scenarios")
plt.savefig("Results/Images/Net Present Value.png",dpi=300,bbox_inches="tight")


# %%

groups = {"Pretreatment & Pyrolysis":['Handling','Mixer','Grinder',
                                    'CHScreen','Mixer2','CFB_Reactor',
                                    'Cyclone1','furnace','cooler'],
        "Product Fractionation Unit": ['Condenser','Heater7','FlashSeparator','Compressor1',
                                        'Heater2','evaporator_ref','compressor_ref','condenser_ref',
                                        'expansion_device','Compressor2','evaporator_ref2',
                                        'compressor_ref2','condenser_ref2','expansion_device2',
                                        'evaporator_ref3','compressor_ref3','condenser_ref3','evaporator_ref4',
                                        'expansion_device3','Condenser2','Pump','Heater6',
                                        'De_ethanizer','EthyleneFractionator','Depropanizer','PropyleneFractionator',
                                        'Heater8','CompressorD2', 'Heater9','Mixer3','Debutanizer','NaphthaSplitter',
                                        'DieselSplitter','Mixer4','NaphthaSplitter2','DieselSplitter2'],
        "Hydrocracking Unit": ['Compressor3','Hydrocracking','Hydrocracking_Unit','H2split'],
        "Others":[]
}

# groups = {"Pretreatment & Pyrolysis":['Handling','Mixer','Grinder',
#                                     'CHScreen','Mixer2','CFB_Reactor',
#                                     'Cyclone1','furnace','cooler','Condenser'],
#         "Product Fractionation Unit": ['Heater7','FlashSeparator','Compressor1',
#                                         'Heater2','evaporator_ref','compressor_ref','condenser_ref',
#                                         'expansion_device','Compressor2','evaporator_ref2',
#                                         'compressor_ref2','condenser_ref2','expansion_device2',
#                                         'evaporator_ref3','compressor_ref3','condenser_ref3',
#                                         'expansion_device3','Condenser2','Pump','Heater6',
#                                         'De_ethanizer','Depropanizer','PropyleneFractionator',
#                                         'EthyleneFractionator','Mixer3','Debutanizer','NaphthaSplitter',
#                                         'DieselSplitter','Mixer4'],
#         "Hydrogen Production Unit": ['Steam_Reformer', 'Mixer5', 'Hydrogen_production', 'PSA'],
#         "Hydrocracking Unit": ['Compressor3','Hydrocracking','Hydrocracking_Unit','H2split','NaphthaSplitter2',
#                                 'DieselSplitter2'],
#         "Other":[]
# }
# %%

def find_group(equipment):
    for k in groups.keys():
        if equipment in groups[k]:
            return k
    return "Others"


# %%
# equipment_ids = [i[0] for i in all_capital_cost[1]]
equipment_costs = []
equipment_purchase = []
for i in all_capital_cost:
    costs = {k:0 for k in groups.keys()}
    for j in range(len(i)):
        group = find_group(i[j][0])
        costs[group] += i[j][1]
    equipment_costs.append(costs.values())

for i in all_purchase_cost:
    costs = {k:0 for k in groups.keys()}
    for j in range(len(i)):
        group = find_group(i[j][0])
        costs[group] += i[j][1]
    equipment_purchase.append(costs.values())
df_cap_cost = pd.DataFrame(equipment_costs, index=scenarios_labels, columns=groups.keys())
df_purchase_cost = pd.DataFrame(equipment_purchase, index=scenarios_labels, columns=groups.keys())
df_cap_cost = df_cap_cost/1e6
df_purchase_cost = df_purchase_cost/1e6

df_cap_cost = df_cap_cost.drop(columns=["Others"]) 
df_cap_cost.plot.bar(stacked=True, figsize=(9,6),width = 0.75)
plt.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.) #loc='upper center', ncols=3, 
# plt.legend(bbox_to_anchor=(0.5, 1.20), loc='upper center', borderaxespad=0., ncol=3)
plt.xlabel("Scenarios")
plt.ylabel("Capital Cost (MM USD)")
plt.title("(A) Breakdown of Capital Costs of all Scenarios")
plt.xticks(rotation=0)
plt.savefig("Results/Images/Capital Cost.png",dpi=300,bbox_inches="tight")

df_cap_cost['Total'] = df_cap_cost.sum(axis=1)
df_cap_cost.T.to_excel("Results/cap_cost.xlsx")
# %%
df_ope_cost = pd.DataFrame(all_operating_cost, index=scenarios_labels)
df_ope_cost = df_ope_cost.fillna(0)
df_ope_cost = df_ope_cost/1e6


#  %%
df_ope_summary = pd.DataFrame()
df_ope_summary["Feedstock Cost"] = df_ope_cost["HDPE_Feed"]
df_ope_summary["Utilities"] = df_ope_cost["Utilities"]
df_ope_summary["Depreciaton"] = df_ope_cost["Depreciation"]
df_ope_summary["Operations & Maintenance"] = df_ope_cost["O&M"]
df_ope_summary["Natural Gas"] = df_ope_cost['comb_nat_gas']
df_ope_summary["Hydrogen"] = df_ope_cost["Hydrogen"]
df_ope_summary["Others"] = df_ope_cost["Other"] + df_ope_cost["hydrocracking_catalyst"]

df_plot = df_ope_summary
df_plot.plot.bar(stacked=True, figsize=(9,6),width = 0.75)
# plt.xlabel("Scenarios")
plt.xlabel("Scenarios", fontsize="large", color="black")
plt.ylabel("Annual Operating Cost (MM USD)", fontsize="large", color="black")
plt.title("(B) Breakdown of Annual Operating Costs of all Scenarios")
plt.xticks(rotation=0)

plt.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.) #loc='upper center', ncols=3, 
plt.savefig("Results/Images/Operating Cost.png",dpi=300,bbox_inches="tight")
# df_ope_cost.to_excel("Results/ope_cost.xlsx")
# df_ope_summary.to_excel("Results/ope_summary.xlsx")


# %%
# equipment_costs
# %%
# equipment_ids2 = [i[0] for i in all_operating_cost[1]]
# equipment_costs2 = []
# for i in all_operating_cost:
#     costs = {k:0 for k in groups.keys()}
#     for j in range(len(i)):
#         group = find_group(equipment_ids2[j])
#         costs[group] += i[j][1]
#     equipment_costs2.append(costs.values())
# df = pd.DataFrame(equipment_costs2, index=scenarios_labels, columns=groups.keys())
# df.plot.bar(stacked=True, figsize=(14,10))
# plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
# %%
# equipment_ids = [i[0] for i in all_purchase_cost[1]]
# equipment_costs = []
# for i in all_purchase_cost:
#     costs = {k:0 for k in groups.keys()}
#     for j in range(len(i)):
#         group = find_group(i[j][0])
#         costs[group] += i[j][1]
#     equipment_costs.append(costs.values())
# df_cap_cost2 = pd.DataFrame(equipment_costs, index=scenarios_labels, columns=groups.keys())
# df_cap_cost2.plot.bar(stacked=True, figsize=(9,7))
# plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)


# %% 
fig, ax = plt.subplots(figsize=(8, 6))
plt.bar(scenarios_labels,[x/1e6 for x in all_NPV],width=0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")#,fontweight ="bold")
plt.ylabel("Net Present Value (MM USD)",fontsize="large",color = "black")#,fontweight ="bold")
# plt.savefig("Results/Images/Net Present Value.png",dpi=300,bbox_inches="tight")

# %%
df_annual_revenue2 = df_annual_revenue/1e6 
df_annual_revenue2.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")#,fontweight ="bold")
plt.xticks(rotation='horizontal')

plt.ylabel("Annual Revenue (MM USD)",fontsize="large",color = "black")#,fontweight ="bold")
plt.legend(bbox_to_anchor=(1.02, 0.7), loc='upper left', borderaxespad=0.)
# plt.show()
plt.savefig("Results/Images/Annual Revenue.png",dpi=300,bbox_inches="tight")
df_annual_revenue_3 = (df_annual_revenue/1e6).copy()
df_annual_revenue_3['Total'] = df_annual_revenue_3.sum(axis=1)
df_annual_revenue_3.T.to_excel("Results/annual_revenue.xlsx")

# %%

# %%
df_plot = df_annual_yield/1e6
df_plot.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.xlabel("Scenarios",fontsize="large",color = "black")#,fontweight ="bold")
plt.xticks(rotation='horizontal')
plt.ylabel("Annual Output (kilotonnes/year)",fontsize="large",color = "black")#,fontweight ="bold")
plt.legend(bbox_to_anchor=(1.15, 0.7), loc='upper center', borderaxespad=0.)
plt.savefig("Results/Images/Annual Yield.png",dpi=300,bbox_inches="tight")
df_plot["Total"] = df_plot.sum(axis=1)
df_annual_yield2 = df_plot.copy()
df_plot.T.to_excel("Results/annual_yield.xlsx")
# %%


# %%
df_GWP_perhr = pd.DataFrame(all_GWP, index=scenarios_labels)
df_GWP_perhr.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.legend(bbox_to_anchor=(1.05, 0.75), loc='upper left', borderaxespad=0.)
plt.ylabel("GWP (kg CO2-eq/hour of operation)")
plt.xlabel("Scenarios")
plt.title("(A) GWP per hour of all Scenarios")
plt.savefig("Results/Images/GWP per hr.png",dpi=300,bbox_inches="tight")
df_GWP_perhr.to_excel("Results/GWP per hr.xlsx")

# %%
df_GWP_tonne = df_GWP_perhr/(plant_capacity/24)
df_GWP_tonne.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.legend(bbox_to_anchor=(1.05, 0.75), loc='upper left', borderaxespad=0.)
plt.xticks(rotation='horizontal')
plt.ylabel("GWP (kg CO2-eq/tonne of waste HDPE)")
plt.xlabel("Scenarios")
plt.title("(A) GWP per tonne of all Scenarios")
plt.savefig("Results/Images/GWP per tonne.png",dpi=300,bbox_inches="tight")
df_GWP_tonne.to_excel("Results/GWP per tonne of waste HDPE.xlsx")


# %%

df_GWP_tonne_2 = df_GWP_tonne.copy()
df_GWP_tonne_2['Total'] = df_GWP_tonne_2.sum(axis=1)
df_GWP_tonne_2

# %%
Total = df_GWP_tonne.sum(axis= 1)
percentage_df = df_GWP_tonne.divide(Total, axis=0) * 100
percentage_df.plot.bar(stacked=True, figsize=(8,6),width = 0.75)
plt.xticks(rotation='horizontal')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
plt.ylabel("Percentage contribution to GWP (%)")
plt.xlabel("Scenarios")
plt.title("(B) Percentage contribution to GWP of all Scenarios")
plt.savefig("Results/Images/Percentage contribution to GWP.png",dpi=300,bbox_inches="tight")
percentage_df
# %%
df_GWP_tonne_2 = df_GWP_tonne.copy()
df_GWP_tonne_2['Total'] = df_GWP_tonne_2.sum(axis=1)
df_GWP_tonne_2.T.to_excel("Results/GWP per tonne of waste HDPE.xlsx")
# %%
avoided_emission_factors = {"Ethylene": 1.37893,
                            "Propylene": 1.41647,
                            "Butene": 1.50706,  
                            "Naphtha": 0.43911,
                            "Diesel": 0.49756,
                            "Wax": 0.75109}
                
# %%
primary_product = {"CPY": "Wax",
                    "CPY-HC": "Naphtha",
                    "TOD": "Wax",
                    "TOD-HC": "Naphtha",
                    "HRT": "Naphtha",
                    "HRT-HC": "Naphtha"
                    }


# %%
df_yield_per_kg = df_annual_yield.copy()
row_sums = df_yield_per_kg.sum(axis=1)
df_yield_per_kg = df_yield_per_kg.div(row_sums, axis=0)
df_avoided_emission = df_yield_per_kg.apply(lambda row: row * avoided_emission_factors[row.name],axis =0)

# Relace primary products with zero
for key,value in primary_product.items():
    df_avoided_emission[value][key] = 0

# update total avoided emissions per kg
df_avoided_emission["Total"] = df_avoided_emission.sum(axis=1)

# add study emissions to the table 
df_avoided_emission["Study emissions"] = df_GWP_tonne_2["Total"]/1000
df_avoided_emission["Primary product emission"] = df_avoided_emission["Study emissions"] - df_avoided_emission["Total"] 

# %%
df_avoided_emission["Primary product emission per kg"] = np.zeros(len(df_avoided_emission))
df_avoided_emission["Virgin product emission"] = np.zeros(len(df_avoided_emission))
for key,value in primary_product.items():
    df_avoided_emission["Primary product emission per kg"][key] = df_avoided_emission['Primary product emission'][key]/ df_yield_per_kg[value][key]
    df_avoided_emission["Virgin product emission"][key] = avoided_emission_factors[primary_product[key]]
# %%
df_avoided_emission 
# %%

x = np.arange(len(scenarios_labels))
width = 0.4  # Width of the bars

fig, ax = plt.subplots(figsize=(8, 6))

rects1 = ax.bar(x - width/2, df_avoided_emission["Primary product emission per kg"], width, label='Study emissions')
rects2 = ax.bar(x + width/2, df_avoided_emission["Virgin product emission"], width, label='Virgin product')

ax.set_xlabel("Scenarios", color="black")
ax.set_ylabel("GWP", color="black")

ax.set_xticks(x)
ax.set_xticklabels(scenarios_labels) #, rotation='horizontal')
ax.legend(bbox_to_anchor=(1.02, 0.7), borderaxespad=0.) # (title="Legend")

# plt.title("(C) Net Present Value of all Scenarios \n (20 & 30 Years Facility Lifetime)")
# plt.savefig("Results/Images/Net Present Value 20 30 years.png",dpi=300,bbox_inches="tight")

plt.show()
# %%
wax_label = ["CPY","TOD","Virgin"]
naphtha_label = ["CPY-HC","TOD-HC","HRT","HRT-HC","Virgin"]
wax_list = [df_avoided_emission["Primary product emission per kg"]["CPY"],
            df_avoided_emission["Primary product emission per kg"]["TOD"],
            df_avoided_emission["Virgin product emission"]["CPY"]]
naphtha_list = [df_avoided_emission["Primary product emission per kg"]["CPY-HC"],
                df_avoided_emission["Primary product emission per kg"]["TOD-HC"],
                df_avoided_emission["Primary product emission per kg"]["HRT"],
                df_avoided_emission["Primary product emission per kg"]["HRT-HC"],
                df_avoided_emission["Virgin product emission"]["CPY-HC"]
                ]

width = 0.18  # Width of the bars
colors = ["blue","blue","blue","blue","blue"]
colors2 = ["grey","grey","grey"]
fig, ax = plt.subplots(figsize=(8, 6))
x_positions = [0.1,0.3,0.5,0.7,0.9]
x2_positions = [1.2,1.4,1.6]
rects1 = ax.bar(x_positions,naphtha_list, width,color = colors, label = "Naphtha")
rects2 = ax.bar(x2_positions,wax_list,width,color=colors2, label = "Wax")

# Add labels and title
# ax.set_xlabel("Categories")
ax.set_ylabel("GWP (kg CO2-eq)")
# ax.set_title("Bar Chart with Custom Colors")

ax.set_xticks(x_positions + x2_positions)
ax.set_xticklabels(naphtha_label + wax_label)
# ax.legend(bbox_to_anchor=(1., 0.7), borderaxespad=0.) # (title="Legend")
ax.legend()


# Add a line at zero on the y-axis
ax.axhline(0, color='black', linewidth=0.5)

# Add a legend
ax.set_title("(C) Primary Products Emissons per kg of all Scenarios vs Virgin Products Emissions")

# Show the plot
plt.tight_layout()
plt.show()
# %%
