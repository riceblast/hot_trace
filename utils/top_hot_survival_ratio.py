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

output_prefix = ""
trace_dir = "/home/yangxr/downloads/test_trace/global_dist/ideal/" + args.benchname + "/" + str(args.period)

if (args.type == 'v'):
    output_dir="/home/yangxr/downloads/test_trace/res/ideal/" + args.benchname + "/" + str(args.period) + "/Top_Hot_Survive/VPN/"
    trace_suffix = 'vout'
elif (args.type == 'p'):
    output_dir="/home/yangxr/downloads/test_trace/res/ideal/" + args.benchname + "/" + str(args.period) + "/Top_Hot_Survive/PPN/"
    trace_suffix = 'pout'

global_trace = {}    # 记录着某个benchmark的所有trace
global_file_time_list = []  # 存储着所有file_time
global_top_60_pages = {}    # 占到前60%的热页, file_time -> [addr,...]
global_top_80_pages = {}    # 占到前80%的热页, file_time -> [addr,...]

def get_trace_data(filename):    
    access_freq = []    #list([addr, access_freq])
    with open(trace_dir + "/" + filename, 'r') as t:
        for line in t:
            cols = line.split()
            if (len(cols) < 2):
                continue
            access_freq.append([int(cols[0], 16), int(cols[1], 10)])    # addr, access_freq
    return access_freq

# 获取top热的
def get_top_hot_data(access_freq):
    count = np.array([freq[1] for freq in access_freq])
    total = count.sum()
    cdf = np.cumsum(count) / total

    top_hot_60 = [] # [addr,...]
    perc_idx = np.argmax(cdf > 0.6)
    for idx in range(0, perc_idx + 1):
        top_hot_60.append(access_freq[idx][0])

    top_hot_80 = []
    perc_idx = np.argmax(cdf > 0.8)
    for idx in range(0, perc_idx + 1):
        top_hot_80.append(access_freq[idx][0])
    
    top_hot_60.sort()
    top_hot_80.sort()
    return top_hot_60, top_hot_80
    
    
def init_global_env():
    global global_trace
    global global_life_time
    global global_file_time_list
    global global_top_60_pages
    global global_top_80_pages

    period = 0
    for filename in os.listdir(trace_dir):
        if (filename.endswith(trace_suffix)):
            period += 1
            base_filename = os.path.basename(filename)
            file_time = int(base_filename.split('.')[0].split('_')[1])

            data = get_trace_data(filename)
            global_trace[file_time] = data
            global_file_time_list.append(int(file_time))

            top_hot_60, top_hot_80 = get_top_hot_data(data)
            global_top_60_pages[file_time] = top_hot_60
            global_top_80_pages[file_time] = top_hot_80            
            
    global_file_time_list.sort()
    print(f"total time cnt: {period}")

def dump_survival_ratio(period_idx, survival_ratio_60_60, survival_ratio_60_80):
    # 热页lifetime信息
    df = pd.DataFrame({
        'period_time': range(0, global_file_time_list[-1] + args.period, args.period),
        'survival_ratio_60_in_60': survival_ratio_60_60[period_idx],
        'survival_ratio_60_in_80': survival_ratio_60_80[period_idx],
    })

    df['survival_ratio_60_in_60'] = df['survival_ratio_60_in_60'].apply(lambda x: format(x, '.2%'))
    df['survival_ratio_60_in_80'] = df['survival_ratio_60_in_80'].apply(lambda x: format(x, '.2%'))
    df.to_csv(f'{output_dir}/{args.benchname}_{global_file_time_list[period_idx]}.survival_ratio.csv')
    print(f"Save surival ratio to {output_dir}/{args.benchname}_{global_file_time_list[period_idx]}.survival_ratio.csv")

def check_survive(pages_cur, pages_future):
    survival_num = 0

    cur_addr_idx = 0
    future_addr_idx = 0
    while (cur_addr_idx < len(pages_cur) and 
        future_addr_idx < len(pages_future)):

        cur_addr = pages_cur[cur_addr_idx]
        future_addr = pages_future[future_addr_idx]

        if (cur_addr == future_addr):
            survival_num += 1

            cur_addr_idx +=1
            future_addr_idx += 1
            continue

        if (cur_addr > future_addr):
            future_addr_idx += 1
            continue

        if (cur_addr < future_addr):
            cur_addr_idx += 1
            continue
    
    return survival_num

# 查看某个时间点后，其所有top_hot的热页存活情况
def monitor_survival_ratio():
    survival_ratio_60_80 = [] # [[0.5, 0.6,...], [0.1, 0.2,...], ...]
    survival_ratio_60_60 = []   # 现在占据60%访存的页面，在未来同样是cover60%的页面内，能占多少比例(和自己比)
    for cur_idx in range(0, len(global_file_time_list) - 1):
        survival_ratio_60_60.append([])
        survival_ratio_60_80.append([])

        for future_idx in range(0, len(global_file_time_list)):
            print(f'{args.benchname} {args.period} compare {global_file_time_list[cur_idx]}...{global_file_time_list[future_idx]}')
            
            # 判断cur_addr是否在future_addr出现过
            survival_ratio_60_80[-1].append(0)
            survival_ratio_60_60[-1].append(0)
            survival_num = 0

            pages_60 = global_top_60_pages[global_file_time_list[cur_idx]]
            pages_60_future = global_top_60_pages[global_file_time_list[future_idx]]
            pages_80 = global_top_80_pages[global_file_time_list[future_idx]]

            survival_num = check_survive(pages_60, pages_60_future)
            survival_ratio_60_60[-1][-1] = survival_num / len(global_top_60_pages[global_file_time_list[cur_idx]])

            survival_num = check_survive(pages_60, pages_80)
            survival_ratio_60_80[-1][-1] = survival_num / len(global_top_60_pages[global_file_time_list[cur_idx]])
        
    for period_idx in range(0, len(global_file_time_list) - 1):
        dump_survival_ratio(period_idx, survival_ratio_60_60, survival_ratio_60_80)

if __name__ == '__main__':
    init_global_env()
    os.makedirs(output_dir, exist_ok=True)
    monitor_survival_ratio()