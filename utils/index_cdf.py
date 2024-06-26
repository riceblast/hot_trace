import sys
import os
import argparse
import matplotlib.pyplot as plt

trace_list = ['redis_0x1b81.skew_10', 'BC_roi_4thr_0x1f4b.skew_30','silo_ycsb_roi_4thr_0x87eb.skew_0', 'BTree_roi_0x961.skew_0']
#trace = 'redis_0x1b81.skew_10'
trace = 'BC_roi_4thr_0x1f4b.skew_30'
#trace = 'silo_ycsb_roi_4thr_0x87eb.skew_0'
#trace = 'BTree_roi_0x961.skew_0'
file_path = ''
output_dir = '/home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/index_test/result'

def get_trace():
    hot_pages = []
    with open(file_path, 'r') as t:
        for line in t:
            cols = line.split()
            if (len(cols) < 2):
                continue
            hot_pages.append(int(cols[0], 16))
    
    return hot_pages

def plot_hot_CDF(hot_pages):
    dram_addr = range(0, len(hot_pages))
    #normalized_dram_addr = [x / len(hot_pages) for x in dram_addr]

    huge_pn_start = (hot_pages[0] & ~((1 << 13) - 1))
    huge_pn_end = huge_pn_start + (1 << 13)
    addr_range = range(huge_pn_start, huge_pn_end + 1)
    plt.plot(hot_pages, dram_addr, '-')
    plt.xlabel('Virtual Address Sapce')
    plt.ylabel('CDF')
    #plt.ylim(0, 1)  # 设置 y 轴范围为 0 到 1
    plt.ylim(0, len(hot_pages))
    plt.gca().set_yticklabels(['{:.1f}'.format(y / len(hot_pages)) for y in plt.gca().get_yticks()])
    #plt.xlim((huge_pn_start, huge_pn_end))
    plt.xticks(addr_range[::1024], [addr - huge_pn_start for addr in addr_range[::1024]])


    plt.savefig(f'{output_dir}/{trace}.cdf.png')
    print(f"Save CDF Plot: {output_dir}/{trace}.cdf.png")

    plt.cla()
    plt.clf()
    plt.close()

if __name__ == '__main__':
    for t in trace_list:
        trace = t
        file_path=f'./index_test/data/{trace}'
        addrs = get_trace()
        plot_hot_CDF(addrs)
