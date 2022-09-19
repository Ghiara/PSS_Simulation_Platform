#充换一体站充换电能力，服务能力综合仿真程序
# -*- coding: UTF-8 -*-

###########################
###### Update logger ######
###########################
# 2022.09.09 User Defined PSS avaiable                      by Y.Meng
# 2022.09.09 FY 4 Variation updated into model              by Y.Meng
# 2022.09.06 Grid interaction update                        by Y.Meng
# 2022.09.02 update the discharge behaviours of PSS         by Y.Meng
# 2022.09.01 modify the power distribution strategy         by Y.Meng
# 2022.07.07 commit filling & coding review                 by Y.Meng 
# 2022.07.01 init generation                                by C.Yang
###########################

### 外部库调用 ###
import numpy as np
import math
import logging
import global_param

# load global Parameters
GC = global_param.Global_Constant()
# GP = global_param.Global_Parameter()

# setup logger
logger = logging.getLogger('main.swap')
data_logger = logging.getLogger('data.swap')

######################################################################
####################### Class: Battery ###############################
######################################################################

class Battery:
    
    def __init__(self, soc, batterytype, target_max_soc = 1, target_min_soc=0, temperature = 25):
        '''
        Initializing the parameters in battery instance
        soc: double, state of charge: 0 -> empty; 1 -> full charged
        charge_limit: 8 * 13 matrix, tempurature -> current at limit_axis
        batterytype: string, indicate which type of batteries are chosen -> 70kWh, 100kWh, 75kWh
        support battery type: 
            1. 70kWh -> NIO
            2. 75kWh -> NIO
            3. 100kWh -> NIO
            4. FY41kWh -> FY
            5. FY62kWh -> FY
        Note:   1-3 cannot combine with 4,5 -> not swapable
                if No Data avaiable, by default we use data from 100kWh
        '''
        self.charge_limit_100 = GC.charge_limit_100
        self.charge_limit_75 = GC.charge_limit_75
        self.charge_limit_70 = GC.charge_limit_70
        self.ocv_100 = GC.ocv_100
        self.ocv_70 = GC.ocv_70
        battery_charge_limit={  
            "70kWh": self.charge_limit_70,
            "75kWh": self.charge_limit_75,
            "100kWh": self.charge_limit_100,
            "FY41kWh": self.charge_limit_100,
            "FY62kWh": self.charge_limit_100
                            }
        self.battery_capacity = GC.battery_capacity                     # battery capacity [Ah]
        self.batterytype = batterytype                                  # string -> 70kWh, 100kWh, 75kWh..
        
        if batterytype in self.battery_capacity:
            self.capacity = self.battery_capacity[batterytype]          # 返回电池Ah数 return int
            self.charge_limit = battery_charge_limit[batterytype]       # 返回充电限制 dict
        else:
            '''
            if No batteries type are found, return default setup (100kWh Batteries)
            '''
            print("No such battery type, using default type 100kWh")
            self.capacity = self.battery_capacity["100kWh"]
            self.charge_limit = battery_charge_limit["100kWh"]
        
        self.soc = soc
        self.set_temperature(temperature)                               # 缺省电池温度为25度
        self.polar_r = 0.04                                             # 假设是40 mohm，0.04欧姆
        self.limit_axis = [0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95,] # soc limit values
        self.target_max_soc = target_max_soc
        self.target_min_soc = target_min_soc
        self.power_command = 0
        self.set_battery_voltage()
        self.calc_current_limit()
        self.power = 0
        self.current = 0

        self.charge_history = []                                        #按照{soc:???,voltage:???,current:???,temperature:???,timer:} 组成一个列表，记录这块电池在仿真周期中被充电的过程
        self.charge_start_time = -1                                     #记录t_timer的时间，表明这块电池从什么时候开始被充电 -1 表明还没有被充电
        self.charge_end_time = -1                                       #记录t_timer的时间，表明这块电池从什么时候开始停止充电

    def battery_charge(self, current, timer, interval):
        # current is the charging current within small period of time, the time period defined as interval
        if self.charge_start_time == -1:
            self.charge_start_time = timer #如果之前没有被充过电，记录开始充电时间
        
        self.calc_current_limit() # calc the self.current_command
        if current > self.current_command:
            current = self.current_command
        
        self.soc = (self.soc * self.capacity + interval * current / 3600) / self.capacity

        if self.soc >= self.target_max_soc:
            self.soc = self.target_max_soc
            # self.charge_end_timer = timer #充电终止，记录充电终止时间，这里的充电终止是定义的充电桩充电情况下的终止时间，换电站充电终止SOC在sr.power_distribution模块中
        
        self.set_battery_voltage()

        self.power = self.battery_voltage * current / 1000.0 # return kWh
        temp = {"soc": self.soc, "voltage": self.battery_voltage, "current": current, "temperature": self.temperature, "timer": timer}
        self.charge_history.append(temp)
        self.current = current
        return

    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def battery_discharge(self, current, timer, interval):
        '''
        perform the battery discharge behaviour
        '''
        if self.charge_start_time == -1:
            self.charge_start_time = timer # 如果之前没有被充过电，记录开始充电时间
        # process 1: calculate the current
        self.calc_current_limit() # calc the self.current_command
        if current > self.current_command:
            current = self.current_command
        # process 2: calculate the soc status
        self.soc = (self.soc * self.capacity - interval * current / 3600) / self.capacity
        if self.soc < self.target_min_soc:
            self.soc = self.target_min_soc
        # process 3: calculate the voltage
        self.set_battery_voltage()
        # process 4: calculate the power (negative value means give the power out of the battery)
        self.power = (-1) * self.battery_voltage * current / 1000.0 # return kWh
        # process 5: log the data
        temp = {"soc": self.soc, "voltage": self.battery_voltage, "current": current, "temperature": self.temperature, "timer": timer}
        self.charge_history.append(temp)
        self.current = current

    def set_battery_voltage(self):
        '''
        ocv_100, ocv_70: battery open circuit voltage at each SOC value for 100 kWh and 70 kWh
        set the battery voltage of current time step according to the current_command
        '''
        cal_soc = self.soc
        if cal_soc < 0.05:
            cal_soc = 0.05
        if cal_soc > 1:
            cal_soc = 1
        cal_soc = int(cal_soc * 100) - 5 # maximal SOC = 96%, minimal SOC = 6%
        # set open circuit voltage under current soc value -> give it to battery_voltage
        if self.batterytype == "70kWh":
            
            self.battery_voltage = self.ocv_70[cal_soc]
            return
        else:
            
            self.battery_voltage = self.ocv_100[cal_soc]
            return

    def set_temperature(self, real_temperature):
        '''
        set the simulation temperature (closest to real temperature)
        '''
        test_temperature = [-20, -10, 0, 10, 20, 25, 30, 40]
        diff_min = abs(test_temperature[0] - real_temperature)
        temp = test_temperature[0]
        # find closet test temperature near the real temperature, use it as current temperature
        if isinstance(real_temperature, int):
            for t in test_temperature:
                diff = abs(t - real_temperature)
                if diff < diff_min:
                    temp = t
                    diff_min = diff
        self.temperature = temp
        return

    def calc_current_limit(self): 
        '''
        calculate the maximal current under the given SOC
        '''
        check_soc = self.soc
        if check_soc < 0.05:
            check_soc = 0.05
        if check_soc > 0.95:
            check_soc = 0.95
        if self.limit_axis.count(check_soc) > 0:
                   
            self.current_command = self.charge_limit[self.temperature][self.limit_axis.index(check_soc)]
            return

        for lim in self.limit_axis:
            if lim > check_soc:
                lim_index2 = self.limit_axis.index(lim)
                lim_index1 = lim_index2 - 1
                lim_num1 = self.limit_axis[lim_index1]
                lim_num2 = self.limit_axis[lim_index2]               
                # print("index1 = ",lim_index1,"index2 = ",lim_index2)
                # print("lim_current1 = ",self.charge_limit[temperature][lim_index1])
                # print("lim_current2 = ",self.charge_limit[temperature][lim_index2])
                # print("lim_soc1 = ",lim_num1)
                # print("lim_soc2 = ",lim_num2)
                cur_limit =(check_soc - lim_num1) * (self.charge_limit[self.temperature][lim_index2] - self.charge_limit[self.temperature][lim_index1]) / (lim_num2 - lim_num1)
                cur_limit = cur_limit + self.charge_limit[self.temperature][lim_index1]
                # print("Cur_limit = ",cur_limit)
                self.current_command = cur_limit 
                return

    def request_power(self, current_limit = -1):
        '''
        calculate the battery power output and return in [kW]
        '''
        self.calc_current_limit() # calc current_command
        self.set_battery_voltage() # calc battery_voltage
        if self.current_command > current_limit and current_limit > 0:
            self.current_command = current_limit
        self.power_command = self.battery_voltage * self.current_command / 1000.0
        return

######################################################################
####################### Class: Power_module ##########################
######################################################################

class Power_Module:
    def __init__(self, module, id):
        # 模块参数用字典输入，参数包括最大功率以及最大电流
        self.max_power = module["max_power"]
        self.max_current = module["max_current"]
        self.line_resistance = 0.008 # 8 mohm
        self.id = id
        self.status = "free" # free & in_use
        # Defines the state of being connected to the battery compartment of the swap station 
        # or to an external charging pile
        self.link_to = 0 # 0 disconnect, 正整数 - 换电站内电池仓，负整数 - 充电桩   
        self.power = 0
        self.output_voltage = 0
        self.output_current = 0

    def output_power(self, current_command, battery_voltage): 
        #开启充电，输入指令电流，当前电池电压，根据模块特性返回输出功率和电流
        if self.link_to == 0:
            logger.info("forget to define the module output source")
            return
        if current_command > self.max_current:
            current_command = self.max_current
        expect_voltage = battery_voltage + current_command * self.line_resistance
        expect_power = expect_voltage * current_command / 1000.0 # return value in kW
        if expect_power <= self.max_power:
            self.output_current = current_command
            self.power = expect_power
            self.output_voltage = 1000.0 * self.power / self.output_current # return in Volt
            self.status = "in_use"
        else: # expect_power > max_power
            self.output_current = -1 * battery_voltage + math.sqrt(battery_voltage **2 + 4 * self.line_resistance * self.max_power * 1000)
            self.output_current = self.output_current / 2 / self.line_resistance
            self.power = self.max_power  
            self.output_voltage = 1000.0 * self.power / self.output_current
            self.status = "in_use"
        return
    
    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def grid_interactive_output_power(self, current_command, battery_voltage): 
        '''
        calculate the power supply back to the grid according
        to the grid interaction order and voltage & current
        +1 positive power output means the PSS charge the battery
        -1 negative power output means the PSS discharge battery, send strom back to grid
        '''
        # power module should link to the battery in the swap rack
        if self.link_to <= 0:
            logger.info("Power module doesn't connect to battery in the rack. link_to = %d" %self.link_to)
            return
        # case: current should limited within upper limit
        if current_command > self.max_current:
            current_command = self.max_current
        
        expect_voltage = battery_voltage + current_command * self.line_resistance
        expect_power = expect_voltage * current_command / 1000.0            # return value in kW
        
        if expect_power <= self.max_power:
            self.output_current = current_command
            self.power = -1 * expect_power                                  # negative power output means back to grid
            self.output_voltage = 1000.0 * abs(self.power) / self.output_current # return in Volt
            self.status = "in_use"
        else: # expect_power > max_power
            self.output_current = -1 * battery_voltage + math.sqrt(battery_voltage **2 + 4 * self.line_resistance * self.max_power * 1000)
            self.output_current = self.output_current / 2 / self.line_resistance
            self.power = -1 * self.max_power  
            self.output_voltage = 1000.0 * abs(self.power) / self.output_current
            self.status = "in_use"
        return

    def stop_charge(self): #停止充电
        self.power = 0
        self.output_current=0
        self.link_to = 0
        self.output_voltage = 0
        self.status = "free"

