# -*- coding: UTF-8 -*-

###########################
###### Update logger ######
###########################
# 2022.09.09 User Defined PSS avaiable                      by Y.Meng
# 2022.09.09 FY 4 Variation updated into model              by Y.Meng
# 2022.08.26 fusion the single station & Multi station func by Y.Meng
# 2022.08.19 optimization for nio & non nio user grouping   by Y.Meng
# 2022.08.18 adding labeling for Non NIO user               by Y.Meng
# 2022.08.08 modify user service time dist plot             by Y.Meng
# 2022.08.03 plot optimization                              by Y.Meng
# 2022.08.01 coding review                                  by Y.Meng 
# 2022.07.25 init generation                                by Y.Meng
###########################

##################################
######## Import packages #########
##################################
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.pyplot import MultipleLocator
import datetime
from datetime import datetime as dt
import streamlit as st
from PIL import Image
import pandas as pd
import numpy as np
import random

# import the model and global parameters
import main
import global_param
GC = global_param.Global_Constant()

##################################
##### Function Declaration #######
##################################

# function for calculating the energy consumption
@st.cache
def energy_calc(power, time_interval):
    energy = 0
    for i in range(len(power)):
        energy += time_interval * power[i] / 3600 # kWh
    return energy

# calculate the area user number, divide them randomly to the respective stations
@st.cache
def areaNumDivision(station_num, area_user_num):
    result = []
    remain = station_num
    max_num = int((area_user_num / station_num) * 1.5) # upper limit of each slice
    min_num = int((area_user_num / station_num) * 0.5) # lower limit of each slice
    for i in range(station_num):
        remain -= 1
        if remain > 0:
            if remain <= area_user_num: # num of area user >= num of remaining station num
                slice_num = random.randint(min_num, min(area_user_num - remain, max_num))
            else:
                slice_num = random.randint(0, area_user_num)
        else: # if all number of user divided, then rests are 0
            slice_num = area_user_num
        result.append(slice_num)
        area_user_num -= slice_num
    return result # return the sliced number list

# convert the dataframe into csv format
@st.cache
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

##################################
######## Set up Web config #######
##################################

################################################################################
##################### Part 0: Set up Web Notation ##############################
################################################################################
logo = Image.open("image/NIO_logo.png")
left_col, right_col = st.columns([4,1])
with left_col:
    st.title("NIO Multistation Interactive Tech-Platform (MIT)")
with right_col:
    st.image(logo)
st.markdown("## Developed by NIO Power EU Team (Munich)")
st.markdown("This application is developed and maintained by NIO Power EU, which is used to analyze \
            the service ability of NIO Power Swap Station, and is used to assist clients in \
            customizing services. The current version is only used for internal test.\
             Users should abide by the NIO sensitive information protection clause, prohibit the \
            application from being open source to the outside. NIO Power EU reserves all rights to this Application.")

image = Image.open('image/image.png')
st.image(image)
st.write("")
###############################################################################
######################### Part 1: Set up App Layout ###########################
###############################################################################

# for main page
st.markdown("# Step 1: PSS configuration")
tab1, tab2 = st.tabs(["Single Station", "Multiple Stations"])
with tab1:
    col_l1, col_r1 = st.columns(2)
    col_l2, col_r2 = st.columns(2)
    col_l3, col_r3 = st.columns(2)
    col_l4, col_r4 = st.columns(2)
    col_l5, col_r5 = st.columns(2)
    col_l6, col_r6 = st.columns(2)
    col_l7, col_r7 = st.columns(2)
    
    st.markdown("# Step 2: Simulation Initiation")
    st.write("Press the button to start the simulation")
    _, col_m1, _ = st.columns(3)
    success_info_single_station = st.container()
    single_station_result = st.container()

with tab2:
    col_l8, col_r8   = st.columns(2)
    col_l9, col_r9   = st.columns(2)
    col_l10, col_r10 = st.columns(2)
    col_l11, col_r11 = st.columns(2)
    col_l12, col_r12 = st.columns(2)
    col_l13, col_r13 = st.columns(2)
    col_l14, col_r14 = st.columns(2)
    col_l15, col_r15 = st.columns(2)
    col_l16, col_r16 = st.columns(2)
    col_l17, col_r17 = st.columns(2)
    st.markdown("# Step 2: Simulation Initiation")
    st.write("Press the button to start the simulation")
    _, col_m2, _ = st.columns(3)
    success_info_multiple_station = st.container()
    multiple_station_result = st.container()


###############################################################################
######################### Part 2: Single station Set up #######################
###############################################################################
with col_l1: # pss type
    st.write("")
    st.markdown("### PSS Type")
    pss_candidates = ["PSS 2.0 - 500kW", "PSS 3.0 PUS A - 600kW", "PSS 3.0 PUS B - 1200kW",
                        "FY_TypeA - 600kW", "FY_TypeB - 630kW", "FY_TypeC - 1320kW", "FY_TypeD - 600kW", "User Defined"]
    tab3, tab4, tab5 = st.tabs(["PSS Type", "Swap Time", "Power Module"])
    with tab3: # PSS Type
        type_pss = st.selectbox("Select the Power Swap Station(PSS) type", pss_candidates, index=0)
        if type_pss == "PSS 2.0 - 500kW":
            station_type = GC.GEN2_530kW
            default_swap_time = 6.5
        elif type_pss == "PSS 3.0 PUS A - 600kW":
            station_type = GC.GEN3_600kW
            default_swap_time = 4.5
        elif type_pss == "PSS 3.0 PUS B - 1200kW":
            station_type = GC.GEN3_1200kW
            default_swap_time = 4.5
        elif type_pss == "FY_TypeA - 600kW":
            station_type = GC.FY_TypeA
            default_swap_time = 3.0
        elif type_pss == "FY_TypeB - 630kW":
            station_type = GC.FY_TypeB
            default_swap_time = 3.0
        elif type_pss == "FY_TypeC - 1320kW":
            station_type = GC.FY_TypeC
            default_swap_time = 3.0
        elif type_pss == "FY_TypeD - 600kW":
            station_type = GC.FY_TypeD
            default_swap_time = 3.0
        else:
            station_type = GC.User_Defined
            default_swap_time = 3.0
    with tab4: # Swap Time
        min_swap_time = 3.0
        max_swap_time = 10.0
        swap_time = st.slider("Set up the swap time of each NIO user [min]", min_value=min_swap_time, max_value=max_swap_time, value=default_swap_time, step=0.1)
    with tab5: # Power Module
        if type_pss == "User Defined":
            pm_catalog = ["20kW", "30kW", "40kW", "60kW", "80kW"]
            power_module_type = st.selectbox("Select the power module type", options=pm_catalog, index=3)
            power_module_number = st.number_input("Give the power module number (max 100)", min_value=1, max_value=100, value=10)
            # power_module_config = {"Type":power_module_type, "Number":power_module_number}
            power_module_type = GC.power_module_catalog[power_module_type] # UUxxkW dict
            station_type["max_charger_number"] = power_module_number
            station_type["power_module_type"] = power_module_type
            station_type["max_power"] = int(station_type["power_module_type"]["max_power"] * power_module_number)
        else:
            st.write("Selected the PSS type doesn't support for power modules configuration.")    
    st.write("")

with col_r1: # psc num
    # set up the number of PSC
    st.write("")
    st.markdown("### Number of PSC")
    if type_pss == "PSS 3.0 PUS A - 600kW":
        psc_num = st.number_input("Select the number of PSC equipped with PSS", min_value=0, \
            max_value=station_type["max_charge_terminal"], value=station_type["max_charge_terminal"], step=1)      
        st.write("The number of PSC is: ", psc_num)
    elif type_pss == "PSS 3.0 PUS B - 1200kW":
        psc_num = st.number_input("Select the number of PSC equipped with PSS", min_value=0, \
            max_value=station_type["max_charge_terminal"], value=station_type["max_charge_terminal"], step=1)
        st.write("The number of PSC is: ", psc_num)
    elif type_pss == "User Defined":
        psc_num = st.number_input("Select the number of PSC equipped with PSS", min_value=0, \
            max_value=100, value=0, step=1)
        station_type["max_charge_terminal"] = psc_num
    else:
        psc_num = 0
        st.write("The selected PSS facility can not quipped with PSC, thus the number is 0.")
        st.empty()
    st.write("")

with col_l2: # user preference
    # set up the user preference
    st.write("")
    st.markdown("### User Preference")
    selection_candidates = ["markov","full_swap", "fixed_value"]
    help_descrip = "user preference mode indicates how the clients will select their service, \
        the behaviours of clients includes swap, charge, leave. In fixed_value mode, the ratio is: \
        swap : charge : leave = 70% : 30% : 0%. The preference modes can only be applied to NIO user group."
    if (type_pss == "PSS 2.0 - 500kW") or (psc_num == 0):
        user_preference = st.radio("Select the user preference mode",options=["full_swap"], help=help_descrip)
    else:
        user_preference = st.radio("Select the user preference mode",options=selection_candidates, help=help_descrip)
    st.write("")

with col_r2: # service ratio for "fixed value" preference option
    st.write("")
    st.markdown("### Service Ratio")
    if user_preference == "fixed_value":
        user_selection_ratio = st.slider("Select the service Swap : Charge ratio", min_value=0, max_value=100, value=70)
        st.write("The Swap : Charge ratio is %d %% : %d %%" %(user_selection_ratio, 100 - user_selection_ratio))
    else:
        user_selection_ratio = -1
        st.write("Service ratio is determined by the algorithms automatically.")
    st.write("")

with col_l3: # battery config
    # Battery type:
    st.write("")
    st.markdown("### Battery Type & Number")
    battery_help = "Select the number of battery 100kWh, the rest places will be filled with 75kWh"
    
    if type_pss == "PSS 2.0 - 500kW":
        num_battery_type1 = st.slider("Select the number of 100 kWh Batteries", min_value=0,\
             max_value=station_type["max_battery_number"], value=station_type["max_battery_number"], help=battery_help)
        num_battery_type2 = station_type["max_battery_number"] - num_battery_type1
        st.write("Battery configuration for 100kWh: ", num_battery_type1, " 75kWh: ", num_battery_type2)
        battery_config = {"100kWh": num_battery_type1, "75kWh": num_battery_type2}
    
    elif type_pss == "PSS 3.0 PUS A - 600kW" or type_pss == "PSS 3.0 PUS B - 1200kW":
        num_battery_type1 = st.slider("Select the number of 100 kWh Batteries", min_value=0,\
             max_value=station_type["max_battery_number"], value=station_type["max_battery_number"], help=battery_help)
        num_battery_type2 = station_type["max_battery_number"] - num_battery_type1
        st.write("Battery configuration for 100kWh: ", num_battery_type1, " 75kWh: ", num_battery_type2)
        battery_config = {"100kWh": num_battery_type1, "75kWh": num_battery_type2}
    
    elif type_pss == "User Defined":
        tab6, tab7 = st.tabs(["NIO battery", "FY battery"])
        num_FY_1 = 0
        num_FY_2 = 0
        num_nio_type1 = 0
        num_nio_type2 = 0
        num_nio_type3 = 0
        with tab6: # NIO
            if num_FY_1 + num_FY_2 == 0:
                num_nio_type1 = st.number_input("Give the number of 100 kWh battery", min_value=0, max_value=int(power_module_number - num_nio_type2 - num_nio_type3), value=int(power_module_number))
                num_nio_type2 = st.number_input("Give the number of 75 kWh battery", min_value=0, max_value=int(power_module_number - num_nio_type1 - num_nio_type3), value=0)
                num_nio_type3 = st.number_input("Give the number of 70 kWh battery", min_value=0, max_value=int(power_module_number - num_nio_type1 - num_nio_type2), value=0)
                battery_config = {"100kWh": num_nio_type1, "75kWh": num_nio_type2, "70kWh": num_nio_type3}
                station_type["max_battery_number"] = sum(battery_config.values())
            else:
                st.write("The number of FY battery is not 0")
        
        with tab7: # FY
            if (num_nio_type1 + num_nio_type2 + num_nio_type3) == 0:
                num_FY_1 = st.number_input("Give the number of FY 62 kWh battery", min_value=0, max_value=int(power_module_number - num_FY_2), value=int(power_module_number))
                num_FY_2 = st.number_input("Give the number of FY 41 kWh battery", min_value=0, max_value=int(power_module_number - num_FY_1), value=0)
                battery_config = {"FY62kWh":num_FY_1, "FY41kWh":num_FY_2}
                station_type["max_battery_number"] = sum(battery_config.values())
            else:
                st.write("The number of NIO battery is not 0")
        
    else:
        battery_help2 = "Select the number of battery 62kWh, the rest places will be filled with 41kWh"
        num_battery_type1 = st.slider("Select the number of FY 62 kWh Batteries", min_value=0,\
             max_value=station_type["max_battery_number"], value=station_type["max_battery_number"],\
                help=battery_help2)
        num_battery_type2 = station_type["max_battery_number"] - num_battery_type1
        st.write("Battery of FY 62 kWh: ", num_battery_type1, " FY 41 kWh: ", num_battery_type2)
        battery_config = {"FY62kWh": num_battery_type1, "FY41kWh": num_battery_type2}
    st.write("")

