# 📘 STM32F410RB Motor PWM Control & Encoder Telemetry — Source Code Reference

เอกสารรวบรวมโค้ด C สำหรับโปรเจกต์ **STM32CubeIDE** ทั้ง 2 รูปแบบ พร้อมคำอธิบายและตำแหน่งการวาง (User Code Sections) อย่างละเอียด สามารถคัดลอกไปวางใน `Core/Src/main.c` ได้ทันที

---

## 📋 ข้อมูลการตั้งค่า Peripherals (STM32CubeMX)

1. **System Clock**: HSI + PLL = **84 MHz** (APB1 Timer Clock = 84 MHz, APB2 Timer Clock = 84 MHz)
2. **TIM1 (PWM Generation)**:
   - Mode: Clock Source = Internal Clock, Channel 1 = **PWM Generation CH1** (ขา PA8)
   - Prescaler (PSC): `83` (ทำให้ Timer Clock = $\frac{84\text{ MHz}}{83+1} = 1\text{ MHz}$ คือ 1 tick = $1\ \mu\text{s}$)
   - Counter Period (ARR): `999` (ความถี่ $f = \frac{1\text{ MHz}}{999+1} = 1,000\text{ Hz} = 1\text{ kHz}$)
   - Auto-reload preload: **Enable**
3. **TIM5 (Encoder Interface)**:
   - Mode: Combined Channels = **Encoder Mode** (ขา PA0 / PA1)
   - Counter Period (ARR): `4294967295` (32-bit Max)
   - Encoder Mode: `TI1 and TI2` (X4 Mode, 1 รอบ = $4 \times \text{PPR}$ counts)
4. **USART2 (UART Telemetry & Commands)**:
   - Baud Rate: `115200` Bits/s, 8-N-1 (ขา PA2 TX, PA3 RX)

---

## 1️⃣ รูปแบบที่ 1: โค้ดควบคุมเฉพาะ Duty Cycle (PWM)
> **ใช้คู่กับโปรแกรม Python:** `pwmMotor.py`  
> คำสั่งที่รับ: `D<duty>\n` เช่น `D50\n` (Duty 50%)

### 1.1 Includes (`Core/Src/main.c`)
วางในบล็อก `/* USER CODE BEGIN Includes */`:
```c
/* USER CODE BEGIN Includes */
#include "ssd1306.h"
#include "fonts.h"
#include <stdio.h>
#include <string.h>   // สำหรับ strcpy, strlen, strstr
#include <stdlib.h>   // สำหรับ atoi, abs
#include <ctype.h>    // สำหรับ isdigit
/* USER CODE END Includes */
```

### 1.2 Private Variables (`Core/Src/main.c`)
วางในบล็อก `/* USER CODE BEGIN PV */`:
```c
/* USER CODE BEGIN PV */
// --- พารามิเตอร์ Encoder ---
#define ENCODER_PPR       100     // ระบุ PPR ของ Encoder (เช่น 100, 360, 600)
#define SAMPLING_TIME_MS  100     // อัปเดต RPM และทิศทางทุก 100 ms

uint32_t current_count = 0;
uint32_t prev_count = 0;
int32_t diff_count = 0;           // ค่าบวก = ตามเข็ม (CW), ค่าลบ = ทวนเข็ม (CCW)
float rpm = 0.0f;
char dir_str[6] = "STOP";         // "CW", "CCW", หรือ "STOP"

// --- พารามิเตอร์ PWM ---
uint16_t target_duty = 0;         // ความเร็ว 0 - 100 %
uint32_t pwm_val = 0;             // Compare Register (CCR1)
uint32_t freq_hz = 1000;          // ความถี่ PWM (1,000 Hz)
float period_ms = 1.00f;          // คาบเวลา PWM (1.00 ms)

// --- ตัวแปรสื่อสาร UART และจอ OLED ---
uint8_t rx_byte;
char rx_buf[32];
uint8_t rx_idx = 0;
uint32_t last_calc_time = 0;
char tx_buf[80];
char oled_buf[32];                // บัฟเฟอร์ข้อความสำหรับจอ OLED
/* USER CODE END PV */
```

