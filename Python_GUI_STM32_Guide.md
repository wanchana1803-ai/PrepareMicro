# คู่มือการเขียน Python GUI เชื่อมต่อกับ STM32 (ฉบับจำง่าย สำหรับทำข้อสอบ)

คู่มือนี้ออกแบบมาเพื่อให้ **จำโครงสร้างไปเขียนสดได้ง่าย** ไม่ต้องพึ่ง AI หรือโค้ดสำเร็จรูปที่ซับซ้อน โดยใช้เครื่องมือมาตรฐาน:
1. **Python**: ใช้ **`tkinter`** (มีมากับ Python ทุกเครื่อง ไม่ต้องติดตั้งเพิ่ม) + **`pyserial`** (สำหรับคุยผ่านพอร์ต USB/COM)
2. **STM32F410RB**: ใช้พอร์ต **USART2** (บนบอร์ด Nucleo จะเชื่อมเข้าสาย USB เส้นเดียวกับ ST-LINK ไม่ต้องต่อสายแปลงเพิ่ม)

---

## 🧭 ภาพรวมการทำงาน (Concept)

```
[ STM32F410RB ]  <---- สาย USB (Virtual COM Port) ---->  [ คอมพิวเตอร์ / Python GUI ]
 - รับคำสั่ง '1' -> สั่งเปิดไฟ LED                      - กดปุ่ม ON -> ส่ง '1'
 - ส่งค่า ADC "3000\n"                             - รับข้อความ -> นำไปอัปเดต Label
```

---

## ส่วนที่ 1: การตั้งค่าและโค้ดฝั่ง STM32 (CubeIDE)

### 1. การตั้งค่าใน CubeMX
1. ไปที่ **Connectivity** > เลือก **`USART2`**
2. ปรับ Mode เป็น **`Asynchronous`**
3. ดูแท็บ Parameter Settings:
   - **Baud Rate**: `115200` (หรือ `9600`)
   - **Word Length**: 8 Bits
   - **Stop Bits**: 1

*(บนบอร์ด Nucleo ขา `PA2` คือ TX และ `PA3` คือ RX เชื่อมต่อกับคอมฯ ทางสาย USB เรียบร้อยแล้ว)*

---

### 2. โค้ดฝั่ง STM32 (`main.c`)

#### A. ประกาศตัวแปรรับ-ส่ง ใน `/* USER CODE BEGIN PV */`
```c
/* USER CODE BEGIN PV */
uint8_t rx_data;          // ตัวแปรรับคำสั่ง 1 ตัวอักษรจาก Python
char tx_buffer[32];       // บัฟเฟอร์ส่งข้อความกลับไป Python
uint16_t adc_val = 0;     // สมมติอ่านค่า ADC
/* USER CODE END PV */
```

#### B. การทำงานใน `while (1)` ใน `/* USER CODE BEGIN 3 */`
```c
  /* USER CODE BEGIN 3 */
  // 1. ตรวจสอบว่า Python ส่งคำสั่งมาหรือไม่ (Timeout 10 ms เพื่อไม่ให้บล็อกลูป)
  if (HAL_UART_Receive(&huart2, &rx_data, 1, 10) == HAL_OK)
  {
      if (rx_data == '1')
      {
          HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);   // เปิด LED
      }
      else if (rx_data == '0')
      {
          HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET); // ปิด LED
      }
  }

  // 2. อ่านค่า ADC และส่งขึ้น Python ทุกๆ 200 ms
  HAL_ADC_Start(&hadc1);
  if (HAL_ADC_PollForConversion(&hadc1, 10) == HAL_OK)
  {
      adc_val = HAL_ADC_GetValue(&hadc1);
  }
  HAL_ADC_Stop(&hadc1);

  // แปลงค่าเป็นข้อความลงท้ายด้วย \n (เพื่อให้ Python อ่านง่าย)
  sprintf(tx_buffer, "%d\n", adc_val);
  HAL_UART_Transmit(&huart2, (uint8_t*)tx_buffer, strlen(tx_buffer), 100);

  HAL_Delay(200);
  /* USER CODE END 3 */
```

---

## ส่วนที่ 2: โค้ดฝั่ง Python (Tkinter + PySerial)

ติดตั้งไลบรารี serial ก่อนใช้งาน (คำสั่งใน Terminal):
```bash
pip install pyserial
```

### โครงสร้างจำง่าย 4 ขั้นตอน (ฉบับ Minimal ท่องจำไปเขียนสอบได้)

