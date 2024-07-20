#ifndef MEM_SIM_INC_MEM_SIMULATOR_H_
#define MEM_SIM_INC_MEM_SIMULATOR_H_

#include "access_freq_tracker.h"
#include "trace_reader.h"
#include "mem_controller.h"

#include <cstdint>
#include <fstream>
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
        uint64_t track_period_; // memory tracking period(ms)
        uint64_t nr_period_access_;    // Equivalent number of memory accesses per period
        uint64_t segs_; // cxl addr space segs
        std::string bench_name_;
        std::ofstream dump_stream;
        
        MemStat mem_stat_;
        TraceReader trace_reader_;
        AccessFreqTracker access_freq_tracker_;
        MemController mem_controller_;
        
        void UpdateMemStat(AccessStat stat);
        void ShowPeriodicalStat(uint64_t period_idx);
        void ResetPeriodicalStat(void);
        void Run(void);
        MemSimulator(bool direct_map, uint64_t cache_block_size, uint64_t dram_ratio, uint64_t dram_size, uint64_t cxl_size, 
            uint64_t max_seconds, uint64_t bucket_size, uint64_t track_period, std::string bench_name)
            :direct_map_(direct_map), cache_block_size_(cache_block_size), dram_ratio_(dram_ratio), 
            dram_size_(dram_size), nr_dram_hp_(dram_size / (kHugePageSize / 1024 / 1024)),
            cxl_size_(cxl_size), nr_cxl_hp_(cxl_size / (kHugePageSize / 1024 / 1024)), track_period_(track_period),
            nr_period_access_(kLineNumPerSecond * track_period / 1000), segs_(cxl_size / kNrHugePagePerSeg),
            bench_name_(bench_name), mem_stat_({0, 0, 0, 0}),trace_reader_(cache_block_size, kHugePageByteSize, kCxlByteAddrRange, bench_name),
            access_freq_tracker_(cache_block_size, dram_ratio, cxl_size, bucket_size, track_period, bench_name),
            mem_controller_(direct_map, dram_ratio, cache_block_size, dram_size, cxl_size)
            {
                uint64_t equivalent_max_seconds = trace_reader_.max_file_idx_ / (kLineNumPerSecond / 20000000);
                max_seconds_ =   equivalent_max_seconds < max_seconds? equivalent_max_seconds : max_seconds;

                if (direct_map_) {
                    dump_stream.open(kDumpPathPrefix + bench_name_ +  "/direct_map/" + bench_name_ + "_direct_" + std::to_string(dram_size_) + ".csv");;
                    if (!dump_stream.is_open())
                        assert(0);
                    dump_stream << "period_idx,time,cur_hit,acc_hit,cur_miss,acc_miss\n";
                    dump_stream.flush();
                } else {
                    dump_stream.open(kDumpPathPrefix + bench_name_ + "/learned_v1/" + bench_name_ + "_learned_" + std::to_string(dram_size_) + ".csv");
                    if (!dump_stream.is_open())
                        assert(0);
                    dump_stream << "period_idx,time,cur_hit,acc_hit,cur_miss,acc_miss,uniform_cover,bloat_cover,cold_cover,bloat_hit_cur,unused_dram_ratio,nr_avg_remap\n";
                    dump_stream.flush();
                }


                std::cout << "Memory Simulator:\n";
                std::cout << "\tbench_name: " << bench_name_ << std::endl;
                std::cout << "\tcache_block_size: " << cache_block_size_ << "B" << std::endl;
                std::cout << "\tdram_size: " << dram_size_ << "MB" << std::endl;
                std::cout << "\tcxl_size: " << cxl_size_ << "MB" << std::endl;
                std::cout << "\tcxl_region_size_: " << kNrHugePagePerSeg * kHugePageSize / kMB << "MB" << std::endl;
                std::cout << "\tmax_seconds: " << max_seconds_ << "s" << std::endl;
                std::cout << "\ttrack_period_: " << track_period_ << "ms" << std::endl;
            };
        ~MemSimulator(void){};

    private:
        void _DumpPeriodicalStat(uint64_t period_idx);
};

#endif