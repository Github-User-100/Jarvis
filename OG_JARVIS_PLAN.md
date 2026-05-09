# Plan: OG_JARVIS_PLAN

## Goal
Build a local, free voice interface for Claude Code running in VS Code. The user (and family
members) can speak instead of type. Jarvis transcribes speech using a locally-run Whisper model,
identifies who is speaking based on voice characteristics, prepends a persona directive if needed,
pastes the message into VS Code's Claude Code input, and reads Claude's response aloud using
Windows' built-in TTS. No API keys. No cloud. No cost after the one-time model download.

The name: Jarvis. Like Tony Stark's AI. Obviously.

---

## Phase 1 — Basic Push-to-Talk Voice Input + TTS Output

### Goal
Get the core loop working end-to-end: press hotkey → speak → Whisper transcribes → text
appears in Claude Code input → Claude responds → TTS reads it aloud.

### Tasks
- [ ] Set up Python virtual environment in Jarvis/
- [ ] Install dependencies: faster-whisper, sounddevice, pyttsx3, keyboard, pyperclip
- [ ] Download and cache Whisper "medium" model locally (~1.5 GB) on first run
- [ ] Write audio capture: hold hotkey to record, release to stop (push-to-talk)
- [ ] Write STT: send recorded audio through faster-whisper, get transcript
- [ ] Write VS Code input injection: copy transcript to clipboard, simulate Ctrl+V + Enter
      in the focused VS Code window (using pyautogui or keyboard lib)
- [ ] Write TTS output: expose a hotkey (e.g. Ctrl+Alt+R) that reads the current clipboard
      contents aloud via pyttsx3 (user copies Claude's response first)
- [ ] Wire it all together into jarvis.py — single entry point, runs in background
- [ ] Write automated tests for: audio capture duration, Whisper transcript non-empty,
      TTS engine initializes, clipboard injection logic (mocked)
- [ ] Add items to MANUAL_TESTS_CHECKLIST.md for the full end-to-end flow

### Notes
- Push-to-talk hotkey: Ctrl+Alt+Space (holds to record, releases to transcribe+send)
- TTS read-back hotkey: Ctrl+Alt+R
- For Phase 1, user manually copies Claude's response to clipboard before hitting read-back.
  Auto-detection of Claude's response comes in Phase 3.
- Whisper model: "medium" is the default. User can switch to "small" (faster, less accurate)
  or "large" (slower, most accurate) via a config file.
- VS Code injection approach: pyautogui.hotkey('ctrl', 'v') after writing to clipboard.
  Requires the Claude Code input panel to already be focused by the user.

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
- [ ] Add config file (jarvis.config.json) for: pitch thresholds, hotkeys, Whisper model size,
      persona prefix text (so user can customize kid-mode instructions)
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
age-appropriate behavior. Mom might get a different formality level. Profiles are built
through a simple enrollment flow.

### Tasks
- [ ] Add resemblyzer (or speechbrain) dependency for voice embedding extraction
- [ ] Write enrollment flow: "jarvis.py --enroll [name]" records 5–10 seconds, extracts
      voice embedding, saves to profiles/[name].npz
- [ ] Write speaker matcher: for new audio, extract embedding, compare to all profiles
      via cosine similarity, return best match (or "unknown" if confidence < threshold)
- [ ] Extend jarvis.config.json: per-profile persona rules
      e.g. { "dad": null, "mom": null, "kid1": "[kid mode prefix]", "kid2": "[kid mode prefix]" }
- [ ] Replace pitch-based switching with profile-based switching (keep pitch as fallback
      for unknown speakers — unknown + high pitch → kid mode)
- [ ] Write "who am I?" test mode: records audio and prints who Jarvis thinks it is + confidence
- [ ] Write automated tests for: embedding extraction returns ndarray, cosine similarity
      returns float in [0,1], profile loading/saving, fallback-to-pitch when unknown
- [ ] Add manual test items: enroll each family member, verify recognition accuracy,
      test that unknown voices fall back gracefully

### Notes
- resemblyzer is small and works on CPU. speechbrain is more accurate but heavier.
  Start with resemblyzer, upgrade if recognition is poor.
- Profiles are stored as numpy arrays (.npz). No sensitive data — just voice math.
- Confidence threshold for "known speaker" match: start at 0.75, make it configurable.
- If two kids have similar voices, manual override is fine — they can say "It's [name]"
  and Jarvis can honor that for the session.

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
- Wake word ("Hey Jarvis") — pvporcupine has a free tier but isn't fully open source.
  Push-to-talk hotkey is simpler and fully free. Revisit if user wants always-on.
- Mobile / non-Windows support — Windows 10+ only for now.
- Multi-language support — English only for Whisper model selection.
- Voice synthesis that sounds like Jarvis from the movies — out of scope; pyttsx3 Windows
  SAPI voices are functional but not cinematic. User can choose a better SAPI voice
  from Windows settings if desired.

---

## Tech Stack (Planned)
| Component | Library | Reason |
|-----------|---------|--------|
| Speech-to-Text | faster-whisper | Local, free, excellent accuracy, CPU-friendly |
| Audio capture | sounddevice | Simple, cross-platform, no extra drivers |
| Text-to-Speech | pyttsx3 | Wraps Windows SAPI, no setup, fully offline |
| Hotkey detection | keyboard | Global hotkeys, works in background |
| Clipboard/injection | pyperclip + pyautogui | Paste transcript into VS Code |
| Pitch analysis | librosa | F0 extraction for Phase 2 kid detection |
| Voice embeddings | resemblyzer | Speaker recognition for Phase 3 profiles |
| Config | json (stdlib) | jarvis.config.json, no extra deps needed |
| Tests | pytest | Standard, simple, works everywhere |

---

## Notes
- All phases build on top of the previous one. Do not start Phase 2 until Phase 1 is
  working reliably in day-to-day use.
- The kid-mode persona prefix is the key insight: Jarvis doesn't need any special Claude
  integration — it just prepends text to the message. Claude does the rest.
- Kid-appropriate default prefix (customizable): "[Note: This question is from a young
  child. Please respond in 2–3 short sentences using simple words and a fun, friendly tone.]"
