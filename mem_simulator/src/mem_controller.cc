#include "mem_controller.h"
#include "param.h"

#include <cassert>

void MemController::ClearLearnedStat(void)
{
    learned_stat_.uniform_cover = 0;
    learned_stat_.bloat_cover = 0;
    learned_stat_.cold_cover = 0;
    learned_stat_.bloat_hit_cur = 0;
}

uint64_t MemController::_GetDramAddr(uint64_t cache_addr)
{
    assert(direct_map_);
    uint64_t dram_addr =  cache_addr % (dram_size_ * kMB / cache_block_size_);
    return dram_addr;
}

void MemController::_UpdateCacheBlockTag(char rw_type, uint64_t cache_addr)
{
    uint64_t dram_addr = _GetDramAddr(cache_addr);

    dram_blocks[dram_addr].valid = true;
    dram_blocks[dram_addr].tag = cache_addr;
    if (rw_type == 'R') {
        dram_blocks[dram_addr].dirty = false;
    } else {
        dram_blocks[dram_addr].dirty = true;
    }
}

void MemController::_UpdateCacheBlockTag(char rw_type, uint64_t cache_addr, uint64_t dram_addr)
{

    dram_blocks[dram_addr].valid = true;
    dram_blocks[dram_addr].tag = cache_addr;
    if (rw_type == 'R') {
        dram_blocks[dram_addr].dirty = false;
    } else {
        dram_blocks[dram_addr].dirty = true;
    }
}

bool MemController::DirectAccess(char rw_type, uint64_t cache_addr)
{
    uint64_t dram_addr = _GetDramAddr(cache_addr);

    if (dram_blocks[dram_addr].tag == cache_addr &&
        dram_blocks[dram_addr].valid == true) {
        if (rw_type == 'W') {
            dram_blocks[dram_addr].dirty = true;
        }
        return true;
    } else {
        _UpdateCacheBlockTag(rw_type, cache_addr);
        return false;
    }
}

bool MemController::LearnedAccess(char rw_type, uint64_t cache_addr)
{
    uint64_t nr_sub_page_per_huge = (kHugePageSize) / (cache_block_size_);
    uint64_t hp_pn = cache_addr / nr_sub_page_per_huge;
    uint64_t set_idx = hp_pn % (nr_dram_hp_ / kCacheAssoc);
    uint64_t way_offset = hp_way_offset_tbl_[hp_pn];
    assert(hp_metadata_[hp_pn] != kInvalid);

    if (hp_metadata_[hp_pn] == kCold) {
        learned_stat_.cold_cover += 1;
        return false;
    }

    if (hp_metadata_[hp_pn] == kHotUniform) {
        assert(way_offset < kCacheAssoc);
        assert(dram_block_usage_[set_idx * kCacheAssoc + way_offset] == 1);
        assert(dram_block_rmap_[set_idx * kCacheAssoc + way_offset].size() == 1);
        assert(dram_block_rmap_[set_idx * kCacheAssoc + way_offset][0] == hp_pn);
        learned_stat_.uniform_cover += 1;
        return true;
    }

    if (hp_metadata_[hp_pn] == kHotBloat) {
        learned_stat_.bloat_cover += 1;
        uint64_t dram_addr = nr_sub_page_per_huge * (set_idx * kCacheAssoc) +  // set addr
            nr_sub_page_per_huge * hp_way_offset_tbl_[hp_pn]    // way addr
             + cache_addr % (nr_sub_page_per_huge); // huge page inner addr
        uint64_t dram_huge_block = set_idx * kCacheAssoc + hp_way_offset_tbl_[hp_pn];

        assert(dram_block_usage_[dram_huge_block] >= 1);
        assert(dram_block_rmap_[dram_huge_block].size() >= 1);
        int is_pn_exists = 0;
        for (const auto& pn: dram_block_rmap_[dram_huge_block]) {
            if (pn == hp_pn) {
                is_pn_exists += 1;
            }
        }
        assert(is_pn_exists == 1);
        
        if (dram_blocks[dram_addr].tag == cache_addr &&
            dram_blocks[dram_addr].valid == true) {
            learned_stat_.bloat_hit_cur += 1;
            if (rw_type == 'W') {
                dram_blocks[dram_addr].dirty = true;
            }
            return true;
        } else {
            _UpdateCacheBlockTag(rw_type, cache_addr, dram_addr);
            return false;
        }
    }

    assert(0);
}

