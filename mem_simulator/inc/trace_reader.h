#ifndef MEM_SIMULATOR_TRACE_READER_H_
#define MEM_SIMULATOR_TRACE_READER_H_

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>

#include "param.h"
#include "page_translator.h"

namespace fs = std::filesystem;

class TraceReader {
    public:
        std::string bench_name_;
        std::ifstream trace_stream_;
        uint64_t max_file_idx_;  // nr_trace_file - 1
        uint64_t cache_block_size_;
        PageTranslator page_translator_;
        
        bool Eof(void);
        uint64_t NextAddr(char& rw_type);
        uint64_t GetCurFile(void);

        TraceReader(uint64_t cache_block_size, uint64_t page_size, uint64_t cxl_range, std::string bench_name);
        ~TraceReader(){};
    
    private:
        uint64_t cur_file_;

        uint64_t CountTraces(const std::string& file_path);
        uint64_t Str2Addr(std::string str_addr);
        bool _IsValidTrace(const fs::path& path);
};

#endif