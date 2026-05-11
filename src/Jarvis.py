import glob as _glob
import json
import os
import re
import time

import librosa
import numpy as np
from AppLogger import AppLogger
from AudioStream import AudioStream
from EnrollmentConductor import EnrollmentConductor, _SAMPLES_NEEDED
from SpeechDetector import SpeechDetector
from Transcriber import Transcriber
from Speaker import Speaker
from VSCodeInjector import VSCodeInjector

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'jarvis.config.json')
_PROFILES_DIR = os.path.join(os.path.dirname(__file__), '..', 'profiles')
_RESPONSE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'jarvis_response.tmp'))

_ENROLL_KEYWORDS = re.compile(
    r'\b(imprint|enroll|enrollment|voiceprint|voice\s+print|register)\b'
    r'|walk\s+\w+\s+through',
    re.IGNORECASE,
)
_ENROLL_NAME = re.compile(r'this\s+is\s+(\w+)', re.IGNORECASE)

_DEFAULT_CONFIG = {
    'dismissal_words': [
        'thanks', 'thank you', 'goodbye', 'bye', 'hush', 'quiet', 'stop',
        'sleep', 'dismissed', "that's all", 'enough', 'later', 'shush', 'go away',
    ],
    'whisper_model': 'medium',
    'tts_rate': 1,
    'tts_volume': 1.0,
    'sample_rate': 16000,
    'rms_threshold': 300.0,
    'kid_pitch_threshold': 255.0,
    'sentence_pause_ms': 400,
    'match_threshold': 0.75,
    'max_tts_chars': 500,
    'response_timeout_seconds': 120,
    'response_file': _RESPONSE_FILE,
    'response_instruction': (
        f'After responding, write your complete response to {_RESPONSE_FILE} '
        f'then write a line containing only ---END---. Overwrite the file completely each time.'
    ),
    'adult_persona_prefix': (
        '[Voice mode: Your response will be read aloud. '
        'Be concise and conversational — avoid bullet points, markdown, '
        'and long lists unless explicitly asked.]'
    ),
    'kid_persona_prefix': (
        '[Voice mode: Your response will be read aloud to a child. '
        'Answer in 2-3 short sentences using simple, fun, age-appropriate words.]'
    ),
    'named_adult_persona_template': (
        '[Voice mode: You are speaking with {name}. Your response will be read aloud. '
        'Be concise and conversational — avoid bullet points, markdown, '
        'and long lists unless explicitly asked.]'
    ),
    'named_kid_persona_template': (
        '[Voice mode: You are speaking with {name}, age {age}. '
        'Answer in 2-3 short sentences using simple, fun, age-appropriate words.]'
    ),
    'name_pronunciations': {},
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
                sentence_pause_ms=self._config.get('sentence_pause_ms', 0),
            )
            self._injector = VSCodeInjector()
            self._profiles = self._load_profiles()
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

    def _load_profiles(self) -> dict:
        with AppLogger.enter('Jarvis._load_profiles') as log:
            profiles = {}
            for path in _glob.glob(os.path.join(_PROFILES_DIR, '*.npz')):
                try:
                    data = np.load(path, allow_pickle=False)
                    name = str(data['name'])
                    age_val = int(data['age'])
                    age = age_val if age_val > 0 else None
                    pronoun = str(data['pronoun'])
                    embedding = data['embedding']
                    speaker_type = 'kid' if (age is not None and age < 18) else 'adult'
                    profiles[name.lower()] = {
                        'name': name,
                        'age': age,
                        'pronoun': pronoun,
                        'embedding': embedding,
                        'type': speaker_type,
                    }
                    log.log('INFO', f'loaded profile name={name!r} age={age}')
                except Exception as e:
                    log.log('WARN', f'failed to load profile {path!r}: {e}')
            log.log('INFO', f'{len(profiles)} profile(s) loaded')
            return profiles

    def run(self) -> None:
        with AppLogger.enter('Jarvis.run') as log:
            self._stream.start()
            self._speaker.say('Say Jarvis to wake me up.')
            log.log('DEBUG', 'entering main loop')
            print('[JARVIS] Online — listening for wake word')
            try:
                while True:
                    log.log('DEBUG', 'IDLE — scanning for wake word')
                    self._idle_until_wake_word()
                    log.log('INFO', 'wake word detected — entering ACTIVE mode')
                    print('[JARVIS] Wake word detected')
                    self._speaker.say('Yes?')
                    self._speaker.wait_done()
                    self._active_mode()
                    print('[JARVIS] Back to idle — listening for wake word')
            except KeyboardInterrupt:
                log.log('INFO', 'KeyboardInterrupt — shutting down')
            finally:
                self._stream.stop()
                self._speaker.say('Shutting down.')
                self._speaker.wait_done()

    def _idle_until_wake_word(self) -> None:
        with AppLogger.enter('Jarvis._idle_until_wake_word') as log:
            while True:
                audio = self._detector.record_until_silence(self._stream)
                transcript = self._transcriber.transcribe(audio, model='tiny', initial_prompt='Jarvis')
                log.log('DEBUG', f'idle scan: {transcript!r}')
                if self._scan_for_wake_word(transcript):
                    return

    def _active_mode(self) -> None:
        with AppLogger.enter('Jarvis._active_mode') as log:
            while True:
                log.log('DEBUG', 'ACTIVE — listening for utterance')
                audio = self._record_utterance()
                transcript = self._transcriber.transcribe(
                    audio,
                    model=self._config['whisper_model'],
                )
                log.log('DEBUG', f'transcript: {transcript!r}')
                print(f'[HEARD] {transcript!r}')

                enrollment = self._parse_enrollment_trigger(transcript)
                if enrollment:
                    name, pronoun = enrollment
                    log.log('INFO', f'enrollment trigger detected name={name!r}')
                    self._enroll(name, pronoun)
                    continue

                if self._is_dismissal(transcript):
                    log.log('INFO', 'dismissal detected — returning to IDLE')
                    self._speaker.interrupt()
                    self._speaker.say('Going back to sleep now.')
                    return

                if transcript:
                    if 'who am i' in transcript.lower():
                        self._announce_speaker(audio)
                        continue

                    speaker = self._identify_speaker(audio)
                    final_text = self._apply_persona(speaker, transcript)
                    log.log('INFO', f'injecting name={speaker.get("name")!r} type={speaker.get("type")}')
                    print(f'[INJECT] {final_text!r}')
                    self._clear_response_file()
                    self._injector.inject(final_text)

                    response = self._wait_for_response()
                    if response is None:
                        self._speaker.say("I didn't get a response — please check the screen.")
                    elif len(response) > self._config.get('max_tts_chars', 500):
                        log.log('INFO', f'response too long ({len(response)} chars) — skipping TTS')
                        self._speaker.say("Response is on screen — it's a long one.")
                    else:
                        self._speaker.say(response)
                else:
                    log.log('WARN', 'empty transcript — skipping injection')

    def _scan_for_wake_word(self, transcript: str) -> bool:
        t = transcript.lower()
        return 'jarvis' in t or 'arvis' in t

    def _record_utterance(self) -> bytes:
        with AppLogger.enter('Jarvis._record_utterance') as log:
            log.log('DEBUG', 'delegating to SpeechDetector')
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
                    log.log('INFO', f'dismissal word={word!r} before "jarvis" — dismissing')
                    return True
            log.log('DEBUG', 'jarvis present but no dismissal word before it')
            return False

    def _parse_enrollment_trigger(self, transcript: str) -> tuple[str, str] | None:
        with AppLogger.enter('Jarvis._parse_enrollment_trigger') as log:
            if not _ENROLL_KEYWORDS.search(transcript):
                return None
            name_match = _ENROLL_NAME.search(transcript)
            if not name_match:
                log.log('DEBUG', 'enrollment keyword found but no name — ignoring')
                return None
            name = name_match.group(1).capitalize()
            t = transcript.lower()
            pronoun = 'her' if ' her' in t else 'him' if ' him' in t else 'them'
            log.log('INFO', f'enrollment trigger parsed name={name!r} pronoun={pronoun!r}')
            return name, pronoun

    def _enroll(self, name: str, pronoun: str) -> None:
        with AppLogger.enter('Jarvis._enroll') as log:
            conductor = EnrollmentConductor(name, pronoun, ask_claude=self._ask_claude_for_enrollment, tts_name=self._tts_name(name))

            self._speaker.say(conductor.greeting())
            self._speaker.wait_done()

            while not conductor.is_complete():
                audio = self._detector.record_until_silence(self._stream)
                transcript = self._transcriber.transcribe(audio, model='small')
                log.log('DEBUG', f'enrollment response: {transcript!r}')

                if conductor.age is None:
                    conductor.try_parse_age(transcript)

                embedding = self._extract_embedding(audio)
                conductor.add_sample(embedding)

                if conductor.is_complete():
                    break

                if conductor.needs_age():
                    self._speaker.say(f"One last thing — how old are you, {self._tts_name(name)}?")
                    self._speaker.wait_done()
                    audio = self._detector.record_until_silence(self._stream)
                    transcript = self._transcriber.transcribe(audio, model='small')
                    conductor.try_parse_age(transcript)
                    embedding = self._extract_embedding(audio)
                    conductor.add_sample(embedding)
                    break

                prompt = conductor.next_prompt(transcript)
                self._speaker.say(prompt)
                self._speaker.wait_done()

            path = conductor.save(_PROFILES_DIR)
            log.log('INFO', f'enrollment complete — profile saved to {path!r}')
            self._profiles = self._load_profiles()
            self._speaker.say(f"Perfect, I've got your voice now {self._tts_name(name)}! Nice to meet you.")
            self._speaker.wait_done()

    def _ask_claude_for_enrollment(self, last_answer: str, conductor) -> str:
        with AppLogger.enter('Jarvis._ask_claude_for_enrollment') as log:
            age_hint = ''
            if conductor.age is None and not conductor._age_asked and len(conductor._samples) >= 2:
                age_hint = (
                    f"{conductor.tts_name} has consented to voice enrollment and we still need "
                    f"their age for the speaker profile — please ask it directly as part of the conversation. "
                )

            instruction = self._config.get('response_instruction', '')
            prompt = (
                f"[Voice enrollment assistant: {conductor.tts_name} has consented to enroll "
                f"their voice in a family home assistant. You are collecting {_SAMPLES_NEEDED} voice samples "
                f"through friendly conversation. This is sample {len(conductor._samples) + 1} of {_SAMPLES_NEEDED}. "
                f"{age_hint}"
                f"Their last response: '{last_answer}'. "
                f"Reply with ONE short friendly follow-up question only — no preamble.] "
                f"{instruction}"
            )
            log.log('DEBUG', f'sending enrollment prompt to Claude sample={len(conductor._samples) + 1}')
            self._clear_response_file()
            self._injector.inject(prompt)
            response = self._wait_for_response()
            if response:
                log.log('INFO', f'Claude enrollment prompt: {response!r}')
                return response
            log.log('WARN', 'no Claude response for enrollment — falling back to template')
            return ''

    def _clear_response_file(self) -> None:
        with AppLogger.enter('Jarvis._clear_response_file') as log:
            path = self._config.get('response_file', _RESPONSE_FILE)
            try:
                open(path, 'w').close()
                log.log('DEBUG', f'cleared response file: {path}')
            except OSError as e:
                log.log('WARN', f'could not clear response file: {e}')

    def _wait_for_response(self) -> str | None:
        with AppLogger.enter('Jarvis._wait_for_response') as log:
            path = self._config.get('response_file', _RESPONSE_FILE)
            timeout = self._config.get('response_timeout_seconds', 120)
            deadline = time.monotonic() + timeout
            log.log('DEBUG', f'waiting for response file sentinel path={path}')

            while time.monotonic() < deadline:
                time.sleep(0.1)
                try:
                    content = open(path, encoding='utf-8').read()
                except OSError:
                    continue
                if '---END---' in content:
                    response = content.split('---END---')[0].rstrip()
                    log.log('INFO', f'response received length={len(response)}')
                    return response

            log.log('WARN', f'response timeout after {timeout}s')
            return None

    def _extract_embedding(self, audio: bytes) -> np.ndarray:
        with AppLogger.enter('Jarvis._extract_embedding') as log:
            audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            mfcc = librosa.feature.mfcc(y=audio_np, sr=self._config['sample_rate'], n_mfcc=40)
            embedding = np.concatenate([mfcc.mean(axis=1), mfcc.std(axis=1)])
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            log.log('DEBUG', f'embedding extracted shape={embedding.shape}')
            return embedding

    def _match_profile(self, audio: bytes) -> dict | None:
        with AppLogger.enter('Jarvis._match_profile') as log:
            if not self._profiles:
                return None
            embedding = self._extract_embedding(audio)
            best_name = None
            best_score = -np.inf
            for name, profile in self._profiles.items():
                score = float(np.dot(embedding, profile['embedding']))
                log.log('DEBUG', f'similarity name={name!r} score={score:.3f}')
                if score > best_score:
                    best_score = score
                    best_name = name
            threshold = self._config.get('match_threshold', 0.75)
            if best_name and best_score >= threshold:
                log.log('INFO', f'matched profile={best_name!r} score={best_score:.3f}')
                return self._profiles[best_name]
            log.log('INFO', f'no profile match (best={best_name!r} score={best_score:.3f} threshold={threshold})')
            return None

    def _identify_speaker(self, audio: bytes) -> dict:
        with AppLogger.enter('Jarvis._identify_speaker') as log:
            if self._profiles:
                match = self._match_profile(audio)
                if match:
                    return match

            audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            f0, voiced_flag, _ = librosa.pyin(audio_np, fmin=70, fmax=500, sr=self._config['sample_rate'])
            voiced = f0[voiced_flag]
            if len(voiced) == 0:
                log.log('INFO', 'no voiced frames detected — defaulting to adult')
                return {'name': None, 'age': None, 'pronoun': None, 'type': 'adult'}
            median_f0 = float(np.median(voiced))
            threshold = self._config['kid_pitch_threshold']
            speaker_type = 'kid' if median_f0 >= threshold else 'adult'
            log.log('INFO', f'pitch fallback median_f0={median_f0:.1f}Hz threshold={threshold}Hz — {speaker_type}')
            return {'name': None, 'age': None, 'pronoun': None, 'type': speaker_type}

    def _announce_speaker(self, audio: bytes) -> None:
        with AppLogger.enter('Jarvis._announce_speaker') as log:
            speaker = self._identify_speaker(audio)
            name = speaker.get('name')
            age = speaker.get('age')
            if name:
                tts = self._tts_name(name)
                msg = f"You are {tts}!" if not age else f"You are {tts}, age {age}!"
            else:
                msg = "I don't recognize your voice yet. Ask someone to introduce you to me."
            log.log('INFO', f'announcing speaker: {msg!r}')
            self._speaker.say(msg)

    def _tts_name(self, name: str) -> str:
        return self._config.get('name_pronunciations', {}).get(name, name)

    def _apply_persona(self, speaker: dict, transcript: str) -> str:
        with AppLogger.enter('Jarvis._apply_persona') as log:
            name = speaker.get('name')
            age = speaker.get('age')
            speaker_type = speaker.get('type', 'adult')

            if name and age is not None:
                if speaker_type == 'kid':
                    template = self._config.get('named_kid_persona_template', '')
                    prefix = template.format(name=name, age=age) if template else ''
                else:
                    template = self._config.get('named_adult_persona_template', '')
                    prefix = template.format(name=name) if template else ''
            else:
                prefix = self._config.get(
                    'kid_persona_prefix' if speaker_type == 'kid' else 'adult_persona_prefix', ''
                )

            instruction = self._config.get('response_instruction', '')
            text = f'{prefix} {transcript}' if prefix else transcript
            result = f'{text} {instruction}' if instruction else text
            log.log('INFO', f'applied persona name={name!r} type={speaker_type}')
            return result
