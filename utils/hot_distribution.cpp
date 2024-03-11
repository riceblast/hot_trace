#include <iostream>
#include <fstream>
#include <string>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <filesystem>
#include <sstream>
#include <queue>

/*
 * input file name: benchmark_n.out
 * Read all these files in and get the hot distribution;
 * Count the past 6s page access distribution, and mark the 
 * top 5%, 15%, 25% access freqency pages
 */

#define PAGE_SIZE 4096
//const int FILE_PERIOD = 30000;
//const uint64_t LINENUM_PER_SECOND = 10000000;   // every LINENUM_PER_SECOND line trace coresponding to 1s
const int HOT_WINDOW = 5;   // the count window of hot distribution is HOT_WINDOW seconds
const int SLIDING_STEP = 1;   // every SLIDING_STEP seconds will output hot distribution

namespace fs = std::filesystem;

unsigned long long addressToPageNumber(const std::string& address) {
    unsigned long long addr = std::stoull(address, nullptr, 16);
    return addr / PAGE_SIZE;
}

void outputDistribution(const std::unordered_map<unsigned long long, unsigned>& pageAccessCount, const std::string& filePrefix, 
    int fileBatchIndex, const std::string& outputDir) {
    
    std::vector<std::pair<unsigned long long, unsigned>> pages(pageAccessCount.begin(), pageAccessCount.end());
    std::sort(pages.begin(), pages.end(), [](const auto& a, const auto& b) {
        return a.second > b.second; // compared by access count, Descending
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
        outputFile << "0x" << std::hex << pages[i].first << " " << std::dec << pages[i].second << "\n";
    }
    outputFile.close();
}

int main(int argc, char* argv[]) {
    // mkdir sure the command line has the right number
    if (argc != 5 || std::string(argv[1]) != "-o") {
        std::cerr << "Usage: " << argv[0] << " -o <output_directory> <directory> <file_prefix>" << std::endl;
        return 1;
    }

    std::string outputDir = argv[2]; // get output dir
    std::string dirPath = argv[3]; // get input dir
    std::string filePrefix = argv[4]; // get bench_name/filePrefix

    // make sure the output dir is end with '/'
    if (!outputDir.empty() && outputDir.back() != fs::path::preferred_separator) {
        outputDir += fs::path::preferred_separator;
    }

    std::queue<std::unordered_map<unsigned long long, unsigned>> SlidingPageAccessCounts;
    std::unordered_map<unsigned long long, unsigned> TotalPageAccessCounts;

    int lastFileIdx = -1;    // used to count step
    int fileBatchIndex = 0; // track the index number of output file

    // count the number of target files
    // inputfile: bench_n.out
    int fileTotalCount = 0;
    for (const auto& entry : fs::directory_iterator(dirPath)) {
        std::string filePath = entry.path().filename().string();
        if (filePath.find(filePrefix) == 0) {
            fileTotalCount++;
        }
    }
    std::cerr << "Total files: " << fileTotalCount << std::endl;

    int processedFileCount = 0;
    while (processedFileCount < fileTotalCount) {
        std::string filePath = dirPath + "/" + filePrefix + "_" + 
            std::to_string(processedFileCount) + ".out";
        if (fs::exists(filePath)) {
            std::ifstream file(filePath);
            std::string line;

            processedFileCount++;

            // count page access num for current file
            std::unordered_map<unsigned long long, unsigned> pageAccessCountForCurrentFile;

            // process current file
            while (getline(file, line)) {
                std::istringstream iss(line);
                char opType;
                std::string virtual_address, physical_address;
                if (iss >> opType >> virtual_address >> physical_address) {
                    unsigned long long pageNumber = addressToPageNumber(physical_address);
                    pageAccessCountForCurrentFile[pageNumber]++;
                }
            }

            // if current window is full, remove the oldest file
            if (SlidingPageAccessCounts.size() == HOT_WINDOW) {
                auto& oldestPageAccessCount = SlidingPageAccessCounts.front();
                for (const auto& page : oldestPageAccessCount) {
                    TotalPageAccessCounts[page.first] -= page.second;

                    if (TotalPageAccessCounts[page.first] < 0) {
                        std::cerr << "Error sliding, File: " << filePath << " , PPN: " << page.first << std::endl;
                    }

                    if (TotalPageAccessCounts[page.first] == 0) {
                        TotalPageAccessCounts.erase(page.first);
                    }                    
                }
                SlidingPageAccessCounts.pop();
            }  
            
            // add current file to sidling window
            SlidingPageAccessCounts.push(pageAccessCountForCurrentFile);
            for (const auto& page : pageAccessCountForCurrentFile) {
                TotalPageAccessCounts[page.first] += page.second;
            }

            if (SlidingPageAccessCounts.size() >= HOT_WINDOW &&
                (lastFileIdx == -1 || processedFileCount - lastFileIdx >= SLIDING_STEP)) {
                lastFileIdx = processedFileCount;
                std::cerr << "second: " << processedFileCount << std::endl;
                outputDistribution(TotalPageAccessCounts, filePrefix, fileBatchIndex++, outputDir);
            }
        } else {
            std::cerr << "File: " << filePath << " does not exist" << std::endl;
        }
    }

    return 0;
}
