# คู่มือสรุปคำสั่ง STM32 HAL Driver (STM32F410RB)
**โปรแกรมที่ใช้:** STM32CubeMX & STM32CubeIDE  
**หมวดหมู่ครอบคลุม:** Digital Input, Digital Output, Analog Input (ADC), Analog Output (DAC), PWM Output

---

## 📌 โครงสร้างและกฎการวางโค้ดใน `main.c`
เวลาใช้ **STM32CubeMX** ร่วมกับ **STM32CubeIDE** ทุกครั้งที่มีการ Generate โค้ดใหม่ ตัวสร้างโค้ดจะทับไฟล์เดิม ดังนั้น **ต้องเขียนโค้ดไว้ระหว่างคู่ Comment เท่านั้น**:

| ส่วนของ Comment | หน้าที่ / วัตถุประสงค์ |
| :--- | :--- |
| `/* USER CODE BEGIN Includes */` | สำหรับ `#include` ไลบรารีเพิ่มเติม |
| `/* USER CODE BEGIN PV */` | ประกาศตัวแปร Global / Private Variables (เช่น เก็บค่า ADC, PWM) |
| `/* USER CODE BEGIN 2 */` | โค้ดที่รัน **ครั้งเดียว** ก่อนเข้า Loop (เช่น สั่ง Start PWM, Start DAC) |
| `/* USER CODE BEGIN WHILE */` / `/* USER CODE BEGIN 3 */` | โค้ดที่วนทำงานซ้ำเรื่อยๆ ใน `while (1)` (เช่น อ่านปุ่ม, อ่าน ADC, สั่งงาน) |

---

## 1. Digital Output (สั่งเปิด-ปิดขา Pin)

### การตั้งค่าใน CubeMX:
- คลิกเลือกขาที่ต้องการ (เช่น `PA5` บนบอร์ด Nucleo มักเป็น User LED) -> เลือกเป็น **`GPIO_Output`**

### คำสั่งที่ใช้:
```c
// 1. สั่งจ่ายไฟ HIGH (ติด)
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);

// 2. สั่งตัดไฟ LOW (ดับ)
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);

// 3. สลับสถานะ (ถ้าติดให้ดับ, ถ้าดับให้ติด)
HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);

// 4. หน่วงเวลา (หน่วยเป็นมิลลิวินาที: ms)
HAL_Delay(500); // รอ 500 ms
```

### จุดที่นำไปวางใน `main.c`:
```c
  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
    HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5); // สลับสถานะ LED
    HAL_Delay(500);                        // หน่วงเวลา 0.5 วินาที
  }
  /* USER CODE END 3 */
```

---

## 2. Digital Input (อ่านค่าปุ่มกด/สวิตช์)

### การตั้งค่าใน CubeMX:
- คลิกเลือกขาที่ต้องการ (เช่น `PC13` ปุ่ม User Button) -> เลือกเป็น **`GPIO_Input`**
- ในหมวด **System Core** > **GPIO**: ตั้งค่า Pull-up หรือ Pull-down ให้ตรงกับวงจรภายนอก

### คำสั่งพื้นฐานที่ใช้:
```c
// อ่านสถานะขา โดยจะคืนค่าเป็น GPIO_PIN_SET (1) หรือ GPIO_PIN_RESET (0)
GPIO_PinState state = HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13);
```

### แบบที่ 1: "กดติด - ปล่อยดับ" (พื้นฐาน)
```c
  /* USER CODE BEGIN 3 */
  // ถ้ากดปุ่ม (ปุ่ม Active Low บนบอร์ด Nucleo กดแล้วเป็น 0 หรือ GPIO_PIN_RESET)
  if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) == GPIO_PIN_RESET)
  {
      HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);   // ให้ LED ติด
  }
  else
  {
      HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET); // ให้ LED ดับ
  }
  /* USER CODE END 3 */
```

### แบบที่ 2: "กด 1 ครั้งสลับสถานะ (Toggle Switch)" + ตรวจจับขอบสัญญาณ (Edge Detection)
> ⚠️ **ทำไมห้ามสั่ง `TogglePin` ใน `if` ตรงๆ?**  
> เพราะไมโครวนลูปเร็วนับล้านรอบต่อวินาที กดค้างแค่เสี้ยววินาทีไฟจะ Toggle รัวๆ คุมไม่ได้  
> **วิธีแก้:** ต้องตรวจจับเฉพาะจังหวะที่ "เพิ่งกด" (จากไม่กด 1 กลายเป็นกด 0) เท่านั้น!

#### ประกาศตัวแปรใน `/* USER CODE BEGIN PV */`:
```c
/* USER CODE BEGIN PV */
uint8_t last_btn_state = GPIO_PIN_SET; // ปุ่ม Active Low ไม่กดคือ SET (1)
uint8_t press_count = 0;              // ตัวแปรนับจำนวนครั้งที่กด (ถ้าต้องการนับ)
/* USER CODE END PV */
```

