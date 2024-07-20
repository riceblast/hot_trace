#include "mem_simulator.h"

#include <stdio.h>

#include <fstream>
#include <iostream>

#include "param.h"

void MemSimulator::UpdateMemStat(AccessStat access_stat) 
{
    if (access_stat == kReadHit || access_stat == kWriteHit) {
        mem_stat_.nr_cur_hit += 1;
        mem_stat_.nr_accu_hit += 1;
    } else if (access_stat == kReadMiss || access_stat == kWriteMiss) {
        mem_stat_.nr_cur_miss += 1;
        mem_stat_.nr_accu_miss += 1;
    }
}

void MemSimulator::ResetPeriodicalStat(void)
{
    mem_stat_.nr_cur_hit = 0;
    mem_stat_.nr_cur_miss = 0;

    mem_controller_.ClearLearnedStat();
}

void MemSimulator::_DumpPeriodicalStat(uint64_t period_idx)
{
    double second = period_idx * track_period_ / (double)1000;
    double cur_hit = mem_stat_.nr_cur_hit / (double)(mem_stat_.nr_cur_hit + mem_stat_.nr_cur_miss);
    double accu_hit = mem_stat_.nr_accu_hit / (double)(mem_stat_.nr_accu_hit + mem_stat_.nr_accu_miss);
    double cur_miss = mem_stat_.nr_cur_miss / (double)(mem_stat_.nr_cur_hit + mem_stat_.nr_cur_miss);
    double accu_miss = mem_stat_.nr_accu_miss / (double)(mem_stat_.nr_accu_hit + mem_stat_.nr_accu_miss);



    dump_stream << std::to_string(period_idx) << "," 
        << second << "s,"
        << cur_hit * 100 << ","
        << accu_hit * 100 << ","
        << cur_miss * 100 << ","
        << accu_miss * 100;
    if (direct_map_) {
        dump_stream << "\n";
        dump_stream << std::flush;
    } else {
        //uniform_cover,bloat_cover,cold_cover,bloat_hit_cur,unused_dram,nr_avg_remap
        uint64_t line_per_period = (uint64_t)(((double)track_period_ / 1000) * kLineNumPerSecond);
        double uniform_cover_ratio = mem_controller_.learned_stat_.uniform_cover == 0? 0:
            mem_controller_.learned_stat_.uniform_cover / (double)line_per_period;
        double bloat_cover_ratio = mem_controller_.learned_stat_.bloat_cover == 0? 0:
            mem_controller_.learned_stat_.bloat_cover / (double)line_per_period;
        double cold_cover_ratio = mem_controller_.learned_stat_.cold_cover == 0? 0:
            mem_controller_.learned_stat_.cold_cover / (double)line_per_period;
        double bloat_hit_ratio = mem_controller_.learned_stat_.bloat_cover == 0? 0:
            mem_controller_.learned_stat_.bloat_hit_cur / (double)mem_controller_.learned_stat_.bloat_cover;
        uint64_t unused_dram_blocks = 0;
        double unused_dram_ratio = 0;
        uint64_t nr_avg_remap = 0;
        uint64_t nr_bloat = 0;
        for (const auto& usage: mem_controller_.dram_block_usage_) {
            if (usage == 0 || usage == -1) {
                unused_dram_blocks += 1;
            }
            if (usage > 1) {
                nr_bloat += 1;
                nr_avg_remap += usage;
            }
        }
        nr_avg_remap = nr_bloat == 0? 0 : nr_avg_remap / nr_bloat;
        unused_dram_ratio = unused_dram_blocks / mem_controller_.dram_block_usage_.size();

        dump_stream << ","
            << uniform_cover_ratio * 100 << ","
            << bloat_cover_ratio * 100 << ","
            << cold_cover_ratio * 100 << ","
            << bloat_hit_ratio * 100 << ","
            << unused_dram_ratio * 100 << ","
            << nr_avg_remap << "\n";
        dump_stream << std::flush;
    }
}

void MemSimulator::ShowPeriodicalStat(uint64_t period_idx)
{
    double second = period_idx * track_period_ / (double)1000;

    printf("%.2fs: hit -> %.2f-%.2f, miss -> %.2f-%.2f\n", second,
        mem_stat_.nr_cur_hit / (double)(mem_stat_.nr_cur_hit + mem_stat_.nr_cur_miss),
        mem_stat_.nr_accu_hit / (double)(mem_stat_.nr_accu_hit + mem_stat_.nr_accu_miss),
        mem_stat_.nr_cur_miss / (double)(mem_stat_.nr_cur_hit + mem_stat_.nr_cur_miss),
        mem_stat_.nr_accu_miss / (double)(mem_stat_.nr_accu_hit + mem_stat_.nr_accu_miss));

    _DumpPeriodicalStat(period_idx);
}

void MemSimulator::Run(void)
{
    char rw_type;
    uint64_t cache_addr;
    uint64_t access_idx = 0;
    uint64_t nr_total_access = 0;
    uint64_t start_pn = 0;  // cur period start hp_pn
    
    access_freq_tracker_.NewPeriod(start_pn);
    while(!trace_reader_.Eof()) {
        cache_addr = trace_reader_.NextAddr(rw_type);

        if (cache_addr == (uint64_t)-1) {
            continue;
        }

        nr_total_access += 1;
        access_idx += 1;
        if (nr_total_access >= (max_seconds_ + 1) * kLineNumPerSecond) {
            printf("Reach max seconds limit, end simulation\n");
            return;
        }

#ifdef VERBOSE_MODE
        if (access_idx % (kLineNumPerSecond / 100) == 0) {
            printf("Getting %lums\n", nr_total_access / (kLineNumPerSecond / 100) * 10);
        }
#endif

        AccessStat access_stat =  mem_controller_.do_access(rw_type, cache_addr);
        UpdateMemStat(access_stat);
        access_freq_tracker_.UpdateAccessFreq(cache_addr);

        if (access_idx % nr_period_access_ == 0) {
            printf("%lu periods ending...\n", nr_total_access / nr_period_access_);

            access_idx = 0;
            ShowPeriodicalStat(nr_total_access / nr_period_access_);
            ResetPeriodicalStat();

            if (!direct_map_) {
                access_freq_tracker_.GetNewHugePageMetadata();
                mem_controller_.UpdateMetadata(start_pn, access_freq_tracker_.huge_metadata_, 
                    access_freq_tracker_.huge_remap_group_, access_freq_tracker_.huge_remap_info_,
                    access_freq_tracker_.huge_bloat_degree_);

                start_pn = (start_pn + kNrHugePagePerSeg) % nr_cxl_hp_;
                access_freq_tracker_.NewPeriod(start_pn);
            }
        }
    }
}