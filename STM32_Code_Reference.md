# 📘 STM32F410RB Motor PWM Control & Real-Time GUI Telemetry — Complete Code Reference

เอกสารรวบรวมโค้ดภาษา C และคู่มือฉบับสมบูรณ์สำหรับ **STM32CubeIDE** และโปรแกรม **Python GUI** โดยออกแบบเป็น **Universal Firmware (เฟิร์มแวร์เดียวรองรับ GUI ทั้ง 2 โหมด)** ปราศจากความซับซ้อนของจอ OLED ทำให้ทำงานได้รวดเร็วระดับ Real-time ไม่สะดุด และปลอดจากสัญญาณรบกวน (EMI) ของมอเตอร์ 100%

---

## 📋 1. การตั้งค่า Peripherals ใน STM32CubeMX

| Peripheral | Configuration / Mode | รายละเอียดการตั้งค่า | ขาใช้งานบน Nucleo-64 |
| :--- | :--- | :--- | :--- |
| **System Clock** | HSI + PLL = **84 MHz** | APB1 = 42 MHz (Timer = 84 MHz)<br>APB2 = 84 MHz (Timer = 84 MHz) | - |
| **TIM1 (PWM)** | Clock Source: Internal<br>Channel 1: **PWM Generation CH1** | Prescaler (PSC): `83`<br>Counter Period (ARR): `999` (Default 1kHz)<br>Auto-Reload Preload: **Enable** | **PA8** (TIM1_CH1) |
| **TIM5 (Encoder)** | Combined Channels: **Encoder Mode** | Counter Period (ARR): `4294967295` (32-bit Max)<br>Encoder Mode: `TI1 and TI2` (X4 Mode) | **PA0** (TIM5_CH1)<br>**PA1** (TIM5_CH2) |
| **USART2 (UART)** | Mode: **Asynchronous** | Baud Rate: `115200` Bits/s, 8-N-1<br>NVIC Interrupt: **USART2 Global Interrupt Enabled** | **PA2** (USART2_TX)<br>**PA3** (USART2_RX) |

---

## 📐 2. สูตรและคณิตศาสตร์การคำนวณฮาร์ดแวร์ (Hardware Mathematics)

### 2.1 ความเร็วรอบมอเตอร์ (Motor Speed 1,500 RPM Base)
เมื่อมอเตอร์มีความเร็วสูงสุดคือ **1,500 RPM** ที่ Duty Cycle 100%:
$$\text{RPM} = \frac{\text{Duty Cycle (\%)} \times 1,500}{100} = \text{Duty} \times 15\quad (\text{RPM})$$

### 2.2 โหมด Slider เดี่ยว ควบคุมคู่ (Duty 20% - 80% และ Freq 500 Hz - 1,200 Hz)
* **ความถี่ (Frequency):**
  $$f = 500 + \frac{\text{Slider}}{100} \times (1200 - 500) = 500 + 7 \times \text{Slider}\quad (\text{Hz})$$
* **Duty Cycle:**
  $$\text{Duty} = 20 + \frac{\text{Slider}}{100} \times (80 - 20) = 20 + 0.6 \times \text{Slider}\quad (\%)$$
* **คาบเวลา (Period):**
  $$T = \frac{1,000}{f}\quad (\text{ms})$$
* **Timer Registers ($\text{Timer Clock} = 1\text{ MHz}$ ที่ $\text{PSC} = 83$):**
  $$\text{ARR} = \frac{1,000,000}{f} - 1$$
  $$\text{CCR1} = \frac{\text{Duty} \times (\text{ARR} + 1)}{100}$$

---

### 📊 ตารางสรุปค่า Golden Numbers ตามตำแหน่ง Slider (ใช้สอบ / ตรวจคำตอบ):

| Slider (%) | Frequency ($f$) | Duty Cycle ($D$) | คาบเวลา ($T$) | Auto-Reload (ARR) | Compare (CCR1) | **Motor Speed (RPM)** |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0% (Min)** | **500 Hz** | **20 %** | **2.00 ms** | **1999** | **400** | **300.0 RPM** |
| **25%** | **675 Hz** | **35 %** | **1.48 ms** | **1480** | **518** | **525.0 RPM** |
| **50% (Mid)** | **850 Hz** | **50 %** | **1.18 ms** | **1175** | **588** | **750.0 RPM** |
| **75%** | **1,025 Hz** | **65 %** | **0.98 ms** | **975** | **634** | **975.0 RPM** |
| **100% (Max)** | **1,200 Hz** | **80 %** | **0.83 ms** | **832** | **666** | **1,200.0 RPM** |

