"""
Copyright (c) 2022 Ed Millard

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the
following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import datetime
import numpy as np
import signal
import sys
import usgs
from usgs import az, ca, lc, ut, nv   # nm, wy
import usbr
from usbr import az, ca, uc, nv
from source.usgs_gage import USGSGage
from source import usbr_report
from source import usbr_rise
import util
from util import subtract_annual, reshape_annual_range
from graph.water import WaterGraph
from pathlib import Path

interrupted = False

current_last_year = 2021

# matplotlib colors
# https://i.stack.imgur.com/lFZum.png
#
# Yuma area info
# https://www.usbr.gov/lc/yuma/
# https://www.usbr.gov/lc/yuma/programs/YAWMS/GROUNDWATER_maps.cfm
# https://www.usbr.gov/lc/yuma/environmental_docs/environ_docs.html
# estinates of evaporation on lower colorado
# https://eros.usgs.gov/doi-remote-sensing-activities/2020/bor/estimates-evapotranspiration-and-evaporation-along-lower-colorado-river
# https://usbr.gov/lc/region/g4000/4200Rpts/LCRASRpt/2009/report09.pdf
# https://www.usbr.gov/lc/region/g4000/contracts/entitlements.html


# noinspection PyUnusedLocal
def usbr_catalog():
    # unified_region_north_atlantic_appalachian = 1
    # unified_region_south_atlantic_gulf = 2
    # unified_region_great_lakes = 3
    # unified_region_mississippi = 4
    # unified_region_missouri = 5
    # unified_region_arkansas_rio_grande_texas_gulf = 6
    unified_region_upper_colorado = 7
    unified_region_lower_colorado = 8
    # unified_region_columbia_pacific_northwest = 9
    # unified_region_california_great_basin = 10
    # unified_region_alaska = 11
    # unified_region_pacific_islands = 12

    theme_water = 1
    # theme_water_quality = 2
    # theme_biological = 3
    # theme_environmental = 4
    # theme_infrastructure_and_assets = 5
    # theme_hydropower = 7
    # theme_safety_health_and_industrial_hygiene = 10

    catalog_path = Path('data/USBR_RISE/')
    catalog_path.mkdir(parents=True, exist_ok=True)

    upper_colorado_catalog_path = catalog_path.joinpath('Upper_Colorado_Catalog.json')
    records = usbr_rise.load_catalog(upper_colorado_catalog_path, unified_region_upper_colorado, theme_id=theme_water)
    for record in records:
        attributes = record['attributes']
        record_title = attributes['recordTitle']
        if record_title.startswith('Navajo Reservoir'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_navajo')
        elif record_title.startswith('Lake Powell') and not record_title.endswith('Evaporation Pan'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_lake_powell')
        elif record_title.startswith('Fontenelle Reservoir'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_fontenelle')
        elif record_title.startswith('Blue Mesa'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_blue_mesa')
        elif record_title.startswith('Flaming Gorge'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_flaming_gorge')
        elif record_title.startswith('Green Mountain'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_green_mountain')
        elif record_title.startswith('Ruedi'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_ruedi')
        elif record_title.startswith('Lake Granby'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_lake_granby')
        elif record_title.startswith('Grand Lake'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_lake_grand_lake')
        elif record_title.startswith('Willow Creek'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_lake_willow_creek')
        elif record_title.startswith('Shadow Mountain'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_lake_shadow_mountain')
        elif record_title.startswith('Mcphee'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_mcphee')
        elif record_title.startswith('Taylor Park'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_taylor_park')
        # else:
        #    print(record_title)

    lower_colorado_catalog_path = catalog_path.joinpath('Lower_Colorado_Catalog.json')
    records = usbr_rise.load_catalog(lower_colorado_catalog_path, unified_region_lower_colorado, theme_id=theme_water)
    for record in records:
        attributes = record['attributes']
        record_title = attributes['recordTitle']
        if record_title.startswith('Lake Mead'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_lake_mead')
        elif record_title.startswith('Lake Mohave'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_lake_mohave')
        elif record_title.startswith('Lake Havasu'):
            catalog_items = usbr_rise.load_catalog_items(record, 'usbr_lake_havasu')
        else:
            print(record_title)


'''
    SW Colorado
    Lemon Reservoir and Dam Water Operations Monitoring Data from Upper Colorado Hydrologic Database
    Jackson Gulch Reservoir and Dam Water Operations Monitoring Data from Upper Colorado Hydrologic Database
    Vallecito Reservoir and Dam Water Operations Monitoring Data from Upper Colorado Hydrologic Database

    Ridgway Reservoir and Dam Water Operations Monitoring Data from Upper Colorado Hydrologic Database
    Paonia Reservoir and Dam Water Operations Monitoring Data from Upper Colorado Hydrologic Database
    Fruitgrowers Reservoir - Orchard, CO
    Silver Jack Reservoir - Gunnison, CO
    Morrow Point Reservoir Dam and Powerplant Water Operations Monitoring Data from Upper Colorado Hydrologic Database
    Crystal Reservoir Dam and Powerplant Water Operations Monitoring Data from Upper Colorado Hydrologic Database
    Taylor Park Reservoir - Uncompaghre
    Utah:
        Strawberry Reservoir - East Slope of Wasatch
        Starvation Reservoir - West of Duschesne
        Moon Lake Reservoir - North of Duschesne
        Stateline Reservoir - Wyoming Border, Smiths Fork
        Scofield Reservoir - Price River
        Rockport Reservoir - Weber River
        Lost Creek Reservoir - Weber
        Red Fleet Reservoir - Vernal
        Steinaker Reservoir - Vernal
        Trial Lake - Wasatch
        Pineview Reservoir - Ogden
        Willard Bay Reservoir - Ogden
        Upper Stillwater Reservoir - Bonneville
    Wyoming:
        Meeks Cabin Reservoir


'''
'''
    Colorado River Below Davis Dam Water Operations Monitoring Data from the Lower Colorado Hydrologic Database
    Colorado River At Water Wheel Water Operations Monitoring Data from the Lower Colorado Hydrologic Database
    Colorado River At Taylor Ferry Water Operations Monitoring Data from the Lower Colorado Hydrologic Database
    Colorado River At River Section 41 Water Operations Monitoring Data from the Lower Colorado Hydrologic Database
    Colorado River At Parker Gage Water Operations Monitoring Data from the Lower Colorado Hydrologic Database
    Colorado River At Cibola Gage Water Operations Monitoring Data from the Lower Colorado Hydrologic Database
    Colorado River Below Oxbow Bridge Water Operations Monitoring Data from the Lower Colorado Hydrologic Database
    Colorado River Below Mcintyre Park Water Operations Monitoring Data from the Lower Colorado Hydrologic Database
    Colorado River Below Interstate Bridge Water Operations Monitoring Data from the Lower Colorado Hydrologic Database
    Colorado River Below Big Bend Water Operations Monitoring Data from the Lower Colorado Hydrologic Database
'''


def usbr_glen_canyon_annual_release_af(graph=False, start_year=None, end_year=None):
    usbr_lake_powell_release_total_af = 4354
    info, daily_usbr_glen_canyon_daily_release_af = usbr_rise.load(usbr_lake_powell_release_total_af)
    annual_af = WaterGraph.daily_to_water_year(daily_usbr_glen_canyon_daily_release_af)
    if start_year and end_year:
        annual_af = reshape_annual_range(annual_af, start_year, end_year)
    if graph:
        water_graph = WaterGraph(nrows=1)
        water_graph.bars(annual_af, sub_plot=0, title='Glen Canyon Release (Annual)', color='firebrick',
                         ymin=4000000, ymax=21000000, yinterval=1000000,
                         xlabel='Water Year', xinterval=4,
                         ylabel='maf', format_func=WaterGraph.format_maf)
        water_graph.fig.waitforbuttonpress()
    return annual_af


def glen_canyon_analysis():
    lees_ferry_gage = usgs.az.lees_ferry()
    graph = WaterGraph()
    graph.plot_gage(lees_ferry_gage)

    # USGS Lees Ferry Gage Daily Discharge Mean
    #
    usgs_lees_ferry_annual_af = lees_ferry_gage.annual_af(water_year_month=10)
    # usgs_lees_ferry_running_average = rw_running_average(usgs_lees_ferry_annual_af, 10)
    # x = usgs_lees_ferry_running_average['dt']
    # y = usgs_lees_ferry_running_average['val']
    # plot_bars.plot(x, y, linestyle='-', linewidth=3, marker='None', color='goldenrod', label='10Y Running Average')
    # plot_bars.legend()
    # plot_bars.show()
    # plot_bars.waitforbuttonpress()

    usgs_lees_ferry_af_1999_2021 = WaterGraph.array_in_time_range(usgs_lees_ferry_annual_af,
                                                                  datetime.datetime(1999, 1, 1),
                                                                  datetime.datetime(current_last_year, 12, 31))
    # rw_bars(annual_discharge_af, title=name, color='royalblue',
    #        ylabel='maf', ymin=2000000, ymax=21000000, yinterval=500000, format_func=format_maf,
    #        xlabel='Water Year', xinterval=5)
    glen_canyon_annual_release_af = usbr_glen_canyon_annual_release_af()

    # rw_bars(a, title='Lake Powell Release',
    #        ylabel='maf', ymin=7000000, ymax=20750000, yinterval=500000,
    #        xlabel='Water Year', xinterval=3, format_func=format_maf)

    graph = WaterGraph()
    graph.bars_two(glen_canyon_annual_release_af, usgs_lees_ferry_annual_af,
                   title='Lake Powell Release Comparison, USBR Glen Canyon vs USGS Lees Ferry',
                   label_a='Glen Canyon', color_a='royalblue',
                   label_b='Lees Ferry', color_b='limegreen',
                   ylabel='af', ymin=7000000, ymax=13000000, yinterval=250000,
                   xlabel='Water Year', xinterval=3, format_func=WaterGraph.format_maf)
    graph.running_average(glen_canyon_annual_release_af, 10, sub_plot=0)
    graph.running_average(usgs_lees_ferry_annual_af, 10, sub_plot=0)

    usbr_lake_powell_release_af_1999_2021 = WaterGraph.array_in_time_range(glen_canyon_annual_release_af,
                                                                           datetime.datetime(1999, 1, 1),
                                                                           datetime.datetime(current_last_year, 12, 31))

    # USGS Paria At Lees Ferry Gage Daily Discharge Mean
    #
    usgs_paria_annual_af = usgs.az.paria_lees_ferry().annual_af()
    usgs_paria_annual_af_1999_2021 = WaterGraph.array_in_time_range(usgs_paria_annual_af,
                                                                    datetime.datetime(1999, 1, 1),
                                                                    datetime.datetime(current_last_year, 12, 31))

    usbr_glen_canyon_vector = usbr_lake_powell_release_af_1999_2021['val']
    usgs_paria_vector = usgs_paria_annual_af_1999_2021['val']
    usgs_glen_canyon_plus_paria = usbr_glen_canyon_vector + usgs_paria_vector

    glen_canyon_plus_paria = np.empty(2021-1999+1, [('dt', 'i'), ('val', 'f')])
    glen_canyon_plus_paria['dt'] = usbr_lake_powell_release_af_1999_2021['dt']
    glen_canyon_plus_paria['val'] = usgs_glen_canyon_plus_paria

    usgs_lees_ferry_vector = usgs_lees_ferry_af_1999_2021['val']

    print('USBR Glen Canyon:\n', usbr_glen_canyon_vector)
    print('USGS Lees Ferry:\n', usgs_lees_ferry_vector)
    difference = usgs_lees_ferry_vector - usgs_glen_canyon_plus_paria
    difference_sum = difference.sum()
    difference_average = difference_sum / len(difference)
    print('Total discrepancy 1999-2021   = ', int(difference_sum))
    print('Average discrepancy 1999-2021 = ', int(difference_average))
    print('Difference vector:\n', difference)

    discrepancy = np.empty(len(usgs_lees_ferry_af_1999_2021['dt']), [('dt', 'i'), ('val', 'f')])
    discrepancy['dt'] = usgs_lees_ferry_af_1999_2021['dt']
    discrepancy['val'] = difference

    graph = WaterGraph()
    graph.bars_two(glen_canyon_plus_paria, usgs_lees_ferry_af_1999_2021,
                   title='Lake Powell Release Comparison, USBR Glen Canyon + Paria vs USGS Lees Ferry',
                   label_a='Glen Canyon + Paria', color_a='royalblue',
                   label_b='Lees Ferry', color_b='limegreen',
                   ylabel='maf', ymin=7000000, ymax=13000000, yinterval=250000,
                   xlabel='Water Year', xinterval=3, format_func=WaterGraph.format_maf)
    graph.running_average(glen_canyon_plus_paria, 10, sub_plot=0)
    graph.running_average(usgs_lees_ferry_af_1999_2021, 10, sub_plot=0)
    graph.fig.waitforbuttonpress()

    graph = WaterGraph()
    graph.bars(discrepancy,
               title='Lake Powell Release Difference USBR Glen Canyon + paria vs USGS Lees Ferry',
               ylabel='kaf', ymin=0, ymax=300000, yinterval=50000,
               xlabel='Water Year', xinterval=2, format_func=WaterGraph.format_kaf)
    graph.fig.waitforbuttonpress()


def all_american_model():
    year_interval = 4

    # FIXME Hoover, Parker, Davis

    # Colorado River Indian Tribe (CRIT) and Rock Dam Release
    graph = WaterGraph(nrows=4)

    crit_diversion_annual_af = usbr_report.annual_af('az/usbr_az_crit_diversion.csv')
    crit_cu_annual_af = usbr_report.annual_af('az/usbr_az_crit_consumptive_use.csv')

    bar_data = [{'data': crit_diversion_annual_af, 'label': 'Diversion', 'color': 'darkmagenta'},
                {'data': crit_cu_annual_af, 'label': 'Consumptive Use', 'color': 'firebrick'},
                ]
    graph.bars_stacked(bar_data, sub_plot=0, title='USBR AR CRIT Diversion & Consumptive Use (Annual)',
                       xinterval=year_interval, ymin=150000, ymax=750000, yinterval=100000,
                       ylabel='kaf',  format_func=WaterGraph.format_kaf, vertical=False)
    graph.running_average(crit_diversion_annual_af, 10, sub_plot=0)
    graph.running_average(crit_cu_annual_af, 10, sub_plot=0)

    rock_dam_release_annual_af = usbr_report.annual_af('releases/usbr_releases_rock_dam.csv')
    graph.bars(rock_dam_release_annual_af, sub_plot=1, title='USBR AR Rock Dam Release (Annual)',
               xinterval=year_interval, ymin=4500000, ymax=8000000, yinterval=500000, color='firebrick',
               ylabel='maf',  format_func=WaterGraph.format_maf)

    crit_return_flows_annual = subtract_annual(crit_diversion_annual_af, crit_cu_annual_af, 1965, current_last_year)
    graph.bars(crit_return_flows_annual, sub_plot=2, title='USBR AR CRIT Return Flows(Annual)',
               xinterval=year_interval, ymin=150000, ymax=400000, yinterval=50000, color='darkmagenta',
               ylabel='kaf',  format_func=WaterGraph.format_kaf)

    bar_data = [{'data': rock_dam_release_annual_af, 'label': 'Rock Dam Release', 'color': 'firebrick'},
                {'data': crit_return_flows_annual, 'label': 'CRIT Return Flows', 'color': 'darkmagenta'},
                ]
    graph.bars_stacked(bar_data, sub_plot=3, title='USBR AR Flow below Rock Dam with CRIT Return Flows (Annual)',
                       xinterval=year_interval, ymin=4500000, ymax=8000000, yinterval=500000, xlabel='Calendar Year',
                       ylabel='maf',  format_func=WaterGraph.format_maf)
    flows_below_rock_annual = util.add_annual(rock_dam_release_annual_af, crit_return_flows_annual,
                                              1965, current_last_year)
    graph.running_average(flows_below_rock_annual, 10, sub_plot=3)

    graph.fig.waitforbuttonpress()

    # Palo Verde Diversion Dam Release and Return Flows
    graph = WaterGraph(nrows=4)

    palo_verde_diversion_annual_af = usbr_report.annual_af('ca/usbr_ca_palo_verde_diversion.csv')
    palo_verde_cu_annual_af = usbr_report.annual_af('ca/usbr_ca_palo_verde_consumptive_use.csv')
    bar_data = [{'data': palo_verde_diversion_annual_af, 'label': 'Diversion', 'color': 'darkmagenta'},
                {'data': palo_verde_cu_annual_af, 'label': 'Consumptive Use', 'color': 'firebrick'},
                ]
    graph.bars_stacked(bar_data, sub_plot=0, title='USBR AR Palo Verde Diversion & Consumptive Use (Annual)',
                       xinterval=year_interval, ymin=200000, ymax=1100000, yinterval=100000,
                       ylabel='kaf',  format_func=WaterGraph.format_kaf, vertical=False)
    graph.running_average(palo_verde_diversion_annual_af, 10, sub_plot=0)
    graph.running_average(palo_verde_cu_annual_af, 10, sub_plot=0)

    palo_verde_dam_release_annual_af = usbr_report.annual_af('releases/usbr_releases_palo_verde_dam.csv')
    graph.bars(palo_verde_dam_release_annual_af, sub_plot=1, title='USBR AR Palo Verde Dam Release (Annual)',
               xinterval=year_interval, ymin=3500000, ymax=7000000, yinterval=500000, color='firebrick',
               ylabel='maf',  format_func=WaterGraph.format_maf)

    palo_verde_return_flows_annual = util.subtract_annual(palo_verde_diversion_annual_af, palo_verde_cu_annual_af,
                                                          1965, current_last_year)
    graph.bars(palo_verde_return_flows_annual, sub_plot=2, title='Palo Verde Return Flows(Annual)',
               xinterval=year_interval, ymin=200000, ymax=600000, yinterval=50000, color='darkmagenta',
               ylabel='kaf',  format_func=WaterGraph.format_kaf)

    bar_data = [{'data': palo_verde_dam_release_annual_af, 'label': 'Palo Verde Dam Release', 'color': 'firebrick'},
                {'data': palo_verde_return_flows_annual, 'label': 'Palo Verde Return Flows', 'color': 'darkmagenta'},
                ]
    graph.bars_stacked(bar_data, sub_plot=3, title='Flow below Palo Verde Dam with PV Return Flows (Annual)',
                       xinterval=year_interval, ymin=3500000, ymax=7000000, yinterval=500000, xlabel='Calendar Year',
                       ylabel='maf', format_func=WaterGraph.format_maf)
    flows_below_rock_annual = util.add_annual(palo_verde_dam_release_annual_af, palo_verde_return_flows_annual,
                                              1965, current_last_year)
    graph.running_average(flows_below_rock_annual, 10, sub_plot=3)

    graph.fig.waitforbuttonpress()

    # All American Canal Above Imperial Dam
    graph = WaterGraph(nrows=4)

    gage = USGSGage('09523000', start_date='1939-10-01')
    all_american_annual_af = gage.annual_af(start_year=1965, end_year=current_last_year)
    graph.bars(all_american_annual_af, sub_plot=1, title='USGS All American Canal Diversion (Annual)',
               xinterval=year_interval, ymin=3000000, ymax=6500000, yinterval=500000, color='firebrick',
               ylabel='maf',  format_func=WaterGraph.format_maf)

    # Imperial Dam Release
    imperial_dam_release_annual_af = usbr_report.annual_af('releases/usbr_releases_imperial_dam.csv')
    graph.bars(imperial_dam_release_annual_af, sub_plot=3, title='USBR AR Imperial Dam Release (Annual)',
               xinterval=year_interval, ymax=1000000, yinterval=100000,
               color='firebrick',
               ylabel='kaf',  format_func=WaterGraph.format_kaf)

    # Colorado River Below Imperial Dam, new gage, not worth much
    # gage = USGSGage('09429500', start_date='2018-11-29')
    graph.fig.waitforbuttonpress()

    graph = WaterGraph(nrows=4)

    gage = USGSGage('09523200', start_date='1974-10-01')
    reservation_main_annual_af = gage.annual_af(start_year=1965, end_year=current_last_year)
    graph.bars(reservation_main_annual_af, sub_plot=0, title='USBR AR Reservation Main Canal (Annual)',
               xinterval=year_interval, ymin=0, ymax=70000, yinterval=10000, color='firebrick',
               ylabel='kaf',  format_func=WaterGraph.format_kaf)

    gage = USGSGage('09524000', start_date='1938-10-01')
    yuma_main_annual_af = gage.annual_af(start_year=1965, end_year=current_last_year)
    graph.bars(yuma_main_annual_af, sub_plot=1, title='USGS Yuma Main Canal at Siphon Drop PP (Annual)',
               xinterval=year_interval, ymin=0, ymax=800000, yinterval=100000, color='firebrick',
               ylabel='kaf',  format_func=WaterGraph.format_kaf)

    # 09530500 10-14 CFS DRAIN 8-B NEAR WINTERHAVEN, CA
    # 0254970 160 CFS NEW R AT INTERNATIONAL BOUNDARY AT CALEXICO CA  1979-10-01
    # 09527594 150-45 CFS COACHELLA CANAL NEAR NILAND, CA  2009-10-17
    # 09527597 COACHELLA CANAL NEAR DESERT BEACH, CA  2009-10-24
    # 10254730 ALAMO R NR NILAND CA   1960-10-01
    # 10255550 NEW R NR WESTMORLAND CA  1943-01-01
    # 10259540 WHITEWATER R NR MECCA  1960-10-01

    # Coachella
    gage = USGSGage('09527590', start_date='2003-10-01')
    coachella_annual_af = gage.annual_af(start_year=1965, end_year=current_last_year)
    graph.bars(coachella_annual_af, sub_plot=2, title='USGS Coachella (Annual)',
               xinterval=year_interval, ymin=0, ymax=400000, yinterval=50000, color='firebrick',
               ylabel='kaf',  format_func=WaterGraph.format_kaf)

    # All American Drop 2, probably IID
    gage = USGSGage('09527700', start_date='2011-10-26')
    drop_2_annual_af = gage.annual_af(start_year=1965, end_year=current_last_year)
    graph.bars(drop_2_annual_af, sub_plot=3, title='USGS Drop 2 - Imperial(Annual)',
               xlabel='Calendar Year', xinterval=year_interval,
               ymin=0, ymax=3000000, yinterval=500000, color='firebrick',
               ylabel='maf',  format_func=WaterGraph.format_maf)

    graph.fig.waitforbuttonpress()

    graph = WaterGraph(nrows=4)
    # Brock Inlet
    gage = USGSGage('09527630', start_date='2013-11-06')
    brock_inlet_annual_af = gage.annual_af(start_year=1965, end_year=current_last_year)

    # Brock Outlet
    gage = USGSGage('09527660', start_date='2013-10-23')
    brock_outlet_annual_af = gage.annual_af(start_year=1965, end_year=current_last_year)

    graph.bars_two(brock_inlet_annual_af, brock_outlet_annual_af,
                   title='USGS Brock Inlet and Outlet (Annual)', sub_plot=0,
                   label_a='Brock Inlet', color_a='royalblue',
                   label_b='Brock Outlet', color_b='firebrick',
                   xinterval=year_interval, ymax=175000, yinterval=25000,
                   ylabel='kaf', format_func=WaterGraph.format_kaf)
    graph.running_average(brock_outlet_annual_af, 10, sub_plot=0, label="10Y Avg Brock Outlet")

    gage = USGSGage('09523600', start_date='1966-10-01')
    yaqui_main_annual_af = gage.annual_af(start_year=1965, end_year=current_last_year)
    graph.bars(yaqui_main_annual_af, sub_plot=1, title='Yaqui (Annual)',
               xinterval=year_interval, ymin=0, ymax=12000, yinterval=2000, color='firebrick',
               ylabel='kaf',  format_func=WaterGraph.format_kaf)

    gage = USGSGage('09523800', start_date='1966-10-01')
    pontiac_main_annual_af = gage.annual_af(start_year=1965, end_year=current_last_year)
    graph.bars(pontiac_main_annual_af, sub_plot=2, title='Pontiac (Annual)',
               xinterval=year_interval, ymin=0, ymax=12000, yinterval=2000, color='firebrick',
               ylabel='kaf',  format_func=WaterGraph.format_kaf)

    gage = USGSGage('09526200', start_date='1995-01-01')
    ypsilanti_main_annual_af = gage.annual_af(start_year=1965, end_year=current_last_year)
    graph.bars(ypsilanti_main_annual_af, sub_plot=3, title='Ypsilanti (Annual)',
               xinterval=year_interval, ymin=0, ymax=15000, yinterval=3000, color='firebrick',
               ylabel='kaf',  format_func=WaterGraph.format_kaf)
    graph.fig.waitforbuttonpress()


def lake_powell_inflow():
    start_year = 1963
    end_year = 2022

    show_graph = False
    show_annotated = False

    usgs_colorado_cisco_gage = usgs.ut.colorado_cisco(graph=show_graph)
    if show_annotated:
        colorado_cisco_af = usgs_colorado_cisco_gage.annual_af()
        graph = WaterGraph(nrows=1)
        graph.bars(colorado_cisco_af, sub_plot=0, title=usgs_colorado_cisco_gage.site_name, color='royalblue',
                   ymin=0, ymax=11500000, yinterval=500000, xinterval=4,
                   xlabel='Water Year', bar_width=1,  # xmin=start_year, xmax=end_year,
                   ylabel='maf', format_func=WaterGraph.format_maf)
        graph.annotate_vertical_arrow(1916, "Grand Valley", offset_percent=2.5)
        graph.annotate_vertical_arrow(1942, "Green Mountain", offset_percent=2.5)
        graph.annotate_vertical_arrow(1947, "Adams Tunnel", offset_percent=5)
        graph.annotate_vertical_arrow(1963, "Dillon", offset_percent=2.5)
        graph.annotate_vertical_arrow(1966, "Blue Mesa", offset_percent=5)
        graph.fig.waitforbuttonpress()
    colorado_cisco_af = usgs_colorado_cisco_gage.annual_af(start_year=start_year, end_year=end_year)

    usgs_green_river_gage = usgs.ut.green_river_at_green_river(graph=show_graph)
    if show_annotated:
        green_river_af = usgs_green_river_gage.annual_af()
        graph = WaterGraph(nrows=1)
        graph.bars(green_river_af, sub_plot=0, title=usgs_green_river_gage.site_name, color='royalblue',
                   ymin=0, ymax=9000000, yinterval=500000, xinterval=4,
                   xlabel='Water Year', bar_width=1,  # xmin=start_year, xmax=end_year,
                   ylabel='maf', format_func=WaterGraph.format_maf)
        graph.annotate_vertical_arrow(1962, "Flaming Gorge", offset_percent=2.5)
        graph.annotate_vertical_arrow(1963, "Fontenelle", offset_percent=5)
        graph.fig.waitforbuttonpress()
    green_river_af = usgs_green_river_gage.annual_af(start_year=start_year, end_year=end_year)

    usgs_san_juan_bluff_gage = usgs.ut.san_juan_bluff(graph=show_graph)
    if show_annotated:
        san_juan_af = usgs_san_juan_bluff_gage.annual_af()
        graph = WaterGraph(nrows=1)
        graph.bars(san_juan_af, sub_plot=0, title=usgs_san_juan_bluff_gage.site_name, color='royalblue',
                   ymin=0, ymax=3250000, yinterval=250000, xinterval=4,
                   xlabel='Water Year',  # xmin=start_year, xmax=end_year,
                   ylabel='maf', format_func=WaterGraph.format_maf)
        graph.annotate_vertical_arrow(1962, "Navajo", offset_percent=2.5)
        graph.fig.waitforbuttonpress()
    san_juan_af = usgs_san_juan_bluff_gage.annual_af(start_year=start_year, end_year=end_year)

    usgs_dirty_devil_gage = usgs.ut.dirty_devil(graph=True)
    dirty_devil_af = usgs_dirty_devil_gage.annual_af(start_year=start_year, end_year=end_year)
    # Only around 8 kaf annually
    # usgs_escalante_gage = usgs_escalante(graph=True)
    # escalante_af = usgs_escalante_gage.annual_af(start_year=start_year, end_year=end_year)

    year_interval = 3
    graph = WaterGraph(nrows=1)
    usbr_lake_powell_inflow_af = 4288
    usbr_lake_powell_inflow_volume_unregulated_af = 4301
    annual_inflow_af = usbr_rise.annual_af(usbr_lake_powell_inflow_af)
    # graph.bars(annual_inflow_af, sub_plot=0, title='Lake Powell Inflow',
    #            ymin=3000000, ymax=21000000, yinterval=2000000, xinterval=year_interval,
    #           ylabel='maf',  format_func=WaterGraph.format_maf)

    annual_inflow_unregulated_af = usbr_rise.annual_af(usbr_lake_powell_inflow_volume_unregulated_af)
    # graph.bars(annual_inflow_unregulated_af, sub_plot=1, title='Lake Powell Unregulated Inflow',
    #            ymin=300000, ymax=21000000, yinterval=2000000, xinterval=year_interval,
    #            ylabel='maf', format_func=WaterGraph.format_maf)
    # bar_data = [{'data': annual_inflow_unregulated_af, 'label': 'Lake Powell Unregulated Inflow', 'color': 'blue'},
    #             {'data': annual_inflow_af, 'label': 'Lake Powell Inflow', 'color': 'royalblue'},
    #             ]
    # graph.bars_stacked(bar_data, sub_plot=0, title='Lake Powell Inflow & Unregulated Inflow',
    #                    ymin=300000, ymax=21000000, yinterval=2000000,
    #                    xlabel='Water Year', xinterval=3,
    #                    ylabel='maf', format_func=WaterGraph.format_maf, vertical=False)

    graph.bars_two(annual_inflow_af, annual_inflow_unregulated_af,
                   title='Lake Powell Inflow & Unregulated Inflow',
                   label_a='Inflow', color_a='royalblue',
                   label_b='Unregulated Inflow', color_b='darkblue',
                   ylabel='af', ymin=0, ymax=21000000, yinterval=2000000,
                   xlabel='Water Year', xinterval=year_interval, format_func=WaterGraph.format_maf)
    graph.running_average(annual_inflow_af, 10, sub_plot=0)
    graph.running_average(annual_inflow_unregulated_af, 10, sub_plot=0)

    graph.fig.waitforbuttonpress()

    graph = WaterGraph(nrows=2)
    bar_data = [{'data': colorado_cisco_af, 'label': 'Colorado at Cisco', 'color': 'darkblue'},
                {'data': green_river_af, 'label': 'Green at Green River', 'color': 'royalblue'},
                {'data': san_juan_af, 'label': 'San Juan at Bluff', 'color': 'cornflowerblue'},
                {'data': dirty_devil_af, 'label': 'Dirty Devil', 'color': 'lightblue'},
                ]
    graph.bars_stacked(bar_data, sub_plot=0, title='USGS Lake Powell River Inflows',
                       ymin=0, ymax=22000000, yinterval=1000000,
                       xlabel='Water Year', xinterval=year_interval,
                       ylabel='maf', format_func=WaterGraph.format_maf, vertical=True)
    total = util.add3_annual(colorado_cisco_af, green_river_af, san_juan_af)
    graph.running_average(total, 10, sub_plot=0)

    graph.bars(annual_inflow_af, sub_plot=1, title='USBR RISE Lake Powell Inflow',
               ymin=0, ymax=22000000, yinterval=1000000, xinterval=year_interval,
               ylabel='maf',  format_func=WaterGraph.format_maf)
    graph.fig.waitforbuttonpress()


def lake_mead_inflow():
    start_year = 1964
    end_year = current_last_year
    year_interval = 3

    show_graph = False
    usgs_little_colorado_gage = usgs.az.little_colorado_cameron(graph=show_graph)
    little_colorado_af = usgs_little_colorado_gage.annual_af(water_year_month=10,
                                                             start_year=start_year, end_year=end_year)
    usgs_virgin_gage = usgs.az.virgin_at_littlefield(graph=show_graph)
    virgin_af = usgs_virgin_gage.annual_af(water_year_month=10, start_year=start_year, end_year=end_year)
    usgs_muddy_gage = usgs.nv.muddy_near_glendale(graph=show_graph)
    muddy_af = usgs_muddy_gage.annual_af(water_year_month=10, start_year=start_year, end_year=end_year)

    lees_ferry_gage = usgs.az.lees_ferry(graph=show_graph)
    lees_ferry_af = lees_ferry_gage.annual_af(water_year_month=10, start_year=start_year, end_year=end_year)

    glen_canyon_annual_release_af = usbr_glen_canyon_annual_release_af(graph=show_graph,
                                                                       start_year=start_year, end_year=end_year)
    paria_annual_af = usgs.az.paria_lees_ferry(graph=show_graph).annual_af(water_year_month=10,
                                                                           start_year=start_year, end_year=end_year)

    glen_canyon_plus_paria_af = util.add_annual(glen_canyon_annual_release_af, paria_annual_af)
    glen_canyon_seep_af = util.subtract_annual(lees_ferry_af, glen_canyon_plus_paria_af)

    # Add paria to Glen Canyon
    # Subtract from Lee's Ferry

    # Stacked graph of the four inputs
    # Compare to USBR side flows from 24 month
    graph = WaterGraph(nrows=2)
    graph.bars(glen_canyon_seep_af, sub_plot=0, title='Glen Canyon + Paria - Lees Ferry Gage',
               ymin=0, ymax=300000, yinterval=50000, xinterval=year_interval,
               ylabel='kaf',  format_func=WaterGraph.format_kaf)
    bar_data = [{'data': glen_canyon_seep_af, 'label': 'Theoretical Glen Canyon Seep', 'color': 'royalblue'},
                {'data': little_colorado_af, 'label': 'Little Colorado at Cameron', 'color': 'darkred'},
                {'data': virgin_af, 'label': 'Virgin at Littlefield', 'color': 'firebrick'},
                {'data': muddy_af, 'label': 'Muddy at Glendale', 'color': 'lightcoral'},
                ]
    graph.bars_stacked(bar_data, sub_plot=1, title='Lake Mead Inflows Excluding Glen Canyon Release',
                       ymin=0, ymax=1150000, yinterval=100000,
                       xlabel='Water Year', xinterval=year_interval,
                       ylabel='kaf', format_func=WaterGraph.format_kaf, vertical=True)
    total = util.add3_annual(little_colorado_af, virgin_af, muddy_af)
    total = util.add_annual(total, glen_canyon_seep_af)
    graph.annotate_vertical_arrow(2005, "Big Monsoon", sub_plot=1, offset_percent=5.0)
    graph.annotate_vertical_arrow(2017, "May Rain", sub_plot=1, offset_percent=40.0)
    graph.annotate_vertical_arrow(2019, "Spring Bomb Cyclone", sub_plot=1, offset_percent=30.0)

    graph.running_average(total, 10, sub_plot=1)
    graph.fig.waitforbuttonpress()


def usgs_lower_colorado_to_border_gages():
    usgs.az.unit_b_canal_near_yuma()

    usgs.az.gila_gravity_main_canal()
    all_american_model()
    usgs.lc.below_imperial()
    usgs.az.north_gila_main_canal()
    usgs.ca.reservation_main_canal()
    usgs.lc.below_laguna()

    usgs.az.wellton_mohawk_main_canal()
    usgs.az.wellton_mohawk_main_outlet_drain()

    usgs.az.yuma_main_canal()
    usgs.az.yuma_main_canal_wasteway()

    usgs.lc.below_yuma_wasteway()
    usgs.lc.northern_international_border()


def usgs_all_american_canal():
    # Imperial, Yuma, Coachella, Infer Alamo/Mexico (all american below imperial dam - coachella - drop_2)
    all_american_model()
    usgs.ca.imperial_all_american_drop_2()
    usgs.ca.coachella_all_american()


def usbr_lower_basin_states_total_use():
    year_interval = 3
    graph = WaterGraph(nrows=3)

    # CA Total Diversion & Consumptive Use
    ca_diversion_monthly_af = usbr_report.load_monthly_csv('ca/usbr_ca_total_diversion.csv')
    ca_diversion_annual_af = usbr_report.monthly_to_water_year(ca_diversion_monthly_af, water_year_month=1)

    ca_use_monthly_af = usbr_report.load_monthly_csv('ca/usbr_ca_total_consumptive_use.csv')
    ca_use_annual_af = usbr_report.monthly_to_water_year(ca_use_monthly_af, water_year_month=1)

    bar_data = [{'data': ca_diversion_annual_af, 'label': 'California Diversion', 'color': 'darkmagenta'},
                {'data': ca_use_annual_af, 'label': 'California Consumptive Use', 'color': 'firebrick'},
                ]
    graph.bars_stacked(bar_data, sub_plot=0, title='California Totals (Annual)',
                       ymin=0, ymax=6000000, yinterval=1000000,
                       xlabel='', xinterval=year_interval,
                       ylabel='maf', format_func=WaterGraph.format_maf, vertical=False)
    graph.running_average(ca_use_annual_af, 10, sub_plot=0)

    # AZ Total Diversion & Consumptive Use
    az_diversion_monthly_af = usbr_report.load_monthly_csv('az/usbr_az_total_diversion.csv')
    az_diversion_annual_af = usbr_report.monthly_to_water_year(az_diversion_monthly_af, water_year_month=1)

    az_use_monthly_af = usbr_report.load_monthly_csv('az/usbr_az_total_consumptive_use.csv')
    az_use_annual_af = usbr_report.monthly_to_water_year(az_use_monthly_af, water_year_month=1)

    bar_data = [{'data': az_diversion_annual_af, 'label': 'Arizona Diversion', 'color': 'darkmagenta'},
                {'data': az_use_annual_af, 'label': 'Arizona Consumptive Use', 'color': 'firebrick'},
                ]
    graph.bars_stacked(bar_data, sub_plot=1, title='Arizona Totals (Annual)',
                       ymin=0, ymax=4000000, yinterval=500000,
                       xlabel='', xinterval=year_interval,
                       ylabel='maf', format_func=WaterGraph.format_maf, vertical=False)
    graph.running_average(az_use_annual_af, 10, sub_plot=1)

    # NV Total Diversion & Consumptive Use
    nv_diversion_monthly_af = usbr_report.load_monthly_csv('nv/usbr_nv_total_diversion.csv')
    nv_diversion_annual_af = usbr_report.monthly_to_water_year(nv_diversion_monthly_af, water_year_month=1)

    nv_use_monthly_af = usbr_report.load_monthly_csv('nv/usbr_nv_total_consumptive_use.csv')
    nv_use_annual_af = usbr_report.monthly_to_water_year(nv_use_monthly_af, water_year_month=1)

    bar_data = [{'data': nv_diversion_annual_af, 'label': 'Nevada Diversion', 'color': 'darkmagenta'},
                {'data': nv_use_annual_af, 'label': 'Nevada Consumptive Use', 'color': 'firebrick'},
                ]
    graph.bars_stacked(bar_data, sub_plot=2, title='Nevada Totals (Annual)',
                       ymin=0, ymax=550000, yinterval=50000,
                       xlabel='Calendar Year', xinterval=year_interval,
                       ylabel='kaf', format_func=WaterGraph.format_kaf, vertical=False)
    graph.running_average(nv_use_annual_af, 10, sub_plot=2)

    graph.fig.waitforbuttonpress()

    # Total use as stacked bars
    total_use_annual_af = np.zeros(len(ca_use_annual_af), [('dt', 'i'), ('val', 'f')])
    total_use_annual_af['dt'] = ca_use_annual_af['dt']
    total_use_annual_af['val'] = ca_use_annual_af['val']
    total_use_annual_af['val'] += az_use_annual_af['val']
    total_use_annual_af['val'] += nv_use_annual_af['val']

    # total_diversion_annual_af = np.zeros(len(ca_diversion_annual_af), [('dt', 'i'), ('val', 'f')])
    # total_diversion_annual_af['dt'] = ca_diversion_annual_af['dt']
    # total_diversion_annual_af['val'] = ca_diversion_annual_af['val']
    # total_diversion_annual_af['val'] += az_diversion_annual_af['val']
    # total_diversion_annual_af['val'] += nv_diversion_annual_af['val']

    # diversion_above_use_annual_af = np.zeros(len(ca_diversion_annual_af), [('dt', 'i'), ('val', 'f')])
    # diversion_above_use_annual_af['dt'] = ca_diversion_annual_af['dt']
    # diversion_above_use_annual_af['val'] = total_diversion_annual_af['val']
    # diversion_above_use_annual_af['val'] -= total_use_annual_af['val']
    graph = WaterGraph(nrows=1)

    bar_data = [{'data': ca_use_annual_af, 'label': 'California Consumptive Use', 'color': 'maroon'},
                {'data': az_use_annual_af, 'label': 'Arizona Consumptive Use', 'color': 'firebrick'},
                {'data': nv_use_annual_af, 'label': 'Nevada Consumptive Use', 'color': 'lightcoral'},
                # {'data': diversion_above_use_annual_af, 'label': 'Total Diversions', 'color': 'darkmagenta'},
                ]
    graph.bars_stacked(bar_data, sub_plot=0, title='Total Lower Basin Consumptive Use (Annual)',
                       ymin=0, ymax=9000000, yinterval=500000,
                       xlabel='Calendar Year', xinterval=year_interval,
                       ylabel='maf', format_func=WaterGraph.format_maf)
    graph.running_average(total_use_annual_af, 10, sub_plot=0)
    graph.fig.waitforbuttonpress()


# noinspection PyUnusedLocal
def keyboardInterruptHandler(sig, frame):
    global interrupted
    interrupted = True

    try:
        print("exit")
        sys.exit(0)
    except OSError as e:
        print("riverwar exit exception:", e)


def yuma_area_model():
    year_interval = 4
    graph = WaterGraph(nrows=1)
    data = usbr.az.yuma_area_returns()
    graph.bars_stacked(data, sub_plot=0, title='Yuma Area Model',
                       ymin=0, ymax=600000, yinterval=50000,
                       xlabel='Calendar Year', xinterval=year_interval,
                       ylabel='kaf', format_func=WaterGraph.format_kaf)
    #graph.running_average(total_use_annual_af, 10, sub_plot=0)
    graph.fig.waitforbuttonpress()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, keyboardInterruptHandler)

    # usbr_catalog()
    yuma_area_model()
    usbr_lower_basin_states_total_use()
    lake_mead_inflow()
    lake_powell_inflow()
    all_american_model()
    usbr_glen_canyon_annual_release_af()
    glen_canyon_analysis()

    usgs.az.test()
    usgs.lc.test()
    usgs.ca.test()
    usgs.nv.test()
    usgs.co.test()

    usbr.az.yuma_mesa()
    usbr.az.yuma_county_water_users_assoociation()
    usbr.az.wellton_mohawk()

    usbr.nv.test()
    usbr.lc.test()
    usbr.uc.test()
    usbr.az.test()
    usbr.ca.test()
    usbr.uc.test()
