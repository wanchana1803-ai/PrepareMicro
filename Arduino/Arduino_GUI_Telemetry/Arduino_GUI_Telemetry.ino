/*
 * =====================================================================================
 * Project: Arduino Universal GUI Telemetry Firmware (for Python GUI)
 * Compatible with:
 *   1. pwmMotor.py (Duty 0-100% at 1,000 Hz)
 *   2. pwm_freq_duty_motor_control.py (Dual Freq 500-1200 Hz & Duty 20-80%)
 * 
 * Communication: USB Serial (Baud Rate: 115200)
 * Telemetry Format (Sent every 100 ms):
 *   F:<freq>|D:<duty>|T:<period_ms>|RPM:<rpm>|DIR:<dir>\r\n
 * 
 * Hardware Pinout (Arduino Uno / Nano / Mega):
 * - PWM Output:       Pin 9 (Timer 1 OC1A, Fast PWM)
 * - Motor Encoder:    Phase A = Pin 2 (Interrupt INT0), Phase B = Pin 3
 * =====================================================================================
 */

#define PIN_PWM_OUT   9
#define PIN_ENC_A     2
#define PIN_ENC_B     3

#define MOTOR_MAX_RPM 1500
#define ENCODER_PPR   100

// --- ตัวแปร PWM ---
uint16_t freq_hz = 1000;     // ค่าเริ่มต้น 1000 Hz
uint16_t duty_val = 50;      // ค่าเริ่มต้น 50%
float period_ms = 1.00;
uint16_t top_val = 1999;
uint16_t comp_val = 1000;

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
// ตั้งค่า Hardware PWM Timer 1 บน Pin 9
// =====================================================================================
void setupPWM() {
#if defined(__AVR__)
  pinMode(PIN_PWM_OUT, OUTPUT);
  TCCR1A = _BV(COM1A1) | _BV(WGM11);            // Non-inverting Fast PWM Mode 14
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS11); // Prescaler = 8 (2 MHz)
  applyPWM(freq_hz, duty_val);
#else
  pinMode(PIN_PWM_OUT, OUTPUT);
  applyPWM(freq_hz, duty_val);
#endif
}

void applyPWM(uint16_t f, uint8_t d) {
  f = constrain(f, 100, 20000);
  d = constrain(d, 0, 100);

#if defined(__AVR__)
  top_val = (2000000UL / f) - 1;
  ICR1 = top_val;
  comp_val = ((unsigned long)(top_val + 1) * (unsigned long)d) / 100UL;
  OCR1A = comp_val;
#elif defined(ARDUINO_ARCH_STM32)
  analogWriteFrequency(f);
  analogWriteResolution(12);
  analogWrite(PIN_PWM_OUT, ((uint32_t)d * 4095UL) / 100UL);
#else
  analogWrite(PIN_PWM_OUT, map(d, 0, 100, 0, 255));
#endif
}

// =====================================================================================
// SETUP
// =====================================================================================
void setup() {
  Serial.begin(115200);

  setupPWM();

  pinMode(PIN_ENC_A, INPUT_PULLUP);
  pinMode(PIN_ENC_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), isr_encoder, RISING);
}

// =====================================================================================
// LOOP
// =====================================================================================
void loop() {
  // -----------------------------------------------------------------------------------
  // 1. รับคำสั่งจาก Python GUI ผ่าน Serial
  // -----------------------------------------------------------------------------------
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

  // -----------------------------------------------------------------------------------
  // 2. คำนวณความเร็วรอบและส่ง Telemetry ขึ้น GUI ทุก 100 ms
  // -----------------------------------------------------------------------------------
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

    period_ms = 1000.0 / (float)freq_hz;

    // รูปแบบ Telemetry: F:<freq>|D:<duty>|T:<t_ms>|RPM:<rpm>|DIR:<dir>
    Serial.print(F("F:"));
    Serial.print(freq_hz);
    Serial.print(F("|D:"));
    Serial.print(duty_val);
    Serial.print(F("|T:"));
    Serial.print(period_ms, 2);
    Serial.print(F("|RPM:"));
    Serial.print(rpm, 1);
    Serial.print(F("|DIR:"));
    Serial.println(dir_str);
  }
}

// =====================================================================================
// ถอดรหัสคำสั่งจาก Python GUI
// =====================================================================================
void parseCommand(String cmd) {
  cmd.trim();

  // รูปแบบที่ 1: "F:850|D:50" (มาจาก pwm_freq_duty_motor_control.py)
  int f_idx = cmd.indexOf("F:");
  int d_idx = cmd.indexOf("D:");

  if (f_idx >= 0 || d_idx >= 0) {
    if (f_idx >= 0) {
      int pipe_idx = cmd.indexOf('|', f_idx);
      String f_str = (pipe_idx > f_idx) ? cmd.substring(f_idx + 2, pipe_idx) : cmd.substring(f_idx + 2);
      uint16_t parsed_f = f_str.toInt();
      if (parsed_f >= 100 && parsed_f <= 20000) {
        freq_hz = parsed_f;
      }
    }
    if (d_idx >= 0) {
      String d_str = cmd.substring(d_idx + 2);
      uint16_t parsed_d = d_str.toInt();
      duty_val = constrain(parsed_d, 0, 100);
    }
    applyPWM(freq_hz, duty_val);
  }
  // รูปแบบที่ 2: "D75" (มาจาก pwmMotor.py)
  else if (cmd.startsWith("D") || cmd.startsWith("d")) {
    duty_val = constrain(cmd.substring(1).toInt(), 0, 100);
    applyPWM(freq_hz, duty_val);
  }
  // รูปแบบที่ 3: ตัวเลขล้วน "50"
  else if (isDigit(cmd.charAt(0))) {
    duty_val = constrain(cmd.toInt(), 0, 100);
    applyPWM(freq_hz, duty_val);
  }
}
