"""
Voice Input/Output Module for AMAZON AI
Adds speech recognition (voice commands) and text-to-speech (voice responses) to the desktop assistant.
"""
import threading
import time
import platform
import shutil
import subprocess
import importlib
import tempfile

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    whisper = importlib.import_module("whisper")
except Exception:
    whisper = None


class VoiceEngine:
    """Handles voice input (speech-to-text) and voice output (text-to-speech)."""

    def __init__(self):
        self.recognizer = sr.Recognizer() if sr else None
        self.microphone = None
        self.microphone_name = None
        self.tts_engine = None
        self.tts_backend = None
        self.is_listening = False
        self.is_speaking = False
        self.voice_enabled = True
        self.listening_callback = None
        self.listening_callback_error = None
        self.speaking_callback = None
        self.language = "en-US"
        self.os_type = platform.system()
        self._state_lock = threading.RLock()
        self._lifecycle_lock = threading.RLock()
        self._listen_thread = None
        self._speak_thread_ref = None
        self._last_error_ts = 0.0
        self._last_transcript = ""
        self._last_transcript_ts = 0.0
        self._unknown_streak = 0
        self.recognition_backends = []
        self.whisper_model = None
        self.whisper_model_name = "tiny"
        self._whisper_failed = False
        self.listen_timeout = 4
        self.phrase_time_limit = 10
        self.sample_rate = 16000
        self.stt_notice = None

        if pyttsx3 and self.os_type != "Windows":
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 175)  # Slightly faster, more natural
                self.tts_engine.setProperty("volume", 1.0)  # Full volume
                
                os_type = self.os_type
                
                if os_type == "Darwin":
                    # macOS: prefer natural-sounding female voices
                    voices = self.tts_engine.getProperty('voices')
                    for voice in voices:
                        if any(v in voice.name.lower() for v in ['female', 'samantha', 'victoria', 'karen', 'moira', 'tessa']):
                            self.tts_engine.setProperty('voice', voice.id)
                            print(f"Selected macOS voice: {voice.name}")
                            break
                
                elif os_type == "Windows":
                    # Windows: prefer female voices (Zira, Hazel) over male (David)
                    voices = self.tts_engine.getProperty('voices')
                    
                    # First pass: look for female voices
                    female_keywords = ['zira', 'hazel', 'female', 'woman', 'aria', 'jenny', 'emma']
                    for voice in voices:
                        if any(v in voice.name.lower() for v in female_keywords):
                            self.tts_engine.setProperty('voice', voice.id)
                            print(f"Selected Windows voice (female): {voice.name}")
                            break
                    else:
                        # Second pass: any non-David voice
                        for voice in voices:
                            if 'david' not in voice.name.lower():
                                self.tts_engine.setProperty('voice', voice.id)
                                print(f"Selected Windows voice: {voice.name}")
                                break
                    
            except Exception as e:
                print(f"TTS init warning: {e}")
                self.tts_engine = None

        self.tts_backend = self._detect_tts_backend()
        self.recognition_backends = self._detect_recognition_backends()
        self._select_microphone()

    def set_language(self, lang):
        self.language = lang or "en-US"
        # Rebuild backend order when language changes
        self.recognition_backends = self._detect_recognition_backends()

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
        # Prefer physical/default input devices over virtual devices
        preferred_keywords = [
            "microphone array",
            "realtek",
            "frontmic",
            "array",
            "default",
            "built-in",
            "built in",
            "airpods",
            "headset",
            "usb",
        ]
        excluded_keywords = [
            "itop",
            "virtual",
            "monitor",
            "stereo mix",
            "loopback",
        ]
        preferred_indices = []
        fallback_indices = []
        for idx, name in enumerate(names):
            low = name.lower()
            if any(k in low for k in excluded_keywords):
                continue
            if any(k in low for k in preferred_keywords):
                preferred_indices.append(idx)
            elif "output" not in low:
                fallback_indices.append(idx)

        candidate_indices = preferred_indices + fallback_indices
        if 0 not in candidate_indices:
            candidate_indices.append(0)

        for chosen_index in candidate_indices:
            try:
                self.microphone = sr.Microphone(device_index=chosen_index)
                self.microphone_name = names[chosen_index]
                print(f"Selected microphone index {chosen_index}: {self.microphone_name}")
                return
            except Exception as e:
                print(f"Failed to open microphone index {chosen_index}: {e}")

        self.microphone = None
        self.microphone_name = None
        print("No usable microphone device could be opened.")

    def _detect_tts_backend(self):
        """Select the most stable TTS backend available for the current platform."""
        if self.os_type == "Darwin":
            if shutil.which("say"):
                return "say"
            if self.tts_engine is not None:
                return "pyttsx3"
            return None

        if self.os_type == "Windows":
            if pyttsx3 is not None:
                return "pyttsx3_windows"
            if shutil.which("powershell") or shutil.which("pwsh"):
                return "powershell"
            return None

        # Linux/other unix
        if shutil.which("espeak"):
            return "espeak"
        if shutil.which("spd-say"):
            return "spd-say"
        if self.tts_engine is not None:
            return "pyttsx3"
        return None

    def _detect_recognition_backends(self):
        """Detect STT backends in preferred order."""
        backends = []
        self.stt_notice = None
        if sr is None:
            self.stt_notice = "SpeechRecognition library is not installed."
            return backends

        lang = (self.language or "en-US").lower()
        prefers_swahili = lang.startswith("sw")

        # Prefer local/offline backends first for stability
        if whisper is not None:
            backends.append("whisper")
        elif prefers_swahili:
            self.stt_notice = "Offline Whisper backend not installed. Install openai-whisper for offline Swahili."

        # Offline sphinx fallback
        if hasattr(self.recognizer, "recognize_sphinx"):
            backends.append("sphinx")

        # Online Google as last fallback
        if hasattr(self.recognizer, "recognize_google"):
            backends.append("google")

        return backends

    def can_listen(self):
        """Return True when speech recognition input is usable."""
        return (
            sr is not None
            and self.microphone is not None
            and self.recognizer is not None
            and len(self.recognition_backends) > 0
        )

    def can_speak(self):
        """Return True when any TTS backend is available."""
        return self.tts_backend is not None

    def start_listening(self, on_result=None, on_error=None):
        """Start background listening thread."""
        with self._lifecycle_lock:
            if self.is_listening:
                return
            if not self.can_listen():
                self._select_microphone()
            if not self.can_listen():
                if on_error:
                    on_error("Microphone or speech recognition is not available.")
                return

            self.is_listening = True
            self.listening_callback = on_result
            self.listening_callback_error = on_error
            t = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread = t
            t.start()
        try:
            self._play_beep()
        except Exception:
            pass

    def stop_listening(self):
        """Stop listening."""
        with self._lifecycle_lock:
            self.is_listening = False

    def _play_beep(self):
        """Non-blocking, best-effort start-listening beep across platforms."""
        try:
            if self.os_type == "Darwin":
                subprocess.run(["afplay", "/System/Library/Sounds/Pop.aiff"], timeout=1, capture_output=True)
                return
            if self.os_type == "Windows":
                try:
                    import winsound  # type: ignore
                    winsound.MessageBeep()
                    return
                except Exception:
                    pass
            # Linux/other fallback terminal bell
            print("\a", end="", flush=True)
        except Exception:
            pass

    def _listen_loop(self):
        """Background listening loop using speech_recognition."""
        if not self.can_listen():
            err = "speech_recognition library not installed or microphone not available."
            print("VOICE ERROR:", err)
            if self.listening_callback_error:
                self.listening_callback_error(err)
            self.is_listening = False
            return

        print("Voice thread started")
        try:
            # Create a fresh microphone instance for this thread to avoid context manager conflicts
            try:
                chosen_index = None
                if self.microphone is not None:
                    chosen_index = self.microphone.device_index
                thread_mic = sr.Microphone(device_index=chosen_index)
            except Exception:
                thread_mic = self.microphone
            
            with thread_mic as source:
                print("Microphone opened, adjusting ambient noise...")
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.pause_threshold = 0.8
                self.recognizer.non_speaking_duration = 0.5
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                try:
                    self.sample_rate = int(getattr(source, "SAMPLE_RATE", 16000) or 16000)
                except Exception:
                    self.sample_rate = 16000
                print("Ambient noise calibration done. Listening...")
                speaking_stuck_count = 0
                timeout_count = 0
                while self.is_listening:
                    # Skip listening while speaking to avoid feedback loop
                    if self.is_speaking:
                        speaking_stuck_count += 1
                        # Safety: if is_speaking stuck for >30s (150 * 0.2s), force clear
                        if speaking_stuck_count > 150:
                            print("WARNING: is_speaking stuck, force clearing")
                            self.is_speaking = False
                            speaking_stuck_count = 0
                        time.sleep(0.2)
                        continue
                    speaking_stuck_count = 0
                    try:
                        print("Waiting for speech...")
                        audio = self.recognizer.listen(
                            source,
                            timeout=self.listen_timeout,
                            phrase_time_limit=self.phrase_time_limit,
                        )
                        print("Audio captured")
                        timeout_count = 0
                    except sr.WaitTimeoutError:
                        # expected while idle
                        timeout_count += 1
                        # Recalibrate occasionally to adapt to changing environment noise.
                        if timeout_count >= 12:
                            try:
                                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                            except Exception:
                                pass
                            timeout_count = 0
                        continue
                    # Double-check: if speaking started while we were listening, discard
                    if self.is_speaking:
                        continue
                    try:
                        print("Recognizing...")
                        text = self._recognize_audio(audio)
                        print("Recognized:", text)
                        if text:
                            self._unknown_streak = 0
                        if text and self._should_emit_transcript(text) and self.listening_callback:
                            self.listening_callback(text)
                    except sr.UnknownValueError:
                        # Normal in noisy environments; throttle user-facing errors.
                        self._unknown_streak += 1
                        # Do not surface a warning on first miss; transient misses are common.
                        if self._unknown_streak >= 2:
                            self._emit_error("Could not understand audio", throttle_sec=3.0)
                        continue
                    except sr.RequestError as e:
                        self._unknown_streak = 0
                        msg = f"Google recognition error: {e}"
                        print(msg)
                        self._emit_error(msg, throttle_sec=2.0)
                        # Try refreshing mic in case device got disconnected/reconnected
                        self._select_microphone()
                        time.sleep(0.5)
                    except Exception as e:
                        self._unknown_streak = 0
                        msg = f"Recognition unexpected error: {e}"
                        print("VOICE ERROR:", msg)
                        self._emit_error(msg, throttle_sec=2.0)
                        time.sleep(0.5)
        except Exception as e:
            msg = f"Microphone/open error: {e}"
            print("VOICE ERROR:", msg)
            self._emit_error(msg, throttle_sec=1.5)
        finally:
            print("Voice thread stopping")
            self.is_listening = False

    def _recognize_audio(self, audio):
        """Recognize speech using backend fallbacks."""
        last_err = None
        last_request_err = None
        had_unknown_value = False
        for backend in self.recognition_backends:
            try:
                if backend == "google":
                    return self.recognizer.recognize_google(audio, language=self.language)
                if backend == "whisper":
                    return self._recognize_whisper(audio)
                if backend == "sphinx":
                    return self.recognizer.recognize_sphinx(audio, language=self.language)
            except sr.UnknownValueError:
                # Could not decode speech on this backend; keep trying others.
                had_unknown_value = True
                continue
            except sr.RequestError as e:
                last_request_err = e
                continue
            except Exception as e:
                last_err = e
                continue

        # Prefer "could not understand" over network errors when any backend decoded but found no words.
        if had_unknown_value:
            raise sr.UnknownValueError()

        if last_request_err is not None:
            raise last_request_err

        if isinstance(last_err, sr.UnknownValueError):
            raise last_err
        if isinstance(last_err, sr.RequestError):
            raise last_err
        raise sr.UnknownValueError()

    def _ensure_whisper_model(self):
        """Lazy-load local Whisper model for offline STT."""
        if whisper is None:
            return False
        if self._whisper_failed:
            return False
        if self.whisper_model is not None:
            return True
        try:
            with self._state_lock:
                if self.whisper_model is None:
                    try:
                        self.whisper_model = whisper.load_model(self.whisper_model_name)
                    except Exception:
                        # Final fallback for low-memory machines
                        self.whisper_model_name = "base"
                        self.whisper_model = whisper.load_model(self.whisper_model_name)
            return True
        except Exception as e:
            self.stt_notice = f"Whisper model load failed: {e}"
            self._whisper_failed = True
            # Remove whisper from backend order after repeated load failure.
            self.recognition_backends = [b for b in self.recognition_backends if b != "whisper"]
            return False

    def _recognize_whisper(self, audio):
        """Offline recognition using local Whisper model."""
        if not self._ensure_whisper_model():
            raise sr.RequestError("Whisper model is not available")

        tmp_path = None
        try:
            wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(wav_bytes)
                tmp_path = tmp.name

            lang = (self.language or "en").split("-")[0].lower()
            result = self.whisper_model.transcribe(
                tmp_path,
                language=lang,
                task="transcribe",
                fp16=False,
            )
            text = (result.get("text") or "").strip()
            if not text:
                raise sr.UnknownValueError()
            return text
        except sr.UnknownValueError:
            raise
        except Exception as e:
            raise sr.RequestError(f"Whisper recognition error: {e}")
        finally:
            if tmp_path:
                try:
                    import os
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _emit_error(self, message, throttle_sec=1.0):
        """Emit errors to UI with rate limiting to avoid noisy UX."""
        if not self.listening_callback_error:
            return
        now = time.time()
        if (now - self._last_error_ts) < throttle_sec:
            return
        self._last_error_ts = now
        try:
            self.listening_callback_error(message)
        except Exception:
            pass

    def _should_emit_transcript(self, text, dedupe_window_sec=1.2):
        """Avoid duplicate transcript bursts from repeated recognition frames."""
        normalized = (text or "").strip().lower()
        if not normalized:
            return False
        now = time.time()
        if normalized == self._last_transcript and (now - self._last_transcript_ts) < dedupe_window_sec:
            return False
        self._last_transcript = normalized
        self._last_transcript_ts = now
        return True

    def get_diagnostics(self):
        """Return runtime diagnostics for UI and debugging."""
        return {
            "os": self.os_type,
            "can_listen": self.can_listen(),
            "can_speak": self.can_speak(),
            "mic_name": self.microphone_name,
            "tts_backend": self.tts_backend,
            "stt_backends": list(self.recognition_backends),
            "whisper_model": self.whisper_model_name if self.whisper_model is not None else None,
            "stt_notice": self.stt_notice,
            "is_listening": self.is_listening,
            "is_speaking": self.is_speaking,
        }

    def speak(self, text):
        """Speak text aloud using TTS."""
        if not self.voice_enabled:
            self.is_speaking = False
            return
        if not self.can_speak():
            self.is_speaking = False
            return
        if not text or not str(text).strip():
            return
        t = threading.Thread(target=self._speak_thread, args=(str(text),), daemon=True)
        self._speak_thread_ref = t
        t.start()

    def _speak_thread(self, text):
        """Speak in background thread — cross-platform safe."""
        try:
            self.is_speaking = True
            if self.speaking_callback:
                self.speaking_callback(True)
            spoken = False

            if self.tts_backend == "say":
                result = subprocess.run(["say", text], timeout=45, capture_output=True)
                spoken = result.returncode == 0

            elif self.tts_backend == "pyttsx3_windows":
                spoken = self._speak_windows_pyttsx3(text)
                if not spoken:
                    spoken = self._speak_windows_powershell(text)

            elif self.tts_backend == "powershell":
                spoken = self._speak_windows_powershell(text)

            elif self.tts_backend == "espeak":
                result = subprocess.run(["espeak", text], timeout=45, capture_output=True)
                spoken = result.returncode == 0
                if not spoken:
                    spoken = self._speak_with_pyttsx3(text)

            elif self.tts_backend == "spd-say":
                result = subprocess.run(["spd-say", text], timeout=45, capture_output=True)
                spoken = result.returncode == 0
                if not spoken:
                    spoken = self._speak_with_pyttsx3(text)

            elif self.tts_backend == "pyttsx3":
                spoken = self._speak_with_pyttsx3(text)

            if not spoken:
                print("TTS speak warning: no backend succeeded")
        
        except Exception as e:
            print(f"TTS speak error: {e}")
        finally:
            self.is_speaking = False
            if self.speaking_callback:
                self.speaking_callback(False)

    def _speak_with_pyttsx3(self, text):
        """Speak with shared pyttsx3 engine (non-Windows/fallback path)."""
        if self.tts_engine is None:
            return False
        try:
            with self._state_lock:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            return True
        except Exception as e:
            print(f"pyttsx3 fallback error: {e}")
            return False

    def _speak_windows_pyttsx3(self, text):
        """Speak with per-thread Windows SAPI5 engine."""
        if pyttsx3 is None:
            return False
        com_init = False
        pythoncom = None
        try:
            try:
                import pythoncom  # type: ignore
                pythoncom.CoInitialize()
                com_init = True
            except ImportError:
                pass

            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            engine.setProperty("volume", 1.0)
            try:
                voices = engine.getProperty('voices')
                female_keywords = ['zira', 'hazel', 'female', 'woman', 'aria', 'jenny', 'emma']
                for voice in voices:
                    if any(v in voice.name.lower() for v in female_keywords):
                        engine.setProperty('voice', voice.id)
                        break
                else:
                    for voice in voices:
                        if 'david' not in voice.name.lower():
                            engine.setProperty('voice', voice.id)
                            break
            except Exception:
                pass

            engine.say(text)
            engine.runAndWait()
            engine.stop()
            return True
        except Exception as win_err:
            print(f"Windows pyttsx3 error: {win_err}")
            return False
        finally:
            if com_init and pythoncom is not None:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

    def _speak_windows_powershell(self, text):
        """Windows fallback TTS via PowerShell System.Speech."""
        shell = shutil.which("powershell") or shutil.which("pwsh")
        if not shell:
            return False
        escaped = text.replace("'", "''")
        cmd = (
            "Add-Type -AssemblyName System.Speech; "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Speak('{escaped}')"
        )
        try:
            result = subprocess.run(
                [shell, "-NoProfile", "-Command", cmd],
                timeout=45,
                capture_output=True,
            )
            return result.returncode == 0
        except Exception as e:
            print(f"PowerShell TTS error: {e}")
            return False

    def stop_speaking(self):
        """Stop current speech — cross-platform."""
        try:
            if self.os_type == "Darwin":
                subprocess.run(["killall", "say"], capture_output=True, timeout=2)
            elif self.os_type == "Windows":
                # On Windows, the thread-local engine can't be stopped from outside.
                # Just reset state — the engine will be garbage collected.
                pass
            else:
                # Linux: kill espeak
                subprocess.run(["killall", "espeak"], capture_output=True, timeout=2)
                subprocess.run(["killall", "spd-say"], capture_output=True, timeout=2)
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
        return self.can_listen() or self.can_speak()


# Singleton voice engine
_voice_engine = None


def get_voice_engine():
    """Get or create the global voice engine."""
    global _voice_engine
    if _voice_engine is None:
        _voice_engine = VoiceEngine()
    return _voice_engine