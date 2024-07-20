#include "access_freq_tracker.h"
#include "param.h"

#include <algorithm>
#include <cassert>
#include <fstream>
#include <functional>
#include <iostream>
#include <numeric>
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

    printf("\nNew Period: 0x%lx(%luGB) -> 0x%lx(%luGB)\n", 
        start_pn_ * kHugePageSize, start_pn_ * kHugePageSize / kGB,
        end_pn_ * kHugePageSize, end_pn_ * kHugePageSize / kGB);

    cm_sketch_.Clear();
    ClearHugePageState();
}

void AccessFreqTracker::UpdateAccessFreq(uint64_t cache_addr)
{
    if (cache_addr >= start_pn_ * (kHugePageSize / cache_block_size_) &&
        cache_addr < end_pn_ * (kHugePageSize / cache_block_size_)) {
        cm_sketch_.Insert(cache_addr);
    }
}

void AccessFreqTracker::RecordBitMap(int pn_idx, uint64_t huge_pn)
{
    for (uint64_t cache_block_addr = huge_pn * (kHugePageSize / cache_block_size_);
        cache_block_addr < (huge_pn + 1) * (kHugePageSize / cache_block_size_); cache_block_addr += 1) {
            uint64_t access_freq = cm_sketch_.Query(cache_block_addr);
            if (access_freq >= hot_thres_ && access_freq > 0) {
                int cache_block_idx = cache_block_addr - huge_pn * (kHugePageSize / cache_block_size_);
                assert((uint64_t)pn_idx < huge_bitmaps_.size());
                assert((uint64_t)cache_block_idx < huge_bitmaps_[pn_idx].size());
                assert((uint64_t)huge_bitmaps_[pn_idx][cache_block_idx] == 0);
                huge_bitmaps_[pn_idx][cache_block_idx] = 1;
            }
        }
}

void AccessFreqTracker::DumpAccessHist(std::vector<uint64_t> hot_sub_pn, std::vector<std::pair<uint64_t, uint64_t>> access_freq)
{
    std::ofstream out;
    std::cout << "Dumping Access Hist" << std::endl;
    out.open("./log/log_access_dist_" + std::to_string(bucket_size_) + "_" + bench_name_ + ".out");
    for (int idx = 1; (uint64_t)idx < access_hist_.size(); idx++) {
        out << idx << ": " << access_hist_[idx] << std::endl;
    }

    uint64_t sum = std::accumulate(access_hist_.begin() + 1, access_hist_.end(), 0);
    out << -1 << ": " << sum << std::endl;
    out << "hot_thres: " << hot_thres_ << std::endl;
    out.close();

    std::cout << "Dumping Page Access Freq" << std::endl;
    out.open("./log/log_page_freq_" + std::to_string(bucket_size_) + "_" + bench_name_ + ".out");
    std::sort(access_freq.begin(), access_freq.end());
    for (int idx = 0; (uint64_t)idx < access_freq.size(); idx++) {
        out << std::hex << "0x" << access_freq[idx].first << std::dec << " " << access_freq[idx].second << std::endl; 
    }
    out.close();

    printf("Dumping Hot Bloat Degree\n");
    out.open("./log/log_bloat_degree_" + std::to_string(bucket_size_) + "_" + bench_name_ + ".out");
    for (int idx = 0; (uint64_t)idx < huge_bloat_degree_.size(); idx++) {
        if (huge_bloat_degree_[idx] == 0 || huge_bloat_degree_[idx] == 1)
            out << std::hex << "0x" << idx + start_pn_ << " " << std::dec << huge_bloat_degree_[idx] << std::endl;
        else 
            out << std::hex << "0x" << idx + start_pn_ << " " << std::dec << (double)100 / (1 << huge_bloat_degree_[idx]) << std::endl;
    }
    out.close();
}

