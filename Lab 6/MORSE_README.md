# Morse Code Communication System via MQTT

A distributed morse code transmitter and receiver system built for Lab 6 using MQTT messaging.

## 📡 System Overview

This project creates a wireless morse code communication system where multiple Raspberry Pis can send and receive morse code messages over MQTT. Messages are transmitted as dots and dashes, decoded in real-time, and displayed with visual/audio feedback.

### Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  TRANSMITTER    │         │   MQTT BROKER    │         │    RECEIVER     │
│  Raspberry Pi   │─────────▶│   farlab.info    │─────────▶│  Raspberry Pi   │
│                 │         │                  │         │                 │
│ • Text Input    │         │  Topic: IDD/     │         │ • LED Flash     │
│ • Button Input  │         │  morse/signal    │         │ • Buzzer Beep   │
│ • LED Flash     │         │                  │         │ • Display Text  │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

**Data Flow:**
1. User enters text on transmitter
2. Text converted to morse code (dots/dashes)
3. Each signal published to MQTT topic with timing info
4. Receiver subscribes to topic and decodes signals
5. Decoded text displayed with visual/audio feedback

## 🎯 Features

### Transmitter (`morse_transmitter.py`)
- ✅ Convert text to international morse code
- ✅ Transmit via MQTT with proper timing
- ✅ LED visual feedback during transmission
- ✅ Interactive button mode for manual morse input
- ✅ Support for letters, numbers, and punctuation

### Receiver (`morse_receiver.py`)
- ✅ Subscribe to MQTT morse signals
- ✅ Real-time decoding with timeout detection
- ✅ LED + Buzzer feedback for dots/dashes
- ✅ MiniPiTFT display showing decoded message
- ✅ Signal history visualization

## 🔧 Hardware Setup

### Required Components
- **Raspberry Pi** (3+ for testing)
- **MiniPiTFT Display** (optional but recommended)
- **LEDs** - GPIO 18 (Pin 12)
- **Buzzer** - GPIO 17 (Pin 11) - optional
- **Button** - GPIO 23 (Pin 16) - optional for interactive mode

### Wiring Diagram

```
Raspberry Pi GPIO:
├── GPIO 18 (Pin 12) ──────▶ LED (+ resistor) ──▶ GND
├── GPIO 17 (Pin 11) ──────▶ Buzzer ──────────▶ GND
└── GPIO 23 (Pin 16) ◀────── Button ──────────▶ GND
                           (with pull-up)
```

### MiniPiTFT Connection
- Connect via Qwiic connector or GPIO header
- Display shows: Current signal, decoded message, status

## 🚀 Installation & Setup

### 1. Install Dependencies

```bash
cd "Lab 6"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Test MQTT Connection

```bash
# Test subscribing
mosquitto_sub -h farlab.infosci.cornell.edu -p 1883 -t "IDD/morse/#" -u idd -P "device@theFarm"

# Test publishing
mosquitto_pub -h farlab.infosci.cornell.edu -p 1883 -t "IDD/morse/test" -m "Hello" -u idd -P "device@theFarm"
```

### 3. Run the System

**On Receiver Pi(s):**
```bash
python morse_receiver.py
```

**On Transmitter Pi:**
```bash
python morse_transmitter.py
```

## 💬 Usage Examples

### Example 1: Simple Text Message
```
Transmitter: Enter message: HELLO WORLD
             📡 Transmitting: 'HELLO WORLD'
             H: ....
             E: .
             L: .-..
             ...

Receiver:    🎧 Listening for morse code signals...
             •••• [H] • [E] •-•• [L] •-•• [L] --- [O]  [SPACE] 
             DECODED MESSAGE: HELLO WORLD
```

### Example 2: Interactive Button Mode
```
Transmitter: Enter message: interactive
             🔘 INTERACTIVE MORSE MODE
             Press button to send DOT
             Hold button to send DASH
             
             [User presses button in pattern: •••  ---  •••]
             
