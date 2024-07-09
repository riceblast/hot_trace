#ifndef MEM_SIMULATOR_TRACE_READER_H_
#define MEM_SIMULATOR_TRACE_READER_H_

#include <cstdint>
#include <fstream>
#include <string>

#include "param.h"

class TraceReader {
    public:
        std::string bench_name_;
        std::ifstream trace_stream_;
        uint64_t max_seconds_;  // 运行到max_seconds_停止
        
        bool Eof(void);
        uint64_t NextAddr(char& rw_type, bool& flag);
        uint64_t GetCurFile(void);

        TraceReader(std::string bench_name, uint64_t max_seconds);
        ~TraceReader(){};
    
    private:
        uint64_t cur_file_;

        uint64_t CountTraces(const std::string& file_path);
        uint64_t Str2Addr(std::string str_addr);
};

#endif