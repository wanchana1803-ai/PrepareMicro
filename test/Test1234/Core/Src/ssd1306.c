#include "ssd1306.h"

// บัฟเฟอร์หน่วยความจำภาพในแรมของไมโครคอนโทรลเลอร์ (1024 ไบต์)
static uint8_t SSD1306_Buffer[SSD1306_WIDTH * SSD1306_HEIGHT / 8];
static SSD1306_t SSD1306;

// ส่งคำสั่ง Command ผ่าน I2C (Control byte = 0x00)
static void ssd1306_WriteCommand(uint8_t byte) {
    HAL_I2C_Mem_Write(&SSD1306_I2C_PORT, SSD1306_I2C_ADDR, 0x00, 1, &byte, 1, 10);
}

// ส่งข้อมูลพิกเซล Data ผ่าน I2C (Control byte = 0x40)
static void ssd1306_WriteData(uint8_t* buffer, size_t buff_size) {
    HAL_I2C_Mem_Write(&SSD1306_I2C_PORT, SSD1306_I2C_ADDR, 0x40, 1, buffer, buff_size, 100);
}

// เริ่มต้นเปิดการทำงานของหน้าจอ OLED
uint8_t ssd1306_Init(void) {
    // รีเซ็ตสัญญาณ I2C เผื่อบัสค้างจากการแฟลชโค้ด
    __HAL_RCC_I2C1_FORCE_RESET();
    HAL_Delay(10);
    __HAL_RCC_I2C1_RELEASE_RESET();
    HAL_I2C_Init(&SSD1306_I2C_PORT);

    // รอให้โมดูลพร้อมหลังจ่ายไฟ
    HAL_Delay(100);

    // ลำดับคำสั่ง Initialize หน้าจอ
    ssd1306_WriteCommand(0xAE); // Display Off

    ssd1306_WriteCommand(0xD5); // Set Display Clock Divide Ratio / Osc Frequency
    ssd1306_WriteCommand(0x80);

    ssd1306_WriteCommand(0xA8); // Set Multiplex Ratio
    ssd1306_WriteCommand(SSD1306_HEIGHT - 1);

    ssd1306_WriteCommand(0xD3); // Set Display Offset
    ssd1306_WriteCommand(0x00);

    ssd1306_WriteCommand(0x40); // Set Display Start Line = 0

    // เปิดวงจรสร้างไฟเลี้ยงจอ (ส่งทั้งคู่เพื่อรองรับทั้งชิป SSD1306 และ SH1106 ติดแน่นอน 100%)
    ssd1306_WriteCommand(0x8D); // SSD1306 Charge Pump Setting
    ssd1306_WriteCommand(0x14); // Enable Charge Pump (7.5V)
    ssd1306_WriteCommand(0xAD); // SH1106 DC-DC Control Mode
    ssd1306_WriteCommand(0x8B); // DC-DC ON

    ssd1306_WriteCommand(0x20); // Set Memory Addressing Mode
    ssd1306_WriteCommand(0x02); // Page Addressing Mode (เข้ากันได้กับทั้งคู่)

    ssd1306_WriteCommand(0xA1); // Set Segment Re-map (A0=ซ้ายไปขวา, A1=กลับด้านซ้ายขวา)
    ssd1306_WriteCommand(0xC8); // Set COM Output Scan Direction (กลับหัวบนล่าง)

    ssd1306_WriteCommand(0xDA); // Set COM Pins Hardware Configuration
    ssd1306_WriteCommand(0x12);

    ssd1306_WriteCommand(0x81); // Set Contrast Control
    ssd1306_WriteCommand(0xCF);

    ssd1306_WriteCommand(0xD9); // Set Pre-charge Period
    ssd1306_WriteCommand(0xF1);

    ssd1306_WriteCommand(0xDB); // Set VCOMH Deselect Level
    ssd1306_WriteCommand(0x40);

    ssd1306_WriteCommand(0xA4); // Entire Display ON Resume to RAM
    ssd1306_WriteCommand(0xA6); // Set Normal Display (ไม่ Invert)

    ssd1306_WriteCommand(0xAF); // Display ON

    // ล้างจอให้ว่างเปล่า
    ssd1306_Fill(Black);
    ssd1306_UpdateScreen();

    // กำหนดค่าเริ่มต้นเคอร์เซอร์
    SSD1306.CurrentX = 0;
    SSD1306.CurrentY = 0;
    SSD1306.Initialized = 1;

    return 1;
}

// เคลียร์จอ (Black) หรือเติมขาวทั้งจอ (White)
void ssd1306_Fill(SSD1306_COLOR color) {
    memset(SSD1306_Buffer, (color == Black) ? 0x00 : 0xFF, sizeof(SSD1306_Buffer));
}