```python
import tkinter as tk
import serial
import time

# -------------------------------------------------------------
# 1. การเชื่อมต่อ Serial
# -------------------------------------------------------------
# เปลี่ยน COM3 ให้ตรงกับพอร์ตของบอร์ดใน Device Manager
ser = serial.Serial('COM3', 115200, timeout=0.1)
time.sleep(2) # รอให้บอร์ดพร้อมหลัง Reset 2 วินาที

# -------------------------------------------------------------
# 2. ฟังก์ชันส่งคำสั่งไปหา STM32
# -------------------------------------------------------------
def send_on():
    ser.write(b'1') # ส่งตัวอักษร '1' แบบ byte

def send_off():
    ser.write(b'0') # ส่งตัวอักษร '0' แบบ byte

def send_slider(val):
    # ส่งค่าตัวเลขจาก Slider ตามด้วย \n
    ser.write(f"P{val}\n".encode())

# -------------------------------------------------------------
# 3. ฟังก์ชันรับค่าจาก STM32 มาแสดงผลบนหน้าจอ (ใช้ .after() วนลูป)
# -------------------------------------------------------------
def read_serial():
    if ser.in_waiting > 0: # ตรวจสอบว่ามีข้อมูลส่งมาจาก STM32 หรือไม่
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            lbl_adc.config(text=f"ADC Value: {line}")
            
    # ให้ฟังก์ชันนี้เรียกตัวเองซ้ำทุก 100 ms (ไม่ต้องพึ่ง Threading ให้งง)
    root.after(100, read_serial)

# -------------------------------------------------------------
# 4. ออกแบบหน้าต่าง UI ด้วย Tkinter (Layout พื้นฐาน)
# -------------------------------------------------------------
root = tk.Tk()
root.title("STM32 Controller")
root.geometry("300x300")

# ปุ่มเปิด-ปิดไฟ
btn_on = tk.Button(root, text="LED ON", bg="green", fg="white", width=15, command=send_on)
btn_on.pack(pady=5)

btn_off = tk.Button(root, text="LED OFF", bg="red", fg="white", width=15, command=send_off)
btn_off.pack(pady=5)

# สไลเดอร์ปรับค่า PWM (0 - 1000)
slider = tk.Scale(root, from_=0, to=1000, orient="horizontal", label="PWM Duty", command=send_slider)
slider.pack(pady=10)

# ป้ายข้อความแสดงค่า ADC
lbl_adc = tk.Label(root, text="ADC Value: ---", font=("Arial", 14))
lbl_adc.pack(pady=15)

# เริ่มต้นลูปอ่านข้อมูล Serial
root.after(100, read_serial)

# รันหน้าต่าง
root.mainloop()

# ปิดพอร์ตเมื่อปิดโปรแกรม
ser.close()
```

---

## 💡 เทคนิคจำหัวใจหลักไปเขียนเองในห้องสอบ

### 1. หัวใจของการส่งข้อมูล (Python -> STM32)
* **Python**: ใช้ `ser.write(b'X')` หรือ `ser.write("ข้อความ\n".encode())`
* **STM32**: ใช้ `HAL_UART_Receive(&huart2, &rx_data, 1, 10)`

### 2. หัวใจของการรับข้อมูล (STM32 -> Python)
* **STM32**: ใช้ `sprintf(tx_buf, "%d\n", val);` แล้วส่งด้วย `HAL_UART_Transmit(...)` 
  > ⚠️ **กฎสำคัญ:** ให้ปิดท้ายข้อความด้วย `\n` เสมอ เพื่อให้ Python ใช้คำสั่ง `ser.readline()` ตัดรอบบรรทัดได้ง่าย
* **Python**: 
  ```python
  if ser.in_waiting > 0:
      data = ser.readline().decode().strip()
  ```

### 3. ทำไมต้องใช้ `root.after()` แทน `threading` หรือ `while True`?
* ถ้าเขียน `while True` ใน Tkinter หน้าต่างจะ **ค้าง (Freeze)** ทันที
* ถ้าเขียน `threading` โค้ดจะยาวและจำยาก โอกาสเกิด Error สูง
* `root.after(100, read_serial)` คือการบอก GUI ให้ **"อีก 100 มิลลิวินาที ค่อยกลับมาเช็คข้อมูลจาก STM32 อีกรอบนะ"** ทำให้ GUI ทำงานลื่นไหล ไม่ค้าง และโค้ดสั้นเพียง 2 บรรทัด!

---

## 🛠️ ขั้นตอนการ Debug หากเชื่อมต่อไม่ได้
1. **เช็คพอร์ต COM**: กดปุ่ม `Windows + X` > เลือก **Device Manager** > ดูที่หมวด **Ports (COM & LPT)** ว่า STM32 อยู่ที่ `COM` อะไร (เช่น COM3, COM5)
2. **เช็ค Baud Rate**: ต้องตรงกันทั้งใน STM32CubeMX และใน Python (`115200` หรือ `9600`)
3. **พอร์ตชนกัน (Port Busy)**: ปิดโปรแกรม Serial Monitor อื่นๆ (เช่น PuTTY, Arduino IDE, STM32CubeIDE Terminal) ก่อนรัน Python เสมอ
