#include "mem_simulator.h"

#include <iostream>

#include "param.h"

void MemSimulator::run(void)
{
    char rw_type;
    uint64_t addr;
    uint64_t access_idx = 1;
    
    while(!trace_reader_.Eof()) {
        addr = trace_reader_.NextAddr(rw_type);

        access_freq_tracker_.UpdateAccessFreq(addr);
        // do access & count stat info


        if (access_idx % nr_period_access_ == 0) {
            access_freq_tracker_.GetNewHugePageMetadata();
            // update Index info
        }
        access_idx += 1;
    }
}