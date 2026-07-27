# PID Tuner Dashboard

A Tkinter-based GUI for tuning a PID controller on an ESP32-based balancing rig, with live step-response plotting and step-response analysis (overshoot, rise time, settling time, etc).

Talks to the rig over **Serial (USB)** or **UDP over WiFi** (the ESP32 runs its own WiFi access point — no router needed).

## Files

| File | Description |
|---|---|
| `dashboard.py` | Python/Tkinter GUI — PID config, live plot, connectivity |
| `rig_firmware.ino` | ESP32 firmware — reads MPU6050, runs PID, drives two ESCs |

## Hardware

- ESP32 dev board
- MPU6050 (I2C, pins 21/22)
- 2x ESC + motor on pins 18 (left) and 19 (right)

## Requirements

**Python side:**
```bash
pip install pyserial matplotlib websocket-client
```

**Firmware side (Arduino IDE):**
- Board: ESP32
- Libraries: `ESP32Servo` (built-in `WiFi`, `WiFiUdp`, `Wire` are part of the ESP32 core)

## Setup

### 1. Flash the firmware
Open `rig_firmware.ino` in the Arduino IDE, select your ESP32 board, and upload.

On boot the ESP32:
- Creates a WiFi access point: **SSID `TEST_RIG_003`**, **password `password123`**
- Starts listening for UDP packets on **port 8888** at IP **`192.168.4.1`**
- Arms the ESCs (keep the rig still for the first ~3 seconds after power-on — it beeps/arms during this window)

### 2. Connect your computer to the rig's WiFi
Join `TEST_RIG_003` from your laptop like any normal WiFi network. Your computer will get an address on the ESP32's subnet automatically.

### 3. Run the dashboard
```bash
python dashboard.py
```

## Usage

1. **Choose a connection method** from the CONNECTIVITY dropdown:
   - **Serial** — plug the ESP32 in over USB, pick the COM port and baud rate (default `9600`), no extra setup needed.
   - **UDP** — leave IP as `192.168.4.1` and port as `8888` (defaults match the firmware), then hit **CONNECT**. This sends a one-time "PING" so the ESP32 learns where to send data back to.
2. Hit **START** to begin streaming live angle data into the plot.
3. Enter `KP`, `KI`, `KD`, `SP` (setpoint) and hit **CONFIG** to push new gains to the rig live.
4. Setting all of `KP`/`KI`/`KD` to `0` is a kill switch — the firmware cuts the motors to idle.
5. Hit **STOP** to end the stream (closes the Serial/UDP connection).
6. Hit **Analyze** to compute overshoot, rise time, steady-state error, peak time, and settling time from the captured trace.
7. Hit **Clear** to wipe the current trace and start fresh.

## Wire protocol

**Dashboard → rig (PID config):**
```
kp,ki,kd,setpoint\n
```
Sent over whichever channel (Serial or UDP) is currently active.

**Rig → dashboard (telemetry):**
Currently the firmware sends a bare angle value with no timestamp:
- Serial: `Angle:<value>\n`
- UDP: `<value>\n`

The dashboard timestamps each sample locally (wall-clock time since STOP/START) since the firmware doesn't include its own time field yet. If the firmware is ever updated to send `time,angle` pairs directly, the dashboard's parser already supports that format too, no changes needed on the Python side.

## Known limitations / TODO

- PID gains are currently truncated to integers before being sent (`int(kp)` etc. in `config()`), even though the firmware treats them as floats. Fine for coarse tuning, but you'll want that fixed if you need fractional gains.
- WLAN (WebSocket) connectivity option in the dropdown is a placeholder for a future firmware variant — the current firmware doesn't run a WebSocket server, so use **UDP** instead for WiFi.
- Bluetooth and Cloud Websocket options are not implemented yet.
- Planned: a **Vibration Analysis** tab using raw accelerometer FFT to pick the complementary filter cutoff frequency scientifically instead of guessing (see TODO block at the bottom of `dashboard.py`).

## Safety

- Always keep the rig secured/restrained during testing — the ESC arming sequence and PID output can spin the motors unexpectedly.
- Motor PWM is clamped to a safe testing range (1000–1500µs) in firmware regardless of what gains are sent.
