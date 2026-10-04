# คู่มือการใช้งานจอ OLED 1.3 นิ้ว I2C กับ STM32 (ฉบับเข้าใจง่าย สำหรับทำข้อสอบ)

จอ OLED ขนาด **1.3 นิ้ว** (Resolution 128x64) เกือบทั้งหมดในตลาดและในห้องแล็บจะใช้ชิปควบคุมเบอร์ **SH1106** (ซึ่งต่างจากจอ 0.96 นิ้วที่ใช้ **SSD1306**) 

> ⚠️ **ความจริงเรื่องการสอบและการเขียนจอ OLED:**  
> ไม่มีใครเขียนโค้ดวาด Font ทีละพิกเซลสดๆ จากศูนย์ในห้องสอบได้ เพราะต้องใช้ตารางรหัสภาพอักษร (Font Table) หลายร้อยบรรทัด ในการสอบ/แล็บจะทำได้ 2 รูปแบบ:
> 1. **รูปแบบที่ 1 (ข้อสอบทั่วไป):** อาจารย์จะแจกไฟล์ Library (`ssd1306.c` / `ssd1306.h` หรือ `sh1106.c`) มาให้ แล้วให้เรานำเข้าโปรเจกต์และเรียกใช้ฟังก์ชันให้เป็น
> 2. **รูปแบบที่ 2 (ข้อสอบระดับทฤษฎี/Register):** ใช้วิธีส่งคำสั่ง Command ด้วยฟังก์ชัน `HAL_I2C_...` เพียวๆ เพื่อเปิดจอหรือสแกนหา Address

คู่มือนี้สรุปเนื้อหาที่ต้องรู้และต้องจำให้ครบทั้ง 2 รูปแบบครับ

---

## ส่วนที่ 1: การตั้งค่าใน STM32CubeMX

1. ไปที่แถบ **Connectivity** > เลือก **`I2C1`**
2. ปรับ Mode เป็น **`I2C`**
3. เช็คขาที่โปรแกรมเลือกให้ (มักจะเป็น `PB8` สำหรับ **SCL** และ `PB9` สำหรับ **SDA**)
4. ในแท็บ **Parameter Settings**:
   - **I2C Speed Mode**: `Standard Mode` (100 KHz) หรือ `Fast Mode` (400 KHz)
   - แนะนำตั้งเป็น `Fast Mode` (400 KHz) ถ้าต้องการให้จอกระพริบอัปเดตข้อมูลได้ลื่นขึ้น

> 📌 **การต่อสายฮาร์ดแวร์:**
> - `VCC` -> 3.3V (หรือ 5V ขึ้นกับสเปกโมดูล)
> - `GND` -> GND
> - `SCL` -> ขา SCL ของ STM32 (เช่น `PB8`)
> - `SDA` -> ขา SDA ของ STM32 (เช่น `PB9`)

---

## ส่วนที่ 2: วิธีนำ Library เข้าโปรเจกต์ใน STM32CubeIDE

เมื่อมีไฟล์ Library (เช่น `ssd1306.c`, `ssd1306.h`, `fonts.c`, `fonts.h`):
1. ก๊อปปี้ไฟล์ `.h` ไปวางไว้ที่โฟลเดอร์: `Core/Inc`
2. ก๊อปปี้ไฟล์ `.c` ไปวางไว้ที่โฟลเดอร์: `Core/Src`
3. ใน STM32CubeIDE ให้คลิกขวาที่ชื่อโปรเจกต์แล้วเลือก **Refresh** (หรือกดปุ่ม `F5`)

---

## ส่วนที่ 3: 5 คำสั่งหลักที่ต้องจำ (ใช้บ่อยที่สุดในข้อสอบ)

ไม่ว่าจะเป็น Library ยี่ห้อไหน (SSD1306 หรือ SH1106) จะมีรูปแบบคำสั่งมาตรฐานเหมือนกัน 5 คำสั่งนี้:

