import queue
import re
import time
import threading
import win32com.client
import pythoncom
from AppLogger import AppLogger

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])(?=\s|$)')

_ASYNC = 1           # SVSFlagsAsync
_PURGE = 2           # SVSFPurgeBeforeSpeak
_ASYNC_PURGE = 3     # stop + clear queue
_XML = 8             # SVSFIsXML — treat string as SAPI XML markup


class Speaker:
    """Windows SAPI TTS via win32com with a single persistent daemon thread.

    SAPI COM objects have thread affinity — the voice object is created once
    inside the daemon thread and never touched from outside it.

    say(text)     — queues text for speaking.
    interrupt()   — stops current speech and drains the queue.
    wait_done()   — blocks until speech finishes.
    """

    def __init__(self, rate: int = 1, volume: float = 1.0, sentence_pause_ms: int = 0):
        # rate: SAPI scale -10 (slowest) to 10 (fastest), 0 = ~150 WPM default
        # volume: 0.0–1.0 mapped to SAPI 0–100
        # sentence_pause_ms: silence inserted after each sentence boundary (0 = disabled)
        self._rate = rate
        self._volume = int(volume * 100)
        self._pause_ms = sentence_pause_ms
        self._stop_event = threading.Event()
        self._done_event = threading.Event()
        self._done_event.set()
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def say(self, text: str) -> None:
        with AppLogger.enter('Speaker.say') as log:
            self._stop_event.clear()
            self._done_event.clear()
            log.log('DEBUG', f'queuing: {text!r}')
            self._queue.put(text)

    def interrupt(self) -> None:
        with AppLogger.enter('Speaker.interrupt') as log:
            log.log('INFO', 'interrupt requested — draining queue')
            self._stop_event.set()
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break

    def wait_done(self) -> None:
        self._done_event.wait()

    def _run(self) -> None:
        log = AppLogger.enter('Speaker._run')
        pythoncom.CoInitialize()
        try:
            sapi = win32com.client.Dispatch('SAPI.SpVoice')
            sapi.Rate = self._rate
            sapi.Volume = 0
            sapi.Speak('warmup', _ASYNC)
            sapi.WaitUntilDone(-1)
            sapi.Volume = self._volume
            log.log('INFO', 'SAPI voice ready')

            while True:
                text = self._queue.get()
                if text is None:
                    break
                if self._stop_event.is_set():
                    log.log('INFO', 'TTS skipped — stop event set')
                    self._done_event.set()
                    continue
                # Silent lead-in queued first — SAPI reconnects to the audio
                # device during this, so the real text starts without clipping
                sapi.Speak('<SILENCE MSEC="700"/>', _ASYNC | _XML)
                if self._pause_ms > 0:
                    silence = f'<SILENCE MSEC="{self._pause_ms}"/>'
                    for chunk in _SENTENCE_SPLIT.split(text):
                        chunk = chunk.strip()
                        if chunk:
                            sapi.Speak(chunk, _ASYNC)
                            sapi.Speak(silence, _ASYNC | _XML)
                else:
                    sapi.Speak(text, _ASYNC)
                while True:
                    time.sleep(0.05)
                    if self._stop_event.is_set():
                        sapi.Speak('', _ASYNC_PURGE)
                        log.log('INFO', 'TTS interrupted mid-speech')
                        break
                    if sapi.WaitUntilDone(0):
                        break
                self._done_event.set()

        except Exception as e:
            log.log('ERROR', f'speaker thread error: {e}')
        finally:
            log.log('DEBUG', 'speaker thread exiting')
