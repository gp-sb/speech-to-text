# Speech-to-Text Tool — Build Plan

## What This Is

A lightweight, local speech-to-text tool for macOS that:

1. Sits in the menu bar as a persistent icon
2. Toggles recording on/off with a global hotkey
3. Transcribes speech locally using NVIDIA's Parakeet model (via Apple Silicon-optimized MLX)
4. Pastes the transcribed text wherever your cursor is — any app, any text field

No cloud. No API keys. No costs after initial model download (~2.4 GB one-time).

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Menu Bar App                       │
│              (rumps — macOS native)                   │
│                                                       │
│   Icon states: ⏸ Idle  |  🔴 Recording  |  ⏳ Processing │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────┐    ┌──────────────────────────┐    │
│  │  Hotkey       │    │  Audio Recorder           │    │
│  │  Listener     │───▶│  (sounddevice)            │    │
│  │  (pynput)     │    │  16kHz mono float32       │    │
│  └──────────────┘    └──────────┬───────────────┘    │
│                                  │                     │
│                                  ▼                     │
│                     ┌──────────────────────────┐      │
│                     │  Parakeet-MLX             │      │
│                     │  (local inference)         │      │
│                     │  Model: tdt-0.6b-v2       │      │
│                     └──────────┬───────────────┘      │
│                                  │                     │
│                                  ▼                     │
│                     ┌──────────────────────────┐      │
│                     │  Paste at Cursor           │      │
│                     │  (pbcopy + Cmd+V)          │      │
│                     └──────────────────────────┘      │
└─────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Menu Bar App (rumps)

The app lives in the macOS menu bar. No dock icon, no window — just a small status icon.

- **Idle state**: Shows a microphone icon (⏸ or 🎤)
- **Recording state**: Icon changes to red (🔴) so you know it's listening
- **Processing state**: Icon changes to spinner/hourglass while transcribing
- **Right-click menu**: Quit, Settings (hotkey config), About

Library: `rumps` — purpose-built for macOS menu bar apps. Tiny, stable, no Electron bloat.

### 2. Global Hotkey Listener (pynput)

Captures a keyboard shortcut system-wide, even when the app isn't focused.

- **Default hotkey**: `Cmd+Shift+Space` (configurable)
- **Behavior**: Toggle — press once to start recording, press again to stop
- **Runs on**: Background thread, non-blocking
- **macOS requirement**: Accessibility permission must be granted

Library: `pynput` with `GlobalHotKeys` — the most reliable global hotkey solution on macOS.

### 3. Audio Recorder (sounddevice)

Captures microphone audio in real-time.

- **Sample rate**: 16,000 Hz (what Parakeet expects)
- **Channels**: 1 (mono)
- **Format**: float32 NumPy array
- **Behavior**: Streams audio into a buffer while recording is active. When recording stops, the buffer is passed to the transcriber.
- **Max duration safety**: 5-minute auto-stop to prevent accidental infinite recordings

Library: `sounddevice` — clean API, records directly to NumPy arrays, no PortAudio compilation headaches.

### 4. Transcription Engine (parakeet-mlx)

Runs NVIDIA's Parakeet model locally using Apple's MLX framework, optimized for M-series chips.

- **Model**: `mlx-community/parakeet-tdt-0.6b-v2` (English, best accuracy at 6.05% WER)
- **Alternative**: `mlx-community/parakeet-tdt-0.6b-v3` (25 languages, slightly larger)
- **First run**: Downloads model to `~/.cache/huggingface/` (~2.4 GB)
- **Subsequent runs**: Loads from cache, fast startup
- **Performance**: ~30x faster than Whisper on Apple Silicon. A 10-second recording transcribes in well under 1 second.

Library: `parakeet-mlx` — the Apple Silicon-native wrapper. This is NOT the NVIDIA NeMo toolkit (which has dependency issues on macOS). This is a clean reimplementation on MLX.

**Fallback option**: If parakeet-mlx has issues, we can swap in `faster-whisper` with zero architecture changes — same input (audio array), same output (text string).

### 5. Paste at Cursor (pbcopy + AppleScript)

Takes the transcribed text and pastes it wherever the cursor is.

- **Step 1**: Copy text to clipboard via `pbcopy` (macOS native)
- **Step 2**: Simulate `Cmd+V` via AppleScript/System Events
- **Why not pyautogui?**: AppleScript via `osascript` is more reliable on macOS and doesn't need its own separate accessibility permission
- **Clipboard preservation**: Optionally save/restore the clipboard so we don't clobber whatever was there before

```python
import subprocess

def paste_text(text):
    # Save current clipboard (optional)
    old_clipboard = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout

    # Copy new text
    subprocess.run(['pbcopy'], input=text.encode(), check=True)

    # Paste via Cmd+V
    subprocess.run([
        'osascript', '-e',
        'tell application "System Events" to keystroke "v" using command down'
    ])

    # Restore clipboard after a short delay (optional)
```

---

## Dependencies

```
# Core
parakeet-mlx>=0.5.0    # Local Parakeet STT on Apple Silicon
sounddevice>=0.4.6      # Microphone capture
numpy>=1.24.0           # Audio array handling
pynput>=1.7.6           # Global hotkey detection
rumps>=0.4.0            # macOS menu bar app

# Already on macOS (no install needed)
# - pbcopy/pbpaste (clipboard)
# - osascript (AppleScript for Cmd+V simulation)
```

Total pip install footprint: parakeet-mlx is the big one (~2.4 GB model download on first run). Everything else is tiny.

---

## Repository Structure

