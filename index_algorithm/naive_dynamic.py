# 热页划分间隔要灵活
# 固定斜率法或许可行
# 增/删 操作
#
# 二次分组？

import argparse
import os
import shutil
import numpy as np
import pandas as pd

global_threshold = 16
global_learned_segs = []
global_start_index = 0
global_file_name = 0

parser = argparse.ArgumentParser(description='Apply naive linear algorithm to benchmark trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')
parser.add_argument('type', help='[PPN/VPN]')
args = parser.parse_args()

trace_dir='/home/yangxr/downloads/test_trace/hot_dist_5_15/' + args.benchname + '/'
output_dir="/home/yangxr/downloads/test_trace/res/" + args.benchname + "/Learned_Index_v2/" + args.type

# overlap = 0
# total = 0

class Model:
    def __init__(self, _start_addr, _end_addr, _length, _k, _b, _bitmap):
        self.start_addr = int(_start_addr)
        self.end_addr = int(_end_addr)
        self.length = _length
        self.k = _k
        self.b = _b
        self.bitmap = _bitmap


# 求解线性回归（返回的应该是一个1维参数？）
# 返回值 param (b, k)
def linear_regression(X, y):
    # 直接返回
    if len(X) == 1:
        return np.array([0, 1])
    # 在X的第一列添加偏置项
    X_with_bias = np.c_[np.ones(X.shape[0]), X]

    # 使用正规方程求解线性回归参数
    param = np.linalg.inv(X_with_bias.T.dot(X_with_bias)).dot(X_with_bias.T).dot(y)
    return param


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


def traverse_and_train(list, threshold):
    # threshold最小为2
    threshold_is_2 = threshold == 2
    divided_list = divide_with_threshold(list, threshold)
    for sublist in divided_list:
        flag = train_and_test(sublist, threshold_is_2)
        if flag != True: 
            if threshold > 5:
                traverse_and_train(sublist, threshold // 2)
            else:
                traverse_and_train(sublist, threshold - 1)

# 求解线性回归，并测试模型是否在容错范围内，即正确预测的热页占比大于七成
# 返回值: flag
#   flag是bool类型变量：代表当前模型是否通过热页占比测试
def train_and_test(list, _threshold_is_2, _bound=0.7):
    # 模型简化：用更简单的x和y来训练
    # global overlap
    # global total
    global global_learned_segs

    X = np.array(list, dtype=int) - list[0]
    Y = np.array(range(len(X)))
    model = linear_regression(X, Y)

    # 判断正确映射的热页数量是否超过七成
    predictY = np.round((X * model[1] + model[0])).astype(int)
    res = Y == predictY
    if not _threshold_is_2 and sum(res) / len(res) < _bound:
        return False

    assert(model[1] != 0)
    p_x = np.round((Y - model[0]) / model[1]).astype(int)
    bitmap = np.zeros(p_x[-1] - p_x[0] + 1, dtype=bool)
    for i in p_x:
        bitmap[i - p_x[0]] = True
    # # segment前后无法保证一致
    # if len(global_models) != 0 and global_models[-1].end_addr > p_x[0] + list[0]:
    #     overlap += 1
    #     print(f"total: {total}, overlap: {overlap}")
    # total += 1
    global_learned_segs[-1].append(Model(p_x[0] + list[0], p_x[-1] + list[0], len(X), model[1], model[0], bitmap))
    return True


def write_seg_to_file():
    global global_learned_segs
    global global_file_time

    df = pd.DataFrame({
        'start_addr': [hex(seg.start_addr) for seg in global_learned_segs[-1]],
        'end_addr': [hex(seg.end_addr) for seg in global_learned_segs[-1]],
        'stride': [seg.k for seg in global_learned_segs[-1]],
        'intercept': [seg.b for seg in global_learned_segs[-1]],
        'addr_space_cover': [seg.end_addr - seg.start_addr + 1 for seg in global_learned_segs[-1]],
        'hot_page_cover': [seg.length for seg in global_learned_segs[-1]],
    })

    df.to_csv(f'{output_dir}/{args.benchname}_{global_file_time}s.learned_index_v1.segs.csv')



def write_dram_to_file(data):
    global global_file_time
    global global_learned_segs

    new = []
    seg = global_learned_segs[-1]
    for model in seg:
        start = model.start_addr
        for i in range(len(model.bitmap)):
            if model.bitmap[i] == True:
                new.append(start + i)

    # data的第一行
    print(f'len(data): {len(data)}, len(new): {len(new)}')
    assert(len(new) == len(data))
    df = pd.DataFrame({
        'original': [i for i in data],
        'current': [i for i in new],
    })
    df.to_csv(f'{output_dir}/{args.benchname}_{global_file_time}dram_table.csv')


def init_local_env(filename):
    global global_file_time

    base_filename = os.path.basename(filename)
    global_file_time = int(base_filename.split('.')[0].split('_')[1])
    print(f"processing bench: {args.benchname} time: {global_file_time}")


if __name__ == '__main__':
    if args.type == 'PPN':
        prefix = 'hot_dist.pout'
    elif args.type == 'VPN':
        prefix = 'hot_v_5_15.out'
    else:
        print("arg type should be [VPN/PPN]")
        exit(1)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    conv = lambda a: int(a, 16)
    first = True
    for filename in os.listdir(trace_dir):
        if (filename.endswith(prefix)):
            global_learned_segs.append([])
            init_local_env(filename)
            data = np.loadtxt(trace_dir+filename, dtype=int, converters={0: conv}, usecols=0, skiprows=1)
            traverse_and_train(data, threshold=global_threshold)
            write_seg_to_file()
            write_dram_to_file(data)

