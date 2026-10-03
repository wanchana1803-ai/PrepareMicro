#ifndef __FONTS_H__
#define __FONTS_H__

#include <stdint.h>

// โครงสร้างข้อมูลสำหรับ Font
typedef struct {
    const uint8_t FontWidth;    // ความกว้างฟอนต์ (พิกเซล)
    uint8_t FontHeight;         // ความสูงฟอนต์ (พิกเซล)
    const uint16_t *data;       // พอยน์เตอร์ตารางข้อมูลอักขระ
} FontDef;

// ฟอนต์ที่มีให้เลือกใช้
extern FontDef Font_7x10;
extern FontDef Font_11x18;
extern FontDef Font_16x26;

#endif // __FONTS_H__
