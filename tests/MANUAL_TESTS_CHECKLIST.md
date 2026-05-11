# Manual Tests Checklist — Jarvis

> Tests that cannot be automated — UI behavior, OS-level interactions, visual output,
> installation flows, and anything requiring human eyes or hands.
> Add items here whenever Claude identifies something it cannot verify programmatically.
> Check items off during manual QA before a release. Reset checkboxes after each release.

---

## Pre-Release Checklist

### Phase 1 — Wake Word Loop

- [ ] `python audio_server.py` starts without errors; Jarvis says "Jarvis online."
- [ ] Saying "Jarvis" (clearly) transitions from IDLE to ACTIVE; Jarvis says "Yes?"
- [ ] Background speech / TV / ambient noise does NOT trigger wake word
- [ ] In ACTIVE mode, a spoken question is transcribed and injected into VS Code Claude Code input box
- [ ] VS Code Claude Code input box must already be focused for injection to work (known UX requirement)
- [ ] Saying "Thanks Jarvis" while Jarvis is in ACTIVE mode returns to IDLE; Jarvis says "Goodbye."
- [ ] Saying "Hush Jarvis" mid-TTS cuts off speech immediately and returns to IDLE
- [ ] Saying "Goodbye Jarvis", "Stop Jarvis", "Quiet Jarvis" all dismiss correctly
- [ ] After dismissal, saying "Jarvis" again re-enters ACTIVE mode (full loop works)
- [ ] Ctrl+C shuts down cleanly; Jarvis says "Jarvis offline."
- [ ] `jarvis.log` is created and contains structured log entries
- [ ] RMS threshold tuning: adjust `rms_threshold` in jarvis.config.json if speech isn't detected or noise triggers false positives


### Phase 3 — Voice Enrollment & Speaker Identification

- [ ] Say "Jarvis, this is [name], walk him/her through the voice print process" — Jarvis greets the new person and asks the first question
- [ ] Jarvis asks age naturally mid-conversation (after ~2 exchanges) — not as the first question
- [ ] Age is parsed correctly in both word form ("six") and digit form ("6")
- [ ] After 6 responses, Jarvis wraps up and says "Perfect, I've got your voice now [name]!"
- [ ] Profile .npz file appears in profiles/ directory after enrollment
- [ ] Restart audio_server.py — profile loads on startup (log shows "loaded profile name=...")
- [ ] After enrollment, saying the wake word and asking a question — Jarvis identifies the speaker by name in the log
- [ ] Named speaker's persona prefix includes name and age in the injected text
- [ ] Unknown speaker (no profile match) falls back to pitch-based adult/kid detection
- [ ] Say "Jarvis, who am I?" — Jarvis announces name and age if enrolled, or says it doesn't recognize you
- [ ] Enroll a second family member — both profiles load and Jarvis distinguishes between them
- [ ] match_threshold in jarvis.config.json is configurable — lower if recognition fails, raise to tighten


### Phase 4 — Response File & TTS Readback

- [ ] Ask Jarvis a simple question — confirm Claude writes response to `jarvis_response.tmp` ending with `---END---`
- [ ] Confirm Jarvis reads the response aloud after Claude finishes
- [ ] Ask a question that produces a long response (e.g. "explain recursion in detail") — confirm Jarvis says "Response is on screen — it's a long one" instead of reading it all
- [ ] Adjust `max_tts_chars` in jarvis.config.json — confirm threshold is respected
- [ ] Kill Claude Code mid-response — confirm Jarvis times out after 120s and says "I didn't get a response — please check the screen"
- [ ] Enroll a new speaker — confirm Claude drives the conversation naturally (asks follow-up questions, weaves in age question)
- [ ] Confirm enrollment Claude fallback works if response file doesn't arrive — Jarvis falls back to hardcoded template question

## Notes
[Record anything ambiguous, flaky, or environment-specific about manual tests here.]
