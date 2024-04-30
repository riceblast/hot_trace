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
parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('--period', default=1, type=int, help='The division period of trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()

global_file_time = 0 # 现在正在处理的时间数据
trace_dir = "/home/yangxr/downloads/test_trace/hot_dist/ideal/" + args.benchname + "/" + str(args.period)

if (args.type == 'v'):
    output_dir="/home/yangxr/downloads/test_trace/res/ideal/" + args.benchname + "/" + str(args.period) + "/CDF/VPN"
    trace_suffix = 'vout'
elif (args.type == 'p'):
    output_dir="/home/yangxr/downloads/test_trace/res/ideal/" + args.benchname + "/" + str(args.period) + "/CDF/PPN"
    trace_suffix = 'pout'

def plot_hot_CDF(hot_pages):
    dram_addr = range(0, len(hot_pages))
    plt.plot(hot_pages, dram_addr, '-')
    if args.type == 'p':
        plt.xlabel('Physical Address Sapce')
        plt.title(f'Hot PPN CDF({args.benchname}_{global_file_time}s)')
    else:
        plt.xlabel('Virtual Address Sapce')
        plt.title(f'Hot VPN CDF({args.benchname}_{global_file_time}s)')
    plt.ylabel('DRAM Mapping Addr')

    plt.savefig(output_dir + '/' + args.benchname + "_" + str(global_file_time) + ".png")

    print(f"Save CDF Plot: {output_dir}/{args.benchname}_{global_file_time}.png")

    plt.cla()
    plt.clf()
    plt.close()

def init_local_env(filename):
    global global_file_time

    os.makedirs(output_dir, exist_ok=True)

    base_filename = os.path.basename(filename)
    global_file_time = int(base_filename.split('.')[0].split('_')[1])
    print(f"processing bench page difference: {args.benchname} time: {global_file_time}")

def get_hot_pages(trace):
    if (not os.path.exists(trace_dir + "/" + trace)):
        print(f"Err: file {trace} does no exist")
        exit(1)

    hot_pages = []
    with open(trace_dir + "/" + trace, 'r') as t:
        for line in t:
            cols = line.split()
            if (len(cols) < 3):
                continue
            hot_pages.append(int(cols[0], 16))
    
    return hot_pages

if __name__ == "__main__":
    for trace in os.listdir(trace_dir):
        if (trace.endswith(trace_suffix)):
            init_local_env(trace)
            hot_pages = get_hot_pages(trace)
            plot_hot_CDF(hot_pages)