#### โค้ดใน `/* USER CODE BEGIN 3 */` (ใน while loop):
```c
  /* USER CODE BEGIN 3 */
  uint8_t current_btn_state = HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13);

  // ตรวจจับจังหวะ "เพิ่งกด" (ตอนนี้เป็น RESET แต่รอบที่แล้วเป็น SET)
  if (current_btn_state == GPIO_PIN_RESET && last_btn_state == GPIO_PIN_SET)
  {
      // 1. สลับสถานะไฟ LED (กดติด กดอีกทีดับ)
      HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);

      // 2. นับจำนวนครั้งที่กด (ถ้าโจทย์สั่งให้นับ)
      press_count++;

      // 3. หน่วงเวลาสั้นๆ 20ms เพื่อป้องกันหน้าสัมผัสกระดอน (Debounce)
      HAL_Delay(20);
  }

  // จำสถานะปัจจุบันไว้เปรียบเทียบในรอบถัดไป
  last_btn_state = current_btn_state;
  /* USER CODE END 3 */
```

---

## 3. Input Analog (อ่านค่า ADC)

### การตั้งค่าใน CubeMX:
- ไปที่หมวด **Analog** > **ADC1**
- ติ๊กเลือกช่อง Channel ที่ต้องการใช้งาน เช่น `IN0` (ขา `PA0`)

### 1) ประกาศตัวแปรใน `USER CODE BEGIN PV`:
```c
/* USER CODE BEGIN PV */
uint16_t adc_val = 0;   // ค่าดิบ 12-bit (0 ถึง 4095)
float voltage = 0.0f;   // ค่าแรงดันจริง (0.0 ถึง 3.3 V)
uint32_t adc_prev_tick = 0;
/* USER CODE END PV */
```

### 2) คำสั่งที่ใช้อ่านค่าแบบ Polling ใน `USER CODE BEGIN 3`:
```c
  /* USER CODE BEGIN 3 */
  // แนะนำ: ใช้อ่านร่วมกับ HAL_GetTick() ทุก 100 ms เพื่อไม่ให้ค้าง
  if (HAL_GetTick() - adc_prev_tick >= 100)
  {
      adc_prev_tick = HAL_GetTick();

      // 1. สั่งเริ่มการอ่านค่า ADC
      HAL_ADC_Start(&hadc1);

      // 2. รอการแปลงสัญญาณเสร็จสิ้น (Timeout 10 ms)
      if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
      {
          // 3. ดึงค่าผลลัพธ์มาเก็บไว้ในตัวแปร (0 - 4095)
          adc_val = HAL_ADC_GetValue(&hadc1);

          // 4. (สูตรยอดฮิตข้อสอบ) แปลงค่าตัวเลขเป็นแรงดัน Volt จริง (0 - 3.3V)
          voltage = ((float)adc_val * 3.3f) / 4095.0f;
      }

      // 5. สั่งหยุดการทำงานของ ADC
      HAL_ADC_Stop(&hadc1);

      // 6. ปริ้นท์ค่าดูผ่าน Serial Monitor หรือ SWV
      printf("ADC: %4d | Volt: %.2f V\r\n", adc_val, voltage);
  }
  /* USER CODE END 3 */
```

### 💡 ทริคข้อสอบเรื่อง ADC:
- **ความละเอียด (Resolution):** STM32F410 เป็น **12-bit** ค่าที่อ่านได้จะมีช่วงคือ `0` ถึง `4095` ($2^{12} - 1$)
- **สูตรคำนวณแปลงเป็น Volt:**
  $$\text{Voltage} = \frac{\text{ADC\_Value} \times 3.3}{4095}$$


---

## 4. Output Analog (ส่งสัญญาณแรงดันผ่าน DAC)

STM32F410RB มีตัวสร้างแรงดันสัญญาณอนาล็อกจริง (DAC) ที่ขา **PA5** (DAC1 Channel 1)

### การตั้งค่าใน CubeMX:
- ไปที่หมวด **Analog** > **DAC**
- ติ๊กเปิด **`OUT1 Configuration`**
- Trigger: เลือกเป็น **`None`**

### 1) สั่ง Start DAC ใน `USER CODE BEGIN 2`:
```c
  /* USER CODE BEGIN 2 */
  // สั่งเปิดการทำงานของ DAC Channel 1 (เรียกครั้งเดียว)
  HAL_DAC_Start(&hdac, DAC_CHANNEL_1);
  /* USER CODE END 2 */
```

