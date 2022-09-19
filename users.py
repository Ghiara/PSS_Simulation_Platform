# -*- coding: UTF-8 -*-

###########################
###### Update logger ######
###########################
# 2022.09.09 User Defined PSS avaiable                      by Y.Meng
# 2022.09.09 FY 4 Variation updated into model              by Y.Meng
# 2022.08.26 update the fixed value specification           by Y.Meng
# 2022.08.18 adding labeling for Non NIO user               by Y.Meng
# 2022.07.30 markov preference algorithms                   by Y.Meng
# 2022.07.18 create user queue random & statistics          by Y.Meng
# 2022.07.07 commit fullfilling & coding review             by Y.Meng
# 2022.07.01 init generation                                by C.Yang
###########################
import os
import logging
import random
import string
import time
import numpy as np
import pandas as pd
import swap
from swap import Battery
import global_param

# set up the global param
GC = global_param.Global_Constant()
# set up logger
logger = logging.getLogger('main.users')
data_logger = logging.getLogger('data.users')


class User():

    def __init__(self, user_label) -> None:

        self.preference_distribution = {"charge":30,"swap":70,"leave":0} # by dafult setup of the user preference
        self.battery = None                 # save the battery instance object
        self.user_type = user_label         # user_type define the classification of NIO & Non-NIO user, "nio" indicates user belong to nio group, "non-nio" means user belongs to third party
        self.charge_preference = "swap"     # "swap":换电, "charge":充电, "leave":离开
        self.arrival_time = -1              #设置一个计数器，记录用户到达时间，精确到仿真开始后多少秒到达,用于产生用户队列，-1表示不放入队列
        self.max_wait_number = 20           #设置一个最长等待时间，如果在这个时间内没有开始换电，用户会离开队列,单位=排队人数
        self.max_charge_time = -1           #设置一个最长充电时间参数，从充电开始到充电结束时间，超过这个时间用户会停止充电离开
        self.min_charge_soc = 1             #设置用户愿意充到的最小soc状态，超过则离开，缺省为100（充满）
        self.power_consumption = 20         #设置用户百公里电耗
        self.min_milage = -1                #设置用户最小满意的充电里程，根据powr_cosumption可以算出最小需要充多少电，当min_milage不等于-1的时候，计算min_charge_soc和min_milage中更小的一个
        self.status = "waiting"             #"charging"正在充电中，占用一个充电终端，"swaping" 正在换电中，占用一个换电平台
        self.timer = 0                      #记录用户在某一个状态的时间,单位秒，以一个仿真周期为基础计算增量
        self.sequence = -1                  #记录用户在用户队列里的位置 也就是用户到来的时间
        self.swap_start_time = -1           #记录用户换电开始时间
        self.swap_complete_time = -1        #记录用户换电结束时间
        self.swap_service_time = -1         #等于swap_complete_time-sequence
        self.charge_connect_time = -1       #连接到充电桩的时间,但并不一定是充电开始时间
        self.id = -1                        #这是用于记录用户在一天的仿真时序里到达的时间
        self.connect_pile = None
        self.temp = 25

    def charge_service_time(self, mode = 1):   # mode = 1 返回充电加排队时间; mode = 0 只返回充电时间
        if mode == 1:
            # service time = charge time + waiting time
            tt = abs(self.battery.charge_start_time + len(self.battery.charge_history) - self.sequence)
        else:
            # mode == 0
            # only charge time
            tt = len(self.battery.charge_history)
        return tt

    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################    
    def swap_waiting_time(self):
        '''
        返回用户换电队列的排队时间（开始换电时间点 - 进入队列时间点）
        '''
        if self.charge_preference == "swap" and self.sequence != -1 and self.swap_start_time != -1:
            swap_waiting_t = self.swap_start_time - self.sequence
        else:
            swap_waiting_t == None
        return swap_waiting_t
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
    def charge_waiting_time(self):
        '''
        返回用户从进入排队队列到连接到充电桩的时间段
        '''
        if self.charge_preference == "charge" and self.sequence != -1 and self.charge_connect_time != -1:
            wait_time = self.charge_connect_time - self.sequence
        else:
            wait_time = None
        return wait_time
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
    def markov_preference(self, queue_length):
        '''
        Rearrange the user selection preference based on markov chain
        --> Modify: input temp, soc state, queue length
        '''
        x_state = ["swap", "charge", "leave"]
        x_prior = np.array([0.7, 0.25, 0.05],dtype=np.float64)
        Transition_matrix = np.array([[0.8, 0.1, 0.1],
                                      [0.1, 0.1, 0.8],
                                      [0.0, 0.0, 1.0]], dtype=np.float64)
        Observation_matrix = self.O_matrix_generation(self.temp, self.battery.soc, queue_length)
        x_1 = Observation_matrix.dot(Transition_matrix.dot(x_prior))    # one step forward procedure
        x_1 = x_1 / sum(x_1)
        x_1 = [round(s,2) for s in x_1]                                 # estimate probability
        ulist = [1, 2, 3]
        numb = get_number_by_pro(number_list = ulist, pro_list = x_1)
        
        self.charge_preference = x_state[int(numb)]                     # save as string
        return x_state[int(numb)]
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
    def O_matrix_generation(self, temp, soc_state, queue_len):

        if (temp>=5 and temp<=26) and soc_state>=0.4 and queue_len<=12:
            O_matrix = np.array([[0.5, 0.0, 0.0],[0.0, 0.4, 0.0],[0.0, 0.0, 0.1]],dtype=np.float64)
            return O_matrix
        
        if (temp<5 or temp>26) and soc_state>=0.4 and queue_len<=12:
            O_matrix = np.array([[0.7, 0.0, 0.0],[0.0, 0.2, 0.0],[0.0, 0.0, 0.1]],dtype=np.float64)
            return O_matrix

        if (temp>=5 and temp<=26) and soc_state<0.4 and queue_len<=12:
            O_matrix = np.array([[0.9, 0.0, 0.0],[0.0, 0.1, 0.0],[0.0, 0.0, 0.0]],dtype=np.float64)
            return O_matrix

        if (temp>=5 and temp<=26) and soc_state>=0.4 and queue_len>12:
            O_matrix = np.array([[0.6, 0.0, 0.0],[0.0, 0.3, 0.0],[0.0, 0.0, 0.1]],dtype=np.float64)
            return O_matrix

        if (temp<5 or temp>26) and soc_state<0.4 and queue_len<=12:
            O_matrix = np.array([[0.8, 0.0, 0.0],[0.0, 0.1, 0.0],[0.0, 0.0, 0.1]],dtype=np.float64)
            return O_matrix

        if (temp<5 or temp>26) and soc_state>=0.4 and queue_len>12:
            O_matrix = np.array([[0.3, 0.0, 0.0],[0.0, 0.3, 0.0],[0.0, 0.0, 0.4]],dtype=np.float64)
            return O_matrix

        if (temp>=5 and temp<=26) and soc_state<0.4 and queue_len>12:
            O_matrix = np.array([[0.6, 0.0, 0.0],[0.0, 0.2, 0.0],[0.0, 0.0, 0.2]],dtype=np.float64)
            return O_matrix

        if (temp<5 or temp>26) and soc_state<0.4 and queue_len>12:
            O_matrix = np.array([[0.7, 0.0, 0.0],[0.0, 0.1, 0.0],[0.0, 0.0, 0.2]],dtype=np.float64)
            return O_matrix
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
    def full_swap_preference(self):
        self.charge_preference = "swap"
        return
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
    def full_charge_preference(self):
        self.charge_preference = "charge"
        return
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
    def fixed_preference(self, swap_ratio:int):
        '''
        Rearrange the user selection preference
        '''
        # self.preference_distribution = pref_dist # reset the probability of user selection
        if swap_ratio == -1:
            logger.error("this preference mode is not selected")
            return
        else:
            self.preference_distribution["swap"] = swap_ratio
            self.preference_distribution["charge"] = 100 - swap_ratio
            self.preference_distribution["leave"] = 0
        
        tt = self.preference_distribution["charge"] + self.preference_distribution["swap"] + self.preference_distribution["leave"]
        
        if tt != 100:
            logger.error('preference distribution need to sum up to 100 (%d)',tt)
            return 
        pref_c = ["swap", "charge", "leave"]
        
        # ulist = range(1, 5)
        ulist = [1, 2, 3] # 1, 2, 3, 4
        plist = [self.preference_distribution["swap"] / 100, self.preference_distribution["charge"] / 100, 
                self.preference_distribution["leave"] / 100]
        numb = get_number_by_pro(number_list = ulist, pro_list = plist)
        # data_logger.debug(int(numb))
        self.charge_preference = pref_c[int(numb)] # save as string
        return pref_c[int(numb)]
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
    def create_battery(self, battery_config : dict, soc_low_limit = 0.0, soc_up_limit = 1.0, random_soc = 0) -> bool: 
        '''
        Generate the user initial battery with selected generation mode:
        Mode 1 (random_soc = 0): configurate the initial SOC based on real data distribution, namely gamma distribution
        Mode 2 (random_soc = 1): configurate the initial SOC based on real data distribution, but with gaussian distribution (centriod mu and sigma)
        Mode 3 (random_soc = 2): configurate the initial SOC based on uniform distribution
        '''
        # # set up the battery type by ratio in the battery_config dict
        if len(battery_config) ==2:
            ratio = list(battery_config.values())[0] / sum(list(battery_config.values()))
            # set up a flag value that compare with the ratio in order to confirm the battery type
            flag = random.random()
            # Here currently only allows 2 type of battery configuration -> 100 kWh and 75 kWh
            if flag <= ratio:
                # first type of battery
                battery_type = list(battery_config.keys())[0]
            else:
                # second type of battery
                battery_type = list(battery_config.keys())[1]
        else:
            ratio1 = list(battery_config.values())[0] / sum(list(battery_config.values()))
            ratio2 = list(battery_config.values())[0] + list(battery_config.values())[1] / sum(list(battery_config.values()))
            flag = random.random()
            # Here currently only allows 2 type of battery configuration -> 100 kWh and 75 kWh
            if flag <= ratio1:
                # first type of battery
                battery_type = list(battery_config.keys())[0]
            elif flag > ratio1 and flag <= ratio2:
                # second type of battery
                battery_type = list(battery_config.keys())[1]
            else:
                battery_type = list(battery_config.keys())[2]
        
        # check the validity of soc configuration
        if battery_type not in ["70kWh", "75kWh", "100kWh", "FY62kWh", "FY41kWh"]:
            logger.error('invalid battery type %s',battery_type)
            return False
        if soc_up_limit > 1.0:
            logger.debug('invalid battery soc limit: %.2f --> set soc to 1.0',soc_up_limit)
            soc_up_limit = 1.0
        if soc_low_limit < 0.0:
            logger.debug('invalid battery soc limit: %.2f --> set soc to 0.0',soc_low_limit)
            soc_low_limit = 0.0
        
        if random_soc == 0:
            # set up the clients initial soc based on real statistic data -> Gamma distribution
            shape, scale = 3.0, 12.0
            input_soc = random.gammavariate(shape, scale)
            input_soc = round(input_soc/100, 2)

        elif random_soc == 1:
            # set up the clients initial soc based on real statistic data -> Gaussian distribution
            input_soc = random.normalvariate(mu=33.13, sigma=18.71)
            input_soc = round(input_soc/100, 2)
        else:
            # set up the clients initial soc based on Uniform distribution (Not recommend!!!)
            input_soc = random.uniform(soc_low_limit, soc_up_limit)
            input_soc = round(input_soc, 2)
        
        # check the validity of battery initial soc value
        if input_soc > soc_up_limit:
            input_soc = soc_up_limit
        elif input_soc < soc_low_limit:
            input_soc = soc_low_limit
        else:
            pass

        self.battery = Battery(input_soc, battery_type)
        # logger.debug('One %s battery created with soc = %.2f',battery_type,self.battery.soc)
        return True

