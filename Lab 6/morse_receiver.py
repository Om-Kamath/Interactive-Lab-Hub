#!/usr/bin/env python3
"""
Morse Code Receiver
Subscribes to MQTT morse code signals and decodes them to text
Provides visual feedback with display and/or LED
"""

import paho.mqtt.client as mqtt
import uuid
import json
import time
import signal
import sys
from collections import deque

# MQTT Configuration
MQTT_BROKER = 'farlab.infosci.cornell.edu'
MQTT_PORT = 1883
MQTT_TOPIC = 'IDD/morse/signal'
MQTT_USERNAME = 'idd'
MQTT_PASSWORD = 'device@theFarm'

# Morse Code Dictionary (reverse lookup)
MORSE_TO_CHAR = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F',
    '--.': 'G', '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K', '.-..': 'L',
    '--': 'M', '-.': 'N', '---': 'O', '.--.': 'P', '--.-': 'Q', '.-.': 'R',
    '...': 'S', '-': 'T', '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X',
    '-.--': 'Y', '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
    '...--': '3', '....-': '4', '.....': '5', '-....': '6', '--...': '7',
    '---..': '8', '----.': '9', '/': ' ', '.-.-.-': '.', '--..--': ',',
    '..--..': '?', '-.-.--': '!', '-..-.': '/', '-.--.': '(', '-.--.-': ')',
    '.-...': '&', '---...': ':', '-.-.-.': ';', '-...-': '=', '.-.-.': '+',
    '-....-': '-', '..--.-': '_', '.-..-.': '"', '...-..-': '$', '.---.': '@'
}

# Timing thresholds for decoding
LETTER_TIMEOUT = 1.0  # Seconds of silence to complete a letter
WORD_TIMEOUT = 2.0    # Seconds of silence to add a space

# Optional: Hardware integration
try:
    import RPi.GPIO as GPIO
    import board
    import digitalio
    from PIL import Image, ImageDraw, ImageFont
    import adafruit_rgb_display.st7789 as st7789
    HARDWARE_AVAILABLE = True
    DISPLAY_AVAILABLE = True
    
    # LED setup for visual feedback
    LED_PIN = 18  # GPIO18 (Physical pin 12)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    
    # Optional: Buzzer for audio feedback
    BUZZER_PIN = 17  # GPIO17 (Physical pin 11)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    
except ImportError:
    HARDWARE_AVAILABLE = False
    DISPLAY_AVAILABLE = False
    print("GPIO/Display not available - running in text-only mode")


