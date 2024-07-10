#include "mem_controller.h"
#include "param.h"

#include <cassert>

AccessStat MemController::do_access(char rw_type, uint64_t addr) 
{
    return kReadHit;
}

uint64_t MemController::GetFreeBlock(uint64_t set_idx)
{
    int free_block_idx = 0;
    for (;(uint64_t)free_block_idx < (set_idx + 1) * kCacheAssoc; free_block_idx += 1) {
        if (dram_block_usage_[free_block_idx] == 0)
            return free_block_idx;
    }

    return -1;
}

uint64_t MemController::GetBloatBlock(uint64_t set_idx)
{
    int bloat_block_idx = 0;
    for (;(uint64_t)bloat_block_idx < (set_idx + 1) * kCacheAssoc; bloat_block_idx += 1) {
        if (dram_block_usage_[bloat_block_idx] >= 1)
            return bloat_block_idx;
    }

    return -1;
}

uint64_t MemController::GetUniformBlock(uint64_t set_idx)
{
    int Uniform_block_idx = 0;
    for (;(uint64_t)Uniform_block_idx < (set_idx + 1) * kCacheAssoc; Uniform_block_idx += 1) {
        if (dram_block_usage_[Uniform_block_idx] == 0)
            return Uniform_block_idx;
    }

    return -1;
}

void MemController::_UpdateBlockMetadata(uint64_t dram_pn, uint64_t hp_pn, HugePageStat hp_stat, 
    int way_offset, int remap_info, int bloat_degree)
{   
    assert(way_offset >= 0 && (uint64_t)way_offset < kCacheAssoc);

    hp_metadata_[hp_pn] = hp_stat;
    hp_way_offset_tbl_[hp_pn] = way_offset;
    hp_remap_tbl_[hp_pn] = remap_info;
    hp_bloat_degree_[hp_pn] = bloat_degree;

    dram_block_usage_[dram_pn] += 1;
    dram_block_rmap_[dram_pn].push_back(hp_pn);
}

void MemController::UpdateBlockMetadata(uint64_t hp_pn, HugePageStat hp_stat, int remap_info, int bloat_degree)
{
    // find candidate dram block
    uint64_t set_idx = (hp_pn) % (nr_dram_hp / kCacheAssoc);
    uint64_t dram_idx = set_idx + (hp_way_offset_tbl_[hp_pn]);

    uint64_t free_block_idx = GetFreeBlock(set_idx);
    uint64_t bloat_block_idx = GetBloatBlock(set_idx);
    uint64_t uniform_block_idx = GetBloatBlock(set_idx);

    if (hp_metadata_[hp_pn] == kCold) {
        // map to free block/map to already mapped block
        if ((uint64_t)free_block_idx < kCacheAssoc) {
            // free block
            assert(dram_block_usage_[free_block_idx] == 0);
            assert(dram_block_rmap_.size() == 0);

            _UpdateBlockMetadata(free_block_idx, hp_pn, hp_stat, 
                free_block_idx -  set_idx * kCacheAssoc, remap_info, bloat_degree);  
        } else if ((uint64_t)bloat_block_idx < kCacheAssoc){
            // no free block
            assert(dram_block_usage_[bloat_block_idx] > 1);
            assert(dram_block_rmap_.size() >= 1);
            
            _UpdateBlockMetadata(bloat_block_idx, hp_pn, hp_stat, 
                bloat_block_idx - set_idx * kCacheAssoc, remap_info, bloat_degree);
        } else if ((uint64_t)uniform_block_idx < kCacheAssoc) {
            assert(dram_block_usage_[uniform_block_idx] == 1);
            assert(dram_block_rmap_[uniform_block_idx].size() == 1);
            assert((uint64_t)(hp_way_offset_tbl_[dram_block_rmap_[uniform_block_idx][0]]) == 
                (uniform_block_idx - set_idx * kCacheAssoc));

            // modify Uniform to Hot Bloat
            uint64_t old_uniform_pn = dram_block_rmap_[uniform_block_idx][0];
            dram_block_rmap_.pop_back();
            _UpdateBlockMetadata(uniform_block_idx, old_uniform_pn, hp_stat, 
                hp_way_offset_tbl_[old_uniform_pn], 0, 1);

            // add new map
            _UpdateBlockMetadata(uniform_block_idx, hp_pn, hp_stat, 
                uniform_block_idx - set_idx * kCacheAssoc, remap_info, bloat_degree);
        } else {    
            assert(0);
        }
        
    } else if (hp_metadata_[hp_pn] == kHotUniform) {
        assert(dram_block_usage_[dram_idx] == 1);
        assert(dram_block_rmap_[dram_idx].size() == 1);
    } else if (hp_metadata_[hp_pn] == kHotBloat) {
        assert(dram_block_usage_[dram_idx] >= 1);
        assert(dram_block_rmap_[dram_idx].size() >= 1);
    }
}

void MemController::UpdateMetadata(uint64_t start_pn, std::vector<HugePageStat> huge_metadata,
    std::vector<int> huge_remap_info, std::vector<int> huge_block_degree)
{
    for (int idx = 0; (uint64_t)idx < huge_metadata.size(); idx += 1) {
        assert(huge_metadata[idx] != kInvalid);

        // Hot -> Cold
        if (huge_metadata[idx] == kCold) {
            uint64_t set_idx = (start_pn + idx) % (nr_dram_hp / kCacheAssoc);
            uint64_t dram_idx = set_idx + (hp_way_offset_tbl_[start_pn + idx]);

            if (hp_metadata_[start_pn + idx] == kHotUniform) {
                // Uniform Hot -> Cold
                assert(dram_block_usage_[dram_idx] == 1);
                assert(dram_block_rmap_[dram_idx].size() == 1);

                dram_block_usage_[dram_idx] = 0;
            } else if (hp_metadata_[start_pn + idx] == kHotBloat) {
                // Bloat Hot -> Cold                
                assert(dram_block_usage_[dram_idx] >= 1);
                assert(dram_block_rmap_[dram_idx].size() >= 1);
                
                dram_block_usage_[dram_idx] -= 1;
            } else {
                assert(dram_block_usage_[dram_idx] == 0);
                assert(dram_block_rmap_[dram_idx].size() == 0);
            }

            hp_metadata_[start_pn + idx] = kCold;
            hp_way_offset_tbl_[start_pn + idx] = -1;
            hp_remap_tbl_[start_pn + idx] = -1;
            dram_block_rmap_[dram_idx].clear();

            continue;
        } else {
            // Uniform Hot/Bloat Hot
            UpdateBlockMetadata(start_pn + idx, huge_metadata[idx],
                huge_remap_info[idx], huge_block_degree[idx]);
        }
    }

}