### 1. คำสั่ง Include และตั้งค่าเริ่มต้น (Init)
* วางใน `/* USER CODE BEGIN Includes */`
  ```c
  #include "ssd1306.h"
  #include "fonts.h"
  #include <stdio.h> // สำหรับใช้ sprintf แปลงตัวเลขเป็นตัวหนังสือ
  ```
* วางใน `/* USER CODE BEGIN 2 */` (เรียกครั้งเดียวเพื่อปลุกจอ)
  ```c
  ssd1306_Init(); // สั่งเริ่มต้นการทำงานของหน้าจอ
  ```

---

### 2. ล้างหน้าจอ (Clear Screen)
ลบภาพหรือข้อความเก่าออกจากหน่วยความจำบัฟเฟอร์:
```c
ssd1306_Fill(Black); // เติมสีดำทั้งจอ (คือการเคลียร์จอให้ว่าง)
```

---

### 3. เลื่อนเคอร์เซอร์ / จุดเริ่มเขียน (Set Cursor)
พิกัดมุมซ้ายบนสุดคือ `(0, 0)` จอมีความกว้าง `128` สูง `64` พิกเซล:
```c
// ssd1306_SetCursor(แกน X แนวนอน 0-127, แกน Y แนวตั้ง 0-63);
ssd1306_SetCursor(0, 0);   // บรรทัดที่ 1 ชิดซ้าย
ssd1306_SetCursor(0, 20);  // บรรทัดที่ 2 (ขยับลงมา 20 pixel)
```

---

### 4. เขียนข้อความ (Write String)
```c
// รูปแบบ: ssd1306_WriteString("ข้อความ", ขนาดฟอนต์, สีตัวอักษร);
ssd1306_WriteString("Hello World!", Font_7x10, White);
```
*(ขนาด Font มาตรฐานมักมี: `Font_6x8`, `Font_7x10`, `Font_11x18`, `Font_16x26`)*

---

### 5. คำสั่งอัปเดตหน้าจอ (Update Screen)
> 🚨 **ข้อสอบมักพลาดตรงนี้มากที่สุด!**  
> คำสั่ง `WriteString` หรือ `Fill` จะทำงานแค่ใน RAM ของ STM32 เท่านั้น **ถ้าไม่สั่ง `UpdateScreen` หน้าจอจะยังคงมืดสนิท!**

```c
ssd1306_UpdateScreen(); // ส่งข้อมูลจาก RAM ไปยังหน้าจอ I2C จริงๆ
```

---

## ส่วนที่ 4: โค้ดตัวอย่างสมบูรณ์แบบ (พร้อมก๊อปปี้ลงข้อสอบ - ผ่านการทดสอบจริง 100%)

ตัวอย่างนี้แสดงผลครบทุกฟีเจอร์ยอดฮิตในข้อสอบ (อิงจากไลบรารีในโฟลเดอร์ `OLED_Library/`):
- **บรรทัดที่ 1:** หัวข้อเรื่อง (`Font_7x10`)
- **บรรทัดที่ 2:** ค่าความถี่ตัวใหญ่ชัดเจน (`Font_11x18`)
- **บรรทัดที่ 3:** ค่าที่อ่านได้จาก ADC (`Font_7x10`)
- **บรรทัดที่ 4:** สถานะ Duty Cycle (`Font_7x10`)
- ทำงานร่วมกับ Timer PWM และปรับค่าแบบ Real-time ด้วย `HAL_GetTick() >= 50`

### 1. ส่วน Include (`/* USER CODE BEGIN Includes */`)
```c
#include "ssd1306.h"
#include "fonts.h"
#include <stdio.h> // จำเป็นสำหรับ sprintf
```

### 2. ส่วนประกาศตัวแปร (`/* USER CODE BEGIN PV */`)
```c
uint16_t adc_val = 0;       // ค่า ADC (0 - 4095)
float freq_target = 1000.0f; // ความถี่เป้าหมาย
uint32_t last_time = 0;     // ตัวแปรจับเวลา Non-blocking
char str_buf[20];           // บัฟเฟอร์ข้อความสำหรับ OLED
```

