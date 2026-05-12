import time
import pyperclip
import pyautogui
from AppLogger import AppLogger


class VSCodeInjector:
    """Injects text into the focused VS Code Claude Code input box.

    Copies text to clipboard then sends Ctrl+V followed by Enter.
    Requires the Claude Code input box to already be focused in VS Code.
    This is a known UX constraint — documented in MANUAL_TESTS_CHECKLIST.md.
    """

    def __init__(self, paste_delay_sec: float = 0.1):
        self._paste_delay = paste_delay_sec
        pyautogui.FAILSAFE = True

    def inject(self, text: str) -> None:
        with AppLogger.enter('VSCodeInjector.inject') as log:
            log.log('DEBUG', f'injecting text length={len(text)}')
            pyperclip.copy(text)
            time.sleep(self._paste_delay)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(self._paste_delay)
            pyautogui.press('enter')
            log.log('DEBUG', 'injection complete')
