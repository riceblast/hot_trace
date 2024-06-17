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
parser.add_argument('--cacheblock', choices=['256', '4096', '2097152' ,'4K', '2M'], default='4096', help='The size of DRAM cacheblock')
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
hot_type_list = ['top_40', 'top_60', 'top_80']
trace_prefix = f"/home/yangxr/downloads/test_trace/res/{roi_dir}/" + args.benchname + "/" + str(args.period) + "/Zipfan_Hot_Dist"
output_prefix = f"/home/yangxr/downloads/test_trace/res/{roi_dir}/" + args.benchname + "/" + str(args.period) + "/CDF"
trace_dir = ''
output_dir = ''

if (args.type == 'v'):
    trace_prefix += "/VPN"
    output_prefix += "/VPN"
elif (args.type == 'p'):
    trace_prefix += "/PPN"
    output_prefix += "/PPN"
elif (args.type == 'i'):
    trace_prefix += "/MPN"
    output_prefix += "/MPN"

def plot_hot_CDF(hot_pages):
    dram_addr = range(0, len(hot_pages))
    plt.plot(hot_pages, dram_addr, '-')
    if args.type == 'p':
        plt.xlabel('Physical Address Sapce')
        plt.title(f'Hot PPN CDF({args.benchname}_{global_file_time}s)')
    elif args.type == 'v':
        plt.xlabel('Virtual Address Sapce')
        plt.title(f'Hot VPN CDF({args.benchname}_{global_file_time}s)')
    elif args.type == 'm':
        plt.xlabel('Mapped Virtual Address Sapce')
        plt.title(f'Hot MPN CDF({args.benchname}_{global_file_time}s)')
    plt.ylabel('DRAM Mapping Addr')

    plt.savefig(output_dir + '/' + args.benchname + "_" + str(global_file_time) + ".png")

    print(f"Save CDF Plot: {output_dir}/{args.benchname}_{global_file_time}.png")

    plt.cla()
    plt.clf()
    plt.close()

def init_global_env(hot_type):
    global output_dir
    global trace_dir

    trace_dir = trace_prefix + "/" + hot_type
    output_dir = output_prefix + "/" + hot_type
    os.makedirs(output_dir, exist_ok=True)


def init_local_env(filename):
    global global_file_time

    os.makedirs(output_dir, exist_ok=True)

    base_filename = os.path.basename(filename)
    global_file_time = int(base_filename.split('.')[0].split('_')[-1])
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
    for hot_type in hot_type_list:
        init_global_env(hot_type)
        for trace in os.listdir(trace_dir):
            if (trace.endswith(hot_type)):
                init_local_env(trace)
                hot_pages = get_hot_pages(trace)
                plot_hot_CDF(hot_pages)