with col_l4: # battery init soc
    # Battery initial soc:
    st.write("")
    st.markdown("### Battery Initial SOC")
    init_battery_soc = st.slider("Select the battery initial SOC in PSS", min_value=0.0, max_value=1.0, value=0.95, step=0.05)
    st.write("Initial battery soc: ", init_battery_soc)
    st.write("")

with col_r3: # battery target soc
    st.write("")
    # Battery target soc:
    st.markdown("### PSC Target SOC")
    help_target_soc = "User charge the vehicle battery with PSC, when the SOC reaches this target, they will leave."
    target_soc = st.slider("Select the charging target SOC for charge piles", min_value=0.5, max_value=1.0, value=0.9, step=0.05, help=help_target_soc)
    st.write("Target battery soc: ", target_soc)
    st.write("")

with col_r4: # battery selection soc
    # Battery select soc:
    st.write("")
    st.markdown("### PSS Selection SOC")
    help5 = "The swapping service can be performed only when there are batteries reach this SOC"
    select_soc = st.slider("Select the battery output SOC from PSS", min_value=0.5, max_value=1.0, value=0.95, step=0.05, help=help5)
    st.write("Selection battery soc: ", select_soc)
    st.write("")

with col_l5: # queue mode
    # User queue generation modes selection:
    st.write("")
    st.markdown("### Queue Generation")
    user_queue_mode = st.selectbox("Select the generation mode of user queue", ("random", "statistical"), index=0)
    # st.write("The user queue generation mode is: ", user_queue_mode)
    st.write("")

with col_r5: # nio user num
    st.write("")
    # User Queue Generation mode = "random" -> Select daily user number
    if user_queue_mode == "random":
        # Daily user:
        st.markdown("### Number of NIO Clients")
        nio_user_num = st.number_input("Give the number of daily clients that will use this PSS", min_value=1, max_value=300, value=100, step=5)
        # st.write("The number of daily NIO clients are: ", nio_user_num)
        user_area = None
    
    # User Queue Generation mode = "statistical" -> Select PSS deployment area
    else:
        # User sequence generation area:
        st.markdown("### Simulation Area")
        user_area = st.selectbox("Select the area of PSS simulation", ("urban", "suburb/highway"), index=0)
        # st.write("The simulation area is ", user_area)
        nio_user_num = 0
    st.write("")

with col_l6: # power distribution strategy
    st.write("")
    st.markdown("### Power Distribution")
    help_power_dist = "When select 'PSS prefered', the power modules will preferentially supply the battery in the station,\
         and then the redundancy will be allocated to the PSC; otherwise the PSCs have the highest priority to use the power module."
    if type_pss == "PSS 2.0 - 500kW" or psc_num == 0:
        st.write("This type of PSS is not equipped with PSC, only swap service avaiable.")
        power_dist_option = "PSS preferred"
    else:
        power_dist_option = st.selectbox("Select the Power distribution Strategy", ["PSS preferred", "PSC preferred"], help=help_power_dist)
    st.write("")

with col_r6: # non nio user num
    # set up the Non NIO user number
    st.write("")
    st.markdown("### Number of Non-NIO Clients")
    if psc_num == 0:
        st.write("This type of PSS is not equipped with PSC, the Non NIO users can not use this PSS facility.")
        non_nio_user_num = 0
    else:
        help_desp = "Non-NIO user belongs to third party, they can only use the PSC charge service of PSS."
        non_nio_user_num = st.number_input("Give the number of Non-NIO user", min_value=0, max_value=50, value=0, step=1, help=help_desp)
        # st.write("The number of daily Non-NIO clients are: ", non_nio_user_num)
    st.write("")

# with col_l7: # power redistribution trigger
#     # Charge Power redistribution:
#     st.write("")
#     st.markdown("### Power Module Rearrange")
#     help4 = "If activated, the power module will be redistributed after every simulation iterations(10 sec),\
#      the PSC clients may lose their charge priority. We recommend using the default configuration, which means False "
#     charge_power_redist = st.radio("Power module redistribution activation",[True, False], index=1, help=help4)
#     # st.write("The selection is:", charge_power_redist)
#     st.write("")

# with col_r7: # battery rack switch trigger
#     # Battery transport within racks:
#     st.write("")
#     st.markdown("### Battery Rack Switch")
#     help3 = "If activated, the full charged battery will be automatically transported to the rack where there\
#      has no charging ability. We recommend using the default configuration, which means True"
#     switch_flag = st.radio("Battery rack transfer activation", [True, False], index=0, help=help3)
#     if switch_flag:
#         enable_switch = 1
#         # st.write("Selection: Switch allowed")
#     else:
#         enable_switch = 0
#         # st.write("Selection: Switch not allowed")
#     st.write("")

with col_l7: # trigger of Grid interactive
    st.write("")
    st.markdown("### Grid Interaction Trigger")
    grid_interaction_help = "Grid Interaction is the behaviour that allows the PSS take part in the Grid \
        Frequency Balancing by discharging a small part of Energy stored in the batteries. This behaviour will be \
        initiated while a swap service is executed. By default this functionality is deactivated."
    grid_interaction_trigger = st.radio("Request for activating the grid interaction", [True, False], index=1, help=grid_interaction_help)
    st.write("")

with col_r7: # grid interactive time interval
    st.write("")
    st.markdown("### Grid Interaction Time Interval")
    if grid_interaction_trigger == False:
        st.write("The Grid interaction Function is deactivated")
        # idx = -1 means deactivated
        grid_interaction_interval_idx = -1
        interaction_num = 0
    else:
        tab8, tab9 = st.tabs(["Time Interval", "Number of Interactions"])
        with tab8:
            timeIntervalHelp = "The Grid interaction will be executed while swap service btw the selected time interval."
            timeOption = ["0:00 - 1:00", "1:00 - 2:00", "2:00 - 3:00", "3:00 - 4:00", 
                            "4:00 - 5:00", "5:00 - 6:00", "6:00 - 7:00", "7:00 - 8:00",
                            "8:00 - 9:00", "9:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00",
                            "12:00 - 13:00", "13:00 - 14:00", "14:00 - 15:00", "15:00 - 16:00",
                            "16:00 - 17:00", "17:00 - 18:00", "18:00 - 19:00", "19:00 - 20:00",
                            "20:00 - 21:00", "21:00 - 22:00", "22:00 - 23:00", "23:00 - 00:00"]
            grid_interaction_interval = st.selectbox("Select the executing time interval of Grid interaction", options=timeOption, help=timeIntervalHelp)
            grid_interaction_interval_idx = timeOption.index(grid_interaction_interval)
        with tab9:
            numIntervalHelp = "The number of interactions will be performed while user occupying the swap station, \
                if the number of user within selected time not sufficient, interaction behaviour will be skipped."
            interaction_num = st.slider("Select the number of interactions that will be performed within the interval", 1, 6, help=numIntervalHelp)
    st.write("")

with col_m1:
    ######################################################################
    ########### Excute the simulation if the button is pressed ###########
    ######################################################################
    st.write("===========================")
    button_flag_1 = st.button("Start Single Station Simulation")
    st.write("===========================")

if button_flag_1 == True:
    with st.spinner("simulation excuting..."):
        # Perform Simulation
        ####################################################################################################
        # collect the setup congiuration into dict "param", prepare to transport into do_simulation(param) #
        ####################################################################################################
        sim_interval = 10
        sim_days = 1
        sim_ticks = int(sim_days * 24 * 60 * 60 / sim_interval)  

        param = {
            "station_type" : station_type,                                      # set up the PSS type GEN3_600kW, GEN3_1200kW
            "psc_num" : psc_num,                                                # set up the PSC number according to the type of PSS
            "battery_config" : battery_config,                                  # set up the battery configuration in a swap rack module
            "init_battery_soc_in_PSS" : init_battery_soc,                       # set up the initial battery soc in PSS
            "target_soc" : target_soc,                                          # set up the charge target soc
            "select_soc" : select_soc,                                          # set up the which soc of battery in PSS will be selected to swap
            "nio_user_num" : nio_user_num,                                      # set up how many users in a day will use the PSS
            "non_nio_user_num" : non_nio_user_num,                              # set up the number of non nio user
            "sim_days" : sim_days,                                              # set up the simulation day loop
            "sim_interval" : sim_interval,                                      # set up the simulation interval, unit: sec
            "sim_ticks" : sim_ticks,                                            # calculate how many simulation bins in a day loop
            "swap_rack_temperature" : 25,                                       # set up the rack temperature
            "user_sequence_mode" : user_queue_mode,                             # "random" for random sequence create based on distribution defined by user_sequence_random_file
                                                                                # "statistical" generate user sequence based on real statistical data
            "user_area" : user_area,                                            # set up the simulation area for statistical mode
            "user_preference" : user_preference,                                # define the user selection preference in markov, full swap, or fixed value (70% swap, and 30% charge)
            "charge_power_redist" : False,                                      # True: modules will be redistributed after every sim interval, if there exists charging pile, they will be disconnected
                                                                                # False: modules once be connected to outer charging piles, they are not allowed be disconnected until vehicle leaves
            "enable_me_switch" : 1,                                             # define whether the transport btw the battery rack is allowed, 1 means allowable, 0 not allowable
            "power_dist_option" : power_dist_option,                            # define which facility has higher power dist priority PSS or PSC
            "service_ratio": user_selection_ratio,                              # when select fixed ratio of service, configure the specific value
            "grid_interaction_idx" : grid_interaction_interval_idx,             # the time interval of execution of grid interaction, -1 -> service deactivated
            "interaction_num" : interaction_num,                                # define the times that interaction will perform
            "swap_time" : swap_time                                             # configure the swap time
        }

        # container preparation
        user_dist_lst = []
        power_history = []
        residual_power = []
        swap_list = []
        nio_charge_list = []
        non_nio_charge_list = []
        power_mean_list = []
        max_power = 0
        nio_average_time_charge = 0
        non_nio_average_time_chagre = 0
        average_time_swap = 0
        swap_ratio_in_15_min = 0
        queue_length_swap = []
        queue_length_charge = []
        queue_overflow_number = []
        queue_overflow_ratio = 0

        # perform simulation 
        swap_user_wait_time, charge_user_wait_time, queue_length_swap, queue_length_charge, user_dist_lst, max_power, power_history, residual_power, swap_list, \
        nio_charge_list, non_nio_charge_list, average_time_swap, nio_average_time_charge, non_nio_average_time_chagre, swap_ratio_in_15_min = main.do_simulation(param = param)
        
        # 1. calculate time step
        day_step = sim_days + 1
        date1 = datetime.date(2022,1,1)
        date2 = datetime.date(2022,1,day_step)
        delta = datetime.timedelta(seconds = sim_interval)
        dates = mdates.drange(date1, date2, delta)
        
        # 2. success ratio within 15 min
        ratio_persentage = swap_ratio_in_15_min * 100

        # 3. energy consumption
        y_func = []
        y_grid_func = []
        for pw in power_history:
            # collect the power distribution pro sim interval
            if pw[1] >= 0:
                y_func.append(pw[1])
                y_grid_func.append(0)
            else:
                y_func.append(0)
                y_grid_func.append(pw[1])
            
        
        power_mean = np.mean(y_func)
        for i in range(len(dates)):
            # collect the mean value of the power distribution
            power_mean_list.append(power_mean)      
        total_energy = energy_calc(y_func, sim_interval)
        grid_interaction_energy = abs(energy_calc(y_grid_func, sim_interval))

        # 4. total average charge time and charge rate calculation
        if nio_average_time_charge!=0 and non_nio_average_time_chagre!=0:
            total_average_charge_time = (nio_average_time_charge * len(nio_charge_list) + non_nio_average_time_chagre * len(non_nio_charge_list)) / (len(nio_charge_list) + len(non_nio_charge_list))
            total_charge_rate = 60 / total_average_charge_time
            nio_charge_rate = 60 / nio_average_time_charge
            non_nio_charge_rate = 60 / non_nio_average_time_chagre
        else:
            total_average_charge_time = 0
            total_charge_rate = 0
            nio_charge_rate = 0
            non_nio_charge_rate = 0
            
        if average_time_swap != 0:
            swap_rate = 60 / average_time_swap
        else:
            swap_rate = 0
        
        # 5. overflow of service user
        queue_overflow_number.append(queue_length_swap[-1])
        queue_overflow_number.append(queue_length_charge[-1])
        if len(user_dist_lst) != 0:
            queue_overflow_ratio = round((sum(queue_overflow_number) / len(user_dist_lst)) * 100, 2)
        else:
            queue_overflow_ratio = 0
        # ====================== summary the result in a table =============================

        result_data = {
            "Total Number of Serviced Swap Clients" : len(swap_list),
            "Total Number of Serviced Charge Clients" : len(nio_charge_list) + len(non_nio_charge_list),
            "Number of Serviced NIO Charge Clients" : len(nio_charge_list),
            "Number of Serviced Non NIO Charge Clients" : len(non_nio_charge_list),
            "Overflow Number of Swap Queue" : queue_overflow_number[0],
            "Overflow Number of Charge Queue" : queue_overflow_number[1],
            "Total Overflow Ratio [%]" : queue_overflow_ratio,
            "Total Energy [kWh]" : total_energy,
            "Grid Interaction Energy [kWh]" : grid_interaction_energy,
            "Swap Ratio in 15 Minutes [%]" : ratio_persentage,
            "Average Swap Time [minutes]" : average_time_swap,
            "Average Swap Rate [1/hours]" : swap_rate,
            "Average Charge Time for All Clients Group [minutes]" : total_average_charge_time,
            "Average Total Charge Rate [1/hours]" : total_charge_rate,
            "Average Charge Time for NIO Group [minutes]" : nio_average_time_charge,
            "Average Charge Rate for NIO Group [1/hours]" : nio_charge_rate,
            "Average Charge Time for Non NIO Group [minutes]" : non_nio_average_time_chagre,
            "Average Charge Time for Non NIO Group [1/hours]" : non_nio_charge_rate
        }

        result_data = pd.DataFrame.from_dict(result_data, orient='index', columns=['Values'])
        result_data = result_data.reset_index().rename(columns={'index': 'Key Characteristics'})
    success_info_single_station.success("simulation successfully excuted.")
