import numpy as np
import sounddevice as sd
from AppLogger import AppLogger


class AudioStream:
    """Continuous microphone capture via sounddevice.

    Call start() before reading, stop() when done.
    read_chunk(duration_sec) blocks until the requested audio is available.
    """

    def __init__(self, sample_rate: int = 16000, device=None):
        self._sample_rate = sample_rate
        self._device = device
        self._stream: sd.InputStream = None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def start(self) -> None:
        with AppLogger.enter('AudioStream.start') as log:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype='int16',
                device=self._device,
            )
            self._stream.start()
            device_index = self._stream.device
            device_name = sd.query_devices(device_index)['name']
            log.log('INFO', f'stream started sample_rate={self._sample_rate} device=[{device_index}] {device_name!r}')

    def read_chunk(self, duration_sec: float) -> bytes:
        """Block until duration_sec of audio is available; return raw int16 PCM bytes."""
        n_samples = int(duration_sec * self._sample_rate)
        data, overflowed = self._stream.read(n_samples)
        if overflowed:
            with AppLogger.enter('AudioStream.read_chunk') as log:
                log.log('WARN', 'input overflow — some audio frames were dropped')
        return data.tobytes()

    def stop(self) -> None:
        with AppLogger.enter('AudioStream.stop') as log:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
                log.log('DEBUG', 'stream stopped')