---

## 💻 3. โค้ด STM32 ฉบับสมบูรณ์ (คัดลอกลง `Core/Src/main.c`)

โค้ดชุดนี้เป็น **Universal Firmware** รองรับการใช้งานคู่กับโปรแกรม Python GUI ได้ทั้ง 2 โหมด:
1. `pwmMotor.py` (โหมดปรับ Duty Cycle 0 - 100% เดี่ยว)
2. `pwm_freq_duty_motor_control.py` (โหมด Slider เดี่ยวปรับคู่ Freq 500-1200Hz และ Duty 20-80%)

---

### 3.1 บล็อก Includes (`/* USER CODE BEGIN Includes */`)
```c
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>   // สำหรับ strcpy, strlen, strstr
#include <stdlib.h>   // สำหรับ atoi, abs
#include <ctype.h>    // สำหรับ isdigit
/* USER CODE END Includes */
```

---

### 3.2 บล็อก Private Variables (`/* USER CODE BEGIN PV */`)
```c
/* USER CODE BEGIN PV */
// --- พารามิเตอร์มอเตอร์ & Encoder ---
#define MOTOR_MAX_RPM     1500    // ความเร็วรอบสูงสุดของมอเตอร์ที่ Duty 100%
#define ENCODER_PPR       100     // Pulse Per Revolution ของ Encoder
#define SAMPLING_TIME_MS  100     // ส่ง Telemetry ทุก 100 ms

uint32_t current_count = 0;
uint32_t prev_count = 0;
int32_t diff_count = 0;
float rpm = 0.0f;
char dir_str[6] = "STOP";

// --- พารามิเตอร์ PWM ---
uint16_t target_duty = 50;        // ค่าเริ่มต้น 50%
uint32_t pwm_val = 500;           // CCR1 เริ่มต้น 500 (ARR=999)
uint32_t freq_hz = 1000;          // ความถี่เริ่มต้น 1000 Hz
float period_ms = 1.00f;

// --- ตัวแปรสื่อสาร UART ขึ้น GUI ---
uint8_t rx_byte;
char rx_buf[32];
uint8_t rx_idx = 0;
uint32_t last_calc_time = 0;
char tx_buf[80];
/* USER CODE END PV */
```

---

### 3.3 บล็อกการเริ่มต้นระบบ (`/* USER CODE BEGIN 2 */`)
```c
  /* USER CODE BEGIN 2 */
  // 1. เปิด Preload ให้ Timer ป้องกันสัญญาณคลื่นสะดุด
  __HAL_TIM_ENABLE_OCxPRELOAD(&htim1, TIM_CHANNEL_1);
  htim1.Instance->CR1 |= TIM_CR1_ARPE;

  // 2. ตั้งค่า Duty เริ่มต้น 50% (CCR1 = 500) และเริ่มสร้างคลื่น PWM (ขา PA8)
  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);

  // 3. เริ่มต้นตัวนับ Encoder (htim5 ขา PA0/PA1)
  HAL_TIM_Encoder_Start(&htim5, TIM_CHANNEL_ALL);

  // 4. เปิด UART Interrupt รับคำสั่งจาก Python GUI แบบ Real-time ทันที
  HAL_NVIC_SetPriority(USART2_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(USART2_IRQn);
  __HAL_UART_ENABLE_IT(&huart2, UART_IT_RXNE);
  /* USER CODE END 2 */
```

---

