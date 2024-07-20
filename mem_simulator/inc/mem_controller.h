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

struct CacheBlock {
    bool valid;
    bool dirty;
    uint64_t tag;
};

struct LearnedStat {
    uint64_t uniform_cover = 0;
    uint64_t bloat_cover = 0;
    uint64_t cold_cover = 0;
    uint64_t bloat_hit_cur = 0;
};

class MemController {
    public:
        bool direct_map_ = false;
        int dram_ratio_;
        uint64_t cache_block_size_;
        uint64_t dram_size_;
        uint64_t nr_dram_hp_;
        uint64_t cxl_size_;
        uint64_t nr_cxl_hp_;
        std::vector<HugePageStat> hp_metadata_;
        std::vector<int> hp_way_offset_tbl_;
        std::vector<int> hp_remap_tbl_;
        std::vector<int> hp_bloat_degree_;
        std::vector<int> dram_block_usage_;  // dram-pn index, huge-page granilarity, how many huge page map to this block
        std::vector<std::vector<uint64_t>> dram_block_rmap_;  // dram-pn index, reverse map table for dram
        std::vector<CacheBlock> dram_blocks;
        LearnedStat learned_stat_;


        void ClearLearnedStat(void);
        AccessStat do_access(char rw_type, uint64_t cache_addr);
        void UpdateMetadata(uint64_t start_pn, std::vector<HugePageStat> huge_metadata,
            std::vector<std::vector<uint64_t>> huge_remap_group, std::vector<int> huge_remap_info,
            std::vector<int> huge_block_degree);

        MemController(bool direct_map, int dram_ratio, uint64_t cache_block_size, uint64_t dram_size, uint64_t cxl_size)
            :direct_map_(direct_map), dram_ratio_(dram_ratio), cache_block_size_(cache_block_size), dram_size_(dram_size),
            nr_dram_hp_(dram_size / (kHugePageSize / 1024 / 1024)), cxl_size_(cxl_size), nr_cxl_hp_(cxl_size / (kHugePageSize / 1024 / 1024)),
            hp_metadata_(nr_cxl_hp_, kCold), hp_way_offset_tbl_(nr_cxl_hp_, -1),
            hp_remap_tbl_(nr_cxl_hp_, -1), hp_bloat_degree_(nr_cxl_hp_, -1),
            dram_block_usage_(nr_cxl_hp_, 0), 
            dram_block_rmap_(nr_cxl_hp_),
            dram_blocks(dram_size_ * 1024 * 1024 / cache_block_size, {false, false, 0}) {};
        ~MemController(void){};

    private:
        uint64_t _GetDramAddr(uint64_t cache_addr);
        void _UpdateCacheBlockTag(char rw_type, uint64_t cache_addr);
        void _UpdateCacheBlockTag(char rw_type, uint64_t cache_addr, uint64_t dram_addr);
        bool DirectAccess(char rw_type, uint64_t cache_addr);
        bool LearnedAccess(char rw_type, uint64_t cache_addr);
        void ReplaceCacheBlockTag(uint64_t dram_start_cache_addr, uint64_t hp_pn);
        void ClearCacheBlockTag(uint64_t hp_pn);
        uint64_t GetFreeBlock(uint64_t set_idx);
        uint64_t GetBloatBlock(uint64_t set_idx);
        uint64_t GetUniformBlock(uint64_t set_idx);
        void _UpdateBlockMetadata(uint64_t dram_pn, uint64_t hp_pn, HugePageStat hp_stat, int way_offset,
            int remap_info, int bloat_degree);
        int UpdateBlockMetadata(uint64_t hp_pn, HugePageStat hp_stat, int remap_info, int bloat_degree, int remap_way_offset = -1);

};
#endif