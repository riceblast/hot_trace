import matplotlib.pyplot as plt
import argparse
import numpy as np
import os

# 处理命令行输入参数
parser = argparse.ArgumentParser(description='Calculate the page spacing every second')
parser.add_argument('--trace_dir', help='Directory of trace file')
parser.add_argument('--output_dir', help='Output Directory of result')
parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('--start', help='start filename')
parser.add_argument('--cnt', help='process file count')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()

g_data_arr_1_5 = []
g_data_arr_5_10 = []
g_data_arr_10_100 = []
g_data_arr_100_INF = []


def read_data(filename_prefix, filename_suffix, start, end):
    global g_data_arr_1_5
    global g_data_arr_5_10
    global g_data_arr_10_100
    global g_data_arr_100_INF
    curr = start
    while curr <= end:
        filename = filename_prefix + f"/{args.benchname}_{curr}" + filename_suffix
        if not os.path.exists(filename):
            return curr - 1
        # print(f"read {filename}")
        addrs = set() 
        with open(filename, "r") as file:
            for line in file:
                addr = int(line.strip(), 16) # page_aligned
                addrs.add(addr)
        sorted_addrs = sorted(addrs)
        differences = np.array([sorted_addrs[i + 1] - sorted_addrs[i] for i in range(len(sorted_addrs) - 1)])
        
        total = len(differences)
        tmp_1_5, tmp_5_10, tmp_10_100, tmp_100_INF = 0, 0, 0, 0
        for i in differences:
            if i < 5: tmp_1_5 += 1
            elif i < 10: tmp_5_10 += 1
            elif i < 100: tmp_10_100 += 1
            else: tmp_100_INF += 1
        g_data_arr_1_5.append(tmp_1_5 / total * 100)
        g_data_arr_5_10.append(tmp_5_10 / total * 100)
        g_data_arr_10_100.append(tmp_10_100 / total * 100)
        g_data_arr_100_INF.append(tmp_100_INF / total * 100)
        curr += 1
    return end


def plot_bin(output_filename, start, end, benchname):
    global g_data_arr_1_5
    global g_data_arr_5_10
    global g_data_arr_10_100
    global g_data_arr_100_INF
    width = 0.4
    data_arr_1_5 = np.array(g_data_arr_1_5)
    data_arr_5_10 = np.array(g_data_arr_5_10)
    data_arr_10_100 = np.array(g_data_arr_10_100)
    data_arr_100_INF = np.array(g_data_arr_100_INF)
    plt.bar(np.arange(start, start + len(data_arr_1_5)), data_arr_1_5, width, label='[1, 5)')
    plt.bar(np.arange(start, start + len(data_arr_5_10)), data_arr_5_10, width, bottom=data_arr_1_5, label='[5, 10)')
    plt.bar(np.arange(start, start + len(data_arr_10_100)), data_arr_10_100, width, bottom=data_arr_1_5+data_arr_5_10, label='[10, 100)')
    plt.bar(np.arange(start, start + len(data_arr_100_INF)), data_arr_100_INF, width, bottom=data_arr_1_5+data_arr_5_10+data_arr_10_100, label='[100, INF)')
    plt.xlabel(f'Execution Time')
    plt.ylabel('Percentage(%)')
    plt.title(f'Page Spacing Analysis in {benchname}')
    plt.xticks(np.arange(start, 1 + end))
    plt.legend(bbox_to_anchor=(1.05, 0), loc=3, borderaxespad=0)
    plt.tight_layout()
    plt.savefig(output_filename)

    print(f"Save File: {output_filename}")


if __name__ == "__main__":
    if (args.trace_dir is not None):
        trace_dir = args.trace_dir
    else: # default
        trace_dir="/home/yangxr/downloads/test_trace/hot_dist_5_15/"

    if (args.output_dir is not None):
        output_dir = args.output_dir
    else: # default
        output_dir="/home/yangxr/downloads/test_trace/res/"

    if args.start is not None:
        start = int(args.start)
    else:
        start = 0 # default, 0
    
    if args.cnt is not None:
        end = start + int(args.cnt) - 1
    else:
        end = 1e7 # default, INF

    if (args.type == 'v'):
        output_dir += args.benchname + "/" + "PN_DIFF/VPN"
        suffix = ".hot_v_5_15.out"
    elif (args.type == 'p'):
        output_dir += args.benchname + "/" + "PN_DIFF/PPN"
        suffix = ".hot_5_15.out"
    trace_dir = "/home/yangxr/downloads/test_trace/hot_dist_5_15/" + args.benchname
    end = read_data(trace_dir, suffix, start, end)
    output_path = output_dir + '/' + args.benchname + f'_{start}_{end}_pa_diff_bin.png'
    plot_bin(output_path, start, end, args.benchname)