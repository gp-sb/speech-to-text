"""
Global hotkey listener — detects keyboard shortcuts system-wide.

Uses pynput for reliable macOS global hotkey detection.
Requires Accessibility permission in System Settings.
"""

import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    from pynput import keyboard
except ImportError:
    raise RuntimeError("pynput is required: pip install pynput")


# Map config-friendly key names to pynput key objects
_KEY_MAP = {
    "cmd": keyboard.Key.cmd,
    "command": keyboard.Key.cmd,
    "ctrl": keyboard.Key.ctrl,
    "control": keyboard.Key.ctrl,
    "alt": keyboard.Key.alt,
    "option": keyboard.Key.alt,
    "shift": keyboard.Key.shift,
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
    "esc": keyboard.Key.esc,
    "escape": keyboard.Key.esc,
    "f1": keyboard.Key.f1,
    "f2": keyboard.Key.f2,
    "f3": keyboard.Key.f3,
    "f4": keyboard.Key.f4,
    "f5": keyboard.Key.f5,
    "f6": keyboard.Key.f6,
    "f7": keyboard.Key.f7,
    "f8": keyboard.Key.f8,
    "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10,
    "f11": keyboard.Key.f11,
    "f12": keyboard.Key.f12,
}


def parse_hotkey_string(hotkey_str: str) -> str:
    """
    Convert a human-readable hotkey string to pynput format.

    Input examples:
        "cmd+shift+space"
        "ctrl+alt+r"
        "command+shift+s"

    Output:
        "<cmd>+<shift>+<space>"  (pynput GlobalHotKeys format)
    """
    parts = [p.strip().lower() for p in hotkey_str.split("+")]
    pynput_parts = []

    for part in parts:
        if part in _KEY_MAP:
            pynput_parts.append(f"<{part}>")
        elif len(part) == 1:
            # Single character key
            pynput_parts.append(part)
        else:
            # Try as-is (might be a pynput key name)
            pynput_parts.append(f"<{part}>")

    return "+".join(pynput_parts)


class HotkeyListener:
    """
    Listens for a global hotkey and fires a callback.

    Usage:
        def on_toggle():
            print("Hotkey pressed!")

        listener = HotkeyListener("cmd+shift+space", on_toggle)
        listener.start()
        # ... runs in background ...
        listener.stop()
    """

    def __init__(self, hotkey_str: str, callback: Callable):
        """
        Args:
            hotkey_str: Hotkey combo like "cmd+shift+space"
            callback: Function to call when hotkey is pressed
        """
        self.hotkey_str = hotkey_str
        self.callback = callback
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # Parse to pynput format
        self._pynput_hotkey = parse_hotkey_string(hotkey_str)
        logger.info(f"Hotkey configured: {hotkey_str} \u2192 {self._pynput_hotkey}")

    def start(self):
        """Start listening for the global hotkey in a background thread."""
        if self._running:
            logger.warning("Hotkey listener already running")
            return

        self._running = True

        self._listener = keyboard.GlobalHotKeys({
            self._pynput_hotkey: self._on_hotkey,
        })
        self._listener.daemon = True
        self._listener.start()

        logger.info(f"Hotkey listener started \u2014 press {self.hotkey_str} to toggle")

    def stop(self):
        """Stop the hotkey listener."""
        self._running = False

        if self._listener:
            self._listener.stop()
            self._listener = None

        logger.info("Hotkey listener stopped")

    def _on_hotkey(self):
        """Called when the hotkey combo is detected."""
        if self._running and self.callback:
            logger.debug(f"Hotkey {self.hotkey_str} triggered")
            try:
                self.callback()
            except Exception as e:
                logger.error(f"Hotkey callback error: {e}")
