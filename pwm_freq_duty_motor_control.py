"""
=============================================================================
  STM32 Motor Speed & Encoder Telemetry (Dual Frequency & PWM Duty Control)
  ไฟล์: pwm_freq_duty_motor_control.py
=============================================================================
คุณสมบัติ:
  1. ควบคุมทั้ง ความถี่ (Frequency: 100 Hz - 20,000 Hz) และ Duty Cycle (0 - 100%)
  2. แสดงผล Telemetry จาก STM32 แบบ Real-time ครบทั้ง 5 ค่า:
     - PWM Frequency (Hz / kHz)
     - PWM Duty Cycle (%)
     - PWM Period (ms)
     - Encoder RPM (ความเร็วรอบต่อนาที)
     - Measured Direction (ทิศทางการหมุนจริง: CW ↻ / CCW ↺ / STOP)
  3. แถบปุ่ม Quick Presets:
     - Frequency Presets: 500 Hz, 1 kHz, 2 kHz, 5 kHz, 10 kHz, 20 kHz
     - Duty Presets: 0%, 25%, 50%, 75%, 100%
     - ปุ่ม STOP MOTOR ฉุกเฉิน
  4. ระบบ Debounce Rate Limiting 50ms ป้องกันบัส Serial ล้น
  5. รูปแบบคำสั่งที่ส่งไป STM32: "F:<freq>|D:<duty>\\n"
=============================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import serial
import serial.tools.list_ports

BAUD = 115200


class DualPWMApp:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ STM32 Motor Dual Control (Frequency & Duty Cycle)")
        self.root.geometry("680x790")
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

        # ค่าควบคุม
        self.current_freq = 1000   # ความถี่เริ่มต้น 1,000 Hz
        self.current_duty = 0      # Duty เริ่มต้น 0 %

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
        tk.Label(header, text="⚙️ DUAL PWM & ENCODER MONITOR", font=("Segoe UI", 16, "bold"),
                 bg=self.BG_COLOR, fg=self.ACCENT_COLOR).pack()
        tk.Label(header, text="Dynamic Frequency (Hz) & Duty Cycle (%) Control", font=("Segoe UI", 9),
                 bg=self.BG_COLOR, fg="#8B949E").pack()

        # -------------------------------------------------------------
        # 1. Serial Connection
        # -------------------------------------------------------------
        conn_frame = ttk.LabelFrame(self.root, text=" 🔌 Serial Connection ", padding=10)
        conn_frame.pack(fill="x", padx=16, pady=4)

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
        # 2. Live Telemetry Cards (5 ค่าครบถ้วน)
        # -------------------------------------------------------------
        telemetry_frame = ttk.LabelFrame(self.root, text=" 📊 Live Telemetry (Measured by STM32) ", padding=10)
        telemetry_frame.pack(fill="x", padx=16, pady=4)

        cards_box = tk.Frame(telemetry_frame, bg=self.FRAME_BG)
        cards_box.pack(fill="x")

        # แถว 1: Frequency, Duty Cycle, Period
        self.create_metric_card(cards_box, "PWM Frequency", self.freq_var, "#58A6FF", 0, 0)
        self.create_metric_card(cards_box, "Duty Cycle", self.duty_disp_var, "#3FB950", 0, 1)
        self.create_metric_card(cards_box, "PWM Period", self.period_var, "#D29922", 0, 2)

        # แถว 2: RPM และ ทิศทางการหมุนจริง
        self.create_metric_card(cards_box, "Encoder Speed", self.rpm_var, "#A371F7", 1, 0, colspan=2)

        card_dir = tk.Frame(cards_box, bg=self.CARD_BG, bd=1, relief="ridge", padx=12, pady=8)
        card_dir.grid(row=1, column=2, padx=4, pady=5, sticky="nsew")
        tk.Label(card_dir, text="Measured Direction", font=("Segoe UI", 9, "bold"), bg=self.CARD_BG, fg="#8B949E").pack()
        self.lbl_dir = tk.Label(card_dir, textvariable=self.dir_var, font=("Consolas", 18, "bold"),
                                bg=self.CARD_BG, fg="#8B949E")
        self.lbl_dir.pack(pady=2)

        for col in range(3):
            cards_box.grid_columnconfigure(col, weight=1)

        # -------------------------------------------------------------
        # 3. Frequency Control Section (100 Hz - 20,000 Hz)
        # -------------------------------------------------------------
        freq_frame = ttk.LabelFrame(self.root, text=" 🎵 1. PWM Frequency Control (100 Hz - 20,000 Hz) ", padding=10)
        freq_frame.pack(fill="x", padx=16, pady=4)

        freq_header = tk.Frame(freq_frame, bg=self.FRAME_BG)
        freq_header.pack(fill="x")
        tk.Label(freq_header, text="Set Frequency (Hz):", font=("Segoe UI", 10, "bold"),
                 bg=self.FRAME_BG, fg=self.FG_COLOR).pack(side="left")
        self.lbl_freq_num = tk.Label(freq_header, text="1,000 Hz", font=("Consolas", 12, "bold"),
                                     bg=self.FRAME_BG, fg="#58A6FF")
        self.lbl_freq_num.pack(side="right")

        self.slider_freq = ttk.Scale(freq_frame, from_=100, to=20000, orient="horizontal", command=self.on_freq_move)
        self.slider_freq.set(1000)
        self.slider_freq.pack(fill="x", pady=6)
        self.slider_freq.bind("<ButtonRelease-1>", lambda e: self.send_commands())

        # ปุ่ม Presets ความถี่
        freq_preset_box = tk.Frame(freq_frame, bg=self.FRAME_BG)
        freq_preset_box.pack(fill="x", pady=(2, 2))
        tk.Label(freq_preset_box, text="Presets:", font=("Segoe UI", 9), bg=self.FRAME_BG, fg="#8B949E").pack(side="left", padx=(0, 6))

        for f_val, f_lbl in [(500, "500Hz"), (1000, "1kHz"), (2000, "2kHz"), (5000, "5kHz"), (10000, "10kHz"), (20000, "20kHz")]:
            btn = ttk.Button(freq_preset_box, text=f_lbl, style="Preset.TButton", width=7,
                             command=lambda f=f_val: self.set_freq_preset(f))
            btn.pack(side="left", padx=2)

        # -------------------------------------------------------------
        # 4. Duty Cycle Control Section (0 - 100%)
        # -------------------------------------------------------------
        duty_frame = ttk.LabelFrame(self.root, text=" 🎮 2. PWM Duty Cycle Control (0 - 100%) ", padding=10)
        duty_frame.pack(fill="x", padx=16, pady=4)

        duty_header = tk.Frame(duty_frame, bg=self.FRAME_BG)
        duty_header.pack(fill="x")
        tk.Label(duty_header, text="Set Duty Cycle (%):", font=("Segoe UI", 10, "bold"),
                 bg=self.FRAME_BG, fg=self.FG_COLOR).pack(side="left")
        self.lbl_duty_num = tk.Label(duty_header, text="0 %", font=("Consolas", 12, "bold"),
                                     bg=self.FRAME_BG, fg="#3FB950")
        self.lbl_duty_num.pack(side="right")

        self.slider_duty = ttk.Scale(duty_frame, from_=0, to=100, orient="horizontal", command=self.on_duty_move)
        self.slider_duty.set(0)
        self.slider_duty.pack(fill="x", pady=6)
        self.slider_duty.bind("<ButtonRelease-1>", lambda e: self.send_commands())

        # ปุ่ม Presets Duty Cycle
        duty_preset_box = tk.Frame(duty_frame, bg=self.FRAME_BG)
        duty_preset_box.pack(fill="x", pady=(2, 2))
        tk.Label(duty_preset_box, text="Presets:", font=("Segoe UI", 9), bg=self.FRAME_BG, fg="#8B949E").pack(side="left", padx=(0, 6))

        for duty in [0, 25, 50, 75, 100]:
            btn = ttk.Button(duty_preset_box, text=f"{duty}%", style="Preset.TButton", width=5,
                             command=lambda d=duty: self.set_duty_preset(d))
            btn.pack(side="left", padx=2)

        btn_stop = tk.Button(duty_preset_box, text="⏹ STOP (0%)", bg="#DA3633", fg="white",
                             font=("Segoe UI", 9, "bold"), padx=10, pady=2, command=self.stop_motor)
        btn_stop.pack(side="right")

        # -------------------------------------------------------------
        # 5. Telemetry Terminal Log
        # -------------------------------------------------------------
        log_frame = ttk.LabelFrame(self.root, text=" 📜 Telemetry Log Terminal ", padding=8)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        self.text_log = tk.Text(log_frame, height=4, font=("Consolas", 9),
                                bg="#0D1117", fg="#3FB950", insertbackground="white", relief="flat")
        self.text_log.pack(fill="both", expand=True)

        btn_clear = ttk.Button(log_frame, text="Clear Log", command=lambda: self.text_log.delete("1.0", "end"))
        btn_clear.pack(anchor="e", pady=(2, 0))

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
            self.send_commands()
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

    def on_freq_move(self, val):
        self.current_freq = int(float(val))
        self.lbl_freq_num.config(text=f"{self.current_freq:,} Hz")
        self.debounce_send()

    def set_freq_preset(self, freq):
        self.slider_freq.set(freq)
        self.current_freq = freq
        self.lbl_freq_num.config(text=f"{freq:,} Hz")
        self.send_commands()

    def on_duty_move(self, val):
        self.current_duty = int(float(val))
        self.lbl_duty_num.config(text=f"{self.current_duty} %")
        self.debounce_send()

    def set_duty_preset(self, duty):
        self.slider_duty.set(duty)
        self.current_duty = duty
        self.lbl_duty_num.config(text=f"{duty} %")
        self.send_commands()

    def stop_motor(self):
        self.set_duty_preset(0)

    def debounce_send(self):
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(50, self.send_commands)

    def send_commands(self):
        if self.ser and self.ser.is_open:
            # รูปแบบคำสั่ง: "F:<freq>|D:<duty>\n" เช่น "F:2000|D:50\n"
            cmd = f"F:{self.current_freq}|D:{self.current_duty}\n"
            try:
                self.ser.write(cmd.encode("utf-8"))
                self.log(f"PC -> MCU: {cmd.strip()}")
            except Exception as e:
                self.log(f"Error TX: {e}")
                self.disconnect_serial()

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
                for p in parts:
                    p = p.strip()
                    if p.startswith("F:"):
                        self.freq_var.set(f"{p[2:]} Hz")
                    elif p.startswith("D:"):
                        self.duty_disp_var.set(f"{p[2:]} %")
                    elif p.startswith("T:"):
                        self.period_var.set(f"{p[2:]} ms")
                    elif p.startswith("RPM:"):
                        self.rpm_var.set(f"{p[4:]} RPM")
                    elif p.startswith("DIR:"):
                        dir_str = p[4:].strip()
                        self.dir_var.set(dir_str)
                        if dir_str == "CW":
                            self.lbl_dir.config(fg="#3FB950", text="CW ↻")
                        elif dir_str == "CCW":
                            self.lbl_dir.config(fg="#58A6FF", text="CCW ↺")
                        else:
                            self.lbl_dir.config(fg="#8B949E", text="STOP")
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
    app = DualPWMApp(root)
    root.mainloop()
