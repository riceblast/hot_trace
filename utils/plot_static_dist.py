import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap, Normalize
import matplotlib.cm as cm
import os

# 输入变量定义
input_dir = './hot_dist/mcf/'  # 文件夹路径
filePrefix = '20s'  # 文件前缀
numbers = [0,1]  # 文件中数字数组

# 初始化数据容器
data = {}

# 读取并处理多个文件
for n in numbers:
    file_path = f'{input_dir}{filePrefix}_hot_distribution_{n}.out'
    with open(file_path, 'r') as file:
        next(file)  # 跳过第一行
        for line in file:
            address, frequency = line.strip().split()
            #address = int(address, 16)
            frequency = int(frequency)
            if address not in data or \
                (data[address] != 0 and frequency < data[address] and frequency != 0) \
                or (data[address] == 0 and frequency != 0):
                data[address] = frequency

# 将数据转换为按地址排序的列表
sorted_data = sorted(data.items(), key=lambda x: int(x[0], 16))

# 绘图
plt.figure(figsize=(10, 6), dpi=100)
ax = plt.gca()  # 获取当前轴的引用

colors = ['#F7DC6F', '#F39C12', '#d11a2d']  # 颜色映射: 淡黄，橘黄，深红
cmap = ListedColormap(colors)
frequency_to_color = {5: 2, 15: 1, 25: 0}

# 计算地址空间范围
address_space = len(sorted_data)

idx = 0
for address, frequency in sorted_data:
    if frequency != 0:
        color_idx = frequency_to_color.get(frequency, 0)  # 获取颜色索引
        plt.hlines(y=idx, xmin=0, xmax=1, colors=cmap.colors[color_idx], linewidth=0.1)
    idx += 1

plt.title('Heatmap of Page Access Distribution')
plt.ylabel('Address (Hex)')
plt.ylim(0, address_space)
plt.xticks([])  # 移除x轴的标签

y_ticks = np.arange(0, address_space, address_space // 20)
plt.yticks(y_ticks, [hex(y) for y in y_ticks])

norm = Normalize(vmin=0, vmax=2)
sm = cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cb = plt.colorbar(sm, ticks=[5/3, 1, 1/3], ax=ax)
cb.set_ticklabels(['5%', '15%', '25%'])
cb.set_label('Access Frequency')

plt.show()

