import numpy as np
import pytest
from SpeechDetector import SpeechDetector


def _make_frame(rms_target: float, sample_rate=16000, duration=0.02) -> bytes:
    """Generate an int16 PCM frame with approximately the given RMS amplitude."""
    n = int(sample_rate * duration)
    if rms_target == 0:
        return np.zeros(n, dtype=np.int16).tobytes()
    # Scale a sine wave to hit the target RMS
    t = np.linspace(0, duration, n, endpoint=False)
    wave = np.sin(2 * np.pi * 440 * t)
    actual_rms = np.sqrt(np.mean(wave ** 2))
    scaled = (wave * (rms_target / actual_rms)).clip(-32768, 32767).astype(np.int16)
    return scaled.tobytes()


class TestIsSpeech:
    def test_silent_frame_is_not_speech(self):
        detector = SpeechDetector(rms_threshold=300.0)
        frame = _make_frame(0)
        assert detector.is_speech(frame) is False

    def test_loud_frame_is_speech(self):
        detector = SpeechDetector(rms_threshold=300.0)
        frame = _make_frame(1000)
        assert detector.is_speech(frame) is True

    def test_threshold_boundary(self):
        detector = SpeechDetector(rms_threshold=500.0)
        below = _make_frame(400)
        above = _make_frame(600)
        assert detector.is_speech(below) is False
        assert detector.is_speech(above) is True


class TestRecordUntilSilence:
    def test_returns_bytes(self):
        detector = SpeechDetector(rms_threshold=300.0)

        # Simulate: 5 silent frames, then 5 speech frames (onset),
        # then SILENCE_TRIGGER_FRAMES silent frames to end
        silent_frame = _make_frame(0)
        speech_frame = _make_frame(1000)
        frames = (
            [silent_frame] * 5 +
            [speech_frame] * SpeechDetector.SPEECH_TRIGGER_FRAMES +
            [speech_frame] * 10 +
            [silent_frame] * SpeechDetector.SILENCE_TRIGGER_FRAMES
        )
        call_count = [0]

        class FakeStream:
            def read_chunk(self, duration):
                idx = call_count[0]
                call_count[0] += 1
                if idx < len(frames):
                    return frames[idx]
                return silent_frame

        result = detector.record_until_silence(FakeStream())
        assert isinstance(result, bytes)
        assert len(result) > 0
