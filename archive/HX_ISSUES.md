# Completed Issues & Feature History — Jarvis

> ⚠ APPEND ONLY. NEVER overwrite, truncate, or delete entries.
> Use Edit tool to append at the bottom. Never use Write tool on this file.
> Violating this destroys permanent project history.
> Format: ## YYYY-MM-DD HH:MM TZ — Title

---

## 2026-05-09 17:16 CDT — Project initialized
Initial project scaffold created.

## 2026-05-11 — Phase 4 complete: response readback + long-response filter + Claude-driven enrollment
Jarvis now reads Claude's responses aloud automatically. Every outgoing message has the persona
prefix prepended and a file-write instruction appended — Claude writes his complete response to
jarvis_response.tmp and terminates it with ---END---. Jarvis polls at 100ms until the sentinel
appears, then TTS the response. Responses over max_tts_chars (default 500) get "Response is on
screen — it's a long one" instead. 120s timeout with spoken fallback. EnrollmentConductor Phase
3 seam activated — Claude now drives enrollment conversation via the same file loop, with
hardcoded template fallback if Claude is unavailable. 105 automated tests passing.

## 2026-05-11 — Phase 3 complete: voice enrollment + named speaker identification
Implemented conversational voice enrollment via EnrollmentConductor. Enrollment is triggered
by "Jarvis, this is [name], walk her/him through..." — Jarvis conducts a natural conversation,
collects 6 MFCC embeddings, asks the speaker's age mid-conversation, and saves a .npz profile.
MFCC (librosa) used instead of resemblyzer — resemblyzer requires PyTorch (~170MB); MFCC is
accurate enough for a small family set with no new dependencies. _identify_speaker now tries
profile matching first (cosine similarity) and falls back to pitch detection for unknown
speakers. _apply_persona uses named templates (including name + age) for enrolled speakers.
"Who am I?" diagnostic added. Phase 4 seam in EnrollmentConductor._next_prompt() ready for
Claude-driven conversation. 93 automated tests passing.

## 2026-05-10 19:36 CDT — Phase 2 complete: pitch-based speaker identification
Implemented adult/kid detection using librosa pitch extraction. Initially used `librosa.yin`
which produced octave errors (user's 6-year-old measured at 126.8 Hz instead of ~275 Hz).
Switched to `librosa.pyin` (probabilistic YIN with HMM smoothing) which correctly measured
both kids at 273 and 283 Hz vs. user at 119 Hz. Threshold of 255 Hz gives comfortable
separation. Kid transcripts automatically prepend a persona prefix instructing Claude to
respond in 2–3 short, age-appropriate sentences. Adult transcripts prepend a voice-mode
prefix asking for concise, conversational responses without markdown. Both prefixes are
configurable in jarvis.config.json. 57 automated tests passing.
