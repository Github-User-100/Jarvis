# Current Issues — Jarvis

> Active bugs and planned features. Move completed items to archive/HX_ISSUES.md.
> Created: 2026-05-09 17:16 CDT

---

## ISSUES

### BUG: Audio device disconnected while running crashes with PortAudioError
- **Reported:** 2026-05-10
- **Symptom:** Unplugging the audio device (headset/mic) while the script is running raises `sounddevice.PortAudioError: Unanticipated host error [PaErrorCode -9999]: 'There is no driver installed on your system.' [MME error 6]` in `AudioStream.read_chunk()`, propagating up through `_idle_until_wake_word()` and crashing the process.
- **Stack:** `AudioStream.read_chunk` → `sounddevice._InputStreamBase._raw_read` → `PortAudioError`
- **Fix needed:** Catch `PortAudioError` in `AudioStream.read_chunk` (or in `_idle_until_wake_word`) and either gracefully restart the stream or raise a typed exception that `Jarvis.run()` can handle with a user-facing message and clean shutdown.


## FEATURE IDEAS


## FEATURE IDEAS

### FEATURE: Verbal slash commands
- **Detail:** Reserve certain spoken phrases to inject VS Code Claude Code slash commands directly, bypassing the normal persona-wrap and file-write flow. Example mappings: "clear conversation" → `/clear`, "usage" → `/usage`, "compact" → `/compact`, "help" → `/help`. Mapping should be configurable in jarvis.config.json as a dict so the user can add/remove entries without code changes. Detection happens in `_active_mode` after transcription — if the lowercased transcript matches a reserved phrase, inject the slash command and skip `_wait_for_response` (slash commands don't produce a file-written response). Phrase matching should be fuzzy-tolerant (strip punctuation, ignore filler words like "show me" before "usage").


### FEATURE: Personalized wake word greeting
- **Detail:** When "Jarvis" is detected, identify the speaker from the wake word audio (already captured by record_until_silence) and greet them by name — "Yes, [Name]?" instead of "Yes?" for a known speaker, "Yes?" as fallback for unknown. Requires _idle_until_wake_word() to return the detection audio and run() to call _identify_speaker() on it before the greeting.


## DEFERRED / KNOWN LIMITATIONS
> (Also add to archive/KNOWN_LIMITATIONS.md with context)
