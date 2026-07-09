import sys
import json
import os
import threading
import time
import uuid
from pathlib import Path
from tkinter import messagebox
import tkinter as tk
from datetime import datetime, timedelta

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk
import webbrowser

# --- Paths ---
ROOT_DIR = Path(__file__).resolve().parent.parent
SESSIONS_FILE = ROOT_DIR / "database" / "chat_sessions.json"
ASSETS_DIR = ROOT_DIR / "assets"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent import process_command
from system.environment_scanner import get_environment_stats

# --- Theme ---
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

SIDEBAR_COLOR = "#f7f7f8"
SIDEBAR_HOVER = "#ececec"
SIDEBAR_ACTIVE = "#e8e8e8"
SIDEBAR_TEXT = "#202123"
SIDEBAR_MUTED = "#8e8ea0"
SIDEBAR_BORDER = "#e5e5e5"
MAIN_BG = "#ffffff"
INPUT_BG = "#f4f4f5"
INPUT_BORDER = "#d1d5db"
ACCENT = "#10a37f"
ACCENT_HOVER = "#0d8c6d"
ACCENT_LIGHT = "#ecfdf5"
TEXT_PRIMARY = "#202123"
TEXT_SECONDARY = "#6e6e80"
HEADER_BG = "#fafafa"
HEADER_BORDER = "#eaeaea"

# Font sizes
FONT_USER = ("Segoe UI", 14)
FONT_AI = ("Segoe UI", 14)
FONT_HINT = ("Segoe UI", 11)
FONT_HEADER = ("Segoe UI", 16, "bold")
FONT_WELCOME_TITLE = ("Segoe UI", 36, "bold")
FONT_WELCOME_SUB = ("Segoe UI", 16)
FONT_CHIP = ("Segoe UI", 12)
FONT_SIDEBAR = ("Segoe UI", 13)
FONT_SMALL_BTN = ("Segoe UI", 11)
FONT_BRAND = ("Segoe UI", 18, "bold")

# --- Logo loading ---
def _load_logo(name, size=None):
    """Load a logo image from assets folder."""
    path = ASSETS_DIR / name
    if path.exists():
        img = Image.open(path)
        if size:
            img = img.resize((size, size), Image.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size or img.width, size or img.height))
    return None

def _load_pil_logo(name, size=None):
    """Load a raw PIL image from assets folder."""
    path = ASSETS_DIR / name
    if path.exists():
        img = Image.open(path)
        if size:
            img = img.resize((size, size), Image.LANCZOS)
        return img
    return None


# --- Supersampled Icon System ---
# Draw icons at 4x resolution then downscale for smooth anti-aliased edges
_HR = 96  # high-res canvas size


def _ss(draw_func, color="#6e6e80"):
    """Supersampled icon: draw at _HR, return downscaled to 24px."""
    hr = _ss_img(draw_func, _HR, color)
    return hr.resize((24, 24), Image.LANCZOS)


def _ss_img(draw_func, size, color):
    """Call a draw function at high resolution."""
    return draw_func(size, color)


def _hex_rgba(h):
    """Convert hex color to RGBA tuple."""
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)


# -- Icon draw functions (designed at 96px) --

def _icon_copy(s, color):
    """Two overlapping document pages."""
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = _hex_rgba(color)
    w = int(s * 0.065)
    r = int(s * 0.06)
    # Back page
    d.rounded_rectangle(
        [int(s*0.34), int(s*0.06), int(s*0.94), int(s*0.66)],
        radius=r, outline=c, width=w
    )
    # Front page
    d.rounded_rectangle(
        [int(s*0.06), int(s*0.34), int(s*0.66), int(s*0.94)],
        radius=r, outline=c, width=w
    )
    return img


def _icon_edit(s, color):
    """Pencil icon with baseline."""
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = _hex_rgba(color)
    w = int(s * 0.065)
    # Pencil shaft (diagonal)
    d.line([(int(s*0.10), int(s*0.78)), (int(s*0.66), int(s*0.22))], fill=c, width=w)
    d.line([(int(s*0.22), int(s*0.90)), (int(s*0.78), int(s*0.34))], fill=c, width=w)
    # Connect shaft top
    d.line([(int(s*0.66), int(s*0.22)), (int(s*0.78), int(s*0.34))], fill=c, width=w)
    # Pencil tip (filled triangle)
    d.polygon([
        (int(s*0.10), int(s*0.78)),
        (int(s*0.22), int(s*0.90)),
        (int(s*0.06), int(s*0.94)),
    ], fill=c)
    # Eraser cap
    er = int(s * 0.08)
    d.arc(
        [int(s*0.62), int(s*0.18), int(s*0.82), int(s*0.38)],
        start=225, end=45, fill=c, width=w
    )
    # Baseline
    d.line([(int(s*0.04), int(s*0.94)), (int(s*0.44), int(s*0.94))], fill=c, width=w)
    return img


def _icon_thumbs_up(s, color):
    """ChatGPT-style outlined thumbs up."""
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = _hex_rgba(color)
    w = int(s * 0.065)
    r = int(s * 0.05)
    # Thumb bar (left vertical)
    d.rounded_rectangle(
        [int(s*0.08), int(s*0.40), int(s*0.30), int(s*0.92)],
        radius=r, outline=c, width=w
    )
    # Hand/fingers area
    d.rounded_rectangle(
        [int(s*0.30), int(s*0.22), int(s*0.92), int(s*0.92)],
        radius=int(s*0.10), outline=c, width=w
    )
    # Thumb knuckle line going up
    mid_x = (int(s*0.08) + int(s*0.30)) // 2
    d.line([(mid_x, int(s*0.40)), (mid_x, int(s*0.15))], fill=c, width=w)
    # Connect knuckle to hand
    d.line([(mid_x, int(s*0.15)), (int(s*0.40), int(s*0.22))], fill=c, width=w)
    return img


def _icon_thumbs_down(s, color):
    """Rotated thumbs up."""
    up = _icon_thumbs_up(s, color)
    return up.rotate(180, expand=False)


def _icon_share(s, color):
    """Upload/share arrow icon."""
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = _hex_rgba(color)
    w = int(s * 0.065)
    cx = s // 2
    # Arrow shaft
    d.line([(cx, int(s*0.72)), (cx, int(s*0.22))], fill=c, width=w)
    # Arrow head (chevron)
    d.line([(int(s*0.30), int(s*0.40)), (cx, int(s*0.22))], fill=c, width=w)
    d.line([(cx, int(s*0.22)), (int(s*0.70), int(s*0.40))], fill=c, width=w)
    # Base tray
    bw = int(s * 0.065)
    d.line([(int(s*0.20), int(s*0.82)), (int(s*0.80), int(s*0.82))], fill=c, width=bw)
    # Tray sides
    d.line([(int(s*0.20), int(s*0.82)), (int(s*0.20), int(s*0.72))], fill=c, width=bw)
    d.line([(int(s*0.80), int(s*0.82)), (int(s*0.80), int(s*0.72))], fill=c, width=bw)
    return img


def _make_ctk_icon(draw_func, display_size=18, color="#6e6e80"):
    """Create a smooth CTkImage icon using supersampling."""
    pil_img = _ss(draw_func, color)
    return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(display_size, display_size))


# =====================================================================
#  Lightweight Tooltip
# =====================================================================
class _Tooltip:
    """Simple tooltip that appears on hover over a widget."""
    _active = None
    _toplevel = None

    @classmethod
    def bind(cls, widget, text, delay_ms=400):
        widget.bind("<Enter>", lambda e, w=widget, t=text, d=delay_ms: cls._schedule(w, t, d))
        widget.bind("<Leave>", lambda e: cls._hide())
        widget.bind("<ButtonPress>", lambda e: cls._hide())

    @classmethod
    def _schedule(cls, widget, text, delay):
        cls._active = widget
        try:
            widget._tooltip_id = widget.after(delay, lambda: cls._show(widget, text))
        except Exception:
            pass

    @classmethod
    def _show(cls, widget, text):
        if cls._active is not widget:
            return
        cls._hide()
        try:
            x = widget.winfo_rootx() + widget.winfo_width() // 2
            y = widget.winfo_rooty() - 28
        except Exception:
            return
        cls._toplevel = tk.Toplevel(widget)
        cls._toplevel.overrideredirect(True)
        cls._toplevel.attributes("-topmost", True)
        lbl = tk.Label(
            cls._toplevel, text=text,
            font=("Segoe UI", 10), bg="#202123", fg="white",
            padx=8, pady=4
        )
        lbl.pack()
        cls._toplevel.geometry(f"+{x - lbl.winfo_reqwidth()//2}+{y}")

    @classmethod
    def _hide(cls):
        if cls._toplevel and cls._toplevel.winfo_exists():
            cls._toplevel.destroy()
        cls._toplevel = None
        if cls._active:
            try:
                cls._active.after_cancel(getattr(cls._active, '_tooltip_id', ''))
            except Exception:
                pass
        cls._active = None


