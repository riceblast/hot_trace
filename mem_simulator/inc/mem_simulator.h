#ifndef MEM_SIM_INC_MEM_SIMULATOR_H_
#define MEM_SIM_INC_MEM_SIMULATOR_H_

#include "trace_reader.h"

#include <cstdint>
#include <iostream>
#include <string>

struct MemStat {
    double hit_ratio;
    double miss_ratio;
};

class MemSimulator {
    public:
        uint64_t cache_block_size_; // Byte
        uint64_t dram_size_;    // MB
        uint64_t cxl_size_; // MB
        uint64_t max_seconds_;
        std::string bench_name_;
        // memory controller
        
        void run(void);
        MemSimulator(uint64_t cache_block_size, uint64_t dram_size, uint64_t cxl_size, uint64_t max_seconds, std::string bench_name)
            :cache_block_size_(cache_block_size), dram_size_(dram_size), cxl_size_(cxl_size), bench_name_(bench_name), 
            trace_reader_(bench_name, max_seconds)
            {
                max_seconds_ = trace_reader_.max_seconds_;

                std::cout << "Memory Simulator:\n";
                std::cout << "\tbench_name: " << bench_name_ << std::endl;
                std::cout << "\tcache_block_size: " << cache_block_size_ << "B" << std::endl;
                std::cout << "\tdram_size: " << dram_size_ << "MB" << std::endl;
                std::cout << "\tmax_seconds: " << max_seconds_ << "s" << std::endl;
            };
        ~MemSimulator(void){}
    
    private:
        TraceReader trace_reader_;
};

#endif