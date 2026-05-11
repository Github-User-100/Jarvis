import json
import os
import sys
import pytest
import numpy as np
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
        j._profiles = {}
        j._config['response_instruction'] = ''  # isolated in persona tests; see TestApplyPersonaInstruction
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

    def test_detects_arvis(self, jarvis):
        assert jarvis._scan_for_wake_word('Arvis') is True

    def test_case_insensitive(self, jarvis):
        assert jarvis._scan_for_wake_word('JARVIS') is True

    def test_not_detected(self, jarvis):
        assert jarvis._scan_for_wake_word('Hello there') is False

    def test_empty(self, jarvis):
        assert jarvis._scan_for_wake_word('') is False


# ─── _idle_until_wake_word ────────────────────────────────────────────────────

class TestIdleUntilWakeWord:
    def test_detects_on_first_utterance(self, jarvis):
        jarvis._detector.record_until_silence.return_value = b'\x00' * 100
        jarvis._transcriber.transcribe.return_value = 'Hey Jarvis'
        jarvis._idle_until_wake_word()
        jarvis._transcriber.transcribe.assert_called_once()

    def test_loops_until_wake_word_found(self, jarvis):
        jarvis._detector.record_until_silence.return_value = b'\x00' * 100
        jarvis._transcriber.transcribe.side_effect = [
            'nothing', 'still nothing', 'Hey Jarvis'
        ]
        jarvis._idle_until_wake_word()
        assert jarvis._transcriber.transcribe.call_count == 3

    def test_full_audio_passed_to_transcriber(self, jarvis):
        audio = b'\x01' * 3200
        jarvis._detector.record_until_silence.return_value = audio
        jarvis._transcriber.transcribe.return_value = 'Jarvis'
        jarvis._idle_until_wake_word()
        jarvis._transcriber.transcribe.assert_called_once_with(audio, model='tiny', initial_prompt='Jarvis')

    def test_uses_detector_not_stream_directly(self, jarvis):
        jarvis._detector.record_until_silence.return_value = b'\x00' * 100
        jarvis._transcriber.transcribe.return_value = 'Jarvis'
        jarvis._idle_until_wake_word()
        jarvis._detector.record_until_silence.assert_called_with(jarvis._stream)
        jarvis._stream.read_chunk.assert_not_called()


# ─── _identify_speaker ────────────────────────────────────────────────────────

