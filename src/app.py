"""
Main application — macOS menu bar app that ties everything together.

Sits in the menu bar, listens for a hotkey, records audio, transcribes
with Parakeet, and pastes the result at the cursor.
"""

import os
import sys
import threading
import logging
import yaml

logger = logging.getLogger(__name__)

# Determine paths
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(APP_DIR, "config.yaml")
DEFAULT_CONFIG = {
    "hotkey": "cmd+shift+space",
    "model": "mlx-community/parakeet-tdt-0.6b-v2",
    "max_duration": 300,
    "sample_rate": 16000,
    "restore_clipboard": True,
    "add_trailing_space": True,
    "sound_on_start": True,
    "sound_on_stop": True,
}


def load_config() -> dict:
    """Load config from config.yaml, falling back to defaults."""
    config = DEFAULT_CONFIG.copy()

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                user_config = yaml.safe_load(f) or {}
            config.update(user_config)
            logger.info(f"Config loaded from {CONFIG_PATH}")
        except Exception as e:
            logger.warning(f"Failed to load config: {e} — using defaults")
    else:
        logger.info("No config.yaml found — using defaults")

    return config


def play_sound(sound_type: str):
    """Play a subtle system sound for feedback."""
    import subprocess

    sounds = {
        "start": "/System/Library/Sounds/Pop.aiff",
        "stop": "/System/Library/Sounds/Blow.aiff",
        "error": "/System/Library/Sounds/Basso.aiff",
    }

    sound_path = sounds.get(sound_type)
    if sound_path and os.path.exists(sound_path):
        try:
            subprocess.Popen(
                ["afplay", sound_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass  # Not critical if sound fails


class SpeechToTextApp:
    """
    Main application controller.

    Manages the recording toggle state and coordinates between
    hotkey listener, audio recorder, transcriber, and paster.
    """

    def __init__(self, config: dict = None):
        self.config = config or load_config()
        self.is_recording = False
        self._lock = threading.Lock()
        self._model_loaded = False

        # Import components
        from .recorder import Recorder
        from .hotkey import HotkeyListener

        # Initialize recorder
        self.recorder = Recorder(
            sample_rate=self.config["sample_rate"],
            max_duration=self.config["max_duration"],
        )

        # Initialize hotkey listener
        self.hotkey_listener = HotkeyListener(
            hotkey_str=self.config["hotkey"],
            callback=self.toggle,
        )

    def _ensure_model_loaded(self):
        """Load the transcription model if not already loaded."""
        if not self._model_loaded:
            from .transcriber import load_model
            load_model(self.config.get("model"))
            self._model_loaded = True

    def toggle(self):
        """Toggle recording on/off. Called by the hotkey listener."""
        with self._lock:
            if self.is_recording:
                self._stop_recording()
            else:
                self._start_recording()

    def _start_recording(self):
        """Start recording audio."""
        self.is_recording = True
        logger.info("🔴 Recording started")

        if self.config.get("sound_on_start"):
            play_sound("start")

        self.recorder.start()

        # Update menu bar if available
        if hasattr(self, "_menu_bar_app") and self._menu_bar_app:
            self._menu_bar_app.title = "🔴"

    def _stop_recording(self):
        """Stop recording, transcribe, and paste."""
        self.is_recording = False

        if self.config.get("sound_on_stop"):
            play_sound("stop")

        # Update menu bar
        if hasattr(self, "_menu_bar_app") and self._menu_bar_app:
            self._menu_bar_app.title = "⏳"

        logger.info("⏳ Processing...")

        # Get the recorded audio
        audio = self.recorder.stop()

        if audio.size == 0:
            logger.warning("No audio captured")
            if hasattr(self, "_menu_bar_app") and self._menu_bar_app:
                self._menu_bar_app.title = "🎤"
            return

        # Transcribe in a background thread to not block the hotkey listener
        thread = threading.Thread(target=self._transcribe_and_paste, args=(audio,))
        thread.daemon = True
        thread.start()

    def _transcribe_and_paste(self, audio):
        """Transcribe audio and paste result at cursor."""
        try:
            # Ensure model is loaded
            self._ensure_model_loaded()

            # Transcribe
            from .transcriber import transcribe
            text = transcribe(audio, sample_rate=self.config["sample_rate"])

            if text and text.strip():
                logger.info(f"Transcribed: {text[:80]}{'...' if len(text) > 80 else ''}")

                # Paste at cursor
                from .paster import paste_text
                paste_text(
                    text,
                    restore_clipboard=self.config.get("restore_clipboard", True),
                    add_trailing_space=self.config.get("add_trailing_space", True),
                )
            else:
                logger.warning("Transcription returned empty text")
                play_sound("error")

        except Exception as e:
            logger.error(f"Transcription/paste failed: {e}")
            play_sound("error")

        finally:
            # Reset menu bar icon
            if hasattr(self, "_menu_bar_app") and self._menu_bar_app:
                self._menu_bar_app.title = "🎤"

    def run_menu_bar(self):
        """Run as a macOS menu bar app using rumps."""
        try:
            import rumps
        except ImportError:
            logger.error(
                "rumps is required for menu bar mode: pip install rumps\n"
                "Or run in terminal mode: python -m src.app --terminal"
            )
            sys.exit(1)

        class MenuBarApp(rumps.App):
            def __init__(app_self):
                super().__init__("🎤", quit_button=None)
                app_self.menu = [
                    rumps.MenuItem(
                        f"Toggle: {self.config['hotkey']}",
                        callback=lambda _: self.toggle(),
                    ),
                    None,  # Separator
                    rumps.MenuItem("Quit", callback=lambda _: rumps.quit_application()),
                ]

        self._menu_bar_app = MenuBarApp()

        # Pre-load model in background so first transcription is fast
        preload_thread = threading.Thread(target=self._ensure_model_loaded)
        preload_thread.daemon = True
        preload_thread.start()

        # Start hotkey listener
        self.hotkey_listener.start()

        logger.info(f"Speech-to-text ready — press {self.config['hotkey']} to toggle recording")

        # Run the menu bar app (blocks)
        self._menu_bar_app.run()

    def run_terminal(self):
        """Run in terminal mode (no menu bar). Useful for testing."""
        print(f"Speech-to-text ready — press {self.config['hotkey']} to toggle recording")
        print("Press Ctrl+C to quit\n")

        # Pre-load model
        print("Loading model (first run downloads ~2.4 GB)...")
        self._ensure_model_loaded()
        print("Model loaded!\n")

        # Start hotkey listener
        self.hotkey_listener.start()

        try:
            # Keep the main thread alive
            import signal
            signal.pause()
        except (KeyboardInterrupt, SystemExit):
            print("\nShutting down...")
            self.hotkey_listener.stop()


def main():
    """Entry point."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    config = load_config()
    app = SpeechToTextApp(config)

    # Check for --terminal flag
    if "--terminal" in sys.argv:
        app.run_terminal()
    else:
        app.run_menu_bar()


if __name__ == "__main__":
    main()
