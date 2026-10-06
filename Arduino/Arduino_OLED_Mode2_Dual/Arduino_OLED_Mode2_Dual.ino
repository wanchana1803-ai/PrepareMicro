/*
 * =====================================================================================
 * Project: Arduino Standalone OLED Mode 2 - Dual Control (Freq 500-1200Hz & Duty 20-80%)
 * Controlled by: Single Potentiometer VR on Pin A2
 * Motor Base: 1,500 RPM Max (Range: 300 to 1,200 RPM)
 * 
 * Hardware Pinout (Arduino Uno / Nano / Mega):
 * - Potentiometer VR: Pin A2 (Analog In 0 - 5V / 0 - 1023)
 * - PWM Output:       Pin 9 (Timer 1 OC1A, Variable Hardware Fast PWM 500-1200 Hz)
 * - OLED Display:     I2C (SDA = Pin A4, SCL = Pin A5, VCC = 5V/3.3V, GND = GND)
 * - Motor Encoder:    Phase A = Pin 2 (Interrupt INT0), Phase B = Pin 3
 * 
 * Hardware Pinout (STM32duino / Nucleo-64 F410RB via Arduino IDE):
 * - Potentiometer VR: Pin A2 (PA4)
 * - PWM Output:       Pin D7 (PA8 / TIM1_CH1) or Pin D9
 * - OLED Display:     Pin D14 (PB9 SDA), Pin D15 (PB8 SCL)
 * - Motor Encoder:    Pin A0 (PA0), Pin A1 (PA1)
 * =====================================================================================
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- ตั้งค่าจอ OLED SSD1306 ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1     // ใช้ -1 ถ้าไม่มีขา RESET แยก
#define OLED_ADDR     0x3C   // Address มาตรฐานของ I2C OLED (0x3C หรือ 0x3D)

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --- กำหนดขาใช้งาน ---
#define PIN_POT_VR    A2     // ขาอ่านตัวต้านทานปรับค่าได้ (Potentiometer)
#define PIN_PWM_OUT   9      // ขาสัญญาณ PWM (Pin 9: OC1A Timer 1)
#define PIN_ENC_A     2      // ขา Encoder Phase A (Interrupt 0)
#define PIN_ENC_B     3      // ขา Encoder Phase B

// --- พารามิเตอร์มอเตอร์ & Encoder ---
#define MOTOR_MAX_RPM 1500   // ความเร็วรอบสูงสุดของมอเตอร์ที่ Duty 100%
#define ENCODER_PPR   100    // Pulse Per Revolution ของ Encoder

// --- ตัวแปรระบบ ---
volatile long enc_count = 0;
long prev_enc_count = 0;
float rpm_disp = 300.0;
String dir_str = "CW";       // CW, CCW, หรือ STOP

uint16_t freq_hz = 500;      // 500 - 1200 Hz
uint16_t duty_val = 20;      // 20 - 80 %
float period_ms = 2.00;      // 2.00 ms - 0.83 ms
uint8_t vr_pct = 0;          // 0 - 100 % ตำแหน่ง VR
uint32_t adc_val = 0;
uint16_t top_val = 3999;     // ICR1
uint16_t comp_val = 800;     // OCR1A

// ตัวจับเวลา Non-blocking
unsigned long last_adc_tick = 0;
unsigned long last_enc_tick = 0;
unsigned long last_oled_tick = 0;

// =====================================================================================
// ฟังก์ชัน Interrupt ตัวนับ Encoder
// =====================================================================================
void isr_encoder() {
  if (digitalRead(PIN_ENC_B) == HIGH) {
    enc_count++;
  } else {
    enc_count--;
  }
}

// =====================================================================================
// ตั้งค่า Hardware PWM Timer 1 (โหมดแปรผันความถี่ 500 - 1,200 Hz)
// =====================================================================================
void setupVariablePWM() {
#if defined(__AVR__)
  // สำหรับ Arduino Uno / Nano / Mega (ATmega328P)
  // Timer 1: Mode 14 Fast PWM (ICR1 เป็น TOP), Prescaler = 8
  // ความถี่ = 16 MHz / (8 * (ICR1 + 1)) = 2,000,000 / (ICR1 + 1)
  pinMode(PIN_PWM_OUT, OUTPUT);
  TCCR1A = _BV(COM1A1) | _BV(WGM11);            // Non-inverting PWM บน OC1A (Pin 9)
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS11); // Prescaler = 8, Mode 14
  top_val = (2000000UL / 500UL) - 1;            // เริ่มต้นที่ 500 Hz (ICR1 = 3999)
  ICR1 = top_val;
  comp_val = ((unsigned long)(top_val + 1) * 20UL) / 100UL; // Duty 20%
  OCR1A = comp_val;
#elif defined(ARDUINO_ARCH_STM32)
  pinMode(PIN_PWM_OUT, OUTPUT);
  analogWriteFrequency(500);
  analogWriteResolution(12);
  analogWrite(PIN_PWM_OUT, (4095 * 20) / 100);
#else
  pinMode(PIN_PWM_OUT, OUTPUT);
  analogWrite(PIN_PWM_OUT, (255 * 20) / 100);
#endif
}

// ฟังก์ชันอัปเดตทั้งความถี่และ Duty Cycle พร้อมกัน
void updatePWM(uint16_t freq, uint8_t duty) {
  freq = constrain(freq, 500, 1200);
  duty = constrain(duty, 20, 80);

#if defined(__AVR__)
  // 1. คำนวณ TOP (ICR1) = (2,000,000 / freq) - 1
  top_val = (2000000UL / freq) - 1;
  ICR1 = top_val;

  // 2. คำนวณ Compare (OCR1A) = (duty * (top_val + 1)) / 100
  comp_val = ((unsigned long)(top_val + 1) * (unsigned long)duty) / 100UL;
  OCR1A = comp_val;
#elif defined(ARDUINO_ARCH_STM32)
  analogWriteFrequency(freq);
  uint32_t val = ((uint32_t)duty * 4095UL) / 100UL;
  analogWrite(PIN_PWM_OUT, val);
  top_val = (1000000UL / freq) - 1;
  comp_val = ((top_val + 1) * duty) / 100;
#else
  uint16_t val = ((uint16_t)duty * 255) / 100;
  analogWrite(PIN_PWM_OUT, val);
#endif
}

// =====================================================================================
// ฟังก์ชันอ่านค่า ADC พร้อมกรองสัญญาณรบกวน (เฉลี่ย 8 ครั้ง)
// =====================================================================================
uint16_t readADCFiltered(uint8_t pin) {
  uint32_t sum = 0;
  for (int i = 0; i < 8; i++) {
    sum += analogRead(pin);
    delayMicroseconds(50);
  }
  return sum / 8;
}

// =====================================================================================
// ฟังก์ชันวาดแถบกราฟิก Progress Bar บนจอ OLED
// =====================================================================================
void drawProgressBar(int x, int y, int w, int h, int pct) {
  pct = constrain(pct, 0, 100);
  display.drawRect(x, y, w, h, SSD1306_WHITE);
  int fill_w = ((w - 4) * pct) / 100;
  if (fill_w > 0) {
    display.fillRect(x + 2, y + 2, fill_w, h - 4, SSD1306_WHITE);
  }
}

// =====================================================================================
// SETUP
// =====================================================================================
void setup() {
  Serial.begin(115200);

  // 1. ตั้งค่า PWM แปรผัน
  setupVariablePWM();

  // 2. ตั้งค่า Encoder Interrupt
  pinMode(PIN_ENC_A, INPUT_PULLUP);
  pinMode(PIN_ENC_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), isr_encoder, RISING);

  // 3. เริ่มต้นจอ OLED
  Wire.begin();
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println(F("OLED init failed! Check connections."));
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(15, 20);
  display.println(F("ARDUINO OLED OK"));
  display.setCursor(20, 36);
  display.println(F("MODE 2: DUAL"));
  display.display();
  delay(600);
}

// =====================================================================================
// LOOP
// =====================================================================================
void loop() {
  unsigned long current_millis = millis();

  // -----------------------------------------------------------------------------------
  // 1. อ่านค่า VR (A2) และคำนวณ Freq + Duty ทุก 30 ms
  // -----------------------------------------------------------------------------------
  if (current_millis - last_adc_tick >= 30) {
    last_adc_tick = current_millis;

    adc_val = readADCFiltered(PIN_POT_VR);

#if defined(ARDUINO_ARCH_STM32)
    vr_pct = map(adc_val, 0, 4095, 0, 100);
    freq_hz = 500 + (((uint32_t)adc_val * 700UL) / 4095UL);
    duty_val = 20 + (((uint32_t)adc_val * 60UL) / 4095UL);
#else
    vr_pct = map(adc_val, 0, 1023, 0, 100);
    freq_hz = 500 + (((uint32_t)adc_val * 700UL) / 1023UL);
    duty_val = 20 + (((uint32_t)adc_val * 60UL) / 1023UL);
#endif

    freq_hz = constrain(freq_hz, 500, 1200);
    duty_val = constrain(duty_val, 20, 80);
    period_ms = 1000.0 / (float)freq_hz;

    updatePWM(freq_hz, duty_val);
  }

  // -----------------------------------------------------------------------------------
  // 2. คำนวณความเร็วรอบ (RPM) และทิศทางหมุน (CW / CCW) ทุก 100 ms
  // -----------------------------------------------------------------------------------
  if (current_millis - last_enc_tick >= 100) {
    unsigned long dt = current_millis - last_enc_tick;
    last_enc_tick = current_millis;

    long diff = enc_count - prev_enc_count;
    prev_enc_count = enc_count;

    if (abs(diff) > 2) {
      if (diff > 0) dir_str = "CW";
      else dir_str = "CCW";

      rpm_disp = ((float)abs(diff) * 60000.0) / ((4.0 * ENCODER_PPR) * (float)dt);
    } else {
      if (duty_val > 0) {
        dir_str = "CW";
        rpm_disp = ((float)duty_val * (float)MOTOR_MAX_RPM) / 100.0;
      } else {
        dir_str = "STOP";
        rpm_disp = 0.0;
      }
    }
  }

  // -----------------------------------------------------------------------------------
  // 3. รีเฟรชหน้าจอ OLED ทุก 150 ms (แสดงผล 6 ข้อมูล)
  // -----------------------------------------------------------------------------------
  if (current_millis - last_oled_tick >= 150) {
    last_oled_tick = current_millis;

    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);

    // บรรทัดที่ 1: Header
    display.setCursor(10, 0);
    display.print(F("== MODE 2: DUAL =="));

    // บรรทัดที่ 2: ความถี่และคาบเวลาจริง
    display.setCursor(2, 12);
    display.print(F("F:"));
    display.print(freq_hz);
    display.print(F("Hz T:"));
    display.print(period_ms, 2);
    display.print(F("ms"));

    // บรรทัดที่ 3: Duty Cycle (20 - 80%)
    display.setCursor(2, 23);
    display.print(F("Duty : "));
    display.print(duty_val);
    display.print(F(" %"));

    // บรรทัดที่ 4: ความเร็วรอบ RPM พร้อมทิศทางหมุน
    display.setCursor(2, 34);
    display.print(F("RPM  : "));
    display.print((int)rpm_disp);
    display.print(F(" ["));
    display.print(dir_str);
    display.print(F("]"));

    // บรรทัดที่ 5: ค่า Timer Register จริง (ICR1 / OCR1A)
    display.setCursor(2, 45);
    display.print(F("TOP:"));
    display.print(top_val);
    display.print(F(" CMP:"));
    display.print(comp_val);

    // บรรทัดที่ 6: Progress Bar (อิงตาม VR 0 - 100%)
    drawProgressBar(2, 57, 124, 6, vr_pct);

    display.display();
  }
}
