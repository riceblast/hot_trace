import numpy as np
import pandas as pd
import itertools


# 导入所需的库
trace_list = ['redis_0x1b81.skew_10', 'BTree_roi_0x961.skew_0', 'silo_ycsb_roi_4thr_0x87eb.skew_0']
cache_list = [1024, 1024, 245]
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

def extract_bits(data, bit_mask):
    # 提取非0 mask位的数据
    extracted_data = 0
    shift = 0
    for i in range(13):
        if bit_mask & (1 << i):
            if data & (1 << i):
                extracted_data |= (1 << shift)
            shift += 1
    return extracted_data

def test_conflict(addrs, bit_mask):
    conflicts = 0

    cache_blocks = [0] * cache_size

    partition = 1024
    for addr in addrs:
        cache_idx = extract_bits(addr, bit_mask) % cache_size

        if (cache_blocks[cache_idx] > 0):
            conflicts += 1
        cache_blocks[cache_idx] += 1

    return conflicts / hot_num

def generate_combinations(r):

    # 生成所有从13位数据中选出3位的组合
    combinations = list(itertools.combinations(range(r), 3))
    states = []

    for combo in combinations:
        state = 0
        for index in combo:
            state |= (1 << index)

        state = ~state
        states.append(state)
    
    return states

def dump_csv():
    df = pd.DataFrame({
        'bit_mask': [hex(state[0]) for state in conflict_results],
        'conflict_ratio': [state[1] for state in conflict_results]
        })

    df['conflict_ratio'] = df['conflict_ratio'].apply(lambda x: '{:.2f}%'.format(x * 100))
    output_filename = f'/home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/index_test/result/{trace}.conflict.csv'
    df.to_csv(output_filename)

if __name__ == '__main__':
    for idx in range(len(trace_list)):
        trace = trace_list[idx]
        cache_size = cache_list[idx]
        file_path = f'./index_test/data/{trace}'
        conflict_results = []

        states = generate_combinations(13)
        addrs = get_trace()
        for state in states:
            conflict_pair = [state, 0]  # state, conflict_ratio
            conflict_pair[1] = test_conflict(addrs, state)
            conflict_results.append(conflict_pair)
        dump_csv()
        
