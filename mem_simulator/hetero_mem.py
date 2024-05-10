import matplotlib.pyplot as plt
import sys
import argparse
import os
import math
import re
import numpy as np
import pandas as pd

parser = argparse.ArgumentParser(description='Simulate the Heterogenous Memory Artichecture')
parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('--period', default=1, type=int, help='The division period of trace')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()
benchname = args.benchname

cxl_layout_file = "/home/yangxr/downloads/test_trace/compact_addr_space/roi/1_thr/" + benchname + "/" + benchname
trace_dir = "/home/yangxr/downloads/test_trace/raw_data/roi/1_thr/" + benchname + "/"
output_dir = "/home/yangxr/downloads/test_trace/res/compute/" + benchname + "/simulate/" 
if (args.type == 'v'):
    cxl_layout_file += ".vout"
elif (args.type == 'p'):
    cxl_layout_file += ".pout"

class HeterogeneousMemorySystem:
    def __init__(self, cxl_layout_file, trace_dir):
        # 初始化 CXL Memory
        self.initialize_cxl(cxl_layout_file)
        
        # 计算 DRAM 容量，初始化 DRAM cache
        self.dram_capacity = self.cxl_capacity // 8
        self.dram_set_count = self.dram_capacity // 4  # 4-way set associative
        self.dram_cache = np.full((self.dram_set_count, 4), -1, dtype=int)  # -1 表示空位
        self.dram_lru = np.zeros((self.dram_set_count, 4), dtype=int)  # 记录 LRU 顺序
        self.trace_dir = trace_dir
        
        # 初始化统计数据
        self.page_replacements = 0  # 用于统计页面替换的次数
        self.total_hits = 0
        self.total_misses = 0
    
    def initialize_cxl(self, cxl_layout_file):
        with open(cxl_layout_file, 'r') as f:
            first_line = int(f.readline().strip())
            # 找到第一个大于等于 first_line 且能被 64 整除的值作为 CXL 容量
            self.cxl_capacity = ((first_line + 63) // 64) * 64
            self.cxl_mapping = {}
            for line in f:
                index, page_number = line.strip().split()[:2]
                page_number = int(page_number, 16)
                index = int(index)
                if (page_number in self.cxl_mapping):
                    print(f"Err: addr {page_number} already in cxl_mapping list, benchmark: {benchname}")
                    exit(1)
                self.cxl_mapping[page_number] = index

    def find_dram_set(self, page_number):
        # 根据页号找到应该放置的 set
        return page_number % self.dram_set_count

    def access_dram_cache(self, page_number):
        replace = False

        set_index = self.find_dram_set(page_number)
        if page_number in self.dram_cache[set_index]:
            # 命中：更新 LRU，将命中的页号移动到末尾（最新）
            way_index = np.where(self.dram_cache[set_index] == page_number)[0][0]
            for idx in range(way_index, 3):
                self.dram_lru[set_index][idx] = self.dram_lru[set_index][idx + 1]
            self.dram_lru[set_index][-1] = way_index
            self.total_hits += 1
            return True, False
        else:
            # 未命中：替换 LRU 页，将其移到末尾（最新）
            way_index = self.dram_lru[set_index][0]
            if self.dram_cache[set_index][way_index] != -1:
                # 只有在替换有效页面时，才计数
                self.page_replacements += 1
                replace = True
            self.dram_cache[set_index][way_index] = page_number
            self.dram_lru[set_index] = np.roll(self.dram_lru[set_index], -1)
            self.dram_lru[set_index][-1] = way_index
            self.total_misses += 1
            return False, replace

    def process_trace_file(self, trace_file):
        local_hits, local_misses, local_replacements = 0, 0, 0

        # 读取整个文件到 NumPy 数组
        data = np.loadtxt(trace_file, usecols=1, dtype='str')
        addrs = np.array([int(addr, 16) >> 12 for addr in data])  # 转换地址为页号并存储到数组
        print("数据读取完毕")

        for addr in addrs:
            if addr in self.cxl_mapping:
                hit, replaced = self.access_dram_cache(addr)
                if hit:
                    local_hits += 1
                else:
                    local_misses += 1
                if replaced:
                    local_replacements += 1

        return local_hits, local_misses, local_replacements

    def simulate_access(self):
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.join(output_dir, 'memory_access_results.csv')

        # 预先写入文件头
        with open(output_file_path, 'w') as out_file:
            out_file.write("Time, Hit Rate, Miss Rate, Replacements, Replace Ratio\n")

        # 获取 trace 文件列表并排序
        trace_files = os.listdir(self.trace_dir)
        trace_files_sorted = sorted(trace_files, key=lambda x: int(re.search(r'(\d+).out$', x).group(1)))

        for trace_file in trace_files_sorted:
            trace_path = os.path.join(self.trace_dir, trace_file)
            if os.path.isfile(trace_path):
                print(f"Processing {trace_file}")
                hits, misses, replacements = self.process_trace_file(trace_path)
                self.total_hits += hits
                self.total_misses += misses
                self.page_replacements += replacements
                hit_ratio = hits / (hits + misses) if hits + misses > 0 else 0
                miss_ratio = misses / (hits + misses) if hits + misses > 0 else 0
                replace_ratio = replacements / (hits + misses)
                print(f"    hit_ratio: {hit_ratio * 100:.2f}%, miss_ratio: {miss_ratio * 100:.2f}%, replaces: {replacements}, replaces_ratio: {replacements * 100 / (hits + misses):.2f}%")

                file_time = trace_file.split('_')[-1].split('.')[0]

                with open(output_file_path, 'a') as out_file:
                    out_file.write(f"{file_time}, {hit_ratio:.2f}, {miss_ratio:.2f}, {replacements}, {replace_ratio}\n")
        
        total_accesses = self.total_hits + self.total_misses
        total_hit_rate = self.total_hits / total_accesses if total_accesses else 0
        total_miss_rate = self.total_misses / total_accesses if total_accesses else 0
        total_replace_rate = self.page_replacements / total_accesses if total_accesses else 0
        
        # 将结果输出到文件
        with open(output_file_path, 'a') as out_file:
            out_file.write(f"Total, {total_hit_rate:.2f}, {total_miss_rate:.2f}, {self.page_replacements}, {total_replace_rate}\n")

        print(f"Total hits: {self.total_hits}, misses: {self.total_misses}, hit rate: {total_hit_rate:.2f}")
        print(f"Total page replacements: {self.page_replacements}")

if __name__ == '__main__':
    os.makedirs(output_dir, exist_ok=True)
    system = HeterogeneousMemorySystem(cxl_layout_file, trace_dir)
    system.simulate_access()
