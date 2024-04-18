# 统计相邻物理热页的地址差值，并画图
#
# [Usage]: python3 plot_pa_difference.py [--trace_dir] [--output_dir] [--type {v,p}]benchname num 
#   --trace_dir : 输入trace所在的文件夹
#   --output_dir: 结果文件所在文件夹
#   --type      : 所使用的trace类型，虚拟地址(v)或者物理地址(p)
#   benchname   : benchmark的名称，如BFS、PR
#   num         : 所选择的具体测试用例，为一个具体数字
# 注：最终所使用的测试用例为 ../hot_trace/test_trace/hot_dist_5_15/{benchname}/{benchname}_{num}.hot_5_15.out
#
# [output]:
#   图像 ../res/{benchname}/{benchname}_{num}_hot_5_15_pa_diff_ln.png
#   差值 ../res/{benchname}/{benchname}_{num}_hot_5_15_pa_diff.out
#
# 注：地址为硬编码，如有修改需要一并改动！

import matplotlib.pyplot as plt
import sys
import argparse
import os
import math
import numpy as np

# 处理命令行输入参数
parser = argparse.ArgumentParser(description='Caculate the difference between adjacent page numbers')
parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('--period', default=1, type=int, help='The division period of trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')
# parser.add_argument('num', help='Index of benhmark trace')

args = parser.parse_args()

global_file_time = 0 # 现在正在处理的时间数据
trace_dir = "/home/yangxr/downloads/test_trace/ideal_hot_dist/" + args.benchname + "/" + str(args.period)

if (args.type == 'v'):
    output_dir="/home/yangxr/downloads/test_trace/res/ideal/" + args.benchname + "/" + str(args.period) + "/PN_DIFF/VPN"
    trace_suffix = 'vout'
elif (args.type == 'p'):
    output_dir="/home/yangxr/downloads/test_trace/res/ideal/" + args.benchname + "/" + str(args.period) + "/PN_DIFF/PPN"
    trace_suffix = 'pout'

# 从文件中读取页间距差距
def get_pn_diff(trace):
    if (not os.path.exists(trace_dir + "/" + trace)):
        print(f"ERR: file {trace} does not exist")
        exit(1)

    pn_list = []
    with open(trace_dir + "/" + trace, 'r') as t:
        for line in t:
            cols = line.split()
            if (len(cols) < 3 or cols[1] == 0):
                continue
            pn_list.append(int(cols[1]))
    
    return np.array(pn_list)

# 画出差值图像，将y轴设置为对数坐轴
def plot_differences(differences):
    plt.semilogy(range(1, len(differences) + 1), differences, 'b', linewidth=0.05)   # 将y轴设置为对数坐标轴
    #plt.plot(range(1, len(differences) + 1), differences, linewidth=0.05)
    plt.xlabel('Addr')
    plt.ylabel('Difference')
    if args.type == 'p':
        plt.title(f'Differences between Adjacent Physical Pages({args.benchname}_{global_file_time}s)')
    else:
        plt.title(f'Differences between Adjacent Virtual Pages({args.benchname}_{global_file_time}s)')

    plt.grid(True, which="both", ls="--")  # 添加网格线

    plt.savefig(output_dir + '/' + args.benchname + "_" + str(global_file_time) + "_logy.png")
    #plot.show()

    print(f"Save File: {output_dir}/{args.benchname}_{global_file_time}_logy.png")

    plt.cla()
    plt.clf()
    plt.close()

def init_local_env(filename):
    global global_file_time

    os.makedirs(output_dir, exist_ok=True)

    base_filename = os.path.basename(filename)
    global_file_time = int(base_filename.split('.')[0].split('_')[1])
    print(f"processing bench page difference: {args.benchname} time: {global_file_time}")

if __name__ == "__main__":
    for trace in os.listdir(trace_dir):
        if (trace.endswith(trace_suffix)):
            init_local_env(trace)
            pn_diff = get_pn_diff(trace)
            np.savetxt(output_dir + '/' + args.benchname + "_" + str(global_file_time) + 's.out', pn_diff, fmt='%d')
            plot_differences(pn_diff)