st.write("")
st.write("")

#####################################################################################
######################### Part 3: Multiple Station Configurations ###################
#####################################################################################

with col_l8: # urban pss num
    # Number of urban station max 10
    st.write("")
    st.markdown("### Urban PSS Number")
    num_urban_pss = st.number_input("Set number of urban station", 0, 100, value=1)
    st.write("")

with col_r8: # suburb psc num
    # Number of highway station max 10
    st.write("")
    st.markdown("### Suburb PSS Number")
    num_suburb_pss = st.number_input("Set number of suburb station", 0, 100, value=1)
    st.write("")

with col_l9: # urban pss type
    # stationtype of urban PSS
    st.write("")
    st.markdown("### Urban PSS Set Up")
    urban_pss_candidates = ["PSS 2.0 - 500kW", "PSS 3.0 PUS A - 600kW", "PSS 3.0 PUS B - 1200kW", "User Defined"]
    tab10, tab11, tab12, tab13 = st.tabs(["PSS Type", "Swap Time", "Power Module", "PSC Number"])
    with tab10: # PSS Type
        type_urban_pss = st.selectbox("Set up the urban PSS configurations", urban_pss_candidates, index=0)
        if type_urban_pss == "PSS 2.0 - 500kW":
            urban_type = GC.GEN2_530kW
            default_swap_time_urban = 6.5
        elif type_urban_pss == "PSS 3.0 PUS A - 600kW":
            urban_type = GC.GEN3_600kW
            default_swap_time_urban = 4.5
        elif type_urban_pss == "PSS 3.0 PUS B - 1200kW":
            urban_type = GC.GEN3_1200kW
            default_swap_time_urban = 4.5
        else:
            urban_type = GC.User_Defined
            default_swap_time_urban = 3.0
    with tab11: # Swap Time
        min_swap_time = 3.0
        max_swap_time = 10.0
        urban_swap_time = st.slider("Set up the urban swap time of each NIO user [min]", min_value=min_swap_time, max_value=max_swap_time, value=default_swap_time_urban, step=0.1)
    with tab12: # Power Module
        if type_urban_pss == "User Defined":
            pm_catalog = ["20kW", "30kW", "40kW", "60kW", "80kW"]
            urban_power_module_type = st.selectbox("Select the urban power module type", options=pm_catalog, index=3)
            urban_power_module_number = st.number_input("Give the urban power module number (max 100)", min_value=1, max_value=100, value=10)
            urban_power_module_type = GC.power_module_catalog[urban_power_module_type] # UUxxkW dict
            urban_type["max_charger_number"] = urban_power_module_number
            urban_type["power_module_type"] = urban_power_module_type
            urban_type["max_power"] = int(urban_type["power_module_type"]["max_power"] * urban_power_module_number)
        else:
            st.write("Selected the PSS type doesn't support for power modules configuration.")    
    with tab13: # PSC number
        if type_urban_pss == "PSS 3.0 PUS A - 600kW":
            urban_psc_num = st.number_input("Select the number of PSC equipped with urban PSS", min_value=0, \
                max_value=urban_type["max_charge_terminal"], value=urban_type["max_charge_terminal"], step=1)      
            st.write("The number of PSC is: ", urban_psc_num)
        elif type_urban_pss == "PSS 3.0 PUS B - 1200kW":
            urban_psc_num = st.number_input("Select the number of PSC equipped with urban PSS", min_value=0, \
                max_value=urban_type["max_charge_terminal"], value=urban_type["max_charge_terminal"], step=1)
            st.write("The number of PSC is: ", urban_psc_num)
        elif type_urban_pss == "User Defined":
            urban_psc_num = st.number_input("Select the number of PSC equipped with urban PSS", min_value=0, \
                max_value=100, value=0, step=1)
            urban_type["max_charge_terminal"] = urban_psc_num
        else:
            urban_psc_num = 0
            st.write("The selected PSS facility can not quipped with PSC, thus the number is 0.")
            st.empty()
    st.write("")

with col_r9: # suburb pss type
    # stationtype of suburb PSS
    st.write("")
    st.markdown("### Suburb PSS Set Up")
    suburb_pss_candidates = ["PSS 2.0 - 500kW", "PSS 3.0 PUS A - 600kW", "PSS 3.0 PUS B - 1200kW", "User Defined"]
    tab14, tab15, tab16, tab17 = st.tabs(["PSS Type", "Swap Time", "Power Module", "PSC Number"])
    
    with tab14: # PSS Type
        type_suburb_pss = st.selectbox("Set up the suburb PSS configurations", suburb_pss_candidates, index=0)
        if type_suburb_pss == "PSS 2.0 - 500kW":
            suburb_type = GC.GEN2_530kW
            default_swap_time_suburb = 6.5
        elif type_suburb_pss == "PSS 3.0 PUS A - 600kW":
            suburb_type = GC.GEN3_600kW
            default_swap_time_suburb = 4.5
        elif type_suburb_pss == "PSS 3.0 PUS B - 1200kW":
            suburb_type = GC.GEN3_1200kW
            default_swap_time_suburb = 4.5
        else:
            suburb_type = GC.User_Defined
            default_swap_time_suburb = 3.0
    
    with tab15: # Swap Time
        min_swap_time = 3.0
        max_swap_time = 10.0
        suburb_swap_time = st.slider("Set up the suburb swap time of each NIO user [min]", min_value=min_swap_time, max_value=max_swap_time, value=default_swap_time_suburb, step=0.1)
    
    with tab16: # Power Module
        if type_suburb_pss == "User Defined":
            pm_catalog = ["20kW", "30kW", "40kW", "60kW", "80kW"]
            suburb_power_module_type = st.selectbox("Select the suburb power module type", options=pm_catalog, index=3)
            suburb_power_module_number = st.number_input("Give the suburb power module number (max 100)", min_value=1, max_value=100, value=10)
            suburb_power_module_type = GC.power_module_catalog[suburb_power_module_type] # UUxxkW dict
            suburb_type["max_charger_number"] = suburb_power_module_number
            suburb_type["power_module_type"] = suburb_power_module_type
            suburb_type["max_power"] = int(suburb_type["power_module_type"]["max_power"] * suburb_power_module_number)
        else:
            st.write("Selected the PSS type doesn't support for power modules configuration.")    
    
    with tab17: # PSC number
        if type_suburb_pss == "PSS 3.0 PUS A - 600kW":
            suburb_psc_num = st.number_input("Select the number of PSC equipped with suburb PSS", min_value=0, \
                max_value=suburb_type["max_charge_terminal"], value=suburb_type["max_charge_terminal"], step=1)      
            st.write("The number of PSC is: ", suburb_psc_num)
        elif type_suburb_pss == "PSS 3.0 PUS B - 1200kW":
            suburb_psc_num = st.number_input("Select the number of PSC equipped with suburb PSS", min_value=0, \
                max_value=suburb_type["max_charge_terminal"], value=suburb_type["max_charge_terminal"], step=1)
            st.write("The number of PSC is: ", suburb_psc_num)
        elif type_suburb_pss == "User Defined":
            suburb_psc_num = st.number_input("Select the number of PSC equipped with suburb PSS", min_value=0, \
                max_value=100, value=0, step=1)
            suburb_type["max_charge_terminal"] = suburb_psc_num
        else:
            suburb_psc_num = 0
            st.write("The selected PSS facility can not quipped with PSC, thus the number is 0.")
            st.empty()
    st.write("")

with col_l10: # urban battery config
    # Batttery config
    st.write("")
    st.markdown("### Urban Battery Set Up")
    if type_urban_pss == "PSS 2.0 - 500kW":
        urban_num_battery_type1 = st.slider("Select the number of 100 kWh Batteries (urban)", min_value=0, max_value=13, value=13)
        urban_num_battery_type2 = 13 - urban_num_battery_type1
        st.write("Battery number for 100kWh: ", urban_num_battery_type1, " 75kWh: ", urban_num_battery_type2)
        urban_battery_config = {"100kWh": urban_num_battery_type1, "75kWh": urban_num_battery_type2}
    
    elif type_urban_pss == "User Defined":
        tab18, tab19 = st.tabs(["NIO battery", "FY battery"])
        urban_num_FY_1 = 0
        urban_num_FY_2 = 0
        urban_num_nio_type1 = 0
        urban_num_nio_type2 = 0
        urban_num_nio_type3 = 0
        with tab18: # NIO
            if urban_num_FY_1 + urban_num_FY_2 == 0:
                urban_num_nio_type1 = st.number_input("Give the number of 100 kWh battery (urban)", min_value=0, max_value=int(urban_power_module_number - urban_num_nio_type2 - urban_num_nio_type3), value=int(urban_power_module_number))
                urban_num_nio_type2 = st.number_input("Give the number of 75 kWh battery (urban)", min_value=0, max_value=int(urban_power_module_number - urban_num_nio_type1 - urban_num_nio_type3), value=0)
                urban_num_nio_type3 = st.number_input("Give the number of 70 kWh battery (urban)", min_value=0, max_value=int(urban_power_module_number - urban_num_nio_type1 - urban_num_nio_type2), value=0)
                urban_battery_config = {"100kWh": urban_num_nio_type1, "75kWh": urban_num_nio_type2, "70kWh": urban_num_nio_type3}
                urban_type["max_battery_number"] = sum(battery_config.values())
            else:
                st.write("The number of FY battery is not 0")
        
        with tab19: # FY
            if (urban_num_nio_type1 + urban_num_nio_type2 + urban_num_nio_type3) == 0:
                urban_num_FY_1 = st.number_input("Give the number of FY 62 kWh battery (urban)", min_value=0, max_value=int(urban_power_module_number - urban_num_FY_2), value=int(urban_power_module_number))
                urban_num_FY_2 = st.number_input("Give the number of FY 41 kWh battery (urban)", min_value=0, max_value=int(urban_power_module_number - urban_num_FY_1), value=0)
                urban_battery_config = {"FY62kWh":urban_num_FY_1, "FY41kWh":urban_num_FY_2}
                urban_type["max_battery_number"] = sum(battery_config.values())
            else:
                st.write("The number of NIO battery is not 0")
    else:
        urban_num_battery_type1 = st.slider("Select the number of 100 kWh Batteries (urban)", min_value=0, max_value=20, value=20)
        urban_num_battery_type2 = 20 - urban_num_battery_type1
        st.write("Battery number for 100kWh: ", urban_num_battery_type1, " 75kWh: ", urban_num_battery_type2)
        urban_battery_config = {"100kWh": urban_num_battery_type1, "75kWh": urban_num_battery_type2}
    st.write("")

