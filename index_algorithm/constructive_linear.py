# 算法流程：
# 1. 用一个页间距threshold将热页划分成一个个区域（threshold按照经验取5）,即每个热页region内的页间距都必须小于thresdhold
# 2. 对每个热页region依次执行一下算法：(假设此时以1为base stride)
#       以base_stride为基础，判断每个stride内是否有且仅有一个热页
#       如果热页数量大于或小于1，均视为error_page，进行记录
# 
# 算法迭代
# V1: 直接用threadhold进行划分，仅处理页间距小于threshold的热页region，并且base stride为1
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
parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('--period', default=1, type=int, help='The division period of trace')
parser.add_argument('--threshold', default=16, type=int, help='The division threshold of hot addr space')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()

trace_dir_prefix='/home/yangxr/downloads/test_trace/res/roi/' + args.benchname + '/'
output_dir_prefix="/home/yangxr/downloads/test_trace/res/roi/" + args.benchname + "/"

# dram_per_core = 4 * 1024 * 1024 * 1024# 平均每个核能使用的DRAM容量 (Byte)
# target_false_positive = 0.001
# target_bf_size = 10 * 1024  # Byte
base_stride = 1
global_threshold = args.threshold
min_seg_len = 512 * 5
global_start_index = 0
global_file_time = 0
global_hot_page_num = 0 # 当前文件内包含的不同页面数，用于计算当前热页的size: global_page_num * 4 * 1024 Byte
top_hot_list = ['top_40', 'top_60', 'top_80']
global_learned_segs = []
global_learned_stat = []


class LearnedSeg:
    def __init__(self):
        self.start_addr = 0
        self.start_idx = 0
        self.end_addr = 0
        self.end_idx = 0
        self.stride = 1.0
        self.addr_space_cover = 0
        self.addr_space_cover_ratio = 0.0
        self.hot_cover = 0
        self.hot_cover_ratio = 0.0
        self.cold_cover = 0
        self.cold_cover_ratio = 1.0

class LearnedStatistics:
    def __init__(self):
        self.time = 0
        self.seg_num = 0
        self.addr_space_cover = 0
        self.addr_space_cover_ratio = 0
        self.hot_cover = 0
        self.hot_cover_ratio = 0.0
        self.cold_cover = 0
        self.cold_cover_ratio = 1.0

def init_global_variables():
    global global_learned_segs
    global global_learned_stat

    global_learned_segs = []
    global_learned_stat = []

def init_local_env(filename):
    global global_start_index
    global global_file_time
    global global_hot_page_num

    global_start_index = 0
    global_hot_page_num = 0

    base_filename = os.path.basename(filename)
    global_file_time = int(base_filename.split('.')[0].split('_')[-1])
    print(f"processing bench: {args.benchname} time: {global_file_time}")

def get_trace_data(filepath):
    global global_hot_page_num
    
    conv = lambda a: int(a, 16)
    data = np.loadtxt(filepath, skiprows=1, usecols=(0,), converters={0: conv}).astype(int)
    global_hot_page_num = len(data)
    return data

# 将地址按照threshold划分
def divide_with_threshold(data, threshold):
    result = [[data[0]]]
    for i in range(len(data) - 1):
        prev, curr = data[i], data[i + 1]
        if curr - prev > threshold:
            result.append([curr])
        else:
            result[-1].append(curr)

    return result

def train_and_test(list, stride):
    global global_start_index

    seg = LearnedSeg()
    seg.start_idx = global_start_index
    seg.start_addr = list[0]
    seg.end_idx = global_start_index + len(list) - 1
    seg.end_addr = list[-1]
    seg.stride = stride

    # 按照stride将当前region划分为不同的block
    # 判断每一个block内是否有且仅有一个热页
    block_addr = list[0]
    idx = 0 # 正在遍历list中的索引
    while(block_addr <= list[-1]):
        hot_page = 0
        
        # 判断当前block内有多少个热页被cover
        while(idx < len(list) and list[idx] >= block_addr and list[idx] < block_addr + stride):
            hot_page += 1
            idx+=1

        if (hot_page == 1):
            seg.hot_cover += 1
        
        if (hot_page == 0):
            seg.cold_cover += 1

        block_addr += stride

    seg.hot_cover_ratio = seg.hot_cover / global_hot_page_num
    seg.cold_cover_ratio = seg.cold_cover / (seg.hot_cover + seg.cold_cover)

    return seg


