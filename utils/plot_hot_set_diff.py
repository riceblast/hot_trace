import matplotlib.pyplot as plt
import sys
import argparse
import os
import math
import numpy as np
import pandas as pd
import subprocess

parser = argparse.ArgumentParser(description='Caculate the life time of hot pages')
parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('--period', default=1, type=int, help='The division period of trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()

benchname = args.benchname

trace_dir_prefix = "/home/yangxr/downloads/test_trace/res/"
output_dir = "/home/yangxr/downloads/test_trace/res/roi_256/" + args.benchname + "/" + str(args.period) + "/Page_Size/Hot_Set_Diff/"

hot_type_list = ['top_40', 'top_60', 'top_80']
global_file_time_list = []
global_2M_hot_set_list = []
global_256_hot_set_list = []

def init_global_env():
    global global_file_time_list

    plt.cla()
    plt.clf()
    plt.close()

    os.makedirs(output_dir, exist_ok=True)

    trace_dir = '/home/yangxr/downloads/test_trace/global_dist/roi_2M/' + args.benchname + "/" + str(args.period)
    for filename in os.listdir(trace_dir):
        if(filename.endswith('global_dist.vout')):
            base_filename = os.path.basename(filename)
            file_time = int(base_filename.split('.')[0].split('_')[-1])
            global_file_time_list.append(file_time)
    global_file_time_list.sort()

def get_hot_set(roi_type, hot_type):
    global global_256_hot_set_list
    global global_2M_hot_set_list

    hot_set_list = []

    trace_dir = trace_dir_prefix + f'roi_{roi_type}/' + args.benchname + '/' + str(args.period) + '/Zipfan_Hot_Dist/VPN/' + hot_type + '/'
    for file_time in global_file_time_list:
        file_path = trace_dir + f'{args.benchname}_{file_time}.{hot_type}'
        out = subprocess.getoutput(f"wc -l {file_path}")
        hot_set_list.append(int(out.split()[0]))
    
    if (roi_type == '2M'):
        global_2M_hot_set_list = hot_set_list
    if (roi_type == '256'):
        global_256_hot_set_list = hot_set_list

def normalize_hot_set():
    global global_256_hot_set_list
    global global_2M_hot_set_list

    # 转换为MB的单位
    global_256_hot_set_list = [hot_set * 256 // 1024 // 1024 for hot_set in global_256_hot_set_list]
    global_2M_hot_set_list = [hot_set * 2 for hot_set in global_2M_hot_set_list]

def dump_result(hot_type):
    # 先输出文本形式
    diff_mem = []
    for idx in range(len(global_2M_hot_set_list)):
        diff_mem.append(global_2M_hot_set_list[idx]  - global_256_hot_set_list[idx])

    df = pd.DataFrame({
        'Time': [file_time for file_time in global_file_time_list],
        'Bloat_Hot_Set(MB)': [hot_set for hot_set in diff_mem],
        'Bloat_Hot_Set_Ratio': [ diff_mem[idx] / global_2M_hot_set_list[idx] for idx in range(len(global_2M_hot_set_list))]
        })

    df['Bloat_Hot_Set_Ratio'] = df['Bloat_Hot_Set_Ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))

    output_filename = f'{args.benchname}_256_2M.{hot_type}.csv'
    df.to_csv(f'{output_dir}/{output_filename}')

def plot_hot_set_diff(hot_type):
    plt.figure(figsize=(10, 6), dpi=141)

    plt.plot(global_file_time_list, global_2M_hot_set_list, label='2MB hot set')
    plt.plot(global_file_time_list, global_256_hot_set_list, label='256B hot set')

    x_ticks = np.arange(0, max(global_file_time_list) + 120, 120)
    plt.xticks(x_ticks)
    #plt.xticks(global_file_time_list, [str(time) for time in global_file_time_list])

    plt.xlabel('Time(s)')
    plt.ylabel('Hot Set Size(MB)')
    plt.title(f'{args.benchname} Hot Set Diff(256B/2MB 120s)')

    plt.legend()

    output_filename = f'{args.benchname}_256_2M.{hot_type}.png'
    plt.savefig(output_dir + output_filename)


if __name__ == '__main__':
    init_global_env()
    for hot_type in hot_type_list:
        get_hot_set('2M', hot_type)
        get_hot_set('256', hot_type)
        normalize_hot_set()
        dump_result(hot_type)
        plot_hot_set_diff(hot_type)
