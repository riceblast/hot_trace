import matplotlib.pyplot as plt

def read_and_sort_data(filename):
    # 读取数据
    with open(filename, 'r') as file:
        data = file.readlines()

    # 解析并排序数据
    data_parsed = [(int(line.split()[0], 16), int(line.split()[1])) for line in data]
    data_sorted = sorted(data_parsed, key=lambda x: x[0])

    return data_sorted

def plot_data(data_sorted, output_filename):
    # 确定y轴的最大值
    y_max = max(addr for addr, value in data_sorted)

    # 设置图形大小
    plt.figure(figsize=(10, 6), dpi=141)

    # 遍历数据并绘制
    for addr, value in data_sorted:
        if value == 0:
            # 如果值等于0，用蓝色绘制横线
            plt.hlines(y=addr, xmin=0, xmax=1, colors='blue', linestyles='solid', linewidth=0.5)
        elif value > 1:
            # 如果值大于1，用红色绘制横线
            plt.hlines(y=addr, xmin=0, xmax=1, colors='red', linestyles='solid', linewidth=0.5)

    # 设置y轴的范围
    #plt.ylim(0, y_max)
    plt.yticks(range(0, data_sorted[-1][0], data_sorted[-1][0] // 15), \
        [hex(y) for y in range(0, data_sorted[-1][0], data_sorted[-1][0] // 15)])
    plt.xticks([])

    # 设置图形的标题和坐标轴标签
    plt.title('The Application of Learned Index on DRAM')
    plt.xlabel('DRAM')
    plt.ylabel('Address (Hex)')

    # 显示图形
    #plt.show()

    # 保存图形到文件
    plt.savefig(output_filename)

if __name__ == '__main__':
    filename = 'BFS_15.learned_dram.out'
    output_filename = 'BFS_15.learned_dram.png'
    data_sorted = read_and_sort_data(filename)
    plot_data(data_sorted, output_filename)
