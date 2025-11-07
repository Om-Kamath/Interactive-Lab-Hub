# Lab 6 AI Interaction Log - Distributed Interaction

This file automatically logs all significant interactions between students and WendyTA (GitHub Copilot Chat) during Lab 6.

## How to Use This Log
- **Automatic**: WendyTA appends entries when providing substantial help
- **Timestamped**: Each interaction includes date/time in YYYY-MM-DD HH:MM:SS format
- **Commit Required**: Students must commit this file with their lab submission
- **Attribution**: Reference this log in your Lab 6 README.md under "AI Usage"

## Log Entries
*Interactions will be automatically appended below with timestamps*

---

## [2025-11-05 14:30:00] - Morse Code MQTT System Development
**AI Assistant**: GitHub Copilot Chat (WendyTA)

### Code Changes
- **Files Created**: 
  - `Lab 6/morse_transmitter.py` - Complete morse code transmitter with MQTT
  - `Lab 6/morse_receiver.py` - Real-time morse code receiver with decoding
  - `Lab 6/morse_test.py` - Test suite for system validation
  - `Lab 6/MORSE_README.md` - Comprehensive documentation
- **AI-Generated Code**: Full implementation of morse code communication system
  - MQTT publish/subscribe architecture
  - International morse code dictionary and timing standards
  - Hardware integration (LED, buzzer, button, display)
  - Real-time decoding with timeout-based state machine
  - Interactive button mode for manual morse input
- **Student Modifications**: Student requested "morse code transmitter and receiver using MQTT"

### Interaction Summary
- **Questions Asked**: 
  - "I want to build a morse code transmitter and receiver using MQTT. Refer to all the files in Lab 6"
- **Answers Provided**: 
  - Created complete distributed morse code system with transmitter and receiver
  - Integrated with existing Lab 6 MQTT infrastructure
  - Added hardware support for LEDs, buzzer, buttons, and MiniPiTFT display
  - Provided comprehensive documentation with usage examples
  - Included test script for validation
  - Created architecture diagrams and troubleshooting guide
- **Learning Objectives**: 
  - Understanding MQTT publish/subscribe messaging patterns
  - Implementing protocol encoding/decoding (morse code)
  - Working with distributed real-time systems
  - Hardware integration with GPIO devices
  - State machine design for pattern recognition
  - Proper MQTT topic structure and payload design

### Technical Details
**MQTT Configuration:**
- Broker: `farlab.infosci.cornell.edu:1883`
- Topic: `IDD/morse/signal`
- Payload: JSON with signal type, duration, timestamp

**Morse Code Implementation:**
- International morse standard (ITU-R M.1677-1)
- Timing: DOT=200ms, DASH=600ms, proper gaps
- Full alphanumeric + punctuation support
- Timeout-based letter completion

**Hardware Integration:**
- LED on GPIO 18 for visual feedback
- Buzzer on GPIO 17 for audio feedback
- Button on GPIO 23 for interactive mode
- MiniPiTFT display for decoded message output

### Key Design Decisions
1. **JSON Payloads**: Flexible format for future extensions (e.g., sender ID, priority)
2. **Timeout Decoding**: More robust than explicit "end letter" signals
3. **Graceful Degradation**: Works without hardware (software-only mode)
4. **Broadcasting Model**: One transmitter, multiple receivers for group experience

### Next Steps
- Test with multiple Pis (3+ devices recommended)
- Conduct user testing with non-team members
- Document setup photos and interaction videos
- Add acknowledgment system for bi-directional communication
- Consider encryption or error correction extensions

### Files to Commit
- `morse_transmitter.py`
- `morse_receiver.py`
- `morse_test.py`
- `MORSE_README.md`
- `WendyTA/logs/Lab6_ai_interaction_log.md` (this file)

---

## [2025-11-06 10:15:00] - Qwiic Button MQTT Integration
**AI Assistant**: GitHub Copilot Chat (WendyTA)

### Code Changes
- **Files Modified**: 
  - `Lab 6/final_submission.py` - Added complete Qwiic button MQTT publisher
- **Files Created**:
  - `Lab 6/button_receiver.py` - MQTT message receiver for testing
- **AI-Generated Code**: 
  - Button press detection with debouncing
  - MQTT publish on button click
  - LED feedback on button press
  - JSON payload formatting with timestamp and counter
  - Graceful error handling and cleanup

### Interaction Summary
- **Questions Asked**: 
  1. "Which code snippet from this is publishing information to the mqtt server?" (from pixel_grid_publisher.py)
  2. "On clicking the qwiic button, I want to publish the message to the broker"
- **Answers Provided**: 
  - Explained the `client.publish()` method and how MQTT publishing works
  - Created complete Qwiic button integration with MQTT
  - Added button state tracking to prevent multiple triggers
  - Implemented LED feedback for visual confirmation
  - Created companion receiver script for testing
  - Included proper connection handling and error messages
