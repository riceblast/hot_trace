#ifndef MEM_SIMULATOR_CM_SKETCH_H_
#define MEM_SIMULATOR_CM_SKETCH_H_

#include <cassert>
#include <cstdint>
#include <vector>

class CMSketch {
    public:
        int depth_ = 3; // hash func number
        uint64_t width_; // bucket num
        int count_bit_; // bits used to count
        std::vector<std::vector<int>> buckets_;
        std::vector<bool> is_occured_;

        uint64_t Query(uint64_t key);
        void Insert(uint64_t key);
        void Clear(void);
        CMSketch(uint64_t width, int count_bit)
            :width_(width), count_bit_(count_bit), buckets_(depth_, std::vector<int>(width_, 0)){
                uint64_t totalElements = 0;
                for (const auto& row : buckets_) {
                    totalElements += row.size();
                }
                assert(totalElements == (depth_ * width));

                is_occured_.resize(65536UL * 8192UL);
                for (auto it = is_occured_.begin(); it < is_occured_.end(); it++)
                    (*it) = false;
            };
        ~CMSketch(){};

};

#endif