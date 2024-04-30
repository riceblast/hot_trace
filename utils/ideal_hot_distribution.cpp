#include <iostream>
#include <fstream>
#include <string>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <filesystem>
#include <sstream>
#include <queue>
#include <cassert>
#include <unistd.h>
#include <getopt.h>
#include <string.h>
#include <error.h>
#include <sys/stat.h>
#include <sys/types.h>

/*
 * 简介：
 * 该文件负责生成热页分布系列文件,
 * 不需要利用历史预测未来, 直接利用"未来"的数据生成当前的热页分布,
 * 由于使用了未来的数据, 因此该算法是"ideal"的
*/

#define PAGE_SIZE 4096
char addr_type = 'v';    // 处理的地址类型: v/p
int skip_time = 0; // 是否跳过开头几秒以避免影响
int period_idx = 0; // 用于索引periods数组
int time_period = 1;   // 多久进行一次页面迁移/当前时刻的热页来自未来 PERIOD 秒
int trace_num = 0; // 所有trace文件的数量
uint64_t dram_cap_pn = 0;  // DRAM能够存储的页数
uint64_t addr_space_range = 0;  // 最大的地址空间范围
const int DRAM_RATIO = 10; // DRAM 容量为 benchmark稳定WSS的10%

std::string benchname;
std::string input_dir = "/home/yangxr/downloads/test_trace/raw_data/ideal";
//std::string input_dir = "/home/yangxr/downloads/test_trace/tmp";
std::string output_dir;
std::string global_output_dir;

std::vector<int> periods;   // 记录想要所有输出的period序列，形如：1,2,3,4,5
std::vector<std::unordered_map<uint64_t, uint64_t>*> traces; // 处理所有raw_data读入的trace，pn -> access_freq
std::vector<std::unordered_map<uint64_t, uint64_t>*> period_traces; // 按照time_period处理traces，pn -> access_freq

namespace fs = std::filesystem;

void split_period(char* optarg) {
    const char dlim[2] = ",";
    char* token = strtok(optarg, dlim);

    while (token != NULL) {
        int p = 1;
        try {
            p = std::stoull(token, nullptr);
            printf("period: %d\n", p);
        } catch(const std::invalid_argument& ia) {
            std::cerr << "Invalid argument exception when calling stoull" << std::endl;
            std::cerr << "Invalid argument: " << token << std::endl;
            exit(1);
        } catch (const std::out_of_range& oor) {
            std::cerr << "The number is out of range" << std::endl;
            std::cerr << "Out range number: " << token << std::endl;
            exit(1);
        }

        periods.push_back(p);
        token = strtok(NULL, dlim);
    }
}

void parse_options(int argc, char* argv[]) {
    while(1) {
        int c = 0;
        int option_index = 0;
        static struct option long_options[] = {
            {"type", required_argument, 0, 0 },
            {"period", required_argument, 0, 0},
            {"skip", required_argument, 0, 0},
            {0, 0, 0, 0}
        };

        c = getopt_long(argc, argv, "",
            long_options, &option_index);

        if (c == -1)
            break;

        if (c == 0) {
            // addr type
            if (option_index == 0) {
                if (strcmp(optarg, "v") == 0 ||
                    strcmp(optarg, "virtual") == 0) {
                    addr_type = 'v';
                    continue;
                }

                if (strcmp(optarg, "p") == 0 ||
                    strcmp(optarg, "physical") == 0) {
                    addr_type = 'p';
                    continue;
                }

                printf("'--type' option with invalid argument: %s\n", optarg);
                exit(1);
            }

            // time period
            if (option_index == 1) {
                split_period(optarg);
                continue;
            }

            // skip period
            if (option_index == 2) {
                if (atoi(optarg) > 0) {
                    skip_time = atoi(optarg);
                    continue;
                } else {
                    printf("'--skip' option with invalid argument: %s\n", optarg);
                }
            }

            printf("invalid option_index: %d\n", option_index);
            exit(1);
        }
    }

    // 处理必选参数
    if (optind == argc) {
        printf("ideal_hot_distribution option <benchname> can't be omitted\n");
        exit (1);
    } else {
        benchname = argv[optind];
    }

    printf("type: %c\n", addr_type);
    printf("period: %ds\n", time_period);
    printf("benchmark: %s\n", benchname.c_str());
}