######################################################################
####################### Class: Power_Cabinet #########################
######################################################################

class Power_Cabinet:
    '''
    Define the arrangement of Cabinet
    2.0 Unmanned: 13 Power Modules with UU40kW
    3.0 Unmanned PUS A: 10 Power Modules with UU60KW
    3.0 Unmanned PUS B: 20 Power Modules with UU60KW
    '''
    def __init__(self, station_type, pw_module_info = None):
        self.module_list = []
        self.module_number = 0

        # For PSS 2.0
        if station_type == "GEN2_530":
            self.cabinet_type = "GEN2_CAB"
            self.module_number = 13
            for i in range(self.module_number):
                self.module_list.append(Power_Module(GC.UU40kW, i)) # module, id
            self.module_power = self.module_list[0].max_power
            self.module_current = self.module_list[0].max_current
        

        # For PSS 3.0 PUS A, B chargeable module
        if station_type == "GEN3_1200":
            self.cabinet_type = "GEN3_CAB"
            self.module_number = 10  
            for i in range(self.module_number):
                self.module_list.append(Power_Module(GC.UU60kW,i))
            self.module_power = self.module_list[0].max_power
            self.module_current = self.module_list[0].max_current
        
        # For PSS FY_TypeA
        if station_type == "FY_TypeA":
            self.cabinet_type = "FY_A_CAB"
            self.module_number = 15  
            for i in range(self.module_number):
                self.module_list.append(Power_Module(GC.UU40kW,i))
            self.module_power = self.module_list[0].max_power
            self.module_current = self.module_list[0].max_current
        
        # For PSS FY_TypeB
        if station_type == "FY_TypeB":
            self.cabinet_type = "FY_B_CAB"
            self.module_number = 21  
            for i in range(self.module_number):
                self.module_list.append(Power_Module(GC.UU30kW,i))
            self.module_power = self.module_list[0].max_power
            self.module_current = self.module_list[0].max_current

        # For PSS FY_TypeC
        if station_type == "FY_TypeC":
            self.cabinet_type = "FY_C_CAB"
            self.module_number = 33  
            for i in range(self.module_number):
                self.module_list.append(Power_Module(GC.UU40kW,i))
            self.module_power = self.module_list[0].max_power
            self.module_current = self.module_list[0].max_current

        # For PSS FY_TypeD
        if station_type == "FY_TypeD":
            self.cabinet_type = "GEN3_CAB"
            self.module_number = 10  
            for i in range(self.module_number):
                self.module_list.append(Power_Module(GC.UU60kW,i))
            self.module_power = self.module_list[0].max_power
            self.module_current = self.module_list[0].max_current

        if station_type == "User_Defined":
            self.cabinet_type = "User_Defined"
            self.module_number = pw_module_info["max_charger_number"] 
            for i in range(int(self.module_number)):
                self.module_list.append(Power_Module(pw_module_info["power_module_type"],i))
            self.module_power = self.module_list[0].max_power
            self.module_current = self.module_list[0].max_current

    def config_module(self, config_map): # config_map: list
        '''
        Detect the Error of arrangement (module number inconsistence)
        Connect the modules according to the config_map
        '''
        if len(config_map) != self.module_number:
            logger.error('config map size not matching module number')
            return
        for i in range(len(self.module_list)):
            self.module_list[i].link_to = config_map[i]
            if self.module_list[i].link_to == 0:
                self.module_list[i].stop_charge()
        return

    def get_power_pc(self):
        '''
        get total power of current time step, used for data logging
        '''
        total_power = 0
        for i in range(len(self.module_list)):
            if self.module_list[i].link_to != 0:
                total_power += self.module_list[i].power
        return total_power

######################################################################
####################### Class: Battery_Rack ##########################
######################################################################

class Battery_Rack:
    '''
    Basic parameters and operations related to single-layer battery racks are defined
    '''
    def __init__(self, id): 
        self.id = id # id number of battery rack (index of list), begins from 0
       
        self.status = "free" 
        '''
        Definition of status
        free: No battery avaiable
        loaded: battery stored in the rack
        charging: battery in charge
        discharging : battery in discharge back to grid
        '''
        self.battery = None # save a Battery instance
        self.plug = 0 # 0 - 电连接器断开;1 - 电连接器连接
        '''
        Definition of plug
        0: disconnected
        1: connected
        '''

    def plug_in(self):
        '''
        set to "charging"
        '''
        if self.battery is not None: #如果发现电池架上有电池
            self.plug = 1
            self.status = "charging" #更新电池状态为可以接受充电,唯一的地方可以将充电开启状态设置为charging的地方

    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def plug_in_for_discharge(self):
        '''
        set to discharge
        '''
        if self.battery is not None:
            self.plug = 1
            self.status = "discharging"

    def plug_out(self):
        '''
        charging -> loaded
        else -> free
        '''
        if self.status == "charging" or self.status == "discharging": #如果在等待充电状态拔掉插头，退出充电状态
            if self.battery is not None: #如果有电池，将电池架状态设置为装载
                self.status = "loaded"
            else:
                self.status = "free" #否则将电池架状态设置为空闲
        self.plug = 0

    def start_charge(self):
        if self.battery is not None: #如果电池架上有电池
            self.plug_in() #插入后自动充电
            return True
        else:
            return False
    
    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################    
    def start_discharge(self):
        if self.battery is not None: #如果电池架上有电池
            self.plug_in_for_discharge() #插入后自动放电回电网
            return True 
        else:
            return False

    def stop_charge(self):
        if self.battery is not None: #如果电池架上有电池
            self.status = "loaded"
        self.plug_out()
    
    def load_battery(self, battery : Battery):# 成功装载一个电池返回电池架id，否则返回 -1，表示原本就有电池
        if self.battery is not None: #如果电池架上已经有电池
            return -1 #返回-1表示失败
        else:
            self.battery = battery
            self.status = "loaded"
            self.plug_out
            return self.id

    def remove_battery(self): # 成功remove一个电池返回电池架id，否则返回 -1，表示原本就是空的
        if self.battery is not None: #如果电池架上有电池
            self.stop_charge()
            self.battery = None
            self.status = "free"
            return self.id
        else:
            self.plug_out()
            self.status = "free" 
            return -1

######################################################################
####################### Class: Charge_PIle ###########################
######################################################################

class Charge_Pile:
    def __init__(self, max_current, pile_id): #充电枪头只定义最大充电电流 max current = 650
        '''
        Definition of status for piles
        free: No vehicle connected
        connected: vehicle connected but not charged
        charging: vehicle is in charging
        '''
        self.status = "free" #free & connected & charging
        self.vehicle_battery = None # 连接到充电桩的车载电池
        self.max_current = max_current 
        self.output_power = 0
        self.output_current = 0
        self.id = pile_id # 这是表明piles在充换一体站中的编号
        return
         
    def connect_to_vehicle(self, vehicle_battery : Battery):
        '''
        connect vehicle and piles, success return index of pile, failure return -1
        '''
        if vehicle_battery is None: #如果连接的电池为空
            logger.error('pile %d : vehicle_battery not exist',self.id)
            return -1 #连接车辆电池失败    
        elif self.vehicle_battery is not None: # for allready connected piles
            logger.info('pile %d : already has vehicle connected',self.id)
            return -1 #连接车辆电池失败
        else:
            self.status = "connected"
            self.vehicle_battery = vehicle_battery
            return self.id
    
    def vehicle_leave(self): #车辆离开充电桩
        if self.vehicle_battery is None:
            logger.info('pile does not have vehicle connected, pile status = %s, pile# %d',self.status,self.id)
            return -1
        self.stop_charge()
        self.status = "free"
        self.vehicle_battery = None
        return self.id
    
    def stop_charge(self): #充电终端停止充电
        if self.vehicle_battery is None: #如果没有电池连接到充电终端
            # logger.debug('temp to stop charge when there is no vehicle connected, pile status = %s, pile# %d',self.status,self.id)
            self.status = "free"
            return
        else:
            self.status = "connected"
            return

    def start_charge(self): #充电终端开启充电
        if self.vehicle_battery is None: #如果没有电池连接到充电终端
            # logger.debug('temp to start charge when there is no vehicle connected, pile status = %s',self.status)
            self.status = "free"
            return -1
        else:
            self.status = "charging"
            return

######################################################################
####################### Class: Swap_Rack #############################
######################################################################

