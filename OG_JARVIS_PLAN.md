# Plan: OG_JARVIS_PLAN

## Goal
Build a local, free, always-on voice interface for Claude Code running in VS Code. Say "Jarvis"
to wake it up, speak naturally, and it transcribes, identifies who's talking, sends the message
to Claude Code, and reads the response aloud. Dismiss it with any natural goodbye phrase and it
goes quiet until called again. No API keys. No cloud. No cost after one-time model downloads.

The entry point is `audio_server.py` — an always-on audio server. It behaves like a server:
it listens continuously, and saying "Jarvis" is how you connect to it. You run it once and
it lives in the background. Under the hood it's `Jarvis().run()` — one line.

The name: Jarvis. Like Tony Stark's AI. Obviously.

---

## Architecture

### File Structure
```
Jarvis/
├── audio_server.py              ← entry point: glob bootstrap + Jarvis().run()
├── jarvis.config.json           ← user config (dismissal words, model size, thresholds, etc.)
├── profiles/                    ← voice profiles (.npz) — git-ignored
├── src/
│   ├── EnrollmentConductor.py   ← Jarvis-specific: conversational enrollment state machine
│   └── Jarvis.py                ← Jarvis-specific: main class; owns the IDLE/ACTIVE loop
└── tests/
    ├── conftest.py              ← glob bootstrap so pytest finds shared\ classes
    ├── MANUAL_TESTS_CHECKLIST.md
    └── test_*.py
```

Reusable infrastructure lives in `shared\` — not in Jarvis\src\:
```
shared\
├── AppLogger\python\AppLogger.py
├── AudioStream\python\AudioStream.py
├── SpeechDetector\python\SpeechDetector.py
├── Transcriber\python\Transcriber.py
├── Speaker\python\Speaker.py
└── VSCodeInjector\python\VSCodeInjector.py
```

### Classes

**Reusable Infrastructure** — own distinct resources, no Jarvis-specific logic:

| Class | Owns | Key interface |
|-------|------|---------------|
| `AppLogger` | Log handlers, formatting | `AppLogger.enter(name)` → scope |
| `AudioStream` | Mic device, sounddevice stream | `start()`, `read_chunk()`, `stop()` |
| `SpeechDetector` | webrtcvad instance, frame buffer | `is_speech(frame)`, `record_until_silence()` |
| `Transcriber` | faster-whisper model(s), lazy loading | `transcribe(audio, model='tiny'\|'medium')` |
| `Speaker` | pyttsx3 engine, TTS daemon thread | `say(text)`, `interrupt()` |
| `VSCodeInjector` | Clipboard, pyautogui | `inject(text)` |

**`EnrollmentConductor`** — justified as its own class: it has private state the parent
should never care about (current phase, sample count, topics heard, question history),
and its own actions that only make sense in the context of enrolling a new voice:

| Owns | Methods |
|------|---------|
| `name`, `pronoun`, `phase`, `samples`, `question_history` | `start()`, `next_prompt(last_answer)`, `add_sample(audio, embedding)`, `is_complete()`, `save()` |

Jarvis creates one when enrollment is triggered and discards it when done.

**`Jarvis`** — the main class. Owns config, all infrastructure instances, loaded voice
profiles, and the top-level IDLE/ACTIVE state machine. Everything Jarvis *does* is a
method here:

| Method | What it does |
|--------|-------------|
| `__init__` | Loads config, instantiates infrastructure, loads profiles from `profiles/` |
| `run()` | IDLE/ACTIVE state machine loop |
| `_scan_for_wake_word(chunk)` | Tiny Whisper on chunk → bool |
| `_record_utterance()` | webrtcvad-driven recording → audio segment |
| `_is_dismissal(transcript)` | Check against dismissal word list → bool |
| `_identify_speaker(audio)` | Pitch + embedding match → speaker name or "unknown" |
| `_apply_persona(speaker, transcript)` | Prepend kid-mode prefix if needed → final string |
| `_enroll(name, pronoun)` | Create + run an `EnrollmentConductor` |

### Logging
Every method does real work MUST open with `log = AppLogger.enter('ClassName.method_name')`.
Log liberally — state transitions, speaker detection results, dismissal matches, model load
times, injection success/failure. If something goes wrong at 2am, the log should tell the story.

---

## Phase 1 — Wake Word Loop + Dismissal + TTS

### Goal
Get the full always-on interaction loop working end-to-end:
idle scanning → "Jarvis" detected → listen → transcribe → inject into VS Code →
read response → loop → dismissed → back to scanning.

### The Two-State Loop

```
[IDLE — scanning]
  Tiny Whisper processes 1.5-sec audio chunks continuously.
  Low CPU. Waiting for "Jarvis" anywhere in the transcript.
         ↓  "Jarvis" detected
