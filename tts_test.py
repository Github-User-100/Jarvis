"""
Minimal pyttsx3 test — bypasses all Jarvis infrastructure.
Run with:  .venv\Scripts\python tts_test.py
If you hear this clearly, the issue is in our Speaker wiring.
If this is also quiet, it's a Windows Volume Mixer issue.
"""
import pyttsx3

print('Initialising engine...')
engine = pyttsx3.init()
engine.setProperty('rate', 175)
engine.setProperty('volume', 1.0)

voices = engine.getProperty('voices')
print(f'Voice: {voices[0].name}')
print(f'Rate:  {engine.getProperty("rate")}')
print(f'Volume: {engine.getProperty("volume")}')

print('Speaking...')
engine.say('Acknowledged. Jarvis is online. This is a text to speech test.')
engine.runAndWait()
print('Done.')
