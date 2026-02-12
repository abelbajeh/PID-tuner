
```markdown
# ⚙️ PID Tuner Dashboard

A **Graphical PID Tuning Application** built with **Python (Tkinter + Matplotlib)** for visualizing and tuning PID control parameters in real time via **Arduino** or **ESP32** (using serial communication).  

This dashboard helps engineers and students easily observe **step responses**, adjust **PID gains**, and analyze system performance metrics like rise time, overshoot, steady-state error, and settling time.

---

## 🧠 Features

### ✅ Completed
- Modern Tkinter-based GUI  
- Real-time plotting using Matplotlib  
- Serial communication with microcontrollers (Arduino/ESP32)  
- Dynamic parameter configuration (Kp, Ki, Kd, Setpoint)  
- Step response visualization and auto-updating graph  
- Basic system analysis metrics (Overshoot, Rise time, Steady-state error, Peak time, Settling time)  
- `.gitignore` and `requirements.txt` included  

### 🔄 In Progress
- Auto-tuning algorithm implementation (Ziegler–Nichols method)  
- Additional connectivity modes (Wi-Fi, Bluetooth, HTTP)  
- Saving/loading PID profiles  
- Real-time data export and logging  

---

## 🧩 Architecture Overview

```

Python (Tkinter + Matplotlib)
│
├── Dashboard UI
│   ├── PID Control Panel
│   ├── Step Response Graph
│   ├── Data Analysis Section
│   └── Connectivity Settings
│
├── Serial Communication (pySerial)
│   ├── Sends PID config: "Kp:Ki:Kd:SP"
│   └── Reads time, amplitude data as CSV
│
└── Arduino/ESP32 Firmware
└── Sends real-time step response data

````

---

## 🧰 Tech Stack

| Component | Technology |
|------------|-------------|
| **Programming Language** | Python |
| **GUI Library** | Tkinter |
| **Plotting** | Matplotlib |
| **Communication** | PySerial |
| **Hardware** | Arduino / ESP32 |

---

## 🪴 Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd pid-tuner-dashboard
````

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Connect your microcontroller

* Connect your **Arduino or ESP32** to your computer
* Note the **COM port** (e.g., COM3) and **baud rate** (default 9600)

### 4. Run the app

```bash
python main.py
```

### 5. Send Data Format (from MCU)

Your Arduino or ESP32 code should continuously send data in this format:

```
time,value
```

Example:

```
0.00,0.0
0.01,0.1
0.02,0.2
```

---

## ⚡ Operating Modes

| Mode          | Description                 | Status         |
| ------------- | --------------------------- | -------------- |
| **Serial**    | Communicates via USB serial | ✅ Working      |
| **Wi-Fi**     | Wireless tuning via ESP32   | 🔄 In Progress |
| **Bluetooth** | Bluetooth-based control     | 🔄 In Progress |
| **HTTP**      | Network-based tuning mode   | 🔄 In Progress |

---

## 📊 Analysis Metrics

| Metric                 | Description                            |
| ---------------------- | -------------------------------------- |
| **Overshoot**          | Difference between peak and setpoint   |
| **Rise Time**          | Time to go from 10% to 90% of setpoint |
| **Steady-State Error** | Final error at steady state            |
| **Peak Time**          | Time to reach maximum response         |
| **Settling Time**      | Time to stay within ±2% of setpoint    |

---

## 📅 Project Status

This project is **still under active development**.
Upcoming updates will include **auto-tuning**, **logging**, and **wireless control support**.

---

## 🧑‍💻 Developer Notes

> Currently testing and optimizing **real-time plotting** and **serial communication stability**.
> Auto-tuning and Wi-Fi features are next in the roadmap.

---

## 🤝 Contribution

Feel free to fork, improve, and create pull requests!
Suggestions for algorithm improvements are always welcome.

---

## 📜 License

Open Source under the [MIT License](LICENSE).

---

### 🧩 Example Screenshot (coming soon)

*A preview image of the dashboard interface will be added after UI stabilization.*

```

---

Would you like me to also include a **short Arduino/ESP32 code example** that matches this dashboard’s expected serial data format (so you can test the live plotting)?
```