```
speech-to-text/
├── README.md                # Setup instructions, usage guide
├── requirements.txt         # Python dependencies
├── setup.sh                 # One-command install script
├── config.yaml              # User configuration (hotkey, model, etc.)
├── src/
│   ├── __init__.py
│   ├── app.py               # Main entry point — menu bar app
│   ├── hotkey.py             # Global hotkey listener
│   ├── recorder.py           # Audio recording
│   ├── transcriber.py        # Parakeet-MLX inference
│   └── paster.py             # Clipboard + paste at cursor
├── scripts/
│   ├── install.sh            # Full setup (venv, deps, permissions guide)
│   └── uninstall.sh          # Clean removal
└── tests/
    ├── test_recorder.py      # Test mic capture
    ├── test_transcriber.py   # Test model loading + inference
    └── test_paster.py        # Test clipboard + paste
```

---

## Configuration (config.yaml)

```yaml
# Hotkey to toggle recording (default: Cmd+Shift+Space)
hotkey: "<cmd>+<shift>+space"

# Parakeet model (v2 = English only, v3 = multilingual)
model: "mlx-community/parakeet-tdt-0.6b-v2"

# Max recording duration in seconds (safety limit)
max_duration: 300

# Audio settings
sample_rate: 16000

# Paste behavior
restore_clipboard: true   # Restore previous clipboard after paste
add_trailing_space: true   # Add a space after pasted text

# Feedback
sound_on_start: true       # Play a subtle sound when recording starts
sound_on_stop: true        # Play a subtle sound when recording stops
```

---

## Implementation Order

### Phase 1: Core Pipeline (get it working)

1. **transcriber.py** — Load Parakeet model, transcribe a WAV file. Prove the model works.
2. **recorder.py** — Record audio from mic into a NumPy array. Save as WAV to test.
3. **Wire recorder → transcriber** — Record audio, transcribe it, print the text.
4. **paster.py** — Take a string, paste it at cursor position.
5. **Wire full pipeline** — Record → transcribe → paste. Run from terminal.

### Phase 2: Hotkey + Menu Bar (make it usable)

6. **hotkey.py** — Listen for global hotkey, fire callback.
7. **app.py** — Menu bar icon with rumps. Wire hotkey → recorder → transcriber → paster.
8. **State management** — Toggle states (idle/recording/processing), update menu bar icon.
9. **Audio feedback** — Subtle start/stop sounds so you know it's working.

### Phase 3: Polish (make it nice)

10. **config.yaml** — Load user config, support custom hotkeys/models.
11. **setup.sh** — One-command install: create venv, install deps, download model, print permissions guide.
12. **Error handling** — Graceful failures (no mic permission, model not downloaded, etc.).
13. **README.md** — Clear setup and usage instructions.

---

## macOS Permissions Required

The app needs two macOS permissions to function:

### 1. Microphone Access
- **What**: Permission to use the microphone
- **When prompted**: First time the app tries to record
- **How to grant**: macOS will show a popup automatically. Click "Allow."
- **If missed**: System Settings → Privacy & Security → Microphone → enable for Terminal/Python

### 2. Accessibility Access
- **What**: Permission to detect global hotkeys and simulate keyboard input (Cmd+V paste)
- **When needed**: Before the app can detect hotkeys or paste text
- **How to grant**: System Settings → Privacy & Security → Accessibility → add Terminal (or the Python binary)
- **Pro tip**: If running from a virtual environment, you may need to add the venv's Python binary specifically

The setup script will print clear instructions for both of these.

---

## Fallback Strategy

If `parakeet-mlx` doesn't work on Grant's machine for any reason:

**Fallback 1: faster-whisper**
```python
# Drop-in replacement in transcriber.py
from faster_whisper import WhisperModel
model = WhisperModel("base", device="auto")
segments, _ = model.transcribe(audio_array)
text = " ".join(s.text for s in segments)
```
Same interface (audio in, text out). ~2-3x faster than stock Whisper.

**Fallback 2: whisper.cpp (via subprocess)**
```python
# Shell out to whisper.cpp binary
subprocess.run(["./whisper", "-m", "models/ggml-base.bin", "audio.wav"])
```
Fastest startup (<300ms), lowest memory usage.

---

## Testing Plan

### Unit Tests
- **test_recorder.py**: Record 3 seconds of audio, verify it produces a non-empty NumPy array at 16kHz
- **test_transcriber.py**: Feed a known WAV file to Parakeet, verify output contains expected words
- **test_paster.py**: Paste a known string, verify clipboard contents match

### Integration Test
- Run the full pipeline from terminal: speak a phrase → verify transcribed text appears in a text editor

### Manual Test Checklist
- [ ] Menu bar icon appears on launch
- [ ] Hotkey toggles recording on/off
- [ ] Icon changes state (idle → recording → processing → idle)
- [ ] Transcribed text appears at cursor in: Notes, VS Code, Chrome, Slack
- [ ] Audio feedback sounds play on start/stop
- [ ] 5-minute auto-stop works
- [ ] Config changes (hotkey, model) take effect after restart
- [ ] App works after reboot (no stale state)
- [ ] Clipboard is restored after paste (if enabled)

---

## What This Doesn't Do (Scope Limits)

- No LLM integration — this is purely speech → text, not a voice assistant
- No real-time streaming transcription (records a chunk, then transcribes). Could be added later.
- No wake word detection ("Hey computer..."). It's hotkey-only.
- No training or fine-tuning of the model
- macOS only (Parakeet-MLX requires Apple Silicon)

---

## Estimated Timeline

- Phase 1 (core pipeline): ~1 hour
- Phase 2 (hotkey + menu bar): ~1 hour
- Phase 3 (polish + setup): ~30 minutes
- Total: ~2.5 hours of build time

The model download (~2.4 GB) will take 2-10 minutes depending on internet speed, but that happens during setup, not during build.
