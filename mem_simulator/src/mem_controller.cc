#include "mem_controller.h"
#include "param.h"

#include <cassert>

void MemController::_UpdateCacheBlockTag(char rw_type, uint64_t byte_addr)
{
    uint64_t align_addr = byte_addr / cache_block_size_;
    uint64_t dram_addr = align_addr % dram_size_;

    dram_blocks[dram_addr].valid = true;
    dram_blocks[dram_addr].tag = align_addr;
    if (rw_type == 'R') {
        dram_blocks[dram_addr].dirty = false;
    } else {
        dram_blocks[dram_addr].dirty = true;
    }
}

bool MemController::DirectAccess(char rw_type, uint64_t byte_addr)
{
    uint64_t align_addr = byte_addr / cache_block_size_;
    uint64_t dram_addr = align_addr % dram_size_;

    if (dram_blocks[dram_addr].tag == align_addr &&
        dram_blocks[dram_addr].valid == true) {
        if (rw_type == 'W') {
            dram_blocks[dram_addr].dirty = true;
        }
        return true;
    } else {
        _UpdateCacheBlockTag(rw_type, byte_addr);
        return false;
    }
}

bool MemController::LearnedAccess(char rw_type, uint64_t byte_addr)
{
    uint64_t nr_sub_page_per_huge = (kHugePageSize) / (cache_block_size_);
    uint64_t hp_pn = byte_addr / (kHugePageSize);
    uint64_t set_idx = hp_pn % (nr_dram_hp_ / kCacheAssoc);
    uint64_t align_addr = byte_addr / cache_block_size_;
    assert(hp_metadata_[hp_pn] != kInvalid);

    if (hp_metadata_[hp_pn] == kCold) {
        return false;
    }

    if (hp_metadata_[hp_pn] == kHotUniform) {
        return true;
    }

    if (hp_metadata_[hp_pn] == kHotBloat) {
        uint64_t dram_addr = nr_sub_page_per_huge * (set_idx * kCacheAssoc) +  // set addr
            nr_sub_page_per_huge * hp_way_offset_tbl_[hp_pn]    // way addr
             + align_addr % (nr_sub_page_per_huge); // huge page inner addr
        
        if (dram_blocks[dram_addr].tag == align_addr &&
            dram_blocks[dram_addr].valid == true) {
            if (rw_type == 'W') {
                dram_blocks[dram_addr].dirty = true;
            }
            return true;
        } else {
            _UpdateCacheBlockTag(rw_type, byte_addr);
            return false;
        }
    }

    assert(0);
}

