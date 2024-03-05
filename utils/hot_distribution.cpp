#include <iostream>
#include <fstream>
#include <string>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <filesystem>
#include <sstream>

#define PAGE_SIZE 4096 // 定义虚拟页面大小
const int FILE_PERIOD = 30;   // 每FILE_PERIOD这么多个文件就处理一次

namespace fs = std::filesystem;

unsigned long long addressToPageNumber(const std::string& address) {
    unsigned long long addr = std::stoull(address, nullptr, 16);
    return addr / PAGE_SIZE;
}

void outputDistribution(const std::unordered_map<unsigned long long, unsigned>& pageAccessCount, const std::string& filePrefix, 
    int fileBatchIndex, const std::string& outputDir) {
    // 排序、设置优先级并
    std::vector<std::pair<unsigned long long, unsigned>> pages(pageAccessCount.begin(), pageAccessCount.end());
    std::sort(pages.begin(), pages.end(), [](const auto& a, const auto& b) {
        return a.second > b.second; // 按访问次数比较
    });
    
    size_t total = pages.size();
    for (size_t i = 0; i < total; ++i) {
        double percentile = static_cast<double>(i) / total * 100;
        if (percentile < 5) pages[i].second = 5;
        else if (percentile < 15) pages[i].second = 15;
        else if (percentile < 25) pages[i].second = 25;
        else pages[i].second = 0;
    }

    std::sort(pages.begin(), pages.end(), [](const auto& a, const auto& b) {
        return a.first < b.first;
    });

    std::string outputFileName = outputDir + filePrefix + "_hot_distribution_" + std::to_string(fileBatchIndex) + ".out";
    std::ofstream outputFile(outputFileName);
    outputFile << total << std::endl;
    for (size_t i = 0; i < pages.size(); ++i) {
        if (pages[i].second != 0) {
            outputFile << "0x" << std::hex << pages[i].first << " " << std::dec << pages[i].second << "\n";
        }
    }
    outputFile.close();
}

int main(int argc, char* argv[]) {
    // 确保命令行参数数量正确
    if (argc != 5 || std::string(argv[1]) != "-o") {
        std::cerr << "Usage: " << argv[0] << " -o <output_directory> <directory> <file_prefix>" << std::endl;
        return 1;
    }

    std::string outputDir = argv[2]; // 获取输出目录路径
    std::string dirPath = argv[3]; // 获取目录路径
    std::string filePrefix = argv[4]; // 获取文件前缀

    // 确保输出目录以斜杠结束
    if (!outputDir.empty() && outputDir.back() != fs::path::preferred_separator) {
        outputDir += fs::path::preferred_separator;
    }

    std::unordered_map<unsigned long long, unsigned> pageAccessCount;
    int fileCount = 0;
    int fileBatchIndex = 0; // 用于追踪输出文件的编号

    for (const auto& entry : fs::directory_iterator(dirPath)) {
        std::string filePath = entry.path();
        std::string pattern = "filter";
        if (filePath.find(pattern) != std::string::npos &&
            filePath.find(filePrefix) != std::string::npos) {
            std::ifstream file(filePath);
            std::string line;

            while (getline(file, line)) {
                std::istringstream iss(line);
                char opType;
                std::string address;
                if (iss >> opType >> address) {
                    unsigned long long pageNumber = addressToPageNumber(address);
                    pageAccessCount[pageNumber]++;
                }
            }
            fileCount++;

            // 每30个文件统计一次
            if (fileCount == FILE_PERIOD) {
                std::cerr << "period: " << fileBatchIndex << " process done!" << std::endl;
                outputDistribution(pageAccessCount, filePrefix, fileBatchIndex++, outputDir);
                pageAccessCount.clear(); // 重置页面访问计数器
                fileCount = 0; // 重置文件计数器
            }
        }
    }

    // 处理最后一批不足30个的文件
    if (fileCount > 0) {
        outputDistribution(pageAccessCount, filePrefix, fileBatchIndex, outputDir);
        std::cerr << "period: " << fileBatchIndex << " process done!" << std::endl;
    }

    return 0;
}