[ACTIVE MODE]
  webrtcvad watches the mic stream.
  Speech onset detected → start recording.
  1.5 sec of silence → recording ends → medium Whisper transcribes.
  Check transcript for dismissal phrase first.
    → Dismissal: interrupt TTS if playing, announce "Goodbye", back to [IDLE].
    → Otherwise: inject into VS Code, wait for response, TTS reads it, loop.
```

### Dismissal Phrases
Pattern: **[dismissal word/phrase] + "Jarvis"** anywhere in the transcript.

Dismissal words: `thanks`, `thank you`, `goodbye`, `bye`, `hush`, `quiet`, `stop`,
`sleep`, `dismissed`, `that's all`, `enough`, `later`, `shush`, `go away`

Examples: "Thanks Jarvis", "Hush Jarvis", "Dismissed Jarvis", "Sleep Jarvis",
"That's all Jarvis", "Goodbye Jarvis"

Stored as a configurable list in jarvis.config.json so the user can add/remove words.

### TTS Interruption
TTS runs in a daemon thread. While it plays, the mic stays open and tiny Whisper
continues scanning chunks. If a dismissal phrase is detected mid-response:
1. Set a threading.Event() (`tts_stop`)
2. TTS thread checks the event and calls `engine.stop()` immediately
3. Jarvis says "Goodbye" and returns to idle
This means you can always talk over Jarvis if it's rambling.

### Tasks

#### Environment Setup (PARTIALLY DONE — read before touching)
- [x] `requirements.txt` created with pinned versions — see file for final list
      KEY GOTCHA: Python 3.14 has no pre-built wheel for webrtcvad (needs C compiler).
      Must use Python 3.12.10 (last binary release — 3.12.13+ is source-only).
      Download: https://www.python.org/downloads/release/python-31210/ → Windows installer (64-bit)
