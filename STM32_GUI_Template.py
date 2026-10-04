"""
=============================================================================
  STM32 Universal Python GUI Template (Tkinter + PySerial)
  เหมาะสำหรับใช้ทำข้อสอบแล็ป Microcontroller / Project เชื่อมต่อ STM32
=============================================================================
ความสามารถในเทมเพลตนี้:
  1. สแกนหา COM Port อัตโนมัติ + เลือกระดับ Baud Rate (115200 / 9600)
  2. ปุ่ม Connect / Disconnect พร้อมไฟสถานะสีเขียว-แดง
  3. ปุ่มกดส่งคำสั่ง (LED ON / OFF, Button Controls)
  4. สไลเดอร์ (Slider/Scale) ปรับค่า PWM / Duty Cycle สดๆ
  5. กล่องป้อนข้อความ (Entry Box) ให้พิมพ์ค่าตัวเลขแล้วกดปุ่ม Send หรือกด Enter
  6. การ์ดแสดงผลค่า Real-time ขนาดใหญ่ (ADC Value, Voltage, Status)
  7. กล่องมอนิเตอร์ข้อความ (Serial Log Terminal) พร้อมปุ่ม Clear
  8. ทำงานแบบ Non-blocking ด้วย root.after() (หน้าจอไม่ค้าง ไม่กระตุก 100%)
=============================================================================
การติดตั้งไลบรารีก่อนรัน:
  pip install pyserial
=============================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports


class STM32_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("STM32 Universal GUI Controller")
        self.root.geometry("680x720")
        self.root.minsize(600, 650)

        # ตัวแปรระบบ Serial
        self.ser = None

        # ตัวแปรเก็บค่าต่างๆ ของ GUI
        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value="115200")
        self.status_var = tk.StringVar(value="DISCONNECTED")
        
        # ตัวแปรแสดงผล Real-time จาก STM32
        self.adc_val_var = tk.StringVar(value="----")
        self.volt_val_var = tk.StringVar(value="0.00 V")
        self.duty_disp_var = tk.StringVar(value="50.0 %")

        # สร้างหน้าต่างทั้งหมด
        self.create_widgets()

        # สแกนหาพอร์ตทันทีที่เปิดโปรแกรม
        self.scan_ports()

        # เริ่มต้นลูปตรวจจับและอ่านค่า Serial ทุก 50 ms
        self.root.after(50, self.read_serial_loop)

        # จัดการปิดพอร์ตเมื่อกดกากบาทปิดหน้าต่าง
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # =========================================================================
    # ส่วนที่ 1: วาดหน้าต่างและจัดวาง Layout (GUI Design)
    # =========================================================================
    def create_widgets(self):
        # -------------------------------------------------------------
        # กรอบที่ 1: เชื่อมต่อ COM Port
        # -------------------------------------------------------------
        frame_conn = ttk.LabelFrame(self.root, text=" 🔌 1. Serial Connection ", padding=10)
        frame_conn.pack(fill="x", padx=15, pady=8)

        # แถวที่ 1: เลือก COM Port และ Baud Rate
        ttk.Label(frame_conn, text="COM Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.cb_ports = ttk.Combobox(frame_conn, textvariable=self.port_var, width=15, state="readonly")
        self.cb_ports.grid(row=0, column=1, padx=5, pady=5)

        btn_refresh = ttk.Button(frame_conn, text="🔄 Scan", width=8, command=self.scan_ports)
        btn_refresh.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(frame_conn, text="Baud Rate:").grid(row=0, column=3, padx=(15, 5), pady=5, sticky="w")
        cb_baud = ttk.Combobox(frame_conn, textvariable=self.baud_var, width=10, state="readonly",
                               values=["9600", "19200", "38400", "57600", "115200"])
        cb_baud.grid(row=0, column=4, padx=5, pady=5)

        # แถวที่ 2: ปุ่ม Connect และป้ายสถานะ
        self.btn_connect = tk.Button(frame_conn, text="CONNECT", bg="#28a745", fg="white",
                                     font=("Arial", 10, "bold"), width=14, command=self.toggle_connect)
        self.btn_connect.grid(row=1, column=1, padx=5, pady=8)

        self.lbl_status = tk.Label(frame_conn, textvariable=self.status_var, font=("Arial", 10, "bold"),
                                   fg="#dc3545", bg="#f8f9fa", padx=10, relief="solid", bd=1)
        self.lbl_status.grid(row=1, column=2, columnspan=3, padx=10, pady=8, sticky="w")

        # -------------------------------------------------------------
        # กรอบที่ 2: แสดงผลค่า Real-time (Display Cards)
        # -------------------------------------------------------------
        frame_disp = ttk.LabelFrame(self.root, text=" 📊 2. Live Monitoring (From STM32) ", padding=10)
        frame_disp.pack(fill="x", padx=15, pady=8)

        # การ์ดที่ 1: ADC Value
        card_adc = tk.Frame(frame_disp, bg="#e9ecef", bd=2, relief="groove", padx=15, pady=10)
        card_adc.pack(side="left", expand=True, fill="both", padx=5)
        tk.Label(card_adc, text="ADC (Raw)", font=("Arial", 10, "bold"), bg="#e9ecef", fg="#495057").pack()
        tk.Label(card_adc, textvariable=self.adc_val_var, font=("Arial", 22, "bold"), bg="#e9ecef", fg="#007bff").pack(pady=4)
        tk.Label(card_adc, text="Range: 0 - 4095", font=("Arial", 8), bg="#e9ecef", fg="#6c757d").pack()

        # การ์ดที่ 2: Calculated Voltage
        card_volt = tk.Frame(frame_disp, bg="#e9ecef", bd=2, relief="groove", padx=15, pady=10)
        card_volt.pack(side="left", expand=True, fill="both", padx=5)
        tk.Label(card_volt, text="Voltage", font=("Arial", 10, "bold"), bg="#e9ecef", fg="#495057").pack()
        tk.Label(card_volt, textvariable=self.volt_val_var, font=("Arial", 22, "bold"), bg="#e9ecef", fg="#28a745").pack(pady=4)
        tk.Label(card_volt, text="Range: 0.0 - 3.3 V", font=("Arial", 8), bg="#e9ecef", fg="#6c757d").pack()

        # การ์ดที่ 3: Duty Cycle Display
        card_duty = tk.Frame(frame_disp, bg="#e9ecef", bd=2, relief="groove", padx=15, pady=10)
        card_duty.pack(side="left", expand=True, fill="both", padx=5)
        tk.Label(card_duty, text="Duty Cycle", font=("Arial", 10, "bold"), bg="#e9ecef", fg="#495057").pack()
        tk.Label(card_duty, textvariable=self.duty_disp_var, font=("Arial", 22, "bold"), bg="#e9ecef", fg="#fd7e14").pack(pady=4)
        tk.Label(card_duty, text="Target: 0% - 100%", font=("Arial", 8), bg="#e9ecef", fg="#6c757d").pack()

        # -------------------------------------------------------------
        # กรอบที่ 3: ส่งคำสั่งไปยัง STM32 (Controls)
        # -------------------------------------------------------------
        frame_ctrl = ttk.LabelFrame(self.root, text=" 🎮 3. Control Panel (Send to STM32) ", padding=10)
        frame_ctrl.pack(fill="x", padx=15, pady=8)

        # 3.1 ปุ่มกดคำสั่งเปิด-ปิด (Buttons)
        btn_box = ttk.Frame(frame_ctrl)
        btn_box.pack(fill="x", pady=5)
        
        ttk.Label(btn_box, text="LED Command:").pack(side="left", padx=5)
        btn_led_on = tk.Button(btn_box, text="💡 LED ON", bg="#28a745", fg="white", font=("Arial", 9, "bold"),
                               width=12, command=lambda: self.send_command("1"))
        btn_led_on.pack(side="left", padx=8)

        btn_led_off = tk.Button(btn_box, text="⚫ LED OFF", bg="#dc3545", fg="white", font=("Arial", 9, "bold"),
                                width=12, command=lambda: self.send_command("0"))
        btn_led_off.pack(side="left", padx=8)

        btn_toggle = tk.Button(btn_box, text="🔄 TOGGLE", bg="#ffc107", fg="black", font=("Arial", 9, "bold"),
                               width=12, command=lambda: self.send_command("T"))
        btn_toggle.pack(side="left", padx=8)

        # 3.2 สไลเดอร์ปรับค่า PWM (Slider / Scale)
        slider_box = ttk.Frame(frame_ctrl)
        slider_box.pack(fill="x", pady=(10, 5))

        ttk.Label(slider_box, text="PWM Duty Cycle (0 - 1000):").pack(anchor="w", padx=5)
        self.slider_pwm = tk.Scale(slider_box, from_=0, to=1000, orient="horizontal",
                                   resolution=10, showvalue=True, command=self.on_slider_change)
        self.slider_pwm.set(500) # ค่าเริ่มต้น 50%
        self.slider_pwm.pack(fill="x", padx=5, pady=2)

        # 3.3 กล่องป้อนข้อความ (Entry Box)
        entry_box = ttk.Frame(frame_ctrl)
        entry_box.pack(fill="x", pady=8)

        ttk.Label(entry_box, text="Send Custom String:").pack(side="left", padx=5)
        self.txt_entry = ttk.Entry(entry_box, width=28)
        self.txt_entry.pack(side="left", padx=5)
        self.txt_entry.bind("<Return>", lambda event: self.send_entry_text()) # กด Enter ส่งได้เลย

        btn_send = ttk.Button(entry_box, text="Send ↵", command=self.send_entry_text)
        btn_send.pack(side="left", padx=5)

        # -------------------------------------------------------------
        # กรอบที่ 4: กล่องมอนิเตอร์ข้อความ (Serial Log Terminal)
        # -------------------------------------------------------------
        frame_log = ttk.LabelFrame(self.root, text=" 📜 4. Serial Monitor / Log ", padding=10)
        frame_log.pack(fill="both", expand=True, padx=15, pady=8)

        self.txt_log = scrolledtext.ScrolledText(frame_log, height=8, wrap="none", bg="#212529", fg="#00ff66",
                                                 font=("Consolas", 10))
        self.txt_log.pack(fill="both", expand=True, pady=5)

        btn_clear = ttk.Button(frame_log, text="Clear Log", command=self.clear_log)
        btn_clear.pack(anchor="e")

    # =========================================================================
    # ส่วนที่ 2: ฟังก์ชันจัดการ Serial (Connect / Read / Write)
    # =========================================================================
    def scan_ports(self):
        """ ค้นหาพอร์ต COM ที่เชื่อมต่ออยู่ """
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.cb_ports["values"] = ports
        if ports:
            self.cb_ports.current(0)
            self.log_message(f"Found COM Ports: {', '.join(ports)}")
        else:
            self.port_var.set("")
            self.log_message("No COM Ports found!")

    def toggle_connect(self):
        """ สลับสถานะ เชื่อมต่อ / ตัดการเชื่อมต่อ """
        if self.ser and self.ser.is_open:
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        port = self.port_var.get()
        baud = self.baud_var.get()

        if not port:
            messagebox.showwarning("Warning", "Please select a COM Port first!")
            return

        try:
            # เปิดพอร์ต Serial
            self.ser = serial.Serial(port, int(baud), timeout=0.05)
            self.status_var.set(f"CONNECTED ({port} @ {baud})")
            self.lbl_status.config(fg="#28a745")
            self.btn_connect.config(text="DISCONNECT", bg="#dc3545")
            self.log_message(f"=== Successfully Connected to {port} at {baud} bps ===")
        except Exception as e:
            self.ser = None
            messagebox.showerror("Connection Error", f"Failed to open {port}:\n{str(e)}")
            self.status_var.set("CONNECTION FAILED")
            self.lbl_status.config(fg="#dc3545")

    def disconnect_serial(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.status_var.set("DISCONNECTED")
        self.lbl_status.config(fg="#dc3545")
        self.btn_connect.config(text="CONNECT", bg="#28a745")
        self.log_message("=== Disconnected from Port ===")

    def send_command(self, cmd_str):
        """ ส่งข้อความ 1 คำสั่งไปยัง STM32 """
        if self.ser and self.ser.is_open:
            try:
                # เติม \r\n หรือส่งตัวเดียวตามที่ STM32 ออกแบบไว้
                msg = f"{cmd_str}\r\n".encode("utf-8")
                self.ser.write(msg)
                self.log_message(f"[PC -> STM32]: {cmd_str}")
            except Exception as e:
                self.log_message(f"[ERROR SEND]: {str(e)}")
                self.disconnect_serial()
        else:
            messagebox.showwarning("Not Connected", "Please connect to STM32 first!")

    def send_entry_text(self):
        """ ดึงข้อความจาก Entry Box แล้วสั่งส่ง """
        text = self.txt_entry.get().strip()
        if text:
            self.send_command(text)
            self.txt_entry.delete(0, tk.END)

    def on_slider_change(self, val):
        """ เมื่อเลื่อน Slider ให้ส่งค่า PWM เช่น P500 """
        # สามารถแปลงข้อความส่งตามโปรโตคอลที่ต้องการ เช่น "P500" หรือส่งตัวเลขตรงๆ
        if self.ser and self.ser.is_open:
            self.send_command(f"P{val}")

    def read_serial_loop(self):
        """ ลูปอ่านข้อมูลอัตโนมัติจาก STM32 โดยไม่ทำให้ UI ค้าง """
        if self.ser and self.ser.is_open:
            try:
                while self.ser.in_waiting > 0:
                    raw_line = self.ser.readline().decode("utf-8", errors="replace").strip()
                    if raw_line:
                        self.log_message(f"[STM32]: {raw_line}")
                        self.parse_incoming_data(raw_line)
            except Exception as e:
                self.log_message(f"[ERROR READ]: {str(e)}")
                self.disconnect_serial()

        # สั่งให้วนลูปมาตรวจอ่านข้อมูลใหม่ทุกๆ 50 ms
        self.root.after(50, self.read_serial_loop)

    def parse_incoming_data(self, line):
        """
        แยกวิเคราะห์ข้อมูลที่ได้รับจาก STM32 เพื่ออัปเดตขึ้นหน้าจอ:
        ตัวอย่างรูปแบบข้อมูลที่ STM32 ส่งมา:
          แบบ 1: ตัวเลขเพียวๆ เช่น "2048"
          แบบ 2: ข้อความคั่นด้วยจุลภาค เช่น "ADC:2048,DUTY:50.0"
        """
        try:
            # 1. กรณีส่งเป็นข้อความคีย์เวิร์ด
            if "ADC:" in line:
                # ดึงตัวเลขหลังคำว่า ADC:
                parts = line.split("|") if "|" in line else line.split(",")
                for p in parts:
                    p = p.strip()
                    if p.startswith("ADC:"):
                        adc_val = int(p.replace("ADC:", "").strip())
                        self.update_adc_display(adc_val)
                    elif "Duty:" in p:
                        duty_str = p.replace("Duty:", "").strip()
                        self.duty_disp_var.set(duty_str)

            # 2. กรณีส่งตัวเลขเพียวๆ บรรทัดละ 1 ค่า เช่น "3050"
            elif line.isdigit():
                adc_val = int(line)
                self.update_adc_display(adc_val)

        except Exception:
            pass # ถ้าข้อความทั่วไป แปลงไม่สำเร็จก็ปล่อยผ่าน ไม่ให้โปรแกรมแครช

    def update_adc_display(self, adc_val):
        """ คำนวณค่าแรงดันและอัปเดตการ์ดแสดงผล """
        self.adc_val_var.set(f"{adc_val}")
        volt = (adc_val * 3.3) / 4095.0
        self.volt_val_var.set(f"{volt:.2f} V")

    def log_message(self, msg):
        """ พิมพ์ข้อความลงในกล่อง Log Terminal และเลื่อนหน้าจอลงล่างสุด """
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)

    def clear_log(self):
        self.txt_log.delete("1.0", tk.END)

    def on_closing(self):
        """ ปิดพอร์ตอย่างปลอดภัยเมื่อปิดหน้าต่าง """
        self.disconnect_serial()
        self.root.destroy()


# =============================================================================
# จุดเริ่มต้นรันโปรแกรม (Main Entry)
# =============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    # กำหนดไอคอนหรือสไตล์ตามต้องการ
    app = STM32_GUI(root)
    root.mainloop()