void AccessFreqTracker::UpdateHotColdMetadata(void)
{    
    // get access freq histogram
    printf("Getting access freq hist\n");
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
    std::cout << "hot_thres: " << hot_thres_ << std::endl;

    // distinguish hot/cold
    printf("Distinguish hot/cold cacheline\n");
    uint64_t nr_total_hot_sub_page = 0;
    std::vector<std::pair<uint64_t, uint64_t>> access_freq;
    std::vector<uint64_t> hot_sub_pn;
    for (uint64_t huge_pn = start_pn_; huge_pn < end_pn_; huge_pn++) {
        uint64_t sub_hot_page_num = 0;
        for (uint64_t cache_idx = 0; cache_idx < (kHugePageSize / cache_block_size_); cache_idx += 1) {
            if (cm_sketch_.Query(huge_pn * (kHugePageSize / cache_block_size_) + cache_idx) >= hot_thres_ &&
                cm_sketch_.Query(huge_pn * (kHugePageSize / cache_block_size_) + cache_idx) > 0) {
                sub_hot_page_num += 1;
                hot_sub_pn.push_back(huge_pn * (kHugePageSize / cache_block_size_) + cache_idx);
                access_freq.emplace_back(std::pair<uint64_t, uint64_t>(huge_pn * (kHugePageSize / cache_block_size_) + cache_idx,
                    cm_sketch_.Query(huge_pn * (kHugePageSize / cache_block_size_) + cache_idx)));
            }
        }
        nr_total_hot_sub_page += sub_hot_page_num;

        uint64_t bloat_degree = 1;  // 1 -> uniform hot
        while(bloat_degree <= kNrBloatDegree) {
            if (sub_hot_page_num >= (kHugePageSize / cache_block_size_) / (1 << bloat_degree)) {
                break;
            }
            bloat_degree += 1;
        }

        //record bloat_degree, 0: cold page, 1~kNrBloatDegree: >= 1/2^degree
        if (bloat_degree > kNrBloatDegree) {
            huge_bloat_degree_[huge_pn - start_pn_] = 0;
        } else {
            huge_bloat_degree_[huge_pn - start_pn_] = bloat_degree;
        }
    }
    assert(nr_total_hot_sub_page >= capcity_threshold);

#ifdef SKETCH_DEBUG_MODE
    printf("Start Dump\n");
    DumpAccessHist(hot_sub_pn, access_freq);
#endif

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

            uint64_t test_nr_hot_sub_page = 0;
            for (int idx = 0; (uint64_t)idx < (kHugePageSize / cache_block_size_); idx++) {
                assert(huge_bitmaps_[pn_idx][idx] == 1 || huge_bitmaps_[pn_idx][idx] == 0);
                if(huge_bitmaps_[pn_idx][idx])
                    test_nr_hot_sub_page += 1;
            }
            assert(test_nr_hot_sub_page >= ((kHugePageSize / cache_block_size_) / (1 << huge_bloat_degree_[pn_idx])) &&
                test_nr_hot_sub_page < (kHugePageSize / cache_block_size_) / (1 << (huge_bloat_degree_[pn_idx] - 1)));
        }
    }
}

std::vector<uint64_t> AccessFreqTracker::SearchRemapGroup(int pn_idx, std::vector<std::pair<int, int>>& candidate_pn)
{
    std::vector<uint64_t> remap_group;

    assert(candidate_pn[pn_idx].second != 1);
    if (candidate_pn[pn_idx].second == 0)
        return remap_group;

    double fit_ratio = 1 / (double)(1 << candidate_pn[pn_idx].second);

    for (; (uint64_t)pn_idx < candidate_pn.size(); pn_idx += 1) {
        assert(candidate_pn[pn_idx].second != 1);
        if(candidate_pn[pn_idx].second == 0)
            continue;

        if (fit_ratio + (1 / (double)(1 << candidate_pn[pn_idx].second)) <= 1) {
            fit_ratio += (1 / (double)(1 << candidate_pn[pn_idx].second));
            remap_group.push_back(candidate_pn[pn_idx].first);  // FIXME: BUGGY?
            candidate_pn[pn_idx].second = 0;   
        }
    }

    assert(remap_group.size() <= (1 << kNrBloatDegree));
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
            int bit_accu = bitmap_accu[(idx + offset * (sub_page_per_huge / kRemapOffsetRange) ) % sub_page_per_huge];
            int bit_offset = bitmap_cur[idx];

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
        uint64_t offset_idx = (idx + best_offset * (sub_page_per_huge / kRemapOffsetRange)) % sub_page_per_huge;
        int bit_offset = bitmap_cur[idx];
        
        if (bit_offset == 1) {
            bitmap_accu[offset_idx] = 1;
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
            assert(huge_remap_info_[group[cur_idx]] == -1);
            huge_remap_info_[group[cur_idx]] = remap_info;

            cur_idx += 1;
        }
    }
}

