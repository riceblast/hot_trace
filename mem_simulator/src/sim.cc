#include "mem_simulator.h"

#include <unistd.h>
#include <getopt.h>

#include <cstdint>
#include <cassert>
#include <iostream>
#include <string>

uint64_t dram_size = 0;
uint64_t cache_block_size = 0;
uint64_t max_seconds = 0;
std::string bench_name = "";

// --cache-block 缓存块大小(B) --dram-size DRAM容量(MB) benchname benchmark名称
void parse_args(int argc, char* argv[])
{
    while(1) {
        int c = 0;
        int option_index = 0;
        static struct option long_options[] = {
            {"cache-block", required_argument, 0, 0},
            {"dram-size", required_argument, 0, 0},
            {"max-seconds", required_argument, 0, 0},
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
                // dram size
                dram_size = std::stoull(optarg, nullptr);
                continue;
            }else if (option_index == 2) {
                // max seconds
                max_seconds = std::stoull(optarg, nullptr);
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
        std::cout << "\tdram-size: the demand dram size(MB)" << std::endl;
        std::cout << "\tmax-seconds: the time to simulate" << std::endl;
        std::cout << "\tbench-name: the name of benchmark" << std::endl;
        assert(0);
    } else {
        bench_name = argv[optind];
    }
}

int main(int argc, char* argv[]) 
{
    parse_args(argc, argv);

    uint64_t cxl_size = 128 * 1024; // 128GB
    MemSimulator mem_simulator(cache_block_size, dram_size, cxl_size, max_seconds, bench_name);
    mem_simulator.run();
}