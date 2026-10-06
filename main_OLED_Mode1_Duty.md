# 📘 STM32F410RB Standalone OLED Mode 1: ควบคุม Duty Cycle 0% – 100% (ความถี่คงที่ 1,000 Hz)

คู่มือฉบับสมบูรณ์สำหรับการคัดลอก-วาง (Copy & Paste) ลงในไฟล์ `Core/Src/main.c` ที่เจนเนอเรตมาจาก **STM32CubeMX / STM32CubeIDE**  
**โหมด Standalone ไม่ต่อคอมพิวเตอร์ (ไม่ใช้ Python GUI) ควบคุมด้วยตัวต้านทานปรับค่าได้ (VR ที่ขา A2 / PA4) และแสดงผลบนจอ OLED I2C 128x64 พร้อมบอกความเร็วรอบ (0-1500 RPM) และทิศทางหมุน `[CW]` / `[CCW]` / `[STOP]`**

---

## 📌 1. ภาพรวมการทำงาน (System Overview)

* **ความถี่สัญญาณ PWM:** คงที่ที่ **1,000 Hz** ($T = 1.00\text{ ms}$, $\text{ARR} = 999$)
* **ตัวควบคุม:** หมุนตัวต้านทานปรับค่าได้ (VR) ที่ขา **A2 (PA4 / ADC1_IN4)** ปรับ **Duty Cycle 0% – 100%**
* **สัญญาณ PWM ขาออก:** ส่งออกที่ขา **PA8** (TIM1_CH1) เพื่อขับ Motor Driver
* **การวัดความเร็วรอบและทิศทาง:**
  * อ่านค่าจาก Encoder จริงที่ขา **PA0/PA1** (TIM5 Encoder Mode)
  * หากไม่มี Encoder ต่อ จะคำนวณ Dynamic ตามระดับ Duty Cycle (ฐานมอเตอร์สูงสุด **1,500 RPM** ที่ Duty 100%)
  * แสดงทิศทางหมุนบนจอ OLED ชัดเจน: **`[CW]`** (ตามเข็ม), **`[CCW]`** (ทวนเข็ม), หรือ **`[STOP]`** (หยุด)
* **หน้าจอ OLED (SSD1306 / SH1106 I2C):** แสดงผล 5 บรรทัด พร้อมแถบกราฟิก **Progress Bar** ตามเปอร์เซ็นต์ Duty Cycle
* **ระบบความปลอดภัย (Anti-Freeze):** มีฟังก์ชัน **I2C Auto-Recovery** ตรวจจับและกู้คืนบัส I2C ป้องกันจอค้างจากสัญญาณรบกวน (EMI) ของมอเตอร์ 100%

---

## 🔌 2. ตารางการต่อสายฮาร์ดแวร์ (Hardware Wiring Diagram)

| อุปกรณ์ | ขาบนบอร์ด Nucleo-64 | ขาบนชิป STM32F410RB | ฟังก์ชันฮาร์ดแวร์ | รายละเอียดการเชื่อมต่อ |
| :--- | :--- | :--- | :--- | :--- |
| **Potentiometer (VR)** | **A2** (CN8 ขา 3) | **PA4** | `ADC1_IN4` | ขากลางของ VR (ขาสัญญาณ Analog 0 - 3.3V) |
| | **+3.3V** (CN8 ขา 4) | +3.3V | VDD | ขาขวาของ VR (⚠️ **ห้ามต่อ 5V**) |
| | **GND** (CN8 ขา 7) | GND | GND | ขาซ้ายของ VR |
| **I2C OLED 128x64** | **D15** / SCL (CN5 ขา 10) | **PB8** | `I2C1_SCL` | ขา Clock ของจอ OLED |
| | **D14** / SDA (CN5 ขา 9) | **PB9** | `I2C1_SDA` | ขา Data ของจอ OLED |
| | **+3.3V** หรือ **+5V** | VDD | VCC | ไฟเลี้ยงจอ OLED |
| | **GND** | GND | GND | กราวด์ร่วม |
| **Motor Driver (PWM)** | **D7** / PA8 (CN9 ขา 8) | **PA8** | `TIM1_CH1` | สัญญาณ PWM ขับมอเตอร์ |
| **Motor Encoder** | **A0** (CN8 ขา 1) | **PA0** | `TIM5_CH1` | สัญญาณ Encoder Phase A |
| | **A1** (CN8 ขา 2) | **PA1** | `TIM5_CH2` | สัญญาณ Encoder Phase B |

