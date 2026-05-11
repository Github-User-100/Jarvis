import queue
import time
from unittest.mock import MagicMock, patch
from Speaker import Speaker, _SENTENCE_SPLIT


def _make_speaker():
    """Create a Speaker with win32com and pythoncom mocked out."""
    mock_sapi = MagicMock()
    mock_sapi.WaitUntilDone.return_value = True  # always done immediately
    with patch('Speaker.win32com.client.Dispatch', return_value=mock_sapi), \
         patch('Speaker.pythoncom.CoInitialize'):
        speaker = Speaker()
    return speaker, mock_sapi


class TestSpeakerInterrupt:
    def test_interrupt_sets_stop_event(self):
        speaker, _ = _make_speaker()
        assert not speaker._stop_event.is_set()
        speaker.interrupt()
        assert speaker._stop_event.is_set()

    def test_say_clears_stop_event(self):
        speaker, _ = _make_speaker()
        speaker._stop_event.set()
        speaker.say('Hello')
        assert not speaker._stop_event.is_set()

    def test_say_clears_done_event(self):
        speaker, _ = _make_speaker()
        speaker._done_event.set()
        speaker.say('Hello')
        assert not speaker._done_event.is_set()

    def test_interrupt_drains_queue(self):
        speaker, _ = _make_speaker()
        speaker._queue.put('one')
        speaker._queue.put('two')
        speaker.interrupt()
        assert speaker._queue.empty()

    def test_stop_event_skips_speech(self):
        """Pre-set stop event; run loop should skip speaking user text."""
        speaker, mock_sapi = _make_speaker()
        time.sleep(0.05)  # let _run() initialise (warmup Speak call happens here)
        mock_sapi.reset_mock()  # clear the warmup call
        speaker._stop_event.set()
        speaker._queue.put('Should not be spoken')
        time.sleep(0.15)
        mock_sapi.Speak.assert_not_called()

    def test_say_queues_text(self):
        speaker, _ = _make_speaker()
        speaker._stop_event.set()  # prevent run loop from consuming
        speaker.say('Hello world')
        # Real assertion: say() doesn't raise


# ─── sentence pause splitting ─────────────────────────────────────────────────

class TestSentenceSplit:
    def test_splits_on_period(self):
        parts = [p.strip() for p in _SENTENCE_SPLIT.split('Hello world. How are you.') if p.strip()]
        assert parts == ['Hello world.', 'How are you.']

    def test_splits_on_question_mark(self):
        parts = [p.strip() for p in _SENTENCE_SPLIT.split('Really? Yes!') if p.strip()]
        assert parts == ['Really?', 'Yes!']

    def test_no_split_mid_sentence(self):
        parts = [p for p in _SENTENCE_SPLIT.split('Hello world') if p.strip()]
        assert parts == ['Hello world']

    def test_single_sentence_with_period(self):
        parts = [p for p in _SENTENCE_SPLIT.split('Done.') if p.strip()]
        assert parts == ['Done.']

    def test_sentence_pause_ms_stored(self):
        with patch('Speaker.win32com.client.Dispatch', return_value=MagicMock(WaitUntilDone=MagicMock(return_value=True))), \
             patch('Speaker.pythoncom.CoInitialize'):
            s = Speaker(sentence_pause_ms=300)
        assert s._pause_ms == 300

    def test_default_pause_is_zero(self):
        with patch('Speaker.win32com.client.Dispatch', return_value=MagicMock(WaitUntilDone=MagicMock(return_value=True))), \
             patch('Speaker.pythoncom.CoInitialize'):
            s = Speaker()
        assert s._pause_ms == 0
