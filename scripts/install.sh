#!/bin/bash
# Speech-to-Text — Install Script
# ================================
# Run this once to set up everything.

set -e

echo "========================================="
echo "  Speech-to-Text Installer"
echo "========================================="
echo ""

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check for Python 3.10+
echo "Checking Python version..."
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "❌ Python not found. Install Python 3.10+ from https://python.org"
    exit 1
fi

PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    echo "❌ Python $PY_VERSION found, but 3.10+ is required."
    echo "   Install from https://python.org"
    exit 1
fi
echo "✅ Python $PY_VERSION"

# Check for Apple Silicon
echo ""
echo "Checking hardware..."
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    echo "✅ Apple Silicon detected"
else
    echo "⚠️  Intel Mac detected. parakeet-mlx requires Apple Silicon (M1/M2/M3/M4)."
    echo "   You can still use the faster-whisper fallback."
    echo "   Uncomment 'faster-whisper' in requirements.txt and comment out 'parakeet-mlx'."
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo "✅ Dependencies installed"

# Pre-download the model
echo ""
echo "Pre-downloading Parakeet model (~2.4 GB)..."
echo "(This only happens once — the model is cached locally after download)"
python -c "
from parakeet_mlx import from_pretrained
model = from_pretrained('mlx-community/parakeet-tdt-0.6b-v2')
print('Model downloaded and cached successfully!')
" 2>&1 || {
    echo "⚠️  Model pre-download failed. It will download on first use instead."
    echo "   If parakeet-mlx failed to install, try the faster-whisper fallback."
}

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "⚠️  IMPORTANT: macOS Permissions Required"
echo "  ─────────────────────────────────────────"
echo ""
echo "  1. ACCESSIBILITY (for hotkeys + paste):"
echo "     System Settings → Privacy & Security → Accessibility"
echo "     → Add Terminal (or your terminal app)"
echo ""
echo "  2. MICROPHONE (for audio recording):"
echo "     macOS will prompt you automatically on first run."
echo "     Just click 'Allow' when asked."
echo ""
echo "  To run the app:"
echo "    source venv/bin/activate"
echo "    python -m src.app"
echo ""
echo "  Or in terminal mode (no menu bar):"
echo "    python -m src.app --terminal"
echo ""
echo "  Default hotkey: Cmd+Shift+Space"
echo "  Edit config.yaml to change settings."
echo ""