### 3. ส่วนเริ่มการทำงาน (`/* USER CODE BEGIN 2 */`)
```c
HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1); // สั่งเริ่มสร้าง PWM (ถ้ามีโจทย์ PWM)
ssd1306_Init(); // สั่งเปิดจอ (ในไลบรารีเปิดวงจร Charge Pump ทั้ง SSD1306 และ SH1106 อัตโนมัติ)
```

### 4. ส่วนการทำงานในลูป (`/* USER CODE BEGIN 3 */`)
```c
  if (HAL_GetTick() - last_time >= 50) // อัปเดตทุก 50ms (20 ครั้ง/วินาที ไม่หน่วงระบบ)
  {
      last_time = HAL_GetTick();

      // กะพริบไฟ LED LD2 (PA5) เพื่อบอกสถานะว่าไมโครคอนโทรลเลอร์ทำงานปกติ ไม่ค้าง
      HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);

      // 1. อ่านค่า ADC จากวอลลุ่ม (0 - 4095)
      HAL_ADC_Start(&hadc1);
      if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
      {
          adc_val = HAL_ADC_GetValue(&hadc1);
      }
      HAL_ADC_Stop(&hadc1);

      // 2. แปลงค่า ADC เป็นความถี่ (เช่น 1000 - 2000 Hz)
      freq_target = 1000.0f + ((float)adc_val * 1000.0f / 4095.0f);

      // 3. ปรับ ARR / CCR ของ Timer แบบ Real-time (PSC = 83 @ 84MHz)
      uint16_t arr_val = (uint16_t)(1000000.0f / freq_target) - 1;
      uint16_t ccr_val = (arr_val + 1) / 2; // ล็อก 50% Duty Cycle
      __HAL_TIM_SET_AUTORELOAD(&htim1, arr_val);
      __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, ccr_val);

      // 4. จัดการวาดภาพบนจอ OLED
      ssd1306_Fill(Black); // 1. ล้างจอเดิม

      // บรรทัดที่ 1: หัวข้อด้านบน (X=0, Y=0)
      ssd1306_SetCursor(0, 0);
      ssd1306_WriteString("STM32 CONTROLLER", Font_7x10, White);

      // บรรทัดที่ 2: แสดงค่าความถี่ตัวใหญ่ (X=0, Y=16)
      // ⚠️ จุดระวังข้อสอบ: STM32CubeIDE ปิด float ใน sprintf ไว้ ต้อง cast เป็น (int) เสมอ!
      sprintf(str_buf, "%4d Hz", (int)freq_target);
      ssd1306_SetCursor(0, 16);
      ssd1306_WriteString(str_buf, Font_11x18, White);

      // บรรทัดที่ 3: แสดงค่า ADC (X=0, Y=42)
      sprintf(str_buf, "ADC: %4d", adc_val);
      ssd1306_SetCursor(0, 42);
      ssd1306_WriteString(str_buf, Font_7x10, White);

      // บรรทัดที่ 4: แสดง Duty Cycle ด้านขวา (X=70, Y=42)
      ssd1306_SetCursor(70, 42);
      ssd1306_WriteString("D: 50%", Font_7x10, White);

      // 5. สั่งส่งภาพขึ้นจอจริง (ห้ามลืมคำสั่งนี้เด็ดขาด!)
      ssd1306_UpdateScreen();
  }
```

---

### รูปแบบที่ 2: Fix ความถี่คงที่ แล้วปรับ Duty Cycle 20% - 80% ด้วยวอลลุ่ม

โจทย์ยอดนิยมอีกรูปแบบ: **"กำหนดให้ความถี่คงที่ (เช่น 1,000 Hz) และใช้วอลลุ่มปรับ Duty Cycle ในช่วง 20% ถึง 80%"**

#### สูตรการคำนวณ:
1. **Fix ความถี่ (ที่ 84 MHz, PSC = 83 -> นับ 1 MHz):**
   $$ARR = \frac{1,000,000}{1,000} - 1 = 999 \quad (\text{คาบเวลาทั้งหมด } = 1,000 \text{ สเต็ป})$$
