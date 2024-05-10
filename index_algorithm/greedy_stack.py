import argparse
import os
import shutil
import time
import numpy as np
import pandas as pd

global_file_time = 0
global_cold_page_cnt = int(0)
global_total_seg_length = int(0)

parser = argparse.ArgumentParser(description='Apply naive linear algorithm to benchmark trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')
parser.add_argument('period', help='benchmark time period')
args = parser.parse_args()

trace_dir='/home/yangxr/downloads/test_trace/res/roi/1_thr/' + args.benchname + '/' + args.period + '/Zipfan_Hot_Dist/VPN/top_60'
output_dir="/home/yangxr/downloads/test_trace/res/roi/1_thr/" + args.benchname + '/' + args.period  + '/Index/Suboptimal_PLR/VPN/top_60'

class Model:
    def __init__(self, _start_addr, _end_addr, _length, _hotlength, _slope, _is_compact=False):
        self.start_addr = int(_start_addr)
        self.end_addr = int(_end_addr)
        self.length = _length
        self.hotlength = _hotlength
        self.slope = _slope
        self.is_compact = _is_compact


class Statistic:
    def __init__(self, _num, _length, _avg_length, _mispredict, _time):
        self.num = _num
        self.length = _length
        self.avg_length = _avg_length
        self.mispredict = _mispredict
        self.time = _time


def get_num(stat: Statistic):
    return stat.num


# 对热页序列做一个粗略划分
# 
# 去除孤立点（距离大于1000）
def coarse_partition(trace, max_dis=1000) -> list[Model]: 
    global global_total_seg_length

    partition = []
    cur_partition = []
    slope = 0
    for i in range(len(trace)):
        if len(cur_partition) == 0:
            cur_partition.append(trace[i])
            continue
        diff = trace[i] - trace[i-1]     
        if diff > max_dis:
            if len(cur_partition) > 1:
                partition.append(Model(cur_partition[0], cur_partition[-1], len(cur_partition), len(cur_partition), slope))
                global_total_seg_length += len(cur_partition)
            cur_partition = [trace[i]]
            continue
        if len(cur_partition) == 1:
            cur_partition.append(trace[i])
            slope = diff
            continue

        if diff == slope:
            cur_partition.append(trace[i])
        else:
            partition.append(Model(cur_partition[0], cur_partition[-1], len(cur_partition), len(cur_partition), slope))
            global_total_seg_length += len(cur_partition)
            cur_partition = [trace[i]]

    if len(cur_partition) > 1:
        partition.append(Model(cur_partition[0], cur_partition[-1], len(cur_partition), len(cur_partition), slope))
        global_total_seg_length += len(cur_partition)
    return partition


# 区间合并
# 
# 条件
#   1.两区间斜率相同
#   2.两区间距离为斜率的整数
#   3.冷页填充比例小于30%
#
# 目前实现的是最简单的版本，栈的深度为1
def traverse_and_combine(partition: list[Model]) -> list[Model]:
    global global_cold_page_cnt
    if len(partition) < 1:
        return partition

    stack = [partition[0]]
    new_partition: list[Model] = []
    for curr in partition[1:]:
        # flag表示当前一轮是否有区间合并
        # 如果完成了合并，那么下一轮同样有可能有区间合并
        flag = False
        recur_curr = curr
        while flag != True and len(stack) > 0:
            flag = True
            for pos in reversed(range(len(stack))):
                tmp = stack[pos]
                dis = distance(tmp, recur_curr)
                new_length = (recur_curr.end_addr - tmp.start_addr) / tmp.slope
                new_hotlength = tmp.hotlength + recur_curr.hotlength
                if tmp.slope == recur_curr.slope and dis % tmp.slope == 0 and new_hotlength > 0.7 * new_length:
                    global_cold_page_cnt += (dis / tmp.slope - 1)
                    recur_curr = Model(tmp.start_addr, recur_curr.end_addr, new_length, new_hotlength, tmp.slope)
                    flag = False
                    stack = stack[:pos]
                    break
        stack.append(recur_curr)

        # 防止栈无休止地疯长，这里的1000与750是暴力值
        if len(stack) > 1000:
            new_partition.extend(stack[:750])
            stack = stack[750:]

    new_partition.extend(stack)
    return new_partition