# =====================================================================
#  Confirmation Dialog
# =====================================================================
class ConfirmationDialog:
    """Modern confirmation dialog for dangerous commands"""

    def __init__(self, parent, command, details, on_confirm, on_cancel):
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Confirm Action")
        self.dialog.geometry("460x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(fg_color="#ffffff")

        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 230
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 150
        self.dialog.geometry(f"+{x}+{y}")

        icon_frame = ctk.CTkFrame(self.dialog, fg_color="#fef3c7", corner_radius=50, width=60, height=60)
        icon_frame.pack(pady=(30, 10))
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(icon_frame, text="!", font=("Segoe UI", 28, "bold"), text_color="#d97706").pack(expand=True)

        ctk.CTkLabel(
            self.dialog, text="Confirm Action", font=("Segoe UI", 20, "bold"), text_color=TEXT_PRIMARY
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            self.dialog, text=f'"{command}"',
            font=("Consolas", 12), text_color=TEXT_SECONDARY, wraplength=400
        ).pack(pady=2)

        if details:
            ctk.CTkLabel(
                self.dialog, text=details, font=("Segoe UI", 12), text_color="#dc2626", wraplength=400
            ).pack(pady=2)

        btn_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        btn_frame.pack(pady=25)

        ctk.CTkButton(
            btn_frame, text="Cancel", width=110, height=38, font=("Segoe UI", 13),
            fg_color="#e5e7eb", hover_color="#d1d5db", text_color="#374151", corner_radius=8,
            command=self._cancel
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text="Confirm", width=110, height=38, font=("Segoe UI", 13, "bold"),
            fg_color="#dc2626", hover_color="#b91c1c", corner_radius=8,
            command=self._confirm
        ).pack(side="left", padx=10)

    def _confirm(self):
        self.dialog.destroy()
        self.on_confirm()

    def _cancel(self):
        self.dialog.destroy()
        self.on_cancel()


# =====================================================================
#  Animated Thinking Indicator
# =====================================================================
class ThinkingIndicator:
    """Animated pulsing dots for thinking state."""

    def __init__(self, parent):
        self.parent = parent
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.label = ctk.CTkLabel(
            self.frame, text="", font=FONT_AI,
            text_color=TEXT_SECONDARY, justify="left", anchor="w"
        )
        self.label.pack()
        self._step = 0
        self._running = False

    def start(self):
        self._running = True
        self._animate()

    def stop(self):
        self._running = False

    def _animate(self):
        if not self._running:
            return
        dots = "." * (self._step % 4)
        self.label.configure(text=f"Thinking{dots}")
        self._step += 1
        self.frame.after(400, self._animate)


# =====================================================================
#  AMAZONAI Main Application
# =====================================================================
class AMAZONAI:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("AMAZON")
        self.app.geometry("1200x780")
        self.app.minsize(900, 550)
        self.app.configure(fg_color=MAIN_BG)

        # Set window icon
        ico_path = ASSETS_DIR / "nova_icon.ico"
        if ico_path.exists():
            try:
                self.app.iconbitmap(str(ico_path))
            except Exception:
                pass

        # Pre-load logos
        self.logo_sidebar = _load_logo("nova_logo_64.png", 48)
        self.logo_welcome = _load_logo("nova_logo_140.png", 100)
        self.logo_header = _load_logo("nova_logo_36.png", 30)

        # Voice feature toggle (off by default; user can enable from settings/integration)
        self.voice_enabled = False

        # Pre-load action icons (supersampled for smooth edges)
        ic = "#8e8ea0"
        self.icon_copy = _make_ctk_icon(_icon_copy, 18, ic)
        self.icon_edit = _make_ctk_icon(_icon_edit, 18, ic)
        self.icon_thumb_up = _make_ctk_icon(_icon_thumbs_up, 18, ic)
        self.icon_thumb_down = _make_ctk_icon(_icon_thumbs_down, 18, ic)
        self.icon_share = _make_ctk_icon(_icon_share, 18, ic)

        # State
        self.sessions = []
        self.active_session_id = None
        self.is_processing = False
        self.welcome_widget = None
        self.welcome_input = None  # Input embedded in welcome screen
        self._thinking_indicator = None
        self._thinking_card = None

        # Load saved sessions
        self._load_sessions()
        self._validate_active_session()

        # Build UI
        self._build_ui()

        # Initialize voice UI integration
        try:
            from ui.voice_ui import VoiceUIController
            self.voice_ui = VoiceUIController(self)
            self.voice_ui.initialize()
        except Exception as e:
            print(f"Voice integration could not be initialized: {e}")
            self.voice_ui = None

        # Force window to front on Windows
        self.app.lift()
        self.app.attributes('-topmost', True)
        self.app.after(200, lambda: self.app.attributes('-topmost', False))
        self.app.focus_force()

        # Always start with a new chat screen
        self._new_chat()

    # -----------------------------------------------------------------
    #  Session Persistence
    # -----------------------------------------------------------------
    def _load_sessions(self):
        try:
            if SESSIONS_FILE.exists():
                with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.sessions = data.get("sessions", [])
                    self.active_session_id = data.get("active_session_id")
        except Exception:
            self.sessions = []

    def _validate_active_session(self):
        if not self.sessions:
            self.active_session_id = None
            return
        if self.active_session_id and self._get_active_session():
            return
        empty_sessions = [s for s in self.sessions if not s.get("messages")]
        if empty_sessions:
            self.active_session_id = empty_sessions[-1]["session_id"]
        else:
            self.active_session_id = self.sessions[-1]["session_id"]

    def _save_sessions(self):
        try:
            SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "sessions": self.sessions,
                    "active_session_id": self.active_session_id,
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving sessions: {e}")

    def _get_active_session(self):
        for s in self.sessions:
            if s["session_id"] == self.active_session_id:
                return s
        return None

    def _new_chat(self):
        # Check if there's already an empty session - reuse it instead of creating new
        empty_sessions = [s for s in self.sessions if not s.get("messages")]
        if empty_sessions:
            # Reuse the last empty session
            self.active_session_id = empty_sessions[-1]["session_id"]
            self._save_sessions()
            self._refresh_sidebar()
            self._clear_chat_display()
            self._show_input_area(False)
            self._show_welcome()
            return
        
        session = {
            "session_id": str(uuid.uuid4())[:8],
            "title": "New Chat",
            "messages": [],
            "created_at": datetime.now().isoformat(),
        }
        self.sessions.append(session)
        self.active_session_id = session["session_id"]
        self._save_sessions()
        self._refresh_sidebar()
        self._clear_chat_display()
        self._show_input_area(False)  # Hide bottom input on new chat
        self._show_welcome()

    def _clear_all_history(self):
        """Clear all chat history with confirmation."""
        from tkinter import messagebox
        
        result = messagebox.askyesno(
            "Clear History",
            "Are you sure you want to clear all chat history?\n\nThis action cannot be undone.",
            icon="warning"
        )
        
        if result:
            # Keep only one empty session for new chat
            self.sessions = [{
                "session_id": str(uuid.uuid4())[:8],
                "title": "New Chat",
                "messages": [],
                "created_at": datetime.now().isoformat(),
            }]
            self.active_session_id = self.sessions[0]["session_id"]
            self._save_sessions()
            self._refresh_sidebar()
            self._clear_chat_display()
            self._show_input_area(False)
            self._show_welcome()

    def _load_session(self, session_id):
        self.active_session_id = session_id
        session = self._get_active_session()
        if not session:
            if self.sessions:
                self.active_session_id = self.sessions[-1]["session_id"]
            session = self._get_active_session()

        self._save_sessions()
        self._refresh_sidebar()
        self._clear_chat_display()
        
        if session and session["messages"]:
            self._show_input_area(True)  # Show bottom input for active chat
            for msg in session["messages"]:
                if msg["role"] == "user":
                    self._render_user_message(msg["content"])
                else:
                    self._render_ai_message(msg["content"])
            self._refresh_scroll_region()
            try:
                self.chat_scroll._parent_canvas.yview_moveto(1.0)
            except:
                pass
        else:
            self._show_input_area(False)
            self._show_welcome()

    def _delete_session(self, session_id):
        self.sessions = [s for s in self.sessions if s["session_id"] != session_id]
        if self.active_session_id == session_id:
            if self.sessions:
                self._load_session(self.sessions[-1]["session_id"])
            else:
                self._new_chat()
        else:
            self._save_sessions()
            self._refresh_sidebar()

    # -----------------------------------------------------------------
    #  Build UI
    # -----------------------------------------------------------------
    def _build_ui(self):
        self.app.grid_rowconfigure(0, weight=1)
        self.app.grid_columnconfigure(1, weight=1)

        # ======================== SIDEBAR ========================
        self.sidebar = ctk.CTkFrame(
            self.app, width=260, fg_color=SIDEBAR_COLOR, corner_radius=0,
            border_width=0
        )
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        # Right border line
        sidebar_border = ctk.CTkFrame(self.sidebar, width=1, fg_color=SIDEBAR_BORDER)
        sidebar_border.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")

        # Logo area (image only, no text)
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(22, 5))

        if self.logo_sidebar:
            logo_lbl = ctk.CTkLabel(logo_frame, image=self.logo_sidebar, text="")
            logo_lbl.pack(side="left")
        else:
            ctk.CTkLabel(
                logo_frame, text="AMAZON",
                font=FONT_BRAND, text_color=ACCENT
            ).pack(side="left")

        # Brand name next to logo
        if self.logo_sidebar:
            ctk.CTkLabel(
                logo_frame, text="AMAZON",
                font=FONT_BRAND, text_color=TEXT_PRIMARY
            ).pack(side="left", padx=(10, 0))

        # New Chat button
        self.new_chat_btn = ctk.CTkButton(
            self.sidebar, text="+  New Chat", height=42,
            font=FONT_SIDEBAR, fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="white",
            corner_radius=10,
            command=self._new_chat
        )
        self.new_chat_btn.pack(fill="x", padx=14, pady=(18, 10))

        # Separator
        ctk.CTkFrame(self.sidebar, height=1, fg_color=SIDEBAR_BORDER).pack(
            fill="x", padx=16, pady=(5, 10)
        )

        # History section header
        hist_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        hist_header.pack(fill="x", padx=18)
        ctk.CTkLabel(
            hist_header, text="History", font=("Segoe UI", 12, "bold"),
            text_color=SIDEBAR_MUTED
        ).pack(side="left")

        # Clear History button (small, next to header)
        clear_hist_btn = ctk.CTkButton(
            hist_header, text="Clear", width=50, height=22,
            font=("Segoe UI", 10), fg_color="transparent",
            hover_color="#fee2e2", text_color="#dc2626",
            corner_radius=6,
            command=self._clear_all_history
        )
        clear_hist_btn.pack(side="right")

        # Sidebar footer (pinned to bottom)
        footer_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", padx=14, pady=(5, 14))
        # Top separator line above footer
        ctk.CTkFrame(footer_frame, height=1, fg_color=SIDEBAR_BORDER).pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            footer_frame, text="v2.0  |  Desktop Assistant",
            font=("Segoe UI", 11), text_color=SIDEBAR_MUTED
        ).pack(side="left", padx=4)

        # Scrollable history area (fills remaining space above footer)
        self.history_scroll = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent",
            scrollbar_button_color="#c5c5c5",
            scrollbar_button_hover_color="#a0a0a0",
        )
        self.history_scroll.pack(fill="both", expand=True, padx=8, pady=(5, 5))

        # ======================== MAIN AREA ========================
        self.main_frame = ctk.CTkFrame(self.app, fg_color=MAIN_BG, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # ======================== HEADER ========================
        header = ctk.CTkFrame(
            self.main_frame, height=60, fg_color=HEADER_BG, corner_radius=0,
            border_width=0
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        # Bottom border
        header_border = ctk.CTkFrame(header, height=1, fg_color=HEADER_BORDER)
        header_border.place(rely=1.0, relwidth=1.0, anchor="s")

        # Header left: logo + title
        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", padx=20, pady=10)

        if self.logo_header:
            ctk.CTkLabel(header_left, image=self.logo_header, text="").pack(side="left")
        ctk.CTkLabel(
            header_left, text="AMAZON",
            font=FONT_HEADER, text_color=TEXT_PRIMARY
        ).pack(side="left", padx=(8, 0))

        # Header right: action buttons
        self.header_right = ctk.CTkFrame(header, fg_color="transparent")
        self.header_right.pack(side="right", padx=16, pady=10)

        # Upgrade button
        upgrade_btn = ctk.CTkButton(
            self.header_right, text="Upgrade", width=80, height=32,
            font=("Segoe UI", 12), fg_color="transparent",
            hover_color="#f0f0f0", text_color=TEXT_SECONDARY,
            corner_radius=8, border_width=1, border_color=SIDEBAR_BORDER,
            command=self._show_upgrade_info
        )
        upgrade_btn.pack(side="left", padx=(0, 8))

        # Refresh button (circular arrow icon)
        refresh_btn = ctk.CTkButton(
            self.header_right, text="\u21bb", width=36, height=36,
            font=("Segoe UI", 18), fg_color="transparent",
            hover_color="#f0f0f0", text_color=TEXT_SECONDARY,
            corner_radius=8,
            command=self._refresh_app
        )
        refresh_btn.pack(side="left", padx=(0, 4))

        # Settings button (gear icon)
        settings_btn = ctk.CTkButton(
            self.header_right, text="\u2699", width=36, height=36,
            font=("Segoe UI", 18), fg_color="transparent",
            hover_color="#f0f0f0", text_color=TEXT_SECONDARY,
            corner_radius=8,
            command=self._show_settings_info
        )
        settings_btn.pack(side="left", padx=(0, 4))

        # ======================== CHAT AREA ========================
        self.chat_container = ctk.CTkFrame(self.main_frame, fg_color=MAIN_BG, corner_radius=0)
        self.chat_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.chat_container.grid_rowconfigure(0, weight=1)
        self.chat_container.grid_columnconfigure(0, weight=1)

        # Scrollable chat
        self.chat_scroll = ctk.CTkScrollableFrame(
            self.chat_container, fg_color=MAIN_BG, corner_radius=0,
            scrollbar_button_color="#d1d5db",
            scrollbar_button_hover_color="#a0a0a0",
        )
        self.chat_scroll.grid(row=0, column=0, sticky="nsew")
        self.chat_scroll.grid_columnconfigure(0, weight=1)

        # Messages container
        self.msg_frame = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        self.msg_frame.pack(fill="both", expand=True, padx=0)
        self.msg_frame.grid_columnconfigure(0, weight=1)

        self.msg_row = 0
        
        # Click anywhere in chat area to focus input (will be connected after input is created)
        self._chat_click_focus = None

        # ======================== INPUT AREA (bottom, for active chats) ========================
        self.input_outer = ctk.CTkFrame(self.main_frame, fg_color=MAIN_BG, corner_radius=0)
        self.input_outer.grid(row=2, column=0, sticky="ew", padx=0, pady=0)

        input_center = ctk.CTkFrame(self.input_outer, fg_color="transparent")
        input_center.pack(fill="x", padx=40, pady=(8, 6))

        entry_bg = ctk.CTkFrame(
            input_center, fg_color=INPUT_BG, corner_radius=20,
            border_width=2, border_color=INPUT_BORDER
        )
        entry_bg.pack(fill="x")

        self.command_entry = ctk.CTkTextbox(
            entry_bg, height=48, font=FONT_USER,
            fg_color=INPUT_BG, text_color=TEXT_PRIMARY,
            border_width=0, corner_radius=20, wrap="word"
        )
        self.command_entry.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(6, 6))
        
        # Ensure the input is always clickable and focused
        self.command_entry.configure(state="normal")
        
        # Make the ENTIRE input area clickable - bind to all parent frames
        def _focus_input(event=None):
            self.command_entry.focus_set()
        
        # Store reference for chat area binding
        self._chat_click_focus = _focus_input
        
        # Bind click to focus on all input area components
        self.command_entry.bind("<Button-1>", _focus_input)
        entry_bg.bind("<Button-1>", _focus_input)
        input_center.bind("<Button-1>", _focus_input)
        self.input_outer.bind("<Button-1>", _focus_input)
        
        # Bind to the main frame - clicking anywhere in bottom 200px focuses input
        self.main_frame.bind("<Button-1>", lambda e: _focus_input() if e.y > self.main_frame.winfo_height() - 200 else None)
        
        # Bind chat area clicks to focus input (click anywhere in chat to type)
        self.chat_container.bind("<Button-1>", _focus_input)
        self.chat_scroll.bind("<Button-1>", _focus_input)
        self.msg_frame.bind("<Button-1>", _focus_input)

        def on_enter(event):
            self._execute_command()
            return "break"

        self.command_entry.bind("<Return>", on_enter)
        self.command_entry.bind("<Shift-Return>", lambda e: None)

        self.send_btn = ctk.CTkButton(
            entry_bg, text="\u2191", width=38, height=38,
            font=("Segoe UI", 18, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=14,
            command=self._execute_command,
        )
        self.send_btn.pack(side="right", padx=8, pady=6)

        # Hint below input - also clickable to focus
        hint_label = ctk.CTkLabel(
            self.input_outer, text="Press Enter to send  |  Shift+Enter for new line  |  Type 'help' for commands",
            font=FONT_HINT, text_color=TEXT_SECONDARY
        )
        hint_label.pack(pady=(0, 8))
        hint_label.bind("<Button-1>", _focus_input)

        # Hide input area initially (welcome screen has its own input)
        self.input_outer.grid_remove()

    # -----------------------------------------------------------------
    #  Input area visibility
    # -----------------------------------------------------------------
    def _show_input_area(self, show):
        """Show or hide the bottom input area."""
        if show:
            self.input_outer.grid()
        else:
            self.input_outer.grid_remove()

    def _get_active_entry(self):
        """Get the currently active command entry (welcome or bottom)."""
        if self.welcome_input and self.welcome_input.winfo_exists():
            return self.welcome_input
        return self.command_entry

    # -----------------------------------------------------------------
    #  Sidebar / History
    # -----------------------------------------------------------------
    def _refresh_sidebar(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        groups = {"Today": [], "Yesterday": [], "Previous": []}

        for s in reversed(self.sessions):
            created = datetime.fromisoformat(s["created_at"]).date()
            if created == today:
                groups["Today"].append(s)
            elif created == yesterday:
                groups["Yesterday"].append(s)
            else:
                groups["Previous"].append(s)

        for group_name, items in groups.items():
            if not items:
                continue
            ctk.CTkLabel(
                self.history_scroll, text=group_name,
                font=("Segoe UI", 11, "bold"), text_color=SIDEBAR_MUTED,
                anchor="w"
            ).pack(fill="x", padx=10, pady=(12, 2))

            for session in items:
                is_active = session["session_id"] == self.active_session_id
                bg = SIDEBAR_ACTIVE if is_active else SIDEBAR_COLOR
                hover = SIDEBAR_ACTIVE if is_active else SIDEBAR_HOVER

                item_frame = ctk.CTkFrame(
                    self.history_scroll, fg_color=bg, corner_radius=8, height=40
                )
                item_frame.pack(fill="x", padx=4, pady=1)
                item_frame.pack_propagate(False)

                title = session.get("title", "New Chat")[:28]
                lbl = ctk.CTkLabel(
                    item_frame, text=title, font=FONT_SIDEBAR,
                    text_color=SIDEBAR_TEXT, anchor="w",
                )
                lbl.pack(side="left", padx=12, fill="x", expand=True)

                del_btn = ctk.CTkLabel(
                    item_frame, text="x", font=("Segoe UI", 12),
                    text_color=SIDEBAR_MUTED, width=24,
                )
                del_btn.pack(side="right", padx=(0, 8))

                sid = session["session_id"]
                lbl.bind("<Button-1>", lambda e, s=sid: self._load_session(s))
                item_frame.bind("<Button-1>", lambda e, s=sid: self._load_session(s))
                del_btn.bind("<Button-1>", lambda e, s=sid: self._delete_session(s))

                def _on_enter(e, f=item_frame, h=hover):
                    f.configure(fg_color=h)
                def _on_leave(e, f=item_frame, a=is_active):
                    f.configure(fg_color=SIDEBAR_ACTIVE if a else SIDEBAR_COLOR)

                item_frame.bind("<Enter>", _on_enter)
                item_frame.bind("<Leave>", _on_leave)
                lbl.bind("<Enter>", _on_enter)
                lbl.bind("<Leave>", _on_leave)

    # -----------------------------------------------------------------
    #  Welcome Screen (with fade-in animation + embedded input)
    # -----------------------------------------------------------------
    def _show_welcome(self):
        # Configure msg_frame for grid layout
        self.msg_frame.grid_rowconfigure(0, weight=1)
        self.msg_frame.grid_columnconfigure(0, weight=1)
        
        welcome = ctk.CTkFrame(self.msg_frame, fg_color="transparent")
        welcome.grid(row=0, column=0, sticky="nsew", pady=(60, 0))
        welcome.grid_columnconfigure(0, weight=1)
        self.welcome_widget = welcome

        # Content container (centered)
        content = ctk.CTkFrame(welcome, fg_color="transparent")
        content.pack(expand=True)

        # -- Logo image (with fade-in) --
        if self.logo_welcome:
            self._welcome_logo_lbl = ctk.CTkLabel(content, image=self.logo_welcome, text="")
            self._welcome_logo_lbl.pack(pady=(0, 16))
        else:
            ctk.CTkLabel(
                content, text="AMAZON", font=FONT_WELCOME_TITLE, text_color=ACCENT
            ).pack(pady=(0, 8))

        # -- Title & subtitle --
        self._welcome_title = ctk.CTkLabel(
            content, text="How can I help you today?",
            font=("Segoe UI", 24, "bold"), text_color=TEXT_PRIMARY
        )
        self._welcome_title.pack(pady=(0, 6))

        self._welcome_sub = ctk.CTkLabel(
            content, text="Your Desktop Automation Assistant",
            font=FONT_WELCOME_SUB, text_color=TEXT_SECONDARY
        )
        self._welcome_sub.pack(pady=(0, 20))
        
        # Environment discovery stats
        try:
            import platform
            import psutil
            
            # Get system info
            os_name = platform.system()
            os_version = platform.version()
            machine = platform.machine()
            cpu_count = psutil.cpu_count()
            ram = psutil.virtual_memory()
            ram_gb = ram.total / (1024**3)
            
            # Create a nice computer profile card
            profile_frame = ctk.CTkFrame(content, fg_color="#f7f7f8", corner_radius=12, border_width=1, border_color="#e5e5e5")
            profile_frame.pack(pady=(0, 20), padx=40, fill="x")
            
            # Title
            ctk.CTkLabel(
                profile_frame, text="💻 Computer Profile",
                font=("Segoe UI", 14, "bold"), text_color=TEXT_PRIMARY
            ).pack(anchor="w", padx=16, pady=(12, 8))
            
            # Profile details in a grid-like layout
            details_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
            details_frame.pack(fill="x", padx=16, pady=(0, 12))
            
            # Create profile items
            profile_items = [
                ("Device", f"{platform.node()} ({machine})"),
                ("OS", f"{os_name} {os_version[:3] if len(os_version) > 3 else os_version}"),
                ("CPU", f"{cpu_count} cores"),
                ("RAM", f"{ram_gb:.0f} GB"),
            ]
            
            for i, (label, value) in enumerate(profile_items):
                row = i // 2
                col = (i % 2) * 2
                
                # Label
                ctk.CTkLabel(
                    details_frame, text=f"{label}:",
                    font=("Segoe UI", 12), text_color=TEXT_SECONDARY
                ).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=4)
                
                # Value
                ctk.CTkLabel(
                    details_frame, text=value,
                    font=("Segoe UI", 12, "bold"), text_color=TEXT_PRIMARY
                ).grid(row=row, column=col+1, sticky="w", padx=(0, 20), pady=4)
            
            # Environment stats
            stats = get_environment_stats()
            env_text = f"Discovered: {stats.get('total_drives', 0)} drives • {stats.get('total_apps', 0)} apps • {stats.get('total_folders', 0)} folders"
            ctk.CTkLabel(
                content, text=env_text,
                font=("Segoe UI", 11), text_color=TEXT_SECONDARY
            ).pack(pady=(0, 10))
        except Exception:
            # Fallback if system info fails
            try:
                stats = get_environment_stats()
                stats_text = f"Discovered: {stats.get('total_drives', 0)} drives • {stats.get('total_apps', 0)} apps • {stats.get('total_folders', 0)} folders"
                ctk.CTkLabel(
                    content, text=stats_text,
                    font=("Segoe UI", 12), text_color=TEXT_SECONDARY
                ).pack(pady=(0, 30))
            except Exception:
                pass

        # -- Suggestion chips --
        chips_frame = ctk.CTkFrame(content, fg_color="transparent")
        chips_frame.pack(pady=(0, 30))

        suggestions = [
            "Create file report.txt",
            "Open Chrome",
            "Search web python tutorial",
            "Create folder Projects",
            "List processes",
            "Create react project myapp",
        ]

        for i, text in enumerate(suggestions):
            row, col = divmod(i, 3)
            chip = ctk.CTkButton(
                chips_frame, text=text, height=38,
                font=FONT_CHIP,
                fg_color="#f7f7f8", hover_color="#ececf1",
                text_color=TEXT_PRIMARY, corner_radius=20,
                border_width=1, border_color="#e5e5e5",
                command=lambda t=text: self._send_command(t)
            )
            chip.grid(row=row, column=col, padx=6, pady=6)

        # -- Embedded input (centered, below chips) --
        input_container = ctk.CTkFrame(content, fg_color="transparent")
        input_container.pack(fill="x", padx=40, pady=(16, 0))

        entry_bg = ctk.CTkFrame(
            input_container, fg_color=INPUT_BG, corner_radius=20,
            border_width=2, border_color=INPUT_BORDER
        )
        entry_bg.pack(fill="x")

        self.welcome_input = ctk.CTkTextbox(
            entry_bg, height=48, font=FONT_USER,
            fg_color=INPUT_BG, text_color=TEXT_PRIMARY,
            border_width=0, corner_radius=20, wrap="word"
        )
        self.welcome_input.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(6, 6))
        
        # Make the entire welcome input area clickable
        def _focus_welcome(event=None):
            self.welcome_input.focus_set()
        
        self.welcome_input.bind("<Button-1>", _focus_welcome)
        entry_bg.bind("<Button-1>", _focus_welcome)
        input_container.bind("<Button-1>", _focus_welcome)

        def on_welcome_enter(event):
            self._execute_command_from_welcome()
            return "break"

        self.welcome_input.bind("<Return>", on_welcome_enter)
        self.welcome_input.bind("<Shift-Return>", lambda e: None)

        welcome_send_btn = ctk.CTkButton(
            entry_bg, text="\u2191", width=38, height=38,
            font=("Segoe UI", 18, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=14,
            command=self._execute_command_from_welcome,
        )
        welcome_send_btn.pack(side="right", padx=8, pady=6)

        # Hint
        ctk.CTkLabel(
            input_container, text="Press Enter to send  |  Shift+Enter for new line  |  Type 'help' for commands",
            font=FONT_HINT, text_color=TEXT_SECONDARY
        ).pack(pady=(6, 0))

        # -- Fade-in animation: hide all children, then reveal --
        all_children = content.winfo_children()
        pack_opts = []
        for child in all_children:
            opts = child.pack_info()
            opts.pop('in', None)
            pack_opts.append(opts)
            child.pack_forget()
        self._reveal_children(content, all_children, pack_opts, 0)

        # Force scroll region refresh
        self._refresh_scroll_region()
        try:
            self.chat_scroll._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass

    def _reveal_children(self, parent, children, pack_opts, index):
        """Staggered reveal of welcome screen children for smooth animation."""
        if not parent.winfo_exists() or index >= len(children):
            return
        child = children[index]
        try:
            child.pack(**pack_opts[index])
        except Exception:
            pass
        parent.after(120, lambda: self._reveal_children(parent, children, pack_opts, index + 1))

    def _execute_command_from_welcome(self):
        """Execute command from the welcome-screen embedded input."""
        if self.is_processing:
            return
        if not self.welcome_input or not self.welcome_input.winfo_exists():
            return

        command = self.welcome_input.get("1.0", "end").strip()
        if not command:
            return

        # Switch to active chat mode: hide welcome, show bottom input
        self._hide_welcome()
        self._show_input_area(True)

        # Put command into the bottom entry for consistency
        self.command_entry.delete("1.0", "end")
        self.command_entry.insert("1.0", command)
        self._execute_command()

    # -----------------------------------------------------------------
    #  Message Rendering
    # -----------------------------------------------------------------
    def _clear_chat_display(self):
        for widget in self.msg_frame.winfo_children():
            widget.destroy()
        self.msg_row = 0
        self.welcome_widget = None
        self.welcome_input = None
        # Reset grid configuration
        for i in range(self.msg_frame.grid_size()[1]):
            self.msg_frame.grid_rowconfigure(i, weight=0)
        self.msg_frame.grid_rowconfigure(0, weight=1)
        self.msg_frame.grid_columnconfigure(0, weight=1)
        self._refresh_scroll_region()

    def _refresh_scroll_region(self):
        """Force the scrollable frame to recalculate its scroll region."""
        try:
            self.app.update_idletasks()
            canvas = self.chat_scroll._parent_canvas
            canvas.configure(scrollregion=canvas.bbox("all"))
        except Exception:
            pass

    def _hide_welcome(self):
        """Hide welcome screen when first message is sent"""
        if self.welcome_widget and self.welcome_widget.winfo_exists():
            self.welcome_widget.destroy()
        self.welcome_widget = None
        self.welcome_input = None

    def _render_user_message(self, text):
        """User message - right aligned, green pill with copy/edit icons below."""
        self._hide_welcome()

        row_frame = ctk.CTkFrame(self.msg_frame, fg_color="transparent")
        row_frame.grid(row=self.msg_row, column=0, sticky="ew", pady=(10, 0))
        row_frame.grid_columnconfigure(0, weight=1)
        self.msg_row += 1

        # Container for bubble + action icons
        right_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        right_frame.grid(row=0, column=0, sticky="e", padx=(60, 24))

        # User bubble
        bubble = ctk.CTkFrame(right_frame, fg_color=ACCENT, corner_radius=18)
        bubble.pack(anchor="e")

        msg_lbl = ctk.CTkLabel(
            bubble, text=text, font=FONT_USER,
            text_color="white", wraplength=520, justify="left"
        )
        msg_lbl.pack(padx=20, pady=10)

        # Icons row (below bubble, always visible)
        icons_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        icons_frame.pack(anchor="e", pady=(3, 0))

        copy_btn = ctk.CTkButton(
            icons_frame, image=self.icon_copy, text="", width=28, height=28,
            fg_color="transparent", hover_color="#f0f0f0",
            corner_radius=6,
            command=lambda: self._copy_to_clipboard(text, copy_btn)
        )
        copy_btn.pack(side="right", padx=2)
        _Tooltip.bind(copy_btn, "Copy")

        edit_btn = ctk.CTkButton(
            icons_frame, image=self.icon_edit, text="", width=28, height=28,
            fg_color="transparent", hover_color="#f0f0f0",
            corner_radius=6,
            command=lambda: self._edit_user_message(text, row_frame)
        )
        edit_btn.pack(side="right", padx=2)
        _Tooltip.bind(edit_btn, "Edit")

        self._refresh_scroll_region()
        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _render_ai_message(self, text):
        """AI message - left aligned with bubble background and clickable paths."""
        row_frame = ctk.CTkFrame(self.msg_frame, fg_color="transparent")
        row_frame.grid(row=self.msg_row, column=0, sticky="ew", pady=(10, 0))
        row_frame.grid_columnconfigure(0, weight=1)
        self.msg_row += 1

        # Container for bubble + action icons (left-aligned)
        left_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="w", padx=(24, 60))

        # AI bubble with light background
        bubble = ctk.CTkFrame(left_frame, fg_color="#f4f4f5", corner_radius=18)
        bubble.pack(anchor="w")

        # Check if text contains paths and render with clickable links
        if self._has_clickable_paths(text):
            self._render_message_with_links(bubble, text)
        else:
            # Use textbox for selectable/copyable text
            # Calculate proper height based on content
            lines = text.count('\n') + 1
            estimated_height = max(60, lines * 22 + 30)
            
            msg_textbox = ctk.CTkTextbox(
                bubble, font=FONT_AI,
                text_color=TEXT_PRIMARY, fg_color="transparent",
                wrap="word", activate_scrollbars=False,
                height=estimated_height
            )
            msg_textbox.insert("1.0", text)
            msg_textbox.configure(state="disabled")  # Make read-only but selectable
            msg_textbox.pack(padx=16, pady=12)

        # Action buttons with icons - compact row
        actions_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        actions_frame.pack(pady=(4, 0))

        # Copy button
        copy_btn = ctk.CTkButton(
            actions_frame, image=self.icon_copy, text="", width=30, height=30,
            fg_color="transparent", hover_color="#f0f0f0",
            corner_radius=6,
            command=lambda: self._copy_to_clipboard(text, copy_btn)
        )
        copy_btn.pack(side="left", padx=(0, 2))
        _Tooltip.bind(copy_btn, "Copy")

        # Thumbs up button
        like_btn = ctk.CTkButton(
            actions_frame, image=self.icon_thumb_up, text="", width=30, height=30,
            fg_color="transparent", hover_color="#f0f0f0",
            corner_radius=6,
            command=lambda: self._toggle_feedback(like_btn, dislike_btn, "like")
        )
        like_btn.pack(side="left", padx=(0, 2))
        _Tooltip.bind(like_btn, "Good response")

        # Thumbs down button
        dislike_btn = ctk.CTkButton(
            actions_frame, image=self.icon_thumb_down, text="", width=30, height=30,
            fg_color="transparent", hover_color="#f0f0f0",
            corner_radius=6,
            command=lambda: self._toggle_feedback(dislike_btn, like_btn, "dislike")
        )
        dislike_btn.pack(side="left", padx=(0, 2))
        _Tooltip.bind(dislike_btn, "Bad response")

        # Share button
        share_btn = ctk.CTkButton(
            actions_frame, image=self.icon_share, text="", width=30, height=30,
            fg_color="transparent", hover_color="#f0f0f0",
            corner_radius=6,
            command=lambda: self._share_message(text)
        )
        share_btn.pack(side="left")
        _Tooltip.bind(share_btn, "Share")

        self._refresh_scroll_region()
        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

        return row_frame

    def _has_clickable_paths(self, text):
        """Check if text contains file/folder paths."""
        import re
        # Match Unix paths (/Users/...) or Windows paths (C:\...)
        path_pattern = r'(?:/[\w.-]+)+/[\w.-]+|[A-Z]:\\[\w\\.-]+'
        return bool(re.search(path_pattern, text))

    def _render_message_with_links(self, parent, text):
        """Render a message with clickable file/folder paths and markdown support."""
        import re
        
        # Pattern to match paths
        path_pattern = r'((?:/[\w.-]+)+/[\w.-]+|[A-Z]:\\[\w\\.-]+(?:\\[\w.-]+)*)'
        
        # Check if text has paths
        has_paths = bool(re.search(path_pattern, text))
        
        if not has_paths:
            # No paths - use simple textbox with wrapping
            lines = text.count('\n') + 1
            estimated_height = max(60, lines * 22 + 30)
            
            msg_textbox = ctk.CTkTextbox(
                parent, font=FONT_AI,
                text_color=TEXT_PRIMARY, fg_color="transparent",
                wrap="word", activate_scrollbars=False,
                height=estimated_height
            )
            msg_textbox.insert("1.0", text)
            msg_textbox.configure(state="disabled")
            msg_textbox.pack(fill="x", padx=16, pady=12)
            return
        
        # Has paths - split and render with clickable links
        # Create a single container frame for the entire message
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", padx=16, pady=12)
        
        # Split text into segments (text and paths)
        parts = re.split(path_pattern, text)
        
        # Build the message with inline clickable paths
        for part in parts:
            if not part:
                continue
            if re.match(path_pattern, part):
                # This is a path - make it clickable
                path_lbl = ctk.CTkLabel(
                    container, text=part, font=("Segoe UI", 14, "underline"),
                    text_color="#10a37f", cursor="hand2",
                    wraplength=500
                )
                path_lbl.pack(fill="x", anchor="w", pady=2)
                path_lbl.bind("<Button-1>", lambda e, p=part: self._open_path(p))
                _Tooltip.bind(path_lbl, f"Click to open: {part}")
            else:
                # Regular text - split by newlines and create labels with wrapping
                lines = part.split('\n')
                for line in lines:
                    if line:
                        # Check for markdown bold: **text**
                        bold_pattern = r'\*\*(.+?)\*\*'
                        if re.search(bold_pattern, line):
                            # Split by bold markers and create mixed labels
                            segments = re.split(bold_pattern, line)
                            for i, segment in enumerate(segments):
                                if not segment:
                                    continue
                                if i % 2 == 1:  # Bold segment
                                    txt_lbl = ctk.CTkLabel(
                                        container, text=segment, font=("Segoe UI", 14, "bold"),
                                        text_color=TEXT_PRIMARY, anchor="w",
                                        wraplength=500, justify="left"
                                    )
                                else:  # Regular segment
                                    txt_lbl = ctk.CTkLabel(
                                        container, text=segment, font=FONT_AI,
                                        text_color=TEXT_PRIMARY, anchor="w",
                                        wraplength=500, justify="left"
                                    )
                                txt_lbl.pack(fill="x", anchor="w", pady=1)
                        else:
                            txt_lbl = ctk.CTkLabel(
                                container, text=line, font=FONT_AI,
                                text_color=TEXT_PRIMARY, anchor="w",
                                wraplength=500, justify="left"
                            )
                            txt_lbl.pack(fill="x", anchor="w", pady=1)

    def _open_path(self, path):
        """Open a file or folder path using the system's default handler."""
        import subprocess
        import platform
        from pathlib import Path
        
        path = path.strip()
        path_obj = Path(path).expanduser()
        
        if not path_obj.exists():
            messagebox.showinfo("Path Not Found", f"The path does not exist:\n{path}")
            return
        
        try:
            current_os = platform.system()
            if current_os == "Darwin":
                subprocess.Popen(["open", str(path_obj)])
            elif current_os == "Windows":
                os.startfile(str(path_obj))
            else:
                subprocess.Popen(["xdg-open", str(path_obj)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open path:\n{e}")

    def _copy_to_clipboard(self, text, btn):
        """Copy message text to clipboard"""
        self.app.clipboard_clear()
        self.app.clipboard_append(text)
        # Brief visual feedback via background flash
        try:
            btn.configure(fg_color=ACCENT_LIGHT)
            self.app.after(1500, lambda: btn.configure(fg_color="transparent") if btn.winfo_exists() else None)
        except Exception:
            pass

    def _safe_btn_reset(self, btn):
        try:
            if btn.winfo_exists():
                btn.configure(image=self.icon_copy, text="")
        except Exception:
            pass

    def _toggle_feedback(self, active_btn, other_btn, feedback_type):
        """Toggle like/dislike with accent-colored icon on selection."""
        current = active_btn.cget("fg_color")
        if current == ACCENT_LIGHT:
            # Deselect
            active_btn.configure(fg_color="transparent")
        else:
            active_btn.configure(fg_color=ACCENT_LIGHT)
            other_btn.configure(fg_color="transparent")

    def _share_message(self, text):
        """Share/copy message text to clipboard (acts as share)."""
        self.app.clipboard_clear()
        self.app.clipboard_append(text)
        messagebox.showinfo("Shared", "Message copied to clipboard!")

    def _edit_user_message(self, text, row_frame):
        """Allow user to edit their message and resubmit."""
        # Replace the message bubble with an edit textbox
        try:
            for child in row_frame.winfo_children():
                child.destroy()
        except Exception:
            return

        edit_container = ctk.CTkFrame(row_frame, fg_color="transparent")
        edit_container.grid(row=0, column=0, sticky="e", padx=(60, 28))

        edit_bg = ctk.CTkFrame(
            edit_container, fg_color="#f0fdf4", corner_radius=14,
            border_width=2, border_color=ACCENT
        )
        edit_bg.pack(anchor="e")

        edit_entry = ctk.CTkTextbox(
            edit_bg, height=48, font=FONT_USER,
            fg_color="#f0fdf4", text_color=TEXT_PRIMARY,
            border_width=0, corner_radius=14, wrap="word"
        )
        edit_entry.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=(6, 6))
        edit_entry.insert("1.0", text)
        edit_entry.focus_set()

        def _restore_bubble(display_text):
            """Restore the normal bubble view without incrementing msg_row."""
            for child in row_frame.winfo_children():
                child.destroy()
            right_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            right_frame.grid(row=0, column=0, sticky="e", padx=(60, 28))
            bubble = ctk.CTkFrame(right_frame, fg_color=ACCENT, corner_radius=18)
            bubble.pack(anchor="e")
            msg_lbl = ctk.CTkLabel(
                bubble, text=display_text, font=FONT_USER,
                text_color="white", wraplength=520, justify="left"
            )
            msg_lbl.pack(padx=22, pady=12)
            icons_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
            icons_frame.pack(anchor="e", pady=(4, 0))
            cb = ctk.CTkButton(
                icons_frame, image=self.icon_copy, text="", width=28, height=28,
                fg_color="transparent", hover_color="#f0f0f0", corner_radius=6,
                command=lambda: self._copy_to_clipboard(display_text, cb)
            )
            cb.pack(side="right", padx=2)
            eb = ctk.CTkButton(
                icons_frame, image=self.icon_edit, text="", width=28, height=28,
                fg_color="transparent", hover_color="#f0f0f0", corner_radius=6,
                command=lambda: self._edit_user_message(display_text, row_frame)
            )
            eb.pack(side="right", padx=2)
            self._refresh_scroll_region()

        def _submit_edit():
            new_text = edit_entry.get("1.0", "end").strip()
            if new_text and new_text != text:
                session = self._get_active_session()
                if session:
                    for msg in reversed(session["messages"]):
                        if msg["role"] == "user" and msg["content"] == text:
                            msg["content"] = new_text
                            break
                    self._save_sessions()
            _restore_bubble(new_text if new_text else text)

        def _cancel_edit():
            _restore_bubble(text)

        # Save / Cancel buttons
        btn_frame = ctk.CTkFrame(edit_container, fg_color="transparent")
        btn_frame.pack(anchor="e", pady=(4, 0))

        ctk.CTkButton(
            btn_frame, text="Cancel", width=70, height=30,
            font=FONT_SMALL_BTN, fg_color="#e5e7eb", hover_color="#d1d5db",
            text_color="#374151", corner_radius=8,
            command=_cancel_edit
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="Save", width=70, height=30,
            font=(FONT_SMALL_BTN[0], FONT_SMALL_BTN[1], "bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=8,
            command=_submit_edit
        ).pack(side="left")

        edit_entry.bind("<Return>", lambda e: (_submit_edit(), "break"))
        edit_entry.bind("<Escape>", lambda e: _cancel_edit())

    def _show_thinking(self):
        self._hide_welcome()
        row_frame = ctk.CTkFrame(self.msg_frame, fg_color="transparent")
        row_frame.grid(row=self.msg_row, column=0, sticky="ew", pady=(14, 0))
        row_frame.grid_columnconfigure(0, weight=1)
        self.msg_row += 1

        # Animated thinking indicator
        self._thinking_indicator = ThinkingIndicator(row_frame)
        self._thinking_indicator.frame.grid(row=0, column=0, sticky="w", padx=(28, 60))
        self._thinking_indicator.start()

        self._thinking_card = row_frame
        self._refresh_scroll_region()
        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _remove_thinking(self):
        if self._thinking_indicator:
            self._thinking_indicator.stop()
            self._thinking_indicator = None
        if self._thinking_card:
            self._thinking_card.destroy()
            self.msg_row -= 1
            self._thinking_card = None
            self._refresh_scroll_region()

    # -----------------------------------------------------------------
    #  Command Execution
    # -----------------------------------------------------------------
    def _send_command(self, text):
        """Programmatically send a command (from suggestion chips)"""
        # Switch from welcome to chat mode
        self._hide_welcome()
        self._show_input_area(True)

        self.command_entry.delete("1.0", "end")
        self.command_entry.insert("1.0", text)
        self._execute_command()

    def _execute_command(self):
        if self.is_processing:
            return

        command = self.command_entry.get("1.0", "end").strip()
        if not command:
            return

        # Handle 'help' locally
        if command.lower() in ("help", "commands", "what can you do"):
            self._add_msg_to_session("user", command)
            self._render_user_message(command)
            self.command_entry.delete("1.0", "end")
            self._show_help()
            return

        # Check for sensitive commands (delete, remove, etc.) - show confirmation
        if self.is_sensitive_command(command):
            self._add_msg_to_session("user", command)
            self._render_user_message(command)
            self.command_entry.delete("1.0", "end")
            self._show_confirmation_dialog(command)
            return

        self.is_processing = True
        self.send_btn.configure(fg_color="#9ca3af", state="disabled")

        self._add_msg_to_session("user", command)
        self._render_user_message(command)
        self.command_entry.delete("1.0", "end")
        self._show_thinking()

        def process():
            try:
                time.sleep(0.4)
                result = process_command(command)
                self.app.after(0, lambda: self._finish_execution(result, command))
            except Exception as err:
                print(f"Command execution error: {err}")
                error_result = {
                    "intent": "error", "entity": None, "status": "failed",
                    "message": str(err), "details": None, "task_id": 0,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                self.app.after(0, lambda: self._finish_execution(error_result, command))
        
        t = threading.Thread(target=process, daemon=True)
        t.start()
        
        # Safety timeout - reset UI if command takes too long (30 seconds)
        def safety_timeout():
            if self.is_processing:
                print("Warning: Command execution timed out, resetting UI")
                self._finish_execution({
                    "intent": "error", "entity": None, "status": "failed",
                    "message": "Command timed out. Please try again.",
                    "details": None, "task_id": 0,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }, command)
        
        self.app.after(30000, safety_timeout)

    def _show_confirmation_dialog(self, command):
        """Show confirmation dialog for sensitive commands like delete."""
        details = self.get_confirmation_details(command)
        
        def on_confirm():
            """User confirmed - proceed with the command."""
            self.is_processing = True
            self.send_btn.configure(fg_color="#9ca3af", state="disabled")
            self._show_thinking()
            
            def process():
                try:
                    time.sleep(0.4)
                    result = process_command(command)
                    self.app.after(0, lambda: self._finish_execution(result, command))
                except Exception as err:
                    print(f"Command execution error: {err}")
                    error_result = {
                        "intent": "error", "entity": None, "status": "failed",
                        "message": str(err), "details": None, "task_id": 0,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    self.app.after(0, lambda: self._finish_execution(error_result, command))
            
            t = threading.Thread(target=process, daemon=True)
            t.start()
        
        def on_cancel():
            """User cancelled - show cancellation message."""
            # Reset processing state
            self.is_processing = False
            self.send_btn.configure(fg_color=ACCENT, state="normal")
            
            cancel_msg = f"Cancelled: '{command}' was not executed."
            self._add_msg_to_session("ai", cancel_msg)
            self._render_ai_message(cancel_msg)
        
        # Show the confirmation dialog
        ConfirmationDialog(self.app, command, details, on_confirm, on_cancel)

    def _finish_execution(self, result, command):
        """Finish command execution and reset UI state."""
        self._remove_thinking()
        self.is_processing = False
        self.send_btn.configure(fg_color=ACCENT, state="normal")
        
        # Ensure command entry is enabled and focused
        try:
            self.command_entry.configure(state="normal")
            self.command_entry.focus_set()
        except Exception:
            pass
        
        # Force update to ensure UI is responsive
        try:
            self.app.update_idletasks()
        except Exception:
            pass

        response = self._format_response(result, command)
        self._add_msg_to_session("ai", response)
        self._render_ai_message(response)
        self._refresh_scroll_region()
        
        # Auto-focus input after response
        try:
            self.app.after(100, lambda: self.command_entry.focus_set())
        except Exception:
            pass

    def _force_reset_ui(self):
        """Force reset UI state if it gets stuck."""
        self.is_processing = False
        self.send_btn.configure(fg_color=ACCENT, state="normal")
        try:
            self.command_entry.configure(state="normal")
            self.command_entry.focus()
        except Exception:
            pass
        self._remove_thinking()
        try:
            self.app.update_idletasks()
        except Exception:
            pass

    def _add_msg_to_session(self, role, content, timestamp=""):
        session = self._get_active_session()
        if not session:
            return
        if not timestamp:
            timestamp = datetime.now().strftime("%I:%M %p")
        session["messages"].append({
            "role": role, "content": content, "timestamp": timestamp
        })
        if role == "user" and len([m for m in session["messages"] if m["role"] == "user"]) == 1:
            # Generate a friendly title from the first message
            title = content.strip()[:50] if len(content) > 50 else content.strip()
            # Capitalize first letter
            if title:
                title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()
            session["title"] = title
        self._save_sessions()
        self._refresh_sidebar()

    # -----------------------------------------------------------------
    #  Header Actions
    # -----------------------------------------------------------------
    def _show_upgrade_info(self):
        """Show upgrade/version info."""
        messagebox.showinfo(
            "AMAZON",
            "AMAZON Desktop Assistant v2.0\n\n"
            "Current Features:\n"
            "  - File & Folder Management\n"
            "  - App & Website Launcher\n"
            "  - Document Generation\n"
            "  - Web Search\n"
            "  - Project Scaffolding\n"
            "  - Natural Language Commands\n\n"
            "You are running the latest version."
        )

    def _show_settings_info(self):
        """Show settings placeholder."""
        messagebox.showinfo(
            "Settings",
            "Settings coming soon!\n\n"
            "Current Configuration:\n"
            "  - Theme: Light\n"
            "  - Language: English / Swahili\n"
            "  - Default Save: Desktop"
        )
    
    def _refresh_app(self):
        """Refresh the app - reload environment and reset state."""
        try:
            # Reinitialize environment scanner
            from system.environment_scanner import initialize_environment
            initialize_environment(force_rescan=True)
            
            # Show success message
            messagebox.showinfo(
                "Refresh Complete",
                "AMAZON has been refreshed!\n\n"
                "  - Environment rescanned\n"
                "  - Apps and drives updated\n"
                "  - Ready for new commands"
            )
        except Exception as e:
            messagebox.showerror(
                "Refresh Error",
                f"Failed to refresh: {str(e)}"
            )

    # -----------------------------------------------------------------
    #  Safety Checks
    # -----------------------------------------------------------------
    def is_sensitive_command(self, command):
        """Check if command requires confirmation before execution."""
        sensitive = [
            # Delete/remove actions
            "delete", "remove", "erase", "destroy", "discard",
            "wipe", "purge", "eliminate", "get rid of",
            # System actions
            "format", "overwrite", "clear", "drop",
            "shutdown", "restart", "reboot", "log off", "log out",
            # Trash/bin actions
            "empty trash", "empty recycle", "empty bin",
            "clear trash", "clear recycle", "clear bin",
            "move to trash", "send to trash", "move to bin",
        ]
        cmd_lower = command.lower()
        return any(w in cmd_lower for w in sensitive)

    def get_confirmation_details(self, command):
        """Get specific warning message based on command type."""
        cmd_lower = command.lower()
        
        # Delete/remove actions
        if any(w in cmd_lower for w in ["delete", "remove", "erase", "destroy", "discard", "wipe", "purge", "eliminate", "get rid of"]):
            # Check if it's a file or folder
            if "folder" in cmd_lower or "directory" in cmd_lower:
                return "This will permanently delete the folder and ALL its contents. This cannot be undone."
            elif "file" in cmd_lower:
                return "This will permanently delete the file. This cannot be undone."
            else:
                return "This will permanently delete the item. This cannot be undone."
        
        # Trash/bin actions
        if any(w in cmd_lower for w in ["empty trash", "empty recycle", "empty bin", "clear trash", "clear recycle", "clear bin"]):
            return "This will permanently delete ALL items in trash/bin. This cannot be undone."
        
        if any(w in cmd_lower for w in ["move to trash", "send to trash", "move to bin"]):
            return "This will move the item to trash/bin."
        
        # System actions
        if "format" in cmd_lower:
            return "WARNING: This will format the drive. ALL DATA WILL BE LOST."
        if "overwrite" in cmd_lower:
            return "This will overwrite existing files. Previous content will be lost."
        if "shutdown" in cmd_lower or "restart" in cmd_lower or "reboot" in cmd_lower:
            return "This will affect your computer's state. Make sure to save your work."
        if "log off" in cmd_lower or "log out" in cmd_lower:
            return "This will log you out of your session. Make sure to save your work."
        
        return "This action may have irreversible effects. Are you sure?"

    # -----------------------------------------------------------------
    #  Response Formatting (ChatGPT-style)
    # -----------------------------------------------------------------
    def _format_response(self, result, command=None):
        intent = result.get("intent") or "unknown"
        entity = result.get("entity") or ""
        status = result.get("status") or "failed"
        message = result.get("message") or ""
        details = result.get("details")

        lines = []

        if status == "unsupported":
            return message

        # Compound commands: just show the combined message
        if intent == "compound":
            return message

        # Status indicators
        status_icons = {
            "success": "✅",
            "failed": "❌",
            "processing": "⏳",
        }
        status_icon = status_icons.get(status, "️")

        if status == "success":
            action_map = {
                "create_folder": "📁 Folder Created",
                "create_file": "📄 File Created",
                "delete_folder": "🗑️ Folder Deleted",
                "delete_file": "🗑️ File Deleted",
                "rename_file": "✏️ File Renamed",
                "rename_folder": "️ Folder Renamed",
                "move_file": "📦 File Moved",
                "move_folder": "📦 Folder Moved",
                "copy_file": "📋 File Copied",
                "copy_folder": "📋 Folder Copied",
                "open_file": "📂 File Opened",
                "open_folder": " Folder Opened",
                "read_file": "📖 File Read",
                "open_website": "🌐 Website Opened",
                "open_app": "🚀 Application Opened",
                "close_app": "⏹️ Application Closed",
                "generate_document": "📝 Document Generated",
                "search_web": " Web Search Results",
                "search_file": "🔍 File Search Results",
                "search_folder": "🔍 Folder Search Results",
                "search_app": "🔍 App Search Results",
                "run_command": " Command Executed",
                "list_processes": "📊 Running Processes",
                "create_project": "🛠️ Project Created",
                "greeting": " Welcome",
                "system_info": " System Information",
                "empty_trash": "️ Trash Emptied",
                "analyze_document": "📊 Document Analyzed",
            }
            action = action_map.get(intent, f"✅ {intent.replace('_', ' ').title()}")
            
            if intent == "greeting":
                lines.append(message)
            elif intent == "generate_document":
                # For documents, show clean info from details
                if isinstance(details, dict) and details.get("saved_path"):
                    saved_path = details["saved_path"]
                    topic = details.get("topic", entity)
                    filename = Path(saved_path).name
                    lines.append(f"{action}")
                    lines.append("")
                    lines.append(f"**Topic:** {topic}")
                    lines.append(f"**Saved as:** `{filename}`")
                    lines.append(f"**Location:** `{Path(saved_path).parent}`")
                else:
                    lines.append(f"{action}")
                    if entity:
                        lines.append(f"**Document:** {entity}")
                    if message:
                        lines.append("")
                        lines.append(message)
            elif intent in ("search_file", "search_folder"):
                lines.append(f"{action}")
                lines.append("")
                if message:
                    lines.append(message)
            elif intent == "system_info":
                # System info is already formatted in the handler
                lines.append(message)
            else:
                lines.append(f"{action}")
                lines.append("")
                if entity:
                    lines.append(f"**Item:** {entity}")
                if message and not message.startswith(("Sure", "Of course", "Happy", "No problem", "Absolutely", "You got", "Done", "All set", "Perfect", "Great", "Awesome")):
                    lines.append("")
                    lines.append(message)
        else:
            # Failed status
            lines.append(f"{status_icon} **Task Failed**")
            lines.append("")
            lines.append(message)
            # Add helpful suggestion
            if "couldn't find" in message.lower() or "not found" in message.lower():
                lines.append("")
                lines.append("💡 **Tip:** Try checking the spelling or use 'find' to search for it.")

        # Show file list if available (for ALL intents - find_anything, search_file, delete_file, etc.)
        if isinstance(details, dict) and details.get("file_list"):
            lines.append("")
            lines.append("**Files Found:**")
            for f in details["file_list"][:10]:
                # Show full path without backticks so it becomes clickable
                lines.append(f"  • {f}")

        # Additional details
        if isinstance(details, dict):
            # Only add path if it's not already in the message - show without backticks for clickable
            if details.get("path") and details["path"] not in message:
                lines.append("")
                lines.append(f"**Path:** {details['path']}")  # No backticks - makes it clickable
            if details.get("destination"):
                lines.append(f"**Destination:** {details['destination']}")  # No backticks
            # Handle nested details (like file_list) properly
            if details.get("details"):
                nested = details["details"]
                if isinstance(nested, dict):
                    # If it has file_list, it's already handled above
                    if not nested.get("file_list"):
                        # Show other details nicely
                        for key, value in nested.items():
                            if key != "file_list":  # Skip file_list, already shown
                                lines.append(f"**{key.title()}:** {value}")
                elif isinstance(nested, list):
                    lines.append("")
                    lines.append("**Details:**")
                    for item in nested[:10]:
                        lines.append(f"  • {item}")
                else:
                    lines.append(f"**Details:** {nested}")
        elif isinstance(details, list):
            if details:
                lines.append("")
                lines.append(f"**Items Found:** {len(details)}")
                for item in details[:10]:
                    lines.append(f"  • {item}")

        return "\n".join(lines)

    def _show_help(self):
        help_text = (
            "Available Commands:\n\n"
            "Applications\n"
            "  open [app]          - Open app (chrome, vscode, word, etc.)\n"
            "  close [app]         - Close application\n"
            "  list processes      - Show running processes\n"
            "  run command [cmd]   - Execute terminal command\n\n"
            "Files & Folders\n"
            "  create file [name]        - Create file on Desktop\n"
            "  create folder [name]      - Create folder on Desktop\n"
            "  delete file [name]        - Delete file\n"
            "  delete folder [name]      - Delete folder\n"
            "  rename file [old] to [new]\n"
            "  rename folder [old] to [new]\n"
            "  move file [src] to [dst]\n"
            "  copy file [src] to [dst]\n"
            "  open file [name] / open folder [name]\n"
            "  read file [name]          - Read file contents\n\n"
            "Documents\n"
            "  generate document [name.docx]\n"
            "  generate report [name.pdf]\n"
            "  create report [name.xlsx]\n\n"
            "Web & Search\n"
            "  open [website]            - Open website\n"
            "  search [query]            - Google search\n"
            "  find [file]               - Search local files\n"
            "  search app [name]         - Find installed app\n\n"
            "Developer\n"
            "  create react project [name]\n"
            "  create python project [name]\n"
            "  create angular project [name]\n"
            "  create laravel project [name]\n"
            "  create node project [name]\n\n"
            "Tips:\n"
            "  - Files are created on your Desktop by default\n"
            "  - Use 'in documents' or 'on downloads' to specify location\n"
            "  - Type naturally, I'll understand!"
        )
        self._add_msg_to_session("ai", help_text)
        self._render_ai_message(help_text)

    # -----------------------------------------------------------------
    #  Run
    # -----------------------------------------------------------------
    def run(self):
        self.app.mainloop()


if __name__ == "__main__":
    app = AMAZONAI()
    app.run()