###########################################################################################
################################### END of Class ##########################################
###########################################################################################



    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
def create_user_queue_random(nio_user_num : int, non_nio_user_num : int): 
    '''
    use the user_random_dist.dat file to generate the user arrive time distribution
    '''
    if nio_user_num <= 0:
        logger.error('should create a user queue larger than 0')
    
    # read the dat file from data folder
    abspath = os.getcwd()
    abspath = os.path.join(abspath,"data")
    file_list = os.listdir(abspath)
    data_name = None
    for item in file_list:
        if item == "user_random_dist.dat":
            data_name = item
            break
    data_file_path = os.path.join(abspath, data_name)

    # pack and sort the nio & non nio user queue 
    nio_user_list = get_user_distribution(data_file_path, nio_user_num)            # return timestamp list of nio user arrive time
    non_nio_user_list = get_user_distribution(data_file_path, non_nio_user_num)    # return timestamp list of non nio user arrive time

    nio_queue, non_nio_queue = label_queue(nio_user_list, non_nio_user_list)
    sorted_queue, sorted_label = sort_queue(nio_queue, non_nio_queue)

    return sorted_queue, sorted_label
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
def create_user_queue_statistical(area : string, non_nio_user_num : int): 
    '''
    Queue generation mode "real data"
    Generate the user input distribution based on real data (saved under "data" folder)
    Input: 
        data file with ending "*.dat", data format: "2020-07-01 00:28:44", which recorded users arrive time within 24 hours
        area: string that indicates which area will be used for simulation, urban or suburb/highway
    Output:
        time stamp list (in sec) that refered to 00:00:00
    '''
    # Prepare the Non NIO user generation file, read the file path
    abspath = os.getcwd()
    abspath = os.path.join(abspath,"data")
    file_list = os.listdir(abspath)
    data_name = None
    for item in file_list:
        if item == "user_random_dist.dat":
            data_name = item
            break
    data_file_path = os.path.join(abspath, data_name)

    # use statistics to generate NIO user arrive time queue
    if area == "urban":
        file_list = GC.user_dist_urban_file_list                        # get the user distribution file name list for urban
    else:
        file_list = GC.user_dist_highway_file_list                      # get the user distribution file name list for highway
    selection_flag = random.randint(0, len(file_list) - 1)              # generate a random number for selection of file
    file_address = "data/" + file_list[selection_flag]                  # select file and save the reading address

    seq = read_sequence(file_address)                                   # Read time sequence file "*.dat", return string list
    basic = get_time_stamp(seq[0].split(" ")[0]+" 00:00:00")            # Read first line date + 00:00:00 -> return in sec as start point
    for i, v in enumerate(seq):                                         # Calculate: all time stamp in queue - start point sec == sec after start point
        seq[i] = get_time_stamp(v) - basic
    
    nio_user_list = [int(c) for c in seq]                                          # return int list of all queue input time (sec relative to start point)
    non_nio_user_list = get_user_distribution(data_file_path, non_nio_user_num)    # return timestamp list of non nio user arrive time

    nio_queue, non_nio_queue = label_queue(nio_user_list, non_nio_user_list)       # return two dicts with label nio and non_nio
    sorted_queue, sorted_label = sort_queue(nio_queue, non_nio_queue)              # sort the two dict by time

    return sorted_queue, sorted_label
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
def label_queue(nio_list:list, non_nio_list:list):
    '''
    labeling and packaging the nio and non-nio queue into dict
    '''
    nio_user_num = len(nio_list)
    non_nio_user_num = len(non_nio_list)
    nio_user_label = []
    non_nio_user_label = []
    for i in range(nio_user_num):
        nio_user_label.append("nio")
    for i in range(non_nio_user_num):
        non_nio_user_label.append("non_nio")
    
    nio_queue_dict = {
        "time" : nio_list,
        "label" : nio_user_label
    }
    non_nio_queue_dict = {
        "time" : non_nio_list,
        "label" : non_nio_user_label
    }
    return nio_queue_dict, non_nio_queue_dict
    ###################################################################################
    ############################ Modified by Y.Meng ###################################
    ###################################################################################
