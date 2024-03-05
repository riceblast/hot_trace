#include <iostream>
#include <fstream>
#include <string>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <filesystem>
#include <sstream>

#define PAGE_SIZE 4096 // 定义虚拟页面大小

namespace fs = std::filesystem;

// 将十六进制地址字符串转换为虚拟页号
unsigned long long addressToPageNumber(const std::string& address) {
    unsigned long long addr = std::stoull(address, nullptr, 16);
    return addr / PAGE_SIZE;
}

// 主函数，现在接受命令行参数
int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: " << argv[0] << " <directory> <file_prefix>" << std::endl;
        return 1;
    }

    // /home/yangxr/projects/learned_dram/hot_dist/hot_trace/trace/mcf.in
    std::string dirPath = argv[1]; // 从命令行获取目录路径
    std::string filePrefix = argv[2]; // 从命令行获取文件前缀

    std::unordered_map<unsigned long long, unsigned> pageAccessCount; // 存储每个页面的访问次数

    // 遍历指定目录中的所有文件
    std::cout << "start process input file" << std::endl;
    for (const auto& entry : fs::directory_iterator(dirPath)) {
        std::string filePath = entry.path();
        //std::cout << "filePath: " << filePath << std::endl;
        // 构建搜索模式
        //std::string pattern = filePrefix + "*.filter.trace";
        std::string pattern = "filter";
        //std::cout << "patter: " << pattern << std::endl;
        // 检查文件名是否匹配模式
        if (filePath.find(pattern) != std::string::npos &&
            filePath.find(filePrefix) != std::string::npos) {
            std::ifstream file(filePath);
            std::string line;

            // 读取文件中的每一行
            std::cout << filePath << std::endl;
            while (getline(file, line)) {
                std::istringstream iss(line);
                char opType;
                std::string address;
                if (iss >> opType >> address) { // 分析操作类型和地址
                    unsigned long long pageNumber = addressToPageNumber(address);
                    pageAccessCount[pageNumber]++; // 更新访问次数
                }
            }
        }
    }

    // 将unordered_map转换为vector，并准备按访问次数排序
    std::cout << "convert to vector" << std::endl;
    std::vector<std::pair<unsigned long long, unsigned>> pages(pageAccessCount.begin(), pageAccessCount.end());

    // 按访问次数（频率）对pages进行降序排序
    std::cout << "sort by frequency" << std::endl;
    std::sort(pages.begin(), pages.end(), [](const auto& a, const auto& b) {
        return a.second > b.second; // 按访问次数比较
    });

    // // 创建一个单独的数组来存储访存级别
    // std::vector<unsigned> accessLevels(pages.size(), 0);

    // 遍历pages，根据位置判断访存次数级别
    size_t total = pages.size();
    for (size_t i = 0; i < total; ++i) {
        // 根据百分比位置判断访存次数级别
        double percentile = static_cast<double>(i) / total * 100;
        if (percentile < 5) pages[i].second = 5;
        //else if (percentile < 10) pages[i].second = 10;
        else if (percentile < 15) pages[i].second = 15;
        //else if (percentile < 20) pages[i].second = 20;
        else if (percentile < 25) pages[i].second = 25;
        else pages[i].second = 0;
    }

    // 按页面号重新对pages进行升序排序
    std::cout << "sort by page num" << std::endl;
    std::sort(pages.begin(), pages.end(), [](const auto& a, const auto& b) {
        return a.first < b.first;
    });

    // 输出到文件
    std::cout << "output to file" << std::endl;
    std::string outputFileName = filePrefix + "_hot_distribution.out";
    std::ofstream outputFile(outputFileName);
    outputFile << total << std::endl; // 输出页面总数
    for (size_t i = 0; i < pages.size(); ++i) {
        // 只输出非0的访存级别
        if (pages[i].second != 0) {
            outputFile << "0x" << std::hex << i << " " << std::dec << pages[i].second << "\n";
        }
    }

    return 0;
}