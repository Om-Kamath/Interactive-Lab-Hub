#!/bin/bash

echo "Setting up Voice Recorder with Adafruit Display"
echo "=============================================="

# Make sure we're in the Lab 3 directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# Install required Python packages
echo "Installing Python packages..."
pip install --upgrade pip

# Core packages
pip install sounddevice numpy pillow

# Adafruit packages (if not already installed)
pip install adafruit-blinka adafruit-circuitpython-rgb-display adafruit-circuitpython-mpr121

# Audio processing
pip install wave

# Speech recognition (optional but recommended)
echo "Installing Vosk for speech recognition..."
pip install vosk

# Download a small English model for Vosk (if not exists)
if [ ! -d "/home/pi/vosk-model-small-en-us-0.15" ]; then
    echo "Downloading Vosk speech model..."
    cd /home/pi
    wget -q https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    if [ -f "vosk-model-small-en-us-0.15.zip" ]; then
        unzip -q vosk-model-small-en-us-0.15.zip
        rm vosk-model-small-en-us-0.15.zip
        echo "✅ Vosk model installed"
    else
        echo "⚠️  Failed to download Vosk model - speech recognition may not work"
    fi
    cd - > /dev/null
fi

echo ""
echo "Setup complete! 🎉"
echo ""
echo "To run the voice recorder:"
echo "  python3 voice_recorder_display.py"
echo ""
echo "To run the speech listener (with recognition):"  
echo "  python3 speech_listener_display.py"
echo ""
echo "Hardware setup:"
echo "  - Connect your Adafruit display as usual"
if command -v gpio &> /dev/null; then
    echo "  - For button: Connect button between GPIO 21 and GND"
fi
echo "  - For touch: Use MPR121 capacitive touch sensor on I2C"
echo "  - Make sure microphone is connected (webcam or USB mic)"
echo ""