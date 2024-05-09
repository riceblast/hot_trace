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
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include "pin.H"

using namespace std;

string out_dir = "./trace";
std::ofstream* out_raw_file;
std::ofstream* log_file;
string rawName;
string appName;
string logName;

int pagemap_fd = 0;
UINT64 traceStartPos;
UINT64 period;
UINT64 memPeriod;
UINT64 translation_failure;
UINT64 memDumpNum;
UINT64 maxMemSetting;
UINT64 memNum;
UINT64 instCount;

typedef struct {
    char type;  // 0:read, 1:write
    void* addr;
} addr_entry;
const size_t BUFFER_THRESHOLD = 10 * 1024 * 1024; // the overflow entry num
vector<addr_entry> buffer;

/* ===================================================================== */
// Command line switches
/* ===================================================================== */
KNOB< string > KnobOutputFile(KNOB_MODE_WRITEONCE, "pintool", "o", "pfn_test", "specify file name for output");
KNOB< UINT64 > KnobStartPos(KNOB_MODE_WRITEONCE, "pintool", "s", "0", "specify start point of memory");
KNOB< UINT64 > KnobMemPeriod(KNOB_MODE_WRITEONCE, "pintool", "p", "0x1fffffe", "specify period memory access num"); // 8M-period, ~10ms
//KNOB< UINT64 > KnobMaxMem(KNOB_MODE_WRITEONCE, "pintool", "n", "0xfffffffffffffff", "max memory access num");
KNOB< UINT64 > KnobMaxMem(KNOB_MODE_WRITEONCE, "pintool", "n", "0xfff", "max memory access num");

void cnt_ip(void)
{
    instCount++;
}

// Utility function to read physical address from /proc/self/pagemap
bool virtual_to_physical(uint64_t& physical, void* virtual_addr) {
    // Calculate the offset for the virtual address
    uint64_t offset = (reinterpret_cast<uint64_t>(virtual_addr) / sysconf(_SC_PAGESIZE)) * sizeof(uint64_t);
    
    // // Seek to the offset in the pagemap file
    // long int off = lseek(pagemap_fd, offset, SEEK_SET);
    // if (off != (long int)offset) {
    //     *out_raw_file << "lseek failure, off: " << off << ", offset: " << offset <<", fd: " << pagemap_fd << endl;
    //     *out_raw_file << "Error opening /proc/self/pagemap: " << strerror(errno) << endl;
    //     close(pagemap_fd);
    //     return false;
    // }

    // // Read the physical address from pagemap
    // uint64_t entry;
    // if (read(pagemap_fd, &entry, sizeof(entry)) != sizeof(entry)) {
    //     *out_raw_file << "read failure" << endl;
    //     close(pagemap_fd);
    //     return false;
    // }

    // 直接使用 pread 读取，无需 lseek
    uint64_t entry = 0;
    if (pread(pagemap_fd, &entry, sizeof(entry), offset) != sizeof(entry)) {
        *out_raw_file << "pread failure" << endl;
        *out_raw_file << "Error: " << strerror(errno) << endl;
        return false;
    }

    // Check if the page is present
    if ((entry & (1ULL << 63)) == 0) {
        *out_raw_file << "not present" << endl;
        close(pagemap_fd);
        return false;
    }

    // Extract the physical page number
    uint64_t page_frame_number = entry & ((1ULL << 55) - 1);
    physical = page_frame_number * sysconf(_SC_PAGESIZE) + 
        (reinterpret_cast<uint64_t>(virtual_addr) % sysconf(_SC_PAGESIZE));

    //close(pagemap_fd);
    return true;
}

// flush all entry 
void flush_once(void)
{
    for (const auto& entry : buffer) {
        const char* op = (entry.type == 0) ? "r" : "w";

        uint64_t physical_addr;
        if (virtual_to_physical(physical_addr, entry.addr)) {
            *out_raw_file << op << " " << entry.addr << " -> " << physical_addr << "\n";
        } else {
            *out_raw_file << op << " " << "N/A" << "\n"; // Physical address not available
            translation_failure++;
        }
        //*out_raw_file << op << " " << entry.addr << "\n";
    }

    buffer.clear();
    out_raw_file->flush();
}

// if buffer size is greater than theshold than flush
void flush_buffer_to_file(void) 
{
    if (buffer.size() >= BUFFER_THRESHOLD)
        flush_once();
}

void prepareNextFile(void) 
{
    if (memDumpNum >= memPeriod * period) {
        flush_once();
        out_raw_file->close();

        rawName = out_dir + "/" + appName + "/" + KnobOutputFile.Value() 
            + "_" + std::to_string(period++) + ".physical.trace";
        out_raw_file->open(rawName, ios::out | ios::binary);
    }
}

VOID dump_read(VOID* addr)
{
    prepareNextFile();
    flush_buffer_to_file();

    if (memNum >= traceStartPos && memDumpNum < maxMemSetting) {
        buffer.push_back({0, addr});
        memDumpNum++;
    }
    memNum++;
}

VOID dump_write(VOID* addr)
{
    prepareNextFile();
    flush_buffer_to_file();

    if (memNum >= traceStartPos && memDumpNum < maxMemSetting) {
        buffer.push_back({1, addr});
        memDumpNum++;
    }   
    memNum++;
}

// Pin calls this function every time a new instruction is encountered
VOID Instruction(INS ins, VOID* v)
{
    // Insert a call to printip before every instruction, and pass it the IP
    INS_InsertCall(ins, IPOINT_BEFORE, (AFUNPTR)cnt_ip, IARG_INST_PTR, IARG_END);

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
    flush_once();
    out_raw_file->close();

    if (pagemap_fd >= 0) {
        close(pagemap_fd);
        pagemap_fd = -1;
    }

    *log_file << "app name: " << appName << endl;
    *log_file << "start inst position: " << "0x" << hex << traceStartPos << endl;
    *log_file << "period num: " << dec << period << endl;
    *log_file << "period settings: " << "0x" << hex << memPeriod << endl;
    *log_file << "translation failure num: " << "0x" << hex << translation_failure << endl;
    *log_file << "dumped address num: " << "0x" << hex << memDumpNum << endl;
    *log_file << "total memory access num: " << "0x" << hex << memNum << endl;
    *log_file << "max mem setting: " << "0x" << hex << maxMemSetting << endl;
    *log_file << "total executed inst: " << "0x" << hex << instCount << endl;
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
        cerr << "mkdir " << out_dir + "/" + appName << endl;
    }

    period = 0;
    translation_failure = 0;
    memDumpNum = 0;
    memNum = 0;
    maxMemSetting = KnobMaxMem.Value();
    traceStartPos = KnobStartPos.Value();
    memPeriod = KnobMemPeriod.Value();

    // Open the pagemap file for the current process
    int fd = open("/proc/self/pagemap", O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "Error opening /proc/self/pagemap: %s\n", strerror(errno));
        exit(1);
    }

    rawName = out_dir + "/" + appName + "/" + KnobOutputFile.Value() 
        + "_" + std::to_string(period++) + ".physical.trace";
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
    cerr << "This application: '" << appName << "' is instrumented by pfn_dump PINTOOL" << endl;
    cerr << "=======================================================" << endl;

    // Start the program, never returns
    PIN_StartProgram();

    return 0;
}
