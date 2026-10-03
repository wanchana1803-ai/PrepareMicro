# 🚀 STM32F410RB Exam Preparation & HAL Guides

ชุดคู่มือและโค้ดตัวอย่างสำหรับเตรียมสอบวิชาไมโครคอนโทรลเลอร์ (Microcontroller) โดยใช้ **STM32F410RB** ร่วมกับ **STM32CubeMX** และ **STM32CubeIDE**

---

## 📚 รายการคู่มือทั้งหมดใน Repository นี้

1. **[คู่มือสรุปคำสั่ง HAL Driver พื้นฐาน](STM32F410RB_HAL_Guide.md)**
   - Digital Input (กดติด-ปล่อยดับ, Edge Detection, Toggle Switch, Debounce)
   - Digital Output (WritePin, TogglePin)
   - Input Analog (ADC 12-bit Polling, แปลงเป็น Volt จริง)
   - Output Analog (DAC1 OUT1 PA5)
   - Output PWM (Timer PWM Generation, ADC to PWM Dimmer)
   - Non-blocking Delay (`HAL_GetTick()`)

2. **[คู่มือการดูค่าผ่าน Serial Monitor & printf](Serial_Monitor_STM32_Guide.md)**
   - การต่อ UART `printf` ผ่านพอร์ต COM
   - การใช้ Serial Wire Viewer (SWV / ITM) ดูค่าใน STM32CubeIDE โดยตรง

3. **[คู่มือจอแสดงผล OLED 1.3" I2C](OLED_I2C_STM32_Guide.md)**
   - การตั้งค่า I2C Fast Mode 400kHz
   - ชิปควบคุม SH1106 (1.3") vs SSD1306 (0.96")
   - การนำไลบรารีไปใช้ใน 1 นาที และคำสั่งแสดงผล

4. **[คู่มือ Python GUI เชื่อมต่อ STM32](Python_GUI_STM32_Guide.md)**
   - พัฒนา GUI ด้วย `tkinter` และ `pyserial`
   - เทคนิคไม่ใช้ Threading ป้องกัน GUI ค้างด้วย `root.after()`

5. **[คู่มือการวัดความเร็วรอบ Rotary Encoder](Encoder_RPM_STM32_Guide.md)**
   - ความสัมพันธ์ระหว่างความถี่สัญญาณ (Frequency) กับความเร็วรอบ (RPM)
   - การตั้งค่า Timer Encoder Mode (X4: TI1 and TI2)

---

## 📁 โฟลเดอร์ไลบรารี
- **`OLED_Library/`**: ชุดไฟล์ไลบรารีจอ OLED พร้อมใช้งาน (`fonts.h`, `fonts.c`, `ssd1306.h`, `ssd1306.c`)
- **`test/`**: โปรเจกต์ทดลองเขียนจริงใน STM32CubeIDE (`Test1234`)