### 1.3 เริ่มต้น Peripherals ใน `main()`
วางในบล็อก `/* USER CODE BEGIN 2 */`:
```c
  /* USER CODE BEGIN 2 */
  // 1. เปิด Preload ให้ Timer ป้องกันสัญญาณคลื่นสะดุด
  __HAL_TIM_ENABLE_OCxPRELOAD(&htim1, TIM_CHANNEL_1);
  htim1.Instance->CR1 |= TIM_CR1_ARPE;

  // 2. สั่งเริ่มสร้างคลื่น PWM มอเตอร์ (ขา PA8)
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);

  // 3. สั่งเริ่มตัวนับ Encoder (htim5)
  HAL_TIM_Encoder_Start(&htim5, TIM_CHANNEL_ALL);

  // 4. เริ่มต้นหน้าจอ OLED I2C (SSD1306 / SH1106)
  ssd1306_Init();
  ssd1306_Fill(Black);
  ssd1306_SetCursor(10, 20);
  ssd1306_WriteString("OLED READY", Font_7x10, White);
  ssd1306_UpdateScreen();
  /* USER CODE END 2 */
```

### 1.4 โค้ดใน Infinite Loop `while(1)`
วางในบล็อก `/* USER CODE BEGIN 3 */`:
```c
  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
    // -------------------------------------------------------------------------
    // 1. รับคำสั่งปรับความเร็ว (Duty 0 - 100%) จาก Python
    // -------------------------------------------------------------------------
    if (__HAL_UART_GET_FLAG(&huart2, UART_FLAG_ORE))
    {
        __HAL_UART_CLEAR_OREFLAG(&huart2);
    }

    while (__HAL_UART_GET_FLAG(&huart2, UART_FLAG_RXNE))
    {
        rx_byte = (uint8_t)(huart2.Instance->DR & 0x00FF);

        if (rx_byte == '\n') // ตัวปิดท้ายข้อความ
        {
            rx_buf[rx_idx] = '\0';

            // รองรับคำสั่ง "D75" หรือ "75"
            if (rx_buf[0] == 'D')
            {
                target_duty = atoi(&rx_buf[1]);
            }
            else if (isdigit((unsigned char)rx_buf[0]))
            {
                target_duty = atoi(rx_buf);
            }

            if (target_duty > 100) target_duty = 100;

            // คำนวณค่า CCR: ที่ ARR=999 สเกล 0-100% คือ 0-1000
            pwm_val = ((uint32_t)target_duty * 1000) / 100;
            __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);

            rx_idx = 0; // ล้างบัฟเฟอร์
        }
        else if (rx_byte != '\r' && rx_idx < sizeof(rx_buf) - 1)
        {
            rx_buf[rx_idx++] = rx_byte;
        }
    }

    // -------------------------------------------------------------------------
    // 2. คำนวณ RPM + ทิศทางการหมุน และส่ง Telemetry ขึ้น Python ทุก 100 ms
    // -------------------------------------------------------------------------
    if (HAL_GetTick() - last_calc_time >= SAMPLING_TIME_MS)
    {
        last_calc_time = HAL_GetTick();

        // ก) อ่านค่าตัวนับจาก Encoder
        current_count = __HAL_TIM_GET_COUNTER(&htim5);

        // ข) หา Delta Count (พร้อมเครื่องหมาย)
        diff_count = (int32_t)(current_count - prev_count);
        prev_count = current_count;

        // ค) ตรวจวัดทิศทางจากการหมุนจริง
        if (diff_count > 0)
        {
            strcpy(dir_str, "CW");   // ตามเข็ม
        }
        else if (diff_count < 0)
        {
            strcpy(dir_str, "CCW");  // ทวนเข็ม
        }
        else
        {
            strcpy(dir_str, "STOP"); // มอเตอร์หยุดหมุน
        }

        // ง) คำนวณ RPM: (|diff_count| * 60) / (CPR * delta_t)
        // CPR = 4 * ENCODER_PPR (โหมด X4 TI1+TI2)
        rpm = ((float)abs(diff_count) * 60.0f) / ((4.0f * ENCODER_PPR) * (SAMPLING_TIME_MS / 1000.0f));

        // จ) คำนวณ Frequency, Period, และ Duty Cycle แบบ Dynamic จาก Register ฮาร์ดแวร์จริง (ไม่ใช่การ Fix ค่า):
        uint32_t current_arr = __HAL_TIM_GET_AUTORELOAD(&htim1);
        uint32_t current_ccr = __HAL_TIM_GET_COMPARE(&htim1, TIM_CHANNEL_1);

        // 1. ความถี่จริง (Hz) = Timer Clock / (ARR + 1)
        freq_hz = 1000000UL / (current_arr + 1);

        // 2. คาบเวลาจริง (ms) = (ARR + 1) / 1000.0
        period_ms = ((float)(current_arr + 1)) / 1000.0f;

        // 3. Duty Cycle จริง (%) = (CCR1 * 100) / (ARR + 1)
        float actual_duty_pct = ((float)current_ccr * 100.0f) / (float)(current_arr + 1);

        // ฉ) ส่ง Telemetry รูปแบบมาตรฐาน: "F:1000|D:50.0|T:1.00|RPM:280.5|DIR:CW\r\n"
        sprintf(tx_buf, "F:%lu|D:%.1f|T:%.2f|RPM:%.1f|DIR:%s\r\n",
                freq_hz, actual_duty_pct, period_ms, rpm, dir_str);
        HAL_UART_Transmit(&huart2, (uint8_t*)tx_buf, strlen(tx_buf), 50);

        // ช) แสดงผลสดบนจอ OLED (SSD1306 / SH1106)
        ssd1306_Fill(Black);

        // แถว 1: ความถี่ และ Duty Cycle
        sprintf(oled_buf, "F:%4luHz D:%3.0f%%", freq_hz, actual_duty_pct);
        ssd1306_SetCursor(2, 2);
        ssd1306_WriteString(oled_buf, Font_7x10, White);

        // แถว 2: คาบเวลา และ ทิศทางการหมุนจริง
        sprintf(oled_buf, "T:%4.2fms DIR:%-4s", period_ms, dir_str);
        ssd1306_SetCursor(2, 14);
        ssd1306_WriteString(oled_buf, Font_7x10, White);

        // แถว 3: ความเร็วรอบ Encoder RPM
        sprintf(oled_buf, "RPM: %6.1f", rpm);
        ssd1306_SetCursor(2, 26);
        ssd1306_WriteString(oled_buf, Font_7x10, White);

        // แถว 4: ค่า Timer Hardware Registers
        sprintf(oled_buf, "ARR:%-4lu CCR:%-4lu", current_arr, current_ccr);
        ssd1306_SetCursor(2, 38);
        ssd1306_WriteString(oled_buf, Font_7x10, White);

        // แถว 5: กราฟิก Duty Cycle Progress Bar (0 - 100%)
        ssd1306_DrawRectangle(2, 52, 124, 9, White);
        uint8_t bar_w = (uint8_t)(((uint32_t)actual_duty_pct * 120) / 100);
        if (bar_w > 120) bar_w = 120;
        for (uint8_t y = 54; y <= 58; y++) {
            ssd1306_DrawLine(4, y, 4 + bar_w, y, White);
        }

        ssd1306_UpdateScreen();
    }
    /* USER CODE END 3 */
  }
}
```

