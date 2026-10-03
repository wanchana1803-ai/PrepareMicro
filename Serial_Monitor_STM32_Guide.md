# คู่มือการใช้งาน Serial Monitor และคำสั่ง `printf()` บน STM32 (ฉบับสมบูรณ์)

คู่มือนี้จะสอนวิธีดูข้อมูลจาก **STM32F410RB** ผ่าน **Serial Monitor** ในคอมพิวเตอร์ โดยใช้โปรแกรม **STM32CubeIDE ในตัว** (ไม่ต้องโหลดโปรแกรมเพิ่ม) พร้อมเทคนิคเด็ดที่ต้องรู้: **การตั้งค่าให้ใช้คำสั่ง `printf()` ปริ้นท์ออก Serial Monitor ได้เหมือนภาษา C ทั่วไป!**

---

## 📌 จุดเด่นของบอร์ด Nucleo-F410RB (ฮาร์ดแวร์)
บนบอร์ด Nucleo ขา **USART2**:
- `PA2` = TX (ส่งข้อมูลเข้าคอมฯ)
- `PA3` = RX (รับข้อมูลจากคอมฯ)

**คุณไม่ต้องต่อสายอะไรเพิ่มเลย!** เพราะวงจร ST-LINK บนบอร์ดเชื่อมต่อคู่นี้เข้ากับพอร์ต USB ให้แล้ว เสียบสาย USB เส้นเดียวก็เปิด Serial Monitor ดูได้ทันที

---

## ส่วนที่ 1: การตั้งค่า CubeMX (ทำครั้งแรก)

1. ไปที่ **Connectivity** > เลือก **`USART2`**
2. ปรับ Mode เป็น **`Asynchronous`**
3. เช็ค Parameter Settings:
   - **Baud Rate:** `115200` (หรือ `9600`)
   - **Word Length:** 8 Bits
   - **Parity:** None
   - **Stop Bits:** 1

---

## ส่วนที่ 2: สุดยอดเทคนิคเชื่อม `printf()` เพื่อดูค่า (มี 2 วิธี)

โดยปกติ STM32 จะต้องแปลงตัวเลขเป็นตัวหนังสือยาวๆ แต่ถ้าเราเขียนฟังก์ชัน **`__io_putchar`** ดักไว้ เราจะสามารถใช้คำสั่ง **`printf()`** ปริ้นท์ค่าตัวแปรออกจอคอมได้ทันทีเหมือนภาษา C ทั่วไป!

### เลือก 1 ใน 2 วิธีนี้ไปวางใน `/* USER CODE BEGIN 0 */`:

#### 🅰️ วิธีที่ 1: ผ่านพอร์ต USART (สำหรับเปิดดูผ่าน Arduino IDE, PuTTY, Python GUI)
*ต้องเปิด USART2 ใน CubeMX ก่อน*
```c
/* USER CODE BEGIN 0 */
#include <stdio.h>

// เชื่อม printf เข้ากับพอร์ต USART2 (ใช้พอร์ต COM)
int __io_putchar(int ch)
{
    HAL_UART_Transmit(&huart2, (uint8_t *)&ch, 1, HAL_MAX_DELAY);
    return ch;
}
/* USER CODE END 0 */
```

#### 🅱️ วิธีที่ 2: ผ่าน Serial Wire Viewer / SWV (ดูใน STM32CubeIDE ได้ 100% ไม่ต้องเปิด COM Port)
*ไม่ต้องเปิด USART ใน CubeMX, ใช้สาย ST-LINK เส้นเดิมได้ทันที*
```c
/* USER CODE BEGIN 0 */
#include <stdio.h>

// เชื่อม printf เข้ากับฮาร์ดแวร์ ITM (ส่งออกทางขา SWO / ST-LINK)
int __io_putchar(int ch)
{
    ITM_SendChar(ch);
    return ch;
}
/* USER CODE END 0 */
```

---

### โค้ดเรียกใช้ `printf()` ใน `/* USER CODE BEGIN 3 */` (เขียนเหมือนกันทั้ง 2 วิธี!):
```c
  /* USER CODE BEGIN 3 */
  // ตัวอย่าง: ปริ้นท์ค่า ADC และ Volt ทุกๆ 200 ms (ใช้ร่วมกับ HAL_GetTick)
  if (HAL_GetTick() - last_time >= 200)
  {
      last_time = HAL_GetTick();

      // สั่งปริ้นท์ตัวเลขและข้อความออกจอได้ทันที
      // แนะนำใส่ \r\n ปิดท้ายเสมอเพื่อขึ้นบรรทัดใหม่
      printf("ADC: %4d | Volt: %d.%02d V\r\n", 
             adc_val, (int)voltage, (int)(voltage * 100) % 100);
  }
  /* USER CODE END 3 */
```

> ⚠️ **ทริคแก้ปัญหาปริ้นท์เลขทศนิยม (`%f`) ไม่ออกใน STM32CubeIDE:**  
> STM32CubeIDE ปิดการแสดงผลทศนิยมไว้เป็นค่าเริ่มต้นเพื่อประหยัดหน่วยความจำ  
> **วิธีเปิดใช้งาน `%f`:**  
> คลิกขวาที่ชื่อโปรเจกต์ > **Properties** > **C/C++ Build** > **Settings** > แถบ **Tool Settings** > เมนู **MCU GCC Linker** > **Miscellaneous** > ติ๊กถูกที่ช่อง **`Use float with printf from newlib-nano (-u _printf_float)`** > กด **Apply and Close**  
> จากนั้นจะสามารถใช้ `printf("Volt = %.2f V\r\n", voltage);` ได้ทันที!

