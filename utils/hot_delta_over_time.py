# # 作出热页随时间变化情况，将地址空间拆分为不同的区域，

# import matplotlib.pyplot as plt
# import sys
# import argparse
# import os
# import math
# import numpy as np
# import pandas as pd

# parser = argparse.ArgumentParser(description='Caculate the life time of hot pages')
# parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')
# parser.add_argument('--period', default=1, type=int, help='The division period of trace')
# parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

# args = parser.parse_args()

# trace_dir = "/home/yangxr/downloads/test_trace/hot_dist/ideal/" + args.benchname + "/" + str(args.period)

# if (args.type == 'v'):
#     trace_suffix = 'vout'
#     output_dir="/home/yangxr/downloads/test_trace/res/ideal/" + args.benchname + "/" + str(args.period) + "/Hot_DIFF/VPN/"
    
# elif (args.type == 'p'):
#     trace_suffix = 'pout'
#     output_dir="/home/yangxr/downloads/test_trace/res/ideal/" + args.benchname + "/" + str(args.period) + "/Hot_DIFF/PPN/"

# dist_output_dir = output_dir + "Distribution/"
# delta_output_dir = output_dir + "Delta/"

# linewidth = 0.3
# plot_period = 7 # 每隔这么多个period就构成一张新图
# region_num = 2000   # 将地址空间划分为多少个region
# region_size = 0 # addr_range / region, 每个region包括的地址空间大小
# global_addr_range = 0   # 最大的热页addr_range范围
# global_trace = {}    # 记录着某个benchmark的所有trace
# global_file_time_list = []   # 记录着所有有效的file time

# HOT_MORE = 2
# HOT_NORMAL = 1
# HOT_LESS = 0
# COLD = -1
# global_hot_diff = []    # 记录着一个[hot_page_num, type], type: 0(热页变少)，1(热页不变)，2(热页变多)，-1(不存在热页)

# def get_trace_data(filename):
#     conv = lambda a: int(a, 16)
#     data = np.loadtxt(trace_dir + "/" + filename, dtype=int, converters={0: conv}, usecols=0, skiprows=1)
#     return data

# def init_global_env():
#     global global_trace
#     global global_addr_range
#     global region_size
#     global global_hot_diff

#     period_num = 0
#     for filename in os.listdir(trace_dir):
#         if (filename.endswith(trace_suffix)):
#             period_num += 1
#             base_filename = os.path.basename(filename)
#             file_time = int(base_filename.split('.')[0].split('_')[1])

#             data = get_trace_data(filename)
#             global_trace[file_time] = data
#             global_file_time_list.append(int(file_time))

#             if (data[-1] > global_addr_range):
#                 global_addr_range = data[-1]
    
#     region_size = math.ceil((global_addr_range + 1) / region_num)
#     for idx in range(len(global_trace)):
#         global_hot_diff.append([])
#         for region_idx in range(region_num):
#             global_hot_diff[idx].append([0, COLD])   # hot_pages_num, type
#     print(f"addr space range: {hex(global_addr_range)}({global_addr_range * 4 // 1024 // 1024}GB)")
#     print(f"region num: {region_num}, region_size: {region_size}({region_size * 4 // 1024}MB)")

#     global_file_time_list.sort()
#     print(f"total period num: {period_num}")

#     os.makedirs(output_dir, exist_ok=True)
#     os.makedirs(dist_output_dir, exist_ok=True)
#     os.makedirs(delta_output_dir, exist_ok=True)


# # 计算热页变化的情况，最终得到一个二维数组，表示热页的变化情况
# def caculate_hot_diff():
#     global global_hot_diff

#     # 初始化每个region内的热页数量
#     for period_idx in range(len(global_trace)):
#         addr_idx = 0
#         for region_idx in range(region_num):
#             trace_key = global_file_time_list[period_idx]
#             while (addr_idx < len(global_trace[trace_key]) and 
#                 global_trace[trace_key][addr_idx]  >= region_idx * region_size and
#                 global_trace[trace_key][addr_idx] < (region_idx + 1) * region_size):
#                 # addr落在当前region内
#                 global_hot_diff[period_idx][region_idx][0] += 1
#                 global_hot_diff[period_idx][region_idx][1] = HOT_NORMAL
#                 addr_idx += 1
#                 continue
            
#             if (addr_idx >= len(global_trace[trace_key])):
#                 break

#             if (global_trace[trace_key][addr_idx] >= (region_idx + 1) * region_size):
#                 # addr应当落在下一个region中
#                 continue
#             else:
#                 # buggy
#                 print(f"Err,trace_key: {trace_key} addr_idx: {addr_idx} region_idx: {region_idx}")
    
#     draw_plot(is_dist=True)
    