with col_r10: # suburb battery config
    # battery config
    st.write("")
    st.markdown("### Suburb Battery Set Up")
    if type_suburb_pss == "PSS 2.0 - 500kW":
        suburb_num_battery_type1 = st.slider("Select the number of 100 kWh Batteries (suburb)", min_value=0, max_value=13, value=13)
        suburb_num_battery_type2 = 13 - suburb_num_battery_type1
        st.write("Battery number for 100kWh: ", suburb_num_battery_type1, " 75kWh: ", suburb_num_battery_type2)
        suburb_battery_config = {"100kWh": suburb_num_battery_type1, "75kWh": suburb_num_battery_type2}
    
    elif type_suburb_pss == "User Defined":
        tab20, tab21 = st.tabs(["NIO battery", "FY battery"])
        suburb_num_FY_1 = 0
        suburb_num_FY_2 = 0
        suburb_num_nio_type1 = 0
        suburb_num_nio_type2 = 0
        suburb_num_nio_type3 = 0
        with tab20: # NIO
            if suburb_num_FY_1 + suburb_num_FY_2 == 0:
                suburb_num_nio_type1 = st.number_input("Give the number of 100 kWh battery (suburb)", min_value=0, max_value=int(suburb_power_module_number - suburb_num_nio_type2 - suburb_num_nio_type3), value=int(suburb_power_module_number))
                suburb_num_nio_type2 = st.number_input("Give the number of 75 kWh battery (suburb)", min_value=0, max_value=int(suburb_power_module_number - suburb_num_nio_type1 - suburb_num_nio_type3), value=0)
                suburb_num_nio_type3 = st.number_input("Give the number of 70 kWh battery (suburb)", min_value=0, max_value=int(suburb_power_module_number - suburb_num_nio_type1 - suburb_num_nio_type2), value=0)
                suburb_battery_config = {"100kWh": suburb_num_nio_type1, "75kWh": suburb_num_nio_type2, "70kWh": suburb_num_nio_type3}
                suburb_type["max_battery_number"] = sum(battery_config.values())
            else:
                st.write("The number of FY battery is not 0")
        
        with tab21: # FY
            if (suburb_num_nio_type1 + suburb_num_nio_type2 + suburb_num_nio_type3) == 0:
                suburb_num_FY_1 = st.number_input("Give the number of FY 62 kWh battery (suburb)", min_value=0, max_value=int(suburb_power_module_number - suburb_num_FY_2), value=int(suburb_power_module_number))
                suburb_num_FY_2 = st.number_input("Give the number of FY 41 kWh battery (suburb)", min_value=0, max_value=int(suburb_power_module_number - suburb_num_FY_1), value=0)
                suburb_battery_config = {"FY62kWh":suburb_num_FY_1, "FY41kWh":suburb_num_FY_2}
                suburb_type["max_battery_number"] = sum(battery_config.values())
            else:
                st.write("The number of NIO battery is not 0")
    else:
        suburb_num_battery_type1 = st.slider("Select the number of 100 kWh Batteries (suburb)", min_value=0, max_value=20, value=20)
        suburb_num_battery_type2 = 20 - suburb_num_battery_type1
        st.write("Battery number for 100kWh: ", suburb_num_battery_type1, " 75kWh: ", suburb_num_battery_type2)
        suburb_battery_config = {"100kWh": suburb_num_battery_type1, "75kWh": suburb_num_battery_type2}
    st.write("")

with col_l11: # grid interaction urban
    st.write("")
    st.markdown("### Urban Grid Interaction")
    tab22, tab23, tab24 = st.tabs(["Trigger", "Time Intrval", "Number of Interactions"])
    with tab22:
        grid_interaction_help = "Grid Interaction is the behaviour that allows the PSS take part in the Grid \
            Frequency Balancing by discharging a small part of Energy stored in the batteries. This behaviour will be \
            initiated while a swap service is executed. By default this functionality is deactivated."
        urban_grid_interaction_trigger = st.radio("Request for activating the urban grid interaction", [True, False], index=1, help=grid_interaction_help)
    
    with tab23:
        if urban_grid_interaction_trigger == False:
            st.write("Grid interaction deactivated.")
            urban_grid_interaction_interval_idx = -1
        
        else:
            timeIntervalHelp = "The Grid interaction will be executed while swap service btw the selected time interval."
            timeOption = ["0:00 - 1:00", "1:00 - 2:00", "2:00 - 3:00", "3:00 - 4:00", 
                            "4:00 - 5:00", "5:00 - 6:00", "6:00 - 7:00", "7:00 - 8:00",
                            "8:00 - 9:00", "9:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00",
                            "12:00 - 13:00", "13:00 - 14:00", "14:00 - 15:00", "15:00 - 16:00",
                            "16:00 - 17:00", "17:00 - 18:00", "18:00 - 19:00", "19:00 - 20:00",
                            "20:00 - 21:00", "21:00 - 22:00", "22:00 - 23:00", "23:00 - 00:00"]
            urban_grid_interaction_interval = st.selectbox("Select the executing time interval of Grid interaction (urban)", options=timeOption, help=timeIntervalHelp)
            urban_grid_interaction_interval_idx = timeOption.index(urban_grid_interaction_interval)

    with tab24:
        if urban_grid_interaction_trigger == False:
            st.write("Grid interaction deactivated.")
            urban_interaction_num = 0
        else:
            numIntervalHelp = "The number of interactions will be performed while user occupying the swap station, \
                if the number of user within selected time not sufficient, interaction behaviour will be skipped."
            urban_interaction_num = st.slider("Select the number of interactions that will be performed within the interval (urban)", 1, 6, help=numIntervalHelp)
    
    st.write("")

with col_r11: # grid interaction suburb
    st.write("")
    st.markdown("### Suburb Grid Interaction")
    tab25, tab26, tab27 = st.tabs(["Trigger", "Time Intrval", "Number of Interactions"])
    
    with tab25:
        grid_interaction_help = "Grid Interaction is the behaviour that allows the PSS take part in the Grid \
            Frequency Balancing by discharging a small part of Energy stored in the batteries. This behaviour will be \
            initiated while a swap service is executed. By default this functionality is deactivated."
        suburb_grid_interaction_trigger = st.radio("Request for activating the suburb grid interaction", [True, False], index=1, help=grid_interaction_help)
    
    with tab26:
        if suburb_grid_interaction_trigger == False:
            st.write("Grid interaction deactivated.")
            suburb_grid_interaction_interval_idx = -1
        
        else:
            timeIntervalHelp = "The Grid interaction will be executed while swap service btw the selected time interval."
            timeOption = ["0:00 - 1:00", "1:00 - 2:00", "2:00 - 3:00", "3:00 - 4:00", 
                            "4:00 - 5:00", "5:00 - 6:00", "6:00 - 7:00", "7:00 - 8:00",
                            "8:00 - 9:00", "9:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00",
                            "12:00 - 13:00", "13:00 - 14:00", "14:00 - 15:00", "15:00 - 16:00",
                            "16:00 - 17:00", "17:00 - 18:00", "18:00 - 19:00", "19:00 - 20:00",
                            "20:00 - 21:00", "21:00 - 22:00", "22:00 - 23:00", "23:00 - 00:00"]
            suburb_grid_interaction_interval = st.selectbox("Select the executing time interval of Grid interaction (suburb)", options=timeOption, help=timeIntervalHelp)
            suburb_grid_interaction_interval_idx = timeOption.index(urban_grid_interaction_interval)

    with tab27:
        if suburb_grid_interaction_trigger == False:
            st.write("Grid interaction deactivated.")
            suburb_interaction_num = 0
        else:
            numIntervalHelp = "The number of interactions will be performed while user occupying the swap station, \
                if the number of user within selected time not sufficient, interaction behaviour will be skipped."
            suburb_interaction_num = st.slider("Select the number of interactions that will be performed within the interval (suburb)", 1, 6, help=numIntervalHelp)
    
    st.write("")

# with col_l11: # urban psc num
#     # set up the number of PSC for urban station
#     st.write("")
#     st.markdown("### Urban PSC Number")
#     if type_urban_pss == "PSS 2.0 - 500kWh":
#         urban_psc_num = 0
#         st.write("The selected urban PSS facility can not quipped with PSC, thus the number is 0.")
#     else:
#         urban_psc_num = st.number_input("Select the number of PSC for urban stations", min_value=0, \
#             max_value=urban_type["max_charge_terminal"], value=urban_type["max_charge_terminal"], step=1)      
#         st.write("The number of PSC is: ", urban_psc_num)    
#     st.write("")

# with col_r11: # suburb psc num
#     # set up the number of PSC for suburb station
#     st.write("")
#     st.markdown("### Suburb PSC number")
#     if type_suburb_pss == "PSS 2.0 - 500kWh":
#         suburb_psc_num = 0
#         st.write("The selected suburb PSS facility can not quipped with PSC, thus the number is 0.")
#     else:
#         suburb_psc_num = st.number_input("Select the number of PSC for suburb stations", min_value=0, \
#             max_value=suburb_type["max_charge_terminal"], value=suburb_type["max_charge_terminal"], step=1)      
#         st.write("The number of PSC is: ", suburb_psc_num)
#     st.write("")

with col_l12: # urban power distribution
    st.write("")
    st.markdown("### Urban Power Distribution")
    help_power_dist = "When select 'PSS prefered', the power modules will preferentially supply the battery in the station,\
         and then the redundancy will be allocated to the PSC; otherwise the PSCs have the highest priority to use the power module."
    if type_urban_pss == "PSS 2.0 - 500kW" or urban_psc_num == 0:
        st.write("This type of PSS is not equipped with PSC, only swap service avaiable.")
        urban_power_dist_option = "PSS preferred"
    else:
        urban_power_dist_option = st.radio("Select the power distribution strategy for urban stations", ["PSS preferred", "PSC preferred"], help=help_power_dist)
    st.write("")

with col_r12: # suburb power distribution
    st.write("")
    st.markdown("### Suburb Power Distribution")
    help_power_dist = "When select 'PSS prefered', the power modules will preferentially supply the battery in the station,\
         and then the redundancy will be allocated to the PSC; otherwise the PSCs have the highest priority to use the power module."
    if type_suburb_pss == "PSS 2.0 - 500kW" or suburb_psc_num == 0:
        st.write("This type of PSS is not equipped with PSC, only swap service avaiable.")
        suburb_power_dist_option = "PSS preferred"
    else:
        suburb_power_dist_option = st.radio("Select the power distribution strategy for suburb stations", ["PSS preferred", "PSC preferred"], help=help_power_dist)
    st.write("")

with col_l13: # urban user preference
    # User perference
    st.write("")
    st.markdown("### Urban User Preference")
    selection_candidates_urban = ["markov","full_swap", "fixed_value"]
    help_descrip_urban = "user preference mode indicates how the clients will select their service, \
        the behaviours of clients includes swap, charge, leave. In fixed_value mode, the ratio of \
        swap:charge can be configured as customer wishes."
    label_urban = "Select the urban user preference mode"
    if type_urban_pss == "PSS 2.0 - 500kW" or urban_psc_num == 0:
        urban_user_preference = st.radio(label=label_urban, options=["full_swap"], help=help_descrip_urban)
    else:
        urban_user_preference = st.radio(label=label_urban, options=selection_candidates_urban, help=help_descrip_urban)
    st.write("")

with col_r13: # suburb user preference
    # User perference
    st.write("")
    st.markdown("### Suburb User Preference")
    selection_candidates_suburb = ["markov", "full_swap", "fixed_value"]
    help_descrip_suburb = "user preference mode indicates how the clients will select their service, \
        the behaviours of clients includes swap, charge, leave. In fixed_value mode, the ratio of \
        swap:charge can be configured as customer wishes."
    label_suburb = "Select the suburb user preference mode"
    if type_suburb_pss == "PSS 2.0 - 500kW" or suburb_psc_num == 0:
        suburb_user_preference = st.radio(label=label_suburb, options=["full_swap"], help=help_descrip_suburb)
    else:
        suburb_user_preference = st.radio(label=label_suburb, options=selection_candidates_suburb, help=help_descrip_suburb)
    st.write("")

