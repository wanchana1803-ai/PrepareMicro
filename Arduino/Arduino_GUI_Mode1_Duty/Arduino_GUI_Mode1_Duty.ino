/*
 * =====================================================================================
 * Project: Arduino GUI Mode 1 - Duty Cycle Control (0 - 100%) [NO OLED / NO LIBRARIES]
 * Compatible with: python pwmMotor.py
 * Fixed Frequency: 1,000 Hz
 * Motor Base:      1,500 RPM Max
 * 
 * Hardware Pinout (Arduino Uno / Nano / Mega):
 * - PWM Output:    Pin 9 (Timer 1 OC1A, Hardware 16-bit Fast PWM 1,000 Hz)
 * - Motor Encoder: Phase A = Pin 2 (Interrupt INT0), Phase B = Pin 3
 * - USB Serial:    Connect to PC (Baud Rate: 115200)
 * =====================================================================================
 */

#define PIN_PWM_OUT   9
#define PIN_ENC_A     2
#define PIN_ENC_B     3

#define MOTOR_MAX_RPM 1500
#define ENCODER_PPR   100

// --- ตัวแปร PWM (ความถี่คงที่ 1000 Hz) ---
const uint16_t freq_hz = 1000;
uint16_t duty_val = 50;      // เริ่มต้นที่ 50%

// --- ตัวแปร Encoder & ความเร็วรอบ ---
volatile long enc_count = 0;
long prev_enc_count = 0;
float rpm = 0.0;
String dir_str = "STOP";

// --- ตัวจับเวลา Telemetry ---
unsigned long last_telemetry_tick = 0;

// --- บัฟเฟอร์ Serial ---
String rx_buffer = "";

// =====================================================================================
// ฟังก์ชัน Interrupt Encoder
// =====================================================================================
void isr_encoder() {
  if (digitalRead(PIN_ENC_B) == HIGH) {
    enc_count++;
  } else {
    enc_count--;
  }
}

// =====================================================================================
// ตั้งค่า Hardware PWM 1,000 Hz บน Pin 9
// =====================================================================================
void setupPWM1000Hz() {
#if defined(__AVR__)
  pinMode(PIN_PWM_OUT, OUTPUT);
  TCCR1A = _BV(COM1A1) | _BV(WGM11);            // Mode 14 Fast PWM (ICR1 เป็น TOP)
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS11); // Prescaler = 8 (2 MHz)
  ICR1 = 1999;                                   // 1,000 Hz
  applyDuty(duty_val);
#elif defined(ARDUINO_ARCH_STM32)
  pinMode(PIN_PWM_OUT, OUTPUT);
  analogWriteFrequency(1000);
  analogWriteResolution(12);
  applyDuty(duty_val);
#else
  pinMode(PIN_PWM_OUT, OUTPUT);
  applyDuty(duty_val);
#endif
}

void applyDuty(uint8_t d) {
  duty_val = constrain(d, 0, 100);
#if defined(__AVR__)
  OCR1A = ((unsigned long)duty_val * 2000UL) / 100UL;
#elif defined(ARDUINO_ARCH_STM32)
  analogWrite(PIN_PWM_OUT, ((uint32_t)duty_val * 4095UL) / 100UL);
#else
  analogWrite(PIN_PWM_OUT, map(duty_val, 0, 100, 0, 255));
#endif
}

// =====================================================================================
// SETUP
// =====================================================================================
void setup() {
  Serial.begin(115200);

  setupPWM1000Hz();

  pinMode(PIN_ENC_A, INPUT_PULLUP);
  pinMode(PIN_ENC_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), isr_encoder, RISING);
}

// =====================================================================================
// LOOP
// =====================================================================================
void loop() {
  // 1. รับคำสั่งจาก Python GUI (pwmMotor.py)
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (rx_buffer.length() > 0) {
        parseCommand(rx_buffer);
        rx_buffer = "";
      }
    } else {
      if (rx_buffer.length() < 32) {
        rx_buffer += c;
      }
    }
  }

  // 2. ส่ง Telemetry กลับไปยัง GUI ทุก 100 ms
  unsigned long current_millis = millis();
  if (current_millis - last_telemetry_tick >= 100) {
    unsigned long dt = current_millis - last_telemetry_tick;
    last_telemetry_tick = current_millis;

    long diff = enc_count - prev_enc_count;
    prev_enc_count = enc_count;

    if (abs(diff) > 2) {
      if (diff > 0) dir_str = "CW";
      else dir_str = "CCW";
      rpm = ((float)abs(diff) * 60000.0) / ((4.0 * ENCODER_PPR) * (float)dt);
    } else {
      if (duty_val > 0) {
        dir_str = "CW";
        rpm = ((float)duty_val * (float)MOTOR_MAX_RPM) / 100.0;
      } else {
        dir_str = "STOP";
        rpm = 0.0;
      }
    }

    // Telemetry: F:1000|D:<duty>|T:1.00|RPM:<rpm>|DIR:<dir>
    Serial.print(F("F:1000|D:"));
    Serial.print(duty_val);
    Serial.print(F("|T:1.00|RPM:"));
    Serial.print(rpm, 1);
    Serial.print(F("|DIR:"));
    Serial.println(dir_str);
  }
}

void parseCommand(String cmd) {
  cmd.trim();
  if (cmd.startsWith("D") || cmd.startsWith("d")) {
    applyDuty(cmd.substring(1).toInt());
  } else if (cmd.indexOf("D:") >= 0) {
    int idx = cmd.indexOf("D:");
    applyDuty(cmd.substring(idx + 2).toInt());
  } else if (isDigit(cmd.charAt(0))) {
    applyDuty(cmd.toInt());
  }
}