def _pcm(f0_hz: float, duration_sec: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Synthesize a pure sine wave at the given frequency as raw int16 PCM."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    wave = (np.sin(2 * np.pi * f0_hz * t) * 32767).astype(np.int16)
    return wave.tobytes()


class TestIdentifySpeaker:
    def test_low_pitch_is_adult(self, jarvis):
        audio = _pcm(120.0)  # typical adult male
        result = jarvis._identify_speaker(audio)
        assert result['type'] == 'adult'

    def test_high_pitch_is_kid(self, jarvis):
        audio = _pcm(320.0)  # typical child
        result = jarvis._identify_speaker(audio)
        assert result['type'] == 'kid'

    def test_boundary_below_threshold_is_adult(self, jarvis):
        audio = _pcm(254.0)
        result = jarvis._identify_speaker(audio)
        assert result['type'] == 'adult'

    def test_boundary_at_threshold_is_kid(self, jarvis):
        audio = _pcm(255.0)
        result = jarvis._identify_speaker(audio)
        assert result['type'] == 'kid'

    def test_silence_defaults_to_adult(self, jarvis):
        audio = bytes(3200)  # all zeros
        result = jarvis._identify_speaker(audio)
        assert result['type'] == 'adult'

    def test_threshold_is_configurable(self, jarvis):
        jarvis._config['kid_pitch_threshold'] = 200.0
        audio = _pcm(210.0)
        assert jarvis._identify_speaker(audio)['type'] == 'kid'
        jarvis._config['kid_pitch_threshold'] = 300.0
        assert jarvis._identify_speaker(audio)['type'] == 'adult'

    def test_returns_dict_with_required_keys(self, jarvis):
        result = jarvis._identify_speaker(_pcm(120.0))
        assert {'name', 'age', 'pronoun', 'type'}.issubset(result.keys())

    def test_unknown_speaker_has_no_name(self, jarvis):
        jarvis._profiles = {}
        result = jarvis._identify_speaker(_pcm(120.0))
        assert result['name'] is None

    def test_profile_match_returns_name(self, jarvis):
        embedding = np.ones(80) / np.sqrt(80)
        jarvis._profiles = {
            'dad': {'name': 'Dad', 'age': 40, 'pronoun': 'him', 'type': 'adult', 'embedding': embedding}
        }
        jarvis._config['match_threshold'] = -1.0  # force a match regardless of score
        result = jarvis._identify_speaker(_pcm(120.0))
        assert result['name'] == 'Dad'


# ─── _apply_persona ───────────────────────────────────────────────────────────

class TestApplyPersona:
    def _adult(self, name=None, age=None):
        return {'name': name, 'age': age, 'pronoun': 'him', 'type': 'adult'}

    def _kid(self, name=None, age=None):
        return {'name': name, 'age': age, 'pronoun': 'her', 'type': 'kid'}

    def test_unknown_adult_gets_generic_prefix(self, jarvis):
        result = jarvis._apply_persona(self._adult(), 'Hello')
        assert result.startswith(jarvis._config['adult_persona_prefix'])
        assert 'Hello' in result

    def test_unknown_kid_gets_generic_prefix(self, jarvis):
        result = jarvis._apply_persona(self._kid(), 'Hello')
        assert result.startswith(jarvis._config['kid_persona_prefix'])
        assert 'Hello' in result

    def test_named_adult_gets_named_template(self, jarvis):
        result = jarvis._apply_persona(self._adult(name='Dave', age=40), 'Hello')
        assert 'Dave' in result
        assert 'Hello' in result

    def test_named_kid_gets_name_and_age(self, jarvis):
        result = jarvis._apply_persona(self._kid(name='Alex', age=6), 'Hello')
        assert 'Alex' in result
        assert '6' in result
        assert 'Hello' in result

    def test_adult_and_kid_prefixes_differ(self, jarvis):
        adult = jarvis._apply_persona(self._adult(), 'Hello')
        kid = jarvis._apply_persona(self._kid(), 'Hello')
        assert adult != kid

    def test_empty_prefix_returns_transcript_unchanged(self, jarvis):
        jarvis._config['adult_persona_prefix'] = ''
        result = jarvis._apply_persona(self._adult(), 'Hello')
        assert result == 'Hello'

    def test_transcript_appended_after_prefix(self, jarvis):
        jarvis._config['adult_persona_prefix'] = '[PREFIX]'
        result = jarvis._apply_persona(self._adult(), 'my question')
        assert result == '[PREFIX] my question'


# ─── _tts_name ───────────────────────────────────────────────────────────────

class TestTtsName:
    def test_mapped_name_returns_pronunciation(self, jarvis):
        jarvis._config['name_pronunciations'] = {'A.J.': 'A J'}
        assert jarvis._tts_name('A.J.') == 'A J'

    def test_unmapped_name_returns_original(self, jarvis):
        jarvis._config['name_pronunciations'] = {}
        assert jarvis._tts_name('Alex') == 'Alex'

    def test_empty_map_returns_original(self, jarvis):
        jarvis._config['name_pronunciations'] = {}
        assert jarvis._tts_name('A.J.') == 'A.J.'


# ─── _parse_enrollment_trigger ───────────────────────────────────────────────

class TestParseEnrollmentTrigger:
    def test_detects_walk_her_through(self, jarvis):
        result = jarvis._parse_enrollment_trigger('Jarvis, this is Alex, walk her through the voice print process')
        assert result == ('Alex', 'her')

    def test_detects_imprint(self, jarvis):
        result = jarvis._parse_enrollment_trigger('Jarvis, this is Sam, please imprint him')
        assert result == ('Sam', 'him')

    def test_detects_enroll(self, jarvis):
        result = jarvis._parse_enrollment_trigger('this is Jordan, please enroll them')
        assert result == ('Jordan', 'them')

    def test_defaults_pronoun_to_them(self, jarvis):
        result = jarvis._parse_enrollment_trigger('this is Riley, please imprint')
        assert result[1] == 'them'

    def test_capitalises_name(self, jarvis):
        result = jarvis._parse_enrollment_trigger('this is alex, please enroll her')
        assert result[0] == 'Alex'

    def test_no_keyword_returns_none(self, jarvis):
        assert jarvis._parse_enrollment_trigger('Jarvis, this is Alex') is None

    def test_no_name_returns_none(self, jarvis):
        assert jarvis._parse_enrollment_trigger('please imprint her voice') is None

    def test_normal_question_returns_none(self, jarvis):
        assert jarvis._parse_enrollment_trigger('what is the weather today') is None


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


# ─── _apply_persona response instruction ─────────────────────────────────────

class TestApplyPersonaInstruction:
    def test_instruction_appended_to_message(self, jarvis):
        jarvis._config['response_instruction'] = '[WRITE TO FILE]'
        jarvis._config['adult_persona_prefix'] = '[PREFIX]'
        result = jarvis._apply_persona({'type': 'adult', 'name': None, 'age': None}, 'hello')
        assert result == '[PREFIX] hello [WRITE TO FILE]'

    def test_instruction_appended_when_no_prefix(self, jarvis):
        jarvis._config['response_instruction'] = '[WRITE TO FILE]'
        jarvis._config['adult_persona_prefix'] = ''
        result = jarvis._apply_persona({'type': 'adult', 'name': None, 'age': None}, 'hello')
        assert result == 'hello [WRITE TO FILE]'

    def test_no_instruction_leaves_message_unchanged(self, jarvis):
        jarvis._config['response_instruction'] = ''
        jarvis._config['adult_persona_prefix'] = '[PREFIX]'
        result = jarvis._apply_persona({'type': 'adult', 'name': None, 'age': None}, 'hello')
        assert result == '[PREFIX] hello'


# ─── _wait_for_response ───────────────────────────────────────────────────────

class TestWaitForResponse:
    def test_returns_content_before_sentinel(self, jarvis, tmp_path):
        f = tmp_path / 'response.tmp'
        jarvis._config['response_file'] = str(f)
        jarvis._config['response_timeout_seconds'] = 5
        f.write_text('Hello from Claude\n---END---\n', encoding='utf-8')
        result = jarvis._wait_for_response()
        assert result == 'Hello from Claude'

    def test_strips_trailing_whitespace(self, jarvis, tmp_path):
        f = tmp_path / 'response.tmp'
        jarvis._config['response_file'] = str(f)
        jarvis._config['response_timeout_seconds'] = 5
        f.write_text('Hello\n\n---END---\n', encoding='utf-8')
        assert jarvis._wait_for_response() == 'Hello'

    def test_returns_none_on_timeout(self, jarvis, tmp_path):
        f = tmp_path / 'response.tmp'
        jarvis._config['response_file'] = str(f)
        jarvis._config['response_timeout_seconds'] = 0.2
        f.write_text('', encoding='utf-8')
        assert jarvis._wait_for_response() is None

    def test_multiline_response_preserved(self, jarvis, tmp_path):
        f = tmp_path / 'response.tmp'
        jarvis._config['response_file'] = str(f)
        jarvis._config['response_timeout_seconds'] = 5
        f.write_text('Line one\nLine two\n---END---\n', encoding='utf-8')
        assert jarvis._wait_for_response() == 'Line one\nLine two'
