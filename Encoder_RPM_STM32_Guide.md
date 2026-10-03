# คู่มือการใช้งาน Rotary Encoder วัดความเร็วรอบ (RPM) สัมพันธ์กับความถี่ และนำขึ้น Python GUI

คู่มือนี้สรุปทฤษฎีความสัมพันธ์ระหว่าง **ความถี่ (Frequency)** กับ **ความเร็วรอบ (RPM)** พร้อมการตั้งค่า **STM32F410RB (Encoder Mode)** และโค้ด **Python GUI** สำหรับรับค่าไปแสดงผลแบบจำง่ายสำหรับทำข้อสอบ

---

## 🧭 ส่วนที่ 1: ทฤษฎีความสัมพันธ์ระหว่าง ความถี่ และ ความเร็วรอบ (RPM)

### 1. รู้จักสเปกของ Rotary Encoder (Incremental)
Encoder แบบ 2 เฟส (Phase A และ Phase B) ส่งสัญญาณพัลส์รูปคลื่นสี่เหลี่ยมเยื้องเฟสกัน 90 องศา
- **PPR (Pulses Per Revolution):** จำนวนพัลส์ต่อการหมุน 1 รอบ เช่น 100, 360, 600 PPR
- **CPR (Counts Per Revolution):** จำนวนการนับต่อ 1 รอบจริงในไมโครคอนโทรลเลอร์
  - ใน STM32 เมื่อตั้งเป็นโหมด **Encoder Mode TI1 and TI2 (โหมด X4)** ไมโครจะนับทั้ง **ขอบขาขึ้นและขาลงของทั้ง 2 เฟส**
  - ดังนั้น:
    $$\text{CPR} = 4 \times \text{PPR}$$
    *(เช่น ถ้า Encoder มี 100 PPR ในโหมด X4 จะนับได้ $4 \times 100 = 400$ Count ต่อการหมุน 1 รอบ)*

---

### 2. ความสัมพันธ์ทางคณิตศาสตร์ (สูตรที่มักออกข้อสอบ)

#### ก) ความถี่ของสัญญาณพัลส์ (Frequency: $f$)
ความถี่คือจำนวนพัลส์ (Count) ที่เกิดขึ้นใน 1 วินาที (Hz):
$$f = \frac{\Delta\text{Count}}{\Delta t}$$
*(เมื่อ $\Delta\text{Count}$ คือจำนวนพัลส์ที่นับได้ในช่วงเวลา $\Delta t$ วินาที)*

#### ข) ความเร็วรอบต่อวินาที (RPS: Revolutions Per Second)
$$\text{RPS} = \frac{f}{\text{CPR}} = \frac{f}{4 \times \text{PPR}}$$

#### ค) ความเร็วรอบต่อนาที (RPM: Revolutions Per Minute)
แปลงจากต่อวินาทีให้เป็นต่อนาที (คูณด้วย 60 วินาที):
$$\text{RPM} = \text{RPS} \times 60 = \frac{f \times 60}{\text{CPR}}$$
หรือเขียนในรูปของจำนวนพัลส์ที่นับได้:
$$\text{RPM} = \frac{\Delta\text{Count} \times 60}{(4 \times \text{PPR}) \times \Delta t}$$

---

### 📝 ตัวอย่างการคำนวณด้วยมือ (เผื่อเจอในข้อสอบ)
> **โจทย์:** ใช้ Encoder ขนาด **100 PPR** อ่านค่าทุกๆ **0.1 วินาที ($\Delta t = 0.1\text{ s}$)**  
> ในโหมด X4 ถ้านับพัลส์ได้ $\Delta\text{Count} = 200$ พัลส์ จงหาความถี่และ RPM
> 
> **วิธีทำ:**
> 1. หาความถี่:  
>    $$f = \frac{200}{0.1} = 2,000 \text{ Hz (หรือ counts/sec)}$$
> 2. หา CPR:  
>    $$\text{CPR} = 4 \times 100 = 400 \text{ counts/rev}$$
> 3. หา RPM:  
>    $$\text{RPM} = \frac{2,000 \times 60}{400} = 300 \text{ RPM}$$
> **ตอบ:** ความถี่ 2,000 Hz, ความเร็วรอบ 300 RPM

---

## ⚙️ ส่วนที่ 2: การตั้งค่าใน STM32CubeMX

