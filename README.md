# Speech-to-Text

Local speech-to-text for macOS. Press a hotkey to start talking, press again to stop — transcribed text gets pasted wherever your cursor is.

Runs entirely on your Mac using NVIDIA's [Parakeet](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2) model via [parakeet-mlx](https://github.com/senstella/parakeet-mlx) (optimized for Apple Silicon). No cloud, no API keys, no per-minute costs.

## Quick Start

```bash
git clone https://github.com/gp-sb/speech-to-text.git
cd speech-to-text
chmod +x scripts/install.sh
./scripts/install.sh
```

The install script will:
1. Create a Python virtual environment
2. Install all dependencies
3. Download the Parakeet model (~2.4 GB, one-time)
4. Print instructions for granting macOS permissions

Then run:

```bash
source venv/bin/activate
python -m src.app
```

## Usage

1. The app sits in your **menu bar** as a 🎤 icon
2. Press **Cmd+Shift+Space** to start recording (icon turns 🔴)
3. Speak naturally — Parakeet handles fast speech, accents, and technical vocabulary
4. Press **Cmd+Shift+Space** again to stop
5. Transcribed text is **pasted at your cursor** — in any app

### Terminal Mode

If you prefer no menu bar icon (or for debugging):

```bash
python -m src.app --terminal
```

## Configuration

Edit `config.yaml` to customize:

```yaml
hotkey: "cmd+shift+space"              # Change the keyboard shortcut
model: "mlx-community/parakeet-tdt-0.6b-v2"  # English (or v3 for 25 languages)
max_duration: 300                       # Max recording seconds (safety limit)
restore_clipboard: true                 # Preserve your clipboard after paste
sound_on_start: true                    # Audio feedback when recording starts
sound_on_stop: true                     # Audio feedback when recording stops
```

## macOS Permissions

The app needs two permissions:

**Accessibility** (for hotkeys + paste):
System Settings → Privacy & Security → Accessibility → add your Terminal app

**Microphone** (for recording):
macOS prompts automatically on first use — just click Allow.

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.10+
- FFmpeg (for audio processing)

### Installing FFmpeg

```bash
# Via Homebrew
brew install ffmpeg

# Or via conda (if using a conda environment)
conda install ffmpeg
```

### Using a Conda Environment

If your system Python is older than 3.10, you can use a conda environment:

```bash
conda create -n speech-to-text python=3.12 ffmpeg -y
conda activate speech-to-text
pip install -r requirements.txt

# Download the model
python -c "from parakeet_mlx import from_pretrained; from_pretrained('mlx-community/parakeet-tdt-0.6b-v2')"

# Run the app
python -m src.app
```

### Fallback for Intel Macs

If you're on Intel, swap the STT engine in `requirements.txt`:

```
# Comment out:
# parakeet-mlx>=0.5.0

# Uncomment:
faster-whisper>=1.0.0
```

The app auto-detects which engine is available and uses it.

## Architecture

```
Hotkey (pynput) → Recorder (sounddevice) → Parakeet-MLX → Paste at cursor (pbcopy + osascript)
```

Five modules, each doing one thing:

| Module | Job |
|--------|-----|
| `src/app.py` | Main app — menu bar + state machine |
| `src/hotkey.py` | Global hotkey detection |
| `src/recorder.py` | Microphone audio capture |
| `src/transcriber.py` | Parakeet model inference |
| `src/paster.py` | Clipboard + paste at cursor |

## Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

## Credits

Inspired by [Super-Voice-Assistant](https://github.com/hounfodji/Super-Voice-Assistant) 
