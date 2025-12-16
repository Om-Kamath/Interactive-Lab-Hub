# Raspberry Pi LED Integration Guide (SparkX Qwiic)

This guide explains how to connect your **SparkX Qwiic LED Stick** to the Subway Info Dashboard.

## Architecture
`Web UI (Browser)` -> `HTTP Request (JSON)` -> `Python Server (Flask)` -> `I2C Bus` -> `Qwiic LED Stick`

## Hardware Requirements
- Raspberry Pi (Any model with I2C pins)
- **SparkX Qwiic LED Stick** (APA102 driven via I2C)
- **Qwiic Cable** (or Jumper Wires if soldering)

## Wiring (I2C)
If using a Qwiic HAT or pHAT, simply plug in the Qwiic cable.
If wiring directly to GPIO:

- **Black (GND)** -> Ground (Physical Pin 6)
- **Red (3.3V)** -> 3.3V Power (Physical Pin 1)
- **Blue (SDA)** -> GPIO 2 (Physical Pin 3)
- **Yellow (SCL)** -> GPIO 3 (Physical Pin 5)

**Note**: Enable I2C on your Raspberry Pi:
1. Run `sudo raspi-config`
2. Interface Options -> I2C -> Enable

## Software Setup

### 1. Install Dependencies on Raspberry Pi
```bash
sudo apt-get update
sudo apt-get install python3-pip i2c-tools
sudo pip3 install flask flask-cors sparkfun-qwiic-led-stick
```

### 2. Check I2C Connection
Run this command to see if the stick is detected (usually address `0x23`):
```bash
i2cdetect -y 1
```

### 3. Create the Python Server (`server.py`)
Copy the `server.py` file from this project to your Raspberry Pi.

### 4. Run the Server
```bash
sudo python3 server.py
```

### 5. Connect Web UI
In your `script.js` file on the dashboard, update the `PI_API_URL` with your Pi's IP address:

```javascript
const PI_API_URL = 'http://<YOUR_PI_IP>:5000'; 
```

## Troubleshooting
- **"Qwiic LED Stick isn't connected"**: Check your wiring and ensure I2C is enabled in `raspi-config`.
- **Permission Denied**: Accessing I2C usually requires the user to be in the `i2c` group or running as root/sudo.
