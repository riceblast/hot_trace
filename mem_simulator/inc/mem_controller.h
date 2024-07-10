#ifndef MEM_SIMULATOR_MEM_CONTROLLER_H_
#define MEM_SIMULATOR_MEM_CONTROLLER_H_

#include "param.h"

#include <cstdint>
#include <vector>

enum HugePageStat {
    kCold = 0,
    kHotUniform,
    kHotBloat,
    kInvalid
};

enum AccessStat {
    kReadHit = 0,
    kWriteHit,
    kReadMiss,
    kWriteMiss
};

class MemController {
    public:
        bool direct_map_ = false;
        int dram_ratio_;
        uint64_t dram_size_;
        uint64_t nr_dram_hp;
        uint64_t cxl_size_;
        uint64_t huge_page_num_;
        std::vector<HugePageStat> hp_metadata_;
        std::vector<int> hp_way_offset_tbl_;
        std::vector<int> hp_remap_tbl_;
        std::vector<int> hp_bloat_degree_;
        std::vector<int> dram_block_usage_;  // dram-pn index, huge-page granilarity, how many huge page map to this block
        std::vector<std::vector<uint64_t>> dram_block_rmap_;  // dram-pn index, reverse map table for dram

        AccessStat do_access(char rw_type, uint64_t addr);
        void UpdateMetadata(uint64_t start_pn, std::vector<HugePageStat> huge_metadata,
            std::vector<int> huge_remap_info, std::vector<int> huge_block_degree);

        MemController(bool direct_map, int dram_ratio, uint64_t dram_size, uint64_t cxl_size)
            :direct_map_(direct_map), dram_ratio_(dram_ratio), dram_size_(dram_size),
            nr_dram_hp(dram_size / kHugePageSize), cxl_size_(cxl_size), huge_page_num_(cxl_size / 2 * 1024 * 1024),
            hp_metadata_(huge_page_num_, kCold), hp_way_offset_tbl_(huge_page_num_, -1),
            hp_remap_tbl_(huge_page_num_, -1), hp_bloat_degree_(huge_page_num_, -1),
            dram_block_usage_(huge_page_num_, 0), 
            dram_block_rmap_(huge_page_num_) {};
        ~MemController(void){};

    private:
        uint64_t GetFreeBlock(uint64_t set_idx);
        uint64_t GetBloatBlock(uint64_t set_idx);
        uint64_t GetUniformBlock(uint64_t set_idx);
        void _UpdateBlockMetadata(uint64_t dram_pn, uint64_t hp_pn, HugePageStat hp_stat, int way_offset,
            int remap_info, int bloat_degree);
        void UpdateBlockMetadata(uint64_t hp_pn, HugePageStat hp_stat, int remap_info, int bloat_degree);

};
#endif