void AccessFreqTracker::DumpRemapInfo(void)
{  
    printf("Dump Remap Group\n");
    std::ofstream out;
    std::cout << "Dumping Remap Group" << std::endl;
    out.open("./log/log_remap_group_" + std::to_string(bucket_size_) + "_" + bench_name_ + ".out");
    for (const auto& group: huge_remap_group_) {
        double coverage = 0;
        for (const auto& pn_idx: group) {
            assert(huge_bloat_degree_[pn_idx] > 1);
            out << std::hex << "0x" << pn_idx + start_pn_ << std::dec << 
                "(" << (double)100 / (1 << huge_bloat_degree_[pn_idx]) << ")" << "  ";
            coverage += (double)1 / (1 << huge_bloat_degree_[pn_idx]);
        }
        out << std::endl;
        assert(coverage <= 1);
    }
    out.close();

    printf("Dump Index info\n");
    out.open("./log/log_learned_index_" + std::to_string(bucket_size_) + "_" + bench_name_ + ".out");
    for (const auto& group: huge_remap_group_) {
        out << "0x" << std::hex << group[0] + start_pn_ << ": " << std::dec << std::endl;
        uint64_t nr_direct_uncover = 0;
        uint64_t nr_learned_uncover = 0;
        uint64_t sub_page_per_huge = (kHugePageSize / cache_block_size_);
        uint64_t index_seg_size = sub_page_per_huge / kRemapOffsetRange;
        std::vector<int> direct_bitmap(huge_bitmaps_[group[0]]);
        std::vector<int> learned_bitmap(huge_bitmaps_[group[0]]);

        for (const auto& pn_idx: group) {
            std::vector<int> cur_bitmap(huge_bitmaps_[pn_idx]);
            assert(cur_bitmap.size() == sub_page_per_huge);
            for (int idx = 0; (uint64_t)idx < cur_bitmap.size(); idx += 1) {
                int direct_cur_bit = cur_bitmap[idx];
                int learned_cur_bit = cur_bitmap[idx];

                if (direct_cur_bit == 1) {
                    direct_bitmap[idx] = 1;
                }
                if (learned_cur_bit == 1) {
                    learned_bitmap[
                        (idx + huge_remap_info_[pn_idx] * index_seg_size) % cur_bitmap.size()] = 1;
                }
            }

            out << huge_remap_info_[pn_idx] << " ";
        }

        for (const auto& bit: direct_bitmap) {
            if (bit == 0)
                nr_direct_uncover += 1;
        }
        for (const auto& bit: learned_bitmap) {
            if (bit == 0)
                nr_learned_uncover += 1;
        }
        //assert(nr_learned_uncover <= nr_direct_uncover);
        out << ": " << nr_direct_uncover << "->" << nr_learned_uncover << std::endl;
    }
    out.close();
}

