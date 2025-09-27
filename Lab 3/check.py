import requests

def ask_ai(question):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "phi3:mini", "prompt": question, "stream": False}
    )
    return response.json().get('response', 'No response')



import qwiic_button
from vosk import Model, KaldiRecognizer
import sounddevice as sd




button = qwiic_button.QwiicButton().begin()
model = Model(lang="en-us")
recognizer = KaldiRecognizer(model, 16000)

with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16") as stream:
    print("Listening for button press...")
    while True:
        data = stream.read(4000)[0]
        if recognizer.AcceptWaveform(data):
            result = recognizer.Result()
            text = result[14:-3]  # Extract text from JSON result
            if text:
                print(f"You said: {text}")
                response = ask_ai(text)
                print(f"AI Response: {response}")