- [x] `.venv` created — BUT it was created with Python 3.14 and must be DELETED and recreated.
      After installing Python 3.12.10:
        1. Delete `Jarvis\.venv\`
        2. `py -3.12 -m venv .venv`
        3. `.venv\Scripts\pip install -r requirements.txt`
- [x] Set up Python 3.12.10 venv and install dependencies — clean, all wheels installed
- [x] Add glob bootstrap to `audio_server.py` entry point
- [x] Add `tests\conftest.py` with the same glob bootstrap so pytest finds shared\ classes
- [x] Write `shared\AppLogger\python\AppLogger.py`
- [x] Write `shared\AudioStream\python\AudioStream.py` — sounddevice; energy-based VAD (no webrtcvad)
- [x] Write `shared\SpeechDetector\python\SpeechDetector.py` — RMS energy VAD; `record_until_silence()`
- [x] Write `shared\Transcriber\python\Transcriber.py` — faster-whisper; lazy-loads tiny + medium
- [x] Write `shared\Speaker\python\Speaker.py` — pyttsx3 daemon thread; interrupt via threading.Event
- [x] Write `shared\VSCodeInjector\python\VSCodeInjector.py` — clipboard + pyautogui
- [x] Write `jarvis.config.json` with defaults
- [x] Write `src\Jarvis.py` — IDLE/ACTIVE loop; `_is_dismissal()`, `_scan_for_wake_word()` implemented
- [x] Write `audio_server.py` — glob bootstrap + AppLogger.configure + Jarvis().run()
- [x] Write automated tests — 38 passing (dismissal all variants, transcriber, speaker, speech detector, config)
- [x] Add items to MANUAL_TESTS_CHECKLIST.md

### Notes
- For Phase 1, Claude's response is NOT yet auto-read. The VS Code injection sends the
  message; the user reads the response on screen. TTS read-back of Claude's reply comes
  in Phase 4. This lets us validate the wake/dismiss/inject loop before adding complexity.
- Whisper "medium" is the default for transcription. Configurable to "small" or "large".
- VS Code injection requires the Claude Code input box to already be focused. Document
  this as a known UX requirement — user needs VS Code in the foreground.
- webrtcvad operates on 10/20/30ms frames at 8/16/32/48kHz. Use 16kHz, 20ms frames,
  aggressiveness mode 2 (balanced). All configurable.

---

## Phase 2 — Speaker Identification (Pitch-Based, Then Enrollment)

### Goal
Detect who is speaking and automatically switch Claude's response style. Adult voices stay
in normal mode. Kid voices trigger "kid mode" — a prefix is prepended to the transcript
instructing Claude to respond simply, briefly, and in a fun, age-appropriate way.

### Tasks
- [ ] Add librosa (or parselmouth) dependency for pitch/F0 extraction
- [ ] Write pitch detector: extract fundamental frequency (F0) from recorded audio
- [ ] Define pitch thresholds: adults ~80–200 Hz, kids ~200–400 Hz
      (these are starting points — will need calibration per family)
- [ ] Write speaker mode switcher: "adult" vs "kid" based on detected pitch
- [ ] Implement persona prefixing:
      - Kid mode: prepend "[Note: This question is from a child. Please give a short,
        simple, fun, age-appropriate answer.]" before the transcript
      - Adult mode: no prefix — send transcript as-is
- [ ] Extend jarvis.config.json: pitch thresholds, Whisper model size, persona prefix text
      (so user can customize kid-mode instructions)
- [ ] Write automated tests for: pitch extraction returns float, threshold classification
      logic, prefix prepend logic, config file loading with defaults
- [ ] Add manual test items: test with actual family voices, verify kid/adult switching

### Notes
- Pitch thresholds will need manual tuning. Add a "calibrate" mode: user says their name,
  system records their F0, saves it to profiles/. Thresholds auto-adjust from samples.
- This phase does NOT distinguish between specific people — just adult vs kid.
  Named profiles (Dad, Mom, specific kids) come in Phase 3.
- If pitch is ambiguous (borderline frequency), default to adult mode.

---

## Phase 3 — Named Voice Profiles + Per-Person Rules

### Goal
Give each family member a named voice profile. Jarvis recognizes individuals (not just
adult-vs-kid) and applies per-person rules. Dad gets normal Claude. The kids each get
age-appropriate behavior. Mom might get a different formality level.

Enrollment is fully voice-driven and conversational — no command line, no config editing.
You introduce someone to Jarvis by speaking, and Jarvis walks them through it.

### Enrollment Flow (Voice-Driven, Conversational)
1. User says (after waking Jarvis): "Jarvis, this is Alex. Please walk her through how to
   imprint her voice."
2. Jarvis detects the enrollment trigger pattern in the transcript ("this is [name]" +
   "imprint" or "walk [pronoun] through").
3. Jarvis greets the new person and kicks off a casual conversation to collect voice samples:
   "Hi Alex! I'm Jarvis. I want to learn your voice so I can recognize you. I'm going
   to ask you some questions — just talk naturally. What's your favorite cartoon character?"
4. Alex answers (speaks naturally, webrtcvad detects end) → Jarvis captures audio, extracts embedding, asks a
   natural follow-up based on what she said:
   "Oh cool! What do they do in that show?" / "What's your favorite episode?" /
   "Who's your favorite character besides them?" etc.
5. Repeat for 5–8 exchanges. Jarvis keeps the conversation going — topics can drift,
   that's fine. The goal is natural speech, not specific phrases.
6. Once enough samples are collected, Jarvis wraps up:
   "Perfect, I've got your voice now Alex! Nice to meet you. You can ask me anything."
7. Profile saved to profiles/alex.npz. Jarvis returns to normal mode.

### Why Conversational Instead of Scripted Phrases
Natural speech produces better voice embeddings than recited phrases — people hit a wider
range of pitch, rhythm, and articulation when they're actually talking. Kids especially.
Ask a kid to "say this sentence" and they'll mumble it. Ask them about their favorite
Pokémon and they will not shut up. More data, better quality, zero boredom.

### Tasks
- [ ] Add resemblyzer (or speechbrain) dependency for voice embedding extraction
- [ ] Write `EnrollmentConductor` — properties: `name`, `pronoun`, `phase`, `samples`,
      `question_history`; methods: `start()` (TTS greeting), `next_prompt(last_answer)`
      (parses nouns, picks follow-up template), `add_sample(audio, embedding)`,
      `is_complete()` (returns True at 5–8 samples), `save()` (averages embeddings →
      profiles/[name].npz); AppLogger.enter() on every method
- [ ] Write follow-up question template set in EnrollmentConductor — small hardcoded list:
      "What do they do?", "Who's your favorite besides them?", "Why do you like that?",
      "What's the best part?", "What happens in it?" — no LLM needed
- [ ] Add `_enroll(name, pronoun)` to `Jarvis` — detects "this is [name]" + enrollment
      intent, creates an EnrollmentConductor, drives the sample loop, discards conductor
      when done
- [ ] Add `_identify_speaker(audio)` to `Jarvis` — extract embedding via resemblyzer,
      compare to loaded profiles via cosine similarity, return best match name or "unknown"
- [ ] Load profiles dict in `Jarvis.__init__` from profiles/ directory at startup
- [ ] Extend jarvis.config.json: per-profile persona rules and embedding confidence threshold
      e.g. `{ "personas": { "dad": null, "alex": "[kid prefix]" }, "match_threshold": 0.75 }`
- [ ] Replace pitch-based `_identify_speaker` stub (Phase 2) with embedding-based match;
      keep pitch as fallback for unknown speakers — unknown + high pitch → kid mode
- [ ] Add "who am I?" to `Jarvis` — if transcript matches, call `_identify_speaker` and
      have `Speaker` announce the result with confidence score
- [ ] Write automated tests for: `EnrollmentConductor` phase transitions, `is_complete()`
      threshold, `save()` writes valid .npz, cosine similarity returns float in [0,1],
      profile loading in `Jarvis.__init__`, fallback-to-pitch logic
- [ ] Add manual test items: full voice enrollment via natural conversation, recognition
      accuracy across family members, unknown speaker fallback, "who am I?" diagnostic

### Notes
- resemblyzer is small and works on CPU. speechbrain is more accurate but heavier.
  Start with resemblyzer, upgrade if recognition is poor.
- Profiles are stored as numpy arrays (.npz). No sensitive data — just voice math.
- Confidence threshold for "known speaker" match: start at 0.75, make it configurable.
- Pronoun in the trigger phrase ("walk her through", "walk him through", "walk them
  through") can be used in Jarvis's TTS responses for a polished feel — parse it.
- If two kids have similar voices, they can say "Jarvis, it's [name]" as a session
  override. Jarvis honors it for the current session without re-enrolling.

---

## Phase 4 — Auto-Detect Claude's Response (Eliminate the Copy Hotkey)

### Goal
Remove the manual "copy then press Ctrl+Alt+R" step. Jarvis should automatically detect
when Claude has finished responding and read it aloud without the user having to do anything.

### Tasks
- [ ] Research VS Code extension API accessibility: can we read the Claude Code panel's
      text content programmatically? (accessibility tree, UIAutomation, window text)
- [ ] If UIAutomation works: use Get-ElementNames.ps1 pattern (already in QAi project)
      to find and read the Claude Code response panel
- [ ] If UIAutomation doesn't expose it: fall back to screen OCR (pytesseract + PIL)
      targeting the known Claude Code response region
- [ ] Implement response-change detector: poll every ~500ms, detect when new text
      appears, wait for it to stop growing (response complete), then trigger TTS
- [ ] Suppress TTS for short system messages (e.g. "Thinking...", status indicators)
      — only read responses above a minimum character threshold
- [ ] Write automated tests for: change detector logic, minimum-length filter,
      debounce/cooldown between reads
- [ ] Add manual tests: verify TTS fires after Claude finishes, not mid-stream

### Notes
- This phase has the most unknowns. UIAutomation is the cleanest path; OCR is the fallback.
- Screen region for OCR can be user-configured in jarvis.config.json (x, y, w, h).
- Do not attempt this until Phases 1–3 are solid. The complexity jumps here.
- If this proves too unreliable, an acceptable permanent alternative is a "read last
  response" hotkey that the user presses when ready — document that as a known limitation.

---

## Deferred / Out of Scope (for now)
- Mobile / non-Windows support — Windows 10+ only for now.
- Multi-language support — English only for Whisper model selection.
- Voice synthesis that sounds like Jarvis from the movies — out of scope; pyttsx3 Windows
  SAPI voices are functional but not cinematic. User can choose a better SAPI voice
  from Windows settings if desired.
- Always-on mic privacy indicator (e.g. a tray icon that shows IDLE vs ACTIVE state) —
  useful eventually so family knows when Jarvis is listening, but not blocking.

---

## Tech Stack (Planned)
| Class | Library | Reason |
|-------|---------|--------|
| `AppLogger` | logging (stdlib) | From shared\AppLogger\python\ — `configure(app_name=)` sets logger name |
| `AudioStream` | sounddevice | Simple stream API, no extra drivers |
| `SpeechDetector` | webrtcvad | Detects speech start/end; 16kHz, 20ms frames |
| `Transcriber` | faster-whisper | Tiny model for scanning, medium for transcription |
| `Speaker` | pyttsx3 + threading (stdlib) | Windows SAPI TTS; daemon thread + interrupt Event |
| `VSCodeInjector` | pyperclip + pyautogui | Clipboard paste into VS Code input |
| `EnrollmentConductor` | resemblyzer + numpy | Voice embedding extraction + profile save |
| `Jarvis` (Phase 2+) | librosa | F0 pitch extraction for kid/adult fallback |
| `Jarvis` (Phase 3+) | resemblyzer | Cosine similarity matching against saved profiles |
| — | pytest | Test framework |
| — | json (stdlib) | jarvis.config.json, no extra deps needed |

---

## Notes
- All phases build on top of the previous one. Do not start Phase 2 until Phase 1 is
  working reliably in day-to-day use.
- The kid-mode persona prefix is the key insight: Jarvis doesn't need any special Claude
  integration — it just prepends text to the message. Claude does the rest.
- Kid-appropriate default prefix (customizable): "[Note: This question is from a young
  child. Please respond in 2–3 short sentences using simple words and a fun, friendly tone.]"
