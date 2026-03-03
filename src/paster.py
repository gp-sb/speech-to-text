"""
Paste-at-cursor — copies transcribed text to clipboard and pastes it
wherever the cursor is, in any application.

Uses macOS-native pbcopy + AppleScript for maximum reliability.
Optionally preserves the previous clipboard contents.
"""

import subprocess
import time
import logging

logger = logging.getLogger(__name__)


def paste_text(text: str, restore_clipboard: bool = True, add_trailing_space: bool = True):
    """
    Paste text at the current cursor position in whatever app is focused.

    Args:
        text: The text to paste
        restore_clipboard: If True, saves and restores the previous clipboard contents
        add_trailing_space: If True, appends a space after the text
    """
    logger.debug(f"paste_text() called: text={repr(text[:50])}..., restore={restore_clipboard}")
    if not text or not text.strip():
        logger.warning("Empty text — nothing to paste")
        return

    text = text.strip()
    if add_trailing_space:
        text += " "

    old_clipboard = None

    try:
        # Save current clipboard contents
        if restore_clipboard:
            logger.debug("Saving current clipboard...")
            old_clipboard = _get_clipboard()
            logger.debug(f"Saved clipboard: {len(old_clipboard) if old_clipboard else 0} chars")

        # Copy transcribed text to clipboard
        logger.debug("Setting clipboard to transcribed text...")
        _set_clipboard(text)

        # Small delay to ensure clipboard is synced
        time.sleep(0.05)

        # Simulate Cmd+V via AppleScript
        logger.debug("Simulating Cmd+V paste...")
        _simulate_paste()

        logger.info(f"📋 Pasted {len(text)} characters at cursor")

    except Exception as e:
        logger.error(f"❌ Paste failed: {e}", exc_info=True)
        raise

    finally:
        # Restore previous clipboard after a delay
        # (need to wait for the paste to complete)
        if restore_clipboard and old_clipboard is not None:
            time.sleep(0.3)
            _set_clipboard(old_clipboard)
            logger.debug("Previous clipboard restored")


def _get_clipboard() -> str:
    """Get current clipboard contents via pbpaste."""
    try:
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _set_clipboard(text: str):
    """Set clipboard contents via pbcopy."""
    subprocess.run(
        ["pbcopy"],
        input=text.encode("utf-8"),
        check=True,
        timeout=2,
    )


def _simulate_paste():
    """Simulate Cmd+V keystroke via AppleScript."""
    subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "System Events" to keystroke "v" using command down',
        ],
        check=True,
        timeout=5,
    )