### 2) ปรับแรงดันใน `USER CODE BEGIN 3`:
ความละเอียด 12-bit จัดชิดขวา (`DAC_ALIGN_12B_R`) ช่วงค่าคือ `0` (0V) ถึง `4095` (~3.3V)
```c
  /* USER CODE BEGIN 3 */
  // ตัวอย่าง: จ่ายแรงดันประมาณ 1.65V (กึ่งหนึ่งของ 3.3V)
  HAL_DAC_SetValue(&hdac, DAC_CHANNEL_1, DAC_ALIGN_12B_R, 2048);
  HAL_Delay(1000);

  // ปรับเป็น 3.3V เต็มสเกล
  HAL_DAC_SetValue(&hdac, DAC_CHANNEL_1, DAC_ALIGN_12B_R, 4095);
  HAL_Delay(1000);
  /* USER CODE END 3 */
```

---

## 5. Output PWM (สัญญาณควบคุมพัลส์/ความเร็ว/หรี่ไฟ)

### การตั้งค่าใน CubeMX:
- ไปที่หมวด **Timers** > เลือก Timer (เช่น `TIM1`)
- Channel 1: เลือกเป็น **`PWM Generation CH1`** (ขา `PA8`)
- ตั้งค่า **Prescaler (PSC)** และ **Counter Period (ARR)** ในแถบ Parameter Settings:
  - บอร์ด STM32F410RB จาก Clock Tree วิ่งที่ **84 MHz**
  - ตั้ง **`Prescaler (PSC) = 83`** และ **`Counter Period (ARR) = 999`** จะได้ความถี่ **1 kHz** พอดีเป๊ะ ไม่ต้องคำนวณซับซ้อน!

### 1) ประกาศตัวแปรใน `USER CODE BEGIN PV`:
```c
/* USER CODE BEGIN PV */
uint16_t adc_val = 0;   // ค่า ADC (0 - 4095)
uint16_t pwm_val = 0;   // ค่าความสว่าง PWM (0 - 999)
uint32_t last_time = 0; // ตัวแปรจับเวลา
/* USER CODE END PV */
```

### 2) สั่ง Start PWM ใน `USER CODE BEGIN 2`:
```c
  /* USER CODE BEGIN 2 */
  // สั่งให้ Timer เริ่มสร้างสัญญาณ PWM ออกที่ขา Channel นั้นๆ (เรียกครั้งเดียว)
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
  /* USER CODE END 2 */
```

### 3) ตัวอย่างการปรับ Duty Cycle ใน `USER CODE BEGIN 3`:

#### แบบ A: ปรับค่าคงที่ (Fixed Duty Cycle)
```c
  // สูตรคำสั่ง: __HAL_TIM_SET_COMPARE(&htimX, TIM_CHANNEL_X, duty_value);
  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 500);  // Duty Cycle 50% (500/1000)
```

#### แบบ B: ข้อสอบยอดฮิต! นำค่า ADC มาหรี่ไฟ LED ให้ได้ 0 - 100% เต็มสเกล
> 💡 **ทริคแก้ปัญหา Duty ไม่ถึง 100% หรือสว่างไม่สุด:**  
> 1. ใน STM32 PWM Mode 1 สัญญาณเป็น HIGH เมื่อ `CNT < CCR` ดังนั้นถ้าต้องการ 100% เต็มสนิท ค่า Compare ต้องจ่ายได้ถึง `ARR + 1` (เช่น ตั้ง ARR=1000 และจ่าย CCR สูงสุด 1000)  
> 2. วอลลุ่มจริงหมุนสุดอาจได้ไม่ถึง 4095 (อาจได้ 4050 จากความต้านทานสาย) จึงควรใส่ **Deadband (ตัดหัว-ตัดท้าย)** เพื่อรับประกันว่าจะได้ 0% และ 100% แน่นอน

