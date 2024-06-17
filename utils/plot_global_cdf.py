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
import numpy as np

# 处理命令行参数
parser = argparse.ArgumentParser(description='Caculate the CDF plot of hot pages')
parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('--cacheblock', choices=['256', '4096', '2097152' ,'4K', '2M'], default='4096', help='The size of DRAM cacheblock')
parser.add_argument('--period', default=1, type=int, help='The division period of trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()

roi_dir = ""
if args.cacheblock == '256':
    roi_dir = "roi_256"
if args.cacheblock == '4096' or args.cacheblock == '4K':
    roi_dir = "roi_4K"
if args.cacheblock == '2097152' or args.cacheblock == '2M':
    roi_dir = "roi_2M"

global_file_time = 0 # 现在正在处理的时间数据
trace_dir = f"/home/yangxr/downloads/test_trace/global_dist/{roi_dir}/" + args.benchname + "/" + str(args.period)

if (args.type == 'v'):
    output_dir=f"/home/yangxr/downloads/test_trace/res/{roi_dir}/" + args.benchname + "/" + str(args.period) + "/Access_Freq/VPN"
    trace_suffix = 'vout'
elif (args.type == 'p'):
    output_dir=f"/home/yangxr/downloads/test_trace/res/{roi_dir}/" + args.benchname + "/" + str(args.period) + "/Access_Freq/PPN"
    trace_suffix = 'pout'

def plot_access_freq(access_freq):
    addr = range(0, len(access_freq))
    plt.plot(addr, access_freq, '-')
    if args.type == 'p':
        plt.xlabel('Physical Address Sapce')
        plt.title(f'Physical Page Access Freq({args.benchname}_{global_file_time}s)')
    else:
        plt.xlabel('Virtual Address Sapce')
        plt.title(f'Virtual Page Access Freq({args.benchname}_{global_file_time}s)')
    plt.ylabel('Access Freq')

    plt.savefig(output_dir + '/' + "freq_" + args.benchname + "_" + str(global_file_time) + ".png")

    print(f"Save Global Access Freq Dist Plot: {output_dir}/{args.benchname}_{global_file_time}.png")

    plt.cla()
    plt.clf()
    plt.close()

def plot_milestone(cdf, percentage):
    index = np.argmax(cdf > percentage)
    addr_perc = (index + 1) / len(cdf) * 100
    plt.scatter(index, cdf[index], color='red', label=f'{percentage}%')
    plt.text(index, cdf[index], f'{addr_perc:.2f}%', fontsize=10, ha='left')

def plot_freq_cdf(access_freq):
    count = np.array(access_freq)
    total = count.sum()
    cdf = np.cumsum(count) / total

    plt.plot(range(0, len(cdf)), cdf)

    plot_milestone(cdf, 0.6)
    plot_milestone(cdf, 0.8)
    
    if args.type == 'p':
        plt.xlabel('Physical Address Sapce')
        plt.title(f'Physical Page Access Freq CDF({args.benchname}_{global_file_time}s)')
    else:
        plt.xlabel('Virtual Address Sapce')
        plt.title(f'Virtual Page Access Freq CDF({args.benchname}_{global_file_time}s)')
    plt.ylabel('CDF')

    plt.savefig(output_dir + '/' + "freq_CDF_" + args.benchname + "_" + str(global_file_time) + ".png")

    print(f"Save Global Access Freq Dist CDF Plot: {output_dir}/{args.benchname}_{global_file_time}.png")

    plt.cla()
    plt.clf()
    plt.close()
    

def init_local_env(filename):
    global global_file_time

    os.makedirs(output_dir, exist_ok=True)

    base_filename = os.path.basename(filename)
    global_file_time = int(base_filename.split('.')[0].split('_')[-1])
    print(f"processing bench page difference: {args.benchname} time: {global_file_time}")

def get_access_freq(trace):
    if (not os.path.exists(trace_dir + "/" + trace)):
        print(f"Err: file {trace} does no exist")
        exit(1)

    access_freq = []
    with open(trace_dir + "/" + trace, 'r') as t:
        for line in t:
            cols = line.split()
            if (len(cols) < 2):
                continue
            access_freq.append(int(cols[1], 10))
    
    return access_freq

if __name__ == "__main__":
    for trace in os.listdir(trace_dir):
        if (trace.endswith(trace_suffix)):
            init_local_env(trace)
            access_freq = get_access_freq(trace)
            plot_access_freq(access_freq)
            plot_freq_cdf(access_freq)
