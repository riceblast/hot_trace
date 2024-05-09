import argparse
import os
import shutil
import numpy as np
import pandas as pd

global_file_time = 0
parser = argparse.ArgumentParser(description='Apply naive linear algorithm to benchmark trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')
parser.add_argument('type', help='[PPN/VPN]')
args = parser.parse_args()

trace_dir='/home/yangxr/downloads/test_trace/hot_dist/ideal/' + args.benchname + '/1/'
# output_dir="/home/yangxr/downloads/test_trace/res/" + args.benchname + "/test/" + args.type
output_dir='/home/yuyf/code/tmp_0/' 

class Model:
    def __init__(self, _start_addr, _end_addr, _length, _slope, _is_compact=False):
        self.start_addr = int(_start_addr)
        self.end_addr = int(_end_addr)
        self.length = _length
        self.slope = _slope
        self.is_compact = _is_compact


# 对热页序列做一个粗略划分
# 
# 去除孤立点（距离大于1000）
def coarse_partition(trace: list, max_dis=1000) -> list: 
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
                partition.append(Model(cur_partition[0], cur_partition[-1], len(cur_partition), slope))
            cur_partition = [trace[i]]
            continue
        if len(cur_partition) == 1:
            cur_partition.append(trace[i])
            slope = diff
            continue

        if diff == slope:
            cur_partition.append(trace[i])
        else:
            partition.append(Model(cur_partition[0], cur_partition[-1], len(cur_partition), slope))
            cur_partition = [trace[i]]

    if len(cur_partition) > 1:
        partition.append(Model(cur_partition[0], cur_partition[-1], len(cur_partition), slope))
    return partition


# 合并set
# 
# 前后两个斜率相同 
#   条件1：distance ^ 2 < 较大set长度
#   条件2：distance % 斜率 = 0
#
# 目前实现的是最简单的版本，栈的深度为1
def traverse_and_combine(partition: list, max_dis=1000) -> list:
    if len(partition) < 1:
        return partition

    stack = []
    new_partition = []
    for curr in partition:
        if len(stack) == 0:
            stack.append(curr)
        else:
            dis = distance(stack[-1], curr)
            if dis > max_dis:
                new_partition.extend(stack)
                stack = [curr]
            else:
                recur_curr = curr
                while len(stack) > 0:
                    top = stack[-1]
                    slope1 = top.slope
                    slope2 = recur_curr.slope 
                    dis = distance(top, recur_curr)
                    if slope1 == slope2:
                        if dis ** 2 < max(top.length, recur_curr.length) and dis % slope1 == 0:
                            new_length = (recur_curr.end_addr - top.start_addr) / slope1
                            recur_curr = Model(top.start_addr, recur_curr.end_addr, new_length, slope1)
                            stack.pop()
                        else:
                            break
                    else:
                        break
                stack.append(recur_curr)
    
    if len(stack) > 0:
        new_partition.extend(stack)

    return new_partition
                       


# 压缩set
#
# 目前设定最大深度为4
def traverse_and_compact(partition: list, max_depth=4) -> list:
    if len(partition) < 1:
        return partition

    stack = []
    new_partition = []
    len_par = len(partition)
    i = 0
    while i < len_par:
        # print(f"LOG i: {i}")
        curr = partition[i]
        if len(stack) == 0: # i = 0 or compact后stack为空（L137）
            stack.append(curr)            
            i += 1
            continue
        if i + len(stack) >= len_par:
            break
        fir_par, lst_par = stack[0], stack[-1]
        if fir_par.length == curr.length and fir_par.slope == curr.slope:
            maybe_slope = curr.start_addr - fir_par.start_addr
            match_cnt = 0
            maybe_group_size = len(stack)
            while i + maybe_group_size < len_par:
                if par_cmp(stack, partition[i:i+maybe_group_size], maybe_slope, match_cnt + 1) == True:
                    match_cnt += 1
                    lst_par = partition[i + maybe_group_size - 1]
                    i += maybe_group_size
                else: # 匹配结束
                    if match_cnt > 0:
                        group_length = 0
                        for p in stack:
                            group_length += p.length
                        length = (match_cnt + 1) * group_length
                        compacted_model = Model(fir_par.start_addr, lst_par.end_addr, length, maybe_slope, True)
                        new_partition.append(compacted_model)
                        if length >= len(stack):
                            stack = []
                        else:
                            stack = stack[length + 1:]
                    else:
                        if len(stack) < max_depth:
                            i += 1
                            stack.append(curr)
                        else:
                            new_partition.append(stack[0])
                            i -= 2
                            stack = [stack[1]]
                    break
        else:
            if len(stack) < max_depth:
                i += 1
                stack.append(curr)
            else:
                new_partition.append(stack[0])
                i -= 2
                stack = [stack[1]]

    if len(stack) > 0:
        new_partition.extend(stack)
    if i < len_par:
        new_partition.extend(partition[i:])
    return new_partition


def par_cmp(list_a, list_b, new_slope, match_cnt):
    tot = len(list_a)
    for i in range(tot):
        par_a = list_a[i]
        par_b = list_b[i]
        if par_b.start_addr - par_a.start_addr != new_slope * match_cnt:
            return False
        if par_b.end_addr - par_a.end_addr != new_slope * match_cnt:
            return False
        if par_a.slope != par_b.slope and par_a.length != par_b.length:
            return False
    return True




def max_min(a, b):
    if a > b:
        return a, b
    else:
        return b, a
    

# 返回（A,B）两点间的距离
# 要求：A在B左边
def distance(A: Model, B: Model):
    return B.start_addr - A.end_addr


def write_seg_to_file(partitions):
    df = pd.DataFrame({
        'start_addr': [hex(seg.start_addr) for seg in partitions],
        'end_addr': [hex(seg.end_addr) for seg in partitions],
        'stride': [seg.slope for seg in partitions],
        'addr_space_cover': [seg.end_addr - seg.start_addr + 1 for seg in partitions],
        'hot_page_cover': [seg.length for seg in partitions],
    })

    df.to_csv(f'{output_dir}/{args.benchname}_{global_file_time}s.segs.csv')


def init_local_env(filename):
    global global_file_time

    base_filename = os.path.basename(filename)
    global_file_time = int(base_filename.split('.')[0].split('_')[1])
    print(f"processing bench: {args.benchname} time: {global_file_time}")



if __name__ == '__main__':
    if args.type == 'PPN':
        prefix = '.pout'
    elif args.type == 'VPN':
        prefix = '.vout'
    else:
        print("arg type should be [VPN/PPN]")
        exit(1)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    conv = lambda a: int(a, 16)
    for filename in os.listdir(trace_dir):
        if (filename.endswith(prefix)):
            init_local_env(filename)
            data = np.loadtxt(trace_dir+filename, dtype=int, converters={0: conv}, usecols=0, skiprows=1)
            cp = coarse_partition(data)
            cp_combined = traverse_and_combine(cp)
            cp_combined_compact = traverse_and_compact(cp_combined)
            write_seg_to_file(cp_combined_compact)