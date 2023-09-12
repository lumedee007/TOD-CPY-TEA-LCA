import biosteam as bst
import numpy as np

class TEA_MFSP(bst.TEA):
    """
    Create a SugarcaneTEA object for techno-economic analysis of a biorefinery [1]_.

    Parameters
    ----------
    system : System
        Should contain feed and product streams.
    IRR : float
        Internal rate of return (fraction).
    duration : tuple[int, int]
        Start and end year of venture (e.g. (2018, 2038)).
    depreciation : str
        'MACRS' + number of years (e.g. 'MACRS7').
    operating_days : float
        Number of operating days per year.
    income_tax : float
        Combined federal and state income tax rate (fraction).
    lang_factor : float
        Lang factor for getting fixed capital investment from
        total purchase cost. If no lang factor, estimate capital investment
        using bare module factors.
    startup_schedule : tuple[float]
        Startup investment fractions per year
        (e.g. (0.5, 0.5) for 50% capital investment in the first year and 50%
        investment in the second).
    WC_over_FCI : float
        Working capital as a fraction of fixed capital investment.
    labor_cost : float
        Total labor cost (USD/yr).
    fringe_benefits : float
        Cost of fringe benefits as a fraction of labor cost.
    property_tax : float
        Fee as a fraction of fixed capital investment.
    property_insurance : float
        Fee as a fraction of fixed capital investment.
    supplies : float
        Yearly fee as a fraction of labor cost.
    maintenance : float
        Yearly fee as a fraction of fixed capital investment.
    administration : float
        Yearly fee as a fraction of fixed capital investment.

    References
    ----------
    .. [1] Huang, H., Long, S., & Singh, V. (2016). Techno-economic analysis of biodiesel
        and ethanol co-production from lipid-producing sugarcane. Biofuels, Bioproducts
        and Biorefining, 10(3), 299–315. https://doi.org/10.1002/bbb.1640

    """

    __slots__ = ('labor_cost', 'fringe_benefits', 'maintenance',
                 'property_tax', 'property_insurance', '_FCI_cached',
                 'supplies', 'maintanance', 'administration')

    def __init__(self, system, 
                    IRR,
                    duration, 
                    depreciation, 
                    income_tax,
                    operating_days, 
                    lang_factor, 
                    construction_schedule, 
                    WC_over_FCI,
                    labor_cost, 
                    fringe_benefits, 
                    property_tax,
                    property_insurance, 
                    supplies, 
                    maintenance, 
                    administration,
                    finance_interest=0, 
                    finance_years=0,
                    finance_fraction=0):
        super().__init__(system, IRR, duration, depreciation, income_tax,
                         operating_days, lang_factor, construction_schedule,
                         startup_months=0, startup_FOCfrac=0, startup_VOCfrac=0,
                         startup_salesfrac=0, finance_interest=finance_interest, finance_years=finance_years,
                         finance_fraction=finance_fraction, WC_over_FCI=WC_over_FCI)
        self.labor_cost = labor_cost
        self.fringe_benefits = fringe_benefits
        self.property_tax = property_tax
        self.property_insurance = property_insurance
        self.supplies= supplies
        self.maintenance = maintenance
        self.administration = administration

    # The abstract _DPI method should take installed equipment cost
    # and return the direct permanent investment. Huang et. al. assume
    # these values are equal
    def _DPI(self, installed_equipment_cost):
        return installed_equipment_cost

    # The abstract _TDC method should take direct permanent investment
    # and return the total depreciable capital. Huang et. al. assume
    # these values are equal
    def _TDC(self, DPI):
        return DPI

    # The abstract _FCI method should take total depreciable capital
    # and return the fixed capital investment. Again, Huang et. al.
    # assume these values are equal.
    def _FCI(self, TDC):
        return TDC

    # The abstract _FOC method should take fixed capital investment
    # and return the fixed operating cost.
    def _FOC(self, FCI):
        return (FCI*(self.property_tax + self.property_insurance
                     + self.maintenance + self.administration))
    
    def mfsp_table(self, product=None, solve=True):
        costs = {}
        for f in self.feeds:
            if abs(f.cost) > 1.0:
                costs[f.ID] = f.cost*self.operating_days*24
            else:
                costs["Other"] = costs.get("Other", 0) + f.cost*self.operating_days*24
        costs["Utilities"] = self.utility_cost 
        costs["O&M"] = self.FOC 
        costs["Depreciation"] = self.annual_depreciation

        revenues = 0
        if product == None:
            for f in self.products:
                if abs(f.cost) > 0:
                    costs[f.ID] = -f.cost*self.operating_days*24
                    revenues += -f.cost*self.operating_days*24
        else:
            for f in self.products:
                if product != None and f.ID != product.ID:
                    if abs(f.cost) > 0:
                        costs[f.ID] = -f.cost*self.operating_days*24
                        revenues += -f.cost*self.operating_days*24
        if product != None:
            if solve==True:
                price = self.solve_price(product)
            else:
                price = product.price
            sales = price*product.get_total_flow('kg/year')
            costs["Income Tax"] = self.income_tax*(sales-revenues-self.AOC)
            if costs["Income Tax"] < 0:
                costs["Income Tax"] = 0

            costs["ROI"] = sales - sum([v for v in costs.values()]) 
        else:
            costs["ROI"] = self.ROI
        return costs