```c
  /* USER CODE BEGIN 3 */
  if (HAL_GetTick() - last_time >= 50) // อัปเดตทุกๆ 50 ms (ลื่นไหล ไม่กระตุก)
  {
      last_time = HAL_GetTick();

      // 1. อ่านค่า ADC จากตัวต้านทานปรับค่าได้
      HAL_ADC_Start(&hadc1);
      if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
      {
          adc_val = HAL_ADC_GetValue(&hadc1); // อ่านค่า 0 - 4095
      }
      HAL_ADC_Stop(&hadc1);

      // 2. คำนวณเป็น Duty Cycle 0 - 1000 (0.0% - 100.0%)
      pwm_val = (uint32_t)adc_val * 1000 / 4095;

      // 3. ทริคตัดหัวตัดท้าย (Deadband) รับประกัน 0% และ 100% เต็ม
      if (adc_val >= 4050) pwm_val = 1000; // หมุนเกือบสุด ให้จ่าย 100% เต็มทันที
      if (adc_val <= 30)   pwm_val = 0;    // หมุนลงต่ำสุด ให้ดับสนิท 0%

      // 4. สั่งจ่ายค่า Duty Cycle ให้หลอดไฟ LED (ขา PA8)
      __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);

      // 5. ปริ้นท์ดูค่า
      printf("ADC: %4d | PWM: %4d | Duty: %d.%d%%\r\n", 
             adc_val, pwm_val, pwm_val / 10, pwm_val % 10);
  }
#### แบบ C: โจทย์ประยุกต์ขั้นสูง! ล็อก Duty Cycle 50% คงที่ แล้วเปลี่ยนความถี่แบบ Real-time (500 Hz ถึง 1.2 kHz)
> 💡 **หัวใจสำคัญ:**  
> - **เปลี่ยนความถี่สดๆ:** ใช้คำสั่ง `__HAL_TIM_SET_AUTORELOAD(&htim1, arr_val);`  
> - **รักษา Duty 50%:** ตั้งค่า Compare ให้เป็นครึ่งหนึ่งของคาบเสมอ: `ccr_val = (arr_val + 1) / 2;`  
> - **สูตรหา ARR (เมื่อใช้ PSC = 83):** $\text{ARR} = \frac{1,000,000}{f} - 1$  
>   - ที่ $500\text{ Hz}$: $\text{ARR} = \frac{1,000,000}{500} - 1 = \mathbf{1999}$ (Compare 50% = 1000)  
>   - ที่ $1,200\text{ Hz}$: $\text{ARR} = \frac{1,000,000}{1,200} - 1 = \mathbf{832}$ (Compare 50% = 416)

```c
  /* USER CODE BEGIN 3 */
  if (HAL_GetTick() - last_time >= 50)
  {
      last_time = HAL_GetTick();

      // 1. อ่านค่า ADC จากวอลลุ่ม (0 - 4095)
      HAL_ADC_Start(&hadc1);
      if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
      {
          adc_val = HAL_ADC_GetValue(&hadc1);
      }
      HAL_ADC_Stop(&hadc1);

      // 2. แปลงค่า ADC (0 - 4095) ไปเป็น ความถี่เป้าหมาย (500 - 1200 Hz)
      float freq_target = 500.0f + ((float)adc_val * 700.0f / 4095.0f);

      // 3. คำนวณค่า ARR และค่า Compare สำหรับ 50% Duty Cycle
      uint16_t arr_val = (uint16_t)(1000000.0f / freq_target) - 1;
      uint16_t ccr_val = (arr_val + 1) / 2; // ล็อก 50% ตลอดเวลา

      // 4. สั่งเปลี่ยนความถี่ (ARR) และ Duty 50% (CCR) แบบ Real-time!
      __HAL_TIM_SET_AUTORELOAD(&htim1, arr_val);
      __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, ccr_val);

      // 5. ปริ้นท์ดูค่าความถี่
      printf("ADC: %4d | Freq: %4.1f Hz | ARR: %4d | Duty: 50.0%%\r\n", 
             adc_val, freq_target, arr_val);
  }
  /* USER CODE END 3 */
```

#### แบบ D: โจทย์จำกัดช่วงยอดฮิต! ปรับ Duty Cycle 20% ถึง 80% แบบ Fix ความถี่ 1,000 Hz
> 💡 **สูตรคำนวณแบบจำนวนเต็ม (Integer Math) - ไม่ใช้ Float เร็ว เสถียร และนิ่งที่สุด:**  
> - ที่ความถี่ 1,000 Hz (PSC = 83 @ 84MHz) $\to \text{ARR} = 999$ (คาบเต็ม 1000 สเต็ป)  
> - ช่วง Duty 20% ถึง 80% คิดเป็นค่า Compare (CCR) ในช่วง **200 ถึง 800** (ระยะกว้าง = $800 - 200 = 600$)  
> - สูตรแปลง ADC (0 - 4095) ตรงไปยังค่า Compare 200 - 800:  
>   `pwm_val = 200 + (uint32_t)adc_val * 600 / 4095;`  
> - ทศนิยมดึงด้วย: ส่วนจำนวนเต็ม = `pwm_val / 10`, ส่วนทศนิยม = `pwm_val % 10` (เช่น 554 $\to$ 55.4%)

```c
  /* USER CODE BEGIN 3 */
  if (HAL_GetTick() - last_time >= 50)
  {
      last_time = HAL_GetTick();

      // 1. อ่านค่า ADC จากตัวต้านทานปรับค่าได้
      HAL_ADC_Start(&hadc1);
      if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
      {
          adc_val = HAL_ADC_GetValue(&hadc1); // อ่านค่า 0 - 4095
      }
      HAL_ADC_Stop(&hadc1);

      // 2. คำนวณเป็น Duty Cycle 200 - 800 (20.0% - 80.0%) แบบจำนวนเต็ม
      pwm_val = 200 + (uint32_t)adc_val * 600 / 4095;

      // 3. สั่งจ่ายค่า Compare ให้หลอดไฟ LED / สโคป (ขา PA8)
      __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);

      // 4. ปริ้นท์ดูค่า
      printf("ADC: %4d | PWM: %4d | Duty: %d.%d%%\r\n", 
             adc_val, pwm_val, pwm_val / 10, pwm_val % 10);
  }
  /* USER CODE END 3 */
