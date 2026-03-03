"""
Transcription engine — runs Parakeet-MLX locally on Apple Silicon.

Handles model loading, audio-to-text inference, and fallback to faster-whisper
if parakeet-mlx isn't available.
"""

import os
import tempfile
import logging
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# Track which engine is active
_engine = None
_model = None


def _get_engine():
    """Detect which STT engine is available. Prefer parakeet-mlx, fall back to faster-whisper."""
    global _engine

    if _engine is not None:
        return _engine

    # Try parakeet-mlx first (Apple Silicon optimized)
    try:
        import parakeet_mlx  # noqa: F401
        _engine = "parakeet"
        logger.info("Using parakeet-mlx engine (Apple Silicon optimized)")
        return _engine
    except ImportError:
        logger.warning("parakeet-mlx not available, trying faster-whisper...")

    # Fall back to faster-whisper
    try:
        import faster_whisper  # noqa: F401
        _engine = "faster-whisper"
        logger.info("Using faster-whisper engine (fallback)")
        return _engine
    except ImportError:
        logger.error("No STT engine available. Install parakeet-mlx or faster-whisper.")
        raise RuntimeError(
            "No speech-to-text engine found.\n"
            "Install one of:\n"
            "  pip install parakeet-mlx    (recommended for Apple Silicon)\n"
            "  pip install faster-whisper  (fallback)\n"
        )


def load_model(model_name: str = None):
    """
    Load the STT model. Downloads on first run (~2.4 GB for Parakeet).

    Args:
        model_name: Model identifier. Defaults based on engine:
            - parakeet: "mlx-community/parakeet-tdt-0.6b-v2"
            - faster-whisper: "base"
    """
    global _model

    engine = _get_engine()

    if engine == "parakeet":
        from parakeet_mlx import from_pretrained
        model_name = model_name or "mlx-community/parakeet-tdt-0.6b-v2"
        logger.info(f"Loading Parakeet model: {model_name}")
        logger.info("(First run will download ~2.4 GB \u2014 be patient)")
        _model = from_pretrained(model_name)
        logger.info("Parakeet model loaded successfully")

    elif engine == "faster-whisper":
        from faster_whisper import WhisperModel
        model_name = model_name or "base"
        logger.info(f"Loading faster-whisper model: {model_name}")
        _model = WhisperModel(model_name, device="auto", compute_type="default")
        logger.info("faster-whisper model loaded successfully")

    return _model


def transcribe(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Transcribe audio to text.

    Args:
        audio: NumPy array of audio samples (float32, mono)
        sample_rate: Sample rate of the audio (default 16000 Hz)

    Returns:
        Transcribed text string
    """
    global _model

    if _model is None:
        load_model()

    engine = _get_engine()

    if engine == "parakeet":
        return _transcribe_parakeet(audio, sample_rate)
    elif engine == "faster-whisper":
        return _transcribe_faster_whisper(audio, sample_rate)


def _transcribe_parakeet(audio: np.ndarray, sample_rate: int) -> str:
    """Transcribe using parakeet-mlx."""
    from parakeet_mlx import DecodingConfig, SentenceConfig

    # parakeet-mlx expects a file path, so write audio to a temp WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        sf.write(temp_path, audio, sample_rate)

    try:
        config = DecodingConfig(
            sentence=SentenceConfig(
                max_words=50,
                silence_gap=3.0,
                max_duration=60.0,
            )
        )
        result = _model.transcribe(temp_path, decoding_config=config)

        # Extract text from sentences
        if hasattr(result, "sentences") and result.sentences:
            text = " ".join(s.text.strip() for s in result.sentences if s.text.strip())
        elif hasattr(result, "text"):
            text = result.text.strip()
        else:
            text = str(result).strip()

        return text

    finally:
        os.unlink(temp_path)


def _transcribe_faster_whisper(audio: np.ndarray, sample_rate: int) -> str:
    """Transcribe using faster-whisper."""
    # faster-whisper can accept a file path or a numpy array
    # Write to temp file for consistent behavior
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        sf.write(temp_path, audio, sample_rate)

    try:
        segments, _info = _model.transcribe(temp_path, beam_size=5)
        text = " ".join(segment.text.strip() for segment in segments)
        return text
    finally:
        os.unlink(temp_path)