uint64_t address_to_pn(const std::string& address) {
    uint64_t addr = 0;
    try {
        addr = std::stoull(address, nullptr, 16);
    } catch(const std::invalid_argument& ia) {
        std::cerr << "Invalid argument exception when calling stoull" << std::endl;
        std::cerr << "Invalid argument: " << address << std::endl;
        exit(1);
    } catch (const std::out_of_range& oor) {
        std::cerr << "The number is out of range" << std::endl;
        std::cerr << "Out range number: " << address << std::endl;
    }
    return addr / PAGE_SIZE;
}

// 读入所有trace，并计算acces cnt
void get_trace() 
{
    for (const auto& entry : fs::directory_iterator(input_dir)) {
        std::string filePath = entry.path().filename().string();
        if (filePath.find(benchname) == 0) {
            trace_num++;
        }
    }

    traces.resize(trace_num);
    
    int processedFileCount = 0;
    while (processedFileCount < trace_num) {
        std::string filePath = input_dir + "/" + benchname + "_" + 
            std::to_string(processedFileCount) + ".out";

        if (fs::exists(filePath)) {
            printf("Reading %s\n", (benchname + "_" + std::to_string(processedFileCount) + ".out").c_str());

            std::ifstream file(filePath);
            std::string line;

            std::unordered_map<uint64_t, uint64_t>* page_freq_cur = new std::unordered_map<uint64_t, uint64_t>;

            while (getline(file, line)) {
                std::istringstream iss(line);
                char opType;
                std::string virtual_address, physical_address;
                if (iss >> opType >> virtual_address >> physical_address) {
                    uint64_t page_number;
                    if (addr_type == 'v') {
                        page_number = address_to_pn(virtual_address);
                    } else {
                        page_number = address_to_pn(physical_address);
                    }

                    if (page_number > addr_space_range) {
                        addr_space_range = page_number;
                    }

                    if (page_freq_cur->find(page_number) == (page_freq_cur->end())) {
                        (*page_freq_cur)[page_number] = 1;
                    } else {
                        (*page_freq_cur)[page_number] += 1;
                    }
                }
            }

            traces[processedFileCount] = page_freq_cur;
        } else {
            std::cerr << "File: " << filePath << " does not exist" << std::endl;
        }

        processedFileCount++;
    }
}

// 初始化DRAM中的页数
// 跳过前skip个文件后，取剩下footprint的平均值，再乘上 'DRAM_RATIO'% 
void init_dram(void) 
{
    uint64_t total_footprint = 0;
    uint64_t avg_total_footprint = 0;
    int idx = 0;
    for (auto it = period_traces.begin(); it != period_traces.end(); it++) {
        total_footprint += (*it)->size();
        printf("footprint[%d]: %lu\n", idx, (*it)->size());
        idx++;
    }
    avg_total_footprint = total_footprint / period_traces.size();
    dram_cap_pn = avg_total_footprint * DRAM_RATIO / 100;
    printf("Period Num: %u, 平均值: %lu\n", (trace_num + time_period - 1)/ time_period, avg_total_footprint);
    printf("Period: %d, DRAM_RATIO: %d%%, DRAM_PN: %lu\n",time_period, DRAM_RATIO, dram_cap_pn);
}

void init_env(int argc, char* argv[]) 
{
    parse_options(argc, argv);

    input_dir = input_dir + "/" + benchname;

    get_trace();
}

