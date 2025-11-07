#!/usr/bin/env python3
"""
Morse Code MQTT Receiver with MiniPiTFT Display
Subscribes to MQTT messages and displays them on the Adafruit MiniPiTFT
Shows the decoded morse code message in real-time
"""

import paho.mqtt.client as mqtt
import uuid
import json
import time
import sys
from collections import deque

# MQTT Configuration
MQTT_BROKER = 'farlab.infosci.cornell.edu'
MQTT_PORT = 1883
MQTT_TOPIC = 'IDD/lab6/morse/coolguys/symbol'
MQTT_USERNAME = 'idd'
MQTT_PASSWORD = 'device@theFarm'

# Morse code dictionary for decoding
MORSE_TO_CHAR = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F',
    '--.': 'G', '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K', '.-..': 'L',
    '--': 'M', '-.': 'N', '---': 'O', '.--.': 'P', '--.-': 'Q', '.-.': 'R',
    '...': 'S', '-': 'T', '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X',
    '-.--': 'Y', '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
    '...--': '3', '....-': '4', '.....': '5', '-....': '6', '--...': '7',
    '---..': '8', '----.': '9'
}

# Display setup
try:
    import board
    import digitalio
    import busio
    from PIL import Image, ImageDraw, ImageFont
    import adafruit_rgb_display.st7789 as st7789
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False
    print("Display libraries not available - running in text-only mode")

# Message history
message_history = deque(maxlen=10)
current_message = ""
message_count = 0


def setup_display():
    """Setup the MiniPiTFT display"""
    if not DISPLAY_AVAILABLE:
        return None
    
    try:
        # Configuration for CS and DC pins
        cs_pin = digitalio.DigitalInOut(board.D5)   # GPIO5
        dc_pin = digitalio.DigitalInOut(board.D25)  # GPIO25
        reset_pin = None
        BAUDRATE = 64000000

        # Backlight
        backlight = digitalio.DigitalInOut(board.D22)
        backlight.switch_to_output()
        backlight.value = True
        
        # Buttons (optional - for scrolling through history)
        buttonA = digitalio.DigitalInOut(board.D23)
        buttonB = digitalio.DigitalInOut(board.D24)
        buttonA.switch_to_input(pull=digitalio.Pull.UP)
        buttonB.switch_to_input(pull=digitalio.Pull.UP)

        # Setup SPI bus
        spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)

        # Create the display
        disp = st7789.ST7789(
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
        
        print("Display initialized successfully")
        return disp, buttonA, buttonB
        
    except Exception as e:
        print(f"Display setup failed: {e}")
        return None, None, None


def update_display(disp, message, symbols="", msg_count=0):
    """Update the MiniPiTFT display with the current message"""
    if not disp:
        return
    
    try:
        # Create image (240x135 after rotation)
        width = 240
        height = 135
        image = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(image)
        
        # Background color
        draw.rectangle((0, 0, width, height), fill=(0, 0, 50))  # Dark blue
        
        # Load fonts
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
            font_message = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font_title = ImageFont.load_default()
            font_message = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Title bar
        draw.rectangle((0, 0, width, 25), fill=(0, 100, 200))
        draw.text((5, 5), "MORSE RECEIVER", font=font_title, fill=(255, 255, 255))
        
        # Message count
        draw.text((width - 40, 5), f"#{msg_count}", font=font_small, fill=(255, 255, 255))
        
        # Separator line
        draw.line((0, 25, width, 25), fill=(255, 255, 255), width=2)
        
        # Display morse symbols if available
        if symbols:
            y_pos = 35
            draw.text((5, y_pos), "Symbols:", font=font_small, fill=(150, 150, 150))
            draw.text((70, y_pos), symbols, font=font_small, fill=(255, 200, 0))
        
        # Main message (word-wrapped and centered)
        y_pos = 60 if symbols else 50
        
        if message:
            # Word wrap the message
            lines = []
            words = message.split()
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                # Approximate width check (adjust as needed)
                if len(test_line) <= 12:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Display lines (max 2 lines)
            for i, line in enumerate(lines[:2]):
                draw.text((10, y_pos + (i * 30)), line, font=font_message, fill=(0, 255, 0))
        else:
            draw.text((30, y_pos), "Waiting...", font=font_message, fill=(128, 128, 128))
        
        # Timestamp at bottom
        timestamp = time.strftime("%H:%M:%S")
        draw.text((5, height - 20), timestamp, font=font_small, fill=(200, 200, 200))
        
        # Display it (rotate 90 degrees for proper orientation)
        disp.image(image.rotate(90, expand=True))
        
    except Exception as e:
        print(f"Display update error: {e}")


def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"Connection failed with code {rc}")


def decode_morse_symbols(symbols_string):
    """Decode a string of morse symbols separated by spaces into text"""
    if not symbols_string:
        return ""
    
    letters = symbols_string.split()
    decoded = ""
    for letter_code in letters:
        char = MORSE_TO_CHAR.get(letter_code, '?')
        decoded += char
    return decoded


def on_message(client, userdata, msg):
    """Callback when a message is received"""
    global current_message, message_count
    
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        
        # Get symbols from payload and decode them
        symbols = payload.get('symbols', '')
        decoded_message = decode_morse_symbols(symbols)
        
        timestamp = time.strftime('%H:%M:%S', time.localtime(payload.get('timestamp', time.time())))
        count = payload.get('count', 0)
        
        # Update global state
        current_message = decoded_message
        message_count = count
        
        # Add to history
        message_history.append({
            'message': decoded_message,
            'symbols': symbols,
            'timestamp': timestamp,
            'count': count
        })
        
        # Print to console
        print("\n" + "="*60)
        print(f"Message Received at {timestamp}")
        print("="*60)
        print(f"Symbols:     {symbols}")
        print(f"Decoded:     {decoded_message}")
        print(f"Count:       #{count}")
        print("="*60 + "\n")
        
        # Update display
        disp = userdata.get('display')
        if disp:
            update_display(disp, decoded_message, symbols, count)
        
    except json.JSONDecodeError:
        print(f"\nRaw Message: {msg.payload.decode('utf-8')}\n")
    except Exception as e:
        print(f"\nError processing message: {e}\n")


def main():
    print("=" * 60)
    print("  Morse Code MQTT Receiver with Display")
    print("=" * 60)
    print()
    
    # Setup display
    print("Initializing display...")
    disp, buttonA, buttonB = setup_display()
    
    if disp:
        print("Display ready!")
        # Show waiting screen
        update_display(disp, "", "", 0)
    else:
        print("Running without display (text-only mode)")
    
    # Setup MQTT client
    print("Connecting to MQTT broker...")
    client = mqtt.Client(str(uuid.uuid1()))
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Pass display to callback via userdata
    client.user_data_set({'display': disp})
    
    try:
        client.connect(MQTT_BROKER, port=MQTT_PORT, keepalive=60)
        
    except Exception as e:
        print(f"Connection error: {e}")
        return
    
    print()
    print("=" * 60)
    print("Listening for morse code messages...")
    print(f"Topic: {MQTT_TOPIC}")
    print("Messages will appear on display")
    print("Press Ctrl+C to exit")
    print("=" * 60)
    print()
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        client.disconnect()
        print("Disconnected. Goodbye!")


if __name__ == '__main__':
    main()