```

> ⚠️ **เทคนิคป้องกันคลื่นสะดุด / ความถี่ตกฮวบเวลาหมุนวอลลุ่ม:**  
> ใน `USER CODE BEGIN 2` ก่อนสั่ง `HAL_TIM_PWM_Start` ให้ใส่คำสั่งเปิด Preload เสมอ:  
> `__HAL_TIM_ENABLE_OCxPRELOAD(&htim1, TIM_CHANNEL_1);`  
> เพื่อให้ฮาร์ดแวร์สลับค่า Duty เฉพาะตอนจบรอบ ป้องกันไม่ให้คลื่น PWM ยืดคาบเวลาหรือความถี่แกว่งบน Oscilloscope  
> *(หากใช้งานร่วมกับจอ OLED แนะนำให้ตั้ง I2C Speed เป็น 100 kHz และแยกเวลาอัปเดตจอ OLED เป็นทุกๆ 250 ms ดูรายละเอียดในคู่มือ `OLED_I2C_STM32_Guide.md`)*

---

#### แบบ E: ปรับทั้งความถี่และ Duty Cycle พร้อมกัน (ด้วยวอลลุ่มตัวเดียว)
> 🚨 **หัวใจสำคัญ:** เมื่อ `ARR` เปลี่ยนตามความถี่ ค่า `CCR` **จะต้องถูกคำนวณใหม่ให้สัมพันธ์กับ `ARR` ก้อนใหม่เสมอ**:
> $$\mathbf{CCR} = \frac{(\mathbf{ARR} + 1) \times \text{Duty\_Permille}}{1000}$$

```c
/* USER CODE BEGIN PV */
uint16_t adc_val = 0;
uint32_t freq_val = 500;       // ความถี่ 500 - 2,000 Hz
uint32_t arr_val = 1999;       // ค่า ARR
uint32_t duty_permille = 200;  // ค่า Duty 200 - 800 (คือ 20.0% - 80.0%)
uint32_t pwm_val = 400;        // ค่า CCR สัมพันธ์กับ ARR
uint32_t last_time = 0;
/* USER CODE END PV */

/* USER CODE BEGIN 2 */
__HAL_TIM_ENABLE_OCxPRELOAD(&htim1, TIM_CHANNEL_1);
HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
/* USER CODE END 2 */

/* USER CODE BEGIN 3 */
if (HAL_GetTick() - last_time >= 50)
{
    last_time = HAL_GetTick();

    // 1. อ่าน ADC (0 - 4095)
    HAL_ADC_Start(&hadc1);
    if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
    {
        adc_val = HAL_ADC_GetValue(&hadc1);
    }
    HAL_ADC_Stop(&hadc1);

    // 2. คำนวณความถี่ (500 Hz - 2,000 Hz)
    freq_val = 500 + (uint32_t)adc_val * 1500 / 4095;

    // 3. คำนวณ ARR ที่ PSC = 83 (1 MHz tick)
    arr_val = (1000000 / freq_val) - 1;

    // 4. คำนวณ Duty (20.0% - 80.0%)
    duty_permille = 200 + (uint32_t)adc_val * 600 / 4095;

    // 5. คำนวณ Compare (CCR) ให้สัมพันธ์กับ ARR เสมอ
    pwm_val = ((arr_val + 1) * duty_permille) / 1000;

    // 6. อัปเดตฮาร์ดแวร์ไทเมอร์ทั้งคู่
    __HAL_TIM_SET_AUTORELOAD(&htim1, arr_val);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);

    printf("ADC:%4d | F:%4lu Hz | D:%lu.%lu%% | ARR:%4lu | CCR:%4lu\r\n",
           adc_val, freq_val, duty_permille / 10, duty_permille % 10, arr_val, pwm_val);
}
/* USER CODE END 3 */
```

---

#### แบบ F: วอลลุ่ม 1 ตัว + ปุ่มกดสีฟ้า B1 (PC13) สลับโหมดปรับ Freq หรือ Duty
กดปุ่ม B1 (PC13) สลับโหมด: โหมด 0 ปรับความถี่ (Duty ล็อค) / โหมด 1 ปรับ Duty (ความถี่ล็อค)

```c
/* USER CODE BEGIN PV */
uint16_t adc_val = 0;
uint32_t freq_val = 1000;      // ค่าเริ่มต้น 1,000 Hz
uint32_t arr_val = 999;
uint32_t duty_permille = 500;  // Duty เริ่มต้น 50.0%
uint32_t pwm_val = 500;
uint8_t mode = 0;              // 0 = Freq, 1 = Duty
uint8_t last_btn_state = GPIO_PIN_SET;
uint32_t last_time = 0;
/* USER CODE END PV */

