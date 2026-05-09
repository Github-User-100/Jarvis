# Project: Jarvis
> Created: 2026-05-09 17:16 CDT
> See global CLAUDE.md for universal engineering principles.
> This file adds project-specific rules and overrides.

## Archive Rules — INVIOLABLE
The following files are APPEND-ONLY.
- NEVER use the Write tool on these files — only ever use Edit to append.
- Read the full file before appending to avoid duplicates.
- Every entry must begin with a timestamp: ## YYYY-MM-DD HH:MM TZ — Title
  Get the timestamp with: date "+%Y-%m-%d %H:%M %Z"

Protected files:
  - archive/HX_ISSUES.md
  - archive/DESIGN_DECISIONS.md
  - archive/CHANGELOG.md
  - archive/KNOWN_LIMITATIONS.md

## CURRENT_ISSUES.md Policy
- When the user reports a bug or requests a feature → add to CURRENT_ISSUES.md automatically.
- When Claude notices something tangential while working → ask before adding.
- When work is completed → move entry to archive/HX_ISSUES.md with timestamp and context.

## Plans Policy
- Active plans live at the project root — visible, front and center.
- When a plan is fully implemented → move it to archive/plans/
- Every plan must have a task checklist using `- [ ]` / `- [x]` format.
- Check off each task with `- [x]` AS IT IS COMPLETED — not at the end.
  This is how work survives a context reset: the next session reads the plan,
  sees what is checked, and picks up from the first unchecked item.
- Never mark a task done until the code is written, tests pass, and the change is verified.

### Plan File Format
Every plan created at the project root must follow this structure:

```
# Plan: [Name]

## Goal
[One paragraph describing what this plan accomplishes and why.]

## Tasks
- [ ] Task one
- [ ] Task two
- [ ] Task three

## Notes
[Optional: constraints, open questions, approach decisions.]
```

## Testing Policy
- Every new function must have a corresponding automated regression test in tests\.
- Tests must cover: happy path, edge cases, and known failure modes.
- Run the full test suite after EVERY code change before considering work complete.
- If a test fails after a change, fix it before moving on — do not leave broken tests.
- The testing framework is chosen by Claude when the tech stack is established — record
  the decision in archive/DESIGN_DECISIONS.md.
- Things Claude cannot test (UI, user interaction, OS-level behavior) go in
  tests\MANUAL_TESTS_CHECKLIST.md. Add a checklist item any time such a scenario is identified.

## Definition of Done
A feature or fix is not done until:
  - Code change is implemented
  - Automated tests written and passing
  - Manual checklist updated if applicable (tests\MANUAL_TESTS_CHECKLIST.md)
  - Entry added to archive/HX_ISSUES.md with timestamp
  - CURRENT_ISSUES.md updated
  - Plan moved to archive/plans/ if one existed

## Project-Specific Rules
- This project is a local voice interface for Claude Code in VS Code, themed as "Jarvis" from Iron Man.
- All STT and TTS must be local/free — no cloud APIs, no API keys required.
- Speaker profiles (voice prints and pitch baselines) are stored locally in a profiles/ directory.
- When speaker mode changes (adult → kid), prepend the appropriate persona prefix to the transcribed message before sending to Claude Code.
- Python is the primary language. Keep dependencies minimal and document why each is needed.
- OS target: Windows 10+. PowerShell integration is acceptable where Python falls short.