---

## 📐 3. สูตรคณิตศาสตร์และการคำนวณ (Mathematical Calculations)

### 3.1 การแปลงค่า ADC เป็น Duty Cycle:
ADC ขนาด 12-bit มีค่าตั้งแต่ $0$ ถึง $4095$ ($0\text{V} - 3.3\text{V}$):
$$\text{Duty Cycle (\%)} = \frac{\text{adc\_val} \times 100}{4095}$$

### 3.2 การคำนวณ Register TIM1 ($\text{PSC} = 83$ ที่ 84 MHz):
$$\text{ARR} = \frac{1,000,000}{1,000} - 1 = 999$$
$$\text{CCR1} = \frac{\text{Duty (\%)} \times (\text{ARR} + 1)}{100} = \text{Duty (\%)} \times 10$$

### 3.3 การคำนวณความเร็วรอบ (Motor Speed Base 1,500 RPM):
$$\text{RPM} = \frac{\text{Duty (\%)} \times 1,500}{100} = \text{Duty (\%)} \times 15$$

---

## 📊 4. ตารางตรวจเช็กผลการทำงาน (Verification Checklist)

| ตำแหน่งหมุน VR | ค่า ADC (PA4) | Duty Cycle (%) | ARR | CCR1 | **ความเร็วรอบ (RPM)** | สถานะทิศทาง (DIR) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **หมุนซ้ายสุด** | 0 | **0 %** | 999 | 0 | **0 RPM** | `STOP` |
| **หมุน 25%** | ~1023 | **25 %** | 999 | 250 | **375 RPM** | `CW` |
| **หมุนตรงกลาง (50%)** | ~2047 | **50 %** | 999 | 500 | **750 RPM** | `CW` |
| **หมุน 75%** | ~3071 | **75 %** | 999 | 750 | **1,125 RPM** | `CW` |
| **หมุนขวาสุด** | 4095 | **100 %** | 999 | 999 | **1,500 RPM** | `CW` |

---

## 🖥️ 5. รูปแบบหน้าจอ OLED (128x64 Pixels)

```text
+------------------------+
|   == MODE 1: DUTY ==   |  <- Line 1: Header
|   Freq : 1000 Hz       |  <- Line 2: ความถี่คงที่ 1000 Hz
|   Duty :  50 %         |  <- Line 3: เปอร์เซ็นต์ Duty Cycle (0 - 100%)
|   RPM  :  750 [CW]     |  <- Line 4: ความเร็วรอบและทิศทางหมุน
|   DIR  : CW            |  <- Line 5: ทิศทางหมุนชัดเจน
| [======        ]       |  <- Line 6: กราฟิก Progress Bar (0 - 100%)
+------------------------+
```

---

## 📋 6. โค้ดสำหรับคัดลอก-วาง ลงใน `main.c` ที่เจนเนอเรตมาจาก CubeMX

> 💡 **วิธีใช้งาน:**  
> เปิดไฟล์ `Core/Src/main.c` ใน STM32CubeIDE แล้วคัดลอกโค้ดแต่ละบล็อกไปวาง **เฉพาะในช่อง `/* USER CODE BEGIN ... */` ถึง `/* USER CODE END ... */`** ตามหมายเลขหัวข้อด้านล่างนี้ได้เลย (ห้ามลบโค้ดที่ CubeMX สร้างขึ้นภายนอกบล็อก):

---

### บล็อกที่ 1: Includes (`/* USER CODE BEGIN Includes */`)
*(วางไว้ช่วงต้นไฟล์ บรรทัดประมาณ 25)*

```c
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "ssd1306.h"
#include "fonts.h"
/* USER CODE END Includes */
```

---

### บล็อกที่ 2: Private Variables (`/* USER CODE BEGIN PV */`)
*(วางไว้ใต้ตัวแปร Handles เช่น `hadc1`, `hi2c1`, `htim1`, `htim5` บรรทัดประมาณ 55)*

