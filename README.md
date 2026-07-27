# PID Tuner Dashboard

A general-purpose Tkinter GUI for tuning any PID controller over Serial or UDP/WiFi. It streams live process data into a step-response plot, computes step-response metrics (overshoot, rise time, settling time, etc), and pushes new PID gains to your device in real time.

The dashboard doesn't assume any specific hardware — it just needs your device to speak the small text protocol described below. `rig_firmware.ino` is included as a **reference implementation** for an ESP32 (MPU6050 + 2 ESCs), but you can point this dashboard at anything: an Arduino, an ESP32, an STM32, a simulated plant in Python, whatever — as long as it implements the protocol.

## Features

- Live-updating step-response plot (efficient redraws, handles high sample rates without lagging)
- Two built-in transports: **Serial (USB)** and **UDP (WiFi)**
- One-click PID config push (`KP` / `KI` / `KD` / `SP`)
- Step-response analysis: overshoot, rise time, steady-state error, peak time, settling time
- COM port auto-detection and refresh for Serial

## Requirements

```bash
pip install pyserial matplotlib websocket-client
```

## Running it

```bash
python dashboard.py
```

## Integrating your own device

To work with the dashboard, your device just needs to do two things: **accept config messages**, and **send back telemetry**. Pick whichever transport fits your setup.

### Option A: Serial (USB)

1. Have your device print one line per sample over Serial at a known baud rate.
2. In the dashboard, select **Serial** in the CONNECTIVITY dropdown, choose your COM port and baud rate, and hit **START**.

### Option B: UDP (WiFi)

1. Have your device open a UDP listener on a known port (e.g. `8888`).
2. Have it reply to the sender's address once it receives any packet — that first packet (the dashboard sends a `"PING"`) is how your device learns where to send telemetry back to. This is a common pattern for devices that don't know their client's IP ahead of time (e.g. an ESP32 running its own access point).
3. In the dashboard, select **UDP**, enter your device's IP and port, hit **CONNECT**, then **START**.

*(WLAN/WebSocket and Bluetooth appear in the dropdown as placeholders for future transports and aren't implemented yet — see "Placeholder transports" below if you want to build one out. Use UDP or Serial today.)*

## Protocol

### Dashboard → device (PID config)

Sent whenever you hit **CONFIG**, over whichever transport is active:

```
kp,ki,kd,setpoint\n
```

All four values are sent as plain numbers, comma-separated, newline-terminated. Your device should parse this and update its control loop. Setting all three gains to `0` is treated as a natural kill-switch convention if you want to support it (the reference firmware does).

### Device → dashboard (telemetry)

The dashboard's parser is intentionally flexible and accepts **either** of these formats, so you can start with the simple one and upgrade later without touching the Python side:

**Simple (no timestamp) — recommended for a first integration:**
```
<value>\n
```
A single number, e.g. your sensor reading. The dashboard timestamps each sample itself using wall-clock time from when you hit START. An optional `Angle:` prefix (e.g. `Angle:12.34`) is also stripped automatically if present, for compatibility with quick debug prints.

**Full (with timestamp):**
```
<time>,<value>\n
```
Two comma-separated numbers. Use this once you want your device's own clock driving the x-axis (e.g. for precise timing independent of network/serial latency).

Send telemetry as often as makes sense for your control loop — the dashboard drains everything available each redraw tick, so it won't fall behind a fast stream.

## Reference implementation

`rig_firmware.ino` is a complete example targeting an ESP32 balancing rig (MPU6050 + 2 ESCs on pins 18/19), implementing both the UDP transport and the protocol above. Use it as a template:

- It opens a WiFi access point and a UDP socket on port 8888
- It parses incoming `kp,ki,kd,setpoint` messages
- It sends telemetry using the "simple" (no-timestamp) format

Swap out the sensor-reading and motor-driving code for your own hardware and the rest should work as-is.

## Step-response analysis

Hit **Analyze** after capturing a trace to compute:

| Metric | Meaning |
|---|---|
| Overshoot | How far the response exceeds the setpoint |
| Rise time | Time to go from 10% to 90% of the step change |
| Steady-state error | Final offset from the setpoint |
| Peak time | Time at which the max value occurs |
| Settling time | Last time the response was outside a ±2% band around the setpoint |

## Placeholder transports (open for contribution)

Two entries in the CONNECTIVITY dropdown are stubs today — listed here so anyone picking this up knows exactly what's there and what's missing.

### WLAN (WebSocket)

Partially implemented — the wiring exists but there's no server to talk to.

- `WLAN_settings()` (`dashboard.py`) renders an IP field and a Connect button.
- `wlan_connect()` opens a `websocket.WebSocket()` and connects to `ws://<ip>:81/`.
- `wlan_update_data()` reads frames via `self.ws.recv()` and expects the same `<time>,<value>` telemetry format as Serial/UDP.
- `ws_is_connected()` / `config()`'s WLAN branch (sends PID gains as a JSON object `{"P":..., "I":..., "D":..., "s":...}`, not the comma-separated format used by Serial/UDP — worth reconciling if you build this out) are also already in place.

**What's missing:** a device-side WebSocket server on port 81. This would suit a device with a full WiFi stack (e.g. connecting to a real router) rather than the UDP-over-access-point pattern used by the reference firmware. If you build this, either match the existing JSON config format or switch it to the shared comma-separated one for consistency.

### Bluetooth

Not implemented — `bluetooth_settings()` just renders a "coming soon" label. No connection logic, no data parsing. Would need a `bluetooth_connect()` (e.g. via `pybluez` or platform-specific serial-over-Bluetooth) plus a `bluetooth_update_data()` thread mirroring the Serial/UDP ones, ideally reusing the existing `_parse_frame()` telemetry parser and the comma-separated config format.

### Cloud Websocket

Not implemented — `Cloud_Websocket_settings()` is a placeholder label too. Intended for a device that phones home to a cloud relay (useful when the device and dashboard aren't on the same local network). Would need: a relay/broker service, a way to address a specific device (e.g. a device ID), and dashboard-side auth/connection handling in addition to the send/receive thread.

If you implement any of these, the pattern to follow is the UDP option: a `*_settings()` panel, a `*_connect()`/`*_is_connected()` pair, a `*_update_data()` thread that pushes `(t, value)` tuples into `self.data_queue`, and hooking into `start()`/`stop()`'s `active_connection` tracking so START/STOP/switching-dropdowns behaves correctly.

## Known limitations / TODO

- PID gains are currently truncated to integers before being sent (`int(kp)` etc.), even if your device treats them as floats. Fine for coarse tuning; flag if you need fractional gains and it can be relaxed to floats.
- Planned: a **Vibration Analysis** tab using raw accelerometer FFT, for scientifically picking a filter cutoff frequency instead of guessing (see TODO block at the bottom of `dashboard.py`).

## Safety (if driving motors/actuators)

- Always secure/restrain hardware under test before sending live PID output to actuators.
- Clamp actuator output to a safe range in your device's firmware regardless of what gains get sent — don't rely on the dashboard to enforce this.
