#!/bin/bash
# Speech-to-Text — Uninstall Script
# ===================================
# Removes the virtual environment and cached model.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Speech-to-Text Uninstaller"
echo "=========================="
echo ""

# Remove virtual environment
if [ -d "venv" ]; then
    echo "Removing virtual environment..."
    rm -rf venv
    echo "✅ Virtual environment removed"
else
    echo "No virtual environment found"
fi

# Ask about cached model
echo ""
echo "The Parakeet model is cached at: ~/.cache/huggingface/"
echo "This is shared with other HuggingFace models you may have."
read -p "Remove cached Parakeet model? (y/N): " REMOVE_MODEL

if [ "$REMOVE_MODEL" = "y" ] || [ "$REMOVE_MODEL" = "Y" ]; then
    # Remove only the parakeet model, not all HF cache
    find ~/.cache/huggingface/hub -name "*parakeet*" -type d -exec rm -rf {} + 2>/dev/null || true
    echo "✅ Cached model removed"
else
    echo "Cached model kept"
fi

echo ""
echo "Done. The source code is still here — delete this folder to fully remove."
