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
output_prefix = "/home/yangxr/downloads/test_trace/res/roi/1_thr/" + args.benchname + "/" + str(args.period) + "/Top_Hot_Survival/"
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

global_file_time_list = []  # 存储着所有file_time
global_top_pages = {}   # {'top_40' -> {time -> [addr,....]}}

def _get_top_hot_data(filename):    
    access_freq = []    #list([addr])
    with open(trace_dir + "/" + filename, 'r') as t:
        for line in t:
            cols = line.split()
            if (len(cols) < 2):
                continue
            access_freq.append(int(cols[0], 16))    # addr
    return access_freq    
    
def init_local_env(hot_type):
    global output_dir
    global trace_dir

    trace_dir = trace_prefix + "/" + hot_type
    output_dir = output_prefix + "/" + hot_type
    os.makedirs(output_dir, exist_ok=True)

def init_file_time_list():
    global global_file_time_list
    for trace in os.listdir(trace_prefix + "/top_40"):  #TODO 硬编码
            base_filename = os.path.basename(trace)
            file_time = int(base_filename.split('.')[0].split('_')[1])
            
            global_file_time_list.append(file_time)
    
    global_file_time_list.sort()

def get_hot_trace(hot_type):
    global global_top_pages

    for trace in os.listdir(trace_dir):
        base_filename = os.path.basename(trace)
        global_file_time = int(base_filename.split('.')[0].split('_')[1])
        print(f"reading hot_dist trace: {args.benchname} hot_type: {hot_type} time: {global_file_time}")

        addr_list = _get_top_hot_data(trace)
        global_top_pages[hot_type][global_file_time] = addr_list

def init_global_env():
    global trace_dir
    global global_top_pages

    init_file_time_list()

    for hot_type in hot_type_list:
        trace_dir = trace_prefix + "/" + hot_type
        global_top_pages[hot_type] = {}
        get_hot_trace(hot_type)

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

def dump_survival_ratio(hot_idx_cur, hot_type_survival_list):
    # 数组转置
    transposed_sur_list = [list(row) for row in zip(*hot_type_survival_list)]   # 将不同future_hot_type的内容拼接到一起，利用file_time索引二维数组

    for file_time in global_file_time_list:
        output_filename = output_dir + "/" + benchname + "_" + str(file_time) + "." +\
            hot_type_list[hot_idx_cur] + "_survival.csv"
        print(f"output: {output_filename}")
        
        with open(output_filename, 'w') as file:
            # csv 表头
            file.write(",period")
            for idx in range(hot_idx_cur, len(hot_type_list)):
                file.write(f",{hot_type_list[idx]}")
            file.write("\n")

            # csv 表项                
            sur_col_list = transposed_sur_list[file_time // args.period]   # e.g. sur_col_list 存储的是 0s，相对于top_40/top_60/top_80的survial ratio，list中的每个元素对应top_n每一列

            csv_linenum = 0
            for compare_file_time in global_file_time_list:

                survial_row = [col[compare_file_time // args.period] for col in sur_col_list]  # 这个survival_raw就对应输出文件中的每一行
                
                ratio_line_part = ','.join(map("{:.2%}".format, survial_row))

                line = str(csv_linenum) + "," + str(compare_file_time) + "," + ratio_line_part

                file.write(line + "\n")

                csv_linenum += 1


# 查看某个时间点前后，其所有top_hot的热页存活情况
def monitor_survival_ratio(hot_idx_cur):
    # [
    # top_40: [0s: [ratio,...], 1s[ratio,...]...] -> 未来需要比较的hot_type
    # top_60: [0s: [ratio,...], 1s[ratio,...]...]
    # top_68: [0s: [ratio,...], 1s[ratio,...]...]
    # ]
    hot_type_survival_list = [] # {future_hot_type -> [[ratio,...],[ratio,....]]}, 存储着top_40/top_60/top_80(比较对象)对应的所有时间的所有survival情况

    for hot_idx_future in range(hot_idx_cur, len(hot_type_list)):
        hot_type_cur = hot_type_list[hot_idx_cur]
        hot_type_future = hot_type_list[hot_idx_future]

        cur_hot_type_survival_list = []  # 当前hot_type出现的survival
        for file_time_cur in global_file_time_list:

            cur_time_survival_list = []
            cur_hot_len = len(global_top_pages[hot_type_cur][file_time_cur])

            for file_time_furture in global_file_time_list:
                print(f"Comparing {file_time_cur}({hot_type_list[hot_idx_cur]}) ... {file_time_furture}({hot_type_list[hot_idx_future]})")

                survival_num = check_survive(global_top_pages[hot_type_cur][file_time_cur],
                    global_top_pages[hot_type_future][file_time_furture])
                survival_ratio = survival_num / cur_hot_len
                cur_time_survival_list.append(survival_ratio)
            
            cur_hot_type_survival_list.append(cur_time_survival_list)
        
        hot_type_survival_list.append(cur_hot_type_survival_list)
    
    # 输出所有信息
    dump_survival_ratio(hot_idx_cur, hot_type_survival_list)
            
if __name__ == '__main__':
    init_global_env()
    for idx in range(0,len(hot_type_list)):
        hot_type = hot_type_list[idx]
        init_local_env(hot_type)
        monitor_survival_ratio(idx)