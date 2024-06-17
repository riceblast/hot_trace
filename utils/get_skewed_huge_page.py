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
output_dir_prefix = f'/home/yangxr/downloads/test_trace/res/roi_256/{args.benchname}/{args.period}/Page_Size/Skew_Dist/VPN'

hot_skew_list = []  # 统计了某个hot_type在某个时间点下，所有大页的skew情况
global_file_time_list = []

def init_global_env():
    global global_file_time_list

    trace_dir = '/home/yangxr/downloads/test_trace/global_dist/roi_2M/' + args.benchname + "/" + str(args.period)
    for filename in os.listdir(trace_dir):
        if(filename.endswith('global_dist.vout')):
            base_filename = os.path.basename(filename)
            file_time = int(base_filename.split('.')[0].split('_')[-1])
            global_file_time_list.append(file_time)
    global_file_time_list.sort()

    for hot_type in hot_type_list:
        for file_time in global_file_time_list:
            os.makedirs(f'{output_dir_prefix}/{hot_type}/{file_time}/Covered/', exist_ok=True)
            os.makedirs(f'{output_dir_prefix}/{hot_type}/{file_time}/Uncovered/', exist_ok=True)

def init_local_env():
    global hot_skew_list
    global hot_sub_uncover_ratio_list

    hot_skew_list = []

def get_trace(file_path):
    conv = lambda a: int(a, 16)
    data = np.loadtxt(file_path, skiprows=1, usecols=(0,), converters={0: conv}).astype(int)

    return data

def dump_skew_dist(sub_page_list, hot_type, file_time, is_covered):
    assert sub_page_list
    assert len(sub_page_list) <= 8192
    assert (sub_page_list[0] >> 13) == (sub_page_list[-1] >> 13)
    for idx in range(0, len(sub_page_list) - 1):
        assert sub_page_list[idx] < sub_page_list[idx + 1]

    output_dir = ''
    if is_covered:
        output_dir = f'{output_dir_prefix}/{hot_type}/{file_time}/Covered/'
        suffix = 'skew'
    else:
        output_dir = f'{output_dir_prefix}/{hot_type}/{file_time}/Uncovered/'
        suffix = 'uncovered'

    skewness = int(len(sub_page_list) / 8192 * 10) * 10
    output_filename = f'{args.benchname}_{hex(sub_page_list[0] >> 13)}.{suffix}_{str(skewness)}'
    with open(f'{output_dir}/{output_filename}', 'w') as file:
        file.write(f'{len(sub_page_list)}\n')
        file.write(f'{(len(sub_page_list) / 8192):.2f}\n')
        for idx in range(len(sub_page_list) - 1):
            file.write(f'{hex(sub_page_list[idx])} {sub_page_list[idx + 1] - sub_page_list[idx]}\n')
        file.write(f'{hex(sub_page_list[-1])} 0')

def get_hot_skew_dist(hot_type, file_time):
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

    # 用于输出每个大页内部的情况
    skew_pages = []
    uncovered_pages = []

    while(idx_sub < range_sub and idx_huge < range_huge):
        huge_page = hot_huge[idx_huge]
        sub_page = hot_sub[idx_sub]

        # idx_huge指向的是第一个地址大于等于当前sub page的大页
        if (huge_page < (sub_page >> page_offset)):
            if (skew_pages):
                dump_skew_dist(skew_pages, hot_type, file_time, True)
                skew_pages = []
            if (uncovered_pages):
                dump_skew_dist(uncovered_pages, hot_type, file_time, False)
                uncovered_pages = []

            hot_skew_list.append(covered_sub_page)

            covered_sub_page = 0
            idx_huge += 1
            continue

        if (huge_page == (sub_page >> page_offset)):
            skew_pages.append(sub_page)

            covered_sub_page += 1
            idx_sub += 1
            continue

        if (huge_page > (sub_page >> page_offset)):
            if (skew_pages):
                dump_skew_dist(skew_pages, hot_type, file_time, True)
                skew_pages = []
            if (uncovered_pages and (uncovered_pages[0] >> page_offset) != (sub_page >> page_offset)):
                dump_skew_dist(uncovered_pages, hot_type, file_time, False)
                uncovered_pages = []

            uncovered_pages.append(sub_page)

            uncovered_sub_page += 1
            idx_sub += 1
            continue

    if (idx_sub < range_sub):
        uncovered_sub_page += range_sub - idx_sub

    while (idx_huge < range_huge):
        hot_skew_list.append(covered_sub_page)
        covered_sub_page = 0
        idx_huge += 1

    assert len(hot_skew_list) == len(hot_huge)
    assert sum(hot_skew_list) == len(hot_sub) - uncovered_sub_page
    for hot_skew in hot_skew_list:
        assert hot_skew <= 8192

if __name__ == '__main__':
    init_global_env()
    for hot_type in hot_type_list:
        for file_time in global_file_time_list:
            print(f'Generating Skew Dist: {args.benchname} {hot_type} {file_time}s')
            init_local_env()
            get_hot_skew_dist(hot_type, file_time)