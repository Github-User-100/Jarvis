# Jarvis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A local voice interface for [Claude Code](https://claude.ai/code) in VS Code, themed after Jarvis from Iron Man. Speak to it, it transcribes and injects your question into Claude Code, then reads Claude's response aloud. No cloud APIs — all STT and TTS run locally.

---

## What It Does

- **Wake word detection** — says "Jarvis" to activate; dismisses with "Thanks Jarvis", "Hush", "Goodbye", etc.
- **Voice transcription** — faster-whisper (local) transcribes your question
- **Speaker identification** — recognizes enrolled family members by voice and addresses them by name; detects adults vs. kids by pitch and adjusts Claude's response style accordingly
- **Claude Code injection** — pastes the transcribed question into the VS Code Claude Code input box
- **Response readback** — Claude writes its response to a temp file; Jarvis reads it aloud (or announces "it's a long one" for responses over the character limit)
- **Voice enrollment** — say "Jarvis, this is [name], walk him/her through the voice print process" to enroll a new speaker conversationally

---

## Requirements

- Windows 10+
- Python 3.12 (tested; librosa requires 3.12)
- VS Code with [Claude Code](https://claude.ai/code) extension installed and open
- A microphone
- A SAPI-compatible TTS voice (built into Windows)

---

## Setup

```bash
# Clone and create virtualenv
git clone https://github.com/Github-User-100/Jarvis.git
cd Jarvis
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

All shared library dependencies (`AppLogger`, `AudioStream`, `SpeechDetector`, `Transcriber`, `Speaker`, `VSCodeInjector`) are included in the `shared/` folder — no separate install needed.

On first run, faster-whisper downloads Whisper model weights from Hugging Face (~150MB for tiny, ~500MB for small). They are cached locally after the first download.

---

## Running

```bash
.venv\Scripts\python audio_server.py
```

Jarvis says "Say Jarvis to wake me up." and enters idle listening mode.

**VS Code must be focused** with the Claude Code input box active — Jarvis injects text via clipboard paste, so focus is a hard requirement.

---

## Configuration

All tunable values live in `jarvis.config.json`. No code changes needed.

| Key | Default | Description |
|-----|---------|-------------|
| `rms_threshold` | `300.0` | Mic sensitivity — lower = more sensitive, raise to reduce false triggers |
| `kid_pitch_threshold` | `255.0` | Hz cutoff for adult vs. kid pitch detection |
| `match_threshold` | `0.75` | Cosine similarity threshold for speaker profile matching |
| `whisper_model` | `"small"` | Whisper model for active transcription (`tiny`, `small`, `medium`) |
| `max_tts_chars` | `500` | Responses longer than this are announced, not read aloud |
| `response_timeout_seconds` | `120` | How long to wait for Claude's response before giving up |
| `sentence_pause_ms` | `400` | Silence between sentences for more natural TTS delivery (`0` = disabled) |
| `tts_rate` | `1` | SAPI speech rate (-10 slowest → 10 fastest) |
| `tts_volume` | `1.0` | Volume 0.0–1.0 |
| `name_pronunciations` | `{}` | Map display names to TTS-friendly pronunciations e.g. `{"T.J.": "Tee Jay"}` |
| `dismissal_words` | `[...]` | Spoken words that return Jarvis to idle |

---

## Voice Enrollment

Say: **"Jarvis, this is [name], walk him/her through the voice print process"**

Jarvis conducts a short conversation (6 voice samples + age), saves a profile to `profiles/[name].npz`, and loads it immediately. On next wake, Jarvis will recognize that voice and greet the person by name.

Profiles are stored locally in `profiles/`. Delete a `.npz` file to remove a speaker.

---

## Architecture

```
audio_server.py          Entry point; bootstraps shared\ and starts Jarvis.run()
src/
  Jarvis.py              Main class — IDLE/ACTIVE loop, speaker ID, persona, response file
  EnrollmentConductor.py Conversational enrollment state machine
profiles/                Voice print .npz files (git-ignored)
jarvis_response.tmp      Claude writes responses here (git-ignored)
jarvis.log               Structured log output
tests/                   107 automated tests (pytest)
```

Jarvis pulls all audio/TTS/transcription infrastructure from `shared\` — nothing is duplicated locally. See [REUSABLES.md](../shared/REUSABLES.md) for the full shared library index.

---

## Tests

```bash
.venv\Scripts\python -m pytest tests/
```

107 tests covering wake word detection, speaker identification, voice enrollment, persona prefix generation, response polling, TTS name pronunciation, and sentence splitting.

---

## Known Limitations

- VS Code Claude Code input box must be focused for injection to work
- Speaker identification uses MFCC cosine similarity — accurate for a small known-speaker set (family of 4–6); not designed for large populations
- Audio device disconnect while running crashes with `PortAudioError` (fix tracked in `CURRENT_ISSUES.md`)
- Windows only (SAPI TTS + win32com)
