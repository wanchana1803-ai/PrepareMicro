# คู่มือสรุปการคำนวณและสูตรข้อสอบแล็ปไมโครคอนโทรลเลอร์ (STM32F410RB)
### เอกสารเตรียมสอบฉบับสมบูรณ์: เน้นการคำนวณคณิตศาสตร์ทางวิศวกรรมและการแก้ปัญหาจริง

---

## สารบัญเนื้อหา (Table of Contents)
* [บทที่ 1: ระบบสัญญาณนาฬิกาและฐานเวลา Timer (Clock Tree & Timebase)](#บทที่-1-ระบบสัญญาณนาฬิกาและฐานเวลา-timer)
* [บทที่ 2: คณิตศาสตร์ของคลื่น PWM ทุกรูปแบบ (PWM Mathematics Masterclass)](#บทที่-2-คณิตศาสตร์ของคลื่น-pwm-ทุกรูปแบบ)
  * [2.1 โครงสร้างความสัมพันธ์ PSC, ARR, CCR](#21-โครงสร้างความสัมพันธ์-psc-arr-ccr)
  * [2.2 สูตรหาความถี่และการเซ็ตค่า Prescaler](#22-สูตรหาความถี่และการเซ็ตค่า-prescaler)
  * [2.3 การคำนวณ Duty Cycle แบบจำนวนเต็ม (Integer Math) ไม่พึ่งพา Float](#23-การคำนวณ-duty-cycle-แบบจำนวนเต็ม-integer-math)
  * [2.4 สูตรการสเกลค่ากลับทิศทาง (Inverted Mapping Formula)](#24-สูตรการสเกลค่ากลับทิศทาง-inverted-mapping)
  * [2.5 การควบคุม Frequency และ Duty Cycle พร้อมกัน (Dynamic ARR-CCR Scaling)](#25-การควบคุม-frequency-และ-duty-cycle-พร้อมกัน)
  * [2.6 ทฤษฎี Preload Glitch: ทำไมความถี่ถึงวูบเหลือ 500 Hz บนสโคป?](#26-ทฤษฎี-preload-glitch)
* [บทที่ 3: ระบบแปลงสัญญาณอนาล็อก ADC (ADC Resolution & Voltage Math)](#บทที่-3-ระบบแปลงสัญญาณอนาล็อก-adc)
* [บทที่ 4: การสื่อสาร I2C, จอ OLED และการวิเคราะห์สัญญาณรบกวน 18 kHz](#บทที่-4-การสื่อสาร-i2c-และสัญญาณรบกวน-18-khz)
* [บทที่ 5: การจัดสรรเวลาแบบ Non-blocking (Time Slicing Math)](#บทที่-5-การจัดสรรเวลาแบบ-non-blocking)
* [บทที่ 6: การสื่อสาร UART และ Python GUI (Baud Rate & Data Throughput)](#บทที่-6-การสื่อสาร-uart-และ-python-gui)
* [บทที่ 7: สรุปตัวเลขทองคำ Cheat Sheet เข้าห้องสอบทันที](#บทที่-7-สรุปตัวเลขทองคำ-cheat-sheet-เข้าห้องสอบ)

---

## บทที่ 1: ระบบสัญญาณนาฬิกาและฐานเวลา Timer

ไมโครคอนโทรลเลอร์ **STM32F410RB (Nucleo-64)** มีสถาปัตยกรรม Clock Tree สูงสุดที่ **$84\text{ MHz}$**:

```text
  [ HSI / HSE ] ──> [ PLL Multiplier ] ──> SYSCLK (84 MHz)
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
         AHB Bus (84 MHz)                                              AHB Bus (84 MHz)
                 │                                                             │
        APB1 Prescaler (/2)                                           APB2 Prescaler (/1)
                 │                                                             │
         APB1 Peripheral (42 MHz)                                      APB2 Peripheral (84 MHz)
                 │                                                             │
      APB1 Timer Clock (x2 = 84 MHz)                                APB2 Timer Clock (x1 = 84 MHz)
        [ TIM5, TIM6 ]                                                [ TIM1, TIM9, TIM11 ]
```

### กฎการคำนวณความถี่ตัวนับของ Timer (Timer Tick Frequency):
ความถี่ที่ป้อนเข้าตัวนับของไทเมอร์ ($f_{\text{CNT}}$) คำนวณจาก:
$$f_{\text{CNT}} = \frac{f_{\text{TIM\_CLK}}}{\mathbf{PSC} + 1}$$

* ใน STM32F410RB: $f_{\text{TIM\_CLK}} = 84,000,000\text{ Hz}$ ($84\text{ MHz}$)
* เพื่อให้ตัวนับนับก้าวละ **$1\,\mu\text{s}$ พอดี** ($1,000,000\text{ Hz}$):
  $$\text{PSC} = \frac{84,000,000}{1,000,000} - 1 = 84 - 1 = \mathbf{83}$$
* **ตัวเลขทองคำ:** หากตั้ง $\mathbf{PSC = 83}$ ใน CubeMX ทุกๆ 1 ก้าวของไทเมอร์จะมีคาบเวลาเท่ากับ **$1\,\mu\text{s}$ พอดีเป๊ะ** ทำให้คำนวณความถี่และคาบเวลาในห้องสอบได้ง่ายที่สุด

---

## บทที่ 2: คณิตศาสตร์ของคลื่น PWM ทุกรูปแบบ

### 2.1 โครงสร้างความสัมพันธ์ PSC, ARR, CCR

```text
         |<────────────────── คาบเวลา (Period) ──────────────────>|
         |<────── CCR ──────>|
  HIGH   |───────────────────┐                                    │
         │ ไฟติด (ON)        │ ไฟดับ (OFF)                        │
  LOW    │                   └────────────────────────────────────┘
  Count: 0                  CCR                                  ARR
         |<────────────────── ทั้งหมด ARR + 1 ก้าว ──────────────>|
```

1. **PSC (Prescaler):** ควบคุม **"ความเร็วการเดินก้าว"**
2. **ARR (Auto-Reload Register):** ควบคุม **"จำนวนก้าวต่อ 1 รอบ"** $\implies$ **กำหนดความถี่ (Frequency)**
3. **CCR (Capture/Compare Register):** ควบคุม **"จุดตัดสถานะ"** $\implies$ **กำหนด Duty Cycle (%)**

---

### 2.2 สูตรหาความถี่และการเซ็ตค่า Prescaler

ความถี่ของคลื่นเอาต์พุต ($f_{\text{PWM}}$) คำนวณจาก:
$$f_{\text{PWM}} = \frac{f_{\text{TIM\_CLK}}}{(\mathbf{PSC} + 1) \times (\mathbf{ARR} + 1)}$$

เมื่อเราฟิกซ์ความเร็วฐานเวลาไว้ที่ **$\text{PSC} = 83$** ($f_{\text{CNT}} = 1\text{ MHz}$):
$$\mathbf{ARR} = \frac{1,000,000}{f_{\text{PWM}}} - 1$$

#### ตารางค่าคำนวณความถี่มาตรฐาน:
| ความถี่ที่ต้องการ ($f_{\text{PWM}}$) | วัตถุประสงค์การใช้งาน | PSC | ARR คำนวณ | ค่า ARR ที่กรอก | คาบเวลา ($T$) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1,000 Hz (1 kHz)** | หรี่ไฟ LED / ทดสอบทั่วไป | 83 | $\frac{1,000,000}{1,000} - 1$ | **`999`** | $1.0\text{ ms}$ |
| **500 Hz** | มอเตอร์ขนาดเล็ก / Buzzer | 83 | $\frac{1,000,000}{500} - 1$ | **`1999`** | $2.0\text{ ms}$ |
| **2,000 Hz (2 kHz)** | ลำโพงโทนสูง | 83 | $\frac{1,000,000}{2,000} - 1$ | **`499`** | $0.5\text{ ms}$ |
| **50 Hz** | เซอร์โวมอเตอร์ (RC Servo SG90) | 83 | $\frac{1,000,000}{50} - 1$ | **`19999`** | $20.0\text{ ms}$ |
| **20,000 Hz (20 kHz)** | มอเตอร์ DC ไร้เสียงหวีด | 3 | $\frac{84,000,000}{20,000 \times 1,050} - 1$ | **`1049`** | $50.0\,\mu\text{s}$ |

---

### 2.3 การคำนวณ Duty Cycle แบบจำนวนเต็ม (Integer Math)

ในระบบไมโครคอนโทรลเลอร์ การใช้ตัวแปร `float` หรือ `double` กินเวลาประมวลผลสูง (หลายสิบ clock cycle) และทำให้ขนาดไฟล์ Flash บวม รวมถึงฟังก์ชัน `sprintf` บน CubeIDE ปิด `%f` ไว้เป็นค่าเริ่มต้น

#### การพิสูจน์สูตรแปลง ADC (0 - 4095) $\to$ Duty Cycle 20.0% ถึง 80.0%:
* กำหนดให้ความถี่คงที่ $1\text{ kHz}$ ($\text{ARR} = 999 \implies \text{ก้าวทั้งหมด} = 1,000\text{ ก้าว}$)
* Duty 20.0% คิดเป็นค่า $\text{CCR}_{\min} = 1,000 \times 0.20 = \mathbf{200}$
* Duty 80.0% คิดเป็นค่า $\text{CCR}_{\max} = 1,000 \times 0.80 = \mathbf{800}$
* ช่วงกว้างของการปรับค่า ($\text{Span}$) $= 800 - 200 = \mathbf{600}$

สมการเชิงเส้นทั่วไป:
$$\text{Output} = \text{Offset} + \frac{\text{Input} \times \text{Span}}{\text{Input Range}}$$

แทนค่าตัวเลขฮาร์ดแวร์จริง:
$$\mathbf{pwm\_val} = 200 + \frac{\mathbf{adc\_val} \times 600}{4095}$$

```c
// คำนวณแบบ 32-bit Integer Math (ป้องกัน Overflow ในจังหวะคูณ)
pwm_val = 200 + (uint32_t)adc_val * 600 / 4095;
__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);
```

#### การแยกแสดงผลทศนิยม 1 ตำแหน่งโดยไม่ใช้ Float:
* ส่วนจำนวนเต็ม: `pwm_val / 10`
* ส่วนทศนิยม: `pwm_val % 10`
* เช่น `pwm_val = 554` $\implies 554 / 10 = \mathbf{55}$, $554 \% 10 = \mathbf{4} \implies \mathbf{55.4\%}$

---

### 2.4 สูตรการสเกลค่ากลับทิศทาง (Inverted Mapping)

ในข้อสอบมักเจอกรณี: *"เมื่อหมุนวอลลุ่มตามเข็มนาฬิกา ค่าความถี่ต้องลดลงจาก 2,000 Hz เหลือ 500 Hz"*

#### กฎตายตัวสำหรับการกลับทิศทาง:
$$\text{Output} = \mathbf{ค่าสูงสุด} - \frac{\mathbf{adc\_val} \times \text{Span}}{4095}$$

1. **ความถี่ 2,000 Hz ลดลงเหลือ 500 Hz** ($\text{Span} = 2000 - 500 = 1500$):
   $$\mathbf{freq\_val} = 2000 - \frac{\mathbf{adc\_val} \times 1500}{4095}$$
   * ตรวจสอบที่ $\text{ADC} = 0$: $2000 - 0 = \mathbf{2,000\text{ Hz}}$
   * ตรวจสอบที่ $\text{ADC} = 4095$: $2000 - 1500 = \mathbf{500\text{ Hz}}$

2. **Duty Cycle 80.0% ลดลงเหลือ 20.0%** ($\text{Span} = 800 - 200 = 600$):
   $$\mathbf{duty\_permille} = 800 - \frac{\mathbf{adc\_val} \times 600}{4095}$$

---

### 2.5 การควบคุม Frequency และ Duty Cycle พร้อมกัน

> 🚨 **หลุมพรางข้อสอบ:** เมื่อเปลี่ยนความถี่ ค่า `ARR` จะเปลี่ยนไป แต่ถ้าเราส่งค่า `CCR` เดิมออกไป ค่าเปอร์เซ็นต์ Duty Cycle จริงจะเพี้ยนทันที!

#### การพิสูจน์:
สมมติ $\text{CCR} = 400$:
* ที่ $1\text{ kHz}$ ($\text{ARR} = 999$): $\text{Duty} = \frac{400}{1000} = \mathbf{40\%}$
* หากเปลี่ยนเป็น $500\text{ Hz}$ ($\text{ARR} = 1999$): $\text{Duty} = \frac{400}{2000} = \mathbf{20\%}$ (เพี้ยนลงครึ่งหนึ่ง!)

#### สูตรคำนวณผูกความสัมพันธ์ (Dynamic ARR-CCR Rescaling):
$$\mathbf{CCR} = \frac{(\mathbf{ARR} + 1) \times \text{Duty\_Permille}}{1000}$$

```c
// 1. คำนวณความถี่ (500 Hz ถึง 2,000 Hz)
freq_val = 500 + (uint32_t)adc_val * 1500 / 4095;
arr_val = (1000000 / freq_val) - 1;

// 2. คำนวณ Duty เป้าหมาย (20.0% ถึง 80.0%)
duty_permille = 200 + (uint32_t)adc_val * 600 / 4095;

// 3. สเกลค่า CCR ให้สัมพันธ์กับ ARR ตัวใหม่เสมอ
pwm_val = ((arr_val + 1) * duty_permille) / 1000;

// 4. บันทึกลงรีจิสเตอร์ฮาร์ดแวร์
__HAL_TIM_SET_AUTORELOAD(&htim1, arr_val);
__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pwm_val);
```

---

### 2.6 ทฤษฎี Preload Glitch: ทำไมความถี่ถึงวูบเหลือ 500 Hz?

เมื่อเขียนค่าลงรีจิสเตอร์เปรียบเทียบ `CCR1` โดยไม่เปิด **Output Compare Preload (`OC1PE = 0`)**:
* ค่าในรีจิสเตอร์จะเปลี่ยนทันทีกลางรอบ
* หากตัวนับ `CNT` ในรอบนั้นวิ่งเลยค่าเปรียบเทียบใหม่ไปแล้ว ตัวเปรียบเทียบฮาร์ดแวร์จะไม่เกิดเหตุการณ์ Match
* สัญญาณเอาต์พุตจะ **ค้างสถานะ HIGH ตลอดทั้งรอบจนจบ 1,000 ก้าว แล้วต้องเริ่มนับใหม่อีก 1 รอบ**
* ส่งผลให้คาบเวลาพัลส์รอบนั้นยาวเป็น **$2.0\text{ ms}$ (ความถี่ตกลงเหลือ $500\text{ Hz}$ ทันที)**

```text
[ไม่มี Preload]:  CNT: 0 ... 500 ──(เขียน CCR=200 กะทันหัน)──> ข้าม Match! ค้าง HIGH จนครบ 1000 + อีก 1 รอบ = 2 ms
[เปิด Preload]:   เขียนค่าใหม่ ──> พักไว้ใน Shadow Register ──> อัปเดตพร้อมกันที่จุด UEV (CNT=0) ──> คาบ 1 ms นิ่ง 100%
```

#### คำสั่งแก้ปัญหาในโค้ด:
```c
__HAL_TIM_ENABLE_OCxPRELOAD(&htim1, TIM_CHANNEL_1);
```

---

## บทที่ 3: ระบบแปลงสัญญาณอนาล็อก ADC

ไมโครคอนโทรลเลอร์ STM32F410RB มีวงจรแปลงสัญญาณ ADC แบบ Successive Approximation ขนาด **12-bit**:

### 1. การคำนวณขั้นต่ำสุด (Resolution & LSB):
* จำนวนขั้นทั้งหมด: $2^{12} = 4,096$ ระดับ (ค่าดิจิทัลคือ $0$ ถึง $4095$)
* แรงดันอ้างอิง ($V_{\text{REF}}$): $3.30\text{ V}$
* ขนาดของ 1 LSB:
  $$1\text{ LSB} = \frac{V_{\text{REF}}}{2^{12} - 1} = \frac{3.30\text{ V}}{4095} \approx \mathbf{0.8058\text{ mV}}$$

### 2. สูตรแปลงค่าดิจิทัลกลับเป็นแรงดันจริง ($V_{\text{in}}$):
$$V_{\text{in}} = \frac{\text{ADC\_Value} \times 3.30}{4095}\text{ V}$$

---

## บทที่ 4: การสื่อสาร I2C และสัญญาณรบกวน 18 kHz

### 1. การคำนวณเวลาส่งข้อมูลจอ OLED ($128 \times 64$ พิกเซล):
* ขนาดหน่วยความจำภาพ (Display Buffer):
  $$\text{Buffer Size} = \frac{128 \times 64}{8} = \mathbf{1,024\text{ Bytes}}$$
* ปริมาณข้อมูลรวมเมื่อส่งคำสั่งเลือกหน้า (8 Pages $\times$ 3 Command Bytes) $= 1,024 + 24 = \mathbf{1,048\text{ Bytes}}$
* ในระบบ I2C: 1 ไบต์ใช้ 9 บิตสัญญาณนาฬิกา (8 บิตข้อมูล + 1 บิต ACK):
  $$\text{Total Bits} = 1,048 \times 9 \approx \mathbf{9,432\text{ Clocks}}$$

#### เปรียบเทียบความเร็ว I2C:
* **Fast Mode ($400\text{ kHz}$):**
  $$T_{\text{transfer}} = \frac{9,432}{400,000} \approx \mathbf{23.6\text{ ms}}$$
* **Standard Mode ($100\text{ kHz}$):**
  $$T_{\text{transfer}} = \frac{9,432}{100,000} \approx \mathbf{94.3\text{ ms}}$$

---

### 2. การวิเคราะห์สาเหตุความถี่ 18 kHz บน Oscilloscope

เมื่อเชื่อมต่อจอ OLED ร่วมกับวงจร PWM ทำไม Oscilloscope วัดความถี่ได้ **18 kHz**:

```text
[ชิป SSD1306 / SH1106]
 3.3V Input ──> [ Internal DC-DC Charge Pump ] ──> 7.5V OLED Panel
                      │
                      └──> สร้าง Switching Ripple ความถี่ ~18 kHz (~50mV)
                             เกาะอยู่บนยอดคลื่น 3.3V HIGH ของขา PWM PA8
```

1. จอ OLED ต้องใช้ไฟ $7.5\text{V} - 9\text{V}$ ขับหน้าจอ จึงมีวงจร Charge Pump ในตัวสวิตชิ่งที่ความถี่ **$\approx 18\text{ kHz}$**
2. ระลอกคลื่น $18\text{ kHz}$ รั่วไหลเข้าสู่บัสไฟเลี้ยงร่วมและกราวด์
3. **ระบบ Auto-Measure ของสโคป:** หากตั้งเส้น Trigger Level อยู่สูงใกล้ $3.0\text{V}$ ตัวนับของสโคปจะนับระลอกคลื่น $18\text{ kHz}$ บนยอดคลื่นแทนที่จะนับคลื่น $1\text{ kHz}$

#### การตั้งค่า Oscilloscope ที่ถูกต้อง:
* ตั้ง **Trigger Level = 1.50 V** (กึ่งกลางความสูงสัญญาณเสมอ)
* ตั้ง **Trigger Slope = Rising Edge ↗ (ขอบขาขึ้น)**
* เปิด **Noise Reject = ON** หรือ **HF Reject = ON**
* ตั้งสวิตช์โพรบเป็น **10X** เพื่อลดสัญญาณรบกวนรอบข้าง

---

## บทที่ 5: การจัดสรรเวลาแบบ Non-blocking

ในงานสมองกลฝังตัวระดับมืออาชีพ **ห้ามใช้ `HAL_Delay()` ในลูปหลักเด็ดขาด** เพราะจะทำให้ CPU ถูกบล็อก ไม่สามารถรับส่ง Serial หรือกดปุ่มได้ทันที

### การแบ่งแถบเวลาทำงาน (Time Slicing):
```text
Time (ms): 0    50   100   150   200   250   300   350   400   450   500
ADC/PWM:   |────|────|─────|─────|─────|─────|─────|─────|─────|─────|  (ทุก 50 ms)
OLED:      |───────────────────────────|───────────────────────────|  (ทุก 250 ms)
UART:      |─────────|───────────|───────────|───────────|─────────|  (ทุก 100 ms)
```

```c
// ตัวอย่างโครงสร้าง Non-blocking ใน while(1)
if (HAL_GetTick() - last_adc_time >= 50)
{
    last_adc_time = HAL_GetTick();
    // อ่าน ADC และคำนวณ PWM ไวๆ
}

if (HAL_GetTick() - last_oled_time >= 250)
{
    last_oled_time = HAL_GetTick();
    // ส่งข้อมูลขึ้นจอ OLED (ลดภาระบัส I2C ลง 80%)
}
```

---

## บทที่ 6: การสื่อสาร UART และ Python GUI

### 1. การคำนวณ Throughput และเวลาส่งข้อมูลทาง Serial:
ที่ความเร็ว **$115,200\text{ bps}$** (กรอบ 8N1: 1 Start + 8 Data + 1 Stop $= 10\text{ บิต/ไบต์}$):
$$\text{Max Throughput} = \frac{115,200}{10} = \mathbf{11,520\text{ Bytes/sec}}$$
$$\text{Time per Byte} = \frac{10}{115,200} \approx \mathbf{86.8\,\mu\text{s}}$$

* ข้อความส่งกลับคอมพิวเตอร์: `"ADC:4095 | Duty:80.0%\r\n"` (ความยาว 24 ตัวอักษร)
  $$T_{\text{transmit}} = 24 \times 86.8\,\mu\text{s} \approx \mathbf{2.08\text{ ms}}$$

---

### 2. ทางแก้ปัญหา Packet Spam และเลขตกหล่น (Slider Optimization):
* **ปัญหา:** การลาก Slider ใน Tkinter จะกระตุ้น Callback ทุกพิกเซลการเคลื่อนที่ (มากกว่า 100 ครั้ง/วินาที) ทำให้ UART Buffer ล้น
* **ทางแก้ใน Python:** ใช้ระบบ Rate Limiting (60 ms) + ผูกเหตุการณ์ปล่อยเมาส์ `<ButtonRelease-1>`:
```python
def on_slider_change(self, val):
    now = time.time()
    if now - self.last_slider_time >= 0.06: # ส่งไม่เกินทุก 60 ms
        self.last_slider_time = now
        self.send_command(f"A{val}")

def send_slider_final(self):
    val = self.slider_pwm.get()
    self.send_command(f"A{val}") # การันตีส่งค่าสุดท้าย 4095 แน่นอน
```

* **ทางแก้ใน STM32:** ดึงข้อมูลด้วย `while (RXNE)` เพื่อกวาดอ่านข้อมูลจนเกลี้ยงบัฟเฟอร์ และตรวจจับตัวจบด้วย `\n` ตัวเดียว:
```c
if (__HAL_UART_GET_FLAG(&huart2, UART_FLAG_ORE)) __HAL_UART_CLEAR_OREFLAG(&huart2);

while (__HAL_UART_GET_FLAG(&huart2, UART_FLAG_RXNE))
{
    rx_byte = (uint8_t)(huart2.Instance->DR & 0xFF);
    if (rx_byte == '\n')
    {
        rx_buf[rx_idx] = '\0';
        if (rx_buf[0] == 'A') adc_val = atoi(&rx_buf[1]);
        rx_idx = 0;
    }
    else if (rx_byte != '\r' && rx_idx < sizeof(rx_buf) - 1)
    {
        rx_buf[rx_idx++] = rx_byte;
    }
}
```

---

## บทที่ 7: สรุปตัวเลขทองคำ Cheat Sheet เข้าห้องสอบ

| พารามิเตอร์ | ตัวเลขในห้องสอบ | ความหมาย / สูตร |
| :--- | :---: | :--- |
| **System Clock ($f_{\text{SYS}}$)** | **`84 MHz`** | สัญญาณนาฬิกาสูงสุดของ STM32F410RB |
| **Timer Prescaler ($\text{PSC}$)** | **`83`** | ความเร็ว Timer เดินก้าวละ $1.0\,\mu\text{s}$ พอดี ($1\text{ MHz}$) |
| **ARR สำหรับ 1 kHz** | **`999`** | คาบเวลา $1\text{ ms}$ ($1,000$ ขั้นคำนวณ Duty ละเอียด 0.1%) |
| **ARR สำหรับ 500 Hz** | **`1999`** | คาบเวลา $2\text{ ms}$ |
| **ARR สำหรับ 2 kHz** | **`499`** | คาบเวลา $0.5\text{ ms}$ |
| **Duty 20% ถึง 80% (ที่ 1 kHz)**| `200 + adc * 600 / 4095` | ช่วง Compare อยู่ที่ 200 ถึง 800 |
| **Duty 80% ถึง 20% (กลับทิศ)** | `800 - adc * 600 / 4095` | ค่าลดลงเมื่อหมุนตามเข็มนาฬิกา |
| **Freq 500 ถึง 2,000 Hz** | `500 + adc * 1500 / 4095` | นำค่าไปคำนวณ $\text{ARR} = (1000000 / \text{freq}) - 1$ |
| **Dynamic CCR Rescaling** | `((arr + 1) * duty) / 1000`| สเกล Duty ให้อัตโนมัติเมื่อ ARR เปลี่ยน |
| **I2C Speed แนะนำ** | **`100000` (100 kHz)** | Standard Mode ลดสัญญาณรบกวนความถี่สูง |
| **Scope Trigger Level** | **`1.5 V` (Rising Edge)** | ล็อคกึ่งกลางคลื่น ตัดระลอกคลื่น 18 kHz ทิ้ง |
| **UART Baud Rate** | **`115200`** | ค่ามาตรฐานสื่อสารเร็ว 8.68 µs ต่อบิต |
