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
parser.add_argument('--trace_dir', help='Directory of trace file')
parser.add_argument('--output_dir', help='Output Directory of result')
parser.add_argument('--type', choices=['v', 'p'], default='p', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')
parser.add_argument('num', help='Index of benhmark trace')

args = parser.parse_args()

output_dir = "../res"
trace_dir = "../test_trace/hot_dist_5_15"

# 读取文件并排序、去重
def read_and_sort(benchname, num):
    # e.g ../test_trace/hot_dist_5_15/BFS/BFS_20.hot_5_15.out
    if (args.type == 'p'):
        filename = trace_dir + '/' + benchname + '/' + benchname + '_' + num + '.hot_5_15.out'
    else:
        filename = trace_dir + '/' + benchname + '/' + benchname + '_' + num + '.hot_v_5_15.out'

    page_aligned_pas = set()
    with open(filename, 'r') as file:
        for line in file:
            pa = int(line.strip(), 16)
            page_aligned_pas.add(pa)
    print("DEBUG: Successfully read Addr from file ", filename)
    return sorted(page_aligned_pas)

# 计算相邻两个PA的差值
def calculate_differences(pa_list):
    differences = np.array([pa_list[i + 1] - pa_list[i] for i in range(len(pa_list) - 1)])
    return differences

# 画出差值图像，将y轴设置为对数坐轴
def plot_differences(differences, prefix):
    plt.semilogy(range(1, len(differences) + 1), differences, linewidth=0.05)   # 将y轴设置为对数坐标轴
    #plt.plot(range(1, len(differences) + 1), differences, linewidth=0.05)
    plt.xlabel('Index')
    plt.ylabel('Difference')
    if args.type == 'p':
        plt.title(f'Differences between Adjacent Physical Pages({benchname}_{num})')
    else:
        plt.title(f'Differences between Adjacent Virtual Pages({benchname}_{num})')

    plt.grid(True, which="both", ls="--")  # 添加网格线
    #plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: hex(int(x))[2:]))  # 设置纵坐标为16进制

    plt.savefig(output_dir + '/' + benchname + '/' + prefix + "_logy.png")
    plt.show()
    plt.clf()

def plot_calculate(differences, step=5):
    arr = []
    start = step
    arrLen = len(differences)
    i = 0

    differences = sorted(differences)
    while start < 100:
        val = differences[int(arrLen * start / 100)]
        arr.append((i, val))
        start += step
        i += 1

    x = [item[0] for item in arr]
    y = [item[1] for item in arr]

    plt.plot(x, y, marker='o')  # 使用圆点标记数据点
    plt.ylabel('Addr Diff')
    plt.title('The Addr Diff in different Percentage')
    plt.savefig("percentage.png")
    plt.grid(True)  # 添加网格线

def read_and_calculate(benchname, num, bound=10):
    # e.g ../test_trace/BFS/BFS_5_hot_5_pa_diff.out
    filename = trace_dir + '/' + benchname + '/' + benchname + '_' + num + '_hot_5_15_pa_diff.out'
    array = []
    #
    # 1, 1, 3, 10, 1, 1    [4, 3]
    # 1, 1, 3, 10          [4, 1]
    #
    with open(filename, 'r') as file:
        cnt = 1
        for line in file:
            diff = int(line.strip())
            if diff >= bound:
                array.append(cnt)
                cnt = 1
            else:
                cnt += 1
        array.append(cnt)

    output_filename = output_dir + '/' + benchname + '/' + benchname + '_' + num + '_hot_5_15_group_calculate.out'
    sorted_array = sorted(array, reverse=True)
    np.savetxt(output_filename, np.array(sorted_array), fmt='%d')
    plt.plot(range(1, len(sorted_array) + 1), sorted_array)
    plt.xlabel('Rank')
    plt.ylabel('Total Page Count')
    # e.g ../res/BFS/BFS_from_15_to_20_reverse_cdf.png
    plt.grid(True, which="both", ls="--")  # 添加网格线
    plt.savefig(output_dir + '/' + benchname + '/' + benchname + '_' + num + '_hot_5_15_group_calculate.png')
    plt.show()


if __name__ == "__main__":
    benchname, num = args.benchname, args.num
    if (args.trace_dir is not None):
        trace_dir = args.trace_dir
    if (args.output_dir is not None):
        output_dir = args.output_dir

    pa_list = read_and_sort(benchname, num)
    differences = calculate_differences(pa_list)

    if (args.type == 'p'):
        prefix = benchname + '_' + num + '_hot_5_15_pa_diff'
    else:
        prefix = benchname + '_' + num + '_hot_5_15_va_diff'
    os.makedirs(output_dir + '/' + benchname + '/', exist_ok=True)
    # 将差值结果保存
    np.savetxt(output_dir + '/' + benchname + '/' + prefix + '.out', differences, fmt='%d')
    # 根据差值信息，画图并保存
    plot_differences(differences, prefix)

    plot_calculate(differences)
