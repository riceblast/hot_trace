import numpy as np
import pandas as pd
import math
import itertools


# 导入所需的库
# trace_list = ['redis_0x1b81.skew_10', 'BTree_roi_0x961.skew_0', 'silo_ycsb_roi_4thr_0x87eb.skew_0']
# cache_list = [1024, 780, 245]
trace_list = ['redis_0x1b81.skew_10', 'BTree_roi_0x961.skew_0']
cache_list = [1024, 8192]
trace = ''
cache_size = 0
file_path = ''

hot_num = 0
hot_ratio = 0
conflict_results = []

def get_trace():
    global hot_num
    global hot_ratio

    with open(file_path, 'r') as file:
        hot_num = int(file.readline())
        hot_ratio = float(file.readline())

    conv = lambda a: int(a, 16)
    data = np.loadtxt(file_path, skiprows=2, usecols=(0,), converters={0: conv}).astype(int)
    return data

def test_conflict(addrs, group_size):
    global cache_size

    conflicts = 0
    cache_blocks = [0] * cache_size

    partition = 1024
    for addr in addrs:
        cache_idx = (addr // group_size // math.ceil(8192 / cache_size)) % (cache_size // group_size)
        offset = addr % group_size

        if (cache_blocks[cache_idx + offset] > 0):
            conflicts += 1
        cache_blocks[cache_idx + offset] += 1

    return conflicts / hot_num

def dump_csv():
    global trace

    df = pd.DataFrame({
        'group_num': [state[0] for state in conflict_results],
        'conflict_ratio': [state[1] for state in conflict_results]
        })

    df['conflict_ratio'] = df['conflict_ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))
    output_filename = f'/home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/index_test/result/{trace}.group.conflict.csv'
    df.to_csv(output_filename)

if __name__ == '__main__':
    for idx in range(len(trace_list)):
        trace = trace_list[idx]
        cache_size = cache_list[idx]
        file_path = f'./index_test/data/{trace}'
        conflict_results = []

        addrs = get_trace()
        for group_num in range(1, cache_size + 1):
            conflict_pair = [group_num, 0]  # state, conflict_ratio
            conflict_pair[1] = test_conflict(addrs, group_num)
            conflict_results.append(conflict_pair)
        dump_csv()
        
