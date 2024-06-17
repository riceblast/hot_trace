import matplotlib.pyplot as plt
import sys
import argparse
import os
import math
import numpy as np
import pandas as pd
import subprocess

parser = argparse.ArgumentParser(description='Caculate the life time of hot pages')
parser.add_argument('--period', default=1, type=int, help='The division period of trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()

hot_type_list = ['top_40', 'top_60', 'top_80']
trace_256_dir_prefix = f'/home/yangxr/downloads/test_trace/res/roi_256/{args.benchname}/{args.period}/Zipfan_Hot_Dist/VPN/'
trace_2M_dir_prefix = f'/home/yangxr/downloads/test_trace/res/roi_2M/{args.benchname}/{args.period}/Zipfan_Hot_Dist/VPN/'
output_dir_prefix = f'/home/yangxr/downloads/test_trace/res/roi_256/{args.benchname}/{args.period}/Page_Size/Hot_Skew/'

hot_skew_list = []  # 统计了某个hot_type在某个时间点下，所有大页的skew情况
hot_sub_uncover_ratio_list  = []    # 统计了某个hot_type的所有时间点下，没被大页cover住的sub page的个数, (mem, ratio)
global_file_time_list = []

def init_global_env():
    global global_file_time_list

    plt.cla()
    plt.clf()
    plt.close()

    for hot_type in hot_type_list:
        os.makedirs(f'{output_dir_prefix}/{hot_type}', exist_ok=True)

    trace_dir = '/home/yangxr/downloads/test_trace/global_dist/roi_2M/' + args.benchname + "/" + str(args.period)
    for filename in os.listdir(trace_dir):
        if(filename.endswith('global_dist.vout')):
            base_filename = os.path.basename(filename)
            file_time = int(base_filename.split('.')[0].split('_')[-1])
            global_file_time_list.append(file_time)
    global_file_time_list.sort()

def init_local_env():
    global hot_skew_list
    global hot_sub_uncover_ratio_list

    hot_skew_list = []

    plt.cla()
    plt.clf()
    plt.close()

def get_trace(file_path):
    conv = lambda a: int(a, 16)
    data = np.loadtxt(file_path, skiprows=1, usecols=(0,), converters={0: conv}).astype(int)

    return data

def get_hot_skew(hot_type, file_time):
    global hot_skew_list
    global hot_sub_uncover_ratio_list

    trace_256_dir = f'{trace_256_dir_prefix}/{hot_type}'
    trace_2M_dir = f'{trace_2M_dir_prefix}/{hot_type}'

    hot_sub = get_trace(f'{trace_256_dir}/{args.benchname}_{file_time}.{hot_type}')
    hot_huge = get_trace(f'{trace_2M_dir}/{args.benchname}_{file_time}.{hot_type}')

    uncovered_sub_page = 0    # 所有被热大页cover住的sub page
    covered_sub_page = 0    # 单个大页内被cover住的sub page
    idx_sub = 0
    idx_huge = 0
    range_sub = len(hot_sub)
    range_huge = len(hot_huge)
    page_offset = 13  # sub/huge page之间转换的offset

    while(idx_sub < range_sub and idx_huge < range_huge):
        huge_page = hot_huge[idx_huge]
        sub_page = hot_sub[idx_sub]

        # idx_huge指向的是第一个地址大于等于当前sub page的大页
        if (huge_page < (sub_page >> page_offset)):
            hot_skew_list.append(covered_sub_page)
            covered_sub_page = 0
            idx_huge += 1
            continue

        if (huge_page == (sub_page >> page_offset)):
            covered_sub_page += 1
            idx_sub += 1
            continue

        if (huge_page > (sub_page >> page_offset)):
            uncovered_sub_page += 1
            idx_sub += 1
            continue

    if (idx_sub < range_sub):
        uncovered_sub_page += range_sub - idx_sub

    while (idx_huge < range_huge):
        hot_skew_list.append(covered_sub_page)
        covered_sub_page = 0
        idx_huge += 1

    # uncovered_mem, uncovered_ratio
    hot_sub_uncover_ratio_list.append((uncovered_sub_page * 256 / 1024 / 1024, uncovered_sub_page / range_sub * 100))

    assert len(hot_skew_list) == len(hot_huge)
    assert sum(hot_skew_list) == len(hot_sub) - uncovered_sub_page
    for hot_skew in hot_skew_list:
        assert hot_skew <= 8192

def plot_milestone(cdf, percentage):
    index = int(8192 * percentage)
    #addr_perc = (index + 1) / len(cdf) * 100
    # 横坐标需要归一化
    plt.scatter(index / 8192 * 100, cdf[index], color='red', label=f'{percentage}%')
    plt.text(index / 8192 * 100, cdf[index], f'({percentage * 100}%, {cdf[index]:.2f})', fontsize=10, ha='left')

def get_cdf():
    global hot_skew_list
    
    hot_skew_list.sort()
    cdf = []
    huge_num = len(hot_skew_list)
    cur_sub_num = 0 # 生成CDF时，当前正在处理的热sub page数量的情况
    cum = 0    # CDF中的C，代表累计值
    for idx in range(huge_num):
        if(hot_skew_list[idx] == cur_sub_num):
            cum += 1
            continue

        while(hot_skew_list[idx] > cur_sub_num):
            cdf.append(cum)
            cur_sub_num += 1
        
        # 此时hot_skew_list[idx] == cur_sub_num
        cum += 1
        continue
    
    # 最后一个cum一定没有被放进去
    cdf.append(cum)
    cur_sub_num += 1

    while(cur_sub_num <= 8192):
        cdf.append(cum)
        cur_sub_num += 1

    assert(len(cdf) == 8193)
    assert cur_sub_num <= 8193
    assert cum == huge_num

    cdf = [entry / huge_num for entry in cdf]
    return np.array(cdf)

def plot_hot_skew(hot_type, file_time):
    cdf = get_cdf()
    x_normalized = np.arange(8193) / 8192 * 100
    plt.plot(x_normalized, cdf)

    # 画出不同Hot Sub Page Ratio的关键节点(横坐标)
    plot_milestone(cdf, 0.2)
    plot_milestone(cdf, 0.5)
    plot_milestone(cdf, 0.8)

    plt.title(f'{args.benchname} Huge Page Hot Skewness CDF (256B/2MB {hot_type} {file_time}s)')
    plt.xticks(np.linspace(0, 100, 6), [f'{int(i)}%' for i in np.linspace(0, 100, 6)])
    plt.xlabel('Hot Sub Page Ratio in Huge Page (256B/2MB)')
    plt.ylabel('CDF')

    output_filename = f'{args.benchname}_skewness_{file_time}s.256_2M.png'
    plt.savefig(f'{output_dir_prefix}/{hot_type}/{output_filename}')
    print(f'save plot: {hot_type} {output_filename}')

def dump_hot_miss_ratio(hot_type):
    output_filename = f'{args.benchname}_{hot_type}.hot_skew'
    with open(f'{output_dir_prefix}/{hot_type}/{output_filename}', 'w') as file:
        for entry in hot_sub_uncover_ratio_list:
            file.write(f'{entry[0]:.2f}MB {entry[1]:.2f}%\n')

if __name__ == '__main__':
    init_global_env()
    for hot_type in hot_type_list:
        for file_time in global_file_time_list:
            init_local_env()
            get_hot_skew(hot_type, file_time)
            plot_hot_skew(hot_type, file_time)
        #print(hot_sub_uncover_ratio_list)
        dump_hot_miss_ratio(hot_type)
        hot_sub_uncover_ratio_list = []