```c
/* USER CODE BEGIN PV */
#define MOTOR_MAX_RPM     1500
#define ENCODER_PPR       100

// --- ตัวแปร PWM & ADC ---
uint32_t adc_val = 0;
uint16_t duty_val = 0;       // 0 - 100 %
uint32_t ccr_val = 0;        // CCR1
float rpm_disp = 0.0f;       // RPM 0 - 1500

// --- ตัวแปร Encoder & ทิศทางหมุน (CW / CCW / STOP) ---
uint32_t current_count = 0;
uint32_t prev_count = 0;
int32_t diff_count = 0;
char dir_str[6] = "STOP";    // แสดง CW, CCW, หรือ STOP

// --- ตัวจับเวลา ---
uint32_t last_adc_tick = 0;
uint32_t last_enc_tick = 0;
uint32_t last_oled_tick = 0;
char disp_str[32];
/* USER CODE END PV */
```

---

### บล็อกที่ 3: Helper Functions (`/* USER CODE BEGIN 0 */`)
*(วางไว้เหนือฟังก์ชัน `int main(void)` บรรทัดประมาณ 85)*

```c
/* USER CODE BEGIN 0 */
// ฟังก์ชันอ่านค่า ADC PA4 พร้อมกรองสัญญาณรบกวน (เฉลี่ย 8 ครั้ง)
uint32_t Read_ADC_Filtered(void)
{
    uint32_t sum = 0;
    for (int i = 0; i < 8; i++)
    {
        HAL_ADC_Start(&hadc1);
        if (HAL_ADC_PollForConversion(&hadc1, 5) == HAL_OK)
        {
            sum += HAL_ADC_GetValue(&hadc1);
        }
        HAL_ADC_Stop(&hadc1);
    }
    return sum / 8;
}

// ระบบ I2C Auto-Recovery ป้องกันจอค้างจากสัญญาณรบกวนของมอเตอร์
void OLED_CheckAndRecoverI2C(void)
{
    if (hi2c1.State != HAL_I2C_STATE_READY || hi2c1.ErrorCode != HAL_I2C_ERROR_NONE)
    {
        __HAL_RCC_I2C1_FORCE_RESET();
        HAL_Delay(2);
        __HAL_RCC_I2C1_RELEASE_RESET();
        HAL_I2C_Init(&hi2c1);
    }
}

// ฟังก์ชันวาดแถบ Progress Bar
void OLED_DrawBar(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint8_t pct)
{
    if (pct > 100) pct = 100;
    ssd1306_DrawRectangle(x, y, w, h, White);
    uint8_t fill_w = (uint8_t)(((uint16_t)(w - 4) * pct) / 100);
    for (uint8_t i = 2; i < h - 2; i++)
    {
        if (fill_w > 0)
        {
            ssd1306_DrawLine(x + 2, y + i, x + 2 + fill_w, y + i, White);
        }
    }
}
/* USER CODE END 0 */
```

---

### บล็อกที่ 4: การเริ่มต้นระบบ (`/* USER CODE BEGIN 2 */`)
*(วางไว้ในฟังก์ชัน `main()` ใต้ฟังก์ชัน `MX_..._Init()` ทั้งหมด บรรทัดประมาณ 135)*

```c
  /* USER CODE BEGIN 2 */
  // 1. ตั้งค่า Timer Preload
  __HAL_TIM_ENABLE_OCxPRELOAD(&htim1, TIM_CHANNEL_1);
  htim1.Instance->CR1 |= TIM_CR1_ARPE;

  // 2. ความถี่คงที่ 1000 Hz (ARR = 999), เริ่มต้น Duty 0% (CCR1 = 0)
  __HAL_TIM_SET_AUTORELOAD(&htim1, 999);
  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 0);
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);

  // 3. เริ่มต้นตัวนับ Encoder (htim5 ขา PA0/PA1)
  HAL_TIM_Encoder_Start(&htim5, TIM_CHANNEL_ALL);

  // 4. เริ่มต้นหน้าจอ OLED
  HAL_Delay(100);
  ssd1306_Init();
  ssd1306_Fill(Black);
  ssd1306_SetCursor(10, 20);
  ssd1306_WriteString("OLED SYSTEM OK", Font_7x10, White);
  ssd1306_SetCursor(10, 36);
  ssd1306_WriteString("MODE 1: DUTY", Font_7x10, White);
  ssd1306_UpdateScreen();
  HAL_Delay(500);
  /* USER CODE END 2 */
```

---