/* USER CODE BEGIN 3 */
// 1. ตรวจจับการกดปุ่ม B1 (PC13) เพื่อสลับโหมด
uint8_t current_btn = HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13);
if (current_btn == GPIO_PIN_RESET && last_btn_state == GPIO_PIN_SET)
{
    mode = !mode; // สลับ 0 <-> 1
    HAL_Delay(50); // กันปุ่มกระดอน
}
last_btn_state = current_btn;

// 2. อ่าน ADC และปรับค่าตามโหมด
if (HAL_GetTick() - last_time >= 50)
{
    last_time = HAL_GetTick();

    HAL_ADC_Start(&hadc1);
    if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
    {
        adc_val = HAL_ADC_GetValue(&hadc1);
    }
    HAL_ADC_Stop(&hadc1);

    if (mode == 0) // ปรับความถี่ (500 Hz ถึง 2,000 Hz)
    {
        freq_val = 500 + (uint32_t)adc_val * 1500 / 4095;
        arr_val = (1000000 / freq_val) - 1;
    }
    else // ปรับ Duty Cycle (10.0% ถึง 90.0%)
    {
        duty_permille = 100 + (uint32_t)adc_val * 800 / 4095;
    }

    // คำนวณ CCR ให้สัมพันธ์กับ ARR เสมอ
    pwm_val = ((arr_val + 1) * duty_permille) / 1000;

    __HAL_TIM_SET_AUTORELOAD(&htim1, arr_val);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);
}
/* USER CODE END 3 */
```

---

### 🧠 สรุปความสัมพันธ์ PSC, ARR และ CCR (เข้าใจง่ายที่สุดสำหรับทำข้อสอบ)

เปรียบเทียบเหมือน **"คนวิ่งในสนามแข่งรูปวงกลม"**:

| ตัวแปร | ย่อมาจาก | เปรียบเหมือน | หน้าที่ในระบบ PWM | สิ่งที่มันควบคุม |
| :---: | :---: | :--- | :--- | :--- |
| **PSC** | **P**re**sc**aler | **"เกียร์ทดความเร็ว"** | ชะลอความเร็วนาฬิกาชิป (84 MHz) ให้ช้าลงตามต้องการ | **ความเร็วในการเดินก้าว** ของตัวนับ |
| **ARR** | **A**uto-**R**eload **R**egister | **"เส้นชัย 1 รอบสนาม"** | กำหนดว่าต้องนับกี่ก้าว ถึงจะครบรอบแล้วกลับไปเริ่ม 0 ใหม่ | **ความถี่ (Frequency)** และความยาวคาบ |
| **CCR** | **C**apture/**C**ompare **R**egister | **"จุดเปิด-ปิดสวิตช์ไฟ"** | กำหนดว่าในรอบนั้น จะให้ไฟเปิดติด (HIGH) นานกี่ก้าวก่อนจะดับ | **Duty Cycle (%)** หรือความสว่าง |

#### 📊 แผนภาพคลื่น PWM ทำงานร่วมกันอย่างไร:
```text
       |<-------------------- 1 คาบเวลา (Period) -------------------->|
       |<------ CCR ------>|
HIGH   |───────────────────┐                                          |
       │ ไฟติด (ON)        │ ไฟดับ (OFF)                              │
LOW    │                   └──────────────────────────────────────────┘
Count: 0                  CCR                                        ARR
       |<──────────────────── ทั้งหมด ARR + 1 ก้าว ────────────────────>|