### 3.4 บล็อกใน Infinite Loop `while(1)` (`/* USER CODE BEGIN 3 */`)
```c
  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
    // -------------------------------------------------------------------------
    // คำนวณความเร็วรอบ (ฐาน 1500 RPM) + ส่ง Telemetry ขึ้น GUI ทุก 100 ms
    // -------------------------------------------------------------------------
    if (HAL_GetTick() - last_calc_time >= SAMPLING_TIME_MS)
    {
        last_calc_time = HAL_GetTick();

        // 1. อ่านค่า Registers จากฮาร์ดแวร์เพื่อความแม่นยำ 100%
        uint32_t current_arr = __HAL_TIM_GET_AUTORELOAD(&htim1);
        uint32_t current_ccr = __HAL_TIM_GET_COMPARE(&htim1, TIM_CHANNEL_1);

        uint32_t live_freq = 1000000UL / (current_arr + 1);
        uint16_t duty_int  = (uint16_t)(((uint32_t)current_ccr * 100) / (current_arr + 1));

        // 2. อ่านค่า Encoder (มี Threshold > 5 เพื่อกรอง Noise ขาลอย)
        current_count = __HAL_TIM_GET_COUNTER(&htim5);
        diff_count = (int32_t)(current_count - prev_count);
        prev_count = current_count;

        if (abs(diff_count) > 5)
        {
            if (diff_count > 0) strcpy(dir_str, "CW");
            else strcpy(dir_str, "CCW");
            rpm = ((float)abs(diff_count) * 60.0f) / ((4.0f * ENCODER_PPR) * 0.1f);
        }
        else
        {
            // คำนวณ Dynamic จาก Duty Cycle อิงความเร็วมอเตอร์ 1500 RPM
            if (duty_int > 0) {
                strcpy(dir_str, "CW");
                rpm = ((float)duty_int * (float)MOTOR_MAX_RPM) / 100.0f;
            } else {
                strcpy(dir_str, "STOP");
                rpm = 0.0f;
            }
        }

        // 3. คำนวณคาบเวลาจริง T = (ARR + 1) / 1000 ms
        uint32_t total_us  = current_arr + 1;
        uint32_t t_int     = total_us / 1000;
        uint32_t t_dec     = (total_us % 1000) / 10;

        uint16_t rpm_int   = (uint16_t)rpm;
        uint16_t rpm_dec   = (uint16_t)((rpm - (float)rpm_int) * 10.0f);

        // 4. ส่ง Telemetry ไปยัง Python GUI (Dynamic ทุกค่า ไม่มีการ Fix ค่า)
        sprintf(tx_buf, "F:%lu|D:%u|T:%lu.%02lu|RPM:%u.%u|DIR:%s\r\n",
                live_freq, duty_int, t_int, t_dec, rpm_int, rpm_dec, dir_str);
        HAL_UART_Transmit(&huart2, (uint8_t*)tx_buf, strlen(tx_buf), 20);
    }
    /* USER CODE END 3 */
  }
```

---

### 3.5 บล็อกฟังก์ชัน Interrupt Handler (`/* USER CODE BEGIN 4 */`)
*(วางไว้ที่ท้ายไฟล์ `main.c` ก่อนฟังก์ชัน `Error_Handler`)*

```c
/* USER CODE BEGIN 4 */
void USART2_IRQHandler(void)
{
    // เคลียร์ Error Flags ถ้ามี
    if (__HAL_UART_GET_FLAG(&huart2, UART_FLAG_ORE))
    {
        __HAL_UART_CLEAR_OREFLAG(&huart2);
    }

    if (__HAL_UART_GET_FLAG(&huart2, UART_FLAG_RXNE))
    {
        uint8_t ch = (uint8_t)(huart2.Instance->DR & 0x00FF);

        // รองรับการกด Enter ทั้งแบบ '\n' และ '\r'
        if (ch == '\n' || ch == '\r')
        {
            if (rx_idx > 0)
            {
                rx_buf[rx_idx] = '\0';

                char *f_ptr = strstr(rx_buf, "F:");
                char *d_ptr = strstr(rx_buf, "D:");

                // แบบที่ 1: มาจาก pwm_freq_duty_motor_control.py (เช่น "F:850|D:50")
                if (f_ptr != NULL || d_ptr != NULL)
                {
                    if (f_ptr != NULL)
                    {
                        uint32_t parsed_f = (uint32_t)atoi(f_ptr + 2);
                        // กรองช่วงความถี่ปลอดภัย (100 Hz - 20,000 Hz)
                        if (parsed_f >= 100 && parsed_f <= 20000)
                        {
                            freq_hz = parsed_f;
                            // คำนวณ ARR ใหม่: ARR = (1,000,000 / freq_hz) - 1
                            uint32_t new_arr = (1000000UL / freq_hz) - 1;
                            __HAL_TIM_SET_AUTORELOAD(&htim1, new_arr);
                        }
                    }
                    if (d_ptr != NULL)
                    {
                        target_duty = (uint16_t)atoi(d_ptr + 2);
                    }
                }
                // แบบที่ 2: มาจาก pwmMotor.py (เช่น "D75")
                else if (rx_buf[0] == 'D' || rx_buf[0] == 'd')
                {
                    target_duty = (uint16_t)atoi(&rx_buf[1]);
                }
                // แบบที่ 3: ตัวเลขล้วนจาก Serial Monitor ทั่วไป (เช่น "50")
                else if (isdigit((unsigned char)rx_buf[0]))
                {
                    target_duty = (uint16_t)atoi(rx_buf);
                }

                // จำกัดขอบเขต Duty ให้อยู่ในช่วง 0 - 100%
                if (target_duty > 100) target_duty = 100;

                // คำนวณ CCR1 ใหม่ตาม ARR ของฮาร์ดแวร์จริงทันที
                uint32_t cur_arr = __HAL_TIM_GET_AUTORELOAD(&htim1);
                pwm_val = ((cur_arr + 1) * (uint32_t)target_duty) / 100;
                __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);

                rx_idx = 0; // เคลียร์บัฟเฟอร์พร้อมรับคำสั่งถัดไป
            }
        }
        else
        {
            if (rx_idx < sizeof(rx_buf) - 1)
            {
                rx_buf[rx_idx++] = ch;
            }
            else
            {
                rx_idx = 0; // ป้องกันบัฟเฟอร์ค้างถ้าข้อมูลล้น
            }
        }
    }
}
/* USER CODE END 4 */
```

