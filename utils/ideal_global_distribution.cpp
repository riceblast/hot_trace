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
#include <numeric>
#include <unistd.h>
#include <getopt.h>
#include <string.h>
#include <error.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <thread>
#include <mutex>

/*
 * 简介：
 * 该文件负责生成热页分布系列文件,
 * 不需要利用历史预测未来, 直接利用"未来"的数据生成当前的热页分布,
 * 由于使用了未来的数据, 因此该算法是"ideal"的
*/

#define PAGE_SIZE 4096

int trace_num = 0; // 所有trace文件的数量
int least_common_multiple = 0;  // 多个period的最小公倍数

std::string benchname;
std::string input_dir = "/home/yxr/downloads/test_trace/raw_data/roi/";
std::string output_dir_prefix = "/home/yxr/downloads/test_trace/global_dist/roi/";

int max_thread_cnt = 12;
std::mutex mtx;
std::vector<int> periods;   // 记录想要所有输出的period序列，形如：1,2,3,4,5
std::queue<int> file_time_list; // 待处理的文件时间列表，共多线程处理
std::vector<std::thread> threads;   // 用于读取文件作初步处理的多线程
std::vector<std::unordered_map<uint64_t, uint64_t>*> traces_vir; // 处理所有raw_data读入的trace，pn -> access_freq
std::vector<std::unordered_map<uint64_t, uint64_t>*> traces_phy; // 处理所有raw_data读入的trace，pn -> access_freq
std::vector<std::unordered_map<uint64_t, uint64_t>*> period_traces_vir; // 按照time_period处理traces，pn -> access_freq
std::vector<std::unordered_map<uint64_t, uint64_t>*> period_traces_phy; // 按照time_period处理traces，pn -> access_freq

namespace fs = std::filesystem;

void split_period(char* optarg) 
{
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

    std::sort(periods.begin(), periods.end());
    //periods.sort();
}

