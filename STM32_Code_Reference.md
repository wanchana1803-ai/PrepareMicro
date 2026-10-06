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

// --- ตัวแปรสื่อสาร UART ---
uint8_t rx_byte;
char rx_buf[32];
uint8_t rx_idx = 0;
uint32_t last_calc_time = 0;
char tx_buf[80];
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

        // จ) คำนวณ Period (ms)
        period_ms = 1000.0f / (float)freq_hz;

        // ฉ) ส่ง Telemetry รูปแบบมาตรฐาน: "F:1000|D:50|T:1.00|RPM:280.5|DIR:CW\r\n"
        sprintf(tx_buf, "F:%lu|D:%u|T:%.2f|RPM:%.1f|DIR:%s\r\n",
                freq_hz, target_duty, period_ms, rpm, dir_str);
        HAL_UART_Transmit(&huart2, (uint8_t*)tx_buf, strlen(tx_buf), 50);
    }
    /* USER CODE END 3 */
  }
}
```

---

## 2️⃣ รูปแบบที่ 2: โค้ดควบคุมทั้งความถี่ (Frequency) และ Duty Cycle (PWM)
> **ใช้คู่กับโปรแกรม Python:** `pwm_freq_duty_motor_control.py`  
> คำสั่งที่รับ: `F:<freq>|D:<duty>\n` เช่น `F:2000|D:50\n` (ความถี่ 2,000 Hz, Duty 50%)

### 2.1 สูตรการคำนวณปรับความถี่และ Duty Cycle แบบ Real-time
ที่ Timer Clock = $1,000,000\text{ Hz}$ ($\text{PSC} = 83$ ที่บัส 84 MHz):
$$\text{ARR} = \frac{1,000,000}{f} - 1$$
$$\text{CCR} = \frac{\text{Duty}\% \times (\text{ARR} + 1)}{100}$$
$$\text{Period (ms)} = \frac{1,000}{f}$$

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
    // 2. คำนวณ RPM + ทิศทางการหมุนจริง และส่ง Telemetry ทุก 100 ms
    // -------------------------------------------------------------------------
    if (HAL_GetTick() - last_calc_time >= SAMPLING_TIME_MS)
    {
        last_calc_time = HAL_GetTick();

        current_count = __HAL_TIM_GET_COUNTER(&htim5);
        diff_count = (int32_t)(current_count - prev_count);
        prev_count = current_count;

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

        rpm = ((float)abs(diff_count) * 60.0f) / ((4.0f * ENCODER_PPR) * (SAMPLING_TIME_MS / 1000.0f));
        period_ms = 1000.0f / (float)freq_hz;

        // รูปแบบ Telemetry: "F:2000|D:50|T:0.50|RPM:280.5|DIR:CW\r\n"
        sprintf(tx_buf, "F:%lu|D:%u|T:%.2f|RPM:%.1f|DIR:%s\r\n",
                freq_hz, target_duty, period_ms, rpm, dir_str);
        HAL_UART_Transmit(&huart2, (uint8_t*)tx_buf, strlen(tx_buf), 50);
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