void AccessFreqTracker::ComputeRemapInfo(void)
{
    // search candidate
    uint64_t candidate_num = kCacheAssoc * dram_ratio_;

    // for (uint64_t start_idx = 0; start_idx < (kHugePageSize / cache_block_size_); start_idx += candidate_num) {
    //     std::vector<std::pair<int, int>> candidate_pn; // <pn_idx, bloat_degree>
        
    //     for (uint64_t idx = 0; idx < kNrHugePagePerSeg; idx++) {
    //         assert(idx < huge_bloat_degree_.size());
    //         uint64_t degree = huge_bloat_degree_[idx];
    //         if (degree > 1) {
    //             candidate_pn.push_back(std::pair<int, int>(idx, degree));
    //         }
    //     }

    // FIXME 将区间划分改为direct-map style
    uint64_t nr_bloat_hp = 0;
    std::vector<int> bloat_hp_flag(kNrHugePagePerSeg, 0);
    //for (uint64_t candidate_start_idx = 0; candidate_start_idx < kNrHugePagePerSeg; candidate_start_idx += candidate_num) {
        // for (uint64_t idx = 0; idx < candidate_num && candidate_start_idx + idx < kNrHugePagePerSeg; idx += 1) {
        //     uint64_t candidate_pn_idx = candidate_start_idx + idx;
        //     assert(candidate_pn_idx < huge_bloat_degree_.size());
        //     uint64_t degree = huge_bloat_degree_[candidate_pn_idx];

        //     if (degree > 1) {
        //         candidate_pn.push_back(std::pair<int, int>(candidate_pn_idx, degree));
        //         nr_bloat_hp += 1;
        //     }
        // }
    uint64_t nr_dram_pn = (cxl_size_ / dram_ratio_) * kMB / kHugePageByteSize;
    assert(kNrHugePagePerSeg >= nr_dram_pn);
    //assert(kNrHugePagePerSeg % nr_dram_pn == 0);    // FIXME only used for test
    for (uint64_t candidate_start_idx = 0; candidate_start_idx < nr_dram_pn; candidate_start_idx += 1) {
        std::vector<std::pair<int, int>> candidate_pn; // <pn_idx, bloat_degree>, used to construct remap group

        for (uint64_t idx = 0; candidate_start_idx + idx < kNrHugePagePerSeg; idx += nr_dram_pn) {
            uint64_t candidate_pn_idx = candidate_start_idx + idx;
            assert(candidate_pn_idx < huge_bloat_degree_.size());
            uint64_t degree = huge_bloat_degree_[candidate_pn_idx];

            if (degree > 1) {
                candidate_pn.push_back(std::pair<int, int>(candidate_pn_idx, degree));
                nr_bloat_hp += 1;
            }
        }

        // costruct remap group, used to search index remapping
        for (int idx = 0; (uint64_t)idx < candidate_pn.size(); idx += 1) {
            std::vector<uint64_t> group =  SearchRemapGroup(idx, candidate_pn); 
            if (group.size() > 0) {
                huge_remap_group_.push_back(group);
            }
        }
    }

    for (uint64_t idx = 0; idx < huge_remap_group_.size(); idx += 1) {
        assert(huge_remap_group_.size() > 0);
        for (uint64_t inner_idx = 0; inner_idx < huge_remap_group_[idx].size(); inner_idx += 1) {
            uint64_t pn_idx = huge_remap_group_[idx][inner_idx];
            assert(bloat_hp_flag[pn_idx] == 0);
            bloat_hp_flag[pn_idx] = 1;
        }
    }

    uint64_t nr_test_bloat_hp = 0;
    for (uint64_t idx = 0; idx < bloat_hp_flag.size(); idx += 1) {
        if (bloat_hp_flag[idx] == 1)
            nr_test_bloat_hp += 1;
    }
    assert(nr_test_bloat_hp == nr_bloat_hp);

    // search candidate index
    printf("Search Remap Index\n");
    SearchRemapIndex();
    DumpRemapInfo();
}

void AccessFreqTracker::GetNewHugePageMetadata(void)
{
    UpdateHotColdMetadata();
    ComputeRemapInfo();
    assert(huge_remap_info_.size() == huge_bitmaps_.size());
}