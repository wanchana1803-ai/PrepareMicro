#ifndef __SSD1306_H__
#define __SSD1306_H__

#include "stm32f4xx_hal.h"
#include "fonts.h"
#include <stdlib.h>
#include <string.h>

// ============================================================================
// การตั้งค่าฮาร์ดแวร์ (ปรับแต่งได้ตามความต้องการ)
// ============================================================================

// 1 = จอ 1.3 นิ้ว (ชิป SH1106 มี offset 2 pixel)
// 0 = จอ 0.96 นิ้ว (ชิป SSD1306)
#define SSD1306_USE_SH1106      1

// พอร์ต I2C ที่ตั้งใน STM32CubeMX (ปกติคือ hi2c1)
extern I2C_HandleTypeDef hi2c1;
#define SSD1306_I2C_PORT        hi2c1

// Address ของจอ I2C (0x3C << 1 หรือ 0x78)
#define SSD1306_I2C_ADDR        (0x3C << 1)

// ขนาดจอพิกเซล
#define SSD1306_WIDTH           128
#define SSD1306_HEIGHT          64

// ============================================================================
// ชนิดข้อมูลและสี
// ============================================================================
typedef enum {
    Black = 0x00, // ปิดพิกเซล (สีดำ)
    White = 0x01  // เปิดพิกเซล (สีขาว/ฟ้า/เหลือง ตามสีหน้าจอ)
} SSD1306_COLOR;

typedef struct {
    uint16_t CurrentX;
    uint16_t CurrentY;
    uint8_t Inverted;
    uint8_t Initialized;
} SSD1306_t;

// ============================================================================
// ฟังก์ชันสำหรับเรียกใช้งานใน main.c
// ============================================================================

// ฟังก์ชันหลัก
uint8_t ssd1306_Init(void);
void ssd1306_Fill(SSD1306_COLOR color);
void ssd1306_UpdateScreen(void);
void ssd1306_SetCursor(uint8_t x, uint8_t y);

// ฟังก์ชันแสดงตัวอักษรและข้อความ
char ssd1306_WriteChar(char ch, FontDef Font, SSD1306_COLOR color);
char ssd1306_WriteString(char* str, FontDef Font, SSD1306_COLOR color);

// ฟังก์ชันวาดกราฟิกพื้นฐาน
void ssd1306_DrawPixel(uint8_t x, uint8_t y, SSD1306_COLOR color);
void ssd1306_DrawLine(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1, SSD1306_COLOR color);
void ssd1306_DrawRectangle(uint8_t x, uint8_t y, uint8_t w, uint8_t h, SSD1306_COLOR color);

#endif // __SSD1306_H__
