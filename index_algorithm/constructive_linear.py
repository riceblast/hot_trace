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
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()

trace_dir='/home/yangxr/downloads/test_trace/hot_dist_5_15/' + args.benchname + '/'
output_dir="/home/yangxr/downloads/test_trace/res/" + args.benchname + "/Learned_Index_v1/VPN"

base_stride = 1
dram_per_core = 4 * 1024 * 1024 * 1024# 平均每个核能使用的DRAM容量 (Byte)
target_false_positive = 0.001
target_bf_size = 10 * 1024  # Byte
global_threshold = 5
global_start_index = 0
global_file_time = 0
global_hot_page_num = 0 # 当前文件内包含的不同页面数，用于计算当前热页的size: global_page_num * 4 * 1024 Byte
global_learned_segs = []
global_learned_stat = []


class LearnedSeg:
    def __init__(self):
        self.start_addr = 0
        self.start_index = 0
        self.end_addr = 0
        self.end_idx = 0
        self.stride = 1.0
        self.dram_fit = 0
        self.dram_gap = 0
        self.dram_conflict = 0
        self.hot_page_cover = 0
        self.addr_space_cover = 0

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
    global global_start_index
    global global_file_time
    global global_hot_page_num

    global_start_index = 0
    global_hot_page_num = 0

    base_filename = os.path.basename(filename)
    global_file_time = int(base_filename.split('.')[0].split('_')[1])
    print(f"processing bench: {args.benchname} time: {global_file_time}")

def get_trace_data(filename):
    global global_hot_page_num
    
    conv = lambda a: int(a, 16)
    data = np.loadtxt(trace_dir + filename, converters={0: conv}).astype(int)
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
    seg.addr_space_cover = (list[-1] - list[0] + 1)

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

        if (hot_page == 0):
            seg.dram_gap += 1
        elif (hot_page == 1):
            seg.dram_fit += 1
        else:
            seg.dram_conflict += (hot_page - 1)
        seg.hot_page_cover += hot_page

        block_addr += stride

    return seg


def traverse_and_train(list, threshold):
    global global_start_index
    global global_learned_segs
    local_learned_segs = []

    divided_list = divide_with_threshold(list, threshold)
    for sublist in divided_list:
        # 不处理孤立的点
        if (len(sublist) > 1):
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
        'addr_space_cover': [seg.addr_space_cover for seg in global_learned_segs[-1]],
        'hot_page_cover': [seg.hot_page_cover for seg in global_learned_segs[-1]],
        'dram_fit': [seg.dram_fit for seg in global_learned_segs[-1]],
        'dram_gap': [seg.dram_gap for seg in global_learned_segs[-1]],
        'dram_conflict': [seg.dram_conflict for seg in global_learned_segs[-1]]
    })

    df.to_csv(f'{output_dir}/{args.benchname}_{global_file_time}s.learned_index_v1.segs.csv')

def bf_false_positive(err_page):
    """
    在给定item数量和bf array容量后, 计算bf的假阳率
    公式: p = pow(1 - exp(-k / (m / n)), k)
    https://hur.st/bloomfilter/?n=4000&p=&m=1Kb&k=3

    参数:
        err_page - 包含了dram_gap和dram_conflict的数量
        size - bloom filter array容量大小 (Byte)
    """
    global global_hot_page_num
    global target_bf_size

    if (err_page == 0):
        return 0

    # 按照target DRAM容量对error page数量进行等比例放大
    n = err_page * dram_per_core / (global_hot_page_num * 4 * 1024) # 放入bf中的元素个数
    m = target_bf_size * 8
    k = 3   # 默认哈希函数个数
    p = math.pow(1 - math.exp(-k / (m / n)), k)
    return p

def bf_size(err_page):
    # 参照bf_false_positive
    # m = ceil((n * log(p)) / log(1 / pow(2, log(2))))
    global global_hot_page_num
    global target_false_positive

    if (err_page == 0):
        return 0

    p = target_false_positive
    n = err_page * dram_per_core / (global_hot_page_num * 4 * 1024)

    m = math.ceil((n * math.log(p)) / math.log(1 / pow(2, math.log(2)))) / 8 / 1024 # KB
    return m

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
        if (filename.endswith('hot_v_5_15.out')):
            print(f"{filename}")
            init_local_env(filename)
            data = get_trace_data(filename)
            traverse_and_train(data, threshold=global_threshold)
            os.makedirs(output_dir, exist_ok=True)
            caculate_statistics()
            write_seg_to_file()
    write_statistic_to_file()