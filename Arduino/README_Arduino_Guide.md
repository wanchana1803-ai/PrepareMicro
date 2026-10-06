# 📙 Arduino Motor PWM Control & OLED Telemetry — Complete Guide

คู่มือการใช้งานและโครงงานฉบับสมบูรณ์สำหรับ **Arduino (Uno, Nano, Mega)** และ **STM32duino (Nucleo-64 ผ่าน Arduino IDE)**  
รวบรวมโค้ดและวิธีการแปลงระบบจาก STM32 เดิมมาทำงานบนแพลตฟอร์ม **Arduino IDE** โดยสมบูรณ์ 100%

---

## 📁 1. โครงสร้างโฟลเดอร์โปรเจกต์ Arduino

```text
PrepareMicro/
└── Arduino/
    ├── README_Arduino_Guide.md            <- คู่มือฉบับนี้
    ├── Arduino_OLED_Mode1_Duty/
    │   └── Arduino_OLED_Mode1_Duty.ino    <- แบบที่ 1: หมุน VR คุม Duty 0-100% (1,000 Hz) แสดงผลบน OLED
    ├── Arduino_OLED_Mode2_Dual/
    │   └── Arduino_OLED_Mode2_Dual.ino    <- แบบที่ 2: หมุน VR เดี่ยวคุมคู่ Freq 500-1200Hz + Duty 20-80%
    └── Arduino_GUI_Telemetry/
        └── Arduino_GUI_Telemetry.ino      <- แบบที่ 3: Universal Firmware เชื่อมต่อ Python GUI (pwmMotor.py)
```

---

## 🔌 2. ตารางการต่อสายวงจร (Hardware Pinout)

### สำหรับบอร์ด Arduino Uno / Nano (ATmega328P 5V):

| อุปกรณ์ | ขาบน Arduino Uno/Nano | หน้าที่การทำงาน | หมายเหตุ |
| :--- | :--- | :--- | :--- |
| **Potentiometer (VR)** | **A2** | ขากลางของ VR (Analog In 0 - 5V) | อ่านค่า 10-bit ($0 - 1023$) |
| | **5V** | ขาขวาของ VR | ไฟบวก |
| | **GND** | ขาซ้ายของ VR | กราวด์ |
| **I2C OLED 128x64** | **A4** (SDA) | ขาข้อมูล Data | เชื่อมต่อเข้าขา SDA ของจอ OLED |
| | **A5** (SCL) | ขาสัญญาณนาฬิกา Clock | เชื่อมต่อเข้าขา SCL ของจอ OLED |
| | **5V** หรือ **3.3V** | ไฟเลี้ยงจอ VCC | หน้าจอรองรับ 3.3V - 5V |
| | **GND** | กราวด์ร่วม | กราวด์ |
| **Motor Driver (PWM)** | **Pin 9** (OC1A) | สัญญาณ PWM ขับมอเตอร์ | ขับเคลื่อนด้วย Hardware Timer 1 16-bit |
| **Motor Encoder** | **Pin 2** (INT0) | สัญญาณ Encoder Phase A | รองรับ Hardware External Interrupt |
| | **Pin 3** | สัญญาณ Encoder Phase B | อ่านสถานะทิศทาง CW / CCW |

---

## 📦 3. ไลบรารีที่จำเป็นใน Arduino IDE

ก่อนคอมไพล์ ให้เปิด **Arduino IDE** แล้วไปที่เมนู **Tools -> Manage Libraries...** (หรือกด `Ctrl + Shift + I`) แล้วพิมพ์ค้นหาและกด **Install**:

1. **`Adafruit SSD1306`** (by Adafruit) — ไลบรารีควบคุมจอ OLED 128x64 I2C
2. **`Adafruit GFX Library`** (by Adafruit) — ไลบรารีกราฟิกพื้นฐาน (ระบบจะถามให้ติดตั้งอัตโนมัติ)

---

## ⚙️ 4. เทคนิคเบื้องหลัง: Hardware 16-bit Fast PWM บน Arduino

บน Arduino Uno ปกติ ฟังก์ชัน `analogWrite()` จะสร้างความถี่ได้เพียง ~490 Hz หรือ ~980 Hz ซึ่งไม่ตรงกับสเปกข้อสอบ (1,000 Hz และ 500–1,200 Hz)