class MorseReceiver:
    def __init__(self):
        self.client = mqtt.Client(str(uuid.uuid1()))
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.connected = False
        
        # Decoding state
        self.current_letter = ""
        self.decoded_message = ""
        self.last_signal_time = time.time()
        self.display = None
        
        # Signal history for display
        self.signal_history = deque(maxlen=50)
        
        # Setup display if available
        if DISPLAY_AVAILABLE:
            self.setup_display()
    
    def setup_display(self):
        """Setup the MiniPiTFT display"""
        try:
            cs_pin = digitalio.DigitalInOut(board.D5)
            dc_pin = digitalio.DigitalInOut(board.D25)
            reset_pin = None
            BAUDRATE = 64000000

            backlight = digitalio.DigitalInOut(board.D22)
            backlight.switch_to_output()
            backlight.value = True

            import busio
            spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)

            self.display = st7789.ST7789(
                spi,
                cs=cs_pin,
                dc=dc_pin,
                rst=reset_pin,
                baudrate=BAUDRATE,
                width=135,
                height=240,
                x_offset=53,
                y_offset=40,
            )
            
            print("✓ Display initialized")
            self.update_display()
            
        except Exception as e:
            print(f"Display setup failed: {e}")
            self.display = None
    
    def update_display(self):
        """Update the display with current message"""
        if not self.display:
            return
        
        try:
            # Create image
            image = Image.new("RGB", (240, 135), (0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Load fonts
            try:
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Title
            draw.text((5, 5), "MORSE RECEIVER", font=font_small, fill=(0, 255, 0))
            
            # Current letter being decoded
            if self.current_letter:
                draw.text((5, 25), f"Current: {self.current_letter}", font=font_small, fill=(255, 255, 0))
            
            # Decoded message (word-wrapped)
            y_offset = 45
            msg = self.decoded_message[-60:]  # Last 60 chars
            lines = [msg[i:i+20] for i in range(0, len(msg), 20)]
            for line in lines[-4:]:  # Show last 4 lines
                draw.text((5, y_offset), line, font=font_large, fill=(255, 255, 255))
                y_offset += 20
            
            # Display it (rotated 90 degrees for proper orientation)
            self.display.image(image.rotate(90, expand=True))
            
        except Exception as e:
            print(f"Display update error: {e}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✓ Connected to MQTT broker")
            client.subscribe(MQTT_TOPIC)
            print(f"✓ Subscribed to {MQTT_TOPIC}")
            self.connected = True
        else:
            print(f"✗ Connection failed with code {rc}")
    
    def on_message(self, client, userdata, msg):
        """Handle incoming morse signals"""
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            signal_type = payload.get('type')
            duration = payload.get('duration', 0)
            
            # Visual/audio feedback
            if HARDWARE_AVAILABLE:
                if signal_type in ['DOT', 'DASH']:
                    GPIO.output(LED_PIN, GPIO.HIGH)
                    GPIO.output(BUZZER_PIN, GPIO.HIGH)
                    time.sleep(duration)
                    GPIO.output(LED_PIN, GPIO.LOW)
                    GPIO.output(BUZZER_PIN, GPIO.LOW)
            
            # Decode the signal
            if signal_type == 'DOT':
                self.current_letter += '.'
                print('•', end='', flush=True)
                self.signal_history.append('•')
            elif signal_type == 'DASH':
                self.current_letter += '-'
                print('—', end='', flush=True)
                self.signal_history.append('—')
            elif signal_type == 'WORD_GAP':
                self.complete_letter()
                self.decoded_message += ' '
                print(' [SPACE] ', end='', flush=True)
                self.signal_history.append(' ')
            
            self.last_signal_time = time.time()
            
        except json.JSONDecodeError:
            print(f"Invalid JSON: {msg.payload}")
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def complete_letter(self):
        """Complete the current letter and decode it"""
        if self.current_letter:
            if self.current_letter in MORSE_TO_CHAR:
                char = MORSE_TO_CHAR[self.current_letter]
                self.decoded_message += char
                print(f" [{char}]", end='', flush=True)
            else:
                print(f" [?{self.current_letter}]", end='', flush=True)
            
            self.current_letter = ""
            self.update_display()
    
    def check_timeouts(self):
        """Check if we need to complete a letter or add a space"""
        current_time = time.time()
        time_since_last = current_time - self.last_signal_time
        
        # Complete letter after timeout
        if self.current_letter and time_since_last > LETTER_TIMEOUT:
            self.complete_letter()
    
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
    
    def run(self):
        """Main receiver loop"""
        print("\n🎧 Listening for morse code signals...")
        print("Decoded message will appear below:")
        print("-" * 60)
        
        try:
            while True:
                self.check_timeouts()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n")
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        if HARDWARE_AVAILABLE:
            GPIO.cleanup()
    
    def print_summary(self):
        """Print the decoded message summary"""
        print("\n" + "=" * 60)
        print("DECODED MESSAGE:")
        print("=" * 60)
        print(self.decoded_message)
        print("=" * 60)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Shutting down...")
    if HARDWARE_AVAILABLE:
        GPIO.cleanup()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("   MORSE CODE RECEIVER")
    print("=" * 60)
    
    receiver = MorseReceiver()
    
    if not receiver.connect():
        print("Failed to connect to MQTT broker")
        return
    
    print("\nMorse Code Receiver Ready!")
    print("Topic:", MQTT_TOPIC)
    
    if HARDWARE_AVAILABLE:
        print("Hardware: LED on GPIO", LED_PIN)
        print("          Buzzer on GPIO", BUZZER_PIN)
    
    print("\nPress Ctrl+C to exit\n")
    
    try:
        receiver.run()
    except KeyboardInterrupt:
        print("\n")
    finally:
        receiver.print_summary()
        receiver.disconnect()
        print("\nDisconnected. Goodbye! 👋")


if __name__ == "__main__":
    main()