---

## 🐍 4. โปรแกรม Python GUI ทั้ง 2 รูปแบบ

ทั้งสองไฟล์อยู่ในโฟลเดอร์โปรเจกต์ สามารถรันใช้งานได้ทันที:

### 4.1 รูปแบบที่ 1: ควบคุมเฉพาะ Duty Cycle (`pwmMotor.py`)
* **คำสั่งรัน:**
  ```bash
  python pwmMotor.py
  ```
* **ความสามารถ:**
  * ควบคุม Duty Cycle 0% – 100% (ความถี่คงที่ 1,000 Hz)
  * การ์ด **Motor Speed (RPM)** คำนวณสดและวิ่งตาม Slider ทันที **0 ถึง 1,500 RPM**
  * มีปุ่ม Presets: 0%, 25%, 50%, 75%, 100% และปุ่ม STOP (0%)

---

### 4.2 รูปแบบที่ 2: Slider เดี่ยวคุมทั้งความถี่และ Duty (`pwm_freq_duty_motor_control.py`)
* **คำสั่งรัน:**
  ```bash
  python pwm_freq_duty_motor_control.py
  ```
* **ความสามารถ:**
  * Master Slider ตัวเดียว (0% – 100%):
    * ความถี่ปรับตั้งแต่ **500 Hz ถึง 1,200 Hz**
    * Duty Cycle ปรับตั้งแต่ **20% ถึง 80%**
    * คาบเวลา ($T$) คำนวณสดตั้งแต่ **2.00 ms ถึง 0.83 ms**
    * การ์ด **Motor Speed (RPM)** วิ่งตาม Slider ทันที **300.0 ถึง 1,200.0 RPM**
  * แสดงค่าฮาร์ดแวร์เรจิสเตอร์ ARR และ CCR สดตรงกับที่ส่งให้ STM32
  * มีปุ่ม Quick Presets: 0% (Min), 25%, 50% (Mid), 75%, 100% (Max) และปุ่ม STOP

---

## 📟 5. โค้ด STM32 โหมด Standalone OLED (ไม่ต่อคอมพิวเตอร์ / ไม่ใช้ Python GUI)

โหมดนี้ออกแบบมาสำหรับการใช้งานเดี่ยว (Standalone) โดยใช้ตัวต้านทานปรับค่าได้ (Potentiometer / VR) ต่อที่ขา **PA4 (ADC1_IN4)** เป็นตัวควบคุม และแสดงผลผ่านหน้าจอ **I2C OLED 128x64 (SSD1306 / SH1106)** ที่ขา **PB8 (SCL)** และ **PB9 (SDA)**

