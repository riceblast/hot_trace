# 1. 用一个页间距threshold将热页划分成一个个区域（threshold按照经验取10）
# 2. 遍历：
#       对当前区域求解LR
#       判断每个点是否在误差范围内
#           有不在的点
#               如果当前threshold小于某值，将该页面区域标记为“DirectMap”，即直接映射
#               如果当前threshold大于某值，进行二次划分并重复上述遍历流程
#           全部在误差范围内
#               将该区域标记为“Linear Regression”，即线性映射
#
# 输出: 1个错误集和一个综合集（就在当前目录下）
#   错误集. BFS_15.learned_dram.out    形如"DRAM ADDR, Conflict Count/Zero"
#   综合集. BFS_15.learned_seg.out     形如"Start, End, K, B"
#


import numpy as np

global_threshold = 16
global_models = []
global_start_index = 0

class Model:
    def __init__(self, start_index, length, k, b, is_lr):
        self.start_index = start_index
        self.length = length
        self.k = k
        self.b = b
        self.is_lr = is_lr


# 求解线性回归（返回的应该是一个1维参数？）
# 返回值 param (b, k)
def linear_regression(X, y):
    # 直接返回
    if len(X) == 1:
        return np.array([0, 1])
    # 在X的第一列添加偏置项
    X_with_bias = np.c_[np.ones(X.shape[0]), X]

    # 使用正规方程求解线性回归参数
    param = np.linalg.inv(X_with_bias.T.dot(X_with_bias)).dot(X_with_bias.T).dot(y)
    return param

# 将地址按照threshold划分
def divide_with_threshold(data, threshold):
    result = [[data[0]]]
    for i in range(len(data) - 1):
        prev, curr = data[i], data[i + 1]
        if curr - prev > threshold:
            result.append([curr])
        else:
            result[-1].append(curr)
    return result


def traverse_and_train(list, threshold):
    global global_start_index

    divided_list = divide_with_threshold(list, threshold)
    for sublist in divided_list:
        param, res = train_and_test(sublist)
        if res == True:
            global_models.append(Model(global_start_index, len(sublist), param[1], param[0], True))
            global_start_index += len(sublist)
        elif threshold >= 4: # 最小分割阈值为2
            traverse_and_train(sublist, threshold // 2)
        else:
            global_models.append(Model(global_start_index, len(sublist), None, None, False))
            global_start_index += len(sublist)


# 求解线性回归，并测试模型是否在容错范围内
# 返回值: (theta, flag) 
#   theta是模型参数：theta[0]代表截距，theta[1]代表斜率
#   flag是bool类型变量，代表当前模型能否正常工作（即是否所有点的预测都在容错范围内）
def train_and_test(list):
    # 模型简化：用更简单的x和y来训练
    X = np.array(list) - list[0] + 1
    Y = np.array(range(1, len(X) + 1))
    theta = linear_regression(X, Y)
    for i in range(len(X)):
        x, y = X[i], Y[i]
        y_hat = round(x * theta[1] + theta[0])
        if abs(y_hat - y) > 1: # err_bound: ±1
            return None, False
    return theta, True


def write_seg_to_file(filename):
    global global_models
    directMapCnt = 0
    linearRegressionCnt = 0
    singlePointCnt = 0
    with open(filename, 'w') as file:
        file.write("StartIndex  Length  Slope   Intercept\n")
        for model in global_models:
            if model.is_lr == True:
                if model.length == 1:
                    singlePointCnt += 1
                    file.write("%-11d %-7d\n" % (model.start_index, model.length))
                else:
                    linearRegressionCnt += 1
                    file.write("%-11d %-7d %.4f  %.4f\n" % (model.start_index, model.length, model.k, model.b))
            else:
                directMapCnt += 1
                file.write("%-11d %-7d\n" % (model.start_index, model.length))
        file.write("Total: %d\n\tLinear Regression: %d\n\tSingle Point: %d\n\tDirect Map: %d\n" % (linearRegressionCnt \
                + directMapCnt + singlePointCnt, linearRegressionCnt, singlePointCnt, directMapCnt))


def write_dram_to_file(filename, data):
    global global_models
    simDram = np.zeros(len(data))
    for model in global_models:
        if model.is_lr == True:
            for i in range(1, model.length + 1):
                pos = model.start_index + i - 1
                i_hat = data[pos] - data[model.start_index] + 1
                y_hat = model.start_index + round(model.k * i_hat + model.b) - 1
                simDram[y_hat] += 1
        else:
            for i in range(1, model.length + 1):
                simDram[model.start_index + i - 1] += 1
    with open(filename, 'w') as file:
        file.write("Addr       ConflictCount\n")
        for i in range(len(simDram)):
            if simDram[i] != 1:
                file.write("%#x   %-9d\n" % (int(data[i]), simDram[i]))


filename = '../test_trace/hot_dist_5_15/BFS/BFS_15.hot_5_15.out'
conv = lambda a: int(a, 16)
data = np.loadtxt(filename, converters={0: conv})
traverse_and_train(data, threshold=global_threshold)
write_seg_to_file("BFS_15.learned_seg.out")
write_dram_to_file("BFS_15.learned_dram.out", data)
