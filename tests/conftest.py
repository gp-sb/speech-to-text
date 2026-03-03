"""
Pytest configuration — mock platform-specific modules.

pynput and sounddevice require macOS/PortAudio/X11 at import time,
so we mock them before any test modules import our source code.
"""

import sys
from unittest.mock import MagicMock

# Mock sounddevice and its PortAudio dependency
mock_sd = MagicMock()
mock_sd.InputStream = MagicMock()
mock_sd.query_devices = MagicMock(return_value=[])
mock_sd.default = MagicMock()
mock_sd.default.device = (0, 0)
sys.modules["sounddevice"] = mock_sd
sys.modules["_sounddevice"] = MagicMock()

# Mock pynput and its keyboard submodule
mock_pynput = MagicMock()
mock_keyboard = MagicMock()
mock_pynput.keyboard = mock_keyboard

# Create mock Key enum
mock_key = MagicMock()
mock_key.cmd = "cmd"
mock_key.ctrl = "ctrl"
mock_key.alt = "alt"
mock_key.shift = "shift"
mock_key.space = "space"
mock_key.tab = "tab"
mock_key.esc = "esc"
mock_key.f1 = "f1"
mock_key.f2 = "f2"
mock_key.f3 = "f3"
mock_key.f4 = "f4"
mock_key.f5 = "f5"
mock_key.f6 = "f6"
mock_key.f7 = "f7"
mock_key.f8 = "f8"
mock_key.f9 = "f9"
mock_key.f10 = "f10"
mock_key.f11 = "f11"
mock_key.f12 = "f12"
mock_keyboard.Key = mock_key
mock_keyboard.GlobalHotKeys = MagicMock()
mock_keyboard.Controller = MagicMock()

sys.modules["pynput"] = mock_pynput
sys.modules["pynput.keyboard"] = mock_keyboard

# Mock rumps (macOS menu bar)
sys.modules["rumps"] = MagicMock()
