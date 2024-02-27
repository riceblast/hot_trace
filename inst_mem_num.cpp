/*
 * Copyright (C) 2004-2021 Intel Corporation.
 * SPDX-License-Identifier: MIT
 */

#include <stdio.h>
#include <iostream>
#include <fstream>
#include <sys/stat.h>
#include <sys/types.h>
#include <chrono>
#include <iomanip>
#include "pin.H"

using namespace std;

string appName;
string logName;
string out_dir = "./trace";
std::ofstream* log_file;

UINT64 traceStartPos;
UINT64 period;
UINT64 memPeriod;
UINT64 memDumpNum;
UINT64 maxMemSetting;
UINT64 readNum;
UINT64 writeNum;
UINT64 memNum;
UINT64 instNum;

bool mem = 1;
bool inst = 1;

/* ===================================================================== */
// Command line switches
/* ===================================================================== */
KNOB< BOOL > KnobMem(KNOB_MODE_WRITEONCE, "pintool", "mem", "", "only counter mem");
KNOB< BOOL > KnobInst(KNOB_MODE_WRITEONCE, "pintool", "inst", "", "only counter inst");

// This function is called before every instruction is executed
// and prints the IP
VOID cnt_ip(VOID* ip) 
{ 
    instNum++; 
}

VOID cnt_read(VOID* addr)
{
    readNum++;
}

VOID cnt_write(VOID* addr)
{
    writeNum++;
}

// Pin calls this function every time a new instruction is encountered
VOID Instruction(INS ins, VOID* v)
{
    if (inst) {
        // Insert a call to printip before every instruction, and pass it the IP
        INS_InsertCall(ins, IPOINT_BEFORE, (AFUNPTR)cnt_ip, IARG_INST_PTR, IARG_END);
    }

    if (mem) {
        // instrument memory reads and writes
        UINT32 memOperands = INS_MemoryOperandCount(ins);

        // Iterate over each memory operand of the instruction.
        for (UINT32 memOp = 0; memOp < memOperands; memOp++) {
            if (INS_MemoryOperandIsRead(ins, memOp))
                INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)cnt_read, 
                    IARG_MEMORYOP_EA, memOp, IARG_END);
            if (INS_MemoryOperandIsWritten(ins, memOp))
                INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)cnt_write, 
                    IARG_MEMORYOP_EA, memOp, IARG_END);
        }
    }
}

// This function is called when the application exits
VOID Fini(INT32 code, VOID* v)
{
    memNum = readNum + writeNum;
    *log_file << "app name: " << appName << endl;
    *log_file << "start inst position: " << "0x" << hex << traceStartPos << endl;
    if (mem) {
        *log_file << "total read num: " << "0x" << hex << readNum << endl;
        *log_file << "total write num: " << "0x" << hex << writeNum << endl;
        *log_file << "total memory access num: " << "0x" << hex << memNum << endl;
    }
    if (inst) {
        *log_file << "total instruction num: " << "0x" << hex << instNum << endl;
    }
    log_file->close();
}

/* ===================================================================== */
/* Print Help Message                                                    */
/* ===================================================================== */

INT32 Usage()
{
    //PIN_ERROR("This Pintool prints the IPs of every instruction executed\n" + KNOB_BASE::StringKnobSummary() + "\n");
    cerr << KNOB_BASE::StringKnobSummary() << endl;
    return -1;
}

// do some customized init
void custom_init(int argc, char* argv[])
{
    // make new directory
    appName = argv[argc - 1];
    int status = mkdir((out_dir + "/" + appName).c_str(),
        S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    if (!status) {
        cerr << "mkdir " << out_dir << endl;
    }

    if (KnobInst.Value() == 1 && KnobMem.Value() == 0) {
        inst = 1;
        mem = 0;
    }
    if (KnobInst.Value() == 0 && KnobMem.Value() == 1) {
        inst = 0;
        mem = 1;
    }

    readNum = 0;
    writeNum = 0;
    memNum = 0;
    instNum = 0;

    // get cur time and generate log
    auto currentTimePoint = std::chrono::system_clock::now();
    std::time_t currentTime = std::chrono::system_clock::to_time_t(currentTimePoint);
    std::stringstream time_str;
    time_str << std::put_time(std::localtime(&currentTime), "%Y%m%d_%H:%M");
    if (inst && !mem)
        logName = out_dir + "/" + appName + "/" + "inst_" + time_str.str();
    else if (!inst && mem)
        logName = out_dir + "/" + appName + "/" + "mem_" + time_str.str();
    else
        logName = out_dir + "/" + appName + "/" + "inst_mem_" + time_str.str();
    log_file = new ofstream(logName, ios::out | ios::binary);
}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */

int main(int argc, char* argv[])
{
    //trace = fopen("itrace.out", "w");

    // Initialize pin
    if (PIN_Init(argc, argv)) return Usage();

    custom_init(argc, argv);

    PIN_InitSymbols();

    // Register Instruction to be called to instrument instructions
    INS_AddInstrumentFunction(Instruction, 0);

    // Register Fini to be called when the application exits
    PIN_AddFiniFunction(Fini, 0);

    cerr << "=======================================================" << endl;
    cerr << "This application: '" << appName << "' is instrumented by inst_mem_num PINTOOL" << endl;
    cerr << "=======================================================" << endl;

    // Start the program, never returns
    PIN_StartProgram();

    return 0;
}