#     # 统计热页变化情况
#     for idx in range(1, len(global_hot_diff)):
#         for region_idx in range(region_num):

#             if(global_hot_diff[idx][region_idx][0] > 
#                 global_hot_diff[idx - 1][region_idx][0]):
#                 global_hot_diff[idx][region_idx][1] = HOT_MORE
            
#             if (global_hot_diff[idx][region_idx][0] <
#                 global_hot_diff[idx - 1][region_idx][0]):
#                 global_hot_diff[idx][region_idx][1] = HOT_LESS
    
#     draw_plot(is_dist=False)

# # 根据每个region的状态，画出每条线
# def draw_line(period_idx, region_idx, is_dist):
#     if (is_dist):
#         # 只需画出热页分布
#         if (global_hot_diff[period_idx][region_idx][1] != COLD):
#             plt.hlines(y=region_idx, xmin=period_idx, xmax=period_idx + 1, color="#DC143C", linewidth=linewidth)
#     else:
#         # 画出热页变化
#         # 热页增加 红色
#         if (global_hot_diff[period_idx][region_idx][1] == HOT_MORE):
#             plt.hlines(y=region_idx, xmin=period_idx, xmax=period_idx + 1, color="#DC143C", linewidth=linewidth)

#         # 热页变少，蓝色
#         if (global_hot_diff[period_idx][region_idx][1] == HOT_LESS):
#             plt.hlines(y=region_idx, xmin=period_idx, xmax=period_idx + 1, color="#1E90FF", linewidth=linewidth)


# def draw_plot(is_dist):
#     x_start = 0
#     x_end = 0
#     for idx in range(0, len(global_hot_diff) + 1):
#         if((idx == len(global_hot_diff) and (idx - 1) % plot_period != 0) or
#             (idx != 0 and idx % plot_period == 0)):
#             x_start = x_end
#             x_end = x_start + plot_period
#             plt.xlim(x_start, x_end)
#             plt.ylim(-200, region_num + 200)
#             plt.title("Hot Page Dynamic Change Over Time")
#             plt.xlabel("Period")
#             plt.ylabel("Addr Space Region")

#             if (is_dist):
#                 plt.savefig(dist_output_dir + '/' + "hot_dist_" + args.benchname + "_" + str((idx -1) // plot_period) + ".png")
#                 print(f"Save CDF Plot: {dist_output_dir}/hot_dist_{args.benchname}_{(idx -1) // plot_period}.png")
#             else:
#                 plt.savefig(delta_output_dir + '/' + "hot_delta_" + args.benchname + "_" + str((idx -1) // plot_period) + ".png")
#                 print(f"Save CDF Plot: {delta_output_dir}/hot_delta_{args.benchname}_{(idx -1) // plot_period}.png")

#             plt.cla()
#             plt.clf()
#             plt.close()

#         if (idx >= len(global_hot_diff)):
#             return
        
#         for region_idx in range(region_num):
#             draw_line(idx, region_idx, is_dist)


# if __name__ == '__main__':
#     init_global_env()
#     caculate_hot_diff()

# 用于统计一段时间内，热页的life time

import matplotlib.pyplot as plt
import sys
import argparse
import os
import math
import numpy as np
import pandas as pd

