# 统计相邻物理热页的地址差值，并画图
#
# [Usage]: python3 plot_pa_difference.py benchname num 
#   benchname : benchmark的名称，如BFS、PR
#   num       : 所选择的具体测试用例，为一个具体数字
# 注：最终所使用的测试用例为 ../hot_trace/test_trace/hot_dist_5_15/{benchname}/{benchname}_{num}.hot_5_15.out
#
# [output]:
#   图像 ../res/{benchname}/{benchname}_{num}_hot_5_15_pa_diff_ln.png
#   差值 ../res/{benchname}/{benchname}_{num}_hot_5_15_pa_diff.out
#
# 注：地址为硬编码，如有修改需要一并改动！

import matplotlib.pyplot as plt
import sys
import numpy as np

output_dir = "../res"
trace_dir = "../test_trace/hot_dist_5_15"
mediate_path = "/P/5_15/"

# 读取文件并排序、去重
def read_and_sort(benchname, num):
    page_aligned_pas = set()
    # e.g ../test_trace/hot_dist_5_15/BFS/BFS_20.hot_5_15.out
    filename = trace_dir + '/' + benchname + '/' + benchname + '_' + num + '.hot_5_15.out'
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

# 画出差值图像，对值作自然对数处理(ln)
def plot_differences(differences, prefix):
    plt.plot(range(1, len(differences) + 1), np.log2(differences), linewidth=0.05)
    plt.xlabel('Index')
    plt.ylabel('Difference')
    plt.title('Differences between Adjacent Physical Pages')
    plt.grid(True, which="both", ls="--")  # 添加网格线

    plt.savefig(output_dir + '/' + benchname + mediate_path + prefix + "_log2.png")
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


if __name__ == "__main__":
    benchname, num = sys.argv[1], sys.argv[2]
    pa_list = read_and_sort(benchname, num)
    differences = calculate_differences(pa_list)
    prefix = benchname + '_' + num + '_hot_5_15_pa_diff'
    # 将差值结果保存
    np.savetxt(output_dir + '/' + benchname + mediate_path + prefix + '.out', differences, fmt='%d')
    # 根据差值信息，画图并保存
    plot_differences(differences, prefix)

    plot_calculate(differences)
