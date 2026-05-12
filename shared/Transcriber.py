import numpy as np
from faster_whisper import WhisperModel
from AppLogger import AppLogger

_CUDA_LADDER = ['int8_float16', 'float16', 'int8', 'float32']
_CPU_LADDER  = ['int8', 'float32']


class Transcriber:
    """faster-whisper wrapper with lazy model loading.

    tiny model: loaded on first call with model='tiny' — used for idle wake-word scanning.
    medium model: loaded on first call with model='medium' — used for active transcription.

    Models are downloaded from Hugging Face on first use (~150MB tiny, ~1.5GB medium).
    Subsequent runs use the cached copy.
    """

    def __init__(self, device: str = 'auto', compute_type: str = 'auto'):
        with AppLogger.enter('Transcriber.__init__') as log:
            if device == 'auto':
                try:
                    import ctranslate2
                    if ctranslate2.get_cuda_device_count() > 0:
                        device = 'cuda'
                        log.log('INFO', 'CUDA device found — CUDA enabled')
                    else:
                        device = 'cpu'
                        log.log('INFO', 'No CUDA device found — CUDA disabled, using CPU')
                except Exception:
                    device = 'cpu'
                    log.log('INFO', 'CUDA detection failed — falling back to CPU')
            self._device = device
            self._compute_type = compute_type  # 'auto' → _load() walks the ladder
            self._models: dict = {}

    def _load(self, model_size: str):
        if model_size not in self._models:
            with AppLogger.enter('Transcriber._load') as log:
                if self._compute_type == 'auto':
                    ladder = _CUDA_LADDER if self._device == 'cuda' else _CPU_LADDER
                else:
                    ladder = [self._compute_type]

                for compute_type in ladder:
                    try:
                        log.log('INFO', f'loading model={model_size} device={self._device} compute_type={compute_type}')
                        self._models[model_size] = WhisperModel(
                            model_size,
                            device=self._device,
                            compute_type=compute_type,
                        )
                        log.log('INFO', f'model={model_size} ready — using compute_type={compute_type}')
                        break
                    except (ValueError, RuntimeError) as e:
                        log.log('WARN', f'compute_type={compute_type} not supported ({e}) — trying next')
                        if compute_type == ladder[-1]:
                            raise
        return self._models[model_size]

    def transcribe(self, audio_bytes: bytes, model: str = 'tiny', initial_prompt: str = None) -> str:
        """Transcribe raw int16 PCM bytes. Returns stripped transcript string."""
        with AppLogger.enter('Transcriber.transcribe') as log:
            log.log('DEBUG', f'model={model} audio_bytes={len(audio_bytes)} initial_prompt={initial_prompt!r}')
            whisper = self._load(model)
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            kwargs = dict(beam_size=5, language='en', vad_filter=True)
            if initial_prompt:
                kwargs['initial_prompt'] = initial_prompt
            try:
                segments, info = whisper.transcribe(audio_np, **kwargs)
                transcript = ' '.join(s.text for s in segments).strip()
            except RuntimeError as e:
                if self._device != 'cuda':
                    raise
                log.log('WARN', f'CUDA inference failed ({e}) — clearing models and falling back to CPU')
                self._models.clear()
                self._device = 'cpu'
                self._compute_type = 'auto'
                whisper = self._load(model)
                segments, info = whisper.transcribe(audio_np, **kwargs)
                transcript = ' '.join(s.text for s in segments).strip()
            log.log('DEBUG', f'transcript={transcript!r} language={info.language}')
            return transcript