parser = argparse.ArgumentParser(description='Caculate the life time of hot pages')
parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('--period', default=1, type=int, help='The division period of trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()

benchname = args.benchname
hot_type_list = ['top_40', 'top_60', 'top_80']
#trace_prefix = "/home/yangxr/tmp"
trace_prefix = "/home/yangxr/downloads/test_trace/res/roi/1_thr/" + args.benchname + "/" + str(args.period) + "/Zipfan_Hot_Dist/"
output_prefix = "/home/yangxr/downloads/test_trace/res/roi/1_thr/" + args.benchname + "/" + str(args.period) + "/Hot_Delta/"
trace_dir = ''
output_dir = ''

if (args.type == 'v'):
    trace_prefix += "/VPN"
    output_prefix += "/VPN"
elif (args.type == 'p'):
    trace_prefix += "/PPN"
    output_prefix += "/PPN"
elif (args.type == 'i'):
    trace_prefix += "/MPN"
    output_prefix += "/MPN"

region_pn = 1 * 1024    # 4MB
region_num = 0  # regoin个数
delta_ratio_threshold = 0.3    # 变化率上限
delta_num_threshold = 10   # 变化页面个数上限

global_file_time_list = []  # 存储着所有file_time
global_top_pages = {}   # {'top_40' -> {time -> [addr,....]}}
global_range_list = {}  # {'top_40' -> addr_range}

class HotDeltaStat:
    def __init__(self):
        self.hot_region_num = 0    # 有效的region数,即包含热页的个数
        self.delta_region_num = 0   # 发生变化的region个数
        self.delta_region_ratio = 0 # 发生变化的region比例 (占热页比例)

def _get_top_hot_data(filename):    
    access_freq = []    #list([addr])
    with open(trace_dir + "/" + filename, 'r') as t:
        for line in t:
            cols = line.split()
            if (len(cols) < 2):
                continue
            access_freq.append(int(cols[0], 16))    # addr
    return access_freq    

def init_file_time_list():
    global global_file_time_list
    for trace in os.listdir(trace_prefix + "/top_40"):  #TODO 硬编码
            base_filename = os.path.basename(trace)
            file_time = int(base_filename.split('.')[0].split('_')[1])
            
            global_file_time_list.append(file_time)
    
    global_file_time_list.sort()

def get_hot_trace(hot_type):
    global global_top_pages
    global global_range_list

    for trace in os.listdir(trace_dir):
        base_filename = os.path.basename(trace)
        global_file_time = int(base_filename.split('.')[0].split('_')[1])
        print(f"reading hot_dist trace: {args.benchname} hot_type: {hot_type} time: {global_file_time}")

        addr_list = _get_top_hot_data(trace)
        global_top_pages[hot_type][global_file_time] = addr_list

        if (global_range_list[hot_type] < addr_list[-1]):
            global_range_list[hot_type] = addr_list[-1]

def init_global_env():
    global trace_dir
    global region_num
    global global_top_pages
    global global_range_list

    init_file_time_list()

    for hot_type in hot_type_list:
        trace_dir = trace_prefix + "/" + hot_type
        global_top_pages[hot_type] = {}
        global_range_list[hot_type] = 0
        get_hot_trace(hot_type)

def init_local_env(hot_type):
    global output_dir
    global trace_dir
    global region_num

    region_num = math.ceil(global_range_list[hot_type] + 1 / region_pn)

    trace_dir = trace_prefix + "/" + hot_type
    output_dir = output_prefix + "/" + hot_type
    os.makedirs(output_dir, exist_ok=True)

def _init_region_list(hot_type, file_time):
    region_list = [0 for _ in range(region_num)]
    for addr in global_top_pages[hot_type][file_time]:
        region_list[addr // region_pn] += 1
    
    return region_list

def _caculate_hot_region(region_list):
    cnt = 0
    for hot_num in region_list:
        if hot_num > 0:
            cnt += 1
    
    return cnt

def _caculate_hot_delta(region_list_cur, region_list_next):
    delta_region_num = 0
    for idx in range(0, len(region_list_cur)):
        delta = abs(region_list_next[idx] - region_list_cur[idx])
        if (region_list_cur[idx] != 0 and
            (delta / region_list_cur[idx]) > delta_ratio_threshold and
            delta > 10):
            delta_region_num += 1
    
    return delta_region_num

def dump_hot_delta(hot_type, stat_list):
    df = pd.DataFrame({
        'period': [time for time in global_file_time_list],
        'delta_regoin_num': [stat.delta_region_num for stat in stat_list],
        'hot_region_num': [stat.hot_region_num for stat in stat_list],
        'delta_ratio': [stat.delta_region_ratio for stat in stat_list],
    })

    df['delta_ratio'] = df['delta_ratio'].apply(lambda x: '{:.2%}'.format(x))
    df.to_csv(f"{output_dir}/{benchname}.hot_delta.csv")
    print(f"Hot Delta Output: {output_dir}/{benchname}.hot_delta.csv")

# 计算热页变化区域情
def caculate_hot_diff(hot_type):
    stat_list = [] #[HotDeltaStat, ...]
    region_list_cur = _init_region_list(hot_type, 0) # 初始化0时刻region_list

    for idx in range(0, len(global_file_time_list)):
        file_time = global_file_time_list[idx]
        stat = HotDeltaStat()
        stat.hot_region_num = _caculate_hot_region(region_list_cur)

        print(f"Hot Delta: {benchname} {hot_type} cur({file_time})")

        # 最后一个时刻
        if(idx == len(global_file_time_list) - 1):
            stat_list.append(stat)
            break

        region_list_next = _init_region_list(hot_type, global_file_time_list[idx + 1])
        stat.delta_region_num = _caculate_hot_delta(region_list_cur, region_list_next)
        stat.delta_region_ratio = stat.delta_region_num / stat.hot_region_num

        stat_list.append(stat)
        region_list_cur = region_list_next

    dump_hot_delta(hot_type, stat_list)
            
if __name__ == '__main__':
    init_global_env()
    for idx in range(0,len(hot_type_list)):
        hot_type = hot_type_list[idx]
        init_local_env(hot_type)
        caculate_hot_diff(hot_type)