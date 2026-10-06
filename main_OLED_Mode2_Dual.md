# 📘 STM32F410RB Standalone OLED Mode 2: ปรับ VR เดี่ยว ควบคุมคู่ (Freq 500 – 1,200 Hz และ Duty 20% – 80%)

คู่มือฉบับสมบูรณ์สำหรับการคัดลอก-วาง (Copy & Paste) ลงในไฟล์ `Core/Src/main.c` ที่เจนเนอเรตมาจาก **STM32CubeMX / STM32CubeIDE**  
**โหมด Standalone ไม่ต่อคอมพิวเตอร์ (ไม่ใช้ Python GUI) หมุนตัวต้านทานปรับค่าได้ (VR ที่ขา A2 / PA4) เพียงตัวเดียวเพื่อควบคุมทั้งความถี่ (Frequency 500-1200 Hz) และ Duty Cycle (20-80%) พร้อมกัน แสดงผลบนจอ OLED I2C 128x64 ครบทั้งค่าฮาร์ดแวร์ ARR, CCR, คาบเวลา, RPM (300-1200) และทิศทางหมุน `[CW]` / `[CCW]` / `[STOP]`**

---

## 📌 1. ภาพรวมการทำงาน (System Overview)

* **ตัวควบคุม:** หมุนตัวต้านทานปรับค่าได้ (VR) ที่ขา **A2 (PA4 / ADC1_IN4)** ตัวเดียว ปรับพร้อมกันทั้ง 2 ตัวแปร:
  * **ความถี่ (Frequency):** ปรับตั้งแต่ **500 Hz ถึง 1,200 Hz**
  * **Duty Cycle:** ปรับตั้งแต่ **20% ถึง 80%**
* **คาบเวลา (Period):** คำนวณจริงตามความถี่ **2.00 ms ถึง 0.83 ms** ($T = \frac{1,000,000}{f}\ \mu\text{s}$)
* **ฮาร์ดแวร์เรจิสเตอร์ (TIM1):** อัปเดตแบบ Dynamic ทันที:
  * **ARR:** ปรับตั้งแต่ **1999 ลงมาถึง 832**
  * **CCR1:** ปรับตั้งแต่ **400 ขึ้นไปถึง 666**
* **ความเร็วรอบและทิศทาง:**
  * อ่านค่าจาก Encoder จริงที่ขา **PA0/PA1** (TIM5 Encoder Mode)
  * หากไม่มี Encoder ต่อ จะคำนวณ Dynamic ตามระดับ Duty Cycle (ฐานความเร็วมอเตอร์สูงสุด **1,500 RPM** ที่ 100%) ทำให้ได้ช่วงความเร็ว **300 ถึง 1,200 RPM**
  * แสดงทิศทางหมุนบนจอ OLED ชัดเจน: **`[CW]`** (ตามเข็ม), **`[CCW]`** (ทวนเข็ม), หรือ **`[STOP]`** (หยุด)
* **หน้าจอ OLED (SSD1306 / SH1106 I2C):** แสดงผล 6 ข้อมูล พร้อมแถบกราฟิก **Progress Bar** ตามตำแหน่ง VR (0% – 100%)
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

### 3.1 การแปลงค่า ADC (0 – 4095) เป็นตัวแปรควบคุม:
* **ความถี่ (Frequency $f$ ช่วง 500 Hz ถึง 1,200 Hz):**
  $$f = 500 + \frac{\text{adc\_val} \times (1,200 - 500)}{4095} = 500 + \frac{\text{adc\_val} \times 700}{4095}\quad (\text{Hz})$$

* **Duty Cycle ($D$ ช่วง 20% ถึง 80%):**
  $$\text{Duty} = 20 + \frac{\text{adc\_val} \times (80 - 20)}{4095} = 20 + \frac{\text{adc\_val} \times 60}{4095}\quad (\%)$$

### 3.2 การคำนวณ Timer Registers ($\text{Timer Clock} = 1\text{ MHz}$ ที่ $\text{PSC} = 83$):
* **Auto-Reload Register (ARR):**
  $$\text{ARR} = \frac{1,000,000}{f} - 1$$
* **Capture/Compare Register 1 (CCR1):**
  $$\text{CCR1} = \frac{\text{Duty} \times (\text{ARR} + 1)}{100}$$
* **คาบเวลา (Period $T$):**
  $$T = \frac{1,000}{f}\quad (\text{ms}) \quad \text{หรือ} \quad T = \frac{1,000,000}{f}\quad (\mu\text{s})$$

### 3.3 การคำนวณความเร็วรอบ (Motor Speed Base 1,500 RPM):
$$\text{RPM} = \frac{\text{Duty} \times 1,500}{100} = \text{Duty} \times 15\quad (\text{ช่วง } 300 - 1,200\text{ RPM})$$

---

## 📊 4. ตาราง Golden Numbers ตรวจคำตอบ (Exam Verification Table)

| ตำแหน่งหมุน VR | ค่า ADC (PA4) | ความถี่ ($f$) | Duty Cycle | คาบเวลา ($T$) | Auto-Reload (ARR) | Compare (CCR1) | **Motor Speed (RPM)** | ทิศทาง (DIR) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0% (หมุนซ้ายสุด)** | 0 | **500 Hz** | **20 %** | **2.00 ms** | **1999** | **400** | **300.0 RPM** | `CW` |
| **25%** | 1023 | **675 Hz** | **35 %** | **1.48 ms** | **1480** | **518** | **525.0 RPM** | `CW` |
| **50% (ตรงกลาง)** | 2047 | **850 Hz** | **50 %** | **1.18 ms** | **1175** | **588** | **750.0 RPM** | `CW` |
| **75%** | 3071 | **1,025 Hz** | **65 %** | **0.98 ms** | **975** | **634** | **975.0 RPM** | `CW` |
| **100% (หมุนขวาสุด)** | 4095 | **1,200 Hz** | **80 %** | **0.83 ms** | **832** | **666** | **1,200.0 RPM** | `CW` |

