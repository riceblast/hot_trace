#ifndef MEM_SIM_INC_MEM_SIMULATOR_H_
#define MEM_SIM_INC_MEM_SIMULATOR_H_

#include "access_freq_tracker.h"
#include "trace_reader.h"
#include "mem_controller.h"

#include <cstdint>
#include <iostream>
#include <string>

struct MemStat {
    uint64_t nr_cur_hit;
    uint64_t nr_accu_hit;
    uint64_t nr_cur_miss;
    uint64_t nr_accu_miss;
};

class MemSimulator {
    public:
        bool direct_map_ = false;
        uint64_t cache_block_size_; // Byte
        uint64_t dram_ratio_;
        uint64_t dram_size_;    // MB
        uint64_t nr_dram_hp_;
        uint64_t cxl_size_; // MB
        uint64_t nr_cxl_hp_;
        uint64_t max_seconds_;
        uint64_t nr_period_access_;    // Equivalent number of memory accesses per period
        uint64_t segs_; // cxl addr space segs
        std::string bench_name_;
        
        MemStat mem_stat_;
        TraceReader trace_reader_;
        AccessFreqTracker access_freq_tracker_;
        MemController mem_controller_;
        
        void run(void);
        MemSimulator(bool direct_map, uint64_t cache_block_size, uint64_t dram_ratio, uint64_t dram_size, uint64_t cxl_size, 
            uint64_t max_seconds, uint64_t bucket_size, uint64_t track_period, std::string bench_name)
            :direct_map_(direct_map), cache_block_size_(cache_block_size), dram_ratio_(dram_ratio), 
            dram_size_(dram_size), nr_dram_hp_(dram_size / (kHugePageSize / 1024 / 1024)),
            cxl_size_(cxl_size), nr_cxl_hp_(cxl_size / (kHugePageSize / 1024 / 1024)),
            nr_period_access_(kLineNumPerSecond * 10 * track_period / 1000), segs_(cxl_size / kNrHugePagePerSeg),
            bench_name_(bench_name), mem_stat_({0, 0, 0, 0}),trace_reader_(bench_name, max_seconds),
            access_freq_tracker_(cache_block_size, dram_size, cxl_size, bucket_size, track_period),
            mem_controller_(direct_map, cache_block_size, dram_ratio, dram_size, cxl_size)
            {
                max_seconds_ = trace_reader_.max_seconds_;

                std::cout << "Memory Simulator:\n";
                std::cout << "\tbench_name: " << bench_name_ << std::endl;
                std::cout << "\tcache_block_size: " << cache_block_size_ << "B" << std::endl;
                std::cout << "\tdram_size: " << dram_size_ << "MB" << std::endl;
                std::cout << "\tmax_seconds: " << max_seconds_ << "s" << std::endl;
            };
        ~MemSimulator(void){};
};

#endif