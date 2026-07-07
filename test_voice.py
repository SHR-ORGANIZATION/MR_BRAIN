"""Test voice feature directly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from voice import get_voice_engine

engine = get_voice_engine()
print("Voice available:", engine.is_voice_available())
print("TTS engine:", "ok" if engine.tts_engine else "none")
print("Recognizer:", "ok" if engine.recognizer else "none")

# Quick speak test
engine.speak("This is a voice test.")
print("Spoke test speech.")

# Quick listen test
engine.start_listening(
    on_result=lambda text: print("Heard:", text),
    on_error=lambda err: print("Voice error:", err),
)
print("Listening for up to 10 seconds...")