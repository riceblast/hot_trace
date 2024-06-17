# 统计不同阶段的热页：40%, 60%, 80%

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
parser.add_argument('--cacheblock', choices=['256', '4096', '2097152' ,'4K', '2M'], default='4096', help='The size of DRAM cacheblock')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()

benchname = args.benchname
roi_dir = ""
if (args.cacheblock == '256'):
    roi_dir = 'roi_256'
if (args.cacheblock == '4096' or args.cacheblock == '4K'):
    roi_dir = 'roi'
if (args.cacheblock == '2097152' or args.cacheblock == '2M'):
    roi_dir = 'roi_2M'

output_prefix = ""
trace_dir = f"/home/yangxr/downloads/test_trace/global_dist/{roi_dir}/" + args.benchname + "/" + str(args.period)

if (args.type == 'v'):
    output_dir=f"/home/yangxr/downloads/test_trace/res/{roi_dir}/" + args.benchname + "/" + str(args.period) + "/Zipfan_Hot_Dist/VPN/"
    trace_suffix = 'vout'
elif (args.type == 'p'):
    output_dir=f"/home/yangxr/downloads/test_trace/res/{roi_dir}/" + args.benchname + "/" + str(args.period) + "/Zipfan_Hot_Dist/PPN/"
    trace_suffix = 'pout'

#global_trace = {}    # 记录着某个benchmark的所有trace
#global_file_time_list = []  # 存储着所有file_time
global_top_40_pages = {}    # 占到前40%热页, file_time -> [addr,...]
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

# 计算页间距
def caculate_page_diff(top_hot_list):
    # top_hot_list: [[addr, freq],...], ascending by addr
    # return_list: [[addr, pn, freq]...]
    pn_hot_list = []
    for idx in range(0, len(top_hot_list) - 1):
        addr = top_hot_list[idx][0]
        pn = top_hot_list[idx + 1][0] - top_hot_list[idx][0]
        freq = top_hot_list[idx][1]
        pn_hot_list.append([addr, pn, freq])
    
    pn_hot_list.append([top_hot_list[-1][0], 0, top_hot_list[-1][1]])
    return pn_hot_list

def init_global_env():
    os.makedirs(output_dir + "top_40/", exist_ok=True)
    os.makedirs(output_dir + "top_60/", exist_ok=True)
    os.makedirs(output_dir + "top_80/", exist_ok=True)

# 获取top热的
def get_top_hot_data(access_freq):
    count = np.array([freq[1] for freq in access_freq])
    total = count.sum()
    cdf = np.cumsum(count) / total

    # 读入的global_dist按照freq ascending排序
    top_hot_40 = [] # [[addr, freq], ...]
    perc_idx = np.argmax(cdf > 0.4)
    for idx in range(0, perc_idx + 1):
        top_hot_40.append(access_freq[idx])

    top_hot_60 = [] # [[addr, freq], ...]
    perc_idx = np.argmax(cdf > 0.6)
    for idx in range(0, perc_idx + 1):
        top_hot_60.append(access_freq[idx])

    top_hot_80 = [] # [[addr, freq], ...]
    perc_idx = np.argmax(cdf > 0.8)
    for idx in range(0, perc_idx + 1):
        top_hot_80.append(access_freq[idx])
    
    # 按照addr排序
    top_hot_40 = sorted(top_hot_40, key=lambda x: x[0])
    top_hot_60 = sorted(top_hot_60, key=lambda x: x[0])
    top_hot_80 = sorted(top_hot_80, key=lambda x: x[0])

    # 计算页间距
    compelete_top_hot_40 = caculate_page_diff(top_hot_40)
    compelete_top_hot_60 = caculate_page_diff(top_hot_60)
    compelete_top_hot_80 = caculate_page_diff(top_hot_80)
    return compelete_top_hot_40, compelete_top_hot_60, compelete_top_hot_80

def write_hot_to_file(top_hot_list, file_time, trace, hot_type):
    #perc = len(top_hot_list) / len(global_trace[file_time])
    perc = len(top_hot_list) / len(trace)
    output_filename = output_dir + "/" + hot_type + "/" + benchname + "_" + str(file_time) + "." + hot_type
    print(f"writing: {output_filename}")
    with open(output_filename, 'w') as file:
        file.write("{:.2%}".format(perc) + "\n")

        for item in top_hot_list:
            item[0] = hex(item[0])
            line = ' '.join(map(str, item))
            file.write(line + '\n')

def dump_hot_dist():
    #global global_trace
    global global_life_time
    #global global_file_time_list
    global global_top_40_pages
    global global_top_60_pages
    global global_top_80_pages

    period = 0
    for filename in os.listdir(trace_dir):
        if (filename.endswith(trace_suffix)):
            period += 1
            base_filename = os.path.basename(filename)
            file_time = int(base_filename.split('.')[0].split('_')[-1])

            data = get_trace_data(filename)
            #global_trace[file_time] = data
            #global_file_time_list.append(int(file_time))

            top_hot_40, top_hot_60, top_hot_80 = get_top_hot_data(data)

            write_hot_to_file(top_hot_40, file_time, data, "top_40")
            write_hot_to_file(top_hot_60, file_time, data, "top_60")
            write_hot_to_file(top_hot_80, file_time, data, "top_80")   
            
    #global_file_time_list.sort()
    print(f"total time cnt: {period}")

if __name__ == '__main__':
    init_global_env()
    dump_hot_dist()
