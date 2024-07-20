#ifndef MEM_SIM_INC_PARAM_H_
#define MEM_SIM_INC_PARAM_H_

#include <string>

#define SKETCH_DEBUG_MODE
#define DEBUG_MODE
#define VERBOSE_MODE

const uint64_t kMB = 1024UL * 1024UL;
const uint64_t kGB = 1024UL * 1024UL * 1024UL;
const uint64_t kHugePageSize = 2 * 1024UL * 1024UL; // 2MB
const uint64_t kHugePageByteSize = 2 * 1024UL * 1024UL;
const uint64_t kCxlByteAddrRange = 2 * 1024UL * 1024UL * 1024UL * 1024UL;   //2TB
const uint64_t kLineNumPerSecond = 200000000UL;   // 2e8
//const uint64_t kPeriodMilliSecond = 30; // sketch monitoring period(ms)
//const uint64_t kNrHugePagePerSeg = 8192;    // huge page number per cxl seg
const uint64_t kNrHugePagePerSeg = 32768;    // huge page number per cxl seg
const uint64_t kSketchCountBit = 5;
const uint64_t kNrBloatDegree = 6;    // 2^1->2^5
const uint64_t kCacheAssoc = 8; // set-associative
const uint64_t kRemapOffsetRange = 16;
const std::string kRawDataPathPrefix = "/home/yxr/downloads/test_trace/raw_data/roi/";
const std::string kDumpPathPrefix= "/home/yxr/downloads/test_trace/index/";

#endif
