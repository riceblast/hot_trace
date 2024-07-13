#include "access_freq_tracker.h"
#include "param.h"

#include <cassert>
#include <fstream>
#include <iostream>
#include <vector>
#include <utility>

void AccessFreqTracker::ClearHugePageState(void)
{
    hot_thres_ = 0;

    // clear access hist
    for (auto& entry: access_hist_) {
        entry = 0;
    }

    // clear huge page metadata
    for (auto& state: huge_metadata_) {
        state = kInvalid;
    }

    // clear bitmap
    for (auto& row: huge_bitmaps_) {
        for (auto& entry: row) {
            entry = 0;
        }
    }

    // clear huge hot bloat degree info
    for (auto &degree: huge_bloat_degree_) {
        degree = 0;
    }

    // clear aggregate info
    huge_remap_group_.clear();

    // clear remap info
    for (auto& remap: huge_remap_info_) {
        remap = -1;
    }
}

void AccessFreqTracker::NewPeriod(uint64_t start_pn)
{
    start_pn_ = start_pn;
    end_pn_ = start_pn + kNrHugePagePerSeg;

    cm_sketch_.Clear();
    ClearHugePageState();
}

void AccessFreqTracker::UpdateAccessFreq(uint64_t addr)
{
    cm_sketch_.Insert(addr);
}

void AccessFreqTracker::RecordBitMap(int pn_idx, uint64_t huge_pn)
{
    for (uint64_t cache_block_addr = huge_pn * (kHugePageSize / cache_block_size_);
        cache_block_addr < (huge_pn + 1) * (kHugePageSize / cache_block_size_); cache_block_addr += 1) {
            uint64_t access_freq = cm_sketch_.Query(cache_block_addr);
            if (access_freq >= hot_thres_) {
                int cache_block_idx = cache_block_addr - huge_pn * (kHugePageSize / cache_block_size_);
                assert((uint64_t)pn_idx < huge_bitmaps_.size());
                assert((uint64_t)cache_block_idx < huge_bitmaps_[pn_idx].size());
                assert((uint64_t)huge_bitmaps_[pn_idx][cache_block_idx] == 0);
                huge_bitmaps_[pn_idx][cache_block_idx] = 1;
            }
        }
}

void AccessFreqTracker::UpdateHotColdMetadata(void)
{
    std::vector<uint64_t> access_hist_(1 << cm_sketch_.count_bit_, 0);
    
    // get access freq histogram
    uint64_t start_cache_addr = start_pn_ * (kHugePageSize / cache_block_size_);
    uint64_t end_cache_addr = end_pn_ * (kHugePageSize / cache_block_size_);
    for (uint64_t cache_block_addr = start_cache_addr; cache_block_addr < end_cache_addr;
        cache_block_addr += 1) {
        uint64_t cnt = cm_sketch_.Query(cache_block_addr);
        if (cnt >= access_hist_.size()) {
            std::cerr << "Access Hist construction error: " << cnt << std::endl;
            assert(0);
        }
        access_hist_[cnt] += 1;
    }

    uint64_t capcity_threshold = kNrHugePagePerSeg * kHugePageSize / cache_block_size_ / dram_ratio_; //dram cap count threshold(256B)
    uint64_t cur_capacity = 0;

    int hot_thres = access_hist_.size() - 1;
    for (; hot_thres >= 0; hot_thres -= 1) {
        if (cur_capacity + access_hist_[hot_thres] >= capcity_threshold) {
            break;
        }
        cur_capacity += access_hist_[hot_thres];
    }
    hot_thres_ = hot_thres;

    // distinguish hot/cold
    for (uint64_t huge_pn = start_pn_; huge_pn < end_pn_; huge_pn++) {
        uint64_t sub_hot_page_num = 0;
        for (uint64_t cache_idx = 0; cache_idx < (kHugePageSize / cache_block_size_); cache_idx += 1) {
            if (cm_sketch_.Query(huge_pn * (kHugePageSize / cache_block_size_) + cache_idx) >= hot_thres_) {
                sub_hot_page_num += 1;
            }
        }

        uint64_t bloat_degree = 0;
        while(bloat_degree <= kNrBloatDegree) {
            if (sub_hot_page_num >= (kHugePageSize / cache_block_size_) / (1 << bloat_degree)) {
                break;
            }
            bloat_degree += 1;
        }

        //record bloat_degree, 0: cold page, 1~kNrBloatDegree: > 1/2^degree
        if (bloat_degree > kNrBloatDegree) {
            huge_bloat_degree_[huge_pn - start_pn_] = 0;
        } else {
            huge_bloat_degree_[huge_pn - start_pn_] = bloat_degree;
        }
    }

    // record hot/cold info
    for (uint64_t huge_pn = start_pn_; huge_pn < end_pn_; huge_pn++) {
        int pn_idx = huge_pn - start_pn_;
        if (huge_bloat_degree_[pn_idx] == 0) {
            huge_metadata_[pn_idx] = kCold;
        } else if (huge_bloat_degree_[pn_idx] == 1) {
            huge_metadata_[pn_idx] = kHotUniform;
        } else {
            huge_metadata_[pn_idx] = kHotBloat;
        }
    }

    // update bit map info
    for (uint64_t huge_pn = start_pn_; huge_pn < end_pn_; huge_pn++) {
        int pn_idx = huge_pn - start_pn_;
        if (huge_bloat_degree_[pn_idx] > 1) {
            RecordBitMap(pn_idx, huge_pn);
        }
    }
}

