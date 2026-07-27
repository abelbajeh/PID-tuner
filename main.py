import time
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
import threading
import serial
import queue
from tkinter import messagebox
import serial.tools.list_ports
import websocket
import json
import socket


class Dashboard:
    def __init__(self, name):
        self.name = name
        self.dashboard = tk.Tk()
        self.dashboard.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.dashboard.geometry("900x600+0+0")
        self.dashboard.title("PID tuner")
        self.dashboard.resizable(False, False)
        self.P_gain = 0
        self.I_gain = 0
        self.D_gain = 0
        self.S_point = 0
        self.data_queue = queue.Queue(maxsize=2000)
        self.max_points = 500
        self.yarr = []
        self.tarr = []
        self.port = None
        self.baudrate = "9600"
        self.connectivity_setting = "Serial"
        self.running = False
        # UDP state (used by the new "UDP" connectivity option)
        self.udp_sock = None
        self.udp_remote = None
        self.udp_connected = False
        # Tracks which connection is actually live, independent of whatever
        # self.connectivity_setting currently is. Needed because the
        # connectivity combobox switches self.connectivity_setting *before*
        # calling stop(), so stop() used to close the wrong connection type
        # when you switched dropdowns mid-run.
        self.active_connection = None
        # Local wall-clock reference used to generate the x-axis timestamp,
        # since the current (unmodified) firmware only sends a bare angle
        # value with no time field of its own.
        self.stream_start_time = None
        self.show_dashboard()

    def show_dashboard(self):

        # PID CONTROL
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 12, "bold")
                        , foreground="white", background="#0078D7", padding=4)
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold")
                        , foreground="#FFB300")
        style.map("Custom.TButton", background=[("active", "darkgreen"), ("!active", "green")],
                  foreground=[("pressed", "yellow"), ("active", "white")])
        style.map('Custom2.TButton', background=[("active", "darkorange"), ("!active", "orange")],
                  foreground=[("pressed", "yellow"), ("active", "white")])
        self.control_panel()
        self.dashboard.mainloop()

    def control_panel(self) -> None:
        Frame = ttk.LabelFrame(self.dashboard, text="PID CONTROL", borderwidth=2, relief="solid", height=100)
        Frame.pack(side="top", fill="x")
        Frame.pack_propagate(False)
        Frame.grid_propagate(False)
        Frame.rowconfigure(0, pad=10)
        Frame.columnconfigure(0, pad=10)

        # proportional
        P_gain = tk.StringVar()
        ttk.Label(Frame, text="KP:").grid(row=0, column=0, sticky="nw", pady=(20, 0), padx=(10, 0))
        ttk.Entry(Frame, textvariable=P_gain, width=10, font=("segoe UI", 10)).grid(column=1, row=0, sticky="n",
                                                                                    pady=(20, 0))
        P_gain.set("0")
        # INTEGRAL
        I_gain = tk.StringVar()
        ttk.Label(Frame, text="KI:").grid(row=0, column=2, sticky="nw", pady=(20, 0), padx=(20, 0))
        ttk.Entry(Frame, textvariable=I_gain, width=10, font=("segoe UI", 10)).grid(column=3, row=0, sticky="n",
                                                                                    pady=(20, 0))
        I_gain.set("0")

        # INTEGRAL
        D_gain = tk.StringVar()
        ttk.Label(Frame, text="KD:").grid(row=0, column=4, sticky="n", pady=(20, 0), padx=(20, 0))
        ttk.Entry(Frame, textvariable=D_gain, width=10, font=("segoe UI", 10)).grid(column=5, row=0, sticky="n",
                                                                    pady=(20, 0))
        D_gain.set("0")
        # setpoint
        set_point = tk.StringVar()
        ttk.Label(Frame, text="SP:").grid(row=0, column=6, sticky="ne", pady=(20, 0), padx=(20, 0))
        ttk.Entry(Frame, textvariable=set_point, width=10, font=("segoe UI", 10)).grid(column=7, row=0, sticky="n",
                                                                                       pady=(20, 0))
        set_point.set("0")
        # connectivity
        methods = ["Serial", "UDP", "WLAN", "BlueTooth", "Cloud Websocket"]
        ttk.Label(Frame, text="CONNECTIVITY:").grid(row=0, column=8, sticky="n", pady=(20, 0), padx=(50, 0))
        connection = ttk.Combobox(Frame, values=methods)
        connection.grid(row=0, column=9, sticky="n", pady=(20, 0), padx=(20, 0))
        connection.current(0)
        connection.bind("<<ComboboxSelected>>", lambda event: [setattr(self, "connectivity_setting", connection.get()),
                                                               self.show_setting(self.s_frame, connection.get()),
                                                               self.stop()])

        # configure
        ttk.Button(Frame, text="CONFIG", state="active",
                   command=lambda frame=Frame, kp=P_gain, ki=I_gain, kd=D_gain, sp=set_point: self.config(kp.get(),ki.get(), kd.get(),sp.get())).grid(row=0, column=10, sticky="e", padx=(20, 0), pady=(10, 0))

        # graph sheet
        g_frame = ttk.LabelFrame(self.dashboard, text="STEP RESPONSE", width=500, height=100, relief="solid",
                                 borderwidth="2")
        g_frame.pack(side="left", fill="y")
        g_frame.pack_propagate(False)
        g_frame.grid_propagate(False)

        # setting
        s_frame = ttk.LabelFrame(self.dashboard, height=200, text="SETTINGS", width=400)
        s_frame.pack(side="top")
        s_frame.pack_propagate(False)
        s_frame.grid_propagate(False)
        self.s_frame = s_frame
        self.show_setting(s_frame, self.connectivity_setting)

        # DATA
        self.d_frame = ttk.LabelFrame(self.dashboard, height=222, text="DATA", width=400)
        self.d_frame.pack(side="top")
        self.d_frame.pack_propagate(False)
        self.d_frame.grid_propagate(False)
        overshoot = tk.IntVar()
        self.d_frame.grid_columnconfigure(0, pad=10)
        overshoot.set(0)
        ttk.Label(self.d_frame, text="Overshoot:").grid(row=0, column=0, padx=(50, 0), pady=(5, 0))
        ttk.Entry(self.d_frame, textvariable=overshoot).grid(row=0, column=1, pady=(5, 0))

        ttk.Label(self.d_frame, text="Rise time:").grid(row=1, column=0, padx=(50, 0), pady=(5, 0))
        ttk.Entry(self.d_frame, textvariable=overshoot).grid(row=1, column=1, pady=(5, 0))

        ttk.Label(self.d_frame, text="Steady-State Error:").grid(row=2, column=0, padx=(50, 0), pady=(5, 0))
        ttk.Entry(self.d_frame, textvariable=overshoot).grid(row=2, column=1, pady=(5, 0))

        ttk.Label(self.d_frame, text="Peak Time:").grid(row=3, column=0, padx=(50, 0), pady=(5, 0))
        ttk.Entry(self.d_frame, textvariable=overshoot).grid(row=3, column=1, pady=(5, 0))

        ttk.Label(self.d_frame, text="Settling Time:").grid(row=4, column=0, padx=(50, 0), pady=(5, 0))
        ttk.Entry(self.d_frame, textvariable=overshoot).grid(row=4, column=1, pady=(5, 0))

        # botton
        b_frame = ttk.Frame(self.dashboard, width=400, height=100)
        b_frame.pack(side="top")
        b_frame.pack_propagate(False)
        b_frame.grid_propagate(False)

        self.start_button = ttk.Button(b_frame, text="START", command=self.start)
        self.start_button.grid(row=0, column=0, pady=10, padx=50)

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

        # PERF: create the Line2D object once and just mutate its data on every
        # update instead of clearing + re-plotting the whole axes each tick.
        # This is the single biggest win for smoothness at high sample rates.
        (self.line,) = self.ax.plot([], [], color="blue", marker=".")

        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both")
        ttk.Button(frame, text="Analyze", style="Custom.TButton", command=self.analyze).pack(side="left", padx=(50, 0))
        ttk.Button(frame, text="Clear", style="Custom2.TButton", command=self.clear).pack(side="right", padx=(0, 50))

    def show_setting(self, frame, connectivity):
        if connectivity == "Serial":
            self.serial_settings(frame)
        if connectivity == "UDP":
            self.UDP_settings(frame)
        if connectivity == "WLAN":
            self.WLAN_settings(frame)
        if connectivity == "BlueTooth":
            self.bluetooth_settings(frame)
        if connectivity == "Cloud Websocket":
            self.Cloud_Websocket_settings(frame)

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
        ttk.Label(s_frame, text="Baud rate:").grid(row=0, column=0, pady=10, padx=20)
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
        ttk.Button(s_frame, text="refresh", command=lambda frame=self.s_frame: self.serial_settings(frame)).grid(row=1,
                                                                                                                 column=2,
                                                                                                                 padx=10)

    def UDP_settings(self, s_frame):
        # This talks directly to the ESP32's WiFiUDP "mailbox" on port 8888 -
        # matches the firmware, unlike the WebSocket-based WLAN option below
        # (which needs a websocket server the ESP32 doesn't run).
        for widget in s_frame.winfo_children():
            widget.destroy()
        ttk.Label(s_frame, text="ESP32 IP address:", font=("segoe ui", 10)).grid(row=0, column=0, padx=20, pady=10)
        ip_entry = ttk.Entry(s_frame, font=("segoe ui", 10))
        ip_entry.insert(0, "192.168.4.1")  # default softAP address from the firmware
        ip_entry.grid(row=0, column=1, pady=10)

        ttk.Label(s_frame, text="UDP Port:", font=("segoe ui", 10)).grid(row=1, column=0, padx=20, pady=10)
        port_entry = ttk.Entry(s_frame, font=("segoe ui", 10))
        port_entry.insert(0, "8888")
        port_entry.grid(row=1, column=1, pady=10)

        self.udp_ip_entry = ip_entry
        self.udp_port_entry = port_entry

        self.udp_connect_btn = tk.Button(s_frame, text="CONNECT", bg="gray", fg="white", command=self.udp_connect)
        self.udp_connect_btn.grid(row=2, column=0, columnspan=2, pady=10)

    def WLAN_settings(self, s_frame):
        for widget in s_frame.winfo_children():
            widget.destroy()
        ttk.Label(s_frame, text="IP address:", font=("segoe ui", 10)).grid(row=0, column=0, padx=30, pady=10)
        ttk.Entry(s_frame, font=("segoe ui", 10)).grid(row=0, column=1)
        self.wifi_connect = tk.Button(s_frame, text="CONNECT", bg="gray", fg="white", command=self.wlan_connect)
        self.wifi_connect.place(x=150, y=130)

    def bluetooth_settings(self, s_frame):
        for widget in s_frame.winfo_children():
            widget.destroy()
        ttk.Label(s_frame, text=" bluetooth coming soon....", font=("segoe ui", 12)).pack(side="top")

    def Cloud_Websocket_settings(self, s_frame):
        for widget in s_frame.winfo_children():
            widget.destroy()
        ttk.Label(s_frame, text="Cloud websocket coming soon....", font=("segoe ui", 12)).pack(side="top")

    def start(self):
        while not self.data_queue.empty():
            self.data_queue.get()
        # Reference point for the locally-generated timestamp in
        # _parse_frame() (needed since the current firmware doesn't send
        # its own time field).
        self.stream_start_time = time.time()
        if self.connectivity_setting == "Serial":
            self.stop()
            self.yarr.clear()
            self.tarr.clear()
            self.running = True
            self.active_connection = "Serial"
            self.update_graph()
            threading.Thread(target=self.serial_update_data, daemon=True).start()
        elif self.connectivity_setting == "UDP":
            if not self.udp_is_connected():
                messagebox.showerror("UDP", "Connect to the ESP32 first")
                return
            self.clear()
            self.yarr.clear()
            self.tarr.clear()
            self.running = True
            self.active_connection = "UDP"
            self.update_graph()
            threading.Thread(target=self.udp_update_data, daemon=True).start()
        elif self.connectivity_setting == "WLAN":
            self.clear()
            self.yarr.clear()
            self.tarr.clear()
            self.running = True
            self.active_connection = "WLAN"
            self.update_graph()
            threading.Thread(target=self.wlan_update_data, daemon=True).start()


    def serial_update_data(self):
        try:
            self.mcu = serial.Serial(self.port, int(self.baudrate))
            time.sleep(1)
            if self.mcu.is_open:
                self.start_button.config(style="Custom.TButton")
                while self.running:
                    if self.mcu:
                        try:
                            data = self.mcu.readline().decode('utf-8').strip()
                            time.sleep(0.1)
                        except serial.SerialException:
                            break
                        frame = self._parse_frame(data)
                        if frame is not None:
                            self.data_queue.put(frame)
            else:
                self.mcu.close()
                messagebox.showinfo("port", "no mcu")

        except Exception as e:
            if hasattr(self, "mcu") and self.mcu.is_open:
                self.mcu.close()
            # messagebox.showerror("Error","Something went wrong!")
            messagebox.showerror("error", str(e))

    def wlan_update_data(self):
        try:
            if self.ws_is_connected():
                print("connected!")
                self.start_button.config(style="Custom.TButton")
                while self.running:
                    data = self.ws.recv()
                    print(data)
                    parts = data.split(",")
                    if len(parts) == 2:
                        self.data_queue.put_nowait((float(parts[0]), float(parts[1])))
        except Exception as e:
            messagebox.showerror("websocket error", str(e))

    def udp_update_data(self):
        try:
            if self.udp_is_connected():
                self.start_button.config(style="Custom.TButton")
                while self.running:
                    try:
                        data, addr = self.udp_sock.recvfrom(1024)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    text = data.decode("utf-8", errors="ignore").strip()
                    frame = self._parse_frame(text)
                    if frame is not None:
                        try:
                            self.data_queue.put_nowait(frame)
                        except queue.Full:
                            pass
        except Exception as e:
            messagebox.showerror("UDP error", str(e))

    def wlan_connect(self):
        try:
            if not self.ws_is_connected():
                ip_entry = self.s_frame.winfo_children()[1]
                ip_address = ip_entry.get()
                if not ip_address:
                    messagebox.showerror("WLAN", "Enter MCU IP address")
                    return
                ws_URL = f"ws://{ip_address}:81/"

                try:
                    self.ws = websocket.WebSocket()
                    self.ws.connect(ws_URL)
                    self.wifi_connect.config(bg="green", text="Disconnect")

                except Exception as e:
                    messagebox.showerror("WLAN", str(e))
            elif self.ws_is_connected():
                self.stop()
                self.wifi_connect.config(bg="gray", text="Connect")


        except Exception as e:
            messagebox.showerror("WLAN", str(e))

    def udp_connect(self):
        try:
            if not self.udp_is_connected():
                ip = self.udp_ip_entry.get().strip()
                if not ip:
                    messagebox.showerror("UDP", "Enter ESP32 IP address")
                    return
                try:
                    port = int(self.udp_port_entry.get().strip())
                except ValueError:
                    messagebox.showerror("UDP", "Port must be a number")
                    return

                self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # Timeout lets the receive loop wake up periodically to check
                # self.running instead of blocking forever on recvfrom().
                self.udp_sock.settimeout(1.0)
                self.udp_remote = (ip, port)

                # The firmware only learns our IP/port (remoteIP/remotePort)
                # once it *receives* a packet from us - it explicitly ignores
                # a "PING" payload when parsing PID gains, so this is safe to
                # send before any real config has been set.
                self.udp_sock.sendto(b"PING", self.udp_remote)

                self.udp_connected = True
                self.udp_connect_btn.config(bg="green", text="Disconnect")
            else:
                # stop() only closes the socket if data acquisition is the
                # thing currently running (active_connection == "UDP"). You
                # can be "connected" without having pressed START yet, so
                # close it here explicitly too.
                self.stop()
                if self.udp_sock:
                    try:
                        self.udp_sock.close()
                    except OSError:
                        pass
                self.udp_sock = None
                self.udp_connected = False
                self.udp_connect_btn.config(bg="gray", text="Connect")
        except Exception as e:
            messagebox.showerror("UDP", str(e))

    def udp_is_connected(self):
        return bool(self.udp_connected and self.udp_sock)

    def ws_is_connected(self):
        return hasattr(self, "ws") and self.ws.sock

    def stop(self):
        self.running = False
        self.start_button.config(style="TButton")
        # BUGFIX: use active_connection (what's actually running) rather than
        # connectivity_setting, which the dropdown handler already switches
        # to the *new* choice before calling stop(). That mismatch used to
        # mean switching dropdowns mid-run left the real connection open.
        if self.active_connection == "Serial":
            if hasattr(self, "mcu") and self.mcu and self.mcu.is_open:
                self.mcu.close()
        elif self.active_connection == "UDP":
            if self.udp_sock:
                try:
                    self.udp_sock.close()
                except OSError:
                    pass
            self.udp_sock = None
            self.udp_connected = False
        elif self.active_connection == "WLAN":
            if hasattr(self, "ws") and self.ws.sock:
                self.ws.close()
        self.active_connection = None

    def update_graph(self):
        if not self.running:
            return

        # PERF: drain everything currently sitting in the queue instead of
        # pulling a single point per 50ms tick. If the MCU/websocket sends
        # data faster than our redraw rate, a single-point drain makes the
        # queue back up and the plot visibly lags behind real time.
        got_new_data = self.process_queue()

        if got_new_data:
            # PERF: mutate the existing line's data instead of ax.cla() +
            # re-plot + re-set title/labels/grid every tick. cla() throws
            # away all the axes styling and forces a full re-render; set_data
            # just updates the line's vertices.
            self.line.set_data(self.tarr, self.yarr)

            # Rescale the view to fit the new data, then redraw only what's
            # needed. relim()/autoscale_view() are cheap compared to a full
            # cla()+replot, and draw_idle() lets matplotlib coalesce redraw
            # requests instead of forcing an immediate full render.
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw_idle()

        self.dashboard.after(50, self.update_graph)

    def _parse_frame(self, text):
        """Turn one line/packet from the rig into a (t, angle) tuple, or
        None if it's not data (e.g. a boot message).

        FIRMWARE-SIDE TODAY (unmodified):
          - Serial sends "Angle:174.32"
          - UDP sends "174.32" (bare, no comma, no time field)
        Neither includes a time value, so we stamp each sample with our own
        wall-clock time relative to when the stream started.

        Also tolerates a future firmware sending "time,angle" pairs
        directly, so this doesn't need touching again once that's fixed.
        """
        if text.startswith("Angle:"):
            text = text[len("Angle:"):]
        text = text.strip()
        if not text:
            return None

        parts = text.split(",")
        try:
            if len(parts) == 2:
                return float(parts[0]), float(parts[1])
            elif len(parts) == 1:
                angle = float(parts[0])
                t = time.time() - (self.stream_start_time or time.time())
                return t, angle
        except ValueError:
            return None
        return None

    def process_queue(self):
        """Pull every point currently available in the queue.

        Returns True if at least one new point was added, so the caller
        knows whether a redraw is actually needed.
        """
        got_new_data = False
        while True:
            try:
                t_val, y_val = self.data_queue.get_nowait()
            except queue.Empty:
                break
            self.yarr.append(y_val)
            self.tarr.append(t_val)
            got_new_data = True
        if len(self.tarr) > self.max_points:
            overflow = len(self.tarr) - self.max_points
            del self.tarr[:overflow]
            del self.yarr[:overflow]
        return got_new_data

    def clear(self):
        self.tarr.clear()
        self.yarr.clear()
        if hasattr(self, "mcu") and self.mcu and self.mcu.is_open:
            self.mcu.reset_input_buffer()
        # PERF: no need to cla()/re-set title/labels/grid, just clear the
        # line's data and redraw.
        self.line.set_data([], [])
        self.canvas.draw_idle()
        print(self.yarr)

    def analyze(self):
        self.stop()

        if not self.yarr or not self.tarr:
            messagebox.showinfo("No Data", "No data available to analyze!")
            return

        y = self.yarr
        t = self.tarr
        sp = self.S_point

        initial_val = sum(y[:min(5, len(y))]) / min(5, len(y))

        step_change = sp - initial_val

        if abs(step_change) < 0.01:
            messagebox.showinfo("Analysis", "No noticeable step change")
            return

        max_val = max(y)
        overshoot_val = max(0, max_val - sp)

        try:
            threshold_10 = 0.1 * step_change
            threshold_90 = 0.9 * step_change

            t_10 = next(ti for yi, ti in zip(y, t) if yi > threshold_10)
            t_90 = next(ti for yi, ti in zip(y, t) if yi > threshold_90)

            rise_time_val = t_90 - t_10

        except StopIteration:
            rise_time_val = "N/A"


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

        # BUGFIX: rise_time_val can be the string "N/A" (when the response
        # never crosses the 10%/90% thresholds). Formatting a string with
        # ":.2f" raises a ValueError, so format numbers and strings
        # differently instead of assuming everything is a float.
        def fmt(val):
            return f"{val:.2f}" if isinstance(val, (int, float)) else str(val)

        self.var_overshoot = tk.StringVar(value=fmt(overshoot_val))
        self.var_rise_time = tk.StringVar(value=fmt(rise_time_val))
        self.var_steady_state = tk.StringVar(value=fmt(steady_state_val))
        self.var_peak_time = tk.StringVar(value=fmt(peak_time_val))
        self.var_settling_time = tk.StringVar(value=fmt(settling_val))

        labels = ["Overshoot:", "Rise time:", "Steady-State Error:", "Peak Time:", "Settling Time:"]
        vars_ = [self.var_overshoot, self.var_rise_time, self.var_steady_state, self.var_peak_time,
                 self.var_settling_time]

        for i, (text, var) in enumerate(zip(labels, vars_)):
            ttk.Label(self.d_frame, text=text).grid(row=i, column=0, padx=(50, 0), pady=(5, 0))
            ttk.Entry(self.d_frame, state="readonly", textvariable=var).grid(row=i, column=1, pady=(5, 0))

    def config(self, kp, ki, kd, sp):
        try:
            self.P_gain = int(kp)
            self.I_gain = int(ki)
            self.D_gain = int(kd)
            self.S_point = int(sp)
        except:
            messagebox.showerror("PID", "enter numbers only!")
            return
        if self.connectivity_setting == "Serial":
            if hasattr(self, "mcu") and self.mcu.is_open:
                # BUGFIX: firmware parses this with
                # sscanf(..., "%f,%f,%f,%f", ...) - comma separated, not
                # colon separated. The old ":" format never matched, so
                # gains silently never updated over Serial.
                self.mcu.write(f"{self.P_gain},{self.I_gain},{self.D_gain},{self.S_point}\n".encode())
            else:
                messagebox.showerror("config", "no mcu available")
        if self.connectivity_setting == "UDP":
            if self.udp_is_connected():
                msg = f"{self.P_gain},{self.I_gain},{self.D_gain},{self.S_point}\n"
                self.udp_sock.sendto(msg.encode(), self.udp_remote)
            else:
                messagebox.showerror("config", "not connected to ESP32")
        if self.connectivity_setting == "WLAN" and self.ws_is_connected():
            PID = {"P": str(self.P_gain),
                   "I": str(self.I_gain),
                   "D": str(self.D_gain),
                   "s": str(self.S_point)}
            self.ws.send(json.dumps(PID))

    def on_closing(self):
        self.stop()
        time.sleep(0.2)

        if hasattr(self, "mcu") and self.mcu and hasattr(self.mcu, "is_open") and self.mcu.is_open:
            try:
                self.mcu.close()
            except:
                pass
        if hasattr(self, "ws") and self.ws and self.ws.sock:
            try:
                self.ws.close()
            except:
                pass
        if self.udp_sock:
            try:
                self.udp_sock.close()
            except:
                pass
        self.dashboard.destroy()


if __name__ == "__main__":
    dashboard = Dashboard("abel")
# ==============================================================================
# FUTURE UPGRADE: SYSTEM IDENTIFICATION MODULE
# ==============================================================================
# TODO: Add a "Vibration Analysis" tab to this toolbox.
#
# GOAL:
#   To scientifically determine the cutoff frequency for the complementary filter
#   instead of guessing, and to identify structural resonance/motor noise.
#
# IMPLEMENTATION PLAN:
#   1. Create a function to receive 2-3 seconds of RAW accelerometer data
#      (unfiltered) from the robot while motors are ramping up.
#   2. Use numpy.fft (Fast Fourier Transform) to analyze the frequency spectrum.
#   3. Plot the spectrum to visualize noise spikes (e.g., mains hum, frame vibration).
#   4. Use this data to set the optimal Low Pass / Notch filter coefficients.
# ==============================================================================
