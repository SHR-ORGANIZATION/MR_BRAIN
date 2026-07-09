"""
Voice UI Integration Module for AMAZON AI
Adds microphone button, voice status indicators, and voice-controlled command execution.
"""
import threading
from voice import get_voice_engine


class VoiceUIController:
    """Manages voice input/output integration with the main UI."""

    def __init__(self, app_instance):
        self.app = app_instance
        self.voice_engine = get_voice_engine()
        self.is_listening = False
        self.voice_button = None
        self.status_label = None

    def initialize(self):
        """Add voice controls to the UI."""
        try:
            self._add_voice_button()
            self._add_voice_status()
            if self.voice_engine.is_voice_available():
                print("Voice module loaded successfully.")
                self._show_status("Voice ready")
            else:
                print("Voice module unavailable (missing libraries).")
                self._show_status("Voice unavailable")
        except Exception as e:
            print(f"Voice UI initialization failed: {e}")

    def _ensure_listening_state_cleared(self):
        """Ensure listening state is fully cleared."""
        self.is_listening = False
        try:
            self.voice_engine.stop_listening()
        except Exception:
            pass
        self._update_button_state()
        self._show_status("")

    def _add_voice_button(self):
        """Add microphone button to the header."""
        try:
            from customtkinter import CTkButton
            from ui.main import FONT_SMALL_BTN, SIDEBAR_MUTED

            self.voice_button = CTkButton(
                self.app.header_right,
                text="🎤",
                width=36,
                height=36,
                font=("Segoe UI", 16),
                fg_color="transparent",
                hover_color="#f0f0f0",
                text_color=SIDEBAR_MUTED,
                corner_radius=8,
                command=self._toggle_listening
            )
            self.voice_button.pack(side="left", padx=(0, 4))
        except Exception as e:
            print(f"Could not add voice button: {e}")

    def _add_voice_status(self):
        """Add voice status label (listening / speaking)."""
        try:
            from customtkinter import CTkLabel
            from ui.main import FONT_HINT, TEXT_SECONDARY

            self.status_label = CTkLabel(
                self.app.header_right,
                text="",
                font=FONT_HINT,
                text_color=TEXT_SECONDARY
            )
            self.status_label.pack(side="left", padx=(0, 8))
        except Exception as e:
            print(f"Could not add voice status: {e}")

    def _toggle_listening(self):
        """Toggle voice listening on/off."""
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()

    def start_listening(self):
        """Begin voice listening."""
        if self.is_listening:
            return
        if not self.voice_engine.is_voice_available():
            self._show_status("Voice not available")
            return

        # Cancel any previous timeout if present
        try:
            if hasattr(self, '_timeout_id') and self._timeout_id:
                self.app.app.after_cancel(self._timeout_id)
        except Exception:
            pass

        self.is_listening = True
        self._update_button_state()
        self._show_status("Listening...")

        root = self.app.app if hasattr(self.app, 'app') else self.app
        def on_result(text):
            try:
                root.after(0, lambda: self._handle_voice_result(text))
            except Exception:
                self._handle_voice_result(text)

        def on_error(error):
            try:
                root.after(0, lambda: self._handle_voice_error(error))
            except Exception:
                self._handle_voice_error(error)

        self.voice_engine.start_listening(on_result=on_result, on_error=on_error)
        # Safety timeout: stop listening automatically after 15 seconds
        self._timeout_id = root.after(15000, lambda: self._handle_voice_timeout())

    def stop_listening(self):
        """Stop voice listening."""
        self.is_listening = False
        self.voice_engine.stop_listening()
        self._update_button_state()
        self._show_status("")

    def _handle_voice_result(self, text):
        """Process recognized speech."""
        print(f"[VOICE_UI] Voice result: {text[:50] if text else 'empty'}")
        if not text:
            self.stop_listening()
            return
        
        # Mark that this input came from voice (so response will be spoken)
        if hasattr(self.app, 'voice_input_mode'):
            self.app.voice_input_mode = True
            print(f"[VOICE_UI] Set voice_input_mode = True")
        
        # Always show the input area (never hide chat box)
        if hasattr(self.app, '_show_input_area'):
            self.app._show_input_area(True)
        if hasattr(self.app, '_hide_welcome'):
            self.app._hide_welcome()
        # Try to populate both possible active entries to avoid focus/lifecycle issues
        try:
            if hasattr(self.app, 'welcome_input') and self.app.welcome_input and self.app.welcome_input.winfo_exists():
                self.app.welcome_input.delete("1.0", "end")
                self.app.welcome_input.insert("1.0", text)
        except Exception:
            pass
        try:
            if hasattr(self.app, 'command_entry') and self.app.command_entry and self.app.command_entry.winfo_exists():
                self.app.command_entry.delete("1.0", "end")
                self.app.command_entry.insert("1.0", text)
        except Exception:
            pass
        # Stop listening first so status updates clearly
        self.stop_listening()
        # Auto-submit with retries if app is busy
        self._auto_submit(retries=8)

    def _auto_submit(self, retries=5):
        """Auto-submit the voice command. Retries if app is busy."""
        if not retries:
            self._show_status("Voice: busy, try again")
            return
        if hasattr(self.app, 'is_processing') and self.app.is_processing:
            root = self.app.app if hasattr(self.app, 'app') else self.app
            root.after(300, lambda: self._auto_submit(retries-1))
            return
        if hasattr(self.app, '_execute_command'):
            try:
                self.app._execute_command()
            except TypeError:
                # Fallback: some wrappers may not accept extra args
                self.app._execute_command

    def _handle_voice_timeout(self):
        """Handle listening timeout."""
        if self.is_listening:
            self._show_status("Voice: timeout")
            self.stop_listening()

    def _handle_voice_error(self, error):
        """Handle voice recognition error."""
        print(f"Voice error: {error}")
        self.stop_listening()
        
        # Show descriptive error message
        error_lower = str(error).lower()
        if "could not understand" in error_lower:
            self._show_status("Didn't catch that — try again")
        elif "microphone" in error_lower:
            self._show_status("Microphone not available")
        elif "google" in error_lower or "request" in error_lower:
            self._show_status("Voice: network error")
        elif "timeout" in error_lower:
            self._show_status("Voice: no speech detected")
        else:
            self._show_status("Voice error — try again")

    def _update_button_state(self):
        """Update microphone button appearance."""
        if not self.voice_button:
            return
        if self.is_listening:
            self.voice_button.configure(fg_color="#dc2626", text_color="white")
        else:
            self.voice_button.configure(fg_color="transparent", text_color="#8e8ea0")

    def _show_status(self, text):
        """Update status label."""
        if self.status_label:
            self.status_label.configure(text=text)

    def speak_response(self, text):
        """Speak AI response (non-blocking) with cleaned text."""
        print(f"[VOICE_UI] speak_response called, voice_available: {self.voice_engine.is_voice_available()}")
        if not self.voice_engine.is_voice_available():
            print("[VOICE_UI] Voice not available, returning")
            return
        
        # Clean text for natural speech - remove markdown, emojis, code blocks
        import re
        clean_text = text
        # Remove markdown bold/italic
        clean_text = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_text)
        clean_text = re.sub(r'\*(.+?)\*', r'\1', clean_text)
        # Remove code blocks
        clean_text = re.sub(r'`(.+?)`', r'\1', clean_text)
        # Remove emojis (keep text readable)
        clean_text = re.sub(r'[\U0001F300-\U0001F9FF\U00002702-\U000027B0\U000024C2-\U0001F251]+', '', clean_text)
        # Remove bullet points and special chars
        clean_text = re.sub(r'[•\-]\s*', '', clean_text)
        # Remove extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Limit length for speech (first 500 chars)
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "..."
        
        if not clean_text:
            print("[VOICE_UI] Clean text is empty, returning")
            return
        
        print(f"[VOICE_UI] Speaking: {clean_text[:100]}...")
        root = self.app.app if hasattr(self.app, 'app') else self.app

        def on_speak_start(speaking):
            try:
                if self.status_label:
                    self.status_label.configure(text="Speaking..." if speaking else "")
            except Exception:
                pass

        self.voice_engine.speaking_callback = on_speak_start
        self.voice_engine.speak(clean_text)
