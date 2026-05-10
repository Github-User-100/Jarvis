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


## Notes
[Record anything ambiguous, flaky, or environment-specific about manual tests here.]