```

---

### 📐 2 สูตรคณิตศาสตร์หัวใจสำคัญของ PWM:

#### สูตรที่ 1: หา "Duty Cycle (%)" (ขึ้นอยู่กับ CCR และ ARR)
$$\text{Duty Cycle} = \frac{\mathbf{CCR}}{\mathbf{ARR} + 1} \times 100\%$$
> 💡 **ข้อสังเกต:** ความสว่าง/ความกว้างพัลส์ **ไม่เกี่ยวกับ PSC เลย!** เป็นแค่สัดส่วนระหว่าง `CCR` กับ `ARR` เท่านั้น

#### สูตรที่ 2: หา "ความถี่คลื่น PWM" (ขึ้นอยู่กับ PSC และ ARR)
$$f_{\text{PWM}} = \frac{f_{\text{TIM\_CLK}}}{(\mathbf{PSC} + 1) \times (\mathbf{ARR} + 1)}$$
> 💡 **ข้อสังเกต:** ความถี่ของคลื่น **ไม่เกี่ยวกับ CCR เลย!** จะเปลี่ยนความถี่ ต้องไปยุ่งกับ `ARR` หรือ `PSC` เท่านั้น

---

### 📐 สูตรการคำนวณเปลี่ยนความถี่ PWM (มาตรฐาน 84 MHz ของ STM32F410RB)

* **$f_{\text{TIM\_CLK}}$:** สัญญาณนาฬิกาของ Timer ดูจากแท็บ Clock Configuration ช่อง **`APB2 timer clocks` = `84 MHz` (84,000,000 Hz)**
* **$\text{PSC}$ (Prescaler):** ตัวหารความถี่นาฬิกา
* **$\text{ARR}$ (Counter Period):** จำนวนขั้นการนับ (กำหนดความละเอียดของ Duty Cycle เช่น 999 = 1,000 ขั้น)

#### ขั้นตอนการคำนวณหาค่า PSC:
$$\text{PSC} = \frac{84,000,000}{f_{\text{PWM}} \times (\text{ARR} + 1)} - 1$$

#### 🌟 เทคนิคจำง่ายที่สุดสำหรับข้อสอบ (ใช้เลข 83 เป็นหลัก!):
1. **1 kHz (1,000 Hz) - สำหรับหรี่ไฟ LED (ไม่กระพริบ):**
   - ตั้ง $\text{ARR} = 999$ (คือ 1,000 ขั้น)
   - $\text{PSC} = \frac{84,000,000}{1,000 \times 1,000} - 1 = \mathbf{83}$
2. **50 Hz (คาบเวลา 20 ms) - สำหรับเซอร์โวมอเตอร์ (Servo SG90):**
   - ตั้ง $\text{PSC} = \mathbf{83}$ (ความเร็ว Timer เดินก้าวละ $1\,\mu\text{s}$)
   - $\text{ARR} = \frac{1,000,000}{50} - 1 = \mathbf{19999}$
   *(สังเกต: ทั้ง LED และ Servo ใช้ **`PSC = 83`** เลขเดียวกันเลย จำง่ายมาก!)*
3. **20 kHz (20,000 Hz) - สำหรับขับมอเตอร์ DC (ไร้เสียงหวีด):**
   - ตั้ง $\text{ARR} = 1049$
   - $\text{PSC} = \frac{84,000,000}{20,000 \times 1,050} - 1 = 4 - 1 = \mathbf{3}$

---

### 🔍 สาเหตุที่ "ไฟ LED สว่างไม่ถึงครึ่ง / สว่างไม่สุด" และจุดที่ต้องตรวจเช็ค:

1. **เช็คตัวเลขใน Terminal/SWV ก่อน:**
   - ตอนหมุนสุด ค่า `ADC` ขึ้นถึง **4000+** และ `PWM` ขึ้นถึง **900 - 1000** หรือไม่?
   - ถ้าในคอมฯ ค่า ADC ขึ้นสูงสุดแค่ **~2000**: แสดงว่า **ต่อขาวอลลุ่มผิด** (เช่น นำขากลางไปต่อ 3.3V หรือไฟเลี้ยงวอลลุ่มมาไม่ถึง 3.3V)
2. **เช็คขาที่ต่อหลอด LED:**
   - สัญญาณ PWM ของ `TIM1_CH1` ออกที่ขา **`PA8` (ขา D7 บนบอร์ด Nucleo)** ไม่ใช่ขา `PA5` (เพราะ `PA5` เป็นไฟ LED เขียวบนบอร์ดที่ไม่มี Timer PWM)
3. **เช็คค่าตัวต้านทาน (Resistor) ของหลอด LED:**
   - ต้องใช้ตัวต้านทานค่า **`220 Ω` ถึง `330 Ω`** (หรือสูงสุดไม่เกิน `1 kΩ`)
   - ถ้าเผลอไปใช้ตัวต้านทานค่าสูง เช่น **`10 kΩ` หรือ `4.7 kΩ`** กระแสจะไหลน้อยมาก ทำให้ไฟริบหรี่และดูเหมือนสว่างไม่ถึงครึ่ง แม้ Duty จะเป็น 100% แล้วก็ตาม
4. **สายตามนุษย์ตอบสนองแสงแบบไม่เป็นเส้นตรง (Non-linear Perception):**
   - ตาคนเรารับรู้ความสว่างแบบ Logarithmic ช่วง Duty `0% - 20%` จะเห็นความสว่างเพิ่มขึ้นเร็วมาก แต่ช่วง `50% - 100%` ตาเราจะแทบแยกไม่ออกว่าสว่างขึ้น เพราะม่านตาหรี่ลงโดยอัตโนมัติ

---

## 6. การจับเวลาแบบไม่หยุดค้างการทำงาน (Non-blocking Delay ด้วย HAL_GetTick)

> 💡 **ทำไมข้อสอบมักห้ามใช้ `HAL_Delay()`?**  
> เพราะ `HAL_Delay(1000)` จะทำให้ซีพียูหยุดนิ่งทั้งระบบ 1 วินาทีเต็ม ระหว่างนั้นจะไม่สามารถรับส่งข้อมูล UART, ไม่สามารถตรวจจับการกดปุ่มได้ทันที หรือจอ OLED จะค้าง  
> จึงต้องใช้ **`HAL_GetTick()`** (ทำงานเหมือน `millis()` ใน Arduino)

### คอนเซปต์:
`HAL_GetTick()` คืนค่าเป็นตัวเลขมิลลิวินาที (ms) ตั้งแต่เปิดเครื่อง โดยอัปเดตอัตโนมัติจาก SysTick ทุก 1 ms

### 1) ประกาศตัวแปรเก็บเวลาใน `USER CODE BEGIN PV`:
```c
/* USER CODE BEGIN PV */
uint32_t prev_tick = 0; // ตัวแปรเก็บเวลาครั้งก่อนหน้า
/* USER CODE END PV */
```

### 2) โครงสร้างคำสั่งใน `USER CODE BEGIN 3` (ใน while loop):
```c
  /* USER CODE BEGIN 3 */
  // ตรวจสอบว่าเวลาผ่านไปครบ 500 ms หรือยัง
  if (HAL_GetTick() - prev_tick >= 500)
  {
      prev_tick = HAL_GetTick(); // อัปเดตเวลาล่าสุด
      
      // คำสั่งที่ต้องการให้ทำงานทุกๆ 500 ms (เช่น ไฟกระพริบ หรือ อ่าน ADC)
      HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);
  }

  // --- โค้ดส่วนอื่นยังคงทำงานได้ทันที โดยไม่ต้องรอ 500 ms! ---
  // ตัวอย่างเช่น การตรวจจับปุ่มกดจะตอบสนองได้ทันที ไม่หน่วง
  if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) == GPIO_PIN_RESET)
  {
      // สั่งงานทันทีเมื่อกดปุ่ม
  }
  /* USER CODE END 3 */
