#include "mem_simulator.h"

#include <stdio.h>

#include <iostream>

#include "param.h"

void MemSimulator::run(void)
{
    char rw_type;
    uint64_t addr;
    uint64_t access_idx = 1;
    bool warm_up = false;
    uint64_t start_pn = 0;  // cur period start hp_pn
    
    access_freq_tracker_.NewPeriod(start_pn);
    while(!trace_reader_.Eof()) {
        addr = trace_reader_.NextAddr(rw_type);

        if (addr == (uint64_t)-1) {
            continue;
        }

        AccessStat access_stat =  mem_controller_.do_access(rw_type, addr);

        if (access_stat == kReadHit || access_stat == kWriteHit) {
            mem_stat_.nr_cur_hit += 1;
            mem_stat_.nr_accu_hit += 1;
        } else if (access_stat == kReadMiss || access_stat == kWriteMiss) {
            mem_stat_.nr_cur_miss += 1;
            mem_stat_.nr_accu_miss += 1;
        }

        if (access_idx % nr_period_access_ == 0) {
            access_idx = 0;

            printf("hit cur-accu %.2f-%.2f, miss cur-accu: %.2f-%.2f\n", 
                mem_stat_.nr_cur_hit / (double)(mem_stat_.nr_cur_hit + mem_stat_.nr_cur_miss),
                mem_stat_.nr_accu_hit / (double)(mem_stat_.nr_accu_hit + mem_stat_.nr_accu_miss),
                mem_stat_.nr_cur_miss / (double)(mem_stat_.nr_cur_hit + mem_stat_.nr_cur_miss),
                mem_stat_.nr_accu_miss / (double)(mem_stat_.nr_accu_hit + mem_stat_.nr_accu_miss));

            if (!direct_map_) {
                if (access_idx % nr_period_access_ == 0) {
                    access_idx = 0;

                    if (warm_up) {
                        access_freq_tracker_.GetNewHugePageMetadata();
                        mem_controller_.UpdateMetadata(start_pn, access_freq_tracker_.huge_metadata_, 
                            access_freq_tracker_.huge_remap_group_, access_freq_tracker_.huge_remap_info_,
                            access_freq_tracker_.huge_bloat_degree_);
                    }
                    warm_up = true;

                    start_pn = (start_pn + kNrHugePagePerSeg) % nr_cxl_hp_;
                    access_freq_tracker_.NewPeriod(start_pn);
                }

                access_freq_tracker_.UpdateAccessFreq(addr);
            }
        }

        access_idx += 1;
    }
}