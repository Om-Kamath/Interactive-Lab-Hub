#!/usr/bin/env python3
"""
Morse Code Transmitter
Converts text messages to morse code and transmits via MQTT
Can use button input for interactive morse sending
"""

import paho.mqtt.client as mqtt
import uuid
import time
import signal
import sys

# MQTT Configuration
MQTT_BROKER = 'farlab.infosci.cornell.edu'
MQTT_PORT = 1883
MQTT_TOPIC = 'IDD/morse/signal'
MQTT_USERNAME = 'idd'
MQTT_PASSWORD = 'device@theFarm'

# Morse Code Dictionary
MORSE_CODE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---',
    '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.', ' ': '/', '.': '.-.-.-', ',': '--..--',
    '?': '..--..', '!': '-.-.--', '/': '-..-.', '(': '-.--.', ')': '-.--.-',
    '&': '.-...', ':': '---...', ';': '-.-.-.', '=': '-...-', '+': '.-.-.',
    '-': '-....-', '_': '..--.-', '"': '.-..-.', '$': '...-..-', '@': '.--.-.'
}

# Morse timing (in seconds)
DOT_DURATION = 0.2
DASH_DURATION = DOT_DURATION * 3
SYMBOL_GAP = DOT_DURATION
LETTER_GAP = DOT_DURATION * 3
WORD_GAP = DOT_DURATION * 7

# Optional: Hardware integration (uncomment if using GPIO)
try:
    import RPi.GPIO as GPIO
    import board
    import digitalio
    HARDWARE_AVAILABLE = True
    
    # LED setup (change pin as needed)
    LED_PIN = 18  # GPIO18 (Physical pin 12)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    
    # Optional: Button setup for interactive sending
    BUTTON_PIN = 23  # GPIO23 (Physical pin 16)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
except ImportError:
    HARDWARE_AVAILABLE = False
    print("GPIO not available - running in software-only mode")


class MorseTransmitter:
    def __init__(self):
        self.client = mqtt.Client(str(uuid.uuid1()))
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.connected = False
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✓ Connected to MQTT broker")
            self.connected = True
        else:
            print(f"✗ Connection failed with code {rc}")
            
    def connect(self):
        """Connect to MQTT broker"""
        print(f"Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 5
            while not self.connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
                
            if not self.connected:
                print("Connection timeout!")
                return False
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def text_to_morse(self, text):
        """Convert text to morse code"""
        morse = []
        for char in text.upper():
            if char in MORSE_CODE:
                morse.append(MORSE_CODE[char])
            elif char == ' ':
                morse.append('/')
        return morse
    
    def send_morse_signal(self, signal_type, duration=None):
        """Send a morse signal (DOT, DASH, or GAP) via MQTT"""
        if duration is None:
            duration = DOT_DURATION if signal_type == 'DOT' else DASH_DURATION
            
        payload = {
            'type': signal_type,
            'duration': duration,
            'timestamp': time.time()
        }
        
        import json
        self.client.publish(MQTT_TOPIC, json.dumps(payload))
        
        # Visual feedback with LED
        if HARDWARE_AVAILABLE and signal_type in ['DOT', 'DASH']:
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(duration)
            GPIO.output(LED_PIN, GPIO.LOW)
        else:
            time.sleep(duration)
    
    def transmit_morse(self, text):
        """Transmit complete message in morse code"""
        print(f"\n📡 Transmitting: '{text}'")
        morse_list = self.text_to_morse(text)
        
        for i, morse_char in enumerate(morse_list):
            # Print what we're sending
            original_char = [k for k, v in MORSE_CODE.items() if v == morse_char]
            if original_char:
                print(f"  {original_char[0]}: {morse_char}")
            
            # Word gap
            if morse_char == '/':
                print("  [WORD GAP]")
                self.send_morse_signal('WORD_GAP', WORD_GAP)
                continue
            
            # Send dots and dashes
            for symbol in morse_char:
                if symbol == '.':
                    print("  •", end='', flush=True)
                    self.send_morse_signal('DOT')
                elif symbol == '-':
                    print("  —", end='', flush=True)
                    self.send_morse_signal('DASH')
                
                # Gap between symbols in a letter
                time.sleep(SYMBOL_GAP)
            
            print()  # Newline
            
            # Gap between letters
            if i < len(morse_list) - 1:
                time.sleep(LETTER_GAP)
        
        print("✓ Transmission complete!\n")
    
    def interactive_mode(self):
        """Interactive mode with button input (if hardware available)"""
        if not HARDWARE_AVAILABLE:
            print("Interactive mode requires GPIO hardware")
            return
        
        print("\n🔘 INTERACTIVE MORSE MODE")
        print("Press button to send DOT")
        print("Hold button to send DASH")
        print("Release to pause")
        print("Press Ctrl+C to exit\n")
        
        try:
            while True:
                # Wait for button press
                if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    press_time = time.time()
                    
                    # Wait for release
                    while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                        time.sleep(0.01)
                    
                    release_time = time.time()
                    duration = release_time - press_time
                    
                    # Determine if DOT or DASH
                    if duration < DASH_DURATION:
                        print("•", end='', flush=True)
                        self.send_morse_signal('DOT')
                    else:
                        print("—", end='', flush=True)
                        self.send_morse_signal('DASH')
                    
                    time.sleep(SYMBOL_GAP)
                    
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\n\nExiting interactive mode...")
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        if HARDWARE_AVAILABLE:
            GPIO.cleanup()


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Shutting down...")
    if HARDWARE_AVAILABLE:
        GPIO.cleanup()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("   MORSE CODE TRANSMITTER")
    print("=" * 60)
    
    transmitter = MorseTransmitter()
    
    if not transmitter.connect():
        print("Failed to connect to MQTT broker")
        return
    
    print("\nMorse Code Transmitter Ready!")
    print("Topic:", MQTT_TOPIC)
    print("\nOptions:")
    print("1. Type a message to transmit")
    print("2. Type 'interactive' for button mode (requires hardware)")
    print("3. Type 'quit' to exit\n")
    
    try:
        while True:
            message = input("Enter message: ").strip()
            
            if not message:
                continue
            
            if message.lower() == 'quit':
                break
            
            if message.lower() == 'interactive':
                transmitter.interactive_mode()
                continue
            
            transmitter.transmit_morse(message)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n")
    finally:
        transmitter.disconnect()
        print("Disconnected. Goodbye! 👋")


if __name__ == "__main__":
    main()