1. ไปที่หมวด **Timers** > เลือก Timer เช่น **`TIM1`** (หรือ `TIM5`)
2. ตรง **Combined Channels** > เลือกเป็น **`Encoder Mode`**
   - STM32 จะกำหนดขาให้อัตโนมัติ: เช่น `PA8` (TIM1_CH1) และ `PA9` (TIM1_CH2)
3. ในแท็บ **Parameter Settings**:
   - **Encoder Mode:** เลือก `Encoder Mode TI1 and TI2` (โหมด X4 นับละเอียดสุดและรู้ทิศทางการหมุน)
   - **Counter Period (ARR):** ตั้งเป็น `65535` (ค่าสูงสุดของ Timer 16-bit เพื่อไม่ให้ Overflow เร็ว)
4. เปิดใช้งาน **`USART2`** (Asynchronous, Baud 115200) เพื่อส่งข้อมูลเข้าคอมพิวเตอร์

---

## 💻 ส่วนที่ 3: โค้ดฝั่ง STM32 (`main.c`)

### 1) วางคำสั่ง Redirect `printf` ใน `/* USER CODE BEGIN 0 */`
```c
/* USER CODE BEGIN 0 */
#include <stdio.h>
#include <stdlib.h>

int __io_putchar(int ch)
{
    HAL_UART_Transmit(&huart2, (uint8_t *)&ch, 1, HAL_MAX_DELAY);
    return ch;
}
/* USER CODE END 0 */
```

### 2) ประกาศตัวแปรใน `/* USER CODE BEGIN PV */`
```c
/* USER CODE BEGIN PV */
#define PPR 100                 // ระบุ PPR ตามสเปกของ Encoder ที่ใช้ในแล็บ
#define SAMPLING_TIME_MS 100    // สุ่มอ่านทุก 100 ms (0.1 วินาที)

uint16_t current_count = 0;
uint16_t prev_count = 0;
int16_t diff_count = 0;

float frequency_hz = 0.0f;
float rpm = 0.0f;
uint32_t last_time = 0;
/* USER CODE END PV */
```

### 3) สั่ง Start Encoder ใน `/* USER CODE BEGIN 2 */`
```c
  /* USER CODE BEGIN 2 */
  // สั่งเปิด Timer ในโหมด Encoder
  HAL_TIM_Encoder_Start(&htim1, TIM_CHANNEL_ALL);
  /* USER CODE END 2 */
```

### 4) คำนวณความถี่และ RPM ใน `/* USER CODE BEGIN 3 */` (ใน while loop)
```c
  /* USER CODE BEGIN 3 */
  // คำนวณทุกๆ 100 ms (0.1 วินาที) โดยใช้ HAL_GetTick()
  if (HAL_GetTick() - last_time >= SAMPLING_TIME_MS)
  {
      last_time = HAL_GetTick();

      // 1. อ่านค่า Counter ปัจจุบัน
      current_count = __HAL_TIM_GET_COUNTER(&htim1);

      // 2. คำนวณหา Delta Count (แปลงเป็น signed int16_t เพื่อรองรับการหมุนตามเข็ม/ทวนเข็ม)
      diff_count = (int16_t)(current_count - prev_count);
      prev_count = current_count;

      // 3. คำนวณความถี่ (Hz) = จำนวนพัลส์ต่อวินาที (ใช้ค่าสัมบูรณ์ abs)
      frequency_hz = (float)abs(diff_count) / (SAMPLING_TIME_MS / 1000.0f);

      // 4. คำนวณ RPM: (diff_count * 60) / (CPR * delta_time)
      // เมื่อ CPR = 4 * PPR
      rpm = ((float)diff_count * 60.0f) / ((4.0f * PPR) * (SAMPLING_TIME_MS / 1000.0f));

      // 5. ส่งค่าออก UART ในรูปแบบ: RPM,Frequency เช่น "300.5,2000.0\r\n"
      printf("%.1f,%.1f\r\n", rpm, frequency_hz);
  }
  /* USER CODE END 3 */
```

---

## 🖥️ ส่วนที่ 4: โค้ดฝั่ง Python GUI (Tkinter รับค่าและแสดงผล)

โค้ดนี้จะรับข้อความ `"RPM,Frequency"` แยกข้อมูลด้วย `.split(',')` แล้วแสดง:
- **RPM** (พร้อมบอกทิศทาง CW หมุนตามเข็ม / CCW หมุนทวนเข็ม)
- **ความถี่พัลส์ (Hz)**

