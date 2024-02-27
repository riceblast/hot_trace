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

//FILE* trace;
string out_dir = "./trace";
//std::ostream* out_raw = &cerr;
//std::ostream* out_info = &cerr;
std::ofstream* out_raw_file;
std::ofstream* log_file;
string rawName;
string appName;
string logName;

bool only_profile_num = false;
UINT64 traceStartPos;
UINT64 period;
UINT64 memPeriod;
UINT64 memDumpNum;
UINT64 maxMemSetting;
UINT64 memNum;
UINT64 instCount;

/* ===================================================================== */
// Command line switches
/* ===================================================================== */
KNOB< string > KnobOutputFile(KNOB_MODE_WRITEONCE, "pintool", "o", "test", "specify file name for output");
KNOB< UINT64 > KnobStartPos(KNOB_MODE_WRITEONCE, "pintool", "s", "0", "specify start point");
KNOB< UINT64 > KnobMemPeriod(KNOB_MODE_WRITEONCE, "pintool", "p", "0xffffff", "specify period memory access num");
KNOB< UINT64 > KnobMaxMem(KNOB_MODE_WRITEONCE, "pintool", "n", "0xfffffffffffffff", "max memory access num");
KNOB< BOOL > knobProfileMemNum(KNOB_MODE_WRITEONCE, "pintool", "mem_num", "", "only count the total memroy access number");

// This function is called before every instruction is executed
// and prints the IP
//VOID printip(VOID* ip) { fprintf(trace, "%p\n", ip); }

VOID dump_read(VOID* addr)
{
    if (memDumpNum >= memPeriod * period && !only_profile_num) {
        out_raw_file->close();

        rawName = out_dir + "/" + appName + "/" + KnobOutputFile.Value() 
            + "_" + std::to_string(period++) + ".raw.trace";
        out_raw_file->open(rawName, ios::out | ios::binary);
    }

    if (memDumpNum < maxMemSetting && !only_profile_num) {
        *out_raw_file << "r " << addr << "\n";
        memDumpNum++;
    }
    memNum++;
}

VOID dump_write(VOID* addr)
{
    if (memDumpNum >= memPeriod * period && !only_profile_num) {
        out_raw_file->close();

        rawName = out_dir + "/" + appName + "/" + KnobOutputFile.Value() 
            + "_" + std::to_string(period++) + ".raw.trace";
        out_raw_file->open(rawName, ios::out | ios::binary);
    }

    if (memDumpNum < maxMemSetting && !only_profile_num) {
        *out_raw_file << "w " << addr << "\n";
        memDumpNum++;
    }   
    memNum++;
}

// Pin calls this function every time a new instruction is encountered
VOID Instruction(INS ins, VOID* v)
{
    // Insert a call to printip before every instruction, and pass it the IP
    //INS_InsertCall(ins, IPOINT_BEFORE, (AFUNPTR)printip, IARG_INST_PTR, IARG_END);

    // instrument memory reads and writes
    UINT32 memOperands = INS_MemoryOperandCount(ins);

    // Iterate over each memory operand of the instruction.
    for (UINT32 memOp = 0; memOp < memOperands; memOp++) {
        if (INS_MemoryOperandIsRead(ins, memOp))
            INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)dump_read, 
                IARG_MEMORYOP_EA, memOp, IARG_END);
        if (INS_MemoryOperandIsWritten(ins, memOp))
            INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)dump_write, 
                IARG_MEMORYOP_EA, memOp, IARG_END);
    }
}

// This function is called when the application exits
VOID Fini(INT32 code, VOID* v)
{
    out_raw_file->close();
    *log_file << "app name: " << appName << endl;
    *log_file << "start inst position: " << "0x" << hex << traceStartPos << endl;
    *log_file << "period num: " << dec << period << endl;
    *log_file << "period settings: " << "0x" << hex << memPeriod << endl;
    *log_file << "dumped address num: " << "0x" << hex << memDumpNum << endl;
    *log_file << "total memory access num: " << "0x" << hex << memNum << endl;
    *log_file << "max mem setting: " << "0x" << hex << maxMemSetting << endl;
    //*log_file << "total inst cnt: " << instCount << endl;
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

    period = 0;
    memDumpNum = 0;
    memNum = 0;
    only_profile_num = knobProfileMemNum.Value();
    //cerr << "option: " << only_profile_num << endl;
    maxMemSetting = KnobMaxMem.Value();
    traceStartPos = KnobStartPos.Value();
    memPeriod = KnobMemPeriod.Value();

    rawName = out_dir + "/" + appName + "/" + KnobOutputFile.Value() 
        + "_" + std::to_string(period++) + ".raw.trace";
    out_raw_file = new ofstream(rawName, ios::out | ios::binary);
    

    // get cur time and generate log
    auto currentTimePoint = std::chrono::system_clock::now();
    std::time_t currentTime = std::chrono::system_clock::to_time_t(currentTimePoint);
    std::stringstream time_str;
    time_str << std::put_time(std::localtime(&currentTime), "%Y%m%d_%H:%M");
    logName = out_dir + "/" + appName + "/" + "log_" + time_str.str();
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
    cerr << "This application: " << appName << " is instrumented by vpn_dump PINTOOL" << endl;
    cerr << "=======================================================" << endl;

    // Start the program, never returns
    PIN_StartProgram();

    return 0;
}
