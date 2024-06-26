import numpy as np
import pandas as pd
import math
import itertools


# 导入所需的库
trace_list = ['redis_0x1b81.skew_10', 'BTree_roi_0x961.skew_0', 'silo_ycsb_roi_4thr_0x87eb.skew_0']
trace = ''
file_path = ''

hot_num = 0
hot_ratio = 0
den_list = []
direct_results = []
linear_results = []

def get_trace():
    global hot_num
    global hot_ratio

    with open(file_path, 'r') as file:
        hot_num = int(file.readline())
        hot_ratio = float(file.readline())

    conv = lambda a: int(a, 16)
    data = np.loadtxt(file_path, skiprows=2, usecols=(0,), converters={0: conv}).astype(int)
    return data

def caculate_density(addrs, group_num):
    hot_density = [0] * group_num
    group_size = 8192 // group_num

    start_pn = addrs[0] & ~((1 << 13) - 1)
    end_pn = start_pn + 0x2000
    range_start = start_pn
    for addr in addrs:
        while(addr >= range_start):
            range_start += group_size
        range_start -= group_size

        if (addr < range_start):
            print(f'addr: {addr} range_start: {range_start}\n')
            assert 0

        if (range_start >= end_pn):
            break
        
        if (addr >= range_start and addr < range_start + group_size):
            target_den_idx = (range_start - start_pn) // group_size
            hot_density[target_den_idx] += 1
            continue

        if (addr >= range_start + group_size):
            range_start += group_size
            continue

    return hot_density

def test_conflict(addrs, density, group_num):
    assert len(density) == group_num
    
    group_size = 8192 // group_num
    group_idx = 0
    cache_offset = 0 # 目前处理到的cache中的位置

    direct_conflicts = 0
    linear_conflicts = 0
    cache_blocks_direct = [0] * hot_num
    cache_blocks_linear = [0] * hot_num

    start_pn = addrs[0] & ~((1 << 13) - 1)
    end_pn = start_pn + 0x2000

    for addr in addrs:
        if (addr < start_pn + group_idx * group_size):
            print(f'test conflict Error! addr: {addr} range_start: {range_start}\n')
            assert 0

        while(addr >= start_pn + group_idx * group_size):
            group_idx += 1
            assert group_idx < group_num + 1
        group_idx -= 1
        range_start = start_pn + group_idx * group_size

        if (group_idx > 0):
            cache_offset = sum(density[0:group_idx])

        assert (addr >= range_start and addr < range_start + group_size)
        # direct map
        dram_idx = (addr - range_start) % density[group_idx]
        if (cache_blocks_direct[cache_offset + dram_idx] > 0):
            direct_conflicts += 1
        cache_blocks_direct[cache_offset + dram_idx] += 1

        # linear map
        dram_idx = math.floor((addr - range_start) * (density[group_idx] / group_size))
        if (cache_blocks_linear[cache_offset + dram_idx] > 0):
            linear_conflicts += 1
        cache_blocks_linear[cache_offset + dram_idx] += 1

    direct_unconflicts = 0
    linear_unconflicts = 0
    for entry in cache_blocks_direct:
        if (entry == 1):
            direct_unconflicts += 1
    for entry in cache_blocks_linear:
        if (entry == 1):
            linear_unconflicts += 1
    
    return [direct_unconflicts, direct_conflicts], [linear_unconflicts, linear_conflicts]


def dump_csv():
    df = pd.DataFrame({
        'hot_num': [hot_num] * 14,
        'group_num': [(1 << group_num_exp) for group_num_exp in range(0, 13 + 1)],
        'direct_fit_ratio': [conflict[0] / hot_num for conflict in direct_results],
        'direct_conflicts_ratio': [conflict[1] / hot_num for conflict in direct_results],
        'linear_fit_ratio': [conflict[0] / hot_num for conflict in linear_results],
        'linear_conflicts_ratio': [conflict[1] / hot_num for conflict in linear_results]
        })

    df['direct_fit_ratio'] = df['direct_fit_ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))
    df['direct_conflicts_ratio'] = df['direct_conflicts_ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))
    df['linear_fit_ratio'] = df['linear_fit_ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))
    df['linear_conflicts_ratio'] = df['linear_conflicts_ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))

    output_filename = f'/home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/index_test/result/{trace}.search_density.csv'
    df.to_csv(output_filename)
    print(f'output -> {trace}.search_density.csv')

if __name__ == '__main__':
    for idx in range(len(trace_list)):
        trace = trace_list[idx]
        file_path = f'/home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/index_test/data/{trace}'
        direct_results = []
        linear_results = []
        den_list = []

        addrs = get_trace()
        for group_num_exp in range(0, 13 + 1):
        #for group_num_exp in [13]:
            group_num = 1 << group_num_exp
            print(f'{trace} ({group_num})')

            density = caculate_density(addrs, group_num)
            direct_result, linear_result = test_conflict(addrs, density, group_num)

            den_list.append(density)
            direct_results.append(direct_result)
            linear_results.append(linear_result)
        dump_csv()
        
