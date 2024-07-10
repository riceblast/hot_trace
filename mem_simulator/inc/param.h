#ifndef MEM_SIM_INC_PARAM_H_
#define MEM_SIM_INC_PARAM_H_

#include <string>

const uint64_t kCacheBlockSize = 256;   // cache block size: 256B
const uint64_t kHugePageSize = 2 * 1024 * 1024; // 2MB
const uint64_t kLineNumPerSecond = 20000000;
const uint64_t kPeriodMilliSecond = 20; // sketch monitoring period(ms)
const uint64_t kNrHugePagePerSeg = 8192;    // huge page number per cxl seg
const uint64_t kSketchCountBit = 5;
const uint64_t kNrBloatDegree = 5;    // 2^1->2^5
const uint64_t kCacheAssoc = 8; // set-associative
const uint64_t kRemapOffsetRange = 16;
const std::string kRawDataPathPrefix = "/home/yxr/downloads/test_trace/raw_data/roi/";

#endif