def sort_queue(queue1:dict, queue2:dict):
    '''
    sort the two queues dict with key name: "time", "label"
    sort by ["time"]
    '''
    queue1 = pd.DataFrame(queue1)
    queue2 = pd.DataFrame(queue2)
    dt_total = [queue1, queue2]
    dt_total = pd.concat(dt_total)
    sorted_dt = dt_total.sort_values(by=["time"])
    
    # get the sorted queue and label in format list
    sorted_queue = list(sorted_dt["time"])
    sorted_label = list(sorted_dt["label"])

    return sorted_queue, sorted_label

def get_time_stamp(time_str):
    """
    Reform the datetime into sec relative to 1970.1.1 00:00:00
    Input format: "%Y-%m-%d %H:%M:%S"
    Output format: Integer in sec unit
    """
    timeArray = time.strptime(time_str, "%Y-%m-%d %H:%M:%S")            # reform the time string as time struct
    timeStamp = int(time.mktime(timeArray))                             # calculate the time stamp in sec by using given time struct
    return timeStamp

def read_sequence(file_name):
    """
    Read the "*.dat" user queue date time file, save it as string list 
    """
    if file_name is None:
        logger.error('file not specified')
        return
    with open(file_name) as f:
        lines = f.read().splitlines()
        return lines