class Swap_Rack:
# 定义了一组电池架，定义了电池架数量，每个电池仓储位置可以分配到的基本功率，每个电池架支持的外部充电桩扩展数量
# 以及配合多少，什么样的充电模块等参数    
    def __init__(self, param, station_type, psc_num, id):
        self.id = id
        self.psc_num = psc_num
        self.battery_num = 0
        self.pile_connected = 0
        self.battery_rack_list = []
        self.charge_pile_list = []
                                                    # define how module connect with battery or charge pile (index->ID of modules, values->connection form)
        self.connection_map = []                    # 定义了每一个模块连接到电池和充电桩的状态
        self.station_type = station_type
        self.target_soc = param["target_soc"]       # For PSC upper limit
        self.select_soc = param["select_soc"]       # For PSS upper limit
        self.set_sr_temperature()                   # 缺省仓内温度和外部温度为25度
        self.charge_power_redist_trigger = param["charge_power_redist"] # bool
        self.power_dist_option = param["power_dist_option"] # "PSS prefered" or "PSC prefered"

        # For PSS 2.0
        if station_type == "GEN2_530":
            self.power_cabinet = Power_Cabinet(station_type)
            self.max_rack_number = 13
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i)) 
            self.max_pile_number = 0
            self.charge_pile_list = None
            self.connection_map = [0,0,0,0,0,0,0,0,0,0,0,0,0]
            '''
            Definition of connection_map
            list index: Index number of power modules in the cabinet
            list value:
                0: current power module has "No connection"
                -1 ... -4: Index number of charge Pile, current power module connect with this pile No.
                1 ... N: Index number of batteries, current power modules connect with this battery No.
            
            connection_map说明：
            connection_map定义了每一个功率模块输出和需求端的连接关系
            connection_map每一个元素的index代表模块的index，数值代表连接目标，连接目标包括站内电池架电池以及站外的充电终端
            connection_map中元素如果为大于0的正整数N，表示该模块连接到站内第N号电池架，电池架battery_rack的index等于 N-1
            connection_map中元素如果为小于0的负整数N，表示该模块连接到站外第N号充电终端，充电终端pile的index等于 -1*N-1
            connection_map中元素如果为0，表示该模块没有连接到任何充电设备
            例： connection_map[0] = 1 第0号模块连接到0号电池架
            例： connection_map[1] = -2 第1号模块连接到1号充电终端
            例： connection_map[2] = 0 第2号模块无任何连接，不输出
            '''
        
        # Swap Rack Arrangement:
        # For PSS 3.0 PUS A: one Form 1 + one Form 2
        # For PSS 3.0 PUS B: two Form 2
        
        # For PSS 3.0 Form 1
        if station_type == "GEN3_600":
            self.power_cabinet = None
            self.max_rack_number = 10
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i))
            self.max_pile_number = 0
            self.charge_pile_list = None
            self.connection_map = []
        
        # For PSS 3.0 Form 2
        if station_type == "GEN3_1200":
            self.power_cabinet = Power_Cabinet(station_type)
            self.max_rack_number = 10
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i)) # i -> id
            self.max_pile_number = int(self.psc_num)
            for i in range(self.max_pile_number):
                self.charge_pile_list.append(Charge_Pile(650, i)) # i -> id
            self.connection_map = [0,0,0,0,0,0,0,0,0,0]

        # For PSS FY Type A
        if station_type == "FY_TypeA":
            self.power_cabinet = Power_Cabinet(station_type)
            self.max_rack_number = 15
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i)) # i -> id
            self.max_pile_number = 0
            self.charge_pile_list = None
            self.connection_map = [0,0,0,0,0,0,0,0,0,0,
                                    0,0,0,0,0]

        # For PSS FY Type B
        if station_type == "FY_TypeB":
            self.power_cabinet = Power_Cabinet(station_type)
            self.max_rack_number = 21
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i)) # i -> id
            self.max_pile_number = 0
            self.charge_pile_list = None
            self.connection_map = [0,0,0,0,0,0,0,0,0,0,
                                   0,0,0,0,0,0,0,0,0,0,
                                   0]

        # For PSS FY Type C
        if station_type == "FY_TypeC":
            self.power_cabinet = Power_Cabinet(station_type)
            self.max_rack_number = 33
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i)) # i -> id
            self.max_pile_number = 0
            self.charge_pile_list = None
            self.connection_map = [0,0,0,0,0,0,0,0,0,0,
                                   0,0,0,0,0,0,0,0,0,0,
                                   0,0,0,0,0,0,0,0,0,0,
                                   0,0,0]

        # For PSS FY Type D
        if station_type == "FY_TypeD":
            self.power_cabinet = Power_Cabinet(station_type)
            self.max_rack_number = 10
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i)) # i -> id
            self.max_pile_number = 0
            self.charge_pile_list = None
            self.connection_map = [0,0,0,0,0,0,0,0,0,0]

        # For User Defined
        if station_type == "User_Defined":
            self.power_cabinet = Power_Cabinet(station_type, pw_module_info=param["station_type"])
            self.max_rack_number = int(param["station_type"]["max_charger_number"])
            for i in range(self.max_rack_number):
                self.battery_rack_list.append(Battery_Rack(i)) # i -> id
            self.max_pile_number = int(self.psc_num)
            for i in range(self.max_pile_number):
                self.charge_pile_list.append(Charge_Pile(650, i)) # i -> id
            cm = np.zeros(int(param["station_type"]["max_charger_number"]))
            self.connection_map = list([int(s) for s in cm])


    def set_temperature(self, real_temp):
        '''
        set simulation temperature (setup test temp that closest to the real temp)
        '''
        test_list_dict = [-20,-10,0,10,20,25,30,40]
        diff_min = abs(test_list_dict[0] - real_temp)
        temp = test_list_dict[0]
        if isinstance(real_temp, int):
            for t in test_list_dict:
                diff = abs(t - real_temp)
                if diff < diff_min:
                    temp = t
                    diff_min = diff
        return temp

    def set_sr_temperature(self, rack_temperature = 25, external_temperature = 25):
        '''
        set swap rack temp = 25 (real)
        set external temp = 25 (real)
        set batteries temp (in rack) = rack temp
        set batteries on vehicles temp = external temp
        '''
        self.rack_temperature = self.set_temperature(rack_temperature)
        self.external_temperature = self.set_temperature(external_temperature)
        for rack in self.battery_rack_list:
            if isinstance(rack.battery, Battery):
                rack.battery.set_temperature(rack_temperature)
        if self.charge_pile_list is not None:
            for pile in self.charge_pile_list:
                if isinstance(pile.vehicle_battery, Battery): 
                    pile.vehicle_battery.set_temperature(external_temperature)
        return

    def load_battery(self, battery : Battery, position = -1):
        '''
        put batteries into battery rack
        position: -1, find first empty position; otherwise, put battery into given position index
        '''
        if battery is not None: #如果电池是存在的
            if position == -1:  #对于参数为-1，自动寻找第一个空闲位置导入电池
                for battery_rack in self.battery_rack_list:
                    if battery_rack.status == "free":
                        self.battery_num += 1
                        return(battery_rack.load_battery(battery)) # return battery rack id or -1
            else:
                if position < len(self.battery_rack_list) and position >= 0:
                    if self.battery_rack_list[position].status == "free":
                        self.battery_num += 1
                        return(self.battery_rack_list[position].load_battery(battery))
        return -1 # return failed

    def unload_battery(self, position = -1):
        '''
        take batteries out of battery rack
        position: -1, take all batteries; otherwise, take out battery from given position index
        '''
        if position == -1:
            for battery_rack in self.battery_rack_list:
                battery_rack.remove_battery() # return rack id or -1, status -> free
            self.battery_num = 0
            return
        
        else:
            if self.battery_rack_list[position].status != "free":
                self.battery_rack_list[position].remove_battery()
                self.battery_num -= 1
                return

    def stop_charge(self, equipment_number): # equipment number 对于电池仓内电池编号为 0 ~ N，对于充电终端编号为 -1 ~ -N
        '''
        stop the charging behaviour for batteries or charge piles
        equipment_number: 0 -> N: battery; -1 -> -M: charge pile 
        '''
        # For battery
        if equipment_number >= 0: #内部电池架准备停止充电
            if equipment_number >= len(self.battery_rack_list):
                logger.error('stop_charge:equipment number %d larger than rack number %d',equipment_number,len(self.battery_rack_list))
                return
            self.battery_rack_list[equipment_number].stop_charge()
            return
        # For charge pile
        if equipment_number < 0: #充电桩停止充电
            equipment_number = (equipment_number * (- 1)) - 1 #更改成充电桩列表的index
            if equipment_number >= len(self.charge_pile_list):
                logger.error('stop_charge:equipment number %d larger than charger number %d',equipment_number,len(self.charge_pile_list))
                return
            self.charge_pile_list[equipment_number].stop_charge()
            return
            
    def stop_charge_all(self): #停止所有站内电池和充电桩充电
        '''
        stop charging behaviour for all facilities
        '''
        if self.power_cabinet is None:
            if self.power_cabinet is None:
                logger.debug('swap rack without power cabinet: exit')
                return
            
        if self.battery_rack_list is not None:
            for i in range(len(self.battery_rack_list)): #站内电池全部停止充电
                self.stop_charge(i)
        if self.charge_pile_list is not None:
            for i in range(len(self.charge_pile_list)): #充电桩全部停止充电
                self.stop_charge((i + 1) * (-1))

    def start_charge(self, equipment_number): # equipment number 对于电池仓内电池编号为 0 ~ N，对于充电终端编号为 -1 ~ -N
        '''
        start the charging behaviour
        equipment_number: 0->N:battery; -1->-M:charge pile
        '''
        if equipment_number >= 0: #内部电池架准备开启充电
            if equipment_number >= len(self.battery_rack_list):
                logger.error('start_charge:equipment number %d larger than rack number %d',equipment_number,len(self.battery_rack_list))
                return
            self.battery_rack_list[equipment_number].start_charge()
        
        if equipment_number < 0: #预留充电桩开启充电
            equipment_number = (equipment_number * (-1)) - 1 #更改成充电桩列表的index
            if equipment_number >= len(self.charge_pile_list):
                logger.error('start_charge:equipment number %d larger than charger number %d',equipment_number,len(self.charge_pile_list))
                return
            self.charge_pile_list[equipment_number].start_charge()
        
    def start_charge_all(self): #开启所有站内电池和充电桩充电
        '''
        start charging behaviour for all facilities
        '''
        if self.power_cabinet is None:
            logger.debug('swap rack without power cabinet: exit')
            return
        if self.battery_rack_list is not None:        
            for i in range(len(self.battery_rack_list)):
                self.start_charge(i)
        if self.charge_pile_list is not None:        
            for i in range(len(self.charge_pile_list)):  #充电桩全部开始充电
                self.start_charge((i + 1) * (-1))
    
    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def start_discharge(self, equipment_number):
        '''
        start the discharge behaviour of certain battery rack
        '''
        if equipment_number >= 0: #内部电池架准备开启充电
            if equipment_number >= len(self.battery_rack_list):
                logger.error('start_charge:equipment number %d larger than rack number %d',equipment_number,len(self.battery_rack_list))
                return
            self.battery_rack_list[equipment_number].start_discharge()

    def connect_vehicle(self, vehicle_battery : Battery, pile_number : int): # 充电桩连接外部车辆电池, pile_number 为 0 ~ N(这里使用的是充电桩列表的index)
        '''
        connect pile with vehicle battery
        pile_number: index of charge pile list
        '''
        if pile_number < 0 or pile_number >= len(self.charge_pile_list):
            logger.error('pile number %d larger than charger number %d',pile_number,len(self.charge_pile_list))
            return -1
        if vehicle_battery is not None: #如果车辆电池存在
            if self.charge_pile_list[pile_number].connect_to_vehicle(vehicle_battery) >= 0: # pile id
                self.pile_connected += 1
                return pile_number
            else:
                return -1
        else:
            return -1
        
    def vehicle_leave(self, pile_number : int): #车辆离开充电终端, pile_number 为 0 ~ N(这里使用的是充电桩列表的index)
        '''
        vehicle leaves the charge pile
        pile number: index of charge pile list
        '''
        if pile_number < 0 or pile_number >= len(self.charge_pile_list):
            logger.error('pile number %d larger than charger number %d',pile_number,len(self.charge_pile_list))
            return
        if self.charge_pile_list[pile_number].vehicle_leave() >= 0: # pile id
            self.pile_connected -= 1

    def module_number_check(self, battery : Battery, current_limit = 250): #计算电池可以被几个模块充电，返回模块数量
        '''
        calculate the maximal allowable number of power modules (in Power Cabinet) to a battery
        return 0 or module_num
        '''
        # No battery return 0 module
        if battery is None:
            return 0
        # battery reachs its target soc return 0 module
        if battery.soc >= battery.target_max_soc:
            return 0
        
        battery.request_power(current_limit = 250) # calc power_command
        current_allowable = min(battery.current_command, current_limit)        
        power_allowable = current_allowable * battery.battery_voltage / 1000.0 # max allowable power return in kW
        for i in range(10):
            module_num = i + 1
            powerd = power_allowable / module_num
            currentd = current_allowable / module_num
            if powerd <= self.power_cabinet.module_power or currentd <= self.power_cabinet.module_current:
                break
        return module_num

    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def connect_charge_pile(self, pile : Charge_Pile): #将充电终端车辆电池连接到最大可以连接到的模块上，体现在connection_map里,如果成功连接，返回True
        '''
        connect the pile with max number of Power modules
        '''
        if pile.vehicle_battery is None:
            logger.error('pile number %d no vehicle connected - %s',pile.id,pile.status)
            return False
        # calculate the max allowable number of modules connect with this battery
        module_num = self.module_number_check(pile.vehicle_battery, pile.max_current)
        # get the num of still connectable power modules
        module_num = module_num - self.connection_map.count(-1 * pile.id  - 1) # pile id: 0 -> N; pile id in connection map: -N-1 -> -1
        
        # strategy 1: PSS prefered
        if self.power_dist_option == "PSS preferred":
            for i in range(len(self.connection_map)):
                # if current module is free and battery still allow to connect with another module
                if self.connection_map[i] == 0 and module_num > 0:
                    module_num -= 1
                    self.connection_map[i] = ((-1) * pile.id - 1) # for pile index: -1 -> -N-1
                # if current module connect with this id pile, but extend max allowable connection number of modules
                if self.connection_map[i] == ((- 1) * pile.id -1) and module_num < 0:
                    module_num += 1
                    self.connection_map[i] = 0
                # if battery allready connected with max allowable number of modules
                if module_num == 0:
                    break
        # strategy 2: PSC prefered
        else:
            rack_soc_list = self.get_rack_battery_soc()
            while module_num > 0:
                for i in range(len(self.connection_map)):
                    # if current module is free and battery still allow to connect with another module
                    if self.connection_map[i] == 0 and module_num > 0:
                        module_num -= 1
                        self.connection_map[i] = ((-1) * pile.id - 1) # for pile index: -1 -> -N-1
                    # if current module connect with this id pile, but extend max allowable connection number of modules
                    if self.connection_map[i] == ((- 1) * pile.id -1) and module_num < 0:
                        module_num += 1
                        self.connection_map[i] = 0
                    # if battery allready connected with max allowable number of modules
                    if module_num == 0:
                        break
                # after arrangement if residual num still > 0 -> reconnect rack power module with min soc to the PSC
                if module_num > 0:
                    rack_idx = self.get_min_soc_rack_index(rack_soc_list)
                    map_idx = [x for x,y in list(enumerate(self.connection_map)) if y == rack_idx+1]
                    self.stop_charge(rack_idx)
                    for i in map_idx:
                        self.connection_map[i] = ((-1) * pile.id - 1)
                    rack_soc_list.remove(min(rack_soc_list))
                    module_num -= 1
                else:
                    break

    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def get_rack_battery_soc(self):
        '''
        read the rack list and get all soc values -> return in format list
        '''
        rack_battery_soc = []
        for i in range(len(self.battery_rack_list)):
            if isinstance(self.battery_rack_list[i].battery, Battery): #如果相应电池存在
                    rack_battery_soc.append(self.battery_rack_list[i].battery.soc)
        return rack_battery_soc
    
    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def get_min_soc_rack_index(self, soc_list:list):
        '''
        return the index of corresponding minimal value of rack soc
        '''
        idx = soc_list.index(min(soc_list))

        return idx 

    def power_distribution_max(self):
        '''
        distribute the power arrangement
        功率分配原则为，偶数仓0/2/4/6/8/10/12可以分配到N以及N+1的功率，奇数仓可以分配到N以及N-1的功率
        对外放电的功率分配原则为：0-9号（10块电池）功率可以向0-3号外部充电终端分配，10-19号（10块电池）功率可以向4-7号外部充电终端分配
        '''
        # ======================================================================================
        # ================= Part 0: Exception case -> No Power Cabinet =========================
        # ======================================================================================
        # 如果这个电池仓没有功率柜
        if self.power_cabinet is None: 
            # logger.debug('no power cabinet connected')
            return
        
        # ======================================================================================
        # ================= Part 1: Get the power request for PSS and charge piles =============
        # ======================================================================================
        
        # save the battery power command
        swap_power_req = []
        for battery_rack in self.battery_rack_list:
            if battery_rack.battery is not None:
                battery_rack.battery.request_power()
                if battery_rack.battery.soc < self.select_soc:
                    swap_power_req.append(battery_rack.battery.power_command)
                else:
                    swap_power_req.append(-1) # -1 means no power request
            else:
                swap_power_req.append(-1)
        # save the pile(vehicle battery) power command
        charge_power_req = []
        for charge_pile in self.charge_pile_list:
            if charge_pile.vehicle_battery is not None:
                charge_pile.vehicle_battery.Request_Power(current_limit=charge_pile.max_current)
                if charge_pile.vehicle_battery.soc < charge_pile.vehicle_battery.target_max_soc:
                    charge_power_req.append(charge_pile.vehicle_battery.power_command)
                else:
                    charge_power_req.append(-1)
                    charge_pile.vehicle_leave()
            else:
                charge_power_req.append(-1)
    # 以上对目前所有可以充电的目标电池的充电功率需求进行计算，得到目前各个充电负载的功率需求
    # 换电站的充电功率需求存放在swap_power_req列表中
    # 充电终端的充电功率需求存放在charge_power_req列表中
    
        # ======================================================================================
        # ================= Part 2: Setup the power arrangement in the PSS =====================
        # ======================================================================================

        #如果换电站内的电池有充电需求，首先连接一个模块给需求仓位
        connection_map_save = self.connection_map
        for i in range(len(self.connection_map)):
            self.connection_map[i] = 0 # rearrange the power connection 
            if swap_power_req[i] > 0:
                self.connection_map[i] = i + 1 # battery index 0 -> N; battery index in connection map: 1 -> N + 1
    
        #如果换电站内有电池请求的充电模块>1 且存在可以分配的临近功率模块，则将模块和电池仓内电池连接
        for i in range(len(self.battery_rack_list)):
            if (i % 2) == 0: # 偶数位
                if self.connection_map[i] == i + 1 and i + 1 < len(self.battery_rack_list):
                    r_b = self.battery_rack_list[i].battery
                    m_n = self.module_number_check(r_b, current_limit = 250) #换电站内电流最大限制为250                                                        
                    if m_n > 1:
                        if self.connection_map[i + 1] == 0:
                            self.connection_map[i + 1] = i + 1
            else: # 奇数位
                if self.connection_map[i] == i + 1:
                    r_b = self.battery_rack_list[i].battery
                    m_n = self.module_number_check(r_b, current_limit = 250) #换电站内电流最大限制为250                                                        
                    if m_n > 1:
                        if self.connection_map[i - 1] == 0:
                            self.connection_map[i - 1] = i + 1

        # ======================================================================================
        # ================= Part 3: Setup the power arrangement for charge piles ===============
        # ======================================================================================

        #如果原本外部充电桩已经有充电模块连接的优先分配一个模块
        for j in range(len(self.charge_pile_list)): #检查原本充电中的充电桩负载
            r_b = self.charge_pile_list[j].vehicle_battery
            m_n = self.module_number_check(r_b, current_limit = self.charge_pile_list[j].max_current)
            pid = -1 * j - 1 # charge piles index in connection_map:  -1 -> -N - 1
            if connection_map_save.count(pid) > 0 and m_n > 0: #如果原本充电连接里存在连接，而且目前需要的充电模块数量大于0
                for i in range(len(self.connection_map)):
                    if self.connection_map[i] == 0: #如果有可以分配的模块
                        self.connection_map[i] = pid #连接充电模块到目标充电桩
        
        #如果充电模块依旧有空余，连接到外部充电设备
        for j in range(len(self.charge_pile_list)):
            r_b = self.charge_pile_list[j].vehicle_battery
            m_n = self.module_number_check(r_b, current_limit = self.charge_pile_list[j].max_current)
            pid = -1 * j - 1
            m_n = m_n - self.connection_map.count(pid)
            for i in range(len(self.connection_map)):
                if self.connection_map[i] == 0 and m_n > 0:
                    self.connection_map[i] = pid
                    m_n -= 1

        # ======================================================================================
        # ================= Part 4: config modules and start charging behaviour ================
        # ======================================================================================

        self.power_cabinet.config_module(self.connection_map)
        self.stop_charge_all()
        for equipment_id in self.connection_map:
            if equipment_id > 0: #如果是电池内部的equipment
                self.start_charge(equipment_id - 1)
            if equipment_id < 0: #如果是外部充电桩的equipment
                self.start_charge(equipment_id)
        return
        
    def power_distribution_pss_preferred(self):
        '''
        根据当前连接电池状态计算功率分配规则 通过connection_map列表实现
        规则 1: 换电站内电池SOC达到换电站终止充电SOC(select_soc)就停止充电并释放充电模块
        规则 2：换电站内电池优先级高于充电桩优先级，当换电站有剩余功率时才对外分配 -> modify!
        规则 3：充电桩完成充电前，功率模块不释放

        功率分配原则为，偶数仓0/2/4/6/8/10/12可以分配到N以及N+1的功率，奇数仓可以分配到N以及N-1的功率
        对外放电的功率分配原则为：0-9号（前10个充电模块）功率可以向0-3号外部充电终端分配，10-19号（后10个充电模块）功率可以向4-7号外部充电终端分配

        connection_map说明：
        connection_map定义了每一个功率模块输出和需求端的连接关系
        connection_map每一个元素的index代表模块的index，数值代表连接目标，连接目标包括站内电池架电池以及站外的充电终端
        connection_map中元素如果为大于0的正整数N，表示该模块连接到站内第N号电池架，电池架battery_rack的index等于N-1
        connection_map中元素如果为小于0的负整数N，表示该模块连接到站外第N号充电终端，充电终端pile的index等于-1*N-1
        connection_map中元素如果为0，表示该模块没有连接到任何充电设备
        例： connection_map[0] = 1 第0号模块连接到0号电池架
        例： connection_map[1] = -2 第1号模块连接到1号充电终端
        例： connection_map[2] = 0 第2号模块无任何连接，不输出
        '''

        # ======================================================================================
        # ================= Part 0: Exception case -> No Power Cabinet =========================
        # ======================================================================================

        if self.power_cabinet is None: #如果这个电池仓没有功率柜
            if(self.station_type != "GEN3_600"):
                logger.debug('no power cabinet connected')
            return
        
        # ======================================================================================
        # ================= Part 1: Arrangement power modules to PSS and charge piles ==========
        # ======================================================================================

        for i in range(len(self.connection_map)):
            # case 1: check the Battery in Swap Rack
            if self.connection_map[i] > 0:
                '''
                如果当前模块分配到站内电池架
                在以下几种情况下：
                1. 电池架上没有电池 - 释放模块，同时将Rack设定为remove_battery状态
                2. 电池已经充满
                3. 电池plug已经被拔掉 - 释放模块，同时将rack设定为plug_out状态
                通过将connection_map相应位置置零的方式释放模块
                '''
                rack_id = self.connection_map[i] - 1

                if isinstance(self.battery_rack_list[rack_id].battery, Battery): #如果相应电池存在
                    # for event 2 and 3
                    if self.battery_rack_list[rack_id].battery.soc >= self.select_soc or self.battery_rack_list[rack_id].plug == 0:
                        self.battery_rack_list[rack_id].plug_out()
                        self.connection_map[i] = 0
                else:
                    # for event 1
                    self.connection_map[i] = 0
                    self.battery_rack_list[rack_id].remove_battery()

            # case 2: PSC charge piles
            if self.connection_map[i] < 0:
                '''
                如果当前模块分配到充电桩
                在以下几种条件按下：
                1. 充电桩没有连接车辆电池 - 释放充电模块，充电桩vehicle_leave
                2. 车辆电池SOC已经达到设定值 target_max_soc - 释放充电模块，充电桩stop_charge
                3. 车辆停止充电 pile.status = "connected" - 释放充电模块，充电桩stop_charge
                '''
                if self.charge_pile_list is not None:
                    # recalculate the charge pile id
                    pile_id = -1 * self.connection_map[i] - 1

                    if isinstance(self.charge_pile_list[pile_id].vehicle_battery, Battery): #如果相应电池存在
                        # for case 2 and 3
                        if self.charge_pile_list[pile_id].vehicle_battery.soc >= self.target_soc or self.charge_pile_list[pile_id].status == "connected":
                            self.connection_map[i] = 0
                            self.charge_pile_list[pile_id].stop_charge()    
                    else:
                        # for case 1
                        self.connection_map[i] = 0      
                        self.charge_pile_list[pile_id].vehicle_leave()       
                else:
                    logger.error('do not have charge pile list')
        
        # ======================================================================================
        # ================= Part 2: Power distribution and optimization ========================
        # ======================================================================================
                 
        #重新检查换电站功率分配，是否维持两个模块同时输出
        for i in range(len(self.battery_rack_list)):
            if self.connection_map.count(i + 1) > 1:                                        # check if one item connect with more than one power module
                rack_battery = self.battery_rack_list[i].battery
                module_num = self.module_number_check(rack_battery, current_limit = 250)    #换电站内电流最大限制为250
                if module_num < 2:                                                          #如果一个模块就可以支持充电
                    if (i % 2) == 0:                                                        #如果是0/2/4..号电池架
                        if i < len(self.battery_rack_list) - 1:                             #保护 i + 1 index 不溢出
                            self.connection_map[i + 1] = 0                                  # release the residual power module
                    else:
                        self.connection_map[i - 1] = 0


        #根据换电站仓位功率需求分配充电模块
        for i in range(len(self.battery_rack_list)):
            # Battery exists & battery soc < target soc & power module pluged
            if isinstance(self.battery_rack_list[i].battery, Battery) and self.battery_rack_list[i].battery.soc < self.select_soc and self.battery_rack_list[i].plug == 1:
                rack_battery = self.battery_rack_list[i].battery
                module_num = self.module_number_check(rack_battery, current_limit = 250)
                # 如果这个模块被外部充电桩占用，而且连接数大于1，则不做处理
                if self.connection_map[i] < 0 and self.connection_map.count(self.connection_map[i]) > 1: 
                    pass
                else:
                    # 如果模块未被外部充电桩占用，则首先保证电池仓内没有充满的且连接器插上的电池可以被充电
                    self.connection_map[i] = i + 1 
                
                # 强制将外部充电桩的功率分配回站内
                if self.charge_power_redist_trigger == True: 
                    self.connection_map[i] = i + 1
                
                #如果可以被相邻的充电模块充电,或者这个模块被外部占用
                if module_num > 1 or self.connection_map[i] != i + 1: 
                    if (i % 2) == 0: 
                        if i < len(self.battery_rack_list) - 1: #保护i + 1 index 不溢出
                            if self.connection_map[i + 1] == 0:
                                self.connection_map[i + 1] = i + 1
                    else:
                        if self.connection_map[i - 1] == 0:
                            self.connection_map[i - 1] = i + 1

        #优化已经连接的外部充电桩充电功率
        if self.charge_pile_list is not None:
            for pile in self.charge_pile_list:
                # if exists battery connected to PSC
                if isinstance(pile.vehicle_battery, Battery):
                    if pile.vehicle_battery.soc >= self.target_soc: #如果已经充至指定soc，车辆离开
                    # if pile.vehicle_battery.soc >= pile.vehicle_battery.target_max_soc: #如果已经充满，车辆离开
                        self.vehicle_leave(pile.id)
                    if pile.status == "charging": #如果还在充电，优化一下充电功率
                        self.connect_charge_pile(pile) #这里们有一个优先级的问题。暂时未能解决

            #根据剩余功率为外部充电桩分配充电模块
            for pile in self.charge_pile_list:
                if pile.vehicle_battery is not None: #如果充电终端连接了电池
                    if pile.status == "connected" and self.connection_map.count(-1 * pile.id - 1) == 0: #没有在充电，而且没有分配模块
                        self.connect_charge_pile(pile) #将充电终端通过connect_map连接到模块上，连连看
        
        # ======================================================================================
        # ================= Part 3: Restart the power distribution and charging ================
        # ======================================================================================

        self.power_cabinet.config_module(self.connection_map)
        self.stop_charge_all()
        for equipment_id in self.connection_map:
            if equipment_id > 0: #如果是电池内部的equipment
                self.start_charge(equipment_id - 1)
            if equipment_id < 0: #如果是外部充电桩的equipment
                self.start_charge(equipment_id)

    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def power_distribution_psc_preferred(self):
        '''
        根据当前连接电池状态计算功率分配规则 通过connection_map列表实现
        规则 1: 换电站内电池SOC达到换电站终止充电SOC(select_soc)就停止充电并释放充电模块
        规则 2：充电桩优先级高于站内电池，优先满足充电桩功率分配，之后给站内电池
        规则 3：充电桩完成充电前，功率模块不释放

        功率分配原则为，偶数仓0/2/4/6/8/10/12可以分配到N以及N+1的功率，奇数仓可以分配到N以及N-1的功率
        对外放电的功率分配原则为：0-9号（前10个充电模块）功率可以向0-3号外部充电终端分配，10-19号（后10个充电模块）功率可以向4-7号外部充电终端分配

        connection_map说明：
        connection_map定义了每一个功率模块输出和需求端的连接关系
        connection_map每一个元素的index代表模块的index，数值代表连接目标，连接目标包括站内电池架电池以及站外的充电终端
        connection_map中元素如果为大于0的正整数N，表示该模块连接到站内第N号电池架，电池架battery_rack的index等于N-1
        connection_map中元素如果为小于0的负整数N，表示该模块连接到站外第N号充电终端，充电终端pile的index等于-1*N-1
        connection_map中元素如果为0，表示该模块没有连接到任何充电设备
        例： connection_map[0] = 1 第0号模块连接到0号电池架
        例： connection_map[1] = -2 第1号模块连接到1号充电终端
        例： connection_map[2] = 0 第2号模块无任何连接，不输出

        max current for PSC charge pile = 650 A
        '''

        # ======================================================================================
        # ================= Part 0: Exception case -> No Power Cabinet =========================
        # ======================================================================================
        if self.power_cabinet is None: #如果这个电池仓没有功率柜
            if(self.station_type != "GEN3_600"):
                logger.debug('no power cabinet connected')
            return
        
        # ======================================================================================
        # ================= Part 1: Arrangement power modules to PSS and charge piles ==========
        # ======================================================================================
        for i in range(len(self.connection_map)):
            # case 1: check the Battery in Swap Rack
            if self.connection_map[i] > 0:
                '''
                如果当前模块分配到站内电池架
                在以下几种情况下：
                1. 电池架上没有电池 - 释放模块，同时将Rack设定为remove_battery状态
                2. 电池已经充满
                3. 电池plug已经被拔掉 - 释放模块，同时将rack设定为plug_out状态
                通过将connection_map相应位置置零的方式释放模块
                '''
                rack_id = self.connection_map[i] - 1
                if isinstance(self.battery_rack_list[rack_id].battery, Battery): #如果相应电池存在
                    # for event 2 and 3
                    if self.battery_rack_list[rack_id].battery.soc >= self.select_soc or self.battery_rack_list[rack_id].plug == 0:
                        self.battery_rack_list[rack_id].plug_out()
                        self.connection_map[i] = 0
                else:
                    # for event 1
                    self.connection_map[i] = 0
                    self.battery_rack_list[rack_id].remove_battery()

            # case 2: PSC charge piles
            if self.connection_map[i] < 0:
                '''
                如果当前模块分配到充电桩
                在以下几种条件按下：
                1. 充电桩没有连接车辆电池 - 释放充电模块，充电桩vehicle_leave
                2. 车辆电池SOC已经达到设定值 target_soc - 释放充电模块，充电桩stop_charge
                3. 车辆停止充电 pile.status = "connected" - 释放充电模块，充电桩stop_charge
                '''
                if self.charge_pile_list is not None:
                    # recalculate the charge pile id
                    pile_id = -1 * self.connection_map[i] - 1

                    if isinstance(self.charge_pile_list[pile_id].vehicle_battery, Battery): #如果相应电池存在
                        # for case 2 and 3
                        if self.charge_pile_list[pile_id].vehicle_battery.soc >= self.target_soc or self.charge_pile_list[pile_id].status == "connected":
                            self.connection_map[i] = 0
                            self.charge_pile_list[pile_id].stop_charge()    
                    else:
                        # for case 1
                        self.connection_map[i] = 0      
                        self.charge_pile_list[pile_id].vehicle_leave()       
                else:
                    logger.error('do not have charge pile list')
        
        # ======================================================================================
        # ================= Part 2: Power distribution and optimization ========================
        # ======================================================================================        

        #重新检查换电站功率分配，是否维持两个模块同时输出
        for i in range(len(self.battery_rack_list)):
            if self.connection_map.count(i + 1) > 1:                                        # check if one item connect with more than one power module
                rack_battery = self.battery_rack_list[i].battery
                module_num = self.module_number_check(rack_battery, current_limit = 250)    #换电站内电流最大限制为250
                if module_num < 2:                                                          #如果一个模块就可以支持充电
                    if (i % 2) == 0:                                                        #如果是0/2/4..号电池架
                        if i < len(self.battery_rack_list) - 1:                             #保护 i + 1 index 不溢出
                            self.connection_map[i + 1] = 0                                  # release the residual power module
                    else:
                        self.connection_map[i - 1] = 0

        #优化外部充电桩充电功率
        if self.charge_pile_list is not None:
            for pile in self.charge_pile_list:
                # if exists battery connected to PSC
                if isinstance(pile.vehicle_battery, Battery):
                    if pile.vehicle_battery.soc >= self.target_soc:                                     #如果已经充至指定soc，车辆离开
                        self.vehicle_leave(pile.id)                                                     #电池断电，车辆离开
                    if pile.status == "charging":                                                       #如果还在充电，优化一下充电功率
                        self.connect_charge_pile(pile)                                                  #这里有一个优先级的问题。暂时未能解决
                    if pile.status == "connected" and self.connection_map.count(-1 * pile.id - 1) == 0: #没有在充电，而且没有分配模块
                        self.connect_charge_pile(pile)                                                  #将充电终端通过connect_map连接到模块上      

        #根据换电站仓位功率需求分配冗余的充电模块
        for i in range(len(self.battery_rack_list)):
            # Battery exists & battery soc < target soc & power module pluged
            if isinstance(self.battery_rack_list[i].battery, Battery) and self.battery_rack_list[i].battery.soc < self.select_soc and self.battery_rack_list[i].plug == 1:
                rack_battery = self.battery_rack_list[i].battery
                module_num = self.module_number_check(rack_battery, current_limit = 250)
                # 如果这个模块被外部充电桩占用，而且对象连接充电模块数大于1，则不做处理
                if self.connection_map[i] < 0 and self.connection_map.count(self.connection_map[i]) > 1: 
                    pass
                else:
                    # 如果模块未被外部充电桩占用，则首先保证电池仓内没有充满的且连接器插上的电池可以被充电
                    self.connection_map[i] = i + 1 
                
                # # 强制将外部充电桩的功率分配回站内
                # if self.charge_power_redist_trigger == True: 
                #     self.connection_map[i] = i + 1
                
                #如果可以被相邻的充电模块充电,或者这个模块被外部占用
                if module_num > 1 or self.connection_map[i] != i + 1: 
                    if (i % 2) == 0: 
                        if i < len(self.battery_rack_list) - 1: #保护i + 1 index 不溢出
                            if self.connection_map[i + 1] == 0:
                                self.connection_map[i + 1] = i + 1
                    else:
                        if self.connection_map[i - 1] == 0:
                            self.connection_map[i - 1] = i + 1

        # ======================================================================================
        # ================= Part 3: Restart the power distribution and charging ================
        # ======================================================================================

        self.power_cabinet.config_module(self.connection_map)
        self.stop_charge_all()
        for equipment_id in self.connection_map:
            if equipment_id > 0: #如果是电池内部的equipment
                self.start_charge(equipment_id - 1)
            if equipment_id < 0: #如果是外部充电桩的equipment
                self.start_charge(equipment_id)

    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def power_distribution_grid_interaction(self):
        '''
        stop the charging behaviour of the swap rack;
        reconnect the connection map to the batterries in the swap rack, this function is
        used for grid interaction, prepare for batteries discharge behaviour. 
        '''
        # process 1: check cabinet
        if self.power_cabinet is None:                          # 如果这个电池仓没有功率柜
            if(self.station_type != "GEN3_600"):
                logger.debug('no power cabinet connected')
            return
        # process 2: rearrange the connection map
        for i in range(len(self.connection_map)):
            if self.battery_rack_list[i].battery is not None:       # the batteries may not full loaded
                self.connection_map[i] = i + 1                      # reconnect the batteries in the rack
            else:
                self.connection_map[i] = 0
        self.power_cabinet.config_module(self.connection_map)
        self.stop_charge_all()
        for equipment_id in self.connection_map:
            if equipment_id > 0:                                # 如果是电池内部的equipment
                self.start_discharge(equipment_id - 1)
        return

    def do_charge(self, t_timer:int, interval = 1):
        '''
        excute the charging beheviours
        '''
        charge_complete=[]
        for i in range(len(self.connection_map)):
            equipment_id = self.connection_map[i]
            if charge_complete.count(equipment_id) == 0: # current equipment not counted in charge complet list
                charger_array=[]
                for j in range(len(self.connection_map)):
                    if equipment_id == self.connection_map[j]:
                        charger_array.append(j) # append connecting module index
                
                # for battery in PSS
                if equipment_id > 0:
                    rack_id = equipment_id - 1
                    charge_battery = self.battery_rack_list[rack_id].battery
                    module_num = len(charger_array)
                    charge_battery.request_power(250)
                    charger_current = charge_battery.current_command / module_num
                    total_current = 0
                    for t in charger_array:
                        self.power_cabinet.module_list[t].output_power(charger_current, charge_battery.battery_voltage)
                        total_current += self.power_cabinet.module_list[t].output_current
                    charge_battery.battery_charge(total_current, t_timer, interval)                      
                    charge_complete.append(equipment_id)

                # for battery on charge piles
                if equipment_id < 0:
                    pile_id = equipment_id * -1 - 1
                    charge_battery = self.charge_pile_list[pile_id].vehicle_battery
                    module_num = len(charger_array)
                    charge_battery.request_power(self.charge_pile_list[pile_id].max_current)
                    charger_current = charge_battery.current_command / module_num
                    total_current = 0
                    for t in charger_array:
                        self.power_cabinet.module_list[t].output_power(charger_current,charge_battery.battery_voltage)
                        total_current = total_current + self.power_cabinet.module_list[t].output_current
                    charge_battery.battery_charge(total_current,t_timer,interval)                      
                    charge_complete.append(equipment_id)
    
    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def do_grid_discharge(self, t_timer:int, interval = 1):
        '''
        discharge the batteries from swap rack, send power back to grid
        '''
        discharge_complete=[]
        for i in range(len(self.connection_map)):
            equipment_id = self.connection_map[i]
            if discharge_complete.count(equipment_id) == 0:        # current equipment not counted in charge complet list
                discharger_array=[]
                for j in range(len(self.connection_map)):
                    if equipment_id == self.connection_map[j]:
                        discharger_array.append(j)                 # append connecting module index
        
                if equipment_id > 0:
                    rack_id = equipment_id - 1
                    if rack_id < len(self.battery_rack_list):
                        discharge_battery = self.battery_rack_list[rack_id].battery
                    module_num = len(discharger_array)
                    discharge_battery.request_power(250)
                    charger_current = discharge_battery.current_command / module_num
                    total_current = 0
                    for t in discharger_array:
                        self.power_cabinet.module_list[t].grid_interactive_output_power(charger_current, discharge_battery.battery_voltage)
                        total_current += self.power_cabinet.module_list[t].output_current
                    discharge_battery.battery_discharge(total_current, t_timer, interval)                      
                    discharge_complete.append(equipment_id)

    def get_power_sr(self):
        if self.power_cabinet is None:
            return 0
        return self.power_cabinet.get_power_pc()

