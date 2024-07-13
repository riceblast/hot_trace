#include "mem_simulator.h"

#include <unistd.h>
#include <getopt.h>

#include <cstdint>
#include <cassert>
#include <iostream>
#include <string>

bool direct_map = false;
uint64_t dram_ratio = 0;    // e.g. 16 -> 1:16
uint64_t dram_size = 0;
uint64_t cxl_size =0;
uint64_t cache_block_size = kCacheBlockSize;
uint64_t max_seconds = 0;
uint64_t bucket_size = 524288;
uint64_t track_period = 30; // milliseconds(ms)
std::string bench_name = "";

// --cache-block 缓存块大小(B) --dram-size DRAM容量(MB) benchname benchmark名称
void parse_args(int argc, char* argv[])
{
    while(1) {
        int c = 0;
        int option_index = 0;
        static struct option long_options[] = {
            {"cache-block", required_argument, 0, 0},
            {"dram-ratio", required_argument, 0, 0},
            {"cxl-size", required_argument, 0, 0},
            {"max-seconds", required_argument, 0, 0},
            {"direct-map", no_argument, 0, 0},
            {"bucket-size", required_argument, 0, 0},
            {"track-period", required_argument, 0, 0},
            {0, 0, 0, 0}
        };

        c = getopt_long(argc, argv, "",
            long_options, &option_index);

        if (c == -1)
            break;

        if (c == 0) {
            
            if (option_index == 0) {
                // cache block size
                cache_block_size = std::stoull(optarg, nullptr);
                continue;

            } else if (option_index == 1){
                // dram ratio
                dram_ratio = std::stoull(optarg, nullptr);
                continue;
            } else if (option_index == 2){
                // cxl size
                cxl_size = std::stoull(optarg, nullptr);
                continue;
            }else if (option_index == 3) {
                // max seconds
                max_seconds = std::stoull(optarg, nullptr);
                continue;
            } else if (option_index == 4) {
                // direct map or not
                direct_map = true;
                continue;
            } else if (option_index == 5) {
                bucket_size = std::stoull(optarg, nullptr);
                continue;
            } else if (option_index == 6) {
                track_period = std::stoull(optarg, nullptr);
                continue;
            }

            printf("invalid option_index: %d\n", option_index);
            assert(0);
        }
    }

    // 处理必选参数
    if (optind == argc) {
        std::cerr << "mem_sim option option <benchname> can't be omitted\n";
        std::cout << "./mem_simulator <--cache-block> <--dram-size> <--max-seconds> bench-name" << std::endl;
        std::cout << "\tcache-block: the basic cache block size(Byte)" << std::endl;
        std::cout << "\tdram-ratio: ratio of cxl:dram, e.g. 16" << std::endl;
        std::cout << "\tcxl-size: the size of cxl mem(MB)" << std::endl;
        std::cout << "\tbench-name: the name of benchmark" << std::endl;
        assert(0);
    } else {
        bench_name = argv[optind];
    }
}

int main(int argc, char* argv[]) 
{
    parse_args(argc, argv);

    dram_size = cxl_size / dram_ratio;
    MemSimulator mem_simulator(direct_map, cache_block_size, dram_ratio, dram_size, cxl_size, 
        max_seconds, bucket_size, track_period, bench_name);
    mem_simulator.run();
}