with col_l14: # urban fixed value config
    st.write("")
    st.markdown("### Urban Service Ratio")
    if urban_user_preference == "fixed_value":
        urban_user_selection_ratio = st.slider("Select the service \"Swap : Charge\" ratio for urban users", min_value=0, max_value=100, value=70)
        st.write("The Swap : Charge ratio is %d %% : %d %%" %(urban_user_selection_ratio, 100 - urban_user_selection_ratio))
    else:
        urban_user_selection_ratio = -1
        st.write("Service ratio is determined by the algorithms automatically.")
    st.write("")

with col_r14: # suburb fixed value config
    st.write("")
    st.markdown("### Suburb Service Ratio")
    if suburb_user_preference == "fixed_value":
        suburb_user_selection_ratio = st.slider("Select the service \"Swap : Charge\" ratio for suburb users", min_value=0, max_value=100, value=70)
        st.write("The Swap : Charge ratio is %d %% : %d %%" %(suburb_user_selection_ratio, 100 - suburb_user_selection_ratio))
    else:
        suburb_user_selection_ratio = -1
        st.write("Service ratio is determined by the algorithms automatically.")
    st.write("")

with col_l15: # urban queue mode
    # User queue generation modes selection:
    st.write("")
    st.markdown("### Urban Queue Mode")
    urban_user_queue_mode = st.selectbox("Select the generation mode of urban user queue", ("random", "statistical"), index=0)
    st.write("")

with col_r15: # suburb queue mode
    # User queue generation modes selection:
    st.write("")
    st.markdown("### Suburb Queue Mode")
    suburb_user_queue_mode = st.selectbox("Select the generation mode of suburb user queue", ("random", "statistical"), index=0)
    st.write("")

with col_l16: # urban nio user num
    # User Queue Generation mode = "random" -> Select daily user number
    st.write("")
    st.markdown("### Urban NIO User Number")
    if urban_user_queue_mode == "random":
        urban_nio_user_num = st.number_input("Give the total number of NIO clients in urban area", min_value=int(num_urban_pss), max_value=20000, value=int(100*num_urban_pss), step=5)
        # st.write("The number of daily NIO clients are: ", urban_nio_user_num)
    else:
        st.write("The number of urban NIO users depends on the statistics.")
        urban_nio_user_num = 0
    st.write("")

with col_r16: # suburb nio user num
    # User Queue Generation mode = "random" -> Select daily user number
    st.write("")
    st.markdown("### Suburb NIO User Number")
    if suburb_user_queue_mode == "random":
        suburb_nio_user_num = st.number_input("Give the total number of NIO clients in suburb area", min_value=int(num_suburb_pss), max_value=20000, value=int(50*num_urban_pss), step=5)
        # st.write("The number of daily NIO clients are: ", suburb_nio_user_num)
    else:
        st.write("The number of suburb NIO users depends on the statistics.")
        suburb_nio_user_num = 0
    st.write("")

with col_l17: # urban non nio user num
    # set up the urban Non NIO user number
    st.write("")
    st.markdown("### Urban Non-NIO User Number")
    if urban_psc_num == 0:
        st.write("This type of PSS is not equipped with PSC, the Non NIO users can not use this PSS facility.")
        urban_non_nio_user_num = 0
    else:
        help_desp = "Non-NIO user belongs to third party, they can only use the PSC charge service of PSS."
        urban_non_nio_user_num = st.number_input("Give the total number of urban Non-NIO user", min_value=0, max_value=20000, value=0, step=5, help=help_desp)
        # st.write("The number of urban daily Non-NIO clients are: ", urban_non_nio_user_num)
    st.write("")

with col_r17: # suburb non nio user num
    # set up the suburb Non NIO user number
    st.write("")
    st.markdown("### Suburb Non-NIO User Number")
    if suburb_psc_num == 0:
        st.write("This type of PSS is not equipped with PSC, the Non NIO users can not use this PSS facility.")
        suburb_non_nio_user_num = 0
    else:
        help_desp = "Non-NIO user belongs to third party, they can only use the PSC charge service of PSS."
        suburb_non_nio_user_num = st.number_input("Give the number of suburb Non-NIO user", min_value=0, max_value=20000, value=0, step=5, help=help_desp)
        # st.write("The number of suburb daily Non-NIO clients are: ", suburb_non_nio_user_num)
    st.write("")

with col_m2:
    st.write("===========================")
    button_flag_2 = st.button("Start Multiple Station Simulation")
    st.write("===========================")

if button_flag_2 == True:
    # Excute the simulation if the button is pressed
    ################################################################################
    #################### Set up the common property ################################
    ################################################################################
    sim_days = 1
    sim_interval = 10
    sim_ticks = int(sim_days * 24 * 60 * 60 / sim_interval) 
    urban_count = num_urban_pss
    suburb_count = num_suburb_pss
    day_step = sim_days + 1
    date1 = datetime.date(2022,1,1)
    date2 = datetime.date(2022,1,day_step)
    delta = datetime.timedelta(seconds = sim_interval)
    dates = mdates.drange(date1, date2, delta)

    if urban_nio_user_num != 0:
        urban_nio_user_num_list = areaNumDivision(num_urban_pss, urban_nio_user_num)
    else:
        urban_nio_user_num_list = list(np.zeros(num_urban_pss))
        urban_nio_user_num_list = [int(s) for s in urban_nio_user_num_list]
    
    if urban_non_nio_user_num != 0:
        urban_non_nio_user_num_list = areaNumDivision(num_urban_pss, urban_non_nio_user_num)
    else:
        urban_non_nio_user_num_list = list(np.zeros(num_urban_pss))
        urban_non_nio_user_num_list = [int(s) for s in urban_non_nio_user_num_list]

    if suburb_nio_user_num != 0:
        suburb_nio_user_num_list = areaNumDivision(num_suburb_pss, suburb_nio_user_num)
    else:
        suburb_nio_user_num_list = list(np.zeros(num_suburb_pss))
        suburb_nio_user_num_list = [int(s) for s in suburb_nio_user_num_list]
    
    if suburb_non_nio_user_num != 0:
        suburb_non_nio_user_num_list = areaNumDivision(num_suburb_pss, suburb_non_nio_user_num)
    else:
        suburb_non_nio_user_num_list = list(np.zeros(num_suburb_pss))
        suburb_non_nio_user_num_list = [int(s) for s in suburb_nio_user_num_list]
    
    # set up empty container ---> 区分出城镇站和郊区站的list
    user_dist_lst = []
    power_history = []
    residual_power = []
    swap_list = []
    nio_charge_list = []
    non_nio_charge_list = []
    max_power = []
    nio_average_time_charge = []
    non_nio_average_time_charge = []
    average_time_swap = []
    swap_ratio_in_15_min = []
    swap_user_wait_time = [] 
    charge_user_wait_time = []
    queue_length_swap = []
    queue_length_charge = []
    queue_overflow_number = []
    queue_overflow_ratio = []

    # Simulation initiating...
    with st.spinner("simulation initiating..."):
        progress_bar = success_info_multiple_station.progress(0)
    # Urban stations
        while urban_count > 0:
            urban_param = {
                "station_type" : urban_type,                                        # set up the PSS type GEN3_600kW, GEN3_1200kW
                "battery_config" : urban_battery_config,                            # set up the battery configuration in a swap rack module
                "init_battery_soc_in_PSS" : 0.95,                                   # set up the initial battery soc in PSS
                "target_soc" : 0.95,                                                # set up the charge target soc
                "select_soc" : 0.9,                                                 # set up the which soc of battery in PSS will be selected to swap
                "sim_days" : sim_days,                                              # set up the simulation day loop
                "sim_interval" : sim_interval,                                      # set up the simulation interval, unit: sec
                "sim_ticks" : sim_ticks,                                            # calculate how many simulation bins in a day loop
                "swap_rack_temperature" : 25,                                       # set up the rack temperature
                "user_sequence_mode" : urban_user_queue_mode,                       # "random" for random sequence create based on distribution defined by user_sequence_random_file
                                                                                    # "statistical" generate user sequence based on real statistical data
                "user_area" : "urban",                                              # set up the simulation area for statistical mode
                "user_preference" : urban_user_preference,                          # define the user selection preference in persentage
                "charge_power_redist" : False,                                      # True: modules will be redistributed after every sim interval, if there exists charging pile, they will be disconnected
                                                                                    # False: modules once be connected to outer charging piles, they are not allowed be disconnected until vehicle leaves
                "enable_me_switch" : 1,                                             # define whether the transport btw the battery rack is allowed, 1 means allowable, 0 not allowable
                "psc_num" : urban_psc_num,                                          # configure the psc number of each station
                "nio_user_num" : urban_nio_user_num_list[num_urban_pss-urban_count],                                # set up the nio user number
                "non_nio_user_num" : urban_non_nio_user_num_list[num_urban_pss-urban_count],                        # set up the non nio user number
                "power_dist_option" : urban_power_dist_option,                      # configure the power distribution mode (PSS prefered or PSC prefered)
                "service_ratio" : urban_user_selection_ratio,                       # configure the service ratio when select "fixed value" preference mode
                "grid_interaction_idx" : urban_grid_interaction_interval_idx,       # the time interval of execution of grid interaction, -1 -> service deactivated
                "interaction_num" : urban_interaction_num,                          # define the times that interaction will perform
                "swap_time" : urban_swap_time                                       # configure the swap time
            }
            swap_user_wait_time_i, charge_user_wait_time_i, queue_length_swap_i, queue_length_charge_i, user_dist_lst_i, max_power_i, power_history_i, residual_power_i, swap_list_i, nio_charge_list_i, non_nio_charge_list_i,\
            average_time_swap_i, nio_average_time_charge_i, non_nio_average_time_charge_i, swap_ratio_in_15_min_i = main.do_simulation(param = urban_param)
            
            swap_user_wait_time.append(swap_user_wait_time_i)
            charge_user_wait_time.append(charge_user_wait_time_i)
            queue_length_swap.append(queue_length_swap_i)
            queue_length_charge.append(queue_length_charge_i)
            user_dist_lst.append(user_dist_lst_i)
            max_power.append(max_power_i)
            power_history.append(power_history_i)
            residual_power.append(residual_power_i)
            swap_list.append(swap_list_i)
            nio_charge_list.append(nio_charge_list_i)
            non_nio_charge_list.append(non_nio_charge_list_i)
            nio_average_time_charge.append(nio_average_time_charge_i)
            non_nio_average_time_charge.append(non_nio_average_time_charge_i)
            average_time_swap.append(average_time_swap_i)
            swap_ratio_in_15_min.append(swap_ratio_in_15_min_i)
            # iteration
            urban_count -= 1
            progress_bar.progress(1-(urban_count+suburb_count)/(num_urban_pss+num_suburb_pss))
        #####################################################################################################################################################################
        # Suburb stations
        while suburb_count > 0:
            suburb_param = {
                "station_type" : suburb_type,                                       # set up the PSS type GEN3_600kW, GEN3_1200kW
                "battery_config" : suburb_battery_config,                           # set up the battery configuration in a swap rack module
                "init_battery_soc_in_PSS" : 0.95,                                   # set up the initial battery soc in PSS
                "target_soc" : 0.95,                                                # set up the charge target soc
                "select_soc" : 0.9,                                                 # set up the which soc of battery in PSS will be selected to swap
                "sim_days" : sim_days,                                              # set up the simulation day loop
                "sim_interval" : sim_interval,                                      # set up the simulation interval, unit: sec
                "sim_ticks" : sim_ticks,                                            # calculate how many simulation bins in a day loop
                "swap_rack_temperature" : 25,                                       # set up the rack temperature
                "user_sequence_mode" : suburb_user_queue_mode,                      # "random" for random sequence create based on distribution defined by user_sequence_random_file
                                                                                    # "statistical" generate user sequence based on real statistical data
                "user_area" : "suburb",                                             # set up the simulation area for statistical mode
                "user_preference" : suburb_user_preference,                         # define the user selection preference in persentage
                "charge_power_redist" : False,                                      # True: modules will be redistributed after every sim interval, if there exists charging pile, they will be disconnected
                                                                                    # False: modules once be connected to outer charging piles, they are not allowed be disconnected until vehicle leaves
                "enable_me_switch" : 1,                                             # define whether the transport btw the battery rack is allowed, 1 means allowable, 0 not allowable
                "psc_num" : suburb_psc_num,                                         # configure the psc number of each station
                "nio_user_num" : suburb_nio_user_num_list[num_suburb_pss-suburb_count],                               # set up the nio user number
                "non_nio_user_num" : suburb_non_nio_user_num_list[num_suburb_pss-suburb_count],                       # set up the non nio user number
                "power_dist_option" : suburb_power_dist_option,                     # configure the power distribution mode (PSS prefered or PSC prefered)
                "service_ratio" : suburb_user_selection_ratio,                      # configure the service ratio when select "fixed value" preference mode
                "grid_interaction_idx" : suburb_grid_interaction_interval_idx,      # the time interval of execution of grid interaction, -1 -> service deactivated
                "interaction_num" : suburb_interaction_num,                         # define the times that interaction will perform
                "swap_time" : suburb_swap_time                                      # configure the swap time
            }
            swap_user_wait_time_i, charge_user_wait_time_i, queue_length_swap_i, queue_length_charge_i, user_dist_lst_i, max_power_i, power_history_i, residual_power_i, swap_list_i, nio_charge_list_i, non_nio_charge_list_i,\
            average_time_swap_i, nio_average_time_charge_i, non_nio_average_time_charge_i, swap_ratio_in_15_min_i = main.do_simulation(param = suburb_param)

            swap_user_wait_time.append(swap_user_wait_time_i)
            charge_user_wait_time.append(charge_user_wait_time_i)
            queue_length_swap.append(queue_length_swap_i)
            queue_length_charge.append(queue_length_charge_i)
            user_dist_lst.append(user_dist_lst_i)
            max_power.append(max_power_i)
            power_history.append(power_history_i)
            residual_power.append(residual_power_i)
            swap_list.append(swap_list_i)
            nio_charge_list.append(nio_charge_list_i)
            non_nio_charge_list.append(non_nio_charge_list_i)
            nio_average_time_charge.append(nio_average_time_charge_i)
            non_nio_average_time_charge.append(non_nio_average_time_charge_i)
            average_time_swap.append(average_time_swap_i)
            swap_ratio_in_15_min.append(swap_ratio_in_15_min_i)
            # iteration
            suburb_count -= 1
            progress_bar.progress(1-(urban_count+suburb_count)/(num_urban_pss+num_suburb_pss))

        ################################################################################
        ########################## Results calculation #################################
        ################################################################################
        # 1. success ratio within 15 min
        ratio_persentage = [round(s * 100, 2) for s in swap_ratio_in_15_min]
        # 2. swap ability characteristics
        swap_num = [len(s) for s in swap_list]
        swap_rate = [60 / s if s != 0 else 0 for s in average_time_swap]
        # 3. charge ability
        nio_charge_num = [len(s) for s in nio_charge_list]
        non_nio_charge_num = [len(s) for s in non_nio_charge_list]
        nio_charge_rate = [60/s if s != 0 else 0 for s in nio_average_time_charge]
        non_nio_charge_rate = [60/s if s != 0 else 0 for s in non_nio_average_time_charge]
        # 4. overflow of service user
        for i in range(num_urban_pss+num_suburb_pss):
            queue_overflow_number.append(queue_length_swap[i][-1]+queue_length_charge[i][-1])
        
        for i, lst in enumerate(user_dist_lst):
            if len(lst) != 0:
                queue_overflow_ratio.append(round(queue_overflow_number[i] / len(lst) * 100, 2))
            else:
                queue_overflow_ratio.append(0)
        
        # 5. energy consumption
        energy_list = []
        grid_energy_list = []
        for pw_item in power_history:
            power_list = []
            grid_power_list = []
            for pw in pw_item:
                if pw[1] >= 0:
                    power_list.append(pw[1])
                    grid_power_list.append(0)
                else:
                    power_list.append(0)
                    grid_power_list.append(pw[1])
            energy_i = energy_calc(power=power_list, time_interval=sim_interval)
            grid_energy_i = abs(energy_calc(power=grid_power_list, time_interval=sim_interval))
            energy_list.append(energy_i)
            grid_energy_list.append(grid_energy_i)

        total_grid_energy = sum(grid_energy_list) # [kWh]

        # 6. station area info (area & type)
        area = []
        stationType = []
        for i in range(num_urban_pss):
            area.append("urban")
            stationType.append(type_urban_pss)
        for i in range(num_suburb_pss):
            area.append("suburb")
            stationType.append(type_suburb_pss)

        # 6. summarize the result into data frame
        ratio = pd.DataFrame(ratio_persentage,columns=["Swap ratio in 15min [%]"])
        swap_rate = pd.DataFrame(swap_rate, columns=["Swap rate [1/hours]"])
        nio_charge_rate = pd.DataFrame(nio_charge_rate, columns=["NIO user charge rate [1/hours]"])
        non_nio_charge_rate = pd.DataFrame(non_nio_charge_rate, columns=["Non NIO user charge rate [1/hours]"])
        energy_list = pd.DataFrame(energy_list, columns=["Energy consumption in 24hrs [kWh]"])
        stationType = pd.DataFrame(stationType, columns=["PSS Type"])
        area = pd.DataFrame(area, columns=["Area"])
        grid_energy_list = pd.DataFrame(grid_energy_list, columns=["Grid Interaction Energy [kWh]"])
        queue_overflow_ratio = pd.DataFrame(queue_overflow_ratio, columns=["Queue Overflow [%]"])
        
        frames = [area, stationType, energy_list, grid_energy_list, ratio, swap_rate, nio_charge_rate, non_nio_charge_rate, queue_overflow_ratio]
        multistation_results = pd.concat(frames,axis=1)
        
        # calculate the total grid energy in different areas.
        urban_total_grid_energy = 0
        suburb_total_grid_energy = 0
        for i in range(num_urban_pss):
            urban_total_grid_energy += grid_energy_list["Grid Interaction Energy [kWh]"][i]
        urban_grid_energy = pd.DataFrame([urban_total_grid_energy], columns=["Urban total grid energy [kWh]"])
        for i in range(num_urban_pss, len(grid_energy_list)):
            suburb_total_grid_energy += grid_energy_list["Grid Interaction Energy [kWh]"][i]
        suburb_grid_energy = pd.DataFrame([suburb_total_grid_energy], columns=["Suburb total grid energy [kWh]"])

    success_info_multiple_station.success("simulation successfully excuted.")
