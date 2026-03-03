"""Tests for the paster module."""

import unittest
from unittest.mock import patch, call


class TestPaster(unittest.TestCase):
    """Test clipboard and paste functions."""

    @patch("src.paster.subprocess")
    def test_set_clipboard(self, mock_subprocess):
        """_set_clipboard calls pbcopy with correct input."""
        from src.paster import _set_clipboard
        _set_clipboard("hello world")

        mock_subprocess.run.assert_called_once()
        args = mock_subprocess.run.call_args
        assert args[0][0] == ["pbcopy"]
        assert args[1]["input"] == b"hello world"

    @patch("src.paster.subprocess")
    def test_get_clipboard(self, mock_subprocess):
        """_get_clipboard calls pbpaste."""
        from src.paster import _get_clipboard

        mock_subprocess.run.return_value = unittest.mock.MagicMock(stdout="test content")
        result = _get_clipboard()

        assert result == "test content"
        args = mock_subprocess.run.call_args
        assert args[0][0] == ["pbpaste"]

    @patch("src.paster.subprocess")
    def test_simulate_paste(self, mock_subprocess):
        """_simulate_paste calls osascript with Cmd+V."""
        from src.paster import _simulate_paste
        _simulate_paste()

        args = mock_subprocess.run.call_args
        assert args[0][0][0] == "osascript"
        assert "keystroke" in args[0][0][2]
        assert "command down" in args[0][0][2]

    @patch("src.paster._simulate_paste")
    @patch("src.paster._set_clipboard")
    @patch("src.paster._get_clipboard", return_value="old clipboard")
    @patch("src.paster.time")
    def test_paste_text_full_flow(self, mock_time, mock_get, mock_set, mock_paste):
        """paste_text saves clipboard, sets new text, pastes, and restores."""
        from src.paster import paste_text
        paste_text("hello world", restore_clipboard=True, add_trailing_space=True)

        # Should get old clipboard
        mock_get.assert_called_once()

        # Should set new text (with trailing space) then restore old
        assert mock_set.call_count == 2
        first_set = mock_set.call_args_list[0]
        assert first_set[0][0] == "hello world "  # trailing space

        second_set = mock_set.call_args_list[1]
        assert second_set[0][0] == "old clipboard"

        # Should simulate paste
        mock_paste.assert_called_once()

    @patch("src.paster._simulate_paste")
    @patch("src.paster._set_clipboard")
    @patch("src.paster._get_clipboard")
    @patch("src.paster.time")
    def test_paste_text_no_restore(self, mock_time, mock_get, mock_set, mock_paste):
        """paste_text skips clipboard restore when disabled."""
        from src.paster import paste_text
        paste_text("hello", restore_clipboard=False)

        mock_get.assert_not_called()
        assert mock_set.call_count == 1  # Only one set, no restore

    @patch("src.paster.logger")
    def test_paste_empty_text_ignored(self, mock_logger):
        """paste_text does nothing for empty text."""
        from src.paster import paste_text
        paste_text("")
        paste_text("   ")
        assert mock_logger.warning.call_count == 2


if __name__ == "__main__":
    unittest.main()
