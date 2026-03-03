"""Tests for the audio recorder module."""

import sys
import time
import numpy as np
import unittest
from unittest.mock import MagicMock

# conftest.py already mocked sounddevice in sys.modules


class TestRecorder(unittest.TestCase):
    """Test the Recorder class."""

    def test_init_defaults(self):
        from src.recorder import Recorder
        r = Recorder()
        assert r.sample_rate == 16000
        assert r.max_duration == 300
        assert r.is_recording is False

    def test_init_custom(self):
        from src.recorder import Recorder
        r = Recorder(sample_rate=44100, max_duration=60)
        assert r.sample_rate == 44100
        assert r.max_duration == 60

    def test_stop_without_start_returns_empty(self):
        from src.recorder import Recorder
        r = Recorder()
        audio = r.stop()
        assert isinstance(audio, np.ndarray)
        assert audio.size == 0

    def test_start_creates_stream(self):
        from src.recorder import Recorder, sd

        mock_stream = MagicMock()
        sd.InputStream.return_value = mock_stream

        r = Recorder()
        r.start()

        assert r.is_recording is True
        sd.InputStream.assert_called()
        mock_stream.start.assert_called_once()

        r.stop()

    def test_start_stop_cycle(self):
        from src.recorder import Recorder, sd

        mock_stream = MagicMock()
        sd.InputStream.return_value = mock_stream

        r = Recorder()
        r.start()
        assert r.is_recording is True

        # Simulate audio data arriving via callback
        fake_audio = np.random.randn(1024, 1).astype(np.float32)
        r._audio_callback(fake_audio, 1024, None, None)
        r._audio_callback(fake_audio, 1024, None, None)

        audio = r.stop()
        assert r.is_recording is False
        assert isinstance(audio, np.ndarray)
        assert audio.ndim == 1  # Should be flattened
        assert audio.size == 2048  # Two chunks of 1024

    def test_double_start_ignored(self):
        from src.recorder import Recorder, sd

        mock_stream = MagicMock()
        sd.InputStream.return_value = mock_stream

        r = Recorder()
        r.start()
        initial_call_count = sd.InputStream.call_count
        r.start()  # Should be ignored

        # No additional stream created
        assert sd.InputStream.call_count == initial_call_count

        r.stop()

    def test_duration_property(self):
        from src.recorder import Recorder, sd

        mock_stream = MagicMock()
        sd.InputStream.return_value = mock_stream

        r = Recorder()
        assert r.duration == 0.0

        r.start()
        time.sleep(0.1)
        assert r.duration > 0.0

        r.stop()

    def test_audio_callback_ignores_when_not_recording(self):
        from src.recorder import Recorder

        r = Recorder()
        r.is_recording = False

        fake_audio = np.random.randn(1024, 1).astype(np.float32)
        r._audio_callback(fake_audio, 1024, None, None)

        assert len(r._audio_chunks) == 0


class TestRecorderDevices(unittest.TestCase):
    """Test device listing."""

    def test_list_devices(self):
        from src.recorder import Recorder, sd
        Recorder.list_devices()
        sd.query_devices.assert_called()


if __name__ == "__main__":
    unittest.main()
