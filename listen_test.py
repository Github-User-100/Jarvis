"""
Diagnostic listener — continuously transcribes mic input and prints what it hears.
Run with:  .venv\Scripts\python listen_test.py
Ctrl+C to quit.
"""
import sys
import glob

for _d in glob.glob(r'C:\Temp\ClaudeStuff\shared\*\python'):
    sys.path.insert(0, _d)

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
CHUNK_SEC = 1.0
MODEL_SIZE = 'tiny'

print(f'Loading Whisper {MODEL_SIZE} model...')
model = WhisperModel(MODEL_SIZE, device='cpu', compute_type='int8')
print('Model ready.\n')

device_index = sd.default.device[0]
device_name = sd.query_devices(device_index)['name']
print(f'Listening on: [{device_index}] {device_name!r}')
print('(Ctrl+C to stop)\n')

n_samples = int(CHUNK_SEC * SAMPLE_RATE)

with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16') as stream:
    try:
        while True:
            raw, _ = stream.read(n_samples)
            audio = raw.flatten().astype('float32') / 32768.0
            segments, _ = model.transcribe(audio, beam_size=5, language='en')
            text = ' '.join(s.text for s in segments).strip()
            if text:
                print(f'>> {text}')
    except KeyboardInterrupt:
        print('\nStopped.')