---

## 2️⃣ รูปแบบที่ 2: โค้ดควบคุมทั้งความถี่ (Frequency) และ Duty Cycle (PWM)
> **ใช้คู่กับโปรแกรม Python:** `pwm_freq_duty_motor_control.py`  
> คำสั่งที่รับ: `F:<freq>|D:<duty>\n` เช่น `F:2000|D:50\n` (ความถี่ 2,000 Hz, Duty 50%)

### 2.1 สูตรและการคำนวณแบบ Single Slider (Duty 20% - 80% และ Freq 500 Hz - 1,200 Hz)
เมื่อใช้ Slider ตัวเดียว (สเกล 0% ถึง 100%) เพื่อควบคุมทั้งสองค่าพร้อมกัน:
* **สูตรแปลงค่าความถี่ (Frequency):**
  $$f = 500 + \frac{\text{Slider}}{100} \times (1200 - 500) = 500 + 7 \times \text{Slider}\quad (\text{Hz})$$
* **สูตรแปลงค่า Duty Cycle:**
  $$\text{Duty} = 20 + \frac{\text{Slider}}{100} \times (80 - 20) = 20 + 0.6 \times \text{Slider}\quad (\%)$$
* **สูตรหาค่า Timer Registers ($\text{Timer Clock} = 1\text{ MHz}$ ที่ $\text{PSC} = 83$):**
  $$\text{ARR} = \frac{1,000,000}{f} - 1$$
  $$\text{CCR} = \frac{\text{Duty} \times (\text{ARR} + 1)}{100}$$
  $$\text{Period (ms)} = \frac{1,000}{f}$$

#### 📊 ตารางค่า Golden Numbers ตามตำแหน่ง Slider:
| Slider (%) | Frequency (Hz) | Duty Cycle (%) | Period (ms) | Auto-Reload (ARR) | Compare (CCR1) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0% (Min)** | **500 Hz** | **20 %** | **2.00 ms** | **1999** | **400** |
| **25%** | **675 Hz** | **35 %** | **1.48 ms** | **1480** | **518** |
| **50% (Mid)** | **850 Hz** | **50 %** | **1.18 ms** | **1175** | **588** |
| **75%** | **1,025 Hz** | **65 %** | **0.98 ms** | **975** | **634** |
| **100% (Max)** | **1,200 Hz** | **80 %** | **0.83 ms** | **832** | **666** |

