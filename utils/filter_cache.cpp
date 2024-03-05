#include <iostream>
#include <fstream>
#include <unordered_map>
#include <list>
#include <string>
#include <cassert>

#define CACHE_LINE_SIZE 64 // Size of a cache line in bytes
#define PAGE_SIZE 4096 // Size of a virtual page in bytes
//#define LRU_CACHE_SIZE 66048 // Number of cache lines to track
#define LRU_CACHE_SIZE 45000 // Number of cache lines to track

// Converts a hexadecimal address string to a virtual page number
unsigned long long addressToPageNumber(const std::string& address) {
    unsigned long long addr = std::stoull(address, nullptr, 16);
    return addr / PAGE_SIZE;
}

// Converts a hexadecimal address string to a cache line number
unsigned long long addressToCacheLine(const std::string& address) {
    unsigned long long addr = std::stoull(address, nullptr, 16);
    return addr / CACHE_LINE_SIZE;
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <input_file_name>\n";
        return 1;
    }

    std::ifstream inputFile(argv[1]);
    if (!inputFile.is_open()) {
        std::cerr << "Error opening file: " << argv[1] << std::endl;
        return 1;
    }

    std::string inputFileName(argv[1]);
    std::string baseFileName = inputFileName.substr(0, inputFileName.find_last_of('.')); // 从输入文件名中去掉扩展名
    std::string outputFileName = baseFileName + ".filter.trace"; // 生成输出文件名
    std::ofstream outputFile(outputFileName); // 打开输出文件
    //std::ofstream outputFile("output.txt");
    if (!outputFile.is_open()) {
        std::cerr << "Error opening file: output.txt" << std::endl;
        return 1;
    }

    std::string line;
    std::list<unsigned long long> lruCache; // LRU cache for cache lines
    std::unordered_map<unsigned long long, std::list<unsigned long long>::iterator> cacheMap; // Maps cache line to its position in LRU

    // Process each line of the file
    while (getline(inputFile, line)) {
        if (line.empty()) continue; // Skip empty lines

        char opType = line[0]; // Operation type: 'r' or 'w'
        std::string address = line.substr(2); // Hexadecimal address as string

        unsigned long long cacheLine = addressToCacheLine(address);

        // Check if cache line is already in LRU cache
        if (cacheMap.find(cacheLine) != cacheMap.end()) {
            // Move the cache line to the front of the LRU cache
            lruCache.erase(cacheMap[cacheLine]);
            lruCache.push_front(cacheLine);
            cacheMap[cacheLine] = lruCache.begin();
        } else {
            // If cache line is not in cache and cache is full, remove the least recently used cache line
            if (lruCache.size() == LRU_CACHE_SIZE) {
                cacheMap.erase(lruCache.back());
                lruCache.pop_back();
            }
            // Insert the new cache line at the front of the LRU cache
            lruCache.push_front(cacheLine);
            cacheMap[cacheLine] = lruCache.begin();

            // Convert address to virtual page number and output
            //outputFile  << opType << " 0x" << addressToPageNumber(address) << std::endl;
            // outputFile  << opType << " " << address << std::endl;
            outputFile  << opType << " " << address << "\n";
        }
    }

    outputFile.close();

    return 0;
}
