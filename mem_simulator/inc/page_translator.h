#ifndef MEM_SIM_PAGE_TRANSLATOR_H_
#define MEM_SIM_PAGE_TRANSLATOR_H_

#include "param.h"

#include <cstdint>
#include <vector>

class PageTranslator {
    public:
        uint64_t page_size_;    //Byte
        uint64_t cxl_range_; //Byte

        uint64_t Translate(uint64_t byte_addr);
        PageTranslator(){};
        PageTranslator(uint64_t page_size, uint64_t cxl_range):
            page_size_(page_size), cxl_range_(cxl_range), nr_page(0), translation_table((cxl_range / page_size), -1){};

    private:
        uint64_t nr_page;
        std::vector<uint64_t> translation_table;    // 0 is invalid

};

#endif