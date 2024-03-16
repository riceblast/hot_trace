# 统计输入的<虚拟页号，物理页号>，并画出逆CDF图
#
# [Usage]: python3 plot_reverse_cdf.py benchname start end 
#   benchname : benchmark的名称，如BFS、PR
#   start     : 所选择的测试用例的起始编号
#   end       : 所选择的测试用例的末尾编号      
#
# [output]:
#   图像 ../res/{benchname}/{benchname}_from_{start}_to_{end}_reverse_cdf.png
#
# 注：地址为硬编码，如有修改需要一并改动！

import matplotlib.pyplot as plt
from collections import Counter
import sys
import numpy as np

PAGE_SIZE = 4096
output_dir = "../res"
trace_dir = "../test_trace/raw_data"

# 读取文件并统计VPA PPA出现的次数
# VPA, PPA 需要除以 PAGE_SIZE 以计算页号
def count_vpa_ppa(benchname, start, end):
    vpa_ppa_counter = Counter()
    start, end = int(start), int(end)

    for num in range(start, end + 1):
        # e.g ../test_trace/BFS/BFS_5.out
        filename = trace_dir + '/' + benchname + '/' + benchname + '_' + str(num) + '.out'
        with open(filename, 'r') as file:
            for line in file:
                if line[0] == 'R' or line[0] == 'W':
                    _, vpa, ppa = line.strip().split()
                    v = int(vpa, 16) // PAGE_SIZE
                    p = int(ppa, 16) // PAGE_SIZE
                    vpa_ppa_counter[(v, p)] += 1
            print("DEBUG: Successfully read Addr from file ", filename)

    return vpa_ppa_counter

# 画出逆累积分布函数并保存图像
def plot_inverse_cdf(counter, prefix, benchname):
    counts = np.array(sorted(counter.values(), reverse=True))
    total = counts.sum()
    # numpy.cumsum 计算累计和
    cdf = np.cumsum(counts) / total
    inverse_cdf = 1 - cdf

    plt.plot(range(1, len(inverse_cdf) + 1), inverse_cdf)
    plt.xlabel('Rank')
    plt.ylabel('Inverse Cumulative Probability')
    plt.title('Inverse Cumulative Distribution Function')
    # e.g ../res/BFS/BFS_from_15_to_20_reverse_cdf.png
    plt.savefig(output_dir + '/' + benchname + '/' + prefix + '.png')
    plt.show()

if __name__ == "__main__":
    benchname, start, end = sys.argv[1], sys.argv[2], sys.argv[3] 
    counter = count_vpa_ppa(benchname, start, end)
    prefix = benchname + "_from_" + start + "_to_" + end + "_reverse_cdf"
    plot_inverse_cdf(counter, prefix, benchname)
