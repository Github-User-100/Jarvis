import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from Jarvis import Jarvis, _DEFAULT_CONFIG


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def jarvis(tmp_path):
    """Jarvis instance with all infrastructure mocked out."""
    with patch('Jarvis.AudioStream'), \
         patch('Jarvis.SpeechDetector'), \
         patch('Jarvis.Transcriber'), \
         patch('Jarvis.Speaker'), \
         patch('Jarvis.VSCodeInjector'):
        j = Jarvis.__new__(Jarvis)
        j._config = dict(_DEFAULT_CONFIG)
        j._stream = MagicMock()
        j._detector = MagicMock()
        j._transcriber = MagicMock()
        j._speaker = MagicMock()
        j._injector = MagicMock()
        return j


# ─── _is_dismissal ────────────────────────────────────────────────────────────

class TestIsDismissal:
    def test_thanks_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Thanks Jarvis') is True

    def test_thank_you_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Thank you Jarvis') is True

    def test_goodbye_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Goodbye Jarvis') is True

    def test_bye_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Bye Jarvis') is True

    def test_hush_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Hush Jarvis') is True

    def test_quiet_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Quiet Jarvis') is True

    def test_stop_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Stop Jarvis') is True

    def test_sleep_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Sleep Jarvis') is True

    def test_dismissed_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Dismissed Jarvis') is True

    def test_thats_all_jarvis(self, jarvis):
        assert jarvis._is_dismissal("That's all Jarvis") is True

    def test_enough_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Enough Jarvis') is True

    def test_later_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Later Jarvis') is True

    def test_shush_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Shush Jarvis') is True

    def test_go_away_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Go away Jarvis') is True

    def test_case_insensitive(self, jarvis):
        assert jarvis._is_dismissal('THANKS JARVIS') is True

    def test_dismissal_word_in_middle(self, jarvis):
        assert jarvis._is_dismissal('Ok thanks Jarvis') is True

    def test_no_jarvis(self, jarvis):
        assert jarvis._is_dismissal('Thanks') is False

    def test_jarvis_before_dismissal(self, jarvis):
        # "Jarvis thanks" — Jarvis comes first, so not a dismissal
        assert jarvis._is_dismissal('Jarvis thanks') is False

    def test_normal_question(self, jarvis):
        assert jarvis._is_dismissal('Jarvis what time is it') is False

    def test_empty_string(self, jarvis):
        assert jarvis._is_dismissal('') is False


# ─── _scan_for_wake_word ──────────────────────────────────────────────────────

class TestScanForWakeWord:
    def test_detects_jarvis(self, jarvis):
        assert jarvis._scan_for_wake_word('Hey Jarvis') is True

    def test_case_insensitive(self, jarvis):
        assert jarvis._scan_for_wake_word('JARVIS') is True

    def test_not_detected(self, jarvis):
        assert jarvis._scan_for_wake_word('Hello there') is False

    def test_empty(self, jarvis):
        assert jarvis._scan_for_wake_word('') is False


# ─── config loading ───────────────────────────────────────────────────────────

class TestLoadConfig:
    def test_loads_from_file(self, tmp_path):
        cfg_path = tmp_path / 'jarvis.config.json'
        cfg_path.write_text(json.dumps({'whisper_model': 'small', 'tts_rate': 150}))
        with patch('Jarvis._CONFIG_PATH', str(cfg_path)), \
             patch('Jarvis.AudioStream'), patch('Jarvis.SpeechDetector'), \
             patch('Jarvis.Transcriber'), patch('Jarvis.Speaker'), \
             patch('Jarvis.VSCodeInjector'):
            j = Jarvis.__new__(Jarvis)
            j._config = j._load_config()
        assert j._config['whisper_model'] == 'small'
        assert j._config['tts_rate'] == 150

    def test_defaults_when_file_missing(self, tmp_path):
        missing = str(tmp_path / 'no_such_file.json')
        with patch('Jarvis._CONFIG_PATH', missing), \
             patch('Jarvis.AudioStream'), patch('Jarvis.SpeechDetector'), \
             patch('Jarvis.Transcriber'), patch('Jarvis.Speaker'), \
             patch('Jarvis.VSCodeInjector'):
            j = Jarvis.__new__(Jarvis)
            j._config = j._load_config()
        assert j._config['whisper_model'] == _DEFAULT_CONFIG['whisper_model']
        assert 'dismissal_words' in j._config