st.write("")
st.write("")

#####################################################################################
######################### Part 4: Display Simulation results ########################
#####################################################################################

#########################
# for single station case:
#########################

with single_station_result:
    # Set up the text and statistics results for single station
    if button_flag_1 == False:
        # by default the subplot results don't show in the panel
        pass
    else:
        st.markdown("# Step 3: Results Display")
        st.write("")
        st.write("")
        ################################################################
        ############ 0. show the key text results ######################
        ################################################################
        _, col_m3, _ = st.columns([1,10,1])
        col_m3.table(result_data.style.format(precision=2, na_rep='MISSING', thousands=" ",formatter={("Values"):"{:.2f}"}))
        st.write("")
        st.write("")

        # devide the plots into 2 columns
        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)
        col5, col6 = st.columns(2)
        col7, col8 = st.columns(2) 
        # Set the plot diagram into black background and white font
        plt.style.use('dark_background')

        with col1: # arrvie time dist
            ################################################################
            ############## 1. show the user distribution ###################
            ################################################################
            fig1, ax1 = plt.subplots(figsize=(7, 5))
            time_dist = [dt.fromtimestamp(s) for s in user_dist_lst]
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax1.tick_params(axis="both",direction = "out", labelsize= 10)
            ax1.hist(x = time_dist, bins = 48, color = "#005293", edgecolor = "black")
            plt.xlim([dt(1969, 12, 31, 23),dt(1970, 1, 2, 1)]) # 日期上下限
            plt.xlabel("Time ticks")
            plt.ylabel("User number in half hour, user total number = " + '%d' %len(user_dist_lst))
            plt.title("User vehicles reach time distribution")
            plt.grid(True, linestyle=":")
            # fig1.autofmt_xdate()
            st.pyplot(fig1)

        with col3: # charge service time dist
            ################################################################
            ############## 3. show the charge time in sim ticks ############
            ################################################################
            fig3, ax3 = plt.subplots(figsize=(7, 5))
            nio_charge_dist = []
            non_nio_charge_dist = []
            for i in range(sim_ticks):
                for user in nio_charge_list:
                    if user.sequence == i:
                        # mode = 1 wait time + charge time; mode = 0 only charge time
                        nio_charge_dist.append(user.charge_service_time() * sim_interval / 60.0)
                        break
                for user in non_nio_charge_list:
                    if user.sequence == i:
                        non_nio_charge_dist.append(user.charge_service_time() * sim_interval / 60.0)
            
            ax3.hist([nio_charge_dist, non_nio_charge_dist], bins=15, color = ["#005293", "#98C6EA"],\
                edgecolor = "black", label=['NIO user', 'Non NIO user'])
            plt.xlabel("Charge service time in [min]")
            plt.ylabel("Counts")
            plt.title("Charge service time (Charge + Wait) distribution in 24 hours")
            plt.grid(True, linestyle=":")
            plt.legend(loc='upper right')
            st.pyplot(fig3)

        with col5: # charge time (No wait time)
            ################################################################
            ############## 5. show the charge time in sim ticks ############
            ################################################################
            fig5, ax5 = plt.subplots(figsize=(7, 5))
            nio_charge_dist = []
            non_nio_charge_dist = []
            for i in range(sim_ticks):
                for user in nio_charge_list:
                    if user.sequence == i:
                        # mode = 1 wait time + charge time; mode = 0 only charge time
                        nio_charge_dist.append(user.charge_service_time(mode=0) * sim_interval / 60.0)
                        break
                for user in non_nio_charge_list:
                    if user.sequence == i:
                        non_nio_charge_dist.append(user.charge_service_time(mode=0) * sim_interval / 60.0)
            
            ax5.hist([nio_charge_dist, non_nio_charge_dist], bins=15, color = ["#005293", "#98C6EA"],\
                edgecolor = "black", label=['NIO user', 'Non NIO user'])
            plt.xlabel("Charge time distribution in [min]")
            plt.ylabel("Counts")
            plt.title("Charge time (without Wait) distribution in 24 hours")
            plt.grid(True, linestyle=":")
            plt.legend(loc='upper right')
            st.pyplot(fig5)

        with col7: # user num ratio
            # ################################################################
            # ############## 5. show the clients ratio #######################
            # ################################################################
            fig7, ax7 = plt.subplots(figsize=(7, 5), subplot_kw=dict(aspect="equal"))
            label = ["swap", "charge(NIO)", "charge(Non-NIO)"]
            data = [len(swap_list), len(nio_charge_list), len(non_nio_charge_list)]
            colors = ["#005293", "#64A0C8", "#98C6EA"]
            wedges, texts, persent = ax7.pie(data, wedgeprops=dict(width=0.7), startangle=45, colors=colors, autopct="%.2f%%")
            bbox_props = dict(boxstyle="square,pad=0.3", fc="k", ec="k", lw=0.72) # fc=facecolor, ec=edgecolor
            kw = dict(arrowprops=dict(arrowstyle="-"), bbox=bbox_props, zorder=0, va="center")

            for i, p in enumerate(wedges):
                ang = (p.theta2 - p.theta1)/2. + p.theta1
                y = np.sin(np.deg2rad(ang))
                x = np.cos(np.deg2rad(ang))
                horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
                connectionstyle = "angle,angleA=0,angleB={}".format(ang)
                kw["arrowprops"].update({"connectionstyle": connectionstyle})
                ax7.annotate(label[i], xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
                            horizontalalignment=horizontalalignment, **kw)
            ax7.set_title("Clients Ratio")
            st.pyplot(fig7)

        with col2: # power dist
            ################################################################
            ############## 2. show the max power distribution ##############
            ################################################################
            fig2, ax2 = plt.subplots(figsize=(7, 5))
            y_plot1 = y_func
            y_plot2 = y_grid_func
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax2.tick_params(axis="both",direction = "out", labelsize= 10)
            ax2.plot_date(dates, y_plot1, "#64A0C8", label="Power Distribution")
            ax2.plot_date(dates, y_plot2, "red",":", alpha=0.5, label="Grid Interaction")
            ax2.plot_date(dates, power_mean_list, '--', color="#98C6EA")
            ax2.text(x=dates[0], y=power_mean+10, s="Mean %.2f [kW]"%round(power_mean,2))
            plt.xlim([dt(2021, 12, 31, 23),dt(2022, 1, 2, 1)]) # 日期上下限
            plt.xlabel("Time series")
            plt.ylabel("PSS total power, max power = " + '%.0f kW' %max_power)
            plt.title("PSS Power distribution")
            plt.grid(True, linestyle=":")
            plt.legend()
            st.pyplot(fig2)

        with col4: # swap time dist
            ################################################################
            ############## 4. show the swap time in sim ticks ##############
            ################################################################
            fig4, ax4 = plt.subplots(figsize=(7, 5))
            y_plot = []
            recorded = 0
            for i in range(sim_ticks):
                for user in swap_list:
                    if user.sequence == i:
                        y_plot.append(user.swap_service_time * sim_interval / 60.0)
                        break
            ax4.hist(y_plot, bins=30, color = "#005293", edgecolor = "black")
            plt.xlabel("Swap service time in [min]")
            plt.ylabel("Counts")
            plt.title("Swap service time (Swap + Wait) distribution in 24 hours")
            plt.grid(True, linestyle=":")
            st.pyplot(fig4)

        with col6: # wait time distribution

            ################################################################
            ############## 6. show the wait time distribution ##############
            ################################################################
            fig6, ax6 = plt.subplots(figsize=(7, 5))
            ax6.hist([swap_user_wait_time, charge_user_wait_time], bins=15, color = ["#005293", "#64A0C8"],\
                edgecolor = "black", label=["Swap Group Wait Time", "Charge Group Wait Time"])
            plt.xlabel("Wait time distribution [min]")
            # set the interval btw 2 ticks of y axis
            x_major_locator = MultipleLocator(10)
            y_major_locator = MultipleLocator(5)
            ax6.yaxis.set_major_locator(y_major_locator)
            ax6.xaxis.set_major_locator(x_major_locator)
            plt.ylabel("Counts")
            plt.title("Wait time distribution")
            plt.grid(True, linestyle=":")
            plt.legend()
            st.pyplot(fig6)
    
        with col8: # queue length
            ################################################################
            ############## 8. show the Queue length distribution ###########
            ################################################################
            fig8, ax8 = plt.subplots(figsize=(7, 5))
            ax8.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax8.tick_params(axis="both",direction = "out", labelsize= 10)
            ax8.plot_date(dates, queue_length_swap, "#005293", label="Swap Queue")
            ax8.plot_date(dates, queue_length_charge, "#64A0C8", label="Charge Queue")
            plt.xlim([dt(2021, 12, 31, 23),dt(2022, 1, 2, 1)]) # 日期上下限
            # set the interval btw 2 ticks of y axis
            y_major_locator = MultipleLocator(2)
            ax8.yaxis.set_major_locator(y_major_locator)
            plt.xlabel("Time series")
            plt.ylabel("Queue length")
            plt.title("Queue length distribution")
            plt.grid(True, linestyle=":")
            plt.legend()
            st.pyplot(fig8)
            # ################################################################
            # ############## 6. show the average time of service #############
            # ################################################################
            # fig8, ax8 = plt.subplots(figsize = (7, 5))
            # bar_width = 0.4
            # x_index = ["Swap", "Charge(NIO)", "Charge(Non-NIO)"]
            # index = np.arange(len(x_index))
            # y_layer1 = [average_time_swap, nio_average_time_charge, non_nio_average_time_chagre]
            # colors = ["#005293", "#64A0C8", "#98C6EA"]
            # ax8.bar(x_index, y_layer1, color = colors, width=bar_width)
            
            # # set up function that add text at upper of the bar
            # @st.cache
            # def add_text(x, y, data):
            #     for x0, y0, data0 in zip(x, y, data):
            #         ax8.text(x0, y0+1, round(data0, 1))
            
            # add_text(index-bar_width/8, y_layer1, y_layer1)
            # plt.ylabel("Average service time in minute")
            # plt.title("Average service time (including wait time & swap/charge time)")
            # plt.grid(True, linestyle=":")
            # st.pyplot(fig8)

            

    ################################################################
    #################### Download Config ###########################
    ################################################################

    if button_flag_1 == False:
        st.empty()
    else:
        st.markdown("# Step 4: Results Download")
        st.write("Press the button to download the datalog")
        st.markdown("# ")
        param = {
        "station_type" : type_pss,                                          # set up the PSS type GEN3_600kW, GEN3_1200kW
        "psc_num" : psc_num,
        "battery_type1" : list(battery_config.keys())[0],                   # set up the battery configuration in a swap rack module
        "num_battery_type1" : list(battery_config.values())[0],
        "battery_type2" : list(battery_config.keys())[1],  
        "num_battery_type2" : list(battery_config.values())[1],
        "init_battery_soc_in_PSS" : init_battery_soc,                       # set up the initial battery soc in PSS
        "target_soc" : target_soc,                                          # set up the charge target soc
        "select_soc" : select_soc,                                          # set up the which soc of battery in PSS will be selected to swap
        "nio_user_num" : nio_user_num,                                      # set up how many users in a day will use the PSS
        "non_nio_user_num" : non_nio_user_num,                              # set up the number of non nio user
        "sim_days" : sim_days,                                              # set up the simulation day loop
        "sim_interval" : sim_interval,                                      # set up the simulation interval, unit: sec
        "sim_ticks" : sim_ticks,                                            # calculate how many simulation bins in a day loop
        "swap_rack_temperature" : 25,                                       # set up the rack temperature
        "user_sequence_mode" : user_queue_mode,                             # "random" for random sequence create based on distribution defined by user_sequence_random_file
                                                                            # "statistical" generate user sequence based on real statistical data
        "user_area" : user_area,                                            # set up the simulation area for statistical mode
        "user_preference" : user_preference,                                # define the user selection preference in markov, full swap, or fixed value (70% swap, and 30% charge)
        "charge_power_redist" : False,                                      # True: modules will be redistributed after every sim interval, if there exists charging pile, they will be disconnected
                                                                            # False: modules once be connected to outer charging piles, they are not allowed be disconnected until vehicle leaves
        "enable_me_switch" : 1                                              # define whether the transport btw the battery rack is allowed, 1 means allowable, 0 not allowable
    }
        param_df = pd.DataFrame.from_dict(param, orient='index', columns=['Values'])
        param_df = param_df.reset_index().rename(columns={'index': 'Parameters'})
        frames = [param_df, result_data]
        result = pd.concat(frames,axis=1)
        csv = convert_df(result)

        _, col_m4, _ = st.columns([5,3,5])
        with col_m4:

            st.write("================")
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name='datalog.csv',
                mime='text/csv',
            )
            st.write("================")