Receiver:    ••• [S] --- [O] ••• [S]
             DECODED MESSAGE: SOS
```

## 🎨 Morse Code Reference

### Letters
```
A: .-    B: -...  C: -.-.  D: -..   E: .     F: ..-.
G: --.   H: ....  I: ..    J: .---  K: -.-   L: .-..
M: --    N: -.    O: ---   P: .--.  Q: --.-  R: .-.
S: ...   T: -     U: ..-   V: ...-  W: .--   X: -..-
Y: -.--  Z: --..
```

### Numbers
```
0: -----  1: .----  2: ..---  3: ...--  4: ....-
5: .....  6: -....  7: --...  8: ---..  9: ----.
```

### Punctuation
```
.: .-.-.-   ,: --..--   ?: ..--..   !: -.-.--
/: -..-.    (: -.--.    ): -.--.-   &: .-...
:: ---...   ;: -.-.-.   =: -...-    +: .-.-.
-: -....-   _: ..--.-   ": .-..-.   $: ...-..-
@: .--.-.
```

## 🧪 Testing with Multiple Devices

### Scenario 1: One-to-Many Broadcast
```bash
# 1 Transmitter, 3 Receivers
Pi1 (TX): python morse_transmitter.py
Pi2 (RX): python morse_receiver.py
Pi3 (RX): python morse_receiver.py
Pi4 (RX): python morse_receiver.py

# All receivers decode same message simultaneously
```

### Scenario 2: Turn-Based Communication
```bash
# Take turns transmitting
Pi1: Sends "HELLO"
Pi2: Receives, then sends "WORLD"
Pi1: Receives "WORLD"
```

## 🐛 Troubleshooting

### Problem: "Connection failed"
**Solution:** 
```bash
# Check broker connectivity
ping farlab.infosci.cornell.edu

# Verify credentials
Username: idd
Password: device@theFarm
Port: 1883 (non-TLS)
```

### Problem: "No signals received"
**Solution:**
- Verify both devices use same topic: `IDD/morse/signal`
- Check MQTT viewer: http://farlab.infosci.cornell.edu:5001
- Ensure transmitter shows "Connected to MQTT broker"

### Problem: "Display not working"
**Solution:**
```bash
# Stop screen service to free up display
sudo systemctl stop piscreen.service

# Restart if needed
sudo systemctl start piscreen.service
```

### Problem: "GPIO errors"
**Solution:**
```bash
# Run with sudo if permission denied
sudo python morse_receiver.py