# # 压缩set
# #
# # 由于不是普遍现象，暂不使用
# def traverse_and_compact(partition: list, max_depth=4) -> list:
#     if len(partition) < 1:
#         return partition
#     stack = []
#     new_partition = []
#     len_par = len(partition)
#     i = 0
#     while i < len_par:
#         # print(f"LOG i: {i}")
#         curr = partition[i]
#         if len(stack) == 0: # i = 0 or compact后stack为空（L137）
#             stack.append(curr)            
#             i += 1
#             continue
#         if i + len(stack) >= len_par:
#             break
#         fir_par, lst_par = stack[0], stack[-1]
#         if fir_par.length == curr.length and fir_par.slope == curr.slope:
#             maybe_slope = curr.start_addr - fir_par.start_addr
#             match_cnt = 0
#             maybe_group_size = len(stack)
#             while i + maybe_group_size < len_par:
#                 if par_cmp(stack, partition[i:i+maybe_group_size], maybe_slope, match_cnt + 1) == True:
#                     match_cnt += 1
#                     lst_par = partition[i + maybe_group_size - 1]
#                     i += maybe_group_size
#                 else: # 匹配结束
#                     if match_cnt > 0:
#                         group_length = 0
#                         for p in stack:
#                             group_length += p.length
#                         length = (match_cnt + 1) * group_length
#                         compacted_model = Model(fir_par.start_addr, lst_par.end_addr, length, maybe_slope, True)
#                         new_partition.append(compacted_model)
#                         if length >= len(stack):
#                             stack = []
#                         else:
#                             stack = stack[length + 1:]
#                     else:
#                         if len(stack) < max_depth:
#                             i += 1
#                             stack.append(curr)
#                         else:
#                             new_partition.append(stack[0])
#                             i -= 2
#                             stack = [stack[1]]
#                     break
#         else:
#             if len(stack) < max_depth:
#                 i += 1
#                 stack.append(curr)
#             else:
#                 new_partition.append(stack[0])
#                 i -= 2
#                 stack = [stack[1]]
#     if len(stack) > 0:
#         new_partition.extend(stack)
#     if i < len_par:
#         new_partition.extend(partition[i:])
#     return new_partition


# def par_cmp(list_a, list_b, new_slope, match_cnt):
#     tot = len(list_a)
#     for i in range(tot):
#         par_a = list_a[i]
#         par_b = list_b[i]
#         if par_b.start_addr - par_a.start_addr != new_slope * match_cnt:
#             return False
#         if par_b.end_addr - par_a.end_addr != new_slope * match_cnt:
#             return False
#         if par_a.slope != par_b.slope and par_a.length != par_b.length:
#             return False
#     return True
    

# 返回（A,B）两点间的距离
# 要求：A在B左边
def distance(A: Model, B: Model):
    return B.start_addr - A.end_addr


def write_seg_to_file(partitions: list[Model], filename: str):
    df = pd.DataFrame({
        'start_addr': [hex(seg.start_addr) for seg in partitions],
        'end_addr': [hex(seg.end_addr) for seg in partitions],
        'stride': [seg.slope for seg in partitions],
        'addr_space_cover': [seg.end_addr - seg.start_addr + 1 for seg in partitions],
        'hot_page_cover': [seg.hotlength for seg in partitions],
        'page_cover': [seg.length for seg in partitions],
    })
    df.to_csv(f'{output_dir}/{filename}.updatev2.seg.csv')


def write_stat_to_file(stats: list[Statistic]):
    stats.sort(key=get_num)
    df = pd.DataFrame({
        'length': [stat.length for stat in stats],
        'avg_length': [stat.avg_length for stat in stats],
        'mispredict': [stat.mispredict for stat in stats],
        'time': [stat.time for stat in stats], 
    })
    df.to_csv(f'{output_dir}/.updatev2.stat.csv')


def init_local_env(filename: str):
    global global_file_time
    global global_cold_page_cnt
    global global_total_seg_length

    global_cold_page_cnt = 0
    global_total_seg_length = 0

    base_filename = os.path.basename(filename)
    global_file_time = int(base_filename.split('.')[0].split('_')[1])
    print(f"processing bench: {args.benchname} time: {global_file_time}")


if __name__ == '__main__':
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    stat: list[Statistic] = []
    conv = lambda a: int(a, 16)
    for filename in os.listdir(trace_dir):
        if (filename.endswith(".top_60")):
            init_local_env(filename)
            start_time = time.time()
            data = np.loadtxt(trace_dir+'/'+filename, dtype=int, converters={0: conv}, usecols=0, skiprows=1)
            cp = coarse_partition(data)
            cp_combined = traverse_and_combine(cp)
            # cp_combined_compact = traverse_and_compact(cp_combined)
            write_seg_to_file(cp_combined, filename)
            end_time = time.time()
            stat.append(Statistic(global_file_time, len(cp_combined), global_total_seg_length // len(cp_combined), global_cold_page_cnt / global_total_seg_length, end_time - start_time))
    write_stat_to_file(stat)
