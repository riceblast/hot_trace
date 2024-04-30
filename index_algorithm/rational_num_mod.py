# 算法流程：
# 按照一定的数量划分为不同的region，在每个region内依次执行以下算法: 
#       利用 (ax + b) mod n, 更新每个block的新位置，
#       判断能否在error_bound内将所有cache block成功映射
#       a将选择任意有理数
# 
# 算法迭代
# V1: 直接用threadhold进行划分，仅处理页间距小于threshold的热页region，并且base stride为1
# V2: 直接用threshold划分，a可以选择任意的有理数
#
# 输出: 1个错误集和一个综合集（就在当前目录下）
#   (1) BFS_15s.learned_dram.segs
#       包含多个learned seg
#           a. 起始地址(Index)
#           b. 结束地址(Index)
#           b. 斜率/stride
#           c. 成功cover的热页个数
#           d. DRAM出现空缺的位置
#           e. DRAM中出现冲突的个数
#           f. cover的热页个数
#           g. cover的虚拟地址范围
#   (2) BFS.learned_dram.statistics
#       总seg数量
#       min/max/avg每段中的内容
#       成功映射的热页占总热页的比值
#       利用冷页填充的热页的比值/利用其他页面填充所占的比值及数量
#       发生冲突的热页的数量及比值
#       利用发生冲突的页计算bloom filter的false-positive


import matplotlib.pyplot as plt
import sys
import argparse
import os
import math
import numpy as np
import pandas as pd

parser = argparse.ArgumentParser(description='Apply constructive_linear algorithm to benchmark trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')
parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')

args = parser.parse_args()

trace_dir='/home/yangxr/downloads/test_trace/hot_dist_5_15/' + args.benchname + '/'
if args.type == 'v':
    output_dir="/home/yangxr/downloads/test_trace/res/" + args.benchname + "/R_Mod_v1/VPN"
    file_postfix = "hot_v_5_15.out"
else:
    output_dir="/home/yangxr/downloads/test_trace/res/" + args.benchname + "/R_Mod_v1/PPN"
    file_postfix = "hot_5_15.out"

demoniator = 503   # 第一个大于500的质数
numerator_range = demoniator * 10
region_size = 100
error_bound = 10 # 最多能接受有几个cache block映射出错
global_start_index = 0
global_file_time = 0
global_learned_segs = []
global_learned_stat = []

# base_stride = 1
# dram_per_core = 4 * 1024 * 1024 * 1024# 平均每个核能使用的DRAM容量 (Byte)
# target_false_positive = 0.001
# target_bf_size = 10 * 1024  # Byte
# global_threshold = 5
# global_start_index = 0
# global_file_time = 0
# global_hot_page_num = 0 # 当前文件内包含的不同页面数，用于计算当前热页的size: global_page_num * 4 * 1024 Byte
# global_learned_segs = []
# global_learned_stat = []


class LearnedSeg:
    def __init__(self):
        self.start_addr = 0
        self.start_index = 0
        self.end_addr = 0
        self.end_idx = 0
        self.region_size = 0
        self.r_slope = 0
        self.demoniator = 0
        self.numerator = 0
        self.err_num = 0    # 出现错误映射的数量

class LearnedStatistics:
    def __init__(self):
        self.time = 0
        self.total_addr_space_cover = 0
        self.total_hot_page_cover = 0
        self.total_hot_page_correct = 0
        self.seg_num = 0
        self.min_hot_correct = 0
        self.max_hot_correct = 0
        self.avg_hot_correct = 0
        self.avg_hot_cover = 0
        self.dram_fit_ratio = 0
        self.dram_gap_ratio = 0
        self.dram_conflict_ratio = 0
        self.err_page = 0
        self.bf_false_positive = 0
        self.bf_size = 0

def init_local_env(filename):
    """针对每个文件，初始化对应的算法环境"""
    global global_start_index
    global global_file_time
    
    global_start_index = 0

    base_filename = os.path.basename(filename)
    global_file_time = int(base_filename.split('.')[0].split('_')[1])
    print(f"processing bench: {args.benchname} time: {global_file_time}")

