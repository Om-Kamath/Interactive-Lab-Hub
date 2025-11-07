#!/usr/bin/env python3
"""
MQTT Morse Code Message Receiver
Listens for morse code messages published by the Qwiic button
Displays both the morse pattern and decoded text
"""

import paho.mqtt.client as mqtt
import uuid
import json
import time

# MQTT Configuration
MQTT_BROKER = 'farlab.infosci.cornell.edu'
MQTT_PORT = 1883
MQTT_TOPIC = 'IDD/kom/mood'
MQTT_USERNAME = 'idd'
MQTT_PASSWORD = 'device@theFarm'


def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Callback when a message is received"""
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        timestamp = time.strftime('%H:%M:%S', time.localtime(payload.get('timestamp', time.time())))
        
        print(f"\n{'='*60}")
        print(f"Message Received at {timestamp}")
        print(f"{'='*60}")
        
        # Display morse pattern if available
        if payload.get('morse'):
            print(f"Morse Code:  {payload.get('morse')}")
        
        # Display decoded message
        print(f"Decoded:     {payload.get('message', 'N/A')}")
        print(f"Count:       #{payload.get('count', 'N/A')}")
        print(f"{'='*60}\n")
        
    except json.JSONDecodeError:
        print(f"\nRaw Message: {msg.payload.decode('utf-8')}\n")
    except Exception as e:
        print(f"\nError processing message: {e}\n")


def main():
    print("=" * 60)
    print("  MQTT Morse Code Message Receiver")
    print("=" * 60)
    print()
    
    # Setup MQTT client
    print("Connecting to MQTT broker...")
    client = mqtt.Client(str(uuid.uuid1()))
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, port=MQTT_PORT, keepalive=60)
        
    except Exception as e:
        print(f"Connection error: {e}")
        return
    
    print()
    print("=" * 60)
    print("Listening for morse code messages...")
    print(f"Topic: {MQTT_TOPIC}")
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
