import matplotlib.pyplot as plt
import numpy as np
import os
import argparse

# 解析命令行参数
parser = argparse.ArgumentParser(description="Generate a heatmap from multiple files.")
parser.add_argument('-d', '--input_dir', required=True, help="Directory containing input files")
parser.add_argument('-p', '--file_prefix', required=True, help="Prefix of input files")
parser.add_argument('-o', '--output_dir', required=True, help="Directory to save the output plot")
parser.add_argument('-n', '--numbers', required=True, type=int, help="Last of file numbers to process")
parser.add_argument('-f', '--frequency', required=True, type=int, nargs='+', help="Target plot frequency, e.g.: 5 15")

args = parser.parse_args()

target_freq = args.frequency
lineWidth=0.1

# 读取所有文件中的地址并去重
unique_addresses = set()
for n in range(args.numbers + 1):
    file_path = os.path.join(args.input_dir, f"{args.file_prefix}_hot_distribution_{n}.out")
    with open(file_path, 'r') as file:
        next(file)  # 跳过第一行
        for line in file:
            address, _ = line.strip().split()
            unique_addresses.add(int(address, 16))

# 地址排序并建立索引映射
sorted_addresses = sorted(unique_addresses)
address_to_index = {addr: idx for idx, addr in enumerate(sorted_addresses)}
if (len(address_to_index) > 200000):
    lineWidth=0.01

# 初始化绘图
plt.figure(figsize=(10, 6), dpi=141)
color = '#D11A2D'

# 处理每个文件并绘制
for n in range(args.numbers + 1):
    file_path = os.path.join(args.input_dir, f"{args.file_prefix}_hot_distribution_{n}.out")
    with open(file_path, 'r') as file:
        next(file)  # 跳过第一行
        for line in file:
            address, frequency = line.strip().split()
            frequency = int(frequency)
            if frequency in target_freq:
                address = int(address, 16)
                idx = address_to_index[address]
                plt.hlines(y=idx, xmin=n-0.5, xmax=n+0.5, color=color, linewidth=lineWidth)

# 设置图表的标题和轴标签
plt.title('Heatmap of Page Access Frequency over Time')
plt.xlabel('Time(s)')
plt.ylabel('Address')
#plt.yticks(ticks=np.arange(len(sorted_addresses)), labels=[hex(addr) for addr in sorted_addresses])
plt.yticks(range(0, len(sorted_addresses), len(sorted_addresses) // 15), \
    [hex(y) for y in range(0, len(sorted_addresses), len(sorted_addresses) // 15)])

tick_positions = range(args.numbers + 1)
tick_labels = [str(x/2 + 0.5) for x in tick_positions]  # 显示的刻度标签，每个刻度除以2
plt.xticks(ticks=tick_positions, labels=tick_labels)
#plt.xticks(ticks=np.arange(0.5, args.numbers + 1.5, 1))  # 从0.5开始，每隔1单位设置刻度


# 保存绘图
plt.tight_layout()
frequency_suffix = '_'.join(map(str, args.frequency))  # 将频率值转换为字符串并用下划线连接
save_path = os.path.join(args.output_dir, f"{args.file_prefix}_hot_dist_over_time_{frequency_suffix}.png")
plt.savefig(save_path)
plt.close()
