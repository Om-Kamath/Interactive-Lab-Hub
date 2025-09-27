from gpiozero import Button
import time
import requests
import urllib.parse
import subprocess

def ask_ai(question):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "phi3:mini", "prompt": f"Answer in 2 sentences like an angry old british woman in plain simple english. Dont use special characters or numbers. Question: {question}", "stream": False}
    )
    return response.json().get('response', 'No response')

def say(text, language='en'):
    """
    Convert text to speech using Google TTS and play with mplayer
    
    Args:
        text (str): Text to speak
        language (str): Language code (default: 'en' for English)
    """
    # URL encode the text
    encoded_text = urllib.parse.quote_plus(text)
    
    # Build the Google TTS URL
    tts_url = f"http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={encoded_text}&tl={language}"
    
    # Use mplayer to play the audio
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


button = Button(23)

while True:
    button.wait_for_press()
    response = ask_ai("What is the capital of India?")
    print("AI Response:", response.encode('ascii', errors='replace').decode('ascii'))
    say(response)
    time.sleep(5)  # Debounce delay
    print("Spoken the response.")
    time.sleep(0.5)  # Debounce delay
