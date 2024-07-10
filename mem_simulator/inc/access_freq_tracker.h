#ifndef MEM_SIMULATOR_ACCESS_FREQ_TRACKER_H_
#define MEM_SIMULATOR_ACCESS_FREQ_TRACKER_H_

#include "cm_sketch.h"
#include "mem_controller.h"
#include "param.h"

#include <cstdint>

class AccessFreqTracker {
    public:
        uint64_t cache_block_size_;
        uint64_t dram_ratio_;
        uint64_t cxl_size_;
        uint64_t start_pn_ = 0;
        uint64_t end_pn_ = 0;
        uint64_t hot_thres_ = 0; // hot thres for access hist

        CMSketch cm_sketch_;
        std::vector<uint64_t> access_hist_;
        std::vector<HugePageStat> huge_metadata_;   // huge page metadata in cur period
        std::vector<int> huge_bloat_degree_;
        std::vector<std::vector<int>> huge_bitmaps_;    // hot sub page bitmap
        std::vector<std::vector<uint64_t>> huge_remap_group_;  // record the pn_idx of remap group
        std::vector<int> huge_remap_info_;

        void NewPeriod(uint64_t start_pn);
        void UpdateAccessFreq(uint64_t addr);
        void GetNewHugePageMetadata(void);  // Get (1)Hot Uniform,(2)Hot Bloat,(3)Cold info; Get remap info

        AccessFreqTracker(uint64_t cache_block_size, uint64_t dram_ratio, uint64_t cxl_size)
            :cache_block_size_(cache_block_size), dram_ratio_(dram_ratio), cxl_size_(cxl_size),
            cm_sketch_(kNrHugePagePerSeg * (kHugePageSize / kCacheBlockSize), kSketchCountBit),
            access_hist_(1 << cm_sketch_.count_bit_, 0),
            huge_metadata_(kNrHugePagePerSeg),
            huge_bloat_degree_(kNrHugePagePerSeg),
            huge_bitmaps_(kNrHugePagePerSeg, std::vector<int>((kHugePageSize / kCacheBlockSize), 0)),
            huge_remap_info_(kNrHugePagePerSeg) {};
        ~AccessFreqTracker(void){};

        private:
            void ClearHugePageState(void);
            void RecordBitMap(int, uint64_t);
            void UpdateHotColdMetadata(void);
            std::vector<uint64_t> SearchRemapGroup(int pn_idx, std::vector<std::pair<int, int>>& candidate_pn);
            int _SearchRemapIndex(std::vector<int>& bitmap_accu, std::vector<int> bitmap_cur);
            void SearchRemapIndex(void);
            void ComputeRemapInfo(void);
};

#endif