### บล็อกที่ 5: ลูปการทำงานหลัก (`/* USER CODE BEGIN 3 */`)
*(วางไว้ในลูป `while (1)` บรรทัดประมาณ 160)*

```c
    /* USER CODE BEGIN 3 */
    // -------------------------------------------------------------------------
    // 1. อ่านค่า ADC (PA4 / A2) และอัปเดต PWM ทุก 30 ms
    // -------------------------------------------------------------------------
    if (HAL_GetTick() - last_adc_tick >= 30)
    {
        last_adc_tick = HAL_GetTick();

        adc_val = Read_ADC_Filtered();

        // แปลงเป็น Duty Cycle 0 - 100%
        duty_val = (uint16_t)(((uint32_t)adc_val * 100) / 4095);
        if (duty_val > 100) duty_val = 100;

        // คำนวณ CCR1 ที่ ARR = 999 (CCR1 = duty * 10)
        ccr_val = (uint32_t)duty_val * 10;
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, ccr_val);
    }

    // -------------------------------------------------------------------------
    // 2. คำนวณความเร็วรอบ (RPM) และทิศทางหมุน (CW / CCW) ทุก 100 ms
    // -------------------------------------------------------------------------
    if (HAL_GetTick() - last_enc_tick >= 100)
    {
        uint32_t dt = HAL_GetTick() - last_enc_tick;
        last_enc_tick = HAL_GetTick();

        current_count = __HAL_TIM_GET_COUNTER(&htim5);
        diff_count = (int32_t)(current_count - prev_count);
        prev_count = current_count;

        // มีสัญญาณหมุนจาก Encoder จริง (Threshold > 5 กรอง Noise)
        if (abs(diff_count) > 5)
        {
            if (diff_count > 0) strcpy(dir_str, "CW");
            else strcpy(dir_str, "CCW");

            rpm_disp = ((float)abs(diff_count) * 60000.0f) / ((4.0f * ENCODER_PPR) * (float)dt);
        }
        else
        {
            // คำนวณจาก Duty Cycle (ฐาน 1500 RPM)
            if (duty_val > 0)
            {
                strcpy(dir_str, "CW");
                rpm_disp = ((float)duty_val * (float)MOTOR_MAX_RPM) / 100.0f;
            }
            else
            {
                strcpy(dir_str, "STOP");
                rpm_disp = 0.0f;
            }
        }
    }

    // -------------------------------------------------------------------------
    // 3. รีเฟรชหน้าจอ OLED ทุก 150 ms (แสดงผลชัดเจน 5 บรรทัด + แถบกราฟิก)
    // -------------------------------------------------------------------------
    if (HAL_GetTick() - last_oled_tick >= 150)
    {
        last_oled_tick = HAL_GetTick();

        OLED_CheckAndRecoverI2C();
        ssd1306_Fill(Black);

        // บรรทัดที่ 1: Header
        ssd1306_SetCursor(10, 0);
        ssd1306_WriteString("== MODE 1: DUTY ==", Font_7x10, White);

        // บรรทัดที่ 2: ความถี่คงที่ 1000 Hz
        ssd1306_SetCursor(2, 11);
        ssd1306_WriteString("Freq : 1000 Hz", Font_7x10, White);

        // บรรทัดที่ 3: Duty Cycle (0 - 100%)
        sprintf(disp_str, "Duty : %3u %%", duty_val);
        ssd1306_SetCursor(2, 22);
        ssd1306_WriteString(disp_str, Font_7x10, White);

        // บรรทัดที่ 4: ความเร็วรอบ RPM พร้อมทิศทางหมุน [CW] / [CCW] / [STOP]
        sprintf(disp_str, "RPM  : %4u [%s]", (uint16_t)rpm_disp, dir_str);
        ssd1306_SetCursor(2, 33);
        ssd1306_WriteString(disp_str, Font_7x10, White);

        // บรรทัดที่ 5: ทิศทางชัดเจน
        sprintf(disp_str, "DIR  : %s", dir_str);
        ssd1306_SetCursor(2, 44);
        ssd1306_WriteString(disp_str, Font_7x10, White);

        // บรรทัดที่ 6: แถบ Progress Bar (0 - 100%)
        OLED_DrawBar(2, 56, 124, 7, (uint8_t)duty_val);

        ssd1306_UpdateScreen();
    }
    /* USER CODE END 3 */
```