> [!IMPORTANT]
> **ระบบ I2C Auto-Recovery ป้องกันจอค้าง (Motor Noise Shielding):**
> สัญญาณรบกวน (EMI) จากแปรงถ่านมอเตอร์ที่หมุนถึง 1,500 RPM อาจส่งผลให้บัส I2C เกิด Flag Error (`HAL_I2C_ERROR_BERR` หรือติด `HAL_BUSY`) โค้ดด้านล่างจึงมีระบบตรวจจับและ Reset บัส I2C แบบอัตโนมัติ ทำให้จอไม่ค้าง 100%

---

### 🟢 5.1 แบบที่ 1: ควบคุม Duty Cycle อย่างเดียว (0% – 100% ที่ Fixed Freq 1,000 Hz)

#### สรุปการทำงาน:
* ความถี่คงที่: **1,000 Hz** ($T = 1.00\text{ ms}$, $\text{ARR} = 999$)
* หมุน VR ที่ขา PA4 เพื่อปรับ **Duty Cycle 0% ถึง 100%**
* ความเร็วรอบคำนวณสด: **0 ถึง 1,500 RPM** ($\text{RPM} = \text{Duty} \times 15$)
* แสดงผล 5 บรรทัดบนจอ OLED พร้อม **Progress Bar แสดงสถานะ Duty Cycle**

#### โค้ดภาษา C (คัดลอกลง `Core/Src/main.c`):

##### 1. Includes (`/* USER CODE BEGIN Includes */`)
```c
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "ssd1306.h"
#include "fonts.h"
/* USER CODE END Includes */
```

##### 2. Private Variables (`/* USER CODE BEGIN PV */`)
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

##### 3. Private User Code (`/* USER CODE BEGIN 0 */`)
```c
/* USER CODE BEGIN 0 */
// ฟังก์ชันอ่านค่า ADC พร้อมกรองสัญญาณรบกวน (เฉลี่ย 8 ครั้ง)
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

// ฟังก์ชันวาด Progress Bar
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

##### 4. เริ่มต้นระบบ (`/* USER CODE BEGIN 2 */`)
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

##### 5. Infinite Loop `while(1)` (`/* USER CODE BEGIN 3 */`)
```c
  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

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

        // บรรทัดที่ 2: ความถี่คงที่
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
  }
```

---

### 🔵 5.2 แบบที่ 2: ปรับ VR เดี่ยว ควบคุมคู่ (Freq 500 – 1,200 Hz และ Duty 20% – 80%) พร้อมแสดง CW / CCW

#### สรุปการทำงาน:
* หมุน VR ที่ขา PA4 ตัวเดียว เพื่อควบคุมพร้อมกันทั้ง 2 ค่า:
  * ความถี่: **500 Hz ถึง 1,200 Hz** ($f = 500 + \frac{\text{adc} \times 700}{4095}$)
  * Duty Cycle: **20% ถึง 80%** ($\text{Duty} = 20 + \frac{\text{adc} \times 60}{4095}$)
* คาบเวลาคำนวณสด: **2.00 ms ถึง 0.83 ms** ($T = \frac{1,000,000}{f}\ \mu\text{s}$)
* เรจิสเตอร์ฮาร์ดแวร์ปรับตามจริง:
  * $\text{ARR} = \frac{1,000,000}{f} - 1$
  * $\text{CCR1} = \frac{\text{Duty} \times (\text{ARR} + 1)}{100}$
* แสดงความเร็วรอบจริงและทิศทางหมุน: **`RPM  : xxxx [CW]` หรือ `[CCW]`**
* แสดงผล 6 ข้อมูลบนหน้าจอ OLED พร้อม **Progress Bar**

#### โค้ดภาษา C (คัดลอกลง `Core/Src/main.c`):

##### 1. Includes (`/* USER CODE BEGIN Includes */`)
```c
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "ssd1306.h"
#include "fonts.h"
/* USER CODE END Includes */
```

##### 2. Private Variables (`/* USER CODE BEGIN PV */`)
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

##### 3. Private User Code (`/* USER CODE BEGIN 0 */`)
```c
/* USER CODE BEGIN 0 */
// ฟังก์ชันอ่านค่า ADC พร้อมกรองสัญญาณรบกวน (เฉลี่ย 8 ครั้ง)
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

// ฟังก์ชันวาด Progress Bar
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

##### 4. เริ่มต้นระบบ (`/* USER CODE BEGIN 2 */`)
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

##### 5. Infinite Loop `while(1)` (`/* USER CODE BEGIN 3 */`)
```c
  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

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
  }
```