void create_output_dir(void) {
    mkdir(output_dir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    output_dir = "/home/yangxr/downloads/test_trace/hot_dist/ideal/" + benchname;
    mkdir(output_dir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    output_dir = output_dir + "/" + std::to_string(time_period);
    mkdir(output_dir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    printf("output_dir: %s\n", output_dir.c_str());

    mkdir(global_output_dir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    global_output_dir = "/home/yangxr/downloads/test_trace/global_dist/ideal/" + benchname;
    mkdir(global_output_dir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    global_output_dir = global_output_dir + "/" + std::to_string(time_period);
    mkdir(global_output_dir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    printf("global output_dir: %s\n", output_dir.c_str());
}

// 使用不同period生成trace时，初始化环境变量
void init_local_env(void) {
    // 释放已有的period资源
    for (auto map_ptr: period_traces) {
        delete map_ptr;
    }

    time_period = periods[period_idx];
    create_output_dir();

    period_traces.resize((trace_num + time_period - 1)/ time_period);

}

void get_hot_dist(void) {
    // 按照period处理traces data
    // period_idx: 0, 1, 2...
    // trace_idx: 0, time_perid * 1, time_period * 2,...
    for(uint64_t period_idx = 0; period_idx < period_traces.size(); period_idx += 1) {

        std::unordered_map<uint64_t, uint64_t>* page_freq_period = new std::unordered_map<uint64_t, uint64_t>;
        uint64_t trace_range = std::min((uint64_t)((period_idx + 1) * time_period), (uint64_t)(traces.size()));
        for(uint64_t trace_idx = period_idx * time_period; trace_idx < trace_range; trace_idx++) {

            if (trace_idx >= traces.size()) {
                printf("err: trace_idx %ld, traces size %lu\n", trace_idx, traces.size());
                exit(1);
            }
            
            for (const auto& page: *(traces[trace_idx])) {
                if(page_freq_period->find(page.first) == page_freq_period->end()) {
                    (*(page_freq_period))[page.first] = page.second;
                } else {
                    (*(page_freq_period))[page.first] += page.second;
                }
            }
        }
        period_traces[period_idx] = page_freq_period;
    }
}

void dump_hot_dist(void) {
    int tmp_idx = 0;

    // sort by access freq
    for (auto it = period_traces.begin(); it != period_traces.end(); it++) {
        std::vector<std::pair<uint64_t, uint64_t>> access_dist((*it)->begin(), (*it)->end());
        std::vector<std::pair<uint64_t, uint64_t>> hot_pages;

        std::sort(access_dist.begin(), access_dist.end(), [](const auto& a, const auto& b){
            return a.second > b.second; // compared by access count, Descending
        });

        for (uint64_t idx = 0; idx < access_dist.size() && idx < dram_cap_pn; idx++) {
            if (idx >= access_dist.size()) {
                printf("caculate hot dist err: idx %ld, access_dist.size(): %lu, dram_cap_pn: %lu\n", idx, access_dist.size(), dram_cap_pn);
                exit(1);
            }
            hot_pages.push_back(access_dist[idx]);
        }

        // output to hot_dist file
        std::sort(hot_pages.begin(), hot_pages.end(), [](const auto& a, const auto& b) {
            return a.first < b.first;   // compared by addr, ascending
        });

        std::string outputFileName = output_dir + "/" + benchname + "_" + std::to_string(tmp_idx * time_period);
        std::string globalOutPutFileName = global_output_dir + "/" + benchname + "_" + std::to_string(tmp_idx * time_period);
        if (addr_type == 'v') {
            outputFileName += ".hot_dist.vout";
            globalOutPutFileName += ".global_dist.vout";
        } else {
            outputFileName += ".hot_dist.pout";
            globalOutPutFileName += ".global_dist.pout";
        }

        printf("output_file: %s\n", outputFileName.c_str());

        std::ofstream outputFile(outputFileName);
        outputFile << addr_space_range << std::endl;
        for (size_t i = 0; i < hot_pages.size() - 1; ++i) {
            outputFile << "0x" << std::hex << hot_pages[i].first << " " << std::dec << 
                (hot_pages[i + 1].first - hot_pages[i].first) << " " << hot_pages[i].second << "\n";
        }
        outputFile << "0x" << std::hex << hot_pages[hot_pages.size() - 1].first << " 0 " << 
            std::dec << hot_pages[hot_pages.size() - 1].second;
        outputFile.close();

        printf("global_output_file: %s\n", globalOutPutFileName.c_str());
        std::ofstream globalOutputFile(globalOutPutFileName);
        globalOutputFile << addr_space_range << std::endl;
        for (size_t i = 0; i < access_dist.size(); ++i) {
            globalOutputFile << "0x" << std::hex << access_dist[i].first << " " << std::dec << access_dist[i].second << "\n";
        }
        globalOutputFile.close();

        tmp_idx += 1;
    }
}

int main(int argc, char* argv[]) {
    init_env(argc, argv);
    while (period_idx < (int)periods.size()) {
        init_local_env();
        get_hot_dist();
        init_dram();
        dump_hot_dist();
        period_idx++;
    }
}