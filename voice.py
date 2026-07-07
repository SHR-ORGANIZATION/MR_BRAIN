"""
Voice Input/Output Module for AMAZON AI
Adds speech recognition (voice commands) and text-to-speech (voice responses) to the desktop assistant.
"""
import threading
import queue
import time
from pathlib import Path

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None


class VoiceEngine:
    """Handles voice input (speech-to-text) and voice output (text-to-speech)."""

    def __init__(self):
        self.recognizer = sr.Recognizer() if sr else None
        self.microphone = None
        self.microphone_name = None
        self.tts_engine = None
        self.is_listening = False
        self.is_speaking = False
        self.voice_enabled = True
        self.listening_callback = None
        self.listening_callback_error = None
        self.speaking_callback = None
        self.language = "en-US"

        if pyttsx3:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 160)
                self.tts_engine.setProperty("volume", 0.9)
            except Exception:
                self.tts_engine = None

        self._select_microphone()

    def set_language(self, lang):
        self.language = lang or "en-US"

    def _select_microphone(self):
        if not sr:
            return
        try:
            names = sr.Microphone.list_microphone_names()
        except Exception as e:
            print("Mic enumeration failed:", e)
            return
        print("Microphones detected:", len(names))
        if not names:
            print("No microphone available.")
            return
        # Prefer realtek microphone array over virtual devices
        preferred_keywords = [
            "microphone array",
            "realtek",
            "frontmic",
            "array",
            "airpods",
            "headset",
        ]
        excluded_keywords = [
            "itop",
            "virtual",
        ]
        chosen_index = None
        for idx, name in enumerate(names):
            low = name.lower()
            if any(k in low for k in preferred_keywords) and not any(k in low for k in excluded_keywords):
                chosen_index = idx
                break
        if chosen_index is None:
            # fallback: first input-capable device
            for idx, name in enumerate(names):
                if "output" not in name.lower():
                    chosen_index = idx
                    break
        if chosen_index is None:
            chosen_index = 0
        try:
            self.microphone = sr.Microphone(device_index=chosen_index)
            self.microphone_name = names[chosen_index]
            print(f"Selected microphone index {chosen_index}: {self.microphone_name}")
        except Exception as e:
            print(f"Failed to open microphone index {chosen_index}: {e}")

    def start_listening(self, on_result=None, on_error=None):
        """Start background listening thread."""
        if self.is_listening:
            return
        self.is_listening = True
        self.listening_callback = on_result
        self.listening_callback_error = on_error
        t = threading.Thread(target=self._listen_loop, daemon=True)
        t.start()
        try:
            self._play_beep()
        except Exception:
            pass

    def stop_listening(self):
        """Stop listening."""
        self.is_listening = False
        try:
            if self._mic_active and hasattr(self, '_mic_source'):
                pass
        except Exception:
            pass

    def _listen_loop(self):
        """Background listening loop using speech_recognition."""
        if not sr or not self.microphone:
            err = "speech_recognition library not installed or microphone not available."
            print("VOICE ERROR:", err)
            if self.listening_callback_error:
                self.listening_callback_error(err)
            self.is_listening = False
            return

        print("Voice thread started")
        try:
            with self.microphone as source:
                print("Microphone opened, adjusting ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Ambient noise calibration done. Listening...")
                while self.is_listening:
                    try:
                        print("Waiting for speech...")
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=8)
                        print("Audio captured")
                    except sr.WaitTimeoutError:
                        print("Listen timeout: no speech detected")
                        continue
                    try:
                        print("Recognizing...")
                        text = self.recognizer.recognize_google(audio, language=self.language)
                        print("Recognized:", text)
                        if text and self.listening_callback:
                            self.listening_callback(text)
                    except sr.UnknownValueError:
                        print("Could not understand audio (UnknownValueError)")
                        if self.listening_callback_error:
                            self.listening_callback_error("Could not understand audio")
                        continue
                    except sr.RequestError as e:
                        msg = f"Google recognition error: {e}"
                        print(msg)
                        if self.listening_callback_error:
                            self.listening_callback_error(msg)
                        time.sleep(0.5)
                    except Exception as e:
                        msg = f"Recognition unexpected error: {e}"
                        print("VOICE ERROR:", msg)
                        if self.listening_callback_error:
                            self.listening_callback_error(msg)
                        time.sleep(0.5)
        except Exception as e:
            msg = f"Microphone/open error: {e}"
            print("VOICE ERROR:", msg)
            if self.listening_callback_error:
                self.listening_callback_error(msg)
        finally:
            print("Voice thread stopping")
            self.is_listening = False

    def speak(self, text):
        """Speak text aloud using TTS."""
        if not self.voice_enabled:
            return
        if not self.tts_engine:
            return
        threading.Thread(target=self._speak_thread, args=(text,), daemon=True).start()

    def _speak_thread(self, text):
        """Speak in background thread."""
        try:
            self.is_speaking = True
            if self.speaking_callback:
                self.speaking_callback(True)
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception:
            pass
        finally:
            self.is_speaking = False
            if self.speaking_callback:
                self.speaking_callback(False)

    def stop_speaking(self):
        """Stop current speech."""
        try:
            if self.tts_engine:
                self.tts_engine.stop()
        except Exception:
            pass
        self.is_speaking = False

    def set_voice_enabled(self, enabled):
        """Enable or disable voice output."""
        self.voice_enabled = enabled

    def is_voice_available(self):
        """Check if voice libraries are installed."""
        return pyttsx3 is not None and sr is not None


# Singleton voice engine
_voice_engine = None


def get_voice_engine():
    """Get or create the global voice engine."""
    global _voice_engine
    if _voice_engine is None:
        _voice_engine = VoiceEngine()
    return _voice_engine