2. **แปลง ADC (0 - 4095) เป็น Duty Cycle (20.0% - 80.0%):**
   $$\text{Duty (\%)} = 20.0 + \left( \frac{\text{ADC} \times (80.0 - 20.0)}{4095.0} \right) = 20.0 + \left( \frac{\text{ADC} \times 60.0}{4095.0} \right)$$
3. **คำนวณค่า Compare (CCR):**
   $$CCR = \frac{(ARR + 1) \times \text{Duty}}{100.0} = \frac{1000 \times \text{Duty}}{100} = 10 \times \text{Duty}$$
   - เมื่อหมุนต่ำสุด ($ADC = 0$): $\text{Duty} = 20.0\% \implies CCR = 200$
   - เมื่อหมุนสูงสุด ($ADC = 4095$): $\text{Duty} = 80.0\% \implies CCR = 800$

#### โค้ดใน `main.c`:
```c
/* USER CODE BEGIN PV */
uint16_t adc_val = 0;
float duty_percent = 20.0f;
uint16_t ccr_val = 200;
uint32_t last_time = 0;
char str_buf[25];

#define PWM_ARR_FIXED  999 // กำหนดความถี่ 1,000 Hz คงที่ (PSC = 83)
/* USER CODE END PV */

/* USER CODE BEGIN 2 */
HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1); // สั่งเริ่มสร้าง PWM
__HAL_TIM_SET_AUTORELOAD(&htim1, PWM_ARR_FIXED); // ตั้ง ARR ให้ได้ 1,000 Hz
ssd1306_Init(); // เปิดจอ OLED
/* USER CODE END 2 */

/* USER CODE BEGIN 3 */
  if (HAL_GetTick() - last_time >= 50)
  {
      last_time = HAL_GetTick();
      HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5); // ไฟ LED กะพริบบอกสถานะบอร์ด

      // 1. อ่านค่า ADC จากวอลลุ่ม (0 - 4095)
      HAL_ADC_Start(&hadc1);
      if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
      {
          adc_val = HAL_ADC_GetValue(&hadc1);
      }
      HAL_ADC_Stop(&hadc1);

      // 2. คำนวณ Duty Cycle ในช่วง 20.0% ถึง 80.0%
      duty_percent = 20.0f + ((float)adc_val * 60.0f / 4095.0f);

      // 3. คำนวณค่า CCR (ช่วง 200 ถึง 800)
      ccr_val = (uint16_t)(((PWM_ARR_FIXED + 1) * duty_percent) / 100.0f);

      // 4. สั่งเปลี่ยน Duty Cycle ทันที
      __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, ccr_val);

      // 5. แสดงผลบนจอ OLED
      ssd1306_Fill(Black);

      // บรรทัดที่ 1: หัวข้อ
      ssd1306_SetCursor(0, 0);
      ssd1306_WriteString("PWM CONTROLLER", Font_7x10, White);

      // บรรทัดที่ 2: ค่า Duty Cycle ตัวใหญ่ (Font 11x18)
      // เทคนิคแยกทศนิยม 1 ตำแหน่ง เพื่อเลี่ยงบั๊ก Float ใน CubeIDE
      int duty_int = (int)duty_percent;
      int duty_dec = (int)(duty_percent * 10.0f) % 10;
      sprintf(str_buf, "Duty: %2d.%1d %%", duty_int, duty_dec);
      ssd1306_SetCursor(0, 16);
      ssd1306_WriteString(str_buf, Font_11x18, White);

      // บรรทัดที่ 3: ค่า ADC และ CCR (Font 7x10)
      sprintf(str_buf, "ADC:%4d CCR:%3d", adc_val, ccr_val);
      ssd1306_SetCursor(0, 40);
      ssd1306_WriteString(str_buf, Font_7x10, White);

      // บรรทัดที่ 4: ความถี่คงที่ (Font 7x10)
      ssd1306_SetCursor(0, 52);
      ssd1306_WriteString("Freq: 1000 Hz (FIX)", Font_7x10, White);

      // 6. ส่งภาพขึ้นจอจริง
      ssd1306_UpdateScreen();
  }
/* USER CODE END 3 */
```

