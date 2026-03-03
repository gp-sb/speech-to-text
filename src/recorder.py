"""
Audio recorder — captures microphone input into a NumPy array.

Uses sounddevice for clean macOS compatibility. Records at 16kHz mono
(what Parakeet expects) and stores audio in a growing buffer until
recording is stopped.
"""

import threading
import time
import logging
import numpy as np

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
except ImportError:
    raise RuntimeError("sounddevice is required: pip install sounddevice")


class Recorder:
    """
    Toggle-based audio recorder.

    Usage:
        recorder = Recorder()
        recorder.start()    # Begin capturing
        # ... user speaks ...
        audio = recorder.stop()  # Returns numpy array of recorded audio
    """

    def __init__(self, sample_rate: int = 16000, max_duration: int = 300):
        """
        Args:
            sample_rate: Recording sample rate in Hz (default 16000 for Parakeet)
            max_duration: Maximum recording duration in seconds (safety limit)
        """
        self.sample_rate = sample_rate
        self.max_duration = max_duration
        self.is_recording = False

        self._audio_chunks: list[np.ndarray] = []
        self._stream = None
        self._lock = threading.Lock()
        self._start_time = 0.0
        self._auto_stop_timer = None

    def start(self):
        """Start recording from the default microphone."""
        logger.debug("Recorder.start() called")
        with self._lock:
            if self.is_recording:
                logger.warning("Already recording — ignoring start()")
                return

            self._audio_chunks = []
            self._start_time = time.time()
            self.is_recording = True

            logger.debug(f"Opening audio stream: sample_rate={self.sample_rate}, channels=1")
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()
            logger.info(f"🎙️ Recording started (sample_rate={self.sample_rate}Hz)")

            # Safety auto-stop
            self._auto_stop_timer = threading.Timer(
                self.max_duration, self._auto_stop
            )
            self._auto_stop_timer.daemon = True
            self._auto_stop_timer.start()
            logger.debug(f"Auto-stop timer set for {self.max_duration}s")

    def stop(self) -> np.ndarray:
        """
        Stop recording and return the captured audio.

        Returns:
            NumPy array of shape (n_samples,) with float32 audio data.
            Returns empty array if nothing was recorded.
        """
        logger.debug("Recorder.stop() called")
        with self._lock:
            if not self.is_recording:
                logger.warning("Not recording — ignoring stop()")
                return np.array([], dtype=np.float32)

            self.is_recording = False
            logger.debug("is_recording set to False")

            if self._auto_stop_timer:
                self._auto_stop_timer.cancel()
                self._auto_stop_timer = None
                logger.debug("Auto-stop timer cancelled")

            if self._stream:
                logger.debug("Stopping audio stream...")
                self._stream.stop()
                self._stream.close()
                self._stream = None
                logger.debug("Audio stream closed")

            duration = time.time() - self._start_time
            logger.info(f"⏹️ Recording stopped — {duration:.1f}s captured, {len(self._audio_chunks)} chunks")

            if not self._audio_chunks:
                logger.warning("No audio chunks captured!")
                return np.array([], dtype=np.float32)

            # Concatenate all chunks into a single array
            logger.debug(f"Concatenating {len(self._audio_chunks)} audio chunks...")
            audio = np.concatenate(self._audio_chunks, axis=0)

            # Flatten from (n, 1) to (n,) if needed
            if audio.ndim > 1:
                audio = audio.flatten()

            logger.debug(f"Final audio: shape={audio.shape}, min={audio.min():.4f}, max={audio.max():.4f}")
            return audio

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio block."""
        if status:
            logger.warning(f"Audio stream status: {status}")

        if self.is_recording:
            self._audio_chunks.append(indata.copy())

    def _auto_stop(self):
        """Auto-stop recording after max_duration."""
        logger.warning(f"Auto-stopping recording after {self.max_duration}s safety limit")
        self.stop()

    @property
    def duration(self) -> float:
        """Current recording duration in seconds."""
        if self.is_recording:
            return time.time() - self._start_time
        return 0.0

    @staticmethod
    def list_devices():
        """List available audio input devices."""
        return sd.query_devices()

    @staticmethod
    def get_default_input():
        """Get info about the default input device."""
        device_id = sd.default.device[0]
        if device_id is not None and device_id >= 0:
            return sd.query_devices(device_id)
        return None
