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

*(WLAN/WebSocket and Bluetooth appear in the dropdown as placeholders for future transports and aren't implemented yet — use UDP or Serial today.)*

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

## Known limitations / TODO

- PID gains are currently truncated to integers before being sent (`int(kp)` etc.), even if your device treats them as floats. Fine for coarse tuning; flag if you need fractional gains and it can be relaxed to floats.
- WLAN (WebSocket) and Bluetooth connectivity options are placeholders in the dropdown, not yet implemented.
- Planned: a **Vibration Analysis** tab using raw accelerometer FFT, for scientifically picking a filter cutoff frequency instead of guessing (see TODO block at the bottom of `dashboard.py`).

## Safety (if driving motors/actuators)

- Always secure/restrain hardware under test before sending live PID output to actuators.
- Clamp actuator output to a safe range in your device's firmware regardless of what gains get sent — don't rely on the dashboard to enforce this.