*(กรณีนำไปใช้กับ Potentiometer ADC 12-bit บนบอร์ด STM32 โดยตรง: $\text{Slider} = \frac{\text{ADC} \times 100}{4095}$)*

### 2.2 โค้ดในส่วน `while(1)` สำหรับคุมทั้งความถี่และ Duty
แทนที่เนื้อหาใน `/* USER CODE BEGIN 3 */` ด้วยบล็อกนี้:

```c
  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
    // -------------------------------------------------------------------------
    // 1. รับคำสั่งปรับ Frequency และ Duty Cycle จาก Python
    // รูปแบบคำสั่ง: "F:2000|D:50\n" หรือคำสั่ง Duty เดี่ยว "D50\n"
    // -------------------------------------------------------------------------
    if (__HAL_UART_GET_FLAG(&huart2, UART_FLAG_ORE))
    {
        __HAL_UART_CLEAR_OREFLAG(&huart2);
    }

    while (__HAL_UART_GET_FLAG(&huart2, UART_FLAG_RXNE))
    {
        rx_byte = (uint8_t)(huart2.Instance->DR & 0x00FF);

        if (rx_byte == '\n')
        {
            rx_buf[rx_idx] = '\0';

            char *f_ptr = strstr(rx_buf, "F:");
            char *d_ptr = strstr(rx_buf, "D:");

            // กรณีที่ 1: ได้รับคำสั่งทั้งความถี่และ Duty Cycle เช่น "F:2000|D:50"
            if (f_ptr != NULL && d_ptr != NULL)
            {
                freq_hz = (uint32_t)atoi(f_ptr + 2);
                target_duty = (uint16_t)atoi(d_ptr + 2);

                // ป้องกันขอบเขตความถี่ (100 Hz ถึง 50,000 Hz)
                if (freq_hz < 100) freq_hz = 100;
                if (freq_hz > 50000) freq_hz = 50000;
                if (target_duty > 100) target_duty = 100;

                // คำนวณ ARR ใหม่ตามความถี่
                uint32_t new_arr = (1000000UL / freq_hz) - 1;
                __HAL_TIM_SET_AUTORELOAD(&htim1, new_arr);

                // คำนวณ CCR1 ใหม่ตามเปอร์เซ็นต์ Duty
                pwm_val = ((uint32_t)target_duty * (new_arr + 1)) / 100;
                __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);
            }
            // กรณีที่ 2: ได้รับคำสั่งเฉพาะ Duty เช่น "D75"
            else if (rx_buf[0] == 'D')
            {
                target_duty = atoi(&rx_buf[1]);
                if (target_duty > 100) target_duty = 100;

                uint32_t current_arr = __HAL_TIM_GET_AUTORELOAD(&htim1);
                pwm_val = ((uint32_t)target_duty * (current_arr + 1)) / 100;
                __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);
            }

            rx_idx = 0;
        }
        else if (rx_byte != '\r' && rx_idx < sizeof(rx_buf) - 1)
        {
            rx_buf[rx_idx++] = rx_byte;
        }
    }

    // -------------------------------------------------------------------------
    // 2. คำนวณ RPM + ทิศทาง และคำนวณ Freq/Period/Duty จริงจาก Hardware Registers ทุก 100 ms
    // -------------------------------------------------------------------------
    if (HAL_GetTick() - last_calc_time >= SAMPLING_TIME_MS)
    {
        last_calc_time = HAL_GetTick();

        // ก) อ่านค่า Counter จาก Encoder และหา Delta
        current_count = __HAL_TIM_GET_COUNTER(&htim5);
        diff_count = (int32_t)(current_count - prev_count);
        prev_count = current_count;

        // ข) ตรวจวัดทิศทางการหมุนจริง
        if (diff_count > 0)
        {
            strcpy(dir_str, "CW");
        }
        else if (diff_count < 0)
        {
            strcpy(dir_str, "CCW");
        }
        else
        {
            strcpy(dir_str, "STOP");
        }

        // ค) คำนวณ RPM: (|diff_count| * 60) / (CPR * delta_t)
        rpm = ((float)abs(diff_count) * 60.0f) / ((4.0f * ENCODER_PPR) * (SAMPLING_TIME_MS / 1000.0f));

        // ง) คำนวณ Frequency, Period, และ Duty Cycle แบบ Dynamic จาก Register ฮาร์ดแวร์จริง (ไม่ใช่การ Fix ค่า):
        uint32_t current_arr = __HAL_TIM_GET_AUTORELOAD(&htim1);
        uint32_t current_ccr = __HAL_TIM_GET_COMPARE(&htim1, TIM_CHANNEL_1);

        // 1. ความถี่จริง (Hz) = Timer Clock / (ARR + 1)
        freq_hz = 1000000UL / (current_arr + 1);

        // 2. คาบเวลาจริง (ms) = (ARR + 1) / 1000.0
        period_ms = ((float)(current_arr + 1)) / 1000.0f;

        // 3. Duty Cycle จริง (%) = (CCR1 * 100) / (ARR + 1)
        float actual_duty_pct = ((float)current_ccr * 100.0f) / (float)(current_arr + 1);

        // จ) ส่ง Telemetry รูปแบบมาตรฐาน: "F:850|D:50.0|T:1.18|RPM:280.5|DIR:CW\r\n"
        sprintf(tx_buf, "F:%lu|D:%.1f|T:%.2f|RPM:%.1f|DIR:%s\r\n",
                freq_hz, actual_duty_pct, period_ms, rpm, dir_str);
        HAL_UART_Transmit(&huart2, (uint8_t*)tx_buf, strlen(tx_buf), 50);

        // ฉ) แสดงผลสดบนจอ OLED (SSD1306 / SH1106)
        ssd1306_Fill(Black);

        // แถว 1: ความถี่ (500 - 1200 Hz) และ Duty Cycle (20 - 80%)
        sprintf(oled_buf, "F:%4luHz D:%3.0f%%", freq_hz, actual_duty_pct);
        ssd1306_SetCursor(2, 2);
        ssd1306_WriteString(oled_buf, Font_7x10, White);

        // แถว 2: คาบเวลา (ms) และ ทิศทางการหมุนจริง
        sprintf(oled_buf, "T:%4.2fms DIR:%-4s", period_ms, dir_str);
        ssd1306_SetCursor(2, 14);
        ssd1306_WriteString(oled_buf, Font_7x10, White);

        // แถว 3: ความเร็วรอบ Encoder RPM
        sprintf(oled_buf, "RPM: %6.1f", rpm);
        ssd1306_SetCursor(2, 26);
        ssd1306_WriteString(oled_buf, Font_7x10, White);

        // แถว 4: ค่า Timer Hardware Registers (ARR & CCR1)
        sprintf(oled_buf, "ARR:%-4lu CCR:%-4lu", current_arr, current_ccr);
        ssd1306_SetCursor(2, 38);
        ssd1306_WriteString(oled_buf, Font_7x10, White);

        // แถว 5: กราฟิก Duty Cycle Progress Bar (สเกล 20% - 80%)
        ssd1306_DrawRectangle(2, 52, 124, 9, White);
        uint8_t bar_w = (uint8_t)(((uint32_t)actual_duty_pct * 120) / 100);
        if (bar_w > 120) bar_w = 120;
        for (uint8_t y = 54; y <= 58; y++) {
            ssd1306_DrawLine(4, y, 4 + bar_w, y, White);
        }

        ssd1306_UpdateScreen();
    }
    /* USER CODE END 3 */
  }
}
```

