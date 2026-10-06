"""
=============================================================================
  STM32 Motor Speed & Encoder Telemetry (Single Slider Dual Control)
  ไฟล์: pwm_freq_duty_motor_control.py
=============================================================================
คุณสมบัติ:
  1. ใช้ Slider ตัวเดียวควบคุมพร้อมกันทั้ง:
     - Frequency (ความถี่): 500 Hz ถึง 1,200 Hz
     - Duty Cycle (ความกว้างพัลส์): 20% ถึง 80%
  2. สูตรการแปลงเชิงเส้น (Linear Mapping):
     - ที่ Slider 0%   -> F = 500 Hz,   Duty = 20% (Period = 2.00 ms)
     - ที่ Slider 50%  -> F = 850 Hz,   Duty = 50% (Period = 1.18 ms)
     - ที่ Slider 100% -> F = 1,200 Hz, Duty = 80% (Period = 0.83 ms)
  3. แสดงผล Telemetry จาก STM32 แบบ Real-time ครบทั้ง 5 ค่า:
     - PWM Frequency (Hz)
     - PWM Duty Cycle (%)
     - PWM Period (ms)
     - Encoder RPM (ความเร็วรอบต่อนาที)
     - Measured Direction (ทิศทางการหมุนจริง: CW ↻ / CCW ↺ / STOP)
  4. ปุ่ม Quick Presets: 0% (Min), 25%, 50% (Mid), 75%, 100% (Max) และปุ่ม STOP ฉุกเฉิน
  5. ระบบ Debounce Rate Limiting 50ms ป้องกันบัส Serial ล้น
  6. คำสั่งส่งไปยัง STM32: "F:<freq>|D:<duty>\n" เช่น "F:500|D:20\n"
=============================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import serial
import serial.tools.list_ports

BAUD = 115200

# ขอบเขตตามโจทย์
FREQ_MIN = 500       # 500 Hz
FREQ_MAX = 1200      # 1,200 Hz
DUTY_MIN = 20        # 20 %
DUTY_MAX = 80        # 80 %


class SingleSliderDualControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ STM32 Single Slider (Freq 500-1200Hz & Duty 20-80%)")
        self.root.geometry("680x760")
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

        # ค่าควบคุมปัจจุบัน
        self.slider_pos = 0          # ตำแหน่ง 0 - 100 %
        self.target_freq = FREQ_MIN  # 500 Hz
        self.target_duty = DUTY_MIN  # 20 %

        # ตัวแปรแสดงผล Telemetry จาก STM32
        self.freq_var = tk.StringVar(value="500 Hz")
        self.duty_disp_var = tk.StringVar(value="20.0 %")
        self.period_var = tk.StringVar(value="2.00 ms")
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
        tk.Label(header, text="⚙️ SINGLE SLIDER DUAL CONTROL", font=("Segoe UI", 16, "bold"),
                 bg=self.BG_COLOR, fg=self.ACCENT_COLOR).pack()
        tk.Label(header, text="Duty: 20% - 80%  |  Frequency: 500 Hz - 1,200 Hz", font=("Segoe UI", 10, "bold"),
                 bg=self.BG_COLOR, fg="#7EE787").pack()

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
        # 3. Single Slider Control Section (Master Slider)
        # -------------------------------------------------------------
        ctrl_frame = ttk.LabelFrame(self.root, text=" 🎛️ Single Slider Dual Controller ", padding=12)
        ctrl_frame.pack(fill="x", padx=16, pady=5)

        # แถวแสดงผลค่าที่กำลังตั้ง (Calculated Targets)
        disp_box = tk.Frame(ctrl_frame, bg=self.FRAME_BG)
        disp_box.pack(fill="x", pady=(0, 6))

        # Target Frequency Display
        box_f = tk.Frame(disp_box, bg=self.CARD_BG, padx=8, pady=6, relief="ridge", bd=1)
        box_f.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(box_f, text="Target Frequency", font=("Segoe UI", 8, "bold"), bg=self.CARD_BG, fg="#8B949E").pack()
        self.lbl_target_freq = tk.Label(box_f, text="500 Hz", font=("Consolas", 14, "bold"), bg=self.CARD_BG, fg="#58A6FF")
        self.lbl_target_freq.pack()

        # Slider Position %
        box_pos = tk.Frame(disp_box, bg=self.CARD_BG, padx=8, pady=6, relief="ridge", bd=1)
        box_pos.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(box_pos, text="Slider Position", font=("Segoe UI", 8, "bold"), bg=self.CARD_BG, fg="#8B949E").pack()
        self.lbl_target_pos = tk.Label(box_pos, text="0 %", font=("Consolas", 14, "bold"), bg=self.CARD_BG, fg="#F0883E")
        self.lbl_target_pos.pack()

        # Target Duty Display
        box_d = tk.Frame(disp_box, bg=self.CARD_BG, padx=8, pady=6, relief="ridge", bd=1)
        box_d.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(box_d, text="Target Duty Cycle", font=("Segoe UI", 8, "bold"), bg=self.CARD_BG, fg="#8B949E").pack()
        self.lbl_target_duty = tk.Label(box_d, text="20 %", font=("Consolas", 14, "bold"), bg=self.CARD_BG, fg="#3FB950")
        self.lbl_target_duty.pack()

        # The Single Master Slider (0 to 100)
        self.slider = ttk.Scale(ctrl_frame, from_=0, to=100, orient="horizontal", command=self.on_slider_move)
        self.slider.set(0)
        self.slider.pack(fill="x", pady=(10, 4))
        self.slider.bind("<ButtonRelease-1>", lambda e: self.send_commands())

        # สเกลกำกับด้านล่าง Slider
        ticks_frame = tk.Frame(ctrl_frame, bg=self.FRAME_BG)
        ticks_frame.pack(fill="x", pady=(0, 8))
        tk.Label(ticks_frame, text="◀ Min: 500 Hz | Duty 20%", font=("Segoe UI", 8), bg=self.FRAME_BG, fg="#8B949E").pack(side="left")
        tk.Label(ticks_frame, text="Mid: 850 Hz | Duty 50%", font=("Segoe UI", 8), bg=self.FRAME_BG, fg="#8B949E").pack(side="left", expand=True)
        tk.Label(ticks_frame, text="Max: 1,200 Hz | Duty 80% ▶", font=("Segoe UI", 8), bg=self.FRAME_BG, fg="#8B949E").pack(side="right")

        # Quick Presets Buttons
        preset_box = tk.Frame(ctrl_frame, bg=self.FRAME_BG)
        preset_box.pack(fill="x", pady=(2, 2))
        tk.Label(preset_box, text="Presets:", font=("Segoe UI", 9, "bold"), bg=self.FRAME_BG, fg="#8B949E").pack(side="left", padx=(0, 6))

        presets = [
            (0, "Min (20% | 500Hz)"),
            (25, "25% (35% | 675Hz)"),
            (50, "Mid (50% | 850Hz)"),
            (75, "75% (65% | 1025Hz)"),
            (100, "Max (80% | 1200Hz)")
        ]
        for pos, label in presets:
            btn = ttk.Button(preset_box, text=f"{pos}%", style="Preset.TButton", width=5,
                             command=lambda p=pos: self.set_preset(p))
            btn.pack(side="left", padx=2)

        btn_stop = tk.Button(preset_box, text="⏹ STOP (0%)", bg="#DA3633", fg="white",
                             font=("Segoe UI", 9, "bold"), padx=10, pady=2, command=self.stop_motor)
        btn_stop.pack(side="right")

        # -------------------------------------------------------------
        # 4. Telemetry Terminal Log
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

    def on_slider_move(self, val):
        self.slider_pos = int(float(val))
        # คำนวณตามสูตร Linear Mapping:
        # Freq: 500 ถึง 1,200 Hz
        self.target_freq = int(FREQ_MIN + (self.slider_pos / 100.0) * (FREQ_MAX - FREQ_MIN))
        # Duty: 20% ถึง 80%
        self.target_duty = int(round(DUTY_MIN + (self.slider_pos / 100.0) * (DUTY_MAX - DUTY_MIN)))

        # อัปเดตตัวเลขแสดงผลบน UI
        self.lbl_target_pos.config(text=f"{self.slider_pos} %")
        self.lbl_target_freq.config(text=f"{self.target_freq:,} Hz")
        self.lbl_target_duty.config(text=f"{self.target_duty} %")

        # Debounce ส่งข้อมูล 50ms ป้องกันบัส Serial ล้น
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(50, self.send_commands)

    def set_preset(self, pos):
        self.slider.set(pos)
        self.on_slider_move(pos)
        self.send_commands()

    def stop_motor(self):
        # สั่งหยุดมอเตอร์ Duty = 0%
        self.target_duty = 0
        self.lbl_target_duty.config(text="0 % (STOP)")
        if self.ser and self.ser.is_open:
            cmd = f"F:{self.target_freq}|D:0\n"
            try:
                self.ser.write(cmd.encode("utf-8"))
                self.log(f"PC -> MCU: {cmd.strip()} (EMERGENCY STOP)")
            except Exception as e:
                self.log(f"Error TX: {e}")

    def send_commands(self):
        if self.ser and self.ser.is_open:
            # คำสั่งคู่: "F:<freq>|D:<duty>\n" เช่น "F:850|D:50\n"
            cmd = f"F:{self.target_freq}|D:{self.target_duty}\n"
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
    app = SingleSliderDualControlApp(root)
    root.mainloop()