def check_seq(tick, interval, user_dist_list, user_label):
    '''
    check how many users in the interval reached
    Argumentation:
    tick: sim_tick, number of iteration within sim_days
    interval: sim_interval in sec
    seq: user queue

    return the list of user number within the given interval, index of list = sec solution, value = number of users
    '''
    service_list = []
    service_label = []

    for i in range(tick * interval, (tick + 1) * interval):
        if user_dist_list.count(i) > 0:
            ind = [x for x,y in list(enumerate(user_dist_list)) if y==i] # return the index list of corresponding timestamp of i
            for j in range(user_dist_list.count(i)):
                service_list.append(i)                                   # load the timestamp at current iteration
            for s in range(len(ind)):
                service_label.append(user_label[ind[s]])                 # load the label at current iteration
    
    if len(service_list) != len(service_label):
        logger.error("the length of user list and label list not identical, check check_seq() function")
        return
    else:
        return service_list, service_label

def get_number_by_pro(number_list, pro_list):
    """
    定义从一个数字列表中以一定的概率取出对应区间中数字的函数
    param number_list:数字列表
    param pro_list:数字对应的概率列表
    return:按概率从数字列表中抽取的数字
    """
    # 用均匀分布中的样本值来模拟概率
    x = random.uniform(0, 1)
    num = x
    # 累积概率
    sum_pro = 0.0
     # 将可迭代对象打包成元组列表
    for number, number_pro in zip(number_list, pro_list):
        sum_pro += number_pro
        if x < sum_pro:
     # 从区间[number. number - 1]上随机抽取一个值
            num = np.random.uniform(number, number - 1)
     # 返回值
            return num
    return num
    
def get_user_distribution(file_name, daily_user):
    """
    user distribution generation -> random mode
    """

    # case of No file
    if file_name is None:
        logger.error('file not specified')
        return None
    
    with open(file_name) as f:
        lines = f.read().splitlines()
        if len(lines) != 48:
            logger.error('this is not a correct distribution data format(should be 48 float)')
            return None
        ret_i = []
        sum_i = 0
        for i in lines:
            b = float(i)
            ret_i.append(b/100.0)
            sum_i = sum_i + b

        num_list = range(1,49)
        final_list = []
        for i in range(daily_user):
            n = get_number_by_pro(number_list=num_list, pro_list=ret_i)
            n = n / 2.0 * 60.0 * 60.0
            final_list.append(int(n))
        final_list.sort()
        return final_list