void parse_options(int argc, char* argv[]) 
{
    while(1) {
        int c = 0;
        int option_index = 0;
        static struct option long_options[] = {
            {"periods", required_argument, 0, 0},
            {0, 0, 0, 0}
        };

        c = getopt_long(argc, argv, "",
            long_options, &option_index);

        if (c == -1)
            break;

        if (c == 0) {
            // time period
            if (option_index == 0) {
                split_period(optarg);
                continue;
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

    printf("benchmark: %s\n", benchname.c_str());
}

uint64_t address_to_pn(const std::string& address) 
{
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

void cnt_trace_num(void) 
{
    input_dir = input_dir + "/" + benchname;

    for (const auto& entry : fs::directory_iterator(input_dir)) {
        std::string filePath = entry.path().filename().string();
        if (filePath.find(benchname) == 0) {
            trace_num++;
        }
    }
}

uint64_t lcm(uint64_t a, uint64_t b) {
    return a / std::gcd(a, b) * b;
}

// Function to compute the LCM of all elements in a vector<int>
uint64_t lcm_of_periods(const std::vector<int>& elements) {
    uint64_t result = 1;
    for (int num : elements) {
        result = lcm(result, num);
        if (result == 0) break;
    }
    return result;
}

void create_output_dir(void) {
    mkdir(output_dir_prefix.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    std::string global_output_dir = output_dir_prefix + "/" + benchname;
    int ret = mkdir(global_output_dir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    printf("global_output_dir: %s\n", global_output_dir.c_str());
    printf("Error opening file: %s\n", strerror(errno));
    printf("ret: %d\n", ret);

    for (int idx = 0; idx < (int)periods.size(); idx++) {
        global_output_dir = output_dir_prefix + benchname + "/" + std::to_string(periods[idx]);
        mkdir(global_output_dir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
        printf("global output_dir: %s\n", global_output_dir.c_str());
    }
}

void init_env(int argc, char** argv) 
{
    parse_options(argc, argv);
    
    cnt_trace_num();

    least_common_multiple = lcm_of_periods(periods);
    
    create_output_dir();
}

void resize_trace_container(std::vector<std::unordered_map<uint64_t, uint64_t>*>& traces, int time_begin) {
    for (const auto& trace: traces) {
        trace->clear();
    }

    long unsigned int range = (time_begin + least_common_multiple) < trace_num? least_common_multiple : trace_num - time_begin;

    while(traces.size() < range) {
        traces.push_back(new std::unordered_map<uint64_t, uint64_t>);        
    }

    while(traces.size() > range) {
        delete (*traces.begin());
        traces.erase(traces.begin());
    }
}

void init_time_list_queue(int time_begin) {
    int time_bound = (time_begin + least_common_multiple) < trace_num? least_common_multiple : trace_num - time_begin;

    while (!file_time_list.empty()) 
        file_time_list.pop();

    for (int idx = time_begin; idx < time_bound; idx++) {
        file_time_list.push(idx);
    }
}

void init_local_env(int time_begin)
{
    resize_trace_container(traces_vir, time_begin);
    resize_trace_container(traces_phy, time_begin);
    init_time_list_queue(time_begin);
}

void _get_access_freq(int time_begin)
{
    while(true) {

        int time_idx = -1;

        mtx.lock();
        if (file_time_list.empty())
            return;

        time_idx = file_time_list.front();
        file_time_list.pop();
        mtx.unlock();

        std::string filePath = input_dir + "/" + benchname + "_" + 
            std::to_string(time_idx) + ".out";

        if (fs::exists(filePath)) {
            printf("Reading %s\n", (benchname + "_" + std::to_string(time_idx) + ".out").c_str());

            std::ifstream file(filePath);
            std::string line;

            std::unordered_map<uint64_t, uint64_t>* VPN_freq = traces_vir[time_idx - time_begin];
            std::unordered_map<uint64_t, uint64_t>* PPN_freq = traces_phy[time_idx - time_begin];
            while(getline(file, line)) {
                std::istringstream iss(line);
                char opType;
                std::string virtual_address, physical_address;
                if (iss >> opType >> virtual_address >> physical_address) {
                    uint64_t VPN, PPN;
                    VPN = address_to_pn(virtual_address);
                    if (VPN_freq->find(VPN) == (VPN_freq->end())) {
                        (*VPN_freq)[VPN] = 1;
                    } else {
                        (*VPN_freq)[VPN] += 1;
                    }

                    PPN = address_to_pn(physical_address);
                    if(PPN_freq->find(PPN) == (PPN_freq->end())) {
                        (*PPN_freq)[PPN] = 1;
                    } else {
                        (*PPN_freq)[PPN] += 1;
                    }
                }
            }
        } else {
            std::cerr << "File: " << filePath << " does not exist" << std::endl;
        }
    }
}

// 读入所有trace，并计算acces cnt
void get_trace(int time_begin) 
{    
    int time_bound = (time_begin + least_common_multiple) < trace_num? time_begin + least_common_multiple : trace_num;
    printf("准备多线程读取trace并作基础统计, %d线程, %d -> %d\n", max_thread_cnt, time_begin, time_bound);

    for (int i = 0; i < max_thread_cnt; i++)
        threads.emplace_back(_get_access_freq, time_begin);

    // 等待所有线程完成
    for (auto& th : threads) {
        th.join();
    }
}

void clear_period_container(std::vector<std::unordered_map<uint64_t, uint64_t>*>& period_traces) {
    while(period_traces.size() > 0) {
        delete (*(period_traces.begin()));
        period_traces.erase(period_traces.begin());
    }
}

void get_global_dist(const std::vector<std::unordered_map<uint64_t, uint64_t>*>& traces,
    std::vector<std::unordered_map<uint64_t, uint64_t>*>& period_traces, int period)
{
    std::unordered_map<uint64_t, uint64_t>* page_freq_period = new std::unordered_map<uint64_t, uint64_t>;
    for (long unsigned int idx = 0; idx < traces.size(); idx += 1) {
        if (idx != 0 && idx % period == 0) {
            period_traces.push_back(page_freq_period);
            page_freq_period = new std::unordered_map<uint64_t, uint64_t>;
        }

        std::vector<std::pair<uint64_t, uint64_t>> trace(traces[idx]->begin(), traces[idx]->end());
        for (const auto& entry: trace) {
            uint64_t addr = entry.first;
            if(page_freq_period->find(addr) == page_freq_period->end()) {
                (*page_freq_period)[addr] = entry.second;
            } else {
                (*page_freq_period)[addr] += entry.second;
            }
        }
    }

    if (page_freq_period->size() > 0) {
        period_traces.push_back(page_freq_period);
    }
}

void write_to_file(const std::vector<std::unordered_map<uint64_t, uint64_t>*>& period_traces,
    int time_begin, int period, bool is_virt) 
{
    for (long unsigned int idx = 0; idx < period_traces.size(); idx++) {
        std::unordered_map<uint64_t, uint64_t>* trace = period_traces[idx];
        std::vector<std::pair<uint64_t, uint64_t>> access_dist(trace->begin(), trace->end());

        std::sort(access_dist.begin(), access_dist.end(), [](const auto& a, const auto& b) {
            return a.second > b.second;   // compared by freq, descending
        });

        // BFS_0.global_dist.vout
        std::string output_filename = output_dir_prefix + benchname + "/" + std::to_string(period)
            + "/" + benchname + "_" + std::to_string(idx * period + time_begin) + ".global_dist";
        output_filename += (is_virt)? ".vout" : ".pout";
        printf("output file: %s\n", output_filename.c_str());

        std::ofstream outputFile(output_filename);
        outputFile << 0 << std::endl;
        for (size_t i = 0; i < access_dist.size(); ++i) {
            outputFile << "0x" << std::hex << access_dist[i].first << " " << std::dec << access_dist[i].second << "\n";
        }
        outputFile.close();
    }
}

void dump_global_dist(int time_begin)
{
    for(const auto& period: periods) {
        clear_period_container(period_traces_vir);
        clear_period_container(period_traces_phy);

        get_global_dist(traces_vir, period_traces_vir, period);
        write_to_file(period_traces_vir, time_begin, period, true);

        get_global_dist(traces_phy, period_traces_phy, period);
        write_to_file(period_traces_phy, time_begin, period, false);
    }
}

int main(int argc, char* argv[]) {
    init_env(argc, argv);   // 初始化整体系统的变量
    for (int time_begin = 0; time_begin < trace_num; time_begin += least_common_multiple) {
        init_local_env(time_begin); // 主要是初始化traces等数据结构中的内容
        get_trace(time_begin);    // 从time_idx开始读，共计least_common_multiple
        dump_global_dist(time_begin); // 从time_idx这个时刻开始dump 不同period对应的global_dist
    }
}
