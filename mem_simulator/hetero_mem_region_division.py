import matplotlib.pyplot as plt
import sys
import argparse
import os
import math
import re
import numpy as np
import pandas as pd

parser = argparse.ArgumentParser(description='Simulate the Heterogenous Memory Artichecture')
parser.add_argument('--dram_size', type = int , help = "specify the dram size manually(MB")
parser.add_argument('--type', choices=['v', 'p'], default='v', help='Trace type: virtual addr(v)/physical addr(p)')
parser.add_argument('benchname', help='Target benchmark trace used to get page difference')

args = parser.parse_args()
benchname = args.benchname

cxl_layout_file = "/home/yangxr/downloads/test_trace/compact_addr_space/compute/" + benchname + "/" + benchname
trace_dir = "/home/yangxr/downloads/test_trace/raw_data/compute/" + benchname + "/"
output_dir = "/home/yangxr/downloads/test_trace/res/compute/" + benchname + "/simulate/" 
if (args.type == 'v'):
    cxl_layout_file += ".vout"
elif (args.type == 'p'):
    cxl_layout_file += ".pout"

NUM_REGIONS = 512

# Learned Index映射的seg
class MappingSeg:
    # (a*x + b) % m
    def __init__(self, a, b, m):
        self.a = a
        self.b = b
        self.m = m

# CXL region内的sub region,映射到DRAM region
class SubRegionMapping:
    # 左闭右开
    def __init__(self, start, end, dram_region_idx, mapping_seg):
        self.start = start
        self.end = end
        self.dram_region_idx = dram_region_idx
        self.mapping_seg = mapping_seg

    def mapping_func(self, page_number):
        return (int(self.mapping_seg.a * page_number + self.mapping_seg.b)) % self.mapping_seg.m

# CXL region级别的映射
class RegionMapping:
    def __init__(self):
        self.subregions = []

    def add_subregion(self, start, end, dram_region_idx, mapping_seg):
        self.subregions.append(SubRegionMapping(start, end, dram_region_idx, mapping_seg))

class HeterogeneousMemorySystem:
    def __init__(self, cxl_layout_file, trace_dir):
        # 初始化 CXL Memory
        self.initialize_cxl(cxl_layout_file)
        self.capacity_ratio = 1
        self.cxl_regions = [RegionMapping() for _ in range(NUM_REGIONS)]
        self.cxl_region_size = self.cxl_capacity // NUM_REGIONS
        
        # 计算 DRAM 容量，初始化 DRAM cache
        if (args.dram_size is not None):
            dram_page_number = args.dram_size * 1024 // 4
            self.capacity_ratio = math.floor(self.cxl_capacity / dram_page_number)
            self.dram_capacity = ((self.cxl_capacity // self.capacity_ratio + 4095) // 4096) * 4096
        else:
            self.capacity_ratio = 8
            self.dram_capacity = ((self.cxl_capacity // self.capacity_ratio + 4095) // 4096) * 4096

        self.dram_cache = np.full((self.dram_capacity), -1, dtype=int)  # -1 表示空位
        self.dram_saturating = np.zeros((self.dram_capacity), dtype=int)  # 饱和计数器，3位，初始化为4
        self.dram_regions = [-1] * NUM_REGIONS  # 模拟简单 DRAM 缓存，初始化为未使用状态，这是一个反向映射表DRAM region -> CXL region idx
        self.dram_region_size = (self.dram_capacity // NUM_REGIONS)
        self.trace_dir = trace_dir
        
        # 初始化统计数据
        self.page_replacements = 0  # 用于统计页面替换的次数
        self.total_hits = 0
        self.total_misses = 0

        # 初始化Learned Index
        self.init_learned_index()

        print(f"DRAM Size: {self.dram_capacity * 4 // 1024}(MB), CXL Size: {self.cxl_capacity * 4 // 1024}(MB)")
    
    def initialize_cxl(self, cxl_layout_file):
        with open(cxl_layout_file, 'r') as f:
            first_line = int(f.readline().strip())
            # 找到第一个大于等于 first_line 且能被 4096 整除的值作为 CXL 容量
            self.cxl_capacity = ((first_line + 4095) // 4096) * 4096
            self.cxl_mapping = {}
            for line in f:
                index, page_number = line.strip().split()[:2]
                page_number = int(page_number, 16)
                index = int(index)
                if (page_number in self.cxl_mapping):
                    print(f"Err: addr {page_number} already in cxl_mapping list, benchmark: {benchname}")
                    exit(1)
                self.cxl_mapping[page_number] = index

    def init_learned_index(self):
        seg = MappingSeg(1 / self.capacity_ratio, 0, 1)
        for region_idx in range(0, NUM_REGIONS):
            self.cxl_regions[region_idx].add_subregion(region_idx * self.cxl_region_size, (region_idx + 1) * self.cxl_region_size,
                region_idx, seg)

    def find_dram_addr(self, page_number):
        # 判断addr对应的CXL region
        cxl_region_idx = page_number // self.cxl_region_size
        if len(self.cxl_regions[cxl_region_idx].subregions) == 0:
            return -1
        
        sub_region_idx = 0
        for sub_region in self.cxl_regions[cxl_region_idx].subregions:
            if (page_number >= sub_region.start and page_number < sub_region.end):
                break
            sub_region_idx += 1
        
        target_dram_addr = self.cxl_regions[cxl_region_idx].subregions[sub_region_idx].mapping_func(page_number)

        # 根据页号找到应该放置的 set
        return target_dram_addr

    # 处理cache hit的函数
    def cache_hit(self, target_dram_addr, page_number):
        if self.dram_saturating[target_dram_addr] < 8:
            self.dram_saturating[target_dram_addr] += 1

        self.total_hits += 1

    def cache_miss(self, target_dram_addr, page_number):
        replace = False

        if (self.dram_saturating[target_dram_addr] == 0 or self.dram_saturating[target_dram_addr] == 1):
            self.dram_cache[target_dram_addr] = page_number
            self.dram_saturating[target_dram_addr] = 4
            replace = True
        else:
            self.dram_saturating[target_dram_addr] -= 1

        self.total_misses += 1
        return replace

    def is_hit(self, page_number):
        target_dram_addr = self.find_dram_addr(page_number)
        if (target_dram_addr == -1):
            return False
        if (self.dram_cache[target_dram_addr] != page_number):
            return False
        
        return True

    def access_dram_cache(self, page_number):
        replace = False
        
        if self.is_hit(page_number):
            self.cache_hit(self.find_dram_addr(page_number), page_number)
            return True, False
        else:
            replace = self.cache_miss(self.find_dram_addr(page_number), page_number)
            return False, replace

    def process_trace_file(self, trace_file):
        local_hits, local_misses, local_replacements = 0, 0, 0

        # 读取整个文件到 NumPy 数组
        data = np.loadtxt(trace_file, usecols=1, dtype='str')
        addrs = np.array([int(addr, 16) >> 12 for addr in data])  # 转换地址为页号并存储到数组
        print("数据读取完毕")

        for addr in addrs:
            if addr in self.cxl_mapping:
                hit, replaced = self.access_dram_cache(self.cxl_mapping[addr])
                if hit:
                    local_hits += 1
                else:
                    local_misses += 1
                if replaced:
                    local_replacements += 1
            else:
                print(f"Err: addr {addr} fault")

        return local_hits, local_misses, local_replacements

    def simulate_access(self):
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f'region_devision_{self.dram_capacity * 4 // 1024}MB.csv'
        output_file_path = os.path.join(output_dir, output_filename)

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