---

## ส่วนที่ 3: วิธีเปิดดูค่าผ่าน Serial Wire Viewer (SWV) ใน STM32CubeIDE (ไม่ต้องพึ่ง Terminal!)

หาก STM32CubeIDE ไม่มีปลั๊กอิน Serial Terminal หรือไม่อยากสลับหน้าจอไปโปรแกรมอื่น **SWV คือวิธีที่ดีที่สุด** เพราะติดมากับโปรแกรมตั้งแต่แรก:

### 3 ขั้นตอนใช้งาน SWV:

#### ขั้นที่ 1: ตั้งค่า Debugger ให้เปิดใช้งาน SWV
1. ไปที่เมนูด้านบน: คลิก **`Run`** > **`Debug Configurations...`**
2. ดับเบิ้ลคลิกเลือกโปรเจกต์ของคุณใต้ **STM32 C/C++ Application** ทางซ้าย
3. คลิกแท็บ **`Debugger`**
4. เลื่อนลงมาล่างสุด หาหัวข้อ **`Serial Wire Viewer (SWV)`**:
   - ติ๊กถูกที่ช่อง **`Enable`**
   - ช่อง **Core Clock:** ใส่ความถี่ของชิป (ค่ามาตรฐาน Nucleo มักเป็น `16` MHz หรือตามที่ตั้งไว้ใน Clock Configuration)
5. กด **`Apply`** แล้วกด **`Debug`**

#### ขั้นที่ 2: เปิดหน้าต่าง SWV ITM Data Console
1. เมื่อโปรแกรมตัดเข้าหน้าต่าง Debug Mode:
2. ไปที่เมนู: **`Window`** > **`Show View`** > **`SWV`** > เลือก **`SWV ITM Data Console`**  
   *(หน้าต่างสีขาวจะโผล่ขึ้นมาที่แผงควบคุมด้านล่าง)*

#### ขั้นที่ 3: เปิดรับข้อมูลและกดรัน
1. ในหน้าต่าง SWV ITM Data Console ให้คลิกที่ **ไอคอนรูปฟันเฟือง (Configure trace)**
2. ติ๊กถูกที่ช่อง **`0`** (ใต้หัวข้อ ITM Stimulus Ports) แล้วกด **OK**
3. กดปุ่ม **วงกลมสีแดง (Start Trace)** ในหน้าต่าง SWV ITM Data Console เพื่อเริ่มบันทึกข้อมูล
4. กดปุ่ม **Resume (ปุ่ม Play สีเขียวด้านบน)** เพื่อให้บอร์ดเริ่มทำงาน
5. ข้อความ `ADC: ... | Volt: ...` จะวิ่งขึ้นมาในหน้าต่าง SWV ITM Data Console ทันที!

---

## ส่วนที่ 4: การเปิดดูผ่านโปรแกรมภายนอกยอดนิยม

หากไม่อยากดูใน STM32CubeIDE สามารถใช้โปรแกรมเหล่านี้ได้:

### แบบที่ 1: Arduino IDE Serial Monitor (ง่ายที่สุด)
1. เปิดโปรแกรม Arduino IDE
2. ไปที่เมนู **Tools** > **Port** > เลือกพอร์ต COM ของ STM32
3. กดปุ่มไอคอน **Serial Monitor** (มุมขวาบน)
4. ปรับ Baud Rate ที่มุมล่างขวาของ Serial Monitor ให้เป็น **`115200 baud`**

### แบบที่ 2: โปรแกรม PuTTY
1. เปิด PuTTY
2. ตรง Connection type: ติ๊กเลือก **`Serial`**
3. ช่อง **Serial line:** พิมพ์ชื่อพอร์ต เช่น `COM3`
4. ช่อง **Speed:** พิมพ์ `115200`
5. กดปุ่ม **Open**

---

## 🛠️ Checklist ปัญหาที่พบบ่อย (Troubleshooting)

1. **เปิด Port ไม่ได้ / Error "Port Busy" หรือ "Access Denied":**
   - สาเหตุ: มีโปรแกรมอื่นกำลังเชื่อมต่อพอร์ต COM นั้นอยู่ (เช่น เปิด Python GUI ค้างไว้ หรือเปิด PuTTY ซ้อนกัน)
   - วิธีแก้: ปิดโปรแกรมหรือปิดแท็บ Terminal เก่าก่อนเสมอ

2. **ตัวหนังสืออ่านไม่รู้เรื่อง / ออกมาเป็นภาษาต่างดาว ($\diamondsuit$ ??):**
   - สาเหตุ: ค่า **Baud Rate** ไม่ตรงกัน (เช่น ใน CubeMX ตั้ง 115200 แต่ใน Serial Monitor ตั้ง 9600)
   - วิธีแก้: ปรับ Baud Rate ให้เท่ากัน

3. **ข้อความแสดงผลต่อกันเป็นพืด ไม่ยอมขึ้นบรรทัดใหม่:**
   - สาเหตุ: ส่งแค่ `\n` อย่างเดียว (บาง Terminal ต้องการ Carriage Return ด้วย)
   - วิธีแก้: ปิดท้าย `printf()` ด้วย **`\r\n`** เสมอ เช่น `printf("Hello\r\n");`
