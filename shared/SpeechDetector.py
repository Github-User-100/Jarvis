import numpy as np
from collections import deque
from AppLogger import AppLogger


class SpeechDetector:
    """Energy-based voice activity detector.

    Uses RMS amplitude of each 20ms frame to detect speech onset and end.
    No C extensions required — pure numpy.

    Thresholds are configurable; defaults tuned for a quiet home with a close mic.
    Lower rms_threshold if Jarvis misses speech; raise it if ambient noise triggers false positives.
    """

    FRAME_DURATION = 0.02       # 20ms frames
    SPEECH_TRIGGER_FRAMES = 3   # consecutive speech frames to confirm onset
    SILENCE_TRIGGER_FRAMES = 55 # 1.1 seconds of silence to end recording
    PRE_BUFFER_FRAMES = 15      # 300ms of audio kept before speech onset

    def __init__(self, sample_rate: int = 16000, rms_threshold: float = 300.0):
        self._sample_rate = sample_rate
        self._rms_threshold = rms_threshold
        self._frame_samples = int(sample_rate * self.FRAME_DURATION)

    def _rms(self, frame_bytes: bytes) -> float:
        samples = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32)
        return float(np.sqrt(np.mean(samples ** 2)))

    def is_speech(self, frame_bytes: bytes) -> bool:
        return self._rms(frame_bytes) >= self._rms_threshold

    def record_until_silence(self, stream) -> bytes:
        """Read from stream frame-by-frame until 1.5s of silence after speech onset.

        Returns the full utterance as raw int16 PCM bytes, including a 300ms pre-buffer
        so the first syllable is not clipped.
        """
        with AppLogger.enter('SpeechDetector.record_until_silence') as log:
            frame_duration = self.FRAME_DURATION
            ring_buffer = deque(maxlen=self.PRE_BUFFER_FRAMES)
            num_speech = 0
            num_silence = 0
            recording = False
            recorded_frames = []

            log.log('DEBUG', f'listening for speech onset rms_threshold={self._rms_threshold}')

            while True:
                frame = stream.read_chunk(frame_duration)
                speech = self.is_speech(frame)

                if not recording:
                    ring_buffer.append(frame)
                    if speech:
                        num_speech += 1
                        if num_speech >= self.SPEECH_TRIGGER_FRAMES:
                            recording = True
                            recorded_frames = list(ring_buffer)
                            num_silence = 0
                            log.log('INFO', 'speech onset detected — recording')
                    else:
                        num_speech = 0
                else:
                    recorded_frames.append(frame)
                    if speech:
                        num_silence = 0
                    else:
                        num_silence += 1
                        if num_silence >= self.SILENCE_TRIGGER_FRAMES:
                            duration = len(recorded_frames) * frame_duration
                            log.log('INFO', f'silence detected — recording complete duration={duration:.2f}s frames={len(recorded_frames)}')
                            break

            return b''.join(recorded_frames)
