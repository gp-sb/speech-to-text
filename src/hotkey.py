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

    Uses pynput.keyboard.Listener (not GlobalHotKeys) for better
    compatibility with rumps/AppKit event loops.

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
        self._listener: Optional[keyboard.Listener] = None
        self._running = False
        self._pressed_keys: set = set()
        self._hotkey_active = False  # Prevent repeated triggers while held

        # Parse hotkey into required keys
        self._required_keys = self._parse_hotkey(hotkey_str)
        logger.info(f"Hotkey configured: {hotkey_str} → {self._required_keys}")

    def _parse_hotkey(self, hotkey_str: str) -> set:
        """Parse hotkey string into a set of pynput key objects."""
        parts = [p.strip().lower() for p in hotkey_str.split("+")]
        keys = set()
        for part in parts:
            if part in _KEY_MAP:
                keys.add(_KEY_MAP[part])
            elif len(part) == 1:
                keys.add(keyboard.KeyCode.from_char(part))
            else:
                # Try as pynput key name
                try:
                    keys.add(getattr(keyboard.Key, part))
                except AttributeError:
                    logger.warning(f"Unknown key: {part}")
        return keys

    def start(self):
        """Start listening for the global hotkey in a background thread."""
        if self._running:
            logger.warning("Hotkey listener already running")
            return

        self._running = True
        self._pressed_keys = set()

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

        logger.info(f"Hotkey listener started — press {self.hotkey_str} to toggle")

    def stop(self):
        """Stop the hotkey listener."""
        self._running = False

        if self._listener:
            self._listener.stop()
            self._listener = None

        logger.info("Hotkey listener stopped")

    def _normalize_key(self, key):
        """Normalize a key for comparison."""
        # Handle special cases for modifier keys
        if hasattr(key, 'vk'):
            # Map left/right variants to generic modifier
            if key.vk in (54, 55):  # Left/Right Cmd
                return keyboard.Key.cmd
            if key.vk in (56, 60):  # Left/Right Shift
                return keyboard.Key.shift
            if key.vk in (58, 61):  # Left/Right Alt/Option
                return keyboard.Key.alt
            if key.vk in (59, 62):  # Left/Right Ctrl
                return keyboard.Key.ctrl
        return key

    def _on_press(self, key):
        """Track key presses and check for hotkey combo."""
        if not self._running:
            return

        normalized = self._normalize_key(key)
        self._pressed_keys.add(normalized)

        # Check if all required keys are pressed
        if self._required_keys.issubset(self._pressed_keys):
            if not self._hotkey_active:
                self._hotkey_active = True
                self._trigger_callback()

    def _on_release(self, key):
        """Track key releases."""
        if not self._running:
            return

        normalized = self._normalize_key(key)
        self._pressed_keys.discard(normalized)

        # Reset hotkey active state when any required key is released
        if normalized in self._required_keys:
            self._hotkey_active = False

    def _trigger_callback(self):
        """Called when the hotkey combo is detected."""
        logger.info(f"🎯 HOTKEY DETECTED: {self.hotkey_str}")
        if self.callback:
            logger.debug("Calling registered callback...")
            try:
                self.callback()
                logger.debug("Callback completed successfully")
            except Exception as e:
                logger.error(f"Hotkey callback error: {e}", exc_info=True)