###########################
# for multiple station case:
###########################

with multiple_station_result:
    if button_flag_2 == False:
        pass
    else:
        st.markdown("# ")
        st.markdown("# Step 3: Simulation Results")
        st.write("")
        ################################################################
        ############ 0. show the key text results ######################
        ################################################################
        st.markdown("### Service Ability Evaluation")
        st.table(multistation_results.style.format(precision=2, na_rep='MISSING', thousands=" ",\
            formatter={("Energy consumption in 24hrs [kWh]", "Swap success ratio in 15min [%]",\
            "Swap rate [1/hours]", "NIO user charge rate [1/hours]", "Non NIO user charge rate [1/hours]"):"{:.2f}"}))
        st.write("")

        # devide the plots into 2 columns
        st.markdown("### Characteristics Visualization")
        col9, col10 = st.columns(2)
        col11, col12 = st.columns(2)
        col13, col14 = st.columns(2)
        col15, col16 = st.columns(2)
        col17, col18 = st.columns(2)
        col19, col20 = st.columns(2)
        # Set the plot diagram into black background and white font
        plt.style.use('dark_background')
        col9.markdown('<h3 style="text-align: center;">Urban Area</h3>', unsafe_allow_html=True)
        col9.table(urban_grid_energy.style.format(precision=2, na_rep='MISSING', thousands=" ",\
            formatter={("Urban total grid energy [kWh]"):"{:.2f}"}))
        col10.markdown('<h3 style="text-align: center;">Suburb Area</h3>', unsafe_allow_html=True)
        col10.table(suburb_grid_energy.style.format(precision=2, na_rep='MISSING', thousands=" ",\
            formatter={("Suburb total grid energy [kWh]"):"{:.2f}"}))
        ################################################################
        ############## 1. show the PSS power distribution ##############
        ################################################################
        with col11: # power dist urban stations
            st.write("")
            # plot for urban stations
            fig1, ax1 = plt.subplots(figsize=(7, 5))
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax1.tick_params(axis="both",direction = "out", labelsize= 10)
            
            # get urban power log
            power_history_urban = power_history[:num_urban_pss]
            count = 0
            cmap = mpl.cm.get_cmap("Blues", num_urban_pss+10) # get color map
            colors = cmap(np.linspace(0.2, 0.75,num_urban_pss)) # get color list
            for i, power_log in enumerate(power_history_urban):
                y_plot = []
                labelString = ""
                # set up the label
                labelString = "urban No.%d" %(count+1)
                # add power data into y
                for pw in power_log:
                    y_plot.append(pw[1])
                count += 1
                ax1.plot_date(dates, y_plot, "-", label=labelString, color=colors[i])
                
            plt.xlabel("time series")
            plt.ylabel("PSS total power, max power = " + '%.0f kW' %max_power[0])
            plt.title("PSS Power distribution, urban stations")
            plt.xlim([dt(2021, 12, 31, 23),dt(2022, 1, 2, 1)]) # 日期上下限
            ax1.legend(loc="upper left")
            plt.grid(True, linestyle=":")
            st.pyplot(fig1)

        with col12: # power dist suburb stations
            st.write("")
            # plot for suburb stations
            fig2, ax2 = plt.subplots(figsize=(7, 5))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax2.tick_params(axis="both",direction = "out", labelsize= 10)

            # get suburb station power log
            power_history_suburb = power_history[num_urban_pss:]
            count = 0
            cmap = mpl.cm.get_cmap("Blues", num_suburb_pss+10) # get color map
            colors = cmap(np.linspace(0.2, 0.75,num_suburb_pss)) # get color list
            for i, power_log in enumerate(power_history_suburb):
                y_plot = []
                labelString = ""
                # set up the label
                labelString = "suburb No.%d" %(count+1)
                # add power data into y
                for pw in power_log:
                    y_plot.append(pw[1])
                count += 1
                ax2.plot_date(dates, y_plot, "-", label=labelString, color=colors[i])
                
            plt.xlabel("time series")
            plt.ylabel("PSS total power, max power = " + '%.0f kW' %max_power[0])
            plt.title("PSS Power distribution, suburb stations")
            plt.xlim([dt(2021, 12, 31, 23),dt(2022, 1, 2, 1)]) # 日期上下限
            ax2.legend(loc="upper left")
            plt.grid(True, linestyle=":")
            st.pyplot(fig2)
        
        ################################################################
        ############## 2. show the PSS swap time dist ##################
        ################################################################
        with col13: # urban swap time dist
            fig3, ax3 = plt.subplots(figsize=(7, 5))
            swap_time_dist = []
            for station_list in swap_list[:num_urban_pss]:
                for i in range(sim_ticks):
                    for user in station_list:
                        if user.sequence == i:
                            swap_time_dist.append(user.swap_service_time * sim_interval / 60.0)
                            break
            ax3.hist(swap_time_dist, bins=30, color = "#005293", edgecolor = "black")
            # x_major_locator = MultipleLocator(10)
            # y_major_locator = MultipleLocator(20)
            # ax3.yaxis.set_major_locator(y_major_locator)
            # ax3.xaxis.set_major_locator(x_major_locator)
            plt.xlabel("swap service time in [min]")
            plt.ylabel("counts")
            plt.title("Overall Urban Swap Service Time Distribution [24hrs]")
            plt.grid(True, linestyle=":")
            st.pyplot(fig3)

        with col14: # suburb swap time dist
            fig4, ax4 = plt.subplots(figsize=(7, 5))
            swap_time_dist = []
            for station_list in swap_list[num_urban_pss:]:
                for i in range(sim_ticks):
                    for user in station_list:
                        if user.sequence == i:
                            swap_time_dist.append(user.swap_service_time * sim_interval / 60.0)
                            break
            ax4.hist(swap_time_dist, bins=30, color = "#005293", edgecolor = "black")
            # x_major_locator = MultipleLocator(10)
            # y_major_locator = MultipleLocator(20)
            # ax4.yaxis.set_major_locator(y_major_locator)
            # ax4.xaxis.set_major_locator(x_major_locator)
            plt.xlabel("swap service time in [min]")
            plt.ylabel("counts")
            plt.title("Overall Suburb Swap Service Time Distribution [24hrs]")
            plt.grid(True, linestyle=":")
            st.pyplot(fig4)
        
        ################################################################
        ############## 3. show the PSS charge time dist ################
        ################################################################
        with col15: # urban charge time dist
            fig5, ax5 = plt.subplots(figsize=(7, 5))
            urban_nio_charge_dist = []
            urban_non_nio_charge_dist = []
            for i in range(sim_ticks):
                for station_list in nio_charge_list[:num_urban_pss]:
                    for user in station_list:
                        if user.sequence == i:
                            urban_nio_charge_dist.append(user.charge_service_time() * sim_interval / 60.0)
                            break
                for station_list in non_nio_charge_list[:num_urban_pss]:
                    for user in station_list:
                        if user.sequence == i:
                            urban_non_nio_charge_dist.append(user.charge_service_time() * sim_interval / 60.0)
            
            ax5.hist([urban_nio_charge_dist, urban_non_nio_charge_dist], bins=15, color = ["#005293", "#98C6EA"],\
                edgecolor = "black", label=['NIO user', 'Non NIO user'])
            # plt.yticks(np.linspace(0,10,11))
            plt.xlabel("charge service time in [min]")
            plt.ylabel("counts")
            plt.title("Overall Urban Charge Time Distribution [24hrs]")
            plt.grid(True, linestyle=":")
            plt.legend(loc='upper right')
            st.pyplot(fig5)

        with col16: # suburb charge time dist
            fig6, ax6 = plt.subplots(figsize=(7, 5))
            suburb_nio_charge_dist = []
            suburb_non_nio_charge_dist = []
            for i in range(sim_ticks):
                for station_list in nio_charge_list[num_urban_pss:]:
                    for user in station_list:
                        if user.sequence == i:
                            suburb_nio_charge_dist.append(user.charge_service_time() * sim_interval / 60.0)
                            break
                for station_list in non_nio_charge_list[num_urban_pss:]:
                    for user in station_list:
                        if user.sequence == i:
                            suburb_non_nio_charge_dist.append(user.charge_service_time() * sim_interval / 60.0)
            
            ax6.hist([suburb_nio_charge_dist, suburb_non_nio_charge_dist], bins=15, color = ["#005293", "#98C6EA"],\
                edgecolor = "black", label=['NIO user', 'Non NIO user'])
            # plt.yticks(np.linspace(0,10,11))
            plt.xlabel("charge service time in [min]")
            plt.ylabel("counts")
            plt.title("Overall Suburb Charge Time Distribution [24hrs]")
            plt.grid(True, linestyle=":")
            plt.legend(loc='upper right')
            st.pyplot(fig6)

        ################################################################
        ############## 4. show the clients ratio #######################
        ################################################################
        with col17: # user ratio urban
            fig7, ax7 = plt.subplots(figsize=(7, 5), subplot_kw=dict(aspect="equal"))
            label_urban = ["swap", "charge(NIO)", "charge(Non-NIO)"]
            data_urban = [sum(swap_num[:num_urban_pss]), sum(nio_charge_num[:num_urban_pss]), sum(non_nio_charge_num[:num_urban_pss])]
            colors = ["#005293", "#64A0C8", "#98C6EA"]
            wedges, texts, persent = ax7.pie(data_urban, wedgeprops=dict(width=0.7), startangle=45, colors=colors, autopct="%.2f%%")
            bbox_props = dict(boxstyle="square,pad=0.3", fc="k", ec="k", lw=0.72) # fc=facecolor, ec=edgecolor
            kw = dict(arrowprops=dict(arrowstyle="-"), bbox=bbox_props, zorder=0, va="center")

            for i, p in enumerate(wedges):
                ang = (p.theta2 - p.theta1)/2. + p.theta1
                y = np.sin(np.deg2rad(ang))
                x = np.cos(np.deg2rad(ang))
                horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
                connectionstyle = "angle,angleA=0,angleB={}".format(ang)
                kw["arrowprops"].update({"connectionstyle": connectionstyle})
                ax7.annotate(label_urban[i], xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
                            horizontalalignment=horizontalalignment, **kw)
            ax7.set_title("Overall Urban Clients Ratio")
            st.pyplot(fig7)

        with col18: # user ratio suburb
            fig8, ax8 = plt.subplots(figsize=(7, 5), subplot_kw=dict(aspect="equal"))
            label_suburb = ["swap", "charge(NIO)", "charge(Non-NIO)"]
            data_suburb = [sum(swap_num[num_urban_pss:]), sum(nio_charge_num[num_urban_pss:]), sum(non_nio_charge_num[num_urban_pss:])]
            colors = ["#005293", "#64A0C8", "#98C6EA"]
            wedges, texts, persent = ax8.pie(data_suburb, wedgeprops=dict(width=0.7), startangle=45, colors=colors, autopct="%.2f%%")
            bbox_props = dict(boxstyle="square,pad=0.3", fc="k", ec="k", lw=0.72) # fc=facecolor, ec=edgecolor
            kw = dict(arrowprops=dict(arrowstyle="-"), bbox=bbox_props, zorder=0, va="center")

            for i, p in enumerate(wedges):
                ang = (p.theta2 - p.theta1)/2. + p.theta1
                y = np.sin(np.deg2rad(ang))
                x = np.cos(np.deg2rad(ang))
                horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
                connectionstyle = "angle,angleA=0,angleB={}".format(ang)
                kw["arrowprops"].update({"connectionstyle": connectionstyle})
                ax8.annotate(label_suburb[i], xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
                            horizontalalignment=horizontalalignment, **kw)
            ax8.set_title("Overall Suburb Clients Comprehensive Ratio")
            st.pyplot(fig8)
        
        with col19:
            pass

        with col20:
            pass

        #####################################################################################
        ######################### Part 4: Display Simulation results ########################
        #####################################################################################
        st.markdown("# ")
        st.markdown("# Step 4: CSV Download")
        st.write("Press the button to download the CSV datalog")

        csv = convert_df(multistation_results)
        _, col_m5, _ = st.columns([5,3,5])
        with col_m5:
            st.write("")
            st.write("================")
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name='datalog.csv',
                mime='text/csv',
            )
            st.write("================")


