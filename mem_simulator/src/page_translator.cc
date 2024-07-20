#include <cassert>
#include <cstdint>

#include "page_translator.h"

uint64_t PageTranslator::Translate(uint64_t byte_addr)
{
    uint64_t vpn = byte_addr / page_size_;

    assert(translation_table.size() > 0);
    assert(vpn < cxl_range_);
    if (translation_table[vpn] == (uint64_t)-1) {
        translation_table[vpn] = nr_page++;
    }
    
    return translation_table[vpn];
}