#ifndef MEM_SIMULATOR_INC_HASH_H_
#define MEM_SIMULATOR_INC_HASH_H_

#include <cstdint>

uint64_t XXHash(uint64_t key);
uint64_t BobHash(uint64_t key);
uint64_t CityHash(uint64_t key);

#endif