std::vector<uint64_t> AccessFreqTracker::SearchRemapGroup(int pn_idx, std::vector<std::pair<int, int>>& candidate_pn)
{
    std::vector<uint64_t> remap_group;
    double fit_ratio = 1 / (double)(1 << candidate_pn[pn_idx].second);

    for (; (uint64_t)pn_idx < candidate_pn.size(); pn_idx += 1) {
        if(candidate_pn[pn_idx].second <= 1)
            continue;

        if (fit_ratio + (1 / (double)(1 << candidate_pn[pn_idx].second)) <= 1) {
            fit_ratio += (1 / (double)(1 << candidate_pn[pn_idx].second));
            remap_group.push_back(pn_idx);
            candidate_pn[pn_idx].second = 0;   
        }
    }

    return remap_group;
}

int AccessFreqTracker::_SearchRemapIndex(std::vector<int>& bitmap_accu, std::vector<int> bitmap_cur)
{
    int sub_page_per_huge = (kHugePageSize / cache_block_size_);
    int best_offset = 0;
    int min_conflict = 999999;
    assert((uint64_t)sub_page_per_huge == bitmap_accu.size());
    assert((uint64_t)sub_page_per_huge == bitmap_cur.size());

    for (int offset = 0; (uint64_t)offset < kRemapOffsetRange; offset += 1) {
        int cur_conflict = 0;
        for (int idx = 0; (uint64_t)idx < bitmap_accu.size(); idx += 1) {
            int bit_accu = bitmap_accu[idx];
            int bit_offset = bitmap_cur[
                (idx + offset * (sub_page_per_huge / kRemapOffsetRange) ) % sub_page_per_huge];

            assert(bit_accu <= 1);
            assert(bit_offset <= 1);
            if (bit_accu == 1 && bit_offset == 1) {
                cur_conflict += 1;
            }
        }

        if (cur_conflict < min_conflict) {
            best_offset = offset;
            min_conflict = cur_conflict;
        }
    }

    for (int idx = 0; (uint64_t)idx < bitmap_accu.size(); idx += 1) {
        int bit_offset = bitmap_cur[
                (idx + best_offset * (sub_page_per_huge / kRemapOffsetRange) ) % sub_page_per_huge];
        
        if (bit_offset == 1) {
            bitmap_accu[idx] = 1;
        }
    }

    return best_offset;
}

void AccessFreqTracker::SearchRemapIndex(void)
{
    for (const auto& group: huge_remap_group_) {
        huge_remap_info_[group[0]] = 0;

        if (group.size() == 1) {
            continue;
        }

        int cur_idx = 1;
        std::vector<int> bitmap_accu = huge_bitmaps_[group[0]];
        while((uint64_t)cur_idx < group.size()) {
            assert((uint64_t)group[cur_idx] < huge_bitmaps_.size());
            assert((uint64_t)group[cur_idx] < huge_remap_info_.size());

            std::vector<int> bitmap_cur = huge_bitmaps_[group[cur_idx]];
            int remap_info = _SearchRemapIndex(bitmap_accu, bitmap_cur);
            huge_remap_info_[group[cur_idx]] = remap_info;

            cur_idx += 1;
        }
    }
}

void AccessFreqTracker::ComputeRemapInfo(void)
{
    // search candidate
    uint64_t candidate_num = kCacheAssoc * dram_ratio_;

    for (uint64_t start_idx = 0; start_idx < (kHugePageSize / cache_block_size_); start_idx += candidate_num) {
        std::vector<std::pair<int, int>> candidate_pn; // <pn_idx, bloat_degree>
        
        for (uint64_t idx = 0; idx < kNrHugePagePerSeg; idx++) {
            assert(idx < huge_bloat_degree_.size());
            uint64_t degree = huge_bloat_degree_[idx];
            if (degree > 1) {
                candidate_pn.push_back(std::pair<int, int>(idx, degree));
            }
        }

        // costruct remap group
        for (int idx = 0; (uint64_t)idx < candidate_pn.size(); idx += 1) {
            std::vector<uint64_t> group =  SearchRemapGroup(idx, candidate_pn);
            if (group.size() > 0) {
                huge_remap_group_.push_back(group);
            }
        }
    }

    // search candidate index
    SearchRemapIndex();
}

void AccessFreqTracker::GetNewHugePageMetadata(void)
{
    UpdateHotColdMetadata();
    ComputeRemapInfo();
}