---

## ⚠️ ข้อควรระวังและวิธีแก้ปัญหาที่พบบ่อย (Checklist)

1. **ปีกกาปิด `}` ของฟังก์ชัน `main()`:**
   - มักตกหล่นตอนคัดลอกวางโค้ดใน `while(1)`
   - ให้ตรวจดูว่าก่อนฟังก์ชัน `SystemClock_Config(void)` จะต้องมีปีกกาปิด **2 ตัว** เสมอ:
     ```c
       }  // ปิด while(1)
     }    // ปิด main()
     ```
2. **การเปิดใช้งาน Float ใน `sprintf` บน STM32CubeIDE:**
   - หากค่าทศนิยมของ `period_ms` หรือ `rpm` ไม่แสดงผลออกทาง Serial ให้เข้าไปตั้งค่า:
     `Project Properties` → `C/C++ Build` → `Settings` → `Tool Settings` → `MCU Settings`
     → ติ๊ก **Use float with printf from newlib-nano (-u _printf_float)**
3. **การป้องกันคลื่นสะดุด (Glitch-Free PWM Update):**
   - การเปิด Preload ด้วย `__HAL_TIM_ENABLE_OCxPRELOAD(&htim1, TIM_CHANNEL_1)` และ `TIM_CR1_ARPE` จะช่วยให้ค่า ARR และ CCR อัปเดตพร้อมกันตอนครบรอบ Counter เท่านั้น มอเตอร์จะไม่กระตุก
