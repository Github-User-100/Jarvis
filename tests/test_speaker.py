import threading
import time
from unittest.mock import MagicMock, patch
from Speaker import Speaker


class TestSpeakerInterrupt:
    def test_interrupt_sets_stop_event(self):
        speaker = Speaker()
        assert not speaker._stop_event.is_set()
        speaker.interrupt()
        assert speaker._stop_event.is_set()

    def test_say_clears_stop_event(self):
        speaker = Speaker()
        speaker._stop_event.set()
        with patch('Speaker.pyttsx3') as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_pyttsx3.init.return_value = mock_engine
            speaker.say('Hello')
            time.sleep(0.05)
        assert not speaker._stop_event.is_set()

    def test_stop_event_prevents_sentences(self):
        """Pre-set stop event; _speak_thread should not speak any sentences."""
        speaker = Speaker()
        speaker._stop_event.set()
        spoken = []

        with patch('Speaker.pyttsx3') as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_engine.say.side_effect = lambda t: spoken.append(t)
            mock_pyttsx3.init.return_value = mock_engine
            speaker._speak_thread('First. Second. Third.')

        assert len(spoken) == 0
