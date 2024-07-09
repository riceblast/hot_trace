#include "mem_simulator.h"

#include <iostream>

#include "param.h"

void MemSimulator::run(void)
{
    bool flag = false;
    char rw_type;
    uint64_t addr;
    while(!trace_reader_.Eof()) {
        flag = false;
        addr = trace_reader_.NextAddr(rw_type, flag);

        if (flag) {
            std::cout << std::dec << trace_reader_.GetCurFile() << ": 0x" << std::hex << addr << std::endl;
        }
    }
}