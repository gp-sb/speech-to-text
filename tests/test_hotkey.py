"""Tests for the hotkey listener module."""

import sys
import unittest
from unittest.mock import MagicMock

# conftest.py already mocked pynput in sys.modules


class TestHotkeyParsing(unittest.TestCase):
    """Test hotkey string parsing."""

    def test_parse_cmd_shift_space(self):
        from src.hotkey import parse_hotkey_string
        result = parse_hotkey_string("cmd+shift+space")
        assert result == "<cmd>+<shift>+<space>"

    def test_parse_ctrl_alt_r(self):
        from src.hotkey import parse_hotkey_string
        result = parse_hotkey_string("ctrl+alt+r")
        assert result == "<ctrl>+<alt>+r"

    def test_parse_command_alias(self):
        from src.hotkey import parse_hotkey_string
        result = parse_hotkey_string("command+shift+space")
        assert result == "<command>+<shift>+<space>"

    def test_parse_option_alias(self):
        from src.hotkey import parse_hotkey_string
        result = parse_hotkey_string("cmd+option+s")
        assert result == "<cmd>+<option>+s"

    def test_parse_function_keys(self):
        from src.hotkey import parse_hotkey_string
        result = parse_hotkey_string("f5")
        assert result == "<f5>"

    def test_parse_case_insensitive(self):
        from src.hotkey import parse_hotkey_string
        result = parse_hotkey_string("CMD+SHIFT+SPACE")
        assert result == "<cmd>+<shift>+<space>"

    def test_parse_with_spaces(self):
        from src.hotkey import parse_hotkey_string
        result = parse_hotkey_string("cmd + shift + space")
        assert result == "<cmd>+<shift>+<space>"


class TestHotkeyListener(unittest.TestCase):
    """Test the HotkeyListener class."""

    def test_init(self):
        from src.hotkey import HotkeyListener
        callback = MagicMock()
        listener = HotkeyListener("cmd+shift+space", callback)
        assert listener.hotkey_str == "cmd+shift+space"
        assert listener.callback is callback

    def test_start_creates_global_hotkeys(self):
        from src.hotkey import HotkeyListener, keyboard

        mock_gh = MagicMock()
        keyboard.GlobalHotKeys.return_value = mock_gh

        callback = MagicMock()
        listener = HotkeyListener("cmd+shift+space", callback)
        listener.start()

        keyboard.GlobalHotKeys.assert_called()
        mock_gh.start.assert_called_once()
        listener.stop()

    def test_stop_cleans_up(self):
        from src.hotkey import HotkeyListener, keyboard

        mock_gh = MagicMock()
        keyboard.GlobalHotKeys.return_value = mock_gh

        callback = MagicMock()
        listener = HotkeyListener("cmd+shift+space", callback)
        listener.start()
        listener.stop()

        mock_gh.stop.assert_called_once()

    def test_callback_fires_on_hotkey(self):
        from src.hotkey import HotkeyListener

        callback = MagicMock()
        listener = HotkeyListener("cmd+shift+space", callback)
        listener._running = True

        listener._on_hotkey()
        callback.assert_called_once()

    def test_callback_not_fired_when_stopped(self):
        from src.hotkey import HotkeyListener

        callback = MagicMock()
        listener = HotkeyListener("cmd+shift+space", callback)
        listener._running = False

        listener._on_hotkey()
        callback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
