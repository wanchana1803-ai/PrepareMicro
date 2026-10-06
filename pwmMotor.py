"""
=============================================================================
  STM32 Motor PWM Speed Control & Encoder Telemetry (RPM & Direction)
  ไฟล์: pwmMotor.py (โหมดควบคุมเฉพาะ Duty Cycle / PWM)
=============================================================================
คุณสมบัติ:
  1. ควบคุมความเร็วมอเตอร์ผ่าน PWM Duty Cycle (0 - 100%)
  2. แสดงผล Telemetry จาก STM32 แบบ Real-time ครบทั้ง 5 ค่า:
     - PWM Frequency (Hz)
     - PWM Duty Cycle (%)
     - PWM Period (ms)
     - Encoder RPM (ความเร็วรอบต่อนาที)
     - Measured Direction (ตรวจวัดทิศทางการหมุนจริง: CW ↻ / CCW ↺ / STOP)
  3. ปุ่ม Preset ความเร็วรวดเร็ว: 0%, 25%, 50%, 75%, 100% และปุ่ม STOP ฉุกเฉิน
  4. ระบบ Debounce Rate Limiting 50ms ป้องกันบัส Serial ล้น
  5. มอนิเตอร์ Serial Terminal พร้อมบันทึกคำสั่งและข้อมูลย้อนหลัง
=============================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import serial
import serial.tools.list_ports

BAUD = 115200


class PWMMotorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ STM32 Motor Speed & Encoder Telemetry (PWM Only)")
        self.root.geometry("640x700")
        self.root.resizable(False, False)

        # โทนสี Dark Engineering Theme
        self.BG_COLOR = "#0D1117"
        self.FG_COLOR = "#C9D1D9"
        self.ACCENT_COLOR = "#58A6FF"
        self.FRAME_BG = "#161B22"
        self.CARD_BG = "#21262D"

        self.root.configure(bg=self.BG_COLOR)
        self.ser = None
        self.running = False
        self.port = tk.StringVar()
        self.status = tk.StringVar(value="● DISCONNECTED")

        # ตัวแปรแสดงผล Telemetry
        self.freq_var = tk.StringVar(value="1000 Hz")
        self.duty_disp_var = tk.StringVar(value="0.0 %")
        self.period_var = tk.StringVar(value="1.00 ms")
        self.rpm_var = tk.StringVar(value="0.0 RPM")
        self.dir_var = tk.StringVar(value="STOP")

        self._after_id = None

        self.setup_styles()
        self.build_gui()
        self.refresh_ports()
        self.root.protocol("WM_DELETE_WINDOW", self.close_program)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background=self.BG_COLOR, foreground=self.FG_COLOR, font=('Segoe UI', 10))
        style.configure('TLabelframe', background=self.FRAME_BG, bordercolor='#30363D')
        style.configure('TLabelframe.Label', background=self.FRAME_BG, foreground=self.ACCENT_COLOR, font=('Segoe UI', 10, 'bold'))
        style.configure('TButton', background='#30363D', foreground=self.FG_COLOR, borderwidth=0)
        style.configure('Connect.TButton', background="#238636", font=('Segoe UI', 10, 'bold'), foreground="white")
        style.configure('Disconnect.TButton', background='#DA3633', font=('Segoe UI', 10, 'bold'), foreground="white")
        style.configure('Preset.TButton', background="#21262D", foreground="#58A6FF", font=('Segoe UI', 9, 'bold'))
        style.configure('TScale', background=self.FRAME_BG)

    def build_gui(self):
        # -------------------------------------------------------------
        # Header
        # -------------------------------------------------------------
        header = tk.Frame(self.root, bg=self.BG_COLOR)
        header.pack(fill="x", pady=(12, 4))
        tk.Label(header, text="⚙️ MOTOR SPEED & ENCODER MONITOR", font=("Segoe UI", 16, "bold"),
                 bg=self.BG_COLOR, fg=self.ACCENT_COLOR).pack()
        tk.Label(header, text="Duty Cycle Control Mode (D0 - D100)", font=("Segoe UI", 9),
                 bg=self.BG_COLOR, fg="#8B949E").pack()

        # -------------------------------------------------------------
        # 1. Serial Connection
        # -------------------------------------------------------------
        conn_frame = ttk.LabelFrame(self.root, text=" 🔌 Serial Connection ", padding=10)
        conn_frame.pack(fill="x", padx=16, pady=5)

        inner_conn = tk.Frame(conn_frame, bg=self.FRAME_BG)
        inner_conn.pack(fill="x")

        ttk.Label(inner_conn, text="COM Port:", background=self.FRAME_BG).grid(row=0, column=0, sticky="w", pady=4)
        self.combo = ttk.Combobox(inner_conn, textvariable=self.port, state="readonly", width=14)
        self.combo.grid(row=0, column=1, padx=8, pady=4)

        ttk.Button(inner_conn, text="↻ Scan", command=self.refresh_ports, width=8).grid(row=0, column=2, padx=4)

        ttk.Button(inner_conn, text="CONNECT", style="Connect.TButton", command=self.connect_serial, width=13).grid(row=0, column=3, padx=(10, 4))
        ttk.Button(inner_conn, text="DISCONNECT", style="Disconnect.TButton", command=self.disconnect_serial, width=13).grid(row=0, column=4, padx=4)

        self.status_label = tk.Label(conn_frame, textvariable=self.status, font=("Consolas", 9, "bold"),
                                     bg=self.FRAME_BG, fg="#F85149")
        self.status_label.pack(anchor="w", pady=(4, 0))

        # -------------------------------------------------------------
        # 2. Telemetry Cards (Live Monitoring)
        # -------------------------------------------------------------
        telemetry_frame = ttk.LabelFrame(self.root, text=" 📊 Live Telemetry (Measured by STM32) ", padding=10)
        telemetry_frame.pack(fill="x", padx=16, pady=5)

        cards_box = tk.Frame(telemetry_frame, bg=self.FRAME_BG)
        cards_box.pack(fill="x")

        # แถวที่ 1: PWM Telemetry (Frequency, Duty Cycle, Period)
        self.create_metric_card(cards_box, "PWM Frequency", self.freq_var, "#58A6FF", 0, 0)
        self.create_metric_card(cards_box, "Duty Cycle", self.duty_disp_var, "#3FB950", 0, 1)
        self.create_metric_card(cards_box, "PWM Period", self.period_var, "#D29922", 0, 2)

        # แถวที่ 2: Encoder Telemetry (RPM และ Measured Direction)
        self.create_metric_card(cards_box, "Encoder Speed", self.rpm_var, "#A371F7", 1, 0, colspan=2)

        # การ์ดแสดงทิศทางการหมุนที่วัดได้ (Measured Direction Card)
        card_dir = tk.Frame(cards_box, bg=self.CARD_BG, bd=1, relief="ridge", padx=12, pady=8)
        card_dir.grid(row=1, column=2, padx=4, pady=5, sticky="nsew")
        tk.Label(card_dir, text="Measured Direction", font=("Segoe UI", 9, "bold"), bg=self.CARD_BG, fg="#8B949E").pack()
        self.lbl_dir = tk.Label(card_dir, textvariable=self.dir_var, font=("Consolas", 18, "bold"),
                                bg=self.CARD_BG, fg="#8B949E")
        self.lbl_dir.pack(pady=2)

        for col in range(3):
            cards_box.grid_columnconfigure(col, weight=1)

        # -------------------------------------------------------------
        # 3. Motor Speed Control Slider (Duty Cycle 0 - 100%)
        # -------------------------------------------------------------
        ctrl_frame = ttk.LabelFrame(self.root, text=" 🎮 Motor Speed Control (Duty Cycle) ", padding=10)
        ctrl_frame.pack(fill="x", padx=16, pady=5)

        slider_box = tk.Frame(ctrl_frame, bg=self.FRAME_BG)
        slider_box.pack(fill="x", pady=4)

        slider_header = tk.Frame(slider_box, bg=self.FRAME_BG)
        slider_header.pack(fill="x")
        tk.Label(slider_header, text="Set Duty Cycle (0 - 100%):", font=("Segoe UI", 10, "bold"),
                 bg=self.FRAME_BG, fg=self.FG_COLOR).pack(side="left")
        self.lbl_slider_num = tk.Label(slider_header, text="0 %", font=("Consolas", 12, "bold"),
                                       bg=self.FRAME_BG, fg="#3FB950")
        self.lbl_slider_num.pack(side="right")

        self.slider = ttk.Scale(slider_box, from_=0, to=100, orient="horizontal", command=self.on_slider_move)
        self.slider.pack(fill="x", pady=6)
        self.slider.bind("<ButtonRelease-1>", lambda e: self.send_pwm(int(self.slider.get())))

        # แถบปุ่ม Quick Presets
        preset_box = tk.Frame(ctrl_frame, bg=self.FRAME_BG)
        preset_box.pack(fill="x", pady=(4, 6))
        tk.Label(preset_box, text="Quick Presets:", font=("Segoe UI", 9), bg=self.FRAME_BG, fg="#8B949E").pack(side="left", padx=(0, 6))

        for duty in [0, 25, 50, 75, 100]:
            btn = ttk.Button(preset_box, text=f"{duty}%", style="Preset.TButton", width=5,
                             command=lambda d=duty: self.set_preset(d))
            btn.pack(side="left", padx=2)

        btn_stop = tk.Button(preset_box, text="⏹ STOP (0%)", bg="#DA3633", fg="white",
                             font=("Segoe UI", 9, "bold"), padx=10, pady=2, command=self.stop_motor)
        btn_stop.pack(side="right")

        # -------------------------------------------------------------
        # 4. Serial Monitor Log
        # -------------------------------------------------------------
        log_frame = ttk.LabelFrame(self.root, text=" 📜 Telemetry Log Terminal ", padding=8)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        self.text_log = tk.Text(log_frame, height=5, font=("Consolas", 9),
                                bg="#0D1117", fg="#3FB950", insertbackground="white", relief="flat")
        self.text_log.pack(fill="both", expand=True)

        btn_clear = ttk.Button(log_frame, text="Clear Log", command=lambda: self.text_log.delete("1.0", "end"))
        btn_clear.pack(anchor="e", pady=(4, 0))

    def create_metric_card(self, parent, title, variable, text_color, row, col, colspan=1):
        card = tk.Frame(parent, bg=self.CARD_BG, bd=1, relief="ridge", padx=12, pady=8)
        card.grid(row=row, column=col, columnspan=colspan, padx=4, pady=5, sticky="nsew")
        tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), bg=self.CARD_BG, fg="#8B949E").pack()
        tk.Label(card, textvariable=variable, font=("Consolas", 18, "bold"),
                 bg=self.CARD_BG, fg=text_color).pack(pady=2)
        return card

    def refresh_ports(self):
        ports = list(serial.tools.list_ports.comports())
        self.combo["values"] = [p.device for p in ports]
        if ports:
            self.port.set(ports[-1].device)
        else:
            self.port.set("No Ports Found")

    def connect_serial(self):
        if not self.port.get() or self.port.get() == "No Ports Found":
            return
        try:
            self.ser = serial.Serial(self.port.get(), BAUD, timeout=0.1)
            time.sleep(1.0)
            self.ser.reset_input_buffer()
            self.running = True
            self.status.set(f"● CONNECTED : {self.port.get()} @ {BAUD}")
            self.status_label.config(fg="#3FB950")
            self.log("System : Connected to STM32")
            threading.Thread(target=self.serial_reader, daemon=True).start()
            self.send_pwm(int(self.slider.get()))
        except Exception as e:
            self.ser = None
            messagebox.showerror("Connection Error", str(e))

    def disconnect_serial(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = None
        self.status.set("● DISCONNECTED")
        self.status_label.config(fg="#F85149")
        self.log("System : Disconnected")

    def set_preset(self, duty):
        self.slider.set(duty)
        self.lbl_slider_num.config(text=f"{duty} %")
        self.send_pwm(duty)

    def on_slider_move(self, val):
        duty = float(val)
        self.lbl_slider_num.config(text=f"{int(duty)} %")
        # อัปเดตแสดงผลสดจากการคำนวณ (ไม่มีการ Fix ค่า)
        self.duty_disp_var.set(f"{duty:.1f} %")
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(50, lambda: self.send_pwm(int(duty)))

    def send_pwm(self, duty):
        if self.ser and self.ser.is_open:
            cmd = f"D{duty}\n"
            try:
                self.ser.write(cmd.encode("utf-8"))
                self.log(f"PC -> MCU: {cmd.strip()}")
            except Exception as e:
                self.log(f"Error TX: {e}")
                self.disconnect_serial()

    def stop_motor(self):
        self.set_preset(0)

    def serial_reader(self):
        while self.running and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode("utf-8", errors="replace").strip()
                if line:
                    self.root.after(0, self.parse_telemetry, line)
            except:
                break

    def parse_telemetry(self, line):
        self.log(f"MCU: {line}")
        try:
            if "|" in line:
                parts = line.split("|")
                rec_freq = None
                for p in parts:
                    p = p.strip()
                    if p.startswith("F:"):
                        rec_freq = float(p[2:])
                        self.freq_var.set(f"{rec_freq:.1f} Hz")
                    elif p.startswith("D:"):
                        self.duty_disp_var.set(f"{float(p[2:]):.1f} %")
                    elif p.startswith("RPM:"):
                        self.rpm_var.set(f"{float(p[4:]):.1f} RPM")
                    elif p.startswith("DIR:"):
                        dir_str = p[4:].strip()
                        self.dir_var.set(dir_str)
                        if dir_str == "CW":
                            self.lbl_dir.config(fg="#3FB950", text="CW ↻")
                        elif dir_str == "CCW":
                            self.lbl_dir.config(fg="#58A6FF", text="CCW ↺")
                        else:
                            self.lbl_dir.config(fg="#8B949E", text="STOP")

                # คำนวณ Period สดจากความถี่ T = 1000 / F (Dynamic Calculation)
                if rec_freq and rec_freq > 0:
                    dyn_period = 1000.0 / rec_freq
                    self.period_var.set(f"{dyn_period:.2f} ms")
        except Exception:
            pass

    def log(self, message):
        self.text_log.insert("end", message + "\n")
        self.text_log.see("end")

    def close_program(self):
        self.disconnect_serial()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PWMMotorApp(root)
    root.mainloop()