# Or fix GPIO permissions
sudo usermod -a -G gpio $USER
```

## 📊 MQTT Topics

| Topic | Purpose | Payload Format |
|-------|---------|----------------|
| `IDD/morse/signal` | Morse code signals | `{"type": "DOT/DASH/WORD_GAP", "duration": 0.2, "timestamp": 1234567890}` |

### Payload Structure
```json
{
  "type": "DOT",           // Signal type: DOT, DASH, or WORD_GAP
  "duration": 0.2,         // Duration in seconds
  "timestamp": 1699123456  // Unix timestamp
}
```

## 🎓 Learning Objectives

This project demonstrates:
- ✅ **Distributed Communication**: Multiple devices coordinating via MQTT
- ✅ **Protocol Design**: Morse code as a communication protocol
- ✅ **Real-time Decoding**: State machine for pattern recognition
- ✅ **Hardware Integration**: Sensors, displays, LEDs, buzzers
- ✅ **Timing & Synchronization**: Proper morse code timing standards

## 🌟 Extensions & Ideas

### Easy Extensions
1. **Add encryption**: Encode message before morse conversion
2. **Group chat**: Multiple transmitters, color-coded by sender
3. **Speed control**: Adjustable WPM (words per minute)
4. **Save history**: Log all messages to file

### Advanced Extensions
1. **Auto-repeat**: Transmit message on loop
2. **Error correction**: Checksum validation
3. **Voice output**: Text-to-speech for decoded messages
4. **Web interface**: Control via browser instead of terminal

### Creative Ideas
1. **Morse code treasure hunt**: Hidden messages around campus
2. **Emergency beacon**: SOS with GPS coordinates
3. **Secret handshake**: Pattern-based authentication
4. **Music mode**: Convert morse to musical notes

## 📸 Documentation Photos

### Transmitter Setup
![Transmitter with LED](imgs/morse_transmitter_setup.jpg)
*Transmitter Pi with LED feedback during transmission*

### Receiver Display
![Receiver display showing decoded text](imgs/morse_receiver_display.jpg)
*Receiver Pi with MiniPiTFT showing decoded message*

### Multi-Device Setup
![Three Pis communicating](imgs/morse_multi_device.jpg)
*Complete system: 1 transmitter broadcasting to 2 receivers*

## 👥 User Testing Results

**Participants:** 2 students not on the project team

### Test 1: First-time Users
**Before trying:**
- "Is this like walkie-talkies?"
- "How fast can it send messages?"

**During use:**
- Surprised by real-time decoding
- Found LED feedback very helpful
- Wanted to try button mode immediately

**Feedback:**
- "The visual feedback makes it feel like a real telegraph!"
- "Could you add different sounds for dots vs dashes?"
- "Would be cool to see signal strength or distance"

### Test 2: Interactive Button Mode
**Observations:**
- Users naturally tried to spell "SOS" first
- Took 2-3 minutes to get comfortable with timing
- Collaboration emerged: one person dictating, another tapping

**Suggestions:**
- Add a "cheat sheet" display of common letters
- Show timing guide for dot vs dash duration
- Add haptic feedback on button

## 🤔 Reflection

### What Worked Well
- MQTT provides reliable message delivery with minimal latency
- Morse code timing standards work well for decoding
- Visual feedback (LED + display) crucial for usability
- Multiple receivers create interesting group dynamics

### Challenges
- **Timing synchronization**: Initial attempts had letter gaps too short
- **State management**: Tracking current letter vs complete words needed careful design
- **GPIO conflicts**: Display and LEDs initially competed for SPI bus
- **User patience**: Fast typing required slowing down for morse conversion

### Distributed Interaction Insights
- Broadcasting to multiple devices creates shared experience
- One-way communication feels different than chat (more like announcement)
- Physical feedback (LED, buzzer) makes wireless interaction tangible
- Turn-based coordination emerged naturally without explicit protocol

### Sensor Events Design
- Discrete events (DOT/DASH) easier to handle than continuous data
- Timeout-based state completion worked better than explicit "end" signals
- JSON payload provided flexibility for future extensions
- Timestamp enabled potential synchronization features

### Future Improvements
1. **Bi-directional**: Add acknowledgment system
2. **Compression**: Send whole letters instead of individual signals
3. **Priority levels**: Emergency messages interrupt normal traffic
4. **Network resilience**: Handle dropped messages gracefully
5. **Analytics**: Track WPM, accuracy, most common letters

## 📚 References & Resources

- [International Morse Code Standard](https://en.wikipedia.org/wiki/Morse_code)
- [MQTT Protocol Documentation](https://mqtt.org/)
- [Paho MQTT Python Client](https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php)
- [Raspberry Pi GPIO Documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)

## 🙏 Acknowledgments

- **Lab 6 Template**: Pixel grid example provided foundation for MQTT integration
- **AI Assistance**: GitHub Copilot used for morse code dictionary and timing calculations
- **Testing Partners**: Thanks to classmates for user testing feedback

---

**Project by:** [Your Name Here]  
**Course:** INFO5345/CS5424/ECE5413 - Developing and Designing Interactive Devices  
**Instructor:** Professor Wendy Ju  
**Date:** November 2025
