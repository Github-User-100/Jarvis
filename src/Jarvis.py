import json
import os
import re

from AppLogger import AppLogger
from AudioStream import AudioStream
from SpeechDetector import SpeechDetector
from Transcriber import Transcriber
from Speaker import Speaker
from VSCodeInjector import VSCodeInjector

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'jarvis.config.json')

_DEFAULT_CONFIG = {
    'dismissal_words': [
        'thanks', 'thank you', 'goodbye', 'bye', 'hush', 'quiet', 'stop',
        'sleep', 'dismissed', "that's all", 'enough', 'later', 'shush', 'go away',
    ],
    'whisper_model': 'medium',
    'idle_chunk_duration_sec': 1.5,
    'tts_rate': 175,
    'tts_volume': 1.0,
    'sample_rate': 16000,
    'rms_threshold': 300.0,
}


class Jarvis:
    def __init__(self):
        with AppLogger.enter('Jarvis.__init__') as log:
            self._config = self._load_config()
            log.log('INFO', 'config loaded')

            self._stream = AudioStream(sample_rate=self._config['sample_rate'])
            self._detector = SpeechDetector(
                sample_rate=self._config['sample_rate'],
                rms_threshold=self._config['rms_threshold'],
            )
            self._transcriber = Transcriber()
            self._speaker = Speaker(
                rate=self._config['tts_rate'],
                volume=self._config['tts_volume'],
            )
            self._injector = VSCodeInjector()
            log.log('INFO', 'all systems initialised')

    def _load_config(self) -> dict:
        with AppLogger.enter('Jarvis._load_config') as log:
            try:
                with open(_CONFIG_PATH, encoding='utf-8') as f:
                    cfg = json.load(f)
                    log.log('INFO', f'loaded config from {_CONFIG_PATH}')
                    return cfg
            except FileNotFoundError:
                log.log('WARN', f'config not found at {_CONFIG_PATH} — using defaults')
                return dict(_DEFAULT_CONFIG)

    def run(self) -> None:
        with AppLogger.enter('Jarvis.run') as log:
            self._stream.start()
            self._speaker.say('Jarvis online.')
            log.log('INFO', 'entering main loop')
            try:
                while True:
                    log.log('INFO', 'IDLE — scanning for wake word')
                    self._idle_until_wake_word()
                    log.log('INFO', 'wake word detected — entering ACTIVE mode')
                    self._speaker.say('Yes?')
                    self._active_mode()
            except KeyboardInterrupt:
                log.log('INFO', 'KeyboardInterrupt — shutting down')
            finally:
                self._stream.stop()
                self._speaker.say('Jarvis offline.')
                self._speaker.wait_done()

    def _idle_until_wake_word(self) -> None:
        with AppLogger.enter('Jarvis._idle_until_wake_word') as log:
            chunk_duration = self._config['idle_chunk_duration_sec']
            while True:
                chunk = self._stream.read_chunk(chunk_duration)
                transcript = self._transcriber.transcribe(chunk, model='tiny')
                log.log('DEBUG', f'idle scan: {transcript!r}')
                if self._scan_for_wake_word(transcript):
                    return

    def _active_mode(self) -> None:
        with AppLogger.enter('Jarvis._active_mode') as log:
            while True:
                log.log('INFO', 'ACTIVE — listening for utterance')
                audio = self._record_utterance()
                transcript = self._transcriber.transcribe(
                    audio,
                    model=self._config['whisper_model'],
                )
                log.log('INFO', f'transcript: {transcript!r}')

                if self._is_dismissal(transcript):
                    log.log('INFO', 'dismissal detected — returning to IDLE')
                    self._speaker.interrupt()
                    self._speaker.say('Goodbye.')
                    return

                if transcript:
                    speaker = self._identify_speaker(audio)
                    final_text = self._apply_persona(speaker, transcript)
                    log.log('INFO', f'injecting speaker={speaker} text={final_text!r}')
                    self._injector.inject(final_text)
                else:
                    log.log('WARN', 'empty transcript — skipping injection')

    def _scan_for_wake_word(self, transcript: str) -> bool:
        return 'jarvis' in transcript.lower()

    def _record_utterance(self) -> bytes:
        with AppLogger.enter('Jarvis._record_utterance') as log:
            log.log('INFO', 'delegating to SpeechDetector')
            return self._detector.record_until_silence(self._stream)

    def _is_dismissal(self, transcript: str) -> bool:
        with AppLogger.enter('Jarvis._is_dismissal') as log:
            t = transcript.lower()
            if 'jarvis' not in t:
                log.log('DEBUG', 'no "jarvis" in transcript — not a dismissal')
                return False
            jarvis_pos = t.find('jarvis')
            for word in self._config['dismissal_words']:
                pos = t.find(word)
                if pos != -1 and pos < jarvis_pos:
                    log.log('INFO', f'dismissal matched word={word!r}')
                    return True
            log.log('DEBUG', 'jarvis present but no dismissal word before it')
            return False

    def _identify_speaker(self, audio: bytes) -> str:
        # Phase 2: pitch-based adult/kid detection
        # Phase 3: embedding-based named profile matching
        return 'unknown'

    def _apply_persona(self, speaker: str, transcript: str) -> str:
        # Phase 2: prepend kid-mode prefix when speaker is identified as a child
        return transcript