AccessStat MemController::do_access(char rw_type, uint64_t cache_addr) 
{
    assert(rw_type == 'R' || rw_type == 'W');

    bool hit = false;
    if (direct_map_) {
        hit = DirectAccess(rw_type, cache_addr);
    } else {
        hit = LearnedAccess(rw_type, cache_addr);
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
    uint64_t free_block_idx = set_idx * kCacheAssoc;
    for (;(uint64_t)free_block_idx < (set_idx + 1) * kCacheAssoc; free_block_idx += 1) {
        if (dram_block_usage_[free_block_idx] == 0) {
            assert(dram_block_rmap_[free_block_idx].size() == 0);
            return free_block_idx;
        }
    }

    return -1;
}

uint64_t MemController::GetBloatBlock(uint64_t set_idx)
{
    uint64_t bloat_block_idx =  set_idx * kCacheAssoc;
    for (;(uint64_t)bloat_block_idx < (set_idx + 1) * kCacheAssoc; bloat_block_idx += 1) {
        if (dram_block_usage_[bloat_block_idx] > 1) {
            assert(hp_metadata_[dram_block_rmap_[bloat_block_idx][0]] == kHotBloat &&
                dram_block_rmap_[bloat_block_idx].size() > 1);
            return bloat_block_idx;
        }
    }

    return -1;
}

uint64_t MemController::GetUniformBlock(uint64_t set_idx)
{
    uint64_t Uniform_block_idx =  set_idx * kCacheAssoc;
    for (;(uint64_t)Uniform_block_idx < (set_idx + 1) * kCacheAssoc; Uniform_block_idx += 1) {
        if (dram_block_usage_[Uniform_block_idx] == 1) {
            assert((hp_metadata_[dram_block_rmap_[Uniform_block_idx][0]] == kHotUniform ||
                hp_metadata_[dram_block_rmap_[Uniform_block_idx][0]] == kHotBloat) &&
                dram_block_rmap_[Uniform_block_idx].size() == 1);
            return Uniform_block_idx;
        }
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
    for (const auto& pn: dram_block_rmap_[dram_pn]) {
        if (pn == hp_pn)
            assert(0);
    }

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
    uint64_t uniform_block_idx = GetUniformBlock(set_idx);

    if (hp_metadata_[hp_pn] == kCold) {
        // kCold -> Bloat/Uniform hot
        // map to free block/map to already mapped block
        if ((uint64_t)(free_block_idx - set_idx * kCacheAssoc) < kCacheAssoc) {
            // free block
            assert(dram_block_usage_[free_block_idx] == 0);
            assert(dram_block_rmap_[free_block_idx].size() == 0);
            assert(free_block_idx >= set_idx * kCacheAssoc);

            way_offset = free_block_idx -  set_idx * kCacheAssoc;
            _UpdateBlockMetadata(free_block_idx, hp_pn, hp_stat, 
                way_offset, remap_info, bloat_degree);  
            if (hp_stat == kHotUniform) {
                ReplaceCacheBlockTag(dram_idx, hp_pn);
            }

        } else if ((uint64_t)(bloat_block_idx - set_idx * kCacheAssoc) < kCacheAssoc){
            // no free block
            assert(dram_block_usage_[bloat_block_idx] > 1);
            assert(dram_block_rmap_[bloat_block_idx].size() > 1);
            assert(bloat_block_idx >= set_idx * kCacheAssoc);
            
            assert(hp_stat == kHotBloat || hp_stat == kHotUniform);
            way_offset = bloat_block_idx - set_idx * kCacheAssoc;
            if (hp_stat == kHotUniform) {
                _UpdateBlockMetadata(bloat_block_idx, hp_pn, kHotBloat, 
                    way_offset, 0, bloat_degree); 
            } else {
                _UpdateBlockMetadata(bloat_block_idx, hp_pn, hp_stat, 
                    way_offset, remap_info, bloat_degree);
            }

        } else if ((uint64_t)(uniform_block_idx - set_idx * kCacheAssoc)< kCacheAssoc) {
            assert(dram_block_usage_[uniform_block_idx] == 1);
            assert(dram_block_rmap_[uniform_block_idx].size() == 1);
            assert((uint64_t)(hp_way_offset_tbl_[dram_block_rmap_[uniform_block_idx][0]]) == 
                (uniform_block_idx - set_idx * kCacheAssoc));
            assert(uniform_block_idx >= set_idx * kCacheAssoc);

            // modify Uniform to Hot Bloat
            uint64_t old_uniform_pn = dram_block_rmap_[uniform_block_idx][0];
            dram_block_usage_[uniform_block_idx] -= 1;
            dram_block_rmap_[uniform_block_idx].pop_back();
            _UpdateBlockMetadata(uniform_block_idx, old_uniform_pn, kHotBloat, 
                hp_way_offset_tbl_[old_uniform_pn], 0, 1);

            // add new map
            assert(hp_stat == kHotBloat || hp_stat == kHotUniform);
            way_offset = uniform_block_idx - set_idx * kCacheAssoc;
            if (hp_stat == kHotUniform) {
                _UpdateBlockMetadata(uniform_block_idx, hp_pn, kHotBloat, 
                    way_offset, 0, bloat_degree);
            } else {
                _UpdateBlockMetadata(uniform_block_idx, hp_pn, hp_stat, 
                    way_offset, remap_info, bloat_degree);
            }

        } else {    
            assert(0);
        }
        
    } else if (hp_metadata_[hp_pn] == kHotUniform) {
        assert(dram_block_usage_[dram_idx] == 1);
        assert(dram_block_rmap_[dram_idx].size() == 1);

        assert(0);
    } else if (hp_metadata_[hp_pn] == kHotBloat) {
        assert(dram_block_usage_[dram_idx] >= 1);
        assert(dram_block_rmap_[dram_idx].size() >= 1);

        way_offset = hp_way_offset_tbl_[hp_pn];
    }

    return way_offset;
}

void MemController::ReplaceCacheBlockTag(uint64_t dram_start_cache_addr, uint64_t hp_pn)
{
    uint64_t nr_sub_page_per_huge = (kHugePageSize) / (cache_block_size_); 

    for (uint64_t dram_cache_addr = dram_start_cache_addr;
        dram_cache_addr < dram_start_cache_addr + nr_sub_page_per_huge; dram_cache_addr += 1) {
            assert(dram_cache_addr < dram_blocks.size());
            dram_blocks[dram_cache_addr] = {true, false, hp_pn * nr_sub_page_per_huge};
        }
}

void MemController::ClearCacheBlockTag(uint64_t hp_pn)
{
    uint64_t nr_sub_page_per_huge = (kHugePageSize) / (cache_block_size_); 
    for (uint64_t dram_addr = hp_pn * (nr_sub_page_per_huge); 
        dram_addr < (hp_pn + 1) * (nr_sub_page_per_huge) && dram_addr < dram_size_ * kMB / cache_block_size_; 
        dram_addr += 1) {
            dram_blocks[dram_addr] = {false, false, 0};
        }
}

void MemController::UpdateMetadata(uint64_t start_pn, 
    std::vector<HugePageStat> huge_metadata,
    std::vector<std::vector<uint64_t>> huge_remap_group, 
    std::vector<int> huge_remap_info,
    std::vector<int> huge_block_degree)
{
    // Hot Bloat
    uint64_t nr_bloat_hp = 0;
    uint64_t nr_cold_hp = 0;
    uint64_t nr_uniform_hp = 0;
    for (const auto& group: huge_remap_group) {
        // FIXME if exists hugepage was bloat, skip this group
        nr_bloat_hp += group.size();
        bool flag = false;
        for (const auto& hp_pn: group) {
            if (hp_metadata_[start_pn + hp_pn] == kHotBloat) {
                flag = true;
                break;
            }
        }
        if (flag) {
            continue;   // skip this group
        }

        // if block was uniform, clear the block
        for (const auto& hp_pn: group) {
            if (hp_metadata_[start_pn + hp_pn] == kHotUniform) {
                uint64_t set_idx = (start_pn + hp_pn) % (nr_dram_hp_ / kCacheAssoc);
                uint64_t dram_idx = set_idx * kCacheAssoc + (hp_way_offset_tbl_[start_pn + hp_pn]);
                assert(hp_way_offset_tbl_[start_pn + hp_pn] != -1 && 
                    (uint64_t)hp_way_offset_tbl_[start_pn + hp_pn] < kCacheAssoc);
                assert(dram_block_usage_[dram_idx] == 1);
                assert(dram_block_rmap_[dram_idx].size() == 1);

                dram_block_usage_[dram_idx] = 0;
                dram_block_rmap_[dram_idx].clear();
                hp_metadata_[start_pn + hp_pn] = kCold;
                hp_way_offset_tbl_[start_pn + hp_pn] = -1;
                hp_remap_tbl_[start_pn + hp_pn] = -1;
                hp_bloat_degree_[start_pn + hp_pn] = 0;

                ClearCacheBlockTag(start_pn + hp_pn);
            }
        }

        int way_offset = -1;
        for (const auto& hp_pn: group) {
            if (way_offset == -1) {
                way_offset = UpdateBlockMetadata(hp_pn + start_pn, 
                     huge_metadata[hp_pn], huge_remap_info[hp_pn],
                     huge_block_degree[hp_pn]);
                assert(way_offset != -1);
            } else {
                int result = UpdateBlockMetadata(hp_pn + start_pn, 
                    huge_metadata[hp_pn], huge_remap_info[hp_pn],
                    huge_block_degree[hp_pn], way_offset);
                assert(result == -1);
            }
        }
    }

    // Cold & Uniform Hot
    for (int idx = 0; (uint64_t)idx < huge_metadata.size(); idx += 1) {
        assert(huge_metadata[idx] != kInvalid);

        // Cold
        if (huge_metadata[idx] == kCold) {
            nr_cold_hp += 1;
            uint64_t set_idx = (start_pn + idx) % (nr_dram_hp_ / kCacheAssoc);
            uint64_t dram_idx = set_idx * kCacheAssoc + (hp_way_offset_tbl_[start_pn + idx]);

            if (hp_metadata_[start_pn + idx] == kHotUniform) {
                // Uniform Hot -> Cold
                assert(dram_block_usage_[dram_idx] == 1);
                assert(dram_block_rmap_[dram_idx].size() == 1);

                dram_block_usage_[dram_idx] = 0;
                dram_block_rmap_[dram_idx].clear();
            } else if (hp_metadata_[start_pn + idx] == kHotBloat) {
                // Bloat Hot -> Cold                
                assert(dram_block_usage_[dram_idx] >= 1);
                assert(dram_block_rmap_[dram_idx].size() >= 1);
                assert((uint64_t)(dram_block_usage_[dram_idx]) == dram_block_rmap_[dram_idx].size());
                
                dram_block_usage_[dram_idx] -= 1;
                uint64_t erase_cnt = 0;
                for (auto it = dram_block_rmap_[dram_idx].begin(); 
                    it < dram_block_rmap_[dram_idx].end(); it++) {
                    if ((*it) == start_pn + idx) {
                        dram_block_rmap_[dram_idx].erase(it);
                        erase_cnt += 1;
                    }
                }
                assert(erase_cnt == 1);
            } else {
                // Cold -> Cold
                // assert(dram_block_usage_[dram_idx] == 0);
                // assert(dram_block_rmap_[dram_idx].size() == 0);
            }

            hp_metadata_[start_pn + idx] = kCold;
            hp_way_offset_tbl_[start_pn + idx] = -1;
            hp_remap_tbl_[start_pn + idx] = -1;
            hp_bloat_degree_[start_pn + idx] = 0;
            //dram_block_rmap_[dram_idx].clear();

            ClearCacheBlockTag(start_pn + idx);

            continue;
        } else if (huge_metadata[idx] == kHotUniform){
            nr_uniform_hp += 1;
            // Uniform Hot
            // ignore: Uniform/Bloat -> Uniform
            // consider: Cold -> Uniform
            if (hp_metadata_[start_pn + idx] == kCold) {
                UpdateBlockMetadata(start_pn + idx, huge_metadata[idx],
                    huge_remap_info[idx], huge_block_degree[idx]);
            }
        } else {
            // assert kHotBloat in remapGroup
            bool flag = false;
            for (const auto& group: huge_remap_group) {
                for (const auto& hp_pn: group) {
                    if (hp_pn == (uint64_t)idx) {
                        flag = true;
                        break;
                    }
                }
                if (flag)
                    break;
            }
            assert(flag);
        }
    }

    assert(kNrHugePagePerSeg == (nr_bloat_hp + nr_cold_hp + nr_uniform_hp));

}