- **Learning Objectives**: 
  - Understanding MQTT `client.publish()` method
  - Button debouncing and state management
  - Event-driven publishing (trigger on button press)
  - Hardware feedback integration (LED control)
  - JSON payload structure and formatting
  - MQTT client connection lifecycle

### Technical Details
**MQTT Publishing:**
```python
result = client.publish(MQTT_TOPIC, payload)
```
- Topic: `IDD/kom/mood`
- Payload structure: `{'message': str, 'timestamp': float, 'count': int}`

**Button Integration:**
- Uses `qwiic_button.QwiicButton()` library
- Detects state transitions (not pressed → pressed)
- Debouncing via button release detection
- LED flashes on successful publish

**Key Features:**
- Button press counter tracks total clicks
- LED provides immediate visual feedback
- Graceful shutdown on Ctrl+C
- Connection validation before main loop
- Non-blocking button polling

### Student Understanding Check
Student asked about MQTT publishing mechanism, showing they want to understand:
1. **How** data is sent (the `client.publish()` method)
2. **When** to send data (on button events)
3. **What** to send (message payload structure)

This demonstrates good learning progression from understanding examples to implementing custom behavior.

### Next Steps
- Test with button_receiver.py on another Pi or terminal
- Add custom message content (sensor data, user input, etc.)
- Consider adding multiple buttons with different messages
- Integrate with other Lab 6 distributed systems
- Add message acknowledgment or response handling

### Files to Commit
- `final_submission.py`
- `button_receiver.py`
- `WendyTA/logs/Lab6_ai_interaction_log.md` (this file)

---

## [2025-11-06 15:45:00] - MiniPiTFT Display Receiver Integration
**AI Assistant**: GitHub Copilot Chat (WendyTA)

### Code Changes
- **Files Created**: 
  - `Lab 6/morse_display_receiver.py` - MQTT receiver with MiniPiTFT display support
- **AI-Generated Code**: 
  - Complete MQTT subscriber with display integration
  - Real-time message display on MiniPiTFT
  - Visual formatting with title bar, message count, timestamp
  - Word-wrapping for longer messages
  - Color-coded display elements
  - Graceful fallback to text-only mode if display unavailable

### Interaction Summary
- **Questions Asked**: 
  - "Now can you create a separate file for the receiver, where it will read messages published on the broker and display it on the adafruit minipitft display"
- **Answers Provided**: 
  - Created complete display receiver with MQTT subscription
  - Integrated MiniPiTFT display with proper orientation
  - Added visual design with color coding (blue background, green text, yellow morse)
  - Included message history tracking
  - Added timestamp and message counter display
  - Provided graceful degradation for systems without display
- **Learning Objectives**: 
  - Integrating hardware displays with MQTT receivers
  - Real-time visual feedback for distributed systems
  - Display layout and text formatting
  - Message buffering and history management
  - User experience design for physical displays

### Technical Details
**Display Configuration:**
- Resolution: 240x135 (after 90° rotation)
- Interface: SPI bus
- Pins: CS=GPIO5, DC=GPIO25, Backlight=GPIO22
- Rotation: 90° for proper orientation

**Display Layout:**
```
┌─────────────────────────────────┐
│ MORSE RECEIVER           #3     │ ← Title bar (blue)
├─────────────────────────────────┤
│ Morse: ... --- ...              │ ← Pattern (yellow)
│                                 │
│     HELLO                       │ ← Message (green, large)
│                                 │
│ 14:30:45                        │ ← Timestamp (gray)
└─────────────────────────────────┘
```

**Key Features:**
- Title bar with message counter
- Optional morse code pattern display
- Large, readable message text (24pt font)
- Word wrapping for longer messages (max 2 lines)
- Real-time timestamp
- Color coding for visual hierarchy
- Message history buffer (last 10 messages)

### Design Decisions
1. **Visual Hierarchy**: Title → Pattern → Message → Timestamp
2. **Color Psychology**: Blue = system, Yellow = technical, Green = success
3. **Font Sizing**: 24pt for main message (readability at distance)
4. **Word Wrapping**: 12 characters per line for 24pt font
5. **Rotation**: 90° to match physical display orientation
6. **Fallback Mode**: Text-only if display unavailable

### User Experience
- **At a Glance**: Large text shows current message immediately
- **Context**: Title bar shows it's the receiver, counter shows activity
- **Technical Detail**: Morse pattern for learning/verification
- **Temporal Context**: Timestamp shows when message arrived

### Next Steps
- Test display receiver on Pi with MiniPiTFT
- Verify button transmitter → display receiver flow
- Add button controls for scrolling through message history
- Consider adding visual alerts (flashing) for new messages
- Test with multiple transmitters

### Files to Commit
- `morse_display_receiver.py`
- `final_submission.py` (simplified single-word mode)
- `button_receiver.py` (console-only receiver)
- `WendyTA/logs/Lab6_ai_interaction_log.md` (this file)

---
