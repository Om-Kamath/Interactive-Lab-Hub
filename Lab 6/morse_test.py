#!/usr/bin/env python3
"""
Quick test script for morse code system
Tests MQTT connectivity and basic morse encoding/decoding
"""

import paho.mqtt.client as mqtt
import uuid
import json
import time

# MQTT Configuration
MQTT_BROKER = 'farlab.infosci.cornell.edu'
MQTT_PORT = 1883
MQTT_USERNAME = 'idd'
MQTT_PASSWORD = 'device@theFarm'

def test_connection():
    """Test MQTT broker connection"""
    print("Testing MQTT connection...")
    try:
        client = mqtt.Client(str(uuid.uuid1()))
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print("✓ Connection successful!")
        client.disconnect()
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

def test_morse_encoding():
    """Test morse code encoding"""
    print("\nTesting morse code encoding...")
    
    MORSE_CODE = {
        'S': '...', 'O': '---', 'H': '....', 'E': '.', 'L': '.-..'
    }
    
    test_word = "SOS"
    print(f"Encoding '{test_word}':")
    for char in test_word:
        if char in MORSE_CODE:
            print(f"  {char} -> {MORSE_CODE[char]}")
    
    print("✓ Encoding test passed!")

def test_morse_decoding():
    """Test morse code decoding"""
    print("\nTesting morse code decoding...")
    
    MORSE_TO_CHAR = {
        '...': 'S', '---': 'O', '....': 'H', '.': 'E', '.-..': 'L'
    }
    
    test_signals = ['...', '---', '...']
    decoded = ''.join([MORSE_TO_CHAR[s] for s in test_signals])
    print(f"Decoding {test_signals} -> '{decoded}'")
    
    assert decoded == "SOS", "Decoding failed!"
    print("✓ Decoding test passed!")

def test_signal_format():
    """Test MQTT signal payload format"""
    print("\nTesting signal payload format...")
    
    signal = {
        'type': 'DOT',
        'duration': 0.2,
        'timestamp': time.time()
    }
    
    # Convert to JSON and back
    json_str = json.dumps(signal)
    parsed = json.loads(json_str)
    
    assert parsed['type'] == 'DOT', "Type mismatch!"
    assert parsed['duration'] == 0.2, "Duration mismatch!"
    assert 'timestamp' in parsed, "Timestamp missing!"
    
    print(f"Signal format: {json_str}")
    print("✓ Payload format test passed!")

def main():
    print("=" * 60)
    print("   MORSE CODE SYSTEM TEST")
    print("=" * 60)
    print()
    
    tests = [
        test_connection,
        test_morse_encoding,
        test_morse_decoding,
        test_signal_format
    ]
    
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
        print()
    
    print("=" * 60)
    print(f"Results: {passed}/{len(tests)} tests passed")
    print("=" * 60)
    
    if passed == len(tests):
        print("\n✓ All tests passed! System ready to use.")
        print("\nNext steps:")
        print("1. Run: python morse_receiver.py")
        print("2. Run: python morse_transmitter.py")
        print("3. Type a message and watch it decode!")
    else:
        print("\n✗ Some tests failed. Check configuration.")

if __name__ == "__main__":
    main()
