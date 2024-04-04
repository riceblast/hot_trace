# 用于统计一段时间内，热页的life time

import matplotlib.pyplot as plt
import sys
import argparse
import os
import math
import numpy as np
import pandas as pd

parser = argparse.ArgumentParser(description='Caculate the life time of hot pages')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()

trace_dir='/home/yangxr/downloads/test_trace/hot_dist_5_15/' + args.benchname + '/'
output_dir="/home/yangxr/downloads/test_trace/res/" + args.benchname + "/Life_Time/VPN"
file_postfix = "hot_v_5_15.out"

global_trace = {}    # 记录着某个benchmark的所有trace
global_life_time = []   # 一个数组，记录着每种lifeime的热页个数
global_hot_diff = []    # 记录着有多少热页变冷，有多少冷页变热，[0]: 热变冷，[1]: 冷变热 [2]: 热变冷ratio [3]: 冷变热ratio

def get_trace_data(filename):    
    conv = lambda a: int(a, 16)
    data = np.loadtxt(trace_dir + filename, converters={0: conv}).astype(int)
    return data

def init_global_env():
    global global_trace
    global global_life_time

    period = 0
    for filename in os.listdir(trace_dir):
        if (filename.endswith(file_postfix)):
            period += 1
            data = get_trace_data(filename)

            base_filename = os.path.basename(filename)
            file_time = int(base_filename.split('.')[0].split('_')[1])
            global_trace[file_time] = data

    for idx in range(period + 1):
        global_life_time.append(0)

    print(f"total time cnt: {period}")

def monitor_life_time():
    global global_life_time
    global global_trace
    global global_hot_diff

    old_hot_pages = []
    global_hot_diff.append([0, 0, 0, 0])
    for addr in global_trace[0]:
        old_hot_pages.append([addr, 1])

    for time in range(1, len(global_trace)):
        assert time in global_trace.keys()
        print(f"{args.benchname} time: {time}")

        global_hot_diff.append([0, 0, 0, 0])

        old_idx = 0        
        for new_addr in global_trace[time]:
            # 已经没有old hot pages了，只需把剩下的new hot pages都添加到old_hot_pages中即可
            if (old_idx == len(old_hot_pages)):
                old_hot_pages.insert(old_idx, [new_addr, 1])
                old_idx += 1
                continue

            if (old_idx >= len(old_hot_pages)):
                print('test')

            # 每次将old_hot_pages处理到比刚好大于当前new_addr的位置
            if (old_hot_pages[old_idx][0] > new_addr):
                old_hot_pages.insert(old_idx, [new_addr, 1])
                old_idx += 1
                
                # 曾经的冷热变热
                global_hot_diff[time][1] += 1
                continue

            while(old_idx < len(old_hot_pages) and 
                old_hot_pages[old_idx][0] <= new_addr):

                if (old_hot_pages[old_idx][0] == new_addr):
                    old_hot_pages[old_idx][1] += 1
                    break

                global_life_time[old_hot_pages[old_idx][1]] += 1
                del old_hot_pages[old_idx]

                # 热页变冷
                global_hot_diff[time][0] += 1

            if (old_idx == len(old_hot_pages)):
                if (old_hot_pages[old_idx - 1][0] < new_addr):
                    old_hot_pages.insert(old_idx, [new_addr, 1])
                    old_idx += 1
                
                continue

            # 代码执行到这里说明， old_hot_pages[old_idx][0] > new_addr
            # 现在要将new_addr加入到old_hot_pages中
            if (old_idx < len(old_hot_pages) and
                (old_hot_pages[old_idx][0] > new_addr)):
                old_hot_pages.insert(old_idx, [new_addr, 1])

                # 冷页变热
                global_hot_diff[time][1] += 1
            old_idx += 1
        
        while(old_idx < len(old_hot_pages)):
            global_life_time[old_hot_pages[old_idx][1]] += 1
            del old_hot_pages[old_idx]

            # 热页变冷
            global_hot_diff[time][0] += 1

        # 计算冷热页变化相对于上一个周期热页的比例
        global_hot_diff[time][2] = global_hot_diff[time][0] / len(global_trace[time - 1])
        global_hot_diff[time][3] = global_hot_diff[time][1] / len(global_trace[time - 1])
          
        for idx in range(0, len(old_hot_pages)):
            if old_hot_pages[idx][0] != global_trace[time][idx]:
                print(f"idx: {idx} old:{hex(old_hot_pages[idx][0])} new:{hex(global_trace[time][idx])}")
                exit(1)

        if (old_idx != len(global_trace[time])):
            print(f"old_idx: {old_idx} len(global_trace[time]): {len(global_trace[time])}")
        assert(old_idx == len(global_trace[time]))

def dump_file():
    global global_life_time
    global global_hot_diff

    del global_life_time[0]
    total = sum(global_life_time)

    # 热页lifetime信息
    df = pd.DataFrame({
        'life_tim(s)': range(1, len(global_life_time) + 1),
        'page_num': global_life_time,
        'ratio': [num / total for num in global_life_time]
    })

    df['ratio'] = df['ratio'].apply(lambda x: format(x, '.2%'))
    df.to_csv(f'{output_dir}/{args.benchname}.life_time.csv')

    # 热映变化信息
    del global_hot_diff[0]
    df = pd.DataFrame({
        'time(s)': range(1, len(global_hot_diff) + 1),
        'h2c': [diff[0] for diff in global_hot_diff],
        'h2c_ratio': [diff[2] for diff in global_hot_diff],
        'c2h': [diff[1] for diff in global_hot_diff],
        'c2h_ratio': [diff[3] for diff in global_hot_diff]
    })
    df['h2c_ratio'] = df['h2c_ratio'].apply(lambda x: format(x, '.2%'))
    df['c2h_ratio'] = df['c2h_ratio'].apply(lambda x: format(x, '.2%'))
    df.to_csv(f'{output_dir}/{args.benchname}.hot_diff.csv')


if __name__ == '__main__':
    init_global_env()
    monitor_life_time()
    os.makedirs(output_dir, exist_ok=True)
    dump_file()