```

---

## 📊 ตารางสรุป Cheat Sheet รวดเร็วก่อนสอบ

| ฟังก์ชัน | ตัวแปร/คำสั่งหลัก | วางที่ `main.c` |
| :--- | :--- | :--- |
| **Digital Out** | `HAL_GPIO_WritePin(GPIOx, PIN, SET/RESET);`<br>`HAL_GPIO_TogglePin(GPIOx, PIN);` | `USER CODE BEGIN 3` |
| **Digital In (พื้นฐาน)** | `HAL_GPIO_ReadPin(GPIOx, PIN) == GPIO_PIN_SET` | `USER CODE BEGIN 3` |
| **Button Toggle (Edge)** | `if (curr == RESET && last == SET) { Toggle(); count++; Delay(20); } last = curr;` | ตัวแปร: `USER CODE BEGIN PV`<br>ตรวจจับ: `USER CODE BEGIN 3` |
| **Analog In (ADC)** | `HAL_ADC_Start(&hadc1);`<br>`HAL_ADC_PollForConversion(&hadc1, timeout);`<br>`val = HAL_ADC_GetValue(&hadc1);`<br>`HAL_ADC_Stop(&hadc1);` | ตัวแปร: `USER CODE BEGIN PV`<br>อ่านค่า: `USER CODE BEGIN 3` |
| **Analog Out (DAC)**| `HAL_DAC_Start(&hdac, DAC_CHANNEL_1);`<br>`HAL_DAC_SetValue(&hdac, DAC_CHANNEL_1, DAC_ALIGN_12B_R, val);` | Start: `USER CODE BEGIN 2`<br>Set: `USER CODE BEGIN 3` |
| **Output PWM (ปรับ Duty)** | `HAL_TIM_PWM_Start(&htimx, TIM_CHANNEL_x);`<br>`__HAL_TIM_SET_COMPARE(&htimx, TIM_CHANNEL_x, duty);` | Start: `USER CODE BEGIN 2`<br>Set: `USER CODE BEGIN 3` |
| **Change PWM Freq (สดๆ)** | `__HAL_TIM_SET_AUTORELOAD(&htimx, arr);`<br>`__HAL_TIM_SET_COMPARE(&htimx, ch, (arr+1)/2);` | `USER CODE BEGIN 3` |
| **Non-blocking Timer** | `if (HAL_GetTick() - prev_tick >= INTERVAL) { prev_tick = HAL_GetTick(); ... }` | ตัวแปร: `USER CODE BEGIN PV`<br>เงื่อนไข: `USER CODE BEGIN 3` |


