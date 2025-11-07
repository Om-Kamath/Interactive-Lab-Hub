#!/usr/bin/env python3
"""
Qwiic Button Morse Code MQTT Publisher
Uses button press duration to create morse code messages
Short press = DOT, Long press = DASH
Automatically decodes and publishes complete letters/words
"""

import paho.mqtt.client as mqtt
import qwiic_button
import time
import sys
import json
import uuid

# MQTT Configuration
MQTT_BROKER = 'farlab.infosci.cornell.edu'
MQTT_PORT = 1883
MQTT_TOPIC = 'IDD/lab6/morse/coolguys/symbol'
MQTT_USERNAME = 'idd'
MQTT_PASSWORD = 'device@theFarm'

# Morse code timing (in seconds)
DOT_THRESHOLD = 0.3  # Press < 0.3s = DOT
DASH_THRESHOLD = 0.3  # Press >= 0.3s = DASH
LETTER_GAP = 0.75     # Pause > 0.75s = complete letter and transmit
MESSAGE_SEND_GAP = 5.0  # Pause > 5s = publish complete message

# Morse code dictionary (reverse lookup)
MORSE_TO_CHAR = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F',
    '--.': 'G', '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K', '.-..': 'L',
    '--': 'M', '-.': 'N', '---': 'O', '.--.': 'P', '--.-': 'Q', '.-.': 'R',
    '...': 'S', '-': 'T', '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X',
    '-.--': 'Y', '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
    '...--': '3', '....-': '4', '.....': '5', '-....': '6', '--...': '7',
    '---..': '8', '----.': '9'
}

# State tracking
current_morse = ""
decoded_message = ""
morse_symbols = ""  # Track the raw morse symbols for the entire message
last_signal_time = 0
message_count = 0
message_published = False  # Track if current message has been published


def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("Connected to MQTT broker")
    else:
        print(f"Connection failed with code {rc}")


def publish_message(client, morse_symbols):
    """Publish morse symbols to the MQTT broker"""
    global message_count
    message_count += 1
    
    payload = json.dumps({
        'symbol': morse_symbols,
        'device_id': 'om',
        'timestamp': time.time(),
        'count': message_count
    })
    
    result = client.publish(MQTT_TOPIC, payload)
    
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"Published symbols: {morse_symbols}")
    else:
        print(f"Publish failed with code {result.rc}")
    
    return result


def decode_morse(morse_pattern):
    """Decode morse code pattern to character"""
    return MORSE_TO_CHAR.get(morse_pattern, '?')


def process_morse_input(button, mqtt_client):
    """Process button press and convert to morse code"""
    global current_morse, decoded_message, morse_symbols, last_signal_time, message_published
    
    # Wait for button press
    if not button.is_button_pressed():
        # Check if we should complete a letter
        if last_signal_time > 0:
            time_since_last = time.time() - last_signal_time
            
            # Complete current letter if there's morse code pending
            if current_morse and time_since_last > LETTER_GAP:
                char = decode_morse(current_morse)
                
                # Publish immediately for this letter
                print(f"\n[{current_morse}] = '{char}'")
                publish_message(mqtt_client, current_morse)
                print(f"Transmitted: '{current_morse}' -> '{char}'")
                
                # Track for display purposes
                decoded_message += char
                morse_symbols += current_morse + " "
                print(f"Message so far: '{decoded_message}'")
                
                current_morse = ""
                print()
        
        return
    
    # Button is pressed - measure duration
    press_start = time.time()
    button.LED_on(True)
    
    # Wait for release
    while button.is_button_pressed():
        time.sleep(0.01)
    
    press_duration = time.time() - press_start
    button.LED_off()
    
    # Determine DOT or DASH
    if press_duration < DOT_THRESHOLD:
        current_morse += '.'
        print('.', end='', flush=True)
    else:
        current_morse += '-'
        print('-', end='', flush=True)
    
    last_signal_time = time.time()


def main():
    global current_morse, decoded_message, last_signal_time, message_published
    
    print("=" * 60)
    print("  Qwiic Button Morse Code MQTT Publisher")
    print("=" * 60)
    print()
    print("Instructions:")
    print("  - SHORT press (< 0.3s) = DOT (.)")
    print("  - LONG press (>= 0.3s) = DASH (-)")
    print("  - Pause 0.75s = Complete letter & TRANSMIT")
    print()
    print("Example: Press ... (pause 0.75s) -> Transmits 'S'")
    print("         Press --- (pause 0.75s) -> Transmits 'O'")
    print("Note: Each letter transmits immediately")
    print("=" * 60)
    print()
    
    # Initialize Qwiic Button
    print("Initializing Qwiic Button...")
    my_button = qwiic_button.QwiicButton()
    
    if not my_button.begin():
        print("Qwiic Button not connected! Check your connection.")
        sys.exit(1)
    
    print("Qwiic Button ready!")
    
    # Blink LED to show ready
    for _ in range(3):
        my_button.LED_on(True)
        time.sleep(0.1)
        my_button.LED_off()
        time.sleep(0.1)
    
    # Setup MQTT client
    print("Connecting to MQTT broker...")
    mqtt_client = mqtt.Client(str(uuid.uuid1()))
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    
    try:
        mqtt_client.connect(MQTT_BROKER, port=MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        time.sleep(2)  # Wait for connection
        
        if not mqtt_client.is_connected():
            print("Failed to connect to MQTT broker")
            sys.exit(1)
            
    except Exception as e:
        print(f"MQTT connection error: {e}")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("Ready! Start tapping morse code")
    print(f"Topic: {MQTT_TOPIC}")
    print("Press Ctrl+C to exit")
    print("=" * 60)
    print()
    
    last_signal_time = time.time()
    
    try:
        while True:
            process_morse_input(my_button, mqtt_client)
            time.sleep(0.01)  # Small delay
            
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        
        # Publish final letter if in progress
        if current_morse.strip():
            char = decode_morse(current_morse)
            print(f"\nFinal letter: '{current_morse}' -> '{char}'")
            publish_message(mqtt_client, current_morse.strip())
        
        # Show complete message
        if decoded_message.strip():
            print(f"\nComplete message sent: '{decoded_message.strip()}'")
            print(f"All symbols: '{morse_symbols.strip()}'")
            
    finally:
        my_button.LED_off()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Disconnected. Goodbye!")


if __name__ == '__main__':
    main()