AccessStat MemController::do_access(char rw_type, uint64_t byte_addr) 
{
    assert(rw_type == 'R' || rw_type == 'W');

    bool hit = false;
    if (direct_map_) {
        hit = DirectAccess(rw_type, byte_addr);
    } else {
        hit = LearnedAccess(rw_type, byte_addr);
    }

    if (hit) {
        if (rw_type == 'R') {
            return kReadHit;
        } else {
            return kWriteHit;
        }
    } else {
        if (rw_type == 'R') {
            return kReadMiss;
        } else {
            return kWriteMiss;
        }
    }
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

int MemController::UpdateBlockMetadata(uint64_t hp_pn, HugePageStat hp_stat, int remap_info,
    int bloat_degree, int remap_way_offset)
{
    // find candidate dram block
    uint64_t set_idx = (hp_pn) % (nr_dram_hp_ / kCacheAssoc);
    uint64_t dram_idx = set_idx * kCacheAssoc + (hp_way_offset_tbl_[hp_pn]);
    int way_offset = -1;

    if (remap_way_offset >= 0) {
        _UpdateBlockMetadata(set_idx * kCacheAssoc + remap_way_offset , hp_pn,
            hp_stat, remap_way_offset, remap_info, bloat_degree);

        return way_offset;
    }

    uint64_t free_block_idx = GetFreeBlock(set_idx);
    uint64_t bloat_block_idx = GetBloatBlock(set_idx);
    uint64_t uniform_block_idx = GetBloatBlock(set_idx);

    if (hp_metadata_[hp_pn] == kCold) {
        // map to free block/map to already mapped block
        if ((uint64_t)free_block_idx < kCacheAssoc) {
            // free block
            assert(dram_block_usage_[free_block_idx] == 0);
            assert(dram_block_rmap_.size() == 0);

            way_offset = free_block_idx -  set_idx * kCacheAssoc;
            _UpdateBlockMetadata(free_block_idx, hp_pn, hp_stat, 
                way_offset, remap_info, bloat_degree);  
            if (hp_stat == kHotUniform) {
                ReplaceCacheBlockTag(hp_pn);
            }

        } else if ((uint64_t)bloat_block_idx < kCacheAssoc){
            // no free block
            assert(dram_block_usage_[bloat_block_idx] > 1);
            assert(dram_block_rmap_.size() >= 1);
            
            way_offset = bloat_block_idx - set_idx * kCacheAssoc;
            _UpdateBlockMetadata(bloat_block_idx, hp_pn, hp_stat, 
                way_offset, remap_info, bloat_degree);
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
            way_offset = uniform_block_idx - set_idx * kCacheAssoc;
            _UpdateBlockMetadata(uniform_block_idx, hp_pn, hp_stat, 
                way_offset, remap_info, bloat_degree);
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

    return way_offset;
}

void MemController::ReplaceCacheBlockTag(uint64_t hp_pn)
{
    uint64_t nr_sub_page_per_huge = (kHugePageSize) / (cache_block_size_); 
    for (uint64_t dram_addr = hp_pn * (nr_sub_page_per_huge); 
        dram_addr < (hp_pn + 1) * (nr_sub_page_per_huge); dram_addr += 1) {
        dram_blocks[dram_addr] = {true, false, dram_addr};
    }
}

void MemController::ClearCacheBlockTag(uint64_t hp_pn)
{
    uint64_t nr_sub_page_per_huge = (kHugePageSize) / (cache_block_size_); 
    for (uint64_t dram_addr = hp_pn * (nr_sub_page_per_huge); 
        dram_addr < (hp_pn + 1) * (nr_sub_page_per_huge); dram_addr += 1) {
            dram_blocks[dram_addr] = {false, false, 0};
        }
}

void MemController::UpdateMetadata(uint64_t start_pn, std::vector<HugePageStat> huge_metadata,
    std::vector<std::vector<uint64_t>> huge_remap_group, 
    std::vector<int> huge_remap_info,
    std::vector<int> huge_block_degree)
{
    // Hot Bloat
    for (const auto& group: huge_remap_group) {
        int way_offset = -1;
        for (const auto& hp_pn: group) {
            if (way_offset == -1) {
                way_offset = UpdateBlockMetadata(hp_pn, 
                    huge_metadata[hp_pn - start_pn], huge_remap_info[hp_pn - start_pn],
                    huge_block_degree[hp_pn - start_pn]);
                assert(way_offset != -1);
            } else {
                int result = UpdateBlockMetadata(hp_pn, 
                    huge_metadata[hp_pn - start_pn], huge_remap_info[hp_pn - start_pn],
                    huge_block_degree[hp_pn - start_pn], way_offset);
                assert(result == -1);
            }
        }
    }

    for (int idx = 0; (uint64_t)idx < huge_metadata.size(); idx += 1) {
        assert(huge_metadata[idx] != kInvalid);

        // Cold
        if (huge_metadata[idx] == kCold) {
            uint64_t set_idx = (start_pn + idx) % (nr_dram_hp_ / kCacheAssoc);
            uint64_t dram_idx = set_idx * kCacheAssoc + (hp_way_offset_tbl_[start_pn + idx]);

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

            ClearCacheBlockTag(start_pn + idx);

            continue;
        } else if (huge_metadata[idx] == kHotUniform){
            // Uniform Hot
            UpdateBlockMetadata(start_pn + idx, huge_metadata[idx],
                huge_remap_info[idx], huge_block_degree[idx]);
        } else {
            // assert kHotBloat in remapGroup
            //bool flag = false;
        }
    }

}