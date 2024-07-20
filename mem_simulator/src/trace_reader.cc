#include "trace_reader.h"

#include <cassert>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <sstream>
#include <string>

#include "param.h"
#include "page_translator.h"

namespace fs = std::filesystem;

bool TraceReader::Eof()
{
    if ((cur_file_ >= max_file_idx_) &&
        trace_stream_.eof())
        return true;
    else
        return false;
}

uint64_t TraceReader::Str2Addr(std::string str_addr)
{
    uint64_t addr = 0;
    try {
        addr = std::stoull(str_addr, nullptr, 16);
    } catch(const std::invalid_argument& ia) {
        std::cerr << "Invalid argument exception when calling stoull" << std::endl;
        std::cerr << "Invalid argument: " << str_addr << std::endl;
        assert(0);
    } catch (const std::out_of_range& oor) {
        std::cerr << "The number is out of range" << std::endl;
        std::cerr << "Out range number: " << str_addr << std::endl;
        assert(0);
    }
    return addr;
}

uint64_t TraceReader::NextAddr(char& rw_type)
{
    std::string line;

    if (trace_stream_.eof() && cur_file_ < max_file_idx_) {
        std::string trace_file_name = bench_name_ + "_" +  std::to_string(++cur_file_) + ".out";
        if(!fs::exists(kRawDataPathPrefix + bench_name_ + "/" + trace_file_name)) {
            std::cerr << "Bench: " << bench_name_ << " does not exists\n";
            assert(0);
        }

        trace_stream_.close();
        trace_stream_.open(kRawDataPathPrefix + "/" + bench_name_ + "/" + trace_file_name);
        std::cout << "Open Trace: " << trace_file_name << std::endl;
    }

    getline(trace_stream_, line);
    std::istringstream iss(line);

    char op_type;
    std::string virtual_address, physical_address;
    if (iss >> op_type >> virtual_address >> physical_address) {
        assert(op_type == 'R' || op_type == 'W');
        rw_type = op_type;
        uint64_t byte_addr = Str2Addr(virtual_address);
        uint64_t hp_pn = page_translator_.Translate(byte_addr);
        uint64_t cache_vir_addr = byte_addr / cache_block_size_;
        uint64_t nr_sub_page_per_hp = kHugePageByteSize / cache_block_size_;
        uint64_t cache_phy_addr = hp_pn * nr_sub_page_per_hp + (cache_vir_addr % nr_sub_page_per_hp);
        
        return cache_phy_addr;
    } else {
        return -1;
    }
}

uint64_t TraceReader::GetCurFile(void)
{
    return cur_file_;
}

bool TraceReader::_IsValidTrace(const fs::path& path)
{
    // trace path should start with 'bench_name_', ends with .out
    std::string filename = path.filename().string();
    return filename.rfind(bench_name_, 0) == 0 && filename.size() > 4 && filename.substr(filename.size() - 4) == ".out";
}

uint64_t TraceReader::CountTraces(const std::string& path) {
    uint64_t file_count = 0;

    try {
        for (const auto& entry : fs::directory_iterator(path)) {
            if (fs::is_regular_file(entry.path()) && _IsValidTrace(entry.path())) {
                ++file_count;
            }
        }
    } catch (const fs::filesystem_error& ex) {
        std::cerr << "Error accessing folder: " << ex.what() << std::endl;
        assert(0);
    }

    return file_count;
}

TraceReader::TraceReader(uint64_t cache_block_size, uint64_t page_size, uint64_t cxl_range ,std::string bench_name)
{
    bench_name_ = bench_name;
    cache_block_size_ = cache_block_size;
    page_translator_ = PageTranslator(page_size, cxl_range);

    cur_file_ = 0;
    std::string full_raw_data_path = kRawDataPathPrefix + "/" + bench_name;
    if (!fs::exists(full_raw_data_path)) {
        std::cerr << "Bench Path: " << full_raw_data_path << " does not exists\n";
        assert(0);
    }

    std::string trace_name = bench_name_ + "_" +  std::to_string(cur_file_) + ".out";
    if (!fs::exists(full_raw_data_path + "/" + trace_name)) {
        std::cerr << "Bench: " << full_raw_data_path + "/" + trace_name << " does not exists\n";
        assert(0);
    }
    uint64_t file_num = CountTraces(full_raw_data_path);
    max_file_idx_ = file_num - 1;
    std::cout << "file trace num: " << file_num << std::endl;

    trace_stream_.open(full_raw_data_path + "/" + trace_name);
    std::cout << "Open Trace: " << trace_name << std::endl;
}