// ส่งข้อมูลแรมในไมโครคอนโทรลเลอร์ไปยังหน้าจอจริง
void ssd1306_UpdateScreen(void) {
    for (uint8_t m = 0; m < 8; m++) {
        ssd1306_WriteCommand(0xB0 + m); // เลือก Page (0-7)

#if SSD1306_USE_SH1106
        // สำหรับ SH1106 จอ 1.3 นิ้ว: แรม 132 คอลัมน์ จอแสดง 128 คอลัมน์ (ชดเชย Offset 2 พิกเซล)
        ssd1306_WriteCommand(0x02); // Column address ต่ำ = 2
        ssd1306_WriteCommand(0x10); // Column address สูง = 0
#else
        // สำหรับ SSD1306 จอ 0.96 นิ้ว: เริ่มที่คอลัมน์ 0
        ssd1306_WriteCommand(0x00); // Column address ต่ำ = 0
        ssd1306_WriteCommand(0x10); // Column address สูง = 0
#endif
        ssd1306_WriteData(&SSD1306_Buffer[SSD1306_WIDTH * m], SSD1306_WIDTH);
    }
}

// วาดจุด 1 พิกเซล
void ssd1306_DrawPixel(uint8_t x, uint8_t y, SSD1306_COLOR color) {
    if (x >= SSD1306_WIDTH || y >= SSD1306_HEIGHT) {
        return;
    }

    if (color == White) {
        SSD1306_Buffer[x + (y / 8) * SSD1306_WIDTH] |= (1 << (y % 8));
    } else {
        SSD1306_Buffer[x + (y / 8) * SSD1306_WIDTH] &= ~(1 << (y % 8));
    }
}

// กำหนดตำแหน่ง Cursor สำหรับเขียนตัวหนังสือ
void ssd1306_SetCursor(uint8_t x, uint8_t y) {
    SSD1306.CurrentX = x;
    SSD1306.CurrentY = y;
}

// เขียนอักขระ 1 ตัว
char ssd1306_WriteChar(char ch, FontDef Font, SSD1306_COLOR color) {
    if (ch < 32 || ch > 126) {
        ch = ' '; // ข้ามตัวที่ไม่ใช่อักษรพิมพ์ได้
    }

    if (SSD1306_WIDTH < (SSD1306.CurrentX + Font.FontWidth) ||
        SSD1306_HEIGHT < (SSD1306.CurrentY + Font.FontHeight)) {
        return 0; // ข้อความล้นจอ
    }

    for (uint32_t i = 0; i < Font.FontHeight; i++) {
        uint16_t b = Font.data[(ch - 32) * Font.FontHeight + i];
        for (uint32_t j = 0; j < Font.FontWidth; j++) {
            uint8_t pixel_on = 0;
            if (Font.FontWidth == 7) {
                pixel_on = (b >> (7 - j)) & 1;
            } else if (Font.FontWidth == 11) {
                pixel_on = (b >> (10 - j)) & 1;
            } else {
                pixel_on = ((b << j) & 0x8000) ? 1 : 0;
            }

            if (pixel_on) {
                ssd1306_DrawPixel(SSD1306.CurrentX + j, (SSD1306.CurrentY + i), (SSD1306_COLOR)color);
            } else {
                ssd1306_DrawPixel(SSD1306.CurrentX + j, (SSD1306.CurrentY + i), (SSD1306_COLOR)!color);
            }
        }
    }

    SSD1306.CurrentX += Font.FontWidth;
    return ch;
}

// เขียนข้อความ String
char ssd1306_WriteString(char* str, FontDef Font, SSD1306_COLOR color) {
    while (*str) {
        if (ssd1306_WriteChar(*str, Font, color) != *str) {
            return *str;
        }
        str++;
    }
    return *str;
}

// วาดเส้นตรง (Bresenham Algorithm)
void ssd1306_DrawLine(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1, SSD1306_COLOR color) {
    int16_t dx = abs((int16_t)x1 - (int16_t)x0);
    int16_t dy = -abs((int16_t)y1 - (int16_t)y0);
    int8_t sx = (x0 < x1) ? 1 : -1;
    int8_t sy = (y0 < y1) ? 1 : -1;
    int16_t err = dx + dy, e2;

    while (1) {
        ssd1306_DrawPixel(x0, y0, color);
        if (x0 == x1 && y0 == y1) break;
        e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

// วาดสี่เหลี่ยม
void ssd1306_DrawRectangle(uint8_t x, uint8_t y, uint8_t w, uint8_t h, SSD1306_COLOR color) {
    ssd1306_DrawLine(x, y, x + w, y, color);
    ssd1306_DrawLine(x, y + h, x + w, y + h, color);
    ssd1306_DrawLine(x, y, x, y + h, color);
    ssd1306_DrawLine(x + w, y, x + w, y + h, color);
}