---

## ส่วนที่ 5: จุดแตกต่างสำคัญระหว่างจอ 1.3" (SH1106) กับ 0.96" (SSD1306)

* **จอ 0.96 นิ้ว (SSD1306):** แรมของจอมีขนาด `128x64` ตรงกับขนาดการแสดงผล
* **จอ 1.3 นิ้ว (SH1106):** แรมของจอมีขนาด `132x64` แต่หน้าจอแสดงผลเพียง `128x64`
* ❗ **อาการที่มักเจอ:** หากนำไดรเวอร์ของ SSD1306 ไปขับจอ 1.3 นิ้วตรงๆ หน้าจอจะติด แต่ **ภาพจะเบี้ยวเยื้องไปทางขวา 2 พิกเซล** และขอบด้านขวาจะมีจุดสัญญาณรบกวน (Noise)
* 💡 **วิธีแก้ในโค้ด (ถ้าอาจารย์ให้แก้เอง):**  
  ในไฟล์ `ssd1306.c` ตรงฟังก์ชัน `UpdateScreen` ให้ค้นหาคำสั่งที่ตั้ง Column Address:
  - ปกติ SSD1306 จะส่ง: `0x00` (Lower Column) และ `0x10` (Higher Column)
  - ให้เปลี่ยนค่าเริ่มต้นคอลัมน์ของ SH1106 โดยบวก Offset เข้าไป 2 พิกเซล คือส่งคำสั่ง `0x02` แทน `0x00`

---

## ส่วนที่ 6: การเขียน I2C เพียวๆ ด้วย HAL (ระดับ Register / Command)

หากในข้อสอบไม่อนุญาตให้ใช้ไฟล์ไลบรารี แต่ให้อ่าน/เขียน I2C ด้วยคำสั่ง HAL ของ STM32:

### 1. ฟังก์ชันส่งข้อมูล I2C พื้นฐาน
```c
HAL_I2C_Master_Transmit(&hi2c1, DevAddress, pData, Size, Timeout);
```
- `&hi2c1` : ตัวแปร Handle ของ I2C1
- `DevAddress` : เลข Address ของจอ OLED โดยจอ I2C ปกติมี Address คือ `0x3C`
  > ⚠️ **ข้อควรระวังเรื่อง Address ใน STM32 HAL:**  
  > ฟังก์ชันของ HAL ต้องการ Address ขนาด 8-bit (ต้อง Shift ซ้าย 1 บิต):  
  > `0x3C << 1` ซึ่งมีค่าเท่ากับ **`0x78`**

### 2. วิธีเขียนฟังก์ชันสแกนหา Address ของจอ I2C (I2C Scanner)
เทคนิคนี้มีประโยชน์มากในห้องสอบ เพื่อเช็คว่าสายไฟหลวม หรือบอร์ดมองเห็นจอหรือไม่:

```c
void scan_i2c(void)
{
    char msg[32];
    for (uint16_t i = 1; i < 128; i++)
    {
        // ตรวจสอบว่ามีอุปกรณ์ตอบรับที่ Address นี้หรือไม่
        if (HAL_I2C_IsDeviceReady(&hi2c1, (i << 1), 1, 10) == HAL_OK)
        {
            // ถ้าเจอ จะเข้าเงื่อนไขนี้ (จอ OLED มักเจอที่ 0x3C)
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET); // สั่งไฟติดเพื่อบอกว่าเจอแล้ว
            break;
        }
    }
}
```

---

## ส่วนที่ 7: ปัญหาที่พบบ่อยและวิธีแก้ในห้องสอบ (Troubleshooting)