ในโค้ดชุดนี้จึงใช้ **Timer 1 (16-bit Hardware Timer)** ในโหมด **Fast PWM Mode 14** (ใช้รีจิสเตอร์ `ICR1` กำหนดความถี่ และ `OCR1A` กำหนด Duty Cycle) ทำให้ได้ความถี่แม่นยำระดับฮาร์ดแวร์ ปราศจากความคลาดเคลื่อน:

### สูตรการคำนวณ:
ที่สัญญาณนาฬิกา $16\text{ MHz}$ และ Prescaler = 8:
$$\text{Timer Clock} = \frac{16,000,000}{8} = 2,000,000\text{ Hz}$$

$$\text{ICR1 (TOP)} = \frac{2,000,000}{f} - 1$$

$$\text{OCR1A (Compare)} = \frac{\text{Duty (\%)} \times (\text{ICR1} + 1)}{100}$$

#### ตารางค่ารีจิสเตอร์จริงบน Arduino:
* **ความถี่ 1,000 Hz:** $\text{ICR1} = 1999$, ที่ Duty 50% $\rightarrow \text{OCR1A} = 1000$
* **ความถี่ 500 Hz:** $\text{ICR1} = 3999$, ที่ Duty 20% $\rightarrow \text{OCR1A} = 800$
* **ความถี่ 1,200 Hz:** $\text{ICR1} = 1665$, ที่ Duty 80% $\rightarrow \text{OCR1A} = 1332$

---

## 🚀 5. คำอธิบายแต่ละ Sketch

### 🟢 5.1 โหมดที่ 1: `Arduino_OLED_Mode1_Duty.ino`
* **วัตถุประสงค์:** ควบคุม Duty Cycle อย่างเดียว 0% ถึง 100% ที่ความถี่คงที่ **1,000 Hz**
* **การแสดงผลบน OLED:**
  * Line 1: `== MODE 1: DUTY ==`
  * Line 2: `Freq : 1000 Hz`
  * Line 3: `Duty : xx %`
  * Line 4: `RPM  : xxxx [CW]` หรือ `[CCW]` หรือ `[STOP]`
  * Line 5: `DIR  : CW`
  * Line 6: กราฟิก Progress Bar (0 – 100%)

---

### 🔵 5.2 โหมดที่ 2: `Arduino_OLED_Mode2_Dual.ino`
* **วัตถุประสงค์:** หมุน VR ตัวเดียวที่ขา A2 ควบคุมพร้อมกันทั้ง 2 ค่า:
  * ความถี่: **500 Hz ถึง 1,200 Hz**
  * Duty Cycle: **20% ถึง 80%**
* **การแสดงผลบน OLED:**
  * Line 1: `== MODE 2: DUAL ==`
  * Line 2: `F: xxxxHz T: x.xxms`
  * Line 3: `Duty : xx %`
  * Line 4: `RPM  : xxxx [CW]` หรือ `[CCW]` หรือ `[STOP]`
  * Line 5: `TOP: xxxx CMP: xxxx` (ค่าจริงในรีจิสเตอร์ `ICR1` และ `OCR1A`)
  * Line 6: กราฟิก Progress Bar ตามตำแหน่ง VR (0 – 100%)

---

### 🟣 5.3 โหมดที่ 3: `Arduino_GUI_Telemetry.ino`
* **วัตถุประสงค์:** เชื่อมต่อกับโปรแกรม Python GUI บนคอมพิวเตอร์ผ่านสาย USB Serial (Baud rate 115200)
* **การทำงาน:**
  * รองรับทั้ง `python pwmMotor.py` และ `python pwm_freq_duty_motor_control.py`
  * ส่งข้อมูล Telemetry อัตโนมัติทุก 100 ms: `F:<f>|D:<d>|T:<t>|RPM:<rpm>|DIR:<dir>\r\n`
  * สไลด์บาร์บนหน้าจอคอมพิวเตอร์จะขยับตาม และส่งคำสั่งมาปรับ PWM บน Pin 9 ได้ทันที
