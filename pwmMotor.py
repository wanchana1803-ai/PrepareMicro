"""
=============================================================================
  STM32 Motor PWM & Rotary Encoder Telemetry Dashboard
  ไฟล์: pwmMotor.py
=============================================================================
คุณสมบัติ:
  1. ควบคุมความเร็วมอเตอร์ PWM (Duty Cycle 0 - 100%) พร้อมปุ่มทิศทาง (FWD/REV/STOP)
  2. แสดงผล Telemetry จาก STM32 แบบ Real-time ครบทั้ง 5 พารามิเตอร์:
     - PWM Frequency (Hz / kHz)
     - PWM Duty Cycle (%)
     - PWM Period (ms / µs)
     - Encoder RPM (ความเร็วรอบต่อนาที)
     - Encoder Direction (ทิศทางการหมุน CW / CCW / STOP)
  3. ระบบป้องกันบอร์ดค้าง (Debounce Rate-Limit 50ms)
  4. มอนิเตอร์ Serial Terminal พร้อมปุ่ม Clear Log
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
        self.root.title("⚡ STM32 Motor PWM & Encoder Telemetry")
        self.root.geometry("640x720")
        self.root.resizable(False, False)

        # กำหนดโทนสี Dark Engineering Theme
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

        self.slider_val = tk.IntVar(value=0)
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
        style.configure('TScale', background=self.FRAME_BG)

    def build_gui(self):
        # -------------------------------------------------------------
        # Header
        # -------------------------------------------------------------
        header = tk.Frame(self.root, bg=self.BG_COLOR)
        header.pack(fill="x", pady=(12, 4))
        tk.Label(header, text="⚙️ MOTOR PWM & ENCODER DASHBOARD", font=("Segoe UI", 16, "bold"),
                 bg=self.BG_COLOR, fg=self.ACCENT_COLOR).pack()

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
        telemetry_frame = ttk.LabelFrame(self.root, text=" 📊 Live Telemetry (From STM32) ", padding=10)
        telemetry_frame.pack(fill="x", padx=16, pady=5)

        cards_box = tk.Frame(telemetry_frame, bg=self.FRAME_BG)
        cards_box.pack(fill="x")

        # แถวบน: PWM Metrics (Frequency, Duty, Period)
        card_freq = self.create_metric_card(cards_box, "PWM Frequency", self.freq_var, "#58A6FF", 0, 0)
        card_duty = self.create_metric_card(cards_box, "Duty Cycle", self.duty_disp_var, "#3FB950", 0, 1)
        card_period = self.create_metric_card(cards_box, "PWM Period", self.period_var, "#D29922", 0, 2)

        # แถวล่าง: Encoder Metrics (RPM, Direction)
        card_rpm = self.create_metric_card(cards_box, "Encoder Speed", self.rpm_var, "#A371F7", 1, 0, colspan=2)

        # การ์ด Direction แสดงผลพิเศษ
        card_dir = tk.Frame(cards_box, bg=self.CARD_BG, bd=1, relief="ridge", padx=12, pady=8)
        card_dir.grid(row=1, column=2, padx=4, pady=5, sticky="nsew")
        tk.Label(card_dir, text="Direction", font=("Segoe UI", 9, "bold"), bg=self.CARD_BG, fg="#8B949E").pack()
        self.lbl_dir = tk.Label(card_dir, textvariable=self.dir_var, font=("Consolas", 18, "bold"),
                                bg=self.CARD_BG, fg="#8B949E")
        self.lbl_dir.pack(pady=2)

        for col in range(3):
            cards_box.grid_columnconfigure(col, weight=1)

        # -------------------------------------------------------------
        # 3. Motor Control Panel (PWM Duty Slider & Direction Buttons)
        # -------------------------------------------------------------
        ctrl_frame = ttk.LabelFrame(self.root, text=" 🎮 Motor Control Panel ", padding=10)
        ctrl_frame.pack(fill="x", padx=16, pady=5)

        # ปุ่มควบคุมทิศทาง (Forward / Reverse / Stop)
        dir_btn_box = tk.Frame(ctrl_frame, bg=self.FRAME_BG)
        dir_btn_box.pack(fill="x", pady=(2, 8))

        tk.Label(dir_btn_box, text="Direction Cmd:", font=("Segoe UI", 9, "bold"),
                 bg=self.FRAME_BG, fg=self.FG_COLOR).pack(side="left", padx=5)

        btn_fwd = tk.Button(dir_btn_box, text="⏩ FORWARD (CW)", bg="#238636", fg="white",
                            font=("Segoe UI", 9, "bold"), width=16, command=lambda: self.send_cmd("F\n"))
        btn_fwd.pack(side="left", padx=5)

        btn_rev = tk.Button(dir_btn_box, text="⏪ REVERSE (CCW)", bg="#1F6FEB", fg="white",
                            font=("Segoe UI", 9, "bold"), width=16, command=lambda: self.send_cmd("R\n"))
        btn_rev.pack(side="left", padx=5)

        btn_stop = tk.Button(dir_btn_box, text="⏹ STOP", bg="#DA3633", fg="white",
                             font=("Segoe UI", 9, "bold"), width=12, command=self.stop_motor)
        btn_stop.pack(side="left", padx=5)

        # สไลเดอร์ปรับความเร็ว Duty Cycle 0 - 100%
        slider_box = tk.Frame(ctrl_frame, bg=self.FRAME_BG)
        slider_box.pack(fill="x", pady=4)

        slider_header = tk.Frame(slider_box, bg=self.FRAME_BG)
        slider_header.pack(fill="x")
        tk.Label(slider_header, text="Motor Speed (Duty Cycle %):", font=("Segoe UI", 9, "bold"),
                 bg=self.FRAME_BG, fg=self.FG_COLOR).pack(side="left")
        self.lbl_slider_num = tk.Label(slider_header, text="0 %", font=("Consolas", 11, "bold"),
                                       bg=self.FRAME_BG, fg="#3FB950")
        self.lbl_slider_num.pack(side="right")

        self.slider = ttk.Scale(slider_box, from_=0, to=100, orient="horizontal", command=self.on_slider_move)
        self.slider.pack(fill="x", pady=4)
        self.slider.bind("<ButtonRelease-1>", lambda e: self.send_pwm(int(self.slider.get())))

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
            # ส่งค่าความเร็วเริ่มต้น
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

    def on_slider_move(self, val):
        duty = int(float(val))
        self.lbl_slider_num.config(text=f"{duty} %")
        # ระบบ Debounce Rate Limiting 50ms ป้องกันบัส Serial ล้น
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(50, lambda: self.send_pwm(duty))

    def send_pwm(self, duty):
        if self.ser and self.ser.is_open:
            cmd = f"D{duty}\n" # เช่น D75\n
            self.send_cmd(cmd)

    def stop_motor(self):
        self.slider.set(0)
        self.lbl_slider_num.config(text="0 %")
        self.send_cmd("S\n")

    def send_cmd(self, cmd_str):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(cmd_str.encode("utf-8"))
                self.log(f"PC -> MCU: {cmd_str.strip()}")
            except Exception as e:
                self.log(f"Error TX: {e}")
                self.disconnect_serial()

    def serial_reader(self):
        """ เธรดอ่านข้อมูล Telemetry อัตโนมัติจาก STM32 """
        while self.running and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode("utf-8", errors="replace").strip()
                if line:
                    self.root.after(0, self.parse_telemetry, line)
            except:
                break

    def parse_telemetry(self, line):
        """
        แยกวิเคราะห์ข้อมูลจาก STM32 รูปแบบมาตรฐาน:
        ตัวอย่าง: F:1000|D:75.0|T:1.00|RPM:320.5|DIR:CW
        """
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
    app = PWMMotorApp(root)
    root.mainloop()