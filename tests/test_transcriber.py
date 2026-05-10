import numpy as np
from unittest.mock import MagicMock, patch
from Transcriber import Transcriber


class TestTranscriber:
    def _make_audio(self, duration_sec=0.5, sample_rate=16000) -> bytes:
        """Generates silent int16 PCM bytes."""
        n = int(duration_sec * sample_rate)
        return np.zeros(n, dtype=np.int16).tobytes()

    def test_transcribe_returns_string(self):
        transcriber = Transcriber()
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = 'Hello world'
        mock_info = MagicMock()
        mock_info.language = 'en'
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        with patch('Transcriber.WhisperModel', return_value=mock_model):
            result = transcriber.transcribe(self._make_audio(), model='tiny')

        assert isinstance(result, str)
        assert result == 'Hello world'

    def test_transcribe_strips_whitespace(self):
        transcriber = Transcriber()
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = '  hello  '
        mock_info = MagicMock()
        mock_info.language = 'en'
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        with patch('Transcriber.WhisperModel', return_value=mock_model):
            result = transcriber.transcribe(self._make_audio(), model='tiny')

        assert result == 'hello'

    def test_transcribe_empty_segments(self):
        transcriber = Transcriber()
        mock_model = MagicMock()
        mock_info = MagicMock()
        mock_info.language = 'en'
        mock_model.transcribe.return_value = ([], mock_info)

        with patch('Transcriber.WhisperModel', return_value=mock_model):
            result = transcriber.transcribe(self._make_audio(), model='tiny')

        assert result == ''

    def test_model_lazy_loaded_once(self):
        transcriber = Transcriber()
        mock_model = MagicMock()
        mock_info = MagicMock()
        mock_info.language = 'en'
        mock_model.transcribe.return_value = ([], mock_info)

        with patch('Transcriber.WhisperModel', return_value=mock_model) as mock_cls:
            transcriber.transcribe(self._make_audio(), model='tiny')
            transcriber.transcribe(self._make_audio(), model='tiny')

        assert mock_cls.call_count == 1

    def test_tiny_and_medium_are_separate_models(self):
        transcriber = Transcriber()
        mock_tiny = MagicMock()
        mock_medium = MagicMock()
        mock_info = MagicMock()
        mock_info.language = 'en'
        mock_tiny.transcribe.return_value = ([], mock_info)
        mock_medium.transcribe.return_value = ([], mock_info)

        call_count = [0]
        def make_model(size, **kwargs):
            call_count[0] += 1
            return mock_tiny if size == 'tiny' else mock_medium

        with patch('Transcriber.WhisperModel', side_effect=make_model):
            transcriber.transcribe(self._make_audio(), model='tiny')
            transcriber.transcribe(self._make_audio(), model='medium')

        assert call_count[0] == 2
