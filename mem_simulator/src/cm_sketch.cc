#include "cm_sketch.h"
#include "hash.h"

#include <cstdint>

uint64_t CMSketch::Query(uint64_t key)
{
    uint64_t v0, v1, v2;
    v0 = buckets_[0][XXHash(key) % width_];
    v1 = buckets_[1][BobHash(key) % width_];
    v2 = buckets_[2][CityHash(key) % width_];

    return std::min(v0, std::min(v1, v2));
}

void CMSketch::Insert(uint64_t key)
{
    uint64_t max_value = (1 << count_bit_) - 1;
    uint64_t v0, v1, v2;

    v0 = buckets_[0][XXHash(key) % width_];
    buckets_[0][XXHash(key) % width_] = std::min(v0 + 1, max_value);

    v1 = buckets_[1][BobHash(key) % width_];
    buckets_[1][BobHash(key) % width_] = std::min(v1 + 1, max_value);

    v2 = buckets_[2][CityHash(key) % width_];
    buckets_[2][CityHash(key) % width_] = std::min(v2 + 1, max_value);
}

void CMSketch::Clear(void)
{
    for (auto& row : buckets_) {
        for (auto& entry: row) {
            entry = 0;
        }
    }
}