def get_trace_data(filename):
    global global_hot_page_num
    
    conv = lambda a: int(a, 16)
    data = np.loadtxt(trace_dir + filename, converters={0: conv}).astype(int)
    global_hot_page_num = len(data)
    return data

# 将地址按照固定region size进行划分
def divide_with_threshold(data):
    result = [[data[0]]]
    for i in range(1, len(data)):
        if (i % region_size == 0):
            result.append([data[i]])
        else:
            result[-1].append(data[i])
    return result

def try_rational_num_slope(list):
    """
    依次尝试prime_num个素数, 选择使得err_num最小的素数

    参数:
        list: 归一化为从1开始的地址list
    """
    global error_bound

    min_err_num = len(list)
    candidate_numerator = -1    # 最小err_num对应的分子取值
    modulus = len(list)
    map_cnt = []    # 负责记录每个target pos被多少个cache block映射
    for i in range(len(list)):
        map_cnt.append(0)

    for num in range(numerator_range):
        err_num = 0
        for map in range(len(map_cnt)):
            map_cnt[map] = 0
        
        for addr in list:
            target_addr = (addr * num // demoniator) % modulus
            map_cnt[target_addr] += 1
            if (map_cnt[target_addr] > 1):
                err_num += 1

        if (err_num < min_err_num):
            min_err_num = err_num
            candidate_numerator = num

    return candidate_numerator, min_err_num


def train_and_test(list):
    """
    依次尝试有理数, 并使用冲突最小的有理数作为斜率
    可以把所有热页都紧密地映射到另一个地址空间中
    """
    global global_start_index
    seg = LearnedSeg()
    seg.start_idx = global_start_index
    seg.start_addr = list[0]
    seg.end_idx = global_start_index + len(list) - 1
    seg.end_addr = list[-1]
    seg.region_size = len(list)

    aligned_data = [addr - list[0] + 1 for addr in list]    # 归一化为从1开始
    numerator, err_num = try_rational_num_slope(aligned_data)
    seg.numerator = numerator
    seg.demoniator = demoniator
    seg.r_slope = numerator / demoniator
    seg.err_num = err_num

    return seg
 

def traverse_and_train(list):
    global global_learned_segs
    global global_start_index

    local_learned_segs = []

    divided_list = divide_with_threshold(list)
    for sublist in divided_list:
        seg = train_and_test(sublist)
        local_learned_segs.append(seg)

        global_start_index += len(sublist)

    global_learned_segs.append(local_learned_segs)

def write_seg_to_file():
    global global_learned_segs
    global global_file_time

    df = pd.DataFrame({
        'start_addr': [hex(seg.start_addr) for seg in global_learned_segs[-1]],
        'end_addr': [hex(seg.end_addr) for seg in global_learned_segs[-1]],
        'start_index': [seg.start_idx for seg in global_learned_segs[-1]],
        'end_index': [seg.end_idx for seg in global_learned_segs[-1]],
        'region_size': [seg.region_size for seg in global_learned_segs[-1]],
        'numerator': [seg.numerator for seg in global_learned_segs[-1]],
        'demoniator': [seg.demoniator for seg in global_learned_segs[-1]],
        'r_slope': [seg.r_slope for seg in global_learned_segs[-1]],
        'err_num': [seg.err_num for seg in global_learned_segs[-1]],
    })

    df.to_csv(f'{output_dir}/{args.benchname}_{global_file_time}s.r_mod_v1.segs.csv')

def caculate_statistics():
    global global_learned_segs
    global global_learned_stat
    global global_file_time

    stat = LearnedStatistics()
    stat.time = global_file_time
    stat.seg_num = len(global_learned_segs[-1])
    stat.total_addr_space_cover = sum([seg.addr_space_cover for seg in global_learned_segs[-1]])
    stat.total_hot_page_cover = sum([seg.hot_page_cover for seg in global_learned_segs[-1]])
    stat.avg_hot_cover = round(stat.total_hot_page_cover / stat.seg_num, 2)
    stat.total_hot_page_correct = sum([seg.dram_fit for seg in global_learned_segs[-1]]) 
    stat.min_hot_correct = min([seg.dram_fit for seg in global_learned_segs[-1]])
    stat.max_hot_correct = max([seg.dram_fit for seg in global_learned_segs[-1]])
    stat.avg_hot_correct = round(stat.total_hot_page_correct / stat.seg_num)
    stat.dram_fit_ratio = round(stat.total_hot_page_correct / stat.total_hot_page_cover)
    stat.dram_gap_ratio = round(sum([seg.dram_gap for seg in global_learned_segs[-1]]) / stat.total_hot_page_cover, 2)
    stat.dram_conflict_ratio = round(sum([seg.dram_conflict for seg in global_learned_segs[-1]]) / stat.total_hot_page_cover, 2)
    stat.err_page = sum(seg.dram_gap for seg in global_learned_segs[-1]) + sum(seg.dram_conflict for seg in global_learned_segs[-1])    # BUG: 目前只适用于stride=1的情况
    stat.bf_false_positive = round(bf_false_positive(stat.err_page), 2)
    stat.bf_size = round(bf_size(stat.err_page), 2)

    global_learned_stat.append(stat)

    # if (sum(seg.dram_gap for seg in global_learned_segs[-1]) + 
    #     sum(seg.dram_conflict for seg in global_learned_segs[-1]) != (stat.total_addr_space_cover - stat.total_hot_page_correct)):
    #         print(f"{sum(seg.dram_gap for seg in global_learned_segs[-1]) + sum(seg.dram_conflict for seg in global_learned_segs[-1])}")
    #         print(f"{stat.total_addr_space_cover - stat.total_hot_page_correct}")
    # assert (sum(seg.dram_gap for seg in global_learned_segs[-1]) + 
    #     sum(seg.dram_conflict for seg in global_learned_segs[-1]) == (stat.total_addr_space_cover - stat.total_hot_page_correct))


def write_statistic_to_file():
    global global_learned_stat

    global_learned_stat.sort(key=lambda x: x.time)

    df = pd.DataFrame({
        'time': [stat.time for stat in global_learned_stat],
        'seg_num': [stat.seg_num for stat in global_learned_stat],
        'total_addr_space_cover_pn': [stat.total_addr_space_cover for stat in global_learned_stat],
        'total_hot_page_cover_pn': [stat.total_hot_page_cover for stat in global_learned_stat],
        'avg_hot_cover_pn': [stat.avg_hot_cover for stat in global_learned_stat],
        'total_hot_page_correct_pn': [stat.total_hot_page_correct for stat in global_learned_stat],
        'min_hot_correct_pn': [stat.min_hot_correct for stat in global_learned_stat],
        'max_hot_correct_pn': [stat.max_hot_correct for stat in global_learned_stat],
        'avg_hot_correct_pn': [stat.avg_hot_correct for stat in global_learned_stat],
        'dram_fit_ratio': [stat.dram_fit_ratio for stat in global_learned_stat],    # cacheblock被正确放置在DRAM中的情况
        'dram_gap_ratio': [stat.dram_gap_ratio for stat in global_learned_stat],    # DRAM中出现空cacheblock的情况
        'dram_conflict_ratio': [stat.dram_conflict_ratio for stat in global_learned_stat],  # DRAM中热页冲突的情况
        'err_page': [stat.err_page for stat in global_learned_stat],
        f'bf_false_positive ({target_bf_size / 1024}KB)': [stat.bf_false_positive for stat in global_learned_stat],
        f'bf_size ({target_false_positive}, KB)': [stat.bf_size for stat in global_learned_stat]
        })

    df.to_csv(f'{output_dir}/{args.benchname}.learned_index_v1.statistics.csv')


if __name__ == '__main__':
    for filename in os.listdir(trace_dir):
        if (filename.endswith(file_postfix)):
            print(f"{filename}")
            init_local_env(filename)
            data = get_trace_data(filename)
            traverse_and_train(data)
            os.makedirs(output_dir, exist_ok=True)
    #         caculate_statistics()
            write_seg_to_file()
    # write_statistic_to_file()