######################################################################
####################### Class: SwapStation ###########################
######################################################################
class SwapStation:
    '''
    换电站2.0，最大电池13块，外接充电桩0，最大充电输入功率530kW，最大可分配充电单元13个
    换电站3.0-10-20，最大可容纳电池20块，最多外接充电桩4，最大充电输入功率600kW，最大可分配充电单元10个
    换电站3.0-20-20，最大可容纳电池20块，最多外接充电桩8，最大充电输入功率1200kW，最大可分配充电单元20个

    换电站3.0有两个版本，
    版本1 PUS A：20个电池仓可存储20块电池，其中只有10个电池可以充电，剩余的就是仓储
    版本2 PUS B：20个电池仓可存储20块电池，20个电池都可以充电

    功率分配原则为，偶数仓0/2/4/6/8/10/12可以分配到N以及N+1的功率，奇数仓可以分配到N以及N-1的功率
    对外放电的功率分配原则为：0-9号（10块电池）功率可以向0-3号外部充电终端分配，10-19号（10块电池）功率可以向4-7号外部充电终端分配
    '''

    def __init__(self, param):
        '''
        self.GEN2_530kW = {"station_type":"GEN2_530","max_battery_number": 13,"max_charge_terminal":0,"max_power":520,"max_charger_number":13}
        self.GEN3_600kW = {"station_type":"GEN3_600","max_battery_number": 20,"max_charge_terminal":4,"max_power":600,"max_charger_number":10}
        self.GEN3_1200kW = {"station_type":"GEN3_1200","max_battery_number": 20,"max_charge_terminal":8,"max_power":1200,"max_charger_number":20}
        self.FY_TypeA = {"station_type":"FY_TypeA","max_battery_number": 15,"max_charge_terminal":0,"max_power":600,"max_charger_number":15}
        self.FY_TypeB = {"station_type":"FY_TypeB","max_battery_number": 21,"max_charge_terminal":0,"max_power":630,"max_charger_number":21}
        self.FY_TypeC = {"station_type":"FY_TypeC","max_battery_number": 33,"max_charge_terminal":0,"max_power":1320,"max_charger_number":33}
        self.FY_TypeD = {"station_type":"FY_TypeD","max_battery_number": 10,"max_charge_terminal":0,"max_power":600,"max_charger_number":10}
        self.User_Defined = {"station_type":"User_Defined","max_battery_number": 0,"max_charge_terminal":0,"max_power":0,"max_charger_number":0,
                             "power_module_type":None}
        '''
        self.pss_type_dict = param["station_type"]                                      # get the PSS data dict
        self.max_battery_number = self.pss_type_dict["max_battery_number"]              # num of battery in the station
        self.max_charge_terminal = self.pss_type_dict["max_charge_terminal"]            # num of charge piles
        self.max_power = self.pss_type_dict["max_power"]                                # max allowable chargeable power upper limit
        self.max_charger_num = self.pss_type_dict["max_charger_number"]                 # num of power modules
        self.station_type = self.pss_type_dict["station_type"]                          # type of PSS (string)
        self.psc_num = param["psc_num"]                                                 # num of psc connected with pss
        self.power = 0                                                                  # save the real time power cosumption 
        self.status = "free"                                                            # 换电平台状态，free = 没有换电操作，in_use = 换电中，switch = 电池执行仓位交换中
        self.full_battery = 0                                                           # 满电电池数量
        self.swap_timer = 0                                                             # 用来为换电过程计时。这个乘以sim仿真周期就是换电进行多少时间
        self.residual_power = self.max_power - self.power                               # calculate the residual power
        self.swap_rack_list = []                                                        # empty list save for battery swap rack objects
        self.buff_rack = None
        self.battery_num = 0                                                            # !!! battery_num has calculation error !!!!
        self.enable_me_switch = param["enable_me_switch"]
        self.power_history = []                                                         # 记录充电功率的历史，记录在power_history队列中，记录结构为[timer, power]
        self.target_soc = param["target_soc"]                                           # for the PSC charge pile target soc
        self.select_soc = param["select_soc"]                                           # for the PSS battery charge target upper limit, will be select to swap when reaches this soc
        self.power_dist_option = param["power_dist_option"]                             # trigger of PSC or PSS power priority
        if param["grid_interaction_idx"] != -1:                                         # define the grid interaction start time stamp (if idx != -1)
            self.grid_interaction_timeStamp = int(param["grid_interaction_idx"] * 3600 / param["sim_interval"])
            self.grid_interaction_counter = 0                                           # define the how many times the grid interaction will perform
            self.grid_interaction_time_upper_limit = int((param["grid_interaction_idx"] + 1) * 3600 / param["sim_interval"]) # define the upper limit of grid interaction time interval
        else:
            self.grid_interaction_timeStamp = None
            self.grid_interaction_counter = 1
            self.grid_interaction_time_upper_limit = None
        self.trigger = []                                                               # trigger for grid interaction, once time for discharge, this will be 1 otherwise 0, same length as sim_ticks
        self.interaction_num = param["interaction_num"]                                 # number of interaction will be performed
        
        # Set up the station variations
        if self.station_type == "GEN2_530":
            self.swap_period = int(param["swap_time"] * 60) 
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=0, id=0))
            self.module_power = 40

        if self.station_type == "GEN3_600":
            self.swap_period = int(param["swap_time"] * 60) 
            self.swap_rack_list.append(Swap_Rack(param=param, station_type="GEN3_1200", psc_num=self.psc_num, id=0))
            self.swap_rack_list.append(Swap_Rack(param=param, station_type="GEN3_600", psc_num=0, id=1))         
            self.module_power = 60    

        if self.station_type == "GEN3_1200":
            self.swap_period = int(param["swap_time"] * 60)
            psc_num_1 = int(self.psc_num / 2) # num of PSC arranged to first cabinet
            psc_num_2 = int(self.psc_num - psc_num_1)  # num of PSC arranged to second cabinet        
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=psc_num_1, id=0))
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=psc_num_2, id=1))
            self.module_power = 60

        if self.station_type == "FY_TypeA":
            self.swap_period = int(param["swap_time"] * 60) #FY换电站换电时间为180秒，3min
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=0, id=0))
            self.module_power = 40

        if self.station_type == "FY_TypeB":
            self.swap_period = int(param["swap_time"] * 60) #FY换电站换电时间为180秒，3min
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=0, id=0))
            self.module_power = 40

        if self.station_type == "FY_TypeC":
            self.swap_period = int(param["swap_time"] * 60) #FY换电站换电时间为180秒，3min
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=0, id=0))
            self.module_power = 40

        if self.station_type == "FY_TypeD":
            self.swap_period = int(param["swap_time"] * 60) #FY换电站换电时间为180秒，3min
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=0, id=0))
            self.module_power = 40

        if self.station_type == "User_Defined":
            self.swap_period = int(param["swap_time"] * 60) 
            self.swap_rack_list.append(Swap_Rack(param=param, station_type=self.station_type, psc_num=int(self.psc_num), id=0))
            self.module_power = self.pss_type_dict["power_module_type"]["max_power"]

        self.set_temperature(rack_temperature = param["swap_rack_temperature"], env_temperature = param["swap_rack_temperature"]) #缺省温度25度

    def set_temperature(self, rack_temperature = 25, env_temperature = 25):
        '''
        set up environment temperature and rack temperature
        '''
        for swap_rack in self.swap_rack_list:
           if isinstance(swap_rack, Swap_Rack):
               swap_rack.set_sr_temperature(rack_temperature, env_temperature)
               self.rack_temperature = swap_rack.rack_temperature
               self.env_temperature = swap_rack.external_temperature

    def cal_battery_num(self):
        '''
        calculate batteries number
        '''
        self.battery_num = 0
        for swap_rack in self.swap_rack_list:
            self.battery_num += swap_rack.battery_num
        
    def load_battery_auto(self, battery : Battery):
        '''
        load batteries into rack list
        '''
        if isinstance(battery, Battery):
            for swap_rack in self.swap_rack_list:
                tmp = swap_rack.load_battery(battery)  
                if tmp >= 0:
                    logger.debug("Battery Loaded into SWAP_RACK # %d, Battery Rack # %d",swap_rack.id, tmp)
                    break
            if tmp == -1:
                print("No space to load battery")
        else:
            print("无法处理非法的电池对象")
        self.cal_battery_num()

    def load_battery_target(self, battery : Battery, swap_rack_id, rack_id):
        '''
        load battery into target rack(rack_id)
        '''
        # if not isinstance(battery,Battery):
        #     return -1
        if battery is None:
            return -1
        if swap_rack_id > len(self.swap_rack_list) - 1 or swap_rack_id < 0:
            return -1
        if rack_id > self.swap_rack_list[swap_rack_id].max_rack_number - 1:
            return -1
        re = self.swap_rack_list[swap_rack_id].load_battery(battery, rack_id)
        self.cal_battery_num()
        return(re)

    def remove_battery_target(self, swap_rack_id, rack_id):
        '''
        remove battery from target rack(rack_id)
        '''
        if swap_rack_id > len(self.swap_rack_list) - 1 or swap_rack_id < 0:
            return -1
        if rack_id > self.swap_rack_list[swap_rack_id].max_rack_number - 1:
            return -1
        self.swap_rack_list[swap_rack_id].unload_battery(rack_id)
        self.cal_battery_num()

    def exchange_battery_target(self, battery : Battery, swap_rack_id, rack_id):
        '''
        remove the old battery in the rack, load new given battery into target rack_id
        '''
        if not isinstance(battery, Battery):
            return -1
        if swap_rack_id > len(self.swap_rack_list) - 1 or swap_rack_id < 0:
            return -1
        if rack_id > self.swap_rack_list[swap_rack_id].max_rack_number - 1:
            return -1        
        self.remove_battery_target(swap_rack_id, rack_id)
        self.load_battery_target(battery, swap_rack_id, rack_id)

    def switch_battery(self, source_swap_rack, source_rack, target_swap_rack, target_rack):
        '''
        switch the two batteries position btw source and target rack
        '''
        if source_swap_rack > len(self.swap_rack_list) - 1 or source_swap_rack < 0:
            return
        if target_swap_rack > len(self.swap_rack_list) - 1 or target_swap_rack < 0:
            return
        if source_rack > self.swap_rack_list[source_swap_rack].max_rack_number - 1:
            return           
        if target_rack > self.swap_rack_list[target_swap_rack].max_rack_number - 1:
            return                     
        if not isinstance(self.swap_rack_list[source_swap_rack].battery_rack_list[source_rack].battery, Battery):
            return
        if not isinstance(self.swap_rack_list[target_swap_rack].battery_rack_list[target_rack].battery, Battery):
            return
        # self.swap_rack_list[source_swap_rack].battery_rack_list[source_rack].stop_charge()
        # self.swap_rack_list[target_swap_rack].battery_rack_list[target_rack].stop_charge()
        self.swap_rack_list[source_swap_rack].stop_charge(source_rack)
        self.swap_rack_list[target_swap_rack].stop_charge(target_rack)
        
        temp_battery = self.swap_rack_list[source_swap_rack].battery_rack_list[source_rack].battery
        self.swap_rack_list[source_swap_rack].battery_rack_list[source_rack].battery = self.swap_rack_list[target_swap_rack].battery_rack_list[target_rack].battery
        self.swap_rack_list[target_swap_rack].battery_rack_list[target_rack].battery = temp_battery
        
        # self.swap_rack_list[source_swap_rack].battery_rack_list[source_rack].start_charge()
        # self.swap_rack_list[target_swap_rack].battery_rack_list[target_rack].start_charge()
        self.swap_rack_list[source_swap_rack].start_charge(source_rack)
        self.swap_rack_list[target_swap_rack].start_charge(target_rack)
        self.status = "switch"
        self.switch_timer = 0
        return

    def select_battery_rack(self, vehicle_battery : Battery, swap_target_soc):
        '''
        自动选择电池规则:
            1. 电池种类需要一致 vehicle_battery.batterytype -> 此限制被暂时解除
            2. 站内电池达到 soc > swap_target_soc
            3. 根据仓位充电空闲情况优化选择
        返回值: None or corresponding rack object
        '''
        if not isinstance(vehicle_battery, Battery):
            return
        for swap_rack in self.swap_rack_list:
            for rack in swap_rack.battery_rack_list:
                if isinstance(rack.battery, Battery):
                    if rack.battery.soc >= swap_target_soc:
                    # if (rack.battery.batterytype == vehicle_battery.batterytype) and (rack.battery.soc >= swap_target_soc):
                        return rack

    def start_swap(self, vehicle_battery : Battery, swap_targetsoc) -> bool:
        '''
        start swapping behaviour, detect whether suitable battery exists
        Return value: True or False
        '''
        if self.status != "free":
            return False
        
        if isinstance(vehicle_battery, Battery): #如果是合法电池
            self.buff_rack = self.select_battery_rack(vehicle_battery, swap_targetsoc)
            self.vehicle_battery = vehicle_battery
            if not isinstance(self.buff_rack, Battery_Rack):
                # logger.debug('can not find proper battery')
                return False
            # logger.debug("start swap timer start --- ")

            # init the swap timer, switch the status to "in use"
            self.swap_timer = 0
            self.status = "in_use"
            return True
        else:
            logger.error("illegel battery")
            return False
    
    ################################################################################
    ######################## Modified by Y.Meng ####################################
    ################################################################################
    def do_swap(self, current_user, t_timer, interval=1):
        '''
        swapping process
        grid interaction trigger will be calculated in form of list, when the counter
        not reaches max interaction num nor extend the time interval, it will be activated
        when the swap user utilizes the PSS, otherwise will this trigger == 0, we use trigger
        to detect whether we perform the grid interaction or not
        
        return value: True or False
        
        '''
        # case: Battery rack in switch operation
        if self.status == "switch":
            self.switch_timer += 1
            if self.switch_timer * interval >= 30:
                self.status = "free"
        
        # case: detect whether the time extend the grid interaction interval, if so the counter = max performed number
        if self.grid_interaction_timeStamp != None and self.grid_interaction_time_upper_limit != None:
            if t_timer > self.grid_interaction_time_upper_limit:
                self.grid_interaction_counter = self.interaction_num
        
        # case: swap platform in use status
        if self.status == "in_use":

            # establish the grid interaction trigger
            if self.grid_interaction_timeStamp != None:                         # condition1: the grid interaction activated
                if t_timer >= self.grid_interaction_timeStamp:                  # condition2: timestamp reaches into the grid interaction time interval
                    if self.grid_interaction_counter < self.interaction_num:    # condition3: the grid interaction times not extend max allowable number
                        self.trigger.append(1)                                  # if all conditions fullfilled, trigger activated as 1 otherwise 0
                    else:
                        self.trigger.append(0)
                else:
                    self.trigger.append(0)
            else:
                self.trigger.append(0)
            
            # swap time iteration
            self.swap_timer += 1

            if self.swap_timer * interval >= self.swap_period: #换电完成时的动作，交换车上和电池仓里的电池
                # load the vehicle battery, give the stored battery away, start charging new loaded battery
                self.buff_rack.stop_charge()
                temp_battery = self.vehicle_battery
                self.vehicle_battery = self.buff_rack.battery # give buff_rack battery to user
                self.buff_rack.battery = temp_battery         # load vehicle battery into buff_rack
                self.buff_rack.start_charge()
                if current_user is not None:
                    current_user.battery = self.vehicle_battery
                
                # init the swap setup
                self.vehicle_battery = None                     #清空车辆电池缓存
                # total_time = self.swap_timer * interval
                self.swap_timer = 0                             #清空换电时间计时器
                self.status = "free"                            #将换电站状态设置为空闲
                
                # after first swap user (that after certain time stamp comes) finished service, counter up tp 1
                # if counter > 0 then the grid service deactivated.
                if self.grid_interaction_timeStamp != None:
                    if t_timer >= self.grid_interaction_timeStamp:
                        if self.grid_interaction_counter < self.interaction_num:
                            self.grid_interaction_counter += 1
                        else:
                            self.grid_interaction_counter = self.interaction_num
                
                return True
        
        else: #当没有换电动作的时候，做一下电池仓电池位置的调整
            self.trigger.append(0)
            if self.status != "switch":
                if (self.enable_me_switch > 0):
                    self.switch_in_rack()
                    if len(self.swap_rack_list) > 1 and self.enable_me_switch > 1:
                        self.switch_two_racks()
                        # logger.error('Swap between different swap racks -- Have not implemented')
                        pass
        
        return False
    
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
    def do_charge(self, timer, interval=1):
        self.power = 0
        for swap_rack in self.swap_rack_list:

            if self.power_dist_option == "PSS preferred":        
                swap_rack.power_distribution_pss_preferred()
            else:
                swap_rack.power_distribution_psc_preferred()  
             
            swap_rack.do_charge(timer, interval)
            self.power += swap_rack.get_power_sr()
        self.power_history.append([timer, self.power])
    
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
    def do_grid_interaction_discharge(self, timer, interval=1):
        '''
        perform the grid interaction discharge behaviours while a swap service is executing.
        '''
        self.power = 0
        for swap_rack in self.swap_rack_list:
            swap_rack.power_distribution_grid_interaction()
            swap_rack.do_grid_discharge(timer, interval)
            self.power += swap_rack.get_power_sr()
        self.power_history.append([timer, self.power])
    
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
    def init_charge(self):
        for swap_rack in self.swap_rack_list:
            swap_rack.select_soc = self.select_soc
            swap_rack.target_soc = self.target_soc
            if swap_rack.power_cabinet is not None:
                # logger.debug(swap_rack.power_cabinet)
                swap_rack.start_charge_all()
                if self.power_dist_option == "PSS preferred":        
                    swap_rack.power_distribution_pss_preferred()
                else:
                    swap_rack.power_distribution_psc_preferred()    

    def vehicle_charge(self, vb : Battery, pile_id = -1):
        # pile id = -1表明自动连接到空闲充电桩，
        # 返回-1为没有连接成功，返回0-N为连接到的充电桩id
        # 对于外接超过4根的充电桩，或者两个以上swap rack都可以连接充电桩的场景，pile_id = swap_rack_id * swap_rack_pile_number + pile_id
        if self.max_charge_terminal == 0:
            logger.info('No pile defined in this type of swap station')
            return -1
        if pile_id == -1:
            for sr in self.swap_rack_list:
                if sr.max_pile_number > 0:
                    for j in range(len(sr.charge_pile_list)):
                        if sr.connect_vehicle(vb, j) == j:
                            # logger.info('battery connected to pile number %d',j)
                            return j
        
            return -1
        #暂时不提供连接到某一个特定充电终端的代码    
          
    def vehicle_stop_charge(self, vehicle_battery : Battery):
        #pile id = -1表明停止所有充电桩充电,暂时不提供
        if self.max_charge_terminal == 0:
            logger.info('No pile defined in this type of swap station')
            return -1
        
        for sr in self.swap_rack_list:                          # check each swap rack
            if sr.max_pile_number > 0:
                for j in range(len(sr.charge_pile_list)):
                    connected_battery = sr.charge_pile_list[j].vehicle_battery
                    if connected_battery == vehicle_battery:
                        sr.charge_pile_list[j].vehicle_leave()
                        return j
        return -1

    def switch_in_rack(self):
        '''
        rearrange the position of battery in the PSS according to the power distribution
        '''
        for sr in self.swap_rack_list:                      # 遍历所有电池仓(PSS 3.0 有两个电池仓，每个电池仓10个电池架位)
            if sr.power_cabinet is not None:                # 如果电池仓配备了充电能力
                rack_n = len(sr.battery_rack_list)
                for i in range(rack_n):
                    if (i % 2) == 0:                        # at even number index of batteries
                        if sr.battery_rack_list[i].status == "charging": # battery status
                            if i + 1 < rack_n:
                                if sr.battery_rack_list[i + 1].status == "charging":
                                    for j in range(rack_n):
                                        if (j % 2) == 0 and j < rack_n - 1:
                                            if sr.battery_rack_list[j].status != "charging" and sr.battery_rack_list[j + 1].status != "charging":
                                                self.switch_battery(self.swap_rack_list.index(sr), i, self.swap_rack_list.index(sr), j)
                                                break
                                        if (j % 2) == 0 and j == rack_n - 1:
                                            if sr.battery_rack_list[j].status != "charging":
                                                self.switch_battery(self.swap_rack_list.index(sr), i, self.swap_rack_list.index(sr), j)
                                                break

    def switch_two_racks(self):
        '''
        For PSS 3.0 PUS A 600kW arrange the battery position btw rack with 
        charging ability and rack without charging ability
        '''
        # Case 1: for the case with only one swap_rack object (PSS 2.0)
        if len(self.swap_rack_list) <= 1:
            return
        
        # Case 2: 600kW station
        if self.station_type == "GEN3_600":
            sr_b = self.swap_rack_list[1]        # rack unable to be charged
            sr_c = self.swap_rack_list[0]        # rack able to be charged
            rack_n = len(sr_b.battery_rack_list)
            for i in range(rack_n):
                # visit storage rack(unable to charge) to find a unfullcharged battery
                if sr_b.battery_rack_list[i].battery.soc < sr_b.target_soc:
                    # once find a unfull battery, then visit batteries at chargeable rack
                    for j in range(rack_n):
                        # find a full charged battery at chargeable rack
                        if sr_c.battery_rack_list[j].battery.soc >= sr_c.target_soc:
                            # switch 2 batteries
                            self.switch_battery(1,i,0,j)
                            break
                        # or find a empty position at chargeable rack
                        if sr_c.battery_rack_list[j].battery is None:
                            sr_c.battery_rack_list[j].battery = sr_b.battery_rack_list[i].battery
                            sr_b.battery_rack_list[i].battery = None              
                            break
        
        # Case 3: 1200kW station
        if self.station_type == "GEN3_1200":
            rack_n = len(self.swap_rack_list[0].battery_rack_list)
            for sr in self.swap_rack_list: #遍历所有电池仓
                for i in range(rack_n):
                    if (i % 2) == 0: # even number of rack
                        if sr.battery_rack_list[i].status == "charging":
                            if i + 1 < rack_n:
                                if sr.battery_rack_list[i+1].status == "charging":
                                    find_flag = 0
                                    for sr_t in self.swap_rack_list:
                                        for j in range(rack_n):
                                            if (j % 2) == 0 and j < rack_n - 1:
                                                if sr_t.battery_rack_list[j].status != "charging" and sr_t.battery_rack_list[j+1].status != "charging":
                                                    self.switch_battery(self.swap_rack_list.index(sr), i, self.swap_rack_list.index(sr_t), j)
                                                    find_flag = 1
                                                    break
                                            if (j % 2) == 0 and j == rack_n - 1:
                                                if sr_t.battery_rack_list[j].status != "charging":
                                                    self.switch_battery(self.swap_rack_list.index(sr), i, self.swap_rack_list.index(sr_t), j)
                                                    find_flag = 1
                                                    break   
                                    if find_flag == 1:
                                        break 