################################################################
#################### Sidebar Notation ##########################
################################################################
# ========= Set up the PSS selection Recommendation (sidebar) =======
st.sidebar.markdown("# PSS Power Assistant")
st.sidebar.write("")
st.sidebar.markdown("## Set up your PSS proporties:")
pss_type = ["PSS 2.0", "PSS 3.0 PUS A", "PSS 3.0 PUS B"]
power_level = [100, 200, 300, 550, 630, 1250]
pss_select = None
power_select = 0

# Peak swap number
help1 = "PSC not included"
st.sidebar.write("")
st.sidebar.markdown("### Peak Swapping Number (Morning)")
ans1 = st.sidebar.slider("Select the expected peak swapping number (morning)/hour", min_value=0, max_value=20, help=help1)

# Peak charge number
st.sidebar.write("")
st.sidebar.markdown("### Peak Charging Number")
ans2 = st.sidebar.slider("Select the expected peak charging number/hour", min_value=0, max_value=18, help=help1)

# Peak swap day time
st.sidebar.write("")
st.sidebar.markdown("### Peak Swapping Number (Day time)")
ans3 = st.sidebar.slider("Select the expected peak swapping number (day time)/hour", min_value=0, max_value=13, help=help1)

# Swap service capacity
help2 = "The number of daily swapping clients"
st.sidebar.write("")
st.sidebar.markdown("### Daily Swapping Capacity")
ans4 = st.sidebar.number_input("Give the daily swapping number capacity", min_value=0, max_value=150, step=5, value=50, help=help2)

# PSC required
st.sidebar.write("")
st.sidebar.markdown("### Is PSC Required?")
ans5 = st.sidebar.checkbox("PSC required")

##########################################
############ Logic inference #############
##########################################
# first for PSS 2.0
if ans1 <= 13 and ans2 <= 8 and ans3 <= 8 and ans4 <= 93 and ans5 == False:
    pss_select = pss_type[0]
    if ans2 <= 2 and ans3 <=2 and ans4 <= 33:
        power_select = power_level[0]
    elif (ans2 == 3 or ans3 == 3 or ans4 > 33) and ans4 <= 43:
        power_select = power_level[1]
    elif (ans2 > 3 or ans3 > 3 or ans4 > 43) and ans2 <= 5 and ans3 <= 5 and ans4 <= 63:
        power_select = power_level[2]
    else:
        power_select = power_level[3]
# second for PSS 3.0
else:
    if ans2 <= 3 and ans3 <= 3 and ans4 <= 50 and ans5 == False:
        pss_select = pss_type[1]
        power_select = power_level[1]
    elif (ans2 > 3 or ans3 > 3 or ans4 > 50) and ans2 <=5 and ans3 <= 5 and ans4 <= 70 and ans5 == False:
        pss_select = pss_type[1]
        power_select = power_level[2]
    elif (ans2 > 5 or ans3 > 5 or ans4 > 70) and ans2 <=9 and ans3 <= 9 and ans4 <= 110:
        pss_select = pss_type[1]
        power_select = power_level[4]
    else:
        pss_select = pss_type[2]
        power_select = power_level[5]

##########################################
############ Data Collection #############
##########################################
# Summary of PSS configurations
pss_data = {"station_type":         None, 
            "num_battery":          0, 
            "psc":                  None, 
            "num_charge_piles":     0, 
            "transformer_power":    0       
            }
pss_data["station_type"] = pss_select
pss_data["transformer_power"] = power_select

# PSS 2.0
if pss_data["station_type"] == "PSS 2.0":
    pss_data["station_type"] = "PSS 2.0 or above"
    pss_data["num_battery"] = 13
    pss_data["psc"] = "No PSC"
    pss_data["num_charge_piles"] = 0
# PSS 3.0 PUS A
elif pss_data["station_type"] == "PSS 3.0 PUS A":
    pss_data["num_battery"] = 10
    if ans5:
        pss_data["psc"] = "PSC equipped"
    else:
        pss_data["psc"] = "No PSC"
    
    if pss_data["transformer_power"] <= 300:
        pss_data["num_charge_piles"] = 0
    else:
        pss_data["num_charge_piles"] = 4
# PSS 3.0 PUS B
else:
    pss_data["num_battery"] = 20
    pss_data["psc"] = "PSC equipped"
    pss_data["num_charge_piles"] = 8

##########################################
############ Suggestion ##################
##########################################

st.sidebar.write("")
st.sidebar.write("")
st.sidebar.markdown("## Suggestion:")
st.sidebar.write("Press the button to get advice")
_, col_m, _ = st.sidebar.columns([1,2,1])
trigger_btn = col_m.button("Suggestion")

col21, col22 = st.sidebar.columns([2,1])
col23, col24 = st.sidebar.columns([2,1])
col25, col26 = st.sidebar.columns([2,1])
col27, col28 = st.sidebar.columns([2,1])
col29, col30 = st.sidebar.columns([2,1])

if trigger_btn == False:
    st.empty()
else:
    col21.info("PSS Type: ")
    col22.markdown("### %s" %pss_data["station_type"])
    st.write("")
    col23.info("Maximal allowable number of Battery Racks: ")
    col24.markdown("### %d" %pss_data["num_battery"])
    st.write("")
    col25.info("Maximal allowable number of Charge Terminals: ")
    col26.markdown("### %d" %pss_data["num_charge_piles"])
    st.write("")
    col27.info("PSC state: ")
    col28.markdown("### %s" %pss_data["psc"])
    st.write("")
    col29.info("Recommended transformer power: ")
    col30.markdown("### %d" %pss_data["transformer_power"] + " [kVA]")
    st.write("")

# set up the Notation and contact information
st.sidebar.write("")
st.sidebar.write("")
st.sidebar.markdown("Note: This App is developed and maintained by NIO Power EU. \
                    For any technical issue and feedback related to the App, please\
                     feel free to contact the developer: yuan.meng@nio.io")
st.sidebar.write("")
st.sidebar.write("")