### 1. หน้าจอมืดสนิท ไม่มีอะไรขึ้นเลย
* **สาเหตุที่ 1 (โปรแกรมค้างที่โหมด Debug):**  
  หากกดแฟลชผ่านปุ่ม **Debug (ไอคอนแมลง 🐞)** โปรแกรมจะหยุดรออยู่ที่บรรทัดแรกของ `main()` เสมอ **ให้กดปุ่ม Resume (ปุ่ม Play สีเขียว ▶ หรือกด `F8`)** เพื่อให้โปรแกรมเริ่มทำงาน
* **สาเหตุที่ 2 (บัส I2C ค้างจากการแฟลชโค้ด):**  
  ให้ **ถอดสาย USB ของบอร์ด STM32 ออกจากคอมฯ แล้วเสียบใหม่ (Cold Reboot)** เพื่อตัดไฟรีเซ็ตตัวโมดูลจอ OLED จริงๆ
* **สาเหตุที่ 3 (สายหลวมหรือต่อสลับขา):**  
  ตรวจสอบว่าขา `SCL` ต่อเข้า `PB8` และ `SDA` ต่อเข้า `PB9` ของ STM32 แน่นหนาดี
* **สาเหตุที่ 4 (ไฟแสดงสถานะบอร์ด):**  
  สังเกตไฟ **LED LD2 (PA5)** บนบอร์ด STM32 จะต้องกะพริบถี่ๆ แสดงว่าโค้ดกำลังทำงานปกติ

### 2. ตัวเลขไม่แสดงผล หรือขึ้นแค่ตัวหนังสือด้านหลัง (เช่น ขึ้นแค่ " Hz")
* **สาเหตุ:** `STM32CubeIDE` จะปิดฟังก์ชัน Floating Point (`%f`) ใน `sprintf` ไว้เพื่อประหยัดหน่วยความจำ Flash
* **วิธีแก้:** ให้แปลงเป็นเลขจำนวนเต็มด้วยการ Cast เป็น `(int)` เสมอ เช่น:
  ```c
  sprintf(str_buf, "%4d Hz", (int)freq_target); // ✅ ติดชัวร์ 100% โดยไม่ต้องแก้ Linker Flags
  ```

### 3. ตัวหนังสือแหว่งหรือโดนตัด
* **สาเหตุ:** เกิดจากการอ่านบิตในตารางฟอนต์ไม่ตรงกับการจัดเรียงข้อมูล
* **สถานะปัจจุบัน:** ในไฟล์โฟลเดอร์ `OLED_Library/` (`ssd1306.c`, `fonts.c`) ได้รับการแก้ไขและทดสอบกับจอจริงเรียบร้อยแล้ว แสดงผลเต็มตัวอักษรคมชัดทุกขนาดฟอนต์

---

## 📋 Checklist สรุปป้องกันการเสียคะแนนในห้องสอบ
1. [ ] **เช็คสาย I2C:** `SCL` -> `PB8`, `SDA` -> `PB9` (ห้ามสลับขา)
2. [ ] **ตั้งค่า CubeMX:** I2C1 Mode = I2C, Speed = Fast Mode (400 kHz)
3. [ ] **นำไฟล์เข้าโปรเจกต์:** ก๊อป `.h` ไป `Core/Inc` และ `.c` ไป `Core/Src` แล้วกด **F5 (Refresh)**
4. [ ] **อย่าลืมสั่ง Init:** ต้องมี `ssd1306_Init()` ใน `USER CODE BEGIN 2`
5. [ ] **อย่าลืมสั่ง Update:** ทุกครั้งที่เขียนข้อความ ต้องตบท้ายด้วย `ssd1306_UpdateScreen()`
6. [ ] **หน่วงเวลาอัปเดตจอ:** ให้ใช้ `HAL_GetTick() - last_time >= 50` เพื่อไม่ให้อัปเดตถี่เกินไปจน I2C ค้าง
7. [ ] **แปลงตัวเลขด้วย sprintf:** ถ้าเป็นทศนิยมให้ cast เป็น `(int)` เช่น `sprintf(buf, "%d", (int)val);` เสมอ

