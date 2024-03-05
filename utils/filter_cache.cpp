#include <iostream>
#include <fstream>
#include <unordered_map>
#include <list>
#include <string>
#include <string.h>
#include <cassert>
#include <vector>

// cache per core: 2.5MB
// simulation: 2048 sets, 20ways
#define SETS 2048 // Number of cache sets
#define WAYS 20   // Number of ways per set
#define CACHE_LINE_SIZE 64 // Size of a cache line in bytes
#define PAGE_SIZE 4096 // Size of a virtual page in bytes
//#define LRU_CACHE_SIZE 66048 // Number of cache lines to track
#define LRU_CACHE_SIZE 45000 // Number of cache lines to track

// Use std::pair to store cache set number and its iterator within a list
using CacheLineInfo = std::pair<unsigned long long, std::list<unsigned long long>::iterator>;

// Cache structure
std::vector<std::list<unsigned long long>> cacheSets(SETS);
std::unordered_map<unsigned long long, CacheLineInfo> cacheMap; // cacheline_num -> (set_index, iterator)

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

// Function to map an address to a specific set index
unsigned long long addressToSetIndex(const std::string& address) {
    unsigned long long cacheLine = addressToCacheLine(address);
    return cacheLine % SETS;
}

int main(int argc, char* argv[]) {
    std::string outDir;
    std::string inputFileName;

    // check the num of params, at least for 4 params
    if (argc != 4) {
        std::cerr << "Usage: " << argv[0] << " -o <outdir> <input_file_name>\n";
        return 1;
    }

    // analyse the comand parameters
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "-o") == 0) { 
            if (i + 1 < argc) { 
                outDir = argv[i + 1]; 
                ++i;
            } else {
                std::cerr << "Missing argument for -o\n";
                return 1;
            }
        } else {
            inputFileName = argv[i];
        }
    }

    // ensure the inputfile is not empty
    if (inputFileName.empty()) {
        std::cerr << "Input file name is required.\n";
        return 1;
    }

    // get output file path & name
    std::string baseFileName = inputFileName;

    // get rid of ".raw.trace"
    size_t pos = inputFileName.rfind(".raw.trace");
    if (pos != std::string::npos)  
        baseFileName = inputFileName.substr(0, pos);
    // get the pure filename
    pos = baseFileName.find_last_of("/");
    if (pos != std::string::npos)
        baseFileName = baseFileName.substr(pos + 1);

    std::string outputFileName = outDir + "/" + baseFileName + ".filter.trace"; // 生成输出文件名
    std::ofstream outputFile(outputFileName); // 打开输出文件

    if (!outputFile.is_open()) {
        std::cerr << "Error opening file: " << outputFileName << std::endl;
        return 1;
    }

    // Process each line of the file
    std::string line;
    std::ifstream inputFile(inputFileName);
    while (getline(inputFile, line)) {
        if (line.empty()) continue; // Skip empty lines

        char opType = line[0]; // Operation type: 'r' or 'w'
        std::string address = line.substr(2); // Hexadecimal address as string

        unsigned long long cacheLine = addressToCacheLine(address);
        unsigned long long setIndex = addressToSetIndex(address);
        auto& set = cacheSets[setIndex];

        // Check if the cache line is already in the set
        if (cacheMap.find(cacheLine) != cacheMap.end()) {
            // If it exists, move it to the front of the LRU list
            set.erase(cacheMap[cacheLine].second);
            set.push_front(cacheLine);
            cacheMap[cacheLine] = {setIndex, set.begin()};
        } else {
            // If the cache line is not in the cache
            if (set.size() == WAYS) {
                // If the set is full, remove the least recently used cache line
                auto lastElem = set.back();
                cacheMap.erase(lastElem);
                set.pop_back();
            }
            // Add the new cache line to the front of the LRU list
            set.push_front(cacheLine);
            cacheMap[cacheLine] = {setIndex, set.begin()};

            outputFile  << opType << " " << address << "\n";
        }
    }

    outputFile.close();

    return 0;
}
