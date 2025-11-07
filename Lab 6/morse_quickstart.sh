#!/bin/bash
# Quick Start Script for Morse Code System
# Sets up environment and runs basic tests

echo "=========================================="
echo "  MORSE CODE SYSTEM - QUICK START"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "morse_transmitter.py" ]; then
    echo "❌ Error: Please run this from Lab 6 directory"
    echo "   cd \"Lab 6\""
    exit 1
fi

echo "📦 Step 1: Setting up Python environment..."
if [ ! -d ".venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv .venv
fi

echo "   Activating virtual environment..."
source .venv/bin/activate

echo ""
echo "📦 Step 2: Installing dependencies..."
pip install -q paho-mqtt pillow || {
    echo "❌ Installation failed. Try manually:"
    echo "   pip install paho-mqtt pillow"
    exit 1
}

echo "✓ Dependencies installed"
echo ""

echo "🧪 Step 3: Running system tests..."
python morse_test.py

echo ""
echo "=========================================="
echo "  READY TO USE!"
echo "=========================================="
echo ""
echo "On RECEIVER Pi:"
echo "  python morse_receiver.py"
echo ""
echo "On TRANSMITTER Pi:"
echo "  python morse_transmitter.py"
echo ""
echo "📖 Full documentation: MORSE_README.md"
echo ""