```python
import tkinter as tk
import serial

# 1. เชื่อมต่อ Serial (แก้ไข COM ให้ตรงกับบอร์ด)
ser = serial.Serial('COM3', 115200, timeout=0.1)

# 2. ฟังก์ชันอ่านข้อมูลและอัปเดตหน้าจอ GUI (ไม่ใช้ Threading ให้งง)
def read_serial():
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            try:
                # แยกค่า RPM และ Frequency ด้วยเครื่องหมายจุลภาค (,)
                parts = line.split(',')
                if len(parts) == 2:
                    rpm_val = float(parts[0])
                    freq_val = float(parts[1])

                    # ตรวจสอบทิศทางการหมุนจากเครื่องหมาย (+ คือ CW, - คือ CCW)
                    if rpm_val > 0:
                        direction = "หมุนตามเข็ม (CW)"
                        lbl_dir.config(fg="green")
                    elif rpm_val < 0:
                        direction = "หมุนทวนเข็ม (CCW)"
                        lbl_dir.config(fg="blue")
                    else:
                        direction = "หยุดนิ่ง (STOP)"
                        lbl_dir.config(fg="gray")

                    # อัปเดตข้อความบนหน้าจอ
                    lbl_rpm.config(text=f"{abs(rpm_val):.1f} RPM")
                    lbl_freq.config(text=f"ความถี่: {freq_val:.1f} Hz")
                    lbl_dir.config(text=f"สถานะ: {direction}")
            except ValueError:
                pass # ข้ามบรรทัดถ้าข้อมูลมาไม่สมบูรณ์

    # วนลูปอ่านซ้ำทุก 50 ms
    root.after(50, read_serial)

# 3. ออกแบบหน้าต่าง UI
root = tk.Tk()
root.title("ระบบวัดความเร็วรอบ Encoder")
root.geometry("380x300")
root.configure(bg="#f0f0f0")

# หัวข้อ
tk.Label(root, text="ENCODER SPEED MONITOR", font=("Arial", 14, "bold"), bg="#f0f0f0").pack(pady=10)

# แสดงความเร็วรอบ RPM ตัวใหญ่
lbl_rpm = tk.Label(root, text="0.0 RPM", font=("Arial", 28, "bold"), fg="#d9534f", bg="#f0f0f0")
lbl_rpm.pack(pady=10)

# แสดงความถี่ Hz
lbl_freq = tk.Label(root, text="ความถี่: 0.0 Hz", font=("Arial", 14), bg="#f0f0f0")
lbl_freq.pack(pady=5)

# แสดงทิศทาง
lbl_dir = tk.Label(root, text="สถานะ: หยุดนิ่ง (STOP)", font=("Arial", 12, "bold"), bg="#f0f0f0", fg="gray")
lbl_dir.pack(pady=10)

# เริ่มต้นลูปอ่านข้อมูล Serial
root.after(50, read_serial)

root.mainloop()
ser.close()
```

---

## 🎯 จุดเน้นย้ำสำหรับทำข้อสอบ

1. **ทำไมต้อง Cast เป็น `(int16_t)`?**  
   - Counter ของ Timer ใน STM32 เมื่อหมุนถอยหลังจะนับลดจาก `0` ข้ามไป `65535`  
   - การแปลงเป็น `(int16_t)` จะทำให้เลข `65535` กลายเป็น `-1` โดยอัตโนมัติ ทำให้โปรแกรมรู้ทันทีว่าเป็นการหมุนทวนเข็มโดยไม่ต้องเขียน `if-else` ดักให้ซับซ้อน!
2. **ความถี่กับ RPM ต่างกันอย่างไร?**  
   - **ความถี่ ($f$):** บอกว่ามีพัลส์ไฟฟ้าผ่านเซนเซอร์วินาทีละกี่ลูก (หน่วย Hz หรือ pulses/s)  
   - **ความเร็วรอบ (RPM):** แปลงจากความถี่เป็นรอบการหมุนจริงของเพลา โดยคำนึงถึงจำนวนพัลส์ต่อรอบของ Encoder ($4 \times \text{PPR}$) แล้วคูณด้วย $60$ เพื่อคิดเป็นหน่วย "รอบต่อนาที"