def traverse_and_train(list, threshold):
    global global_start_index
    global global_learned_segs
    local_learned_segs = []

    divided_list = divide_with_threshold(list, threshold)
    for sublist in divided_list:
        # 不处理孤立的点 和 seg长度过小的情况
        if (len(sublist) > min_seg_len):
            seg = train_and_test(sublist, base_stride)
            local_learned_segs.append(seg)
        
        global_start_index += len(sublist)
    
    if (not local_learned_segs):
        local_learned_segs.append(LearnedSeg())
    global_learned_segs.append(local_learned_segs)

def write_seg_to_file():
    global global_learned_segs

    df = pd.DataFrame({
        'start_addr': [hex(seg.start_addr) for seg in global_learned_segs[-1]],
        'end_addr': [hex(seg.end_addr) for seg in global_learned_segs[-1]],
        'start_index': [seg.start_idx for seg in global_learned_segs[-1]],
        'end_index': [seg.end_idx for seg in global_learned_segs[-1]],
        'stride': [seg.stride for seg in global_learned_segs[-1]],
        'hot_cover': [seg.hot_cover for seg in global_learned_segs[-1]],
        'hot_cover_ratio': [seg.hot_cover_ratio for seg in global_learned_segs[-1]],
        'cold_cover': [seg.cold_cover for seg in global_learned_segs[-1]],
        'cold_cover_ratio': [seg.cold_cover_ratio for seg in global_learned_segs[-1]]
    })

    df['hot_cover_ratio'] = df['hot_cover_ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))
    df['cold_cover_ratio'] = df['cold_cover_ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))

    df.to_csv(f'{output_dir}/{args.benchname}_{global_file_time}s.naive_linear_{global_threshold}.segs.csv')

def caculate_statistics():
    global global_learned_segs
    global global_learned_stat
    global global_file_time

    stat = LearnedStatistics()
    stat.time = global_file_time
    stat.seg_num = len(global_learned_segs[-1])
    stat.hot_cover = sum([seg.hot_cover for seg in global_learned_segs[-1]])
    stat.hot_cover_ratio = stat.hot_cover / global_hot_page_num
    stat.cold_cover = sum([seg.cold_cover for seg in global_learned_segs[-1]])
    if (stat.hot_cover + stat.cold_cover == 0):
        stat.cold_cover_ratio = 1.0
    else:
        stat.cold_cover_ratio = stat.cold_cover / (stat.hot_cover + stat.cold_cover)

    global_learned_stat.append(stat)


def write_statistic_to_file():
    global global_learned_stat

    global_learned_stat.sort(key=lambda x: x.time)

    df = pd.DataFrame({
        'time': [stat.time for stat in global_learned_stat],
        'seg_num': [stat.seg_num for stat in global_learned_stat],
        'hot_cover': [stat.hot_cover for stat in global_learned_stat],
        'hot_cover_ratio': [stat.hot_cover_ratio for stat in global_learned_stat],
        'cold_cover': [stat.cold_cover for stat in global_learned_stat],
        'cold_cover_ratio': [stat.cold_cover_ratio for stat in global_learned_stat]
        })

    df['hot_cover_ratio'] = df['hot_cover_ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))
    df['cold_cover_ratio'] = df['cold_cover_ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))

    df.to_csv(f'{output_dir}/{args.benchname}.naive_linear_{global_threshold}.statistics.csv')

if __name__ == '__main__':
    period = args.period

    for top_hot in top_hot_list:
        init_global_variables()

        trace_dir = trace_dir_prefix + '/' + str(period) + '/' + 'Zipfan_Hot_Dist/VPN' + '/' + top_hot + '/'

        for filename in os.listdir(trace_dir):
            #if (filename.endswith('hot_v_5_15.out')):
            print(f"constructive_linear period: {period}, hot: {top_hot}, threshold: {global_threshold}, bench: {filename}")
            init_local_env(filename)
            data = get_trace_data(trace_dir + filename)
            traverse_and_train(data, global_threshold)

            output_dir = output_dir_prefix + '/' + str(period) + '/Index/VPN/native_linear/' + top_hot + '/' + str(global_threshold) + '/'
            os.makedirs(output_dir, exist_ok=True)

            caculate_statistics()
            write_seg_to_file()
        write_statistic_to_file()