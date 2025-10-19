import time
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
import threading
import serial
from tkinter import messagebox
import serial.tools.list_ports


class Dashboard:
    def __init__(self, name):
        self.name = name
        self.dashboard = tk.Tk()
        self.dashboard.geometry("900x600+0+0")
        self.dashboard.title("PID tuner")
        self.dashboard.resizable(False, False)
        self.P_gain = 0
        self.I_gain = 0
        self.D_gain = 0
        self.S_point = 0
        self.yarr = []
        self.tarr = []
        self.port = None
        self.baudrate = "9600"
        self.connectivity_setting = "Serial"
        self.running = False
        self.show_dashboard()

    def show_dashboard(self):

        # PID CONTROL
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 12, "bold")
                        , foreground="white", background="#0078D7", padding=4)
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold")
                        , foreground="#FFB300")
        style.map("Custom.TButton",background=[("active", "darkgreen"), ("!active", "green")],
          foreground=[("pressed", "yellow"), ("active", "white")])
        style.map('Custom2.TButton', background=[("active", "darkorange"), ("!active", "orange")],
                  foreground=[("pressed", "yellow"), ("active", "white")])
        self.control_panel()
        self.dashboard.mainloop()

    def control_panel(self) -> None:
        Frame = ttk.LabelFrame(self.dashboard,text="PID CONTROL", borderwidth=2, relief="solid", height=100)
        Frame.pack(side="top", fill="x")
        Frame.pack_propagate(False)
        Frame.grid_propagate(False)
        Frame.rowconfigure(0, pad=10)
        Frame.columnconfigure(0, pad=10)

        #proportional
        P_gain = tk.IntVar()
        ttk.Label(Frame, text="KP:").grid(row=0,column=0, sticky="nw", pady=(20, 0), padx=(10, 0))
        ttk.Entry(Frame,textvariable=P_gain, width=10, font=("segoe UI", 10)).grid(column=1, row=0,sticky="n", pady=(20, 0))
        P_gain.set(0)


        #INTEGRAL
        I_gain = tk.IntVar()
        ttk.Label(Frame, text="KI:").grid(row=0,column=2, sticky="nw", pady=(20, 0), padx=(20, 0))
        ttk.Entry(Frame,textvariable=I_gain, width=10, font=("segoe UI", 10)).grid(column=3, row=0, sticky="n", pady=(20, 0) )
        I_gain.set(0)


        #INTEGRAL
        D_gain = tk.IntVar()
        ttk.Label(Frame, text="KD:").grid(row=0,column=4, sticky="n", pady=(20, 0), padx=(20, 0))
        ttk.Entry(Frame,textvariable=D_gain, width=10, font=("segoe UI", 10)).grid(column=5, row=0, sticky="n", pady=(20, 0))
        D_gain.set(0)

        #setpoint
        set_point = tk.IntVar()
        ttk.Label(Frame, text="SP:").grid(row=0,column=6, sticky="ne", pady=(20, 0), padx=(20, 0))
        ttk.Entry(Frame,textvariable=set_point, width=10, font=("segoe UI", 10)).grid(column=7, row=0, sticky="n", pady=(20, 0))
        set_point.set(0)
        #connectivity
        methods = ["BlueTooth", "WiFi", "Serial", "Http"]
        ttk.Label(Frame, text="CONNECTIVITY:").grid(row=0, column=8, sticky="n", pady=(20, 0), padx=(50, 0))
        connection = ttk.Combobox(Frame, values=methods)
        connection.grid(row=0, column=9, sticky="n", pady=(20, 0), padx=(20, 0))
        connection.current(2)
        connection.bind("<<ComboboxSelected>>", lambda event: [setattr(self, "connectivity_setting", connection.get()),self.show_setting(self.s_frame,connection.get())])

        #configure
        ttk.Button(Frame, text="CONFIG", state="active", command=lambda frame=Frame, kp=P_gain, ki=I_gain, kd=D_gain, sp=set_point : self.config(frame, kp, ki, kd,sp)).grid(row=0, column=10, sticky="e", padx=(20, 0),pady=(10,0))

        #graph sheet
        g_frame = ttk.LabelFrame(self.dashboard,text="STEP RESPONSE", width=500,height=100, relief="solid",  borderwidth="2" )
        g_frame.pack(side="left", fill="y")
        g_frame.pack_propagate(False)
        g_frame.grid_propagate(False)

        #setting
        s_frame = ttk.LabelFrame(self.dashboard, height=200, text="SETTINGS", width=400)
        s_frame.pack(side="top")
        s_frame.pack_propagate(False)
        s_frame.grid_propagate(False)
        self.s_frame = s_frame
        self.show_setting(s_frame,self.connectivity_setting)

        # DATA
        self.d_frame = ttk.LabelFrame(self.dashboard, height=222, text="DATA", width=400)
        self.d_frame.pack(side="top")
        self.d_frame.pack_propagate(False)
        self.d_frame.grid_propagate(False)
        overshoot = tk.IntVar()
        self.d_frame.grid_columnconfigure(0, pad=10)
        overshoot.set(0)
        ttk.Label(self.d_frame, text="Overshoot:").grid(row=0, column=0, padx=(50, 0), pady=(5,0))
        ttk.Entry(self.d_frame, textvariable=overshoot).grid(row=0, column=1, pady=(5,0))

        ttk.Label(self.d_frame, text="Rise time:").grid(row=1, column=0, padx=(50, 0), pady=(5,0))
        ttk.Entry(self.d_frame, textvariable=overshoot).grid(row=1, column=1, pady=(5,0))

        ttk.Label(self.d_frame, text="Steady-State Error:").grid(row=2, column=0, padx=(50, 0), pady=(5,0))
        ttk.Entry(self.d_frame, textvariable=overshoot).grid(row=2, column=1, pady=(5,0))

        ttk.Label(self.d_frame, text="Peak Time:").grid(row=3, column=0, padx=(50, 0), pady=(5,0))
        ttk.Entry(self.d_frame, textvariable=overshoot).grid(row=3, column=1, pady=(5,0))

        ttk.Label(self.d_frame, text="Settling Time:").grid(row=4, column=0, padx=(50, 0), pady=(5,0))
        ttk.Entry(self.d_frame, textvariable=overshoot).grid(row=4, column=1, pady=(5,0))


        #botton
        b_frame = ttk.Frame(self.dashboard, width=400, height=100)
        b_frame.pack(side="top")
        b_frame.pack_propagate(False)
        b_frame.grid_propagate(False)

        self.start_button = ttk.Button(b_frame, text="START", command=self.start)
        self.start_button.grid(row=0, column=0, pady=10,padx=50)

        ttk.Button(b_frame, text="STOP", command=self.stop).grid(row=0, column=1, pady=10)


        self.show_graph(g_frame)



    def show_graph(self, frame):
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("STEP RESPONSE")
        self.ax.set_ylabel("amplitude")
        self.ax.set_xlabel("time")
        # self.ax.yaxis.set_major_locator(MultipleLocator(0.1))
        # self.ax.xaxis.set_major_locator(MultipleLocator(0.1))
        self.ax.grid(True)
        x = []
        y = []

        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both")
        ttk.Button(frame, text="Analyze", style="Custom.TButton", command=self.analyze).pack(side="left", padx=(50,0))
        ttk.Button(frame, text="Clear", style="Custom2.TButton", command=self.clear).pack(side="right", padx=(0, 50))

    def show_setting(self,frame, connectivity):
        if connectivity == "Serial":
            self.serial_settings(frame)
        if connectivity == "WiFi":
            self.Wifi_settings(frame)
        if connectivity == "BlueTooth":
            self.bluetooth_settings(frame)
        if connectivity == "Http":
            self.http_settings(frame)

    def serial_settings(self, s_frame):
        for widgets in s_frame.winfo_children():
            widgets.destroy()
        baud_rates = [
            300,
            1200,
            2400,
            4800,
            9600,
            14400,
            19200,
            28800,
            38400,
            57600,
            115200,
            230400,
            460800,
            921600
        ]
        ttk.Label(s_frame, text="Baud rate:" ).grid(row=0, column=0, pady=10, padx=20)
        baud = ttk.Combobox(s_frame, justify="center", values=baud_rates)
        baud.current(4)
        baud.bind("<<ComboboxSelected>>", lambda event: setattr(self, "baudrate", baud.get()))
        baud.grid(row=0, column=1, pady=10)
        ports = [port.device for port in serial.tools.list_ports.comports()]
        ttk.Label(s_frame, text="COM PORT:").grid(row=1, column=0, pady=10, padx=20)


        port_c = ttk.Combobox(s_frame, values=ports, justify="center")

        port_c.bind("<<ComboboxSelected>>", lambda event: setattr(self, "port", port_c.get()))
        if ports:
            port_c.current(0)
            self.port = ports[0]
        else:
            port_c.set("No port available")
            self.port = None
        port_c.grid(row=1, column=1, pady=10)
        ttk.Button(s_frame, text="refresh", command=lambda frame = self.s_frame: self.serial_settings(frame)).grid(row=1, column=2, padx=10)

    def Wifi_settings(self, s_frame):
        for widget in s_frame.winfo_children():
            widget.destroy()
        ttk.Label(s_frame,text="wifi coming soon....", font=("segoe ui" ,12)).pack(side="top")


    def bluetooth_settings(self, s_frame):
            for widget in s_frame.winfo_children():
                widget.destroy()
            ttk.Label(s_frame,text=" bluetooth coming soon....", font=("segoe ui" ,12)).pack(side="top")


    def http_settings(self, s_frame):
          for widget in s_frame.winfo_children():
                widget.destroy()
          ttk.Label(s_frame,text="http coming soon....", font=("segoe ui" ,12)).pack(side="top")

    def start(self):
        if self.connectivity_setting == "Serial":
            self.yarr.clear()
            self.tarr.clear()
            self.running = True
            self.update_graph()
            threading.Thread(target=self.serial_update_data, daemon=True).start()




    def serial_update_data(self):
        try:
            self.mcu = serial.Serial(self.port, int(self.baudrate))
            time.sleep(1)
            if self.mcu.is_open:
                self.start_button.config(style="Custom.TButton")
                while self.running:
                    max_points = 2000
                    if self.mcu:
                        try:
                            data = self.mcu.readline().decode('utf-8').strip()
                            time.sleep(0.1)
                        except serial.SerialException:
                            break
                        try:
                            parts = data.split(",")
                            if len(parts) == 2:
                                self.yarr.append(float(parts[1]))
                                self.tarr.append(float(parts[0]))
                            if len(self.tarr) > max_points:
                                self.tarr.pop(0)
                                self.yarr.pop(0)

                        except ValueError:
                            pass
            else:
                self.mcu.close()
                messagebox.showinfo("port", serial.SerialException)

        except Exception as e:
            if hasattr(self, "mcu") and self.mcu.is_open:
                self.mcu.close()
            # messagebox.showerror("Error","Something went wrong!")
            messagebox.showerror("error",str(e))

    def stop(self):
        self.running = False
        self.start_button.config(style="TButton")
        if hasattr(self, "mcu") and self.mcu.is_open:
            self.mcu.close()

    def update_graph(self):
        if not self.running:
            return
        self.ax.cla()
        self.ax.set_title("STEP RESPONSE")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Amplitude")
        self.ax.grid(True)
        if self.yarr != None and self.tarr !=None:
            self.ax.plot(list(self.tarr), list(self.yarr), color="blue", marker=".")
        self.canvas.draw()
        self.dashboard.after(50, self.update_graph)

    def clear(self):
        self.stop()
        self.tarr.clear()
        self.yarr.clear()
        self.ax.cla()
        if hasattr(self, "mcu") and self.mcu.is_open:
            self.mcu.reset_input_buffer()
        self.ax.set_title("STEP RESPONSE")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Amplitude")
        self.ax.grid(True)
        self.canvas.draw()
        print(self.yarr)

    def analyze(self):
        self.stop()

        if not self.yarr or not self.tarr:
            messagebox.showinfo("No Data", "No data available to analyze!")
            return

        y = self.yarr
        t = self.tarr
        sp = self.S_point

        max_val = max(y)
        overshoot_val = max(0, max_val - sp)

        try:
            t_10 = next(ti for yi, ti in zip(y, t) if yi >= 0.1 * sp)
            t_90 = next(ti for yi, ti in zip(y, t) if yi >= 0.9 * sp)
            rise_time_val = t_90 - t_10
        except StopIteration:
            rise_time_val = 0



        steady_state_val = abs(y[-1] - sp)

        peak_time_val = t[y.index(max_val)]


        settling_val = 0
        for ti, yi in zip(t[::-1], y[::-1]):
            if abs(yi - sp) > 0.02 * sp:
                settling_val = ti
                break

        # Clear old widgets
        for widget in self.d_frame.winfo_children():
            widget.destroy()

        self.var_overshoot = tk.StringVar(value=f"{overshoot_val:.2f}")
        self.var_rise_time = tk.StringVar(value=f"{rise_time_val:.2f}")
        self.var_steady_state = tk.StringVar(value=f"{steady_state_val:.2f}")
        self.var_peak_time = tk.StringVar(value=f"{peak_time_val:.2f}")
        self.var_settling_time = tk.StringVar(value=f"{settling_val:.2f}")

        labels = ["Overshoot:", "Rise time:", "Steady-State Error:", "Peak Time:", "Settling Time:"]
        vars_ = [self.var_overshoot, self.var_rise_time, self.var_steady_state, self.var_peak_time,
                 self.var_settling_time]

        for i, (text, var) in enumerate(zip(labels, vars_)):
            ttk.Label(self.d_frame, text=text).grid(row=i, column=0, padx=(50, 0), pady=(5, 0))
            ttk.Entry(self.d_frame,state="readonly", textvariable=var).grid(row=i, column=1, pady=(5, 0))

    def config(self, frame, kp, ki, kd, sp):
        self.P_gain = kp.get()
        self.I_gain = ki.get()
        self.D_gain = kd.get()
        self.S_point = sp.get()
        if hasattr(self, "mcu") and self.mcu.is_open:
            self.mcu.write(f"{self.P_gain}:{self.I_gain}:{self.D_gain}:{self.S_point}\n".encode())
        else:
            messagebox.showerror("config", "no mcu available")



if __name__ == "__main__":
    dashboard = Dashboard("abel")