---

## 🖥️ 5. รูปแบบหน้าจอ OLED (128x64 Pixels)

```text
+------------------------+
|   == MODE 2: DUAL ==   |  <- Line 1: Header
|   F: 850Hz T:1.17ms    |  <- Line 2: ความถี่และคาบเวลาจริง
|   Duty : 50 %          |  <- Line 3: เปอร์เซ็นต์ Duty Cycle (20 - 80%)
|   RPM  :  750 [CW]     |  <- Line 4: ความเร็วรอบและทิศทางหมุน
|   ARR:1175 CCR: 588    |  <- Line 5: ค่า Timer Register จริง
| [======        ]       |  <- Line 6: กราฟิก Progress Bar (VR 0-100%)
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
uint32_t freq_hz = 500;      // 500 - 1200 Hz
uint16_t duty_val = 20;      // 20 - 80 %
uint32_t arr_val = 1999;     // ARR
uint32_t ccr_val = 400;      // CCR1
float period_ms = 2.00f;     // คาบเวลา (ms)
float rpm_disp = 300.0f;     // 300 - 1200 RPM
uint8_t vr_pct = 0;          // 0 - 100 % สำหรับ Progress Bar

// --- ตัวแปร Encoder & ทิศทางหมุน (CW / CCW / STOP) ---
uint32_t current_count = 0;
uint32_t prev_count = 0;
int32_t diff_count = 0;
char dir_str[6] = "CW";      // แสดง CW, CCW, หรือ STOP

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

  // 2. เริ่มต้น PWM ที่ 500 Hz (ARR=1999) และ Duty 20% (CCR1=400)
  __HAL_TIM_SET_AUTORELOAD(&htim1, 1999);
  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 400);
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
  ssd1306_WriteString("MODE 2: DUAL", Font_7x10, White);
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
    // 1. อ่านค่า ADC (PA4 / A2) และคำนวณ Freq + Duty พร้อมอัปเดต Timer ทุก 30 ms
    // -------------------------------------------------------------------------
    if (HAL_GetTick() - last_adc_tick >= 30)
    {
        last_adc_tick = HAL_GetTick();

        adc_val = Read_ADC_Filtered();

        // 1.1 คำนวณเปอร์เซ็นต์ VR (0 - 100%)
        vr_pct = (uint8_t)(((uint32_t)adc_val * 100) / 4095);
        if (vr_pct > 100) vr_pct = 100;

        // 1.2 คำนวณ Frequency: 500 Hz ถึง 1,200 Hz
        freq_hz = 500 + (((uint32_t)adc_val * 700) / 4095);

        // 1.3 คำนวณ Duty Cycle: 20% ถึง 80%
        duty_val = 20 + (uint16_t)(((uint32_t)adc_val * 60) / 4095);
        if (duty_val > 80) duty_val = 80;

        // 1.4 คำนวณ Timer ARR & CCR1
        arr_val = (1000000UL / freq_hz) - 1;
        ccr_val = ((arr_val + 1) * (uint32_t)duty_val) / 100;

        // อัปเดตฮาร์ดแวร์ Timer จริง
        __HAL_TIM_SET_AUTORELOAD(&htim1, arr_val);
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, ccr_val);

        // 1.5 คำนวณคาบเวลา Period (ms)
        period_ms = 1000.0f / (float)freq_hz;
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
    // 3. รีเฟรชหน้าจอ OLED ทุก 150 ms (แสดงผลครบ 6 บรรทัด + แถบกราฟิก)
    // -------------------------------------------------------------------------
    if (HAL_GetTick() - last_oled_tick >= 150)
    {
        last_oled_tick = HAL_GetTick();

        OLED_CheckAndRecoverI2C();
        ssd1306_Fill(Black);

        // บรรทัดที่ 1: Header
        ssd1306_SetCursor(10, 0);
        ssd1306_WriteString("== MODE 2: DUAL ==", Font_7x10, White);

        // บรรทัดที่ 2: ความถี่ & คาบเวลา
        uint32_t p_int = (uint32_t)period_ms;
        uint32_t p_dec = (uint32_t)((period_ms - (float)p_int) * 100.0f);
        sprintf(disp_str, "F:%4luHz T:%lu.%02lums", freq_hz, p_int, p_dec);
        ssd1306_SetCursor(2, 12);
        ssd1306_WriteString(disp_str, Font_7x10, White);

        // บรรทัดที่ 3: Duty Cycle (20 - 80%)
        sprintf(disp_str, "Duty : %2u %%", duty_val);
        ssd1306_SetCursor(2, 24);
        ssd1306_WriteString(disp_str, Font_7x10, White);

        // บรรทัดที่ 4: ความเร็วรอบ RPM พร้อมทิศทางหมุน [CW] / [CCW]
        sprintf(disp_str, "RPM  : %4u [%s]", (uint16_t)rpm_disp, dir_str);
        ssd1306_SetCursor(2, 36);
        ssd1306_WriteString(disp_str, Font_7x10, White);

        // บรรทัดที่ 5: ค่า Timer Register จริง
        sprintf(disp_str, "ARR:%4lu CCR:%4lu", arr_val, ccr_val);
        ssd1306_SetCursor(2, 48);
        ssd1306_WriteString(disp_str, Font_7x10, White);

        // บรรทัดที่ 6: แถบ Progress Bar (อิงตาม VR 0 - 100%)
        OLED_DrawBar(2, 58, 124, 6, vr_pct);

        ssd1306_UpdateScreen();
    }
    /* USER CODE END 3 */
```
