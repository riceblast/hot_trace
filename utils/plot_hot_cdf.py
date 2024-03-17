# 利用VPN/PPN热页信息画CDF图
#
# [Usage]: python3 plot_hot_cdf.py [--trace_dir] [--output_dir] [--type {v,p}]benchname num 
#   --trace_dir : 输入trace所在的文件夹
#   --output_dir: 结果文件所在文件夹
#   --type      : 所使用的trace类型，虚拟地址(v)或者物理地址(p)
#   benchname   : benchmark的名称，如BFS、PR
#   num         : 所选择的具体测试用例，为一个具体数字

import sys
import os
import argparse
import matplotlib.pyplot as plt

# 处理命令行参数
parser = argparse.ArgumentParser(description='Caculate the CDF plot of hot pages')
parser.add_argument('--trace_dir', help='Directory of trace file')
parser.add_argument('--output_dir', help='Output Directory of result')
parser.add_argument('--type', choices=['v', 'p'], default='p', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')
parser.add_argument('num', help='Index of benhmark trace')

args = parser.parse_args()

output_dir="../res"
trace_dir = "/Users/yangxr/downloads/hot_dist_5_15/"

def read_and_sort(benchname, num):
    if (args.type == 'p'):
        filename = trace_dir + '/' + benchname + '/' + benchname + '_' + num + '.hot_5_15.out'
    else:
        filename = trace_dir + '/' + benchname + '/' + benchname + '_' + num + '.hot_v_5_15.out'
    
    hot_pages = set()
    with open(filename, 'r') as file:
        for line in file:
            page=int(line.strip(), 16)
            hot_pages.add(page)
    return sorted(hot_pages)

def plot_hot_CDF(hot_pages, prefix):
    dram_addr = range(0, len(hot_pages))
    plt.plot(hot_pages, dram_addr, '-')
    if args.type == 'p':
        plt.xlabel('Physical Address Sapce')
        plt.title(f'Hot PPN CDF({benchname}_{num}s)')
    else:
        plt.xlabel('Virtual Address Sapce')
        plt.title(f'Hot VPN CDF({benchname}_{num}s)')
    plt.ylabel('DRAM Mapping Addr')

    plt.savefig(output_dir + '/' + benchname + '/' + prefix + ".png")


if __name__ == "__main__":
    benchname, num = args.benchname, args.num
    if (args.trace_dir is not None):
        trace_dir = args.trace_dir
    if (args.output_dir is not None):
        output_dir = args.output_dir

    hot_pages = read_and_sort(benchname, num)
    
    if (args.type == 'p'):
        prefix = benchname + '_' + num + 's_hot_5_15_PPN_CDF'
    else:
        prefix = benchname + '_' + num + 's_hot_5_15_VPN_CDF'
    os.makedirs(output_dir + '/' + benchname + '/', exist_ok=True)
    plot_hot_CDF(hot_pages, prefix)
