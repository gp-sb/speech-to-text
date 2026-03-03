"""Tests for the transcriber module."""

import numpy as np
import unittest
from unittest.mock import patch, MagicMock


class TestEngineDetection(unittest.TestCase):
    """Test STT engine auto-detection."""

    def setUp(self):
        """Reset global state between tests."""
        import src.transcriber as t
        t._engine = None
        t._model = None

    @patch.dict("sys.modules", {"parakeet_mlx": MagicMock()})
    def test_prefers_parakeet(self):
        """Prefers parakeet-mlx when available."""
        from src.transcriber import _get_engine
        engine = _get_engine()
        assert engine == "parakeet"

    @patch.dict("sys.modules", {"parakeet_mlx": None, "faster_whisper": MagicMock()})
    def test_falls_back_to_faster_whisper(self):
        """Falls back to faster-whisper when parakeet-mlx is unavailable."""
        import src.transcriber as t
        t._engine = None

        # Mock import failure for parakeet_mlx
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "parakeet_mlx":
                raise ImportError("No module named 'parakeet_mlx'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            engine = t._get_engine()
            assert engine == "faster-whisper"

    def test_raises_when_no_engine(self):
        """Raises RuntimeError when no STT engine is available."""
        import src.transcriber as t
        t._engine = None

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name in ("parakeet_mlx", "faster_whisper"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with self.assertRaises(RuntimeError) as ctx:
                t._get_engine()
            assert "No speech-to-text engine found" in str(ctx.exception)


class TestTranscribe(unittest.TestCase):
    """Test the transcribe function with mocked models."""

    def setUp(self):
        import src.transcriber as t
        t._engine = None
        t._model = None

    @patch("src.transcriber._get_engine", return_value="parakeet")
    @patch("src.transcriber.load_model")
    @patch("src.transcriber._transcribe_parakeet", return_value="hello world")
    def test_transcribe_returns_text(self, mock_tp, mock_load, mock_engine):
        """transcribe() returns a string."""
        import src.transcriber as t
        t._model = MagicMock()  # Pretend model is loaded

        audio = np.random.randn(16000).astype(np.float32)
        result = t.transcribe(audio)

        assert isinstance(result, str)
        assert result == "hello world"

    @patch("src.transcriber._get_engine", return_value="parakeet")
    def test_transcribe_loads_model_if_needed(self, mock_engine):
        """transcribe() auto-loads the model on first call."""
        import src.transcriber as t

        with patch("src.transcriber.load_model") as mock_load:
            with patch("src.transcriber._transcribe_parakeet", return_value="test"):
                t._model = None
                audio = np.random.randn(16000).astype(np.float32)
                t.transcribe(audio)
                mock_load.assert_called_once()


if __name__ == "__main__":
    unittest.main()
