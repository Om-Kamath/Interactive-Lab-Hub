#!/usr/bin/env python3
from gpiozero import Button
import time
import requests
import urllib.parse
import subprocess
import queue
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import tempfile
import requests
import os

# Initialize Vosk model once at startup
model = Model(lang="en-us")
device_info = sd.query_devices(None, "input")
samplerate = int(device_info["default_samplerate"])

# Audio queue for recording
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    """Audio callback for sounddevice."""
    if status:
        print(f"Audio error: {status}")
    audio_queue.put(bytes(indata))

def transcribe_5sec():
    """Record and transcribe 5 seconds of audio using Vosk."""
    # Clear the queue
    while not audio_queue.empty():
        audio_queue.get()
    
    # Create recognizer for this session
    rec = KaldiRecognizer(model, samplerate)
    
    print("Listening for 5 seconds...")
    
    # Start recording
    with sd.RawInputStream(samplerate=samplerate, blocksize=8000,
                          dtype="int16", channels=1, callback=audio_callback):
        
        # Record for 5 seconds
        start = time.time()
        while time.time() - start < 5:
            data = audio_queue.get()
            rec.AcceptWaveform(data)
    
    # Process remaining audio
    while not audio_queue.empty():
        data = audio_queue.get()
        rec.AcceptWaveform(data)
    
    # Get transcription
    result = json.loads(rec.FinalResult())
    text = result.get('text', '')
    
    print(f"Heard: {text}")
    return text

def ask_ai(question):
    """Query local AI model."""
    if not question:
        return "I didn't hear anything. Please try again."
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3:mini",
                "prompt": f"Answer in one short funny phrase like a FURIOUS ANGRY New Yorker. Use plain, simple English. Start with 'Hmm!' Give ONLY the final answer—no explanations, no extra words. Question: {question}\nAnswer:",
                "stream": False
            },
            timeout=60
        )
        return response.json().get('response', 'No response from AI')
    except Exception as e:
        print(f"AI error: {e}")
        return "Sorry, the AI is not responding."

def say(text, language='en'):
    """Convert text to speech using Google TTS."""
    encoded_text = urllib.parse.quote_plus(text)
    tts_url = f"http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={encoded_text}&tl={language}"
    
    try:
        subprocess.run([
            '/usr/bin/mplayer',
            '-ao', 'alsa',
            '-really-quiet',
            '-noconsolecontrols',
            tts_url
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error playing audio: {e}")
    except FileNotFoundError:
        print("Error: mplayer not found. Install with: sudo apt-get install mplayer")



def main():
    """Main loop for button-triggered AI assistant."""
    button = Button(23)
    
    print("AI Assistant ready. Press button to start...")
    
    while True:
        button.wait_for_press()
        
        # Get user's question
        question = transcribe_5sec()
        
        if question:
            # Get AI response
            print("Thinking...")
            response = ask_ai(question)
            
            # Print and speak response
            print(f"AI: {response.encode('utf-8', 'ignore').decode('utf-8')}")
            say(f"Hmm!{response.encode('utf-8', 'ignore').decode('utf-8')}")
            print("Spoken.")
        else:
            say("I didn't hear anything. Please try again.")
        
        # Small delay to prevent accidental double-presses
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Fatal error: {e}")