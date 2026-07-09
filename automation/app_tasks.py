import subprocess
import webbrowser
import os
import sys
import platform
from datetime import datetime
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.environment_scanner import find_app, get_scanner

WEB_APPS = {
    "tiktok": "https://www.tiktok.com",
    "youtube": "https://www.youtube.com",
    "spotify": "https://open.spotify.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://x.com",
    "whatsapp": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "netflix": "https://www.netflix.com",
    "discord": "https://discord.com/app",
    "slack": "https://app.slack.com",
    "zoom": "https://zoom.us/join",
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "github": "https://github.com",
    "reddit": "https://www.reddit.com",
    "twitch": "https://www.twitch.tv",
    "linkedin": "https://www.linkedin.com",
    "google": "https://www.google.com",
    "bing": "https://www.bing.com",
    "wikipedia": "https://www.wikipedia.org",
    "amazon": "https://www.amazon.com",
    "ebay": "https://www.ebay.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com",
}

TERMINATE_PROCESSES = {
    "chrome": "chrome.exe",
    "notepad": "notepad.exe",
    "vscode": "Code.exe",
    "calculator": "Calculator.exe",
    "paint": "mspaint.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "task manager": "Taskmgr.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
}


# macOS app name mapping (friendly name -> .app bundle name)
MACOS_APP_NAMES = {
    "chrome": "Google Chrome",
    "firefox": "Firefox",
    "safari": "Safari",
    "edge": "Microsoft Edge",
    "notepad": "TextEdit",
    "textedit": "TextEdit",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "calculator": "Calculator",
    "paint": "Preview",
    "preview": "Preview",
    "terminal": "Terminal",
    "finder": "Finder",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "outlook": "Microsoft Outlook",
    "teams": "Microsoft Teams",
    "discord": "Discord",
    "slack": "Slack",
    "spotify": "Spotify",
    "vlc": "VLC",
    "zoom": "zoom.us",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "docker": "Docker",
    "pgadmin": "pgAdmin 4",
    "android studio": "Android Studio",
    "intellij": "IntelliJ IDEA",
    "pycharm": "PyCharm",
    "eclipse": "Eclipse",
    "postman": "Postman",
    "obs": "OBS",
    "blender": "Blender",
    "figma": "Figma",
    "canva": "Canva",
    "steam": "Steam",
    # Design & graphics apps
    "corel draw": "CorelDRAW",
    "coreldraw": "CorelDRAW",
    "photoshop": "Adobe Photoshop",
    "illustrator": "Adobe Illustrator",
    "indesign": "Adobe InDesign",
    "lightroom": "Adobe Lightroom",
    "after effects": "Adobe After Effects",
    "premiere": "Adobe Premiere Pro",
    "premiere pro": "Adobe Premiere Pro",
    "sketch": "Sketch",
    "affinity photo": "Affinity Photo",
    "affinity designer": "Affinity Designer",
    "affinity publisher": "Affinity Publisher",
    # Productivity apps
    "onenote": "Microsoft OneNote",
    "publisher": "Microsoft Publisher",
    "access": "Microsoft Access",
    "visio": "Microsoft Visio",
    "project": "Microsoft Project",
    "notes": "Notes",
    "reminders": "Reminders",
    "calendar": "Calendar",
    "maps": "Maps",
    "photos": "Photos",
    "music": "Music",
    "podcasts": "Podcasts",
    "tv": "TV",
    "app store": "App Store",
    "system preferences": "System Preferences",
    "system settings": "System Settings",
    "activity monitor": "Activity Monitor",
    "disk utility": "Disk Utility",
    "time machine": "Time Machine",
    "siri": "Siri",
    "facetime": "FaceTime",
    "face time": "FaceTime",
    "imessage": "Messages",
    "messages": "Messages",
    "mail": "Mail",
    "quicktime": "QuickTime Player",
    "quicktime player": "QuickTime Player",
    "automator": "Automator",
    "script editor": "Script Editor",
    "console": "Console",
    "keychain": "Keychain Access",
    "keychain access": "Keychain Access",
}

# macOS process names for closing (used with killall/quit)
MACOS_CLOSE_NAMES = {
    "chrome": "Google Chrome",
    "firefox": "Firefox",
    "safari": "Safari",
    "edge": "Microsoft Edge",
    "notepad": "TextEdit",
    "textedit": "TextEdit",
    "vscode": "Code",
    "vs code": "Code",
    "visual studio code": "Code",
    "code": "Code",
    "calculator": "Calculator",
    "terminal": "Terminal",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "outlook": "Microsoft Outlook",
    "teams": "Microsoft Teams",
    "discord": "Discord",
    "slack": "Slack",
    "spotify": "Spotify",
    "vlc": "VLC",
    "zoom": "zoom.us",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "docker": "Docker",
    # Design & graphics apps
    "corel draw": "CorelDRAW",
    "coreldraw": "CorelDRAW",
    "photoshop": "Adobe Photoshop",
    "illustrator": "Adobe Illustrator",
    "indesign": "Adobe InDesign",
    "lightroom": "Adobe Lightroom",
    "after effects": "Adobe After Effects",
    "premiere": "Adobe Premiere Pro",
    "premiere pro": "Adobe Premiere Pro",
    "sketch": "Sketch",
    "blender": "Blender",
    "figma": "Figma",
    "canva": "Canva",
    # Productivity apps
    "onenote": "Microsoft OneNote",
    "notes": "Notes",
    "reminders": "Reminders",
    "calendar": "Calendar",
    "maps": "Maps",
    "photos": "Photos",
    "music": "Music",
    "facetime": "FaceTime",
    "face time": "FaceTime",
    "messages": "Messages",
    "mail": "Mail",
    "quicktime": "QuickTime Player",
    "quicktime player": "QuickTime Player",
}


def _get_learned_apps():
    """Load auto-learned app names from learning directory."""
    import json
    learned_apps_file = Path(__file__).resolve().parent.parent / "learning" / "learned_apps.json"
    learned_apps = {}
    
    try:
        if learned_apps_file.exists():
            with open(learned_apps_file, "r", encoding="utf-8") as f:
                learned_apps = json.load(f)
    except Exception:
        pass
    
    return learned_apps


def open_application(app_name):
    app_name = app_name.lower().strip()
    current_os = platform.system()
    
    # Check learned apps first (auto-learned names)
    learned_apps = _get_learned_apps()
    if app_name in learned_apps:
        # Use the learned app name
        app_name = learned_apps[app_name].get("display_name", app_name).lower()

    # Check web apps first (opened in browser)
    if app_name in WEB_APPS:
        try:
            webbrowser.open(WEB_APPS[app_name])
            return {
                "status": "success",
                "message": f"Opened {app_name} in your browser",
                "action": "Open Web App",
                "path": WEB_APPS[app_name],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": str(e),
                "action": "Open Web App",
                "path": WEB_APPS.get(app_name, ""),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    # === macOS ===
    if current_os == "Darwin":
        return _open_app_macos(app_name)

    # === Windows ===
    if current_os == "Windows":
        return _open_app_windows(app_name)

    # === Linux ===
    return _open_app_linux(app_name)


def _open_app_macos(app_name):
    """Open an application on macOS."""
    # Get the macOS app name from mapping
    mac_app = MACOS_APP_NAMES.get(app_name, app_name)
    
    # Try 'open -a' command first (fastest method)
    try:
        result = subprocess.run(["open", "-a", mac_app], capture_output=True, text=True, timeout=8)
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Opened {mac_app}",
                "action": "Open Application",
                "path": mac_app,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
    
    # Try to find .app bundle in /Applications (limited depth for speed)
    search_paths = [Path("/Applications"), Path("/System/Applications"), Path.home() / "Applications"]
    for search_path in search_paths:
        if not search_path.exists():
            continue
        # Look for .app bundle (limited depth for performance)
        try:
            for app_bundle in search_path.glob("*.app"):
                if app_name in app_bundle.stem.lower() or mac_app.lower() in app_bundle.stem.lower():
                    try:
                        subprocess.Popen(["open", str(app_bundle)])
                        return {
                            "status": "success",
                            "message": f"Opened {app_bundle.stem}",
                            "action": "Open Application",
                            "path": str(app_bundle),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    except Exception:
                        pass
            # Also check one level deep for nested apps
            for app_bundle in search_path.glob("*/*.app"):
                if app_name in app_bundle.stem.lower() or mac_app.lower() in app_bundle.stem.lower():
                    try:
                        subprocess.Popen(["open", str(app_bundle)])
                        return {
                            "status": "success",
                            "message": f"Opened {app_bundle.stem}",
                            "action": "Open Application",
                            "path": str(app_bundle),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    except Exception:
                        pass
        except Exception:
            pass
    
    # Try 'which' for command-line apps
    try:
        result = subprocess.run(["which", app_name], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            exe_path = result.stdout.strip()
            subprocess.Popen([exe_path])
            return {
                "status": "success",
                "message": f"Opened {app_name}",
                "action": "Open Application",
                "path": exe_path,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    except Exception:
        pass
    
    # Build helpful error message with suggestions
    suggestions = []
    if mac_app != app_name:
        suggestions.append(f"Try using the full name: '{mac_app}'")
    suggestions.append("Make sure the app is installed in your Applications folder")
    
    return {
        "status": "failed",
        "message": f"Could not find or open '{app_name}'. {' '.join(suggestions)}",
        "action": "Open Application",
        "path": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _open_app_windows(app_name):
    """Open an application on Windows."""
    # Try discovered apps from environment scanner
    try:
        scanner = get_scanner()
        app_info = scanner.find_app(app_name)
        
        if app_info:
            install_location = app_info.get("install_location", "")
            display_name = app_info.get("display_name", app_name)
            
            if install_location:
                try:
                    exe_files = list(Path(install_location).rglob("*.exe"))
                    if exe_files:
                        main_exe = None
                        for exe in exe_files:
                            exe_name = exe.stem.lower()
                            app_lower = app_name.lower().replace(" ", "").replace("-", "").replace("_", "")
                            if app_lower in exe_name or exe_name in app_lower:
                                main_exe = exe
                                break
                        if not main_exe and exe_files:
                            main_exe = exe_files[0]
                        
                        if main_exe:
                            subprocess.Popen(str(main_exe), shell=True)
                            return {
                                "status": "success",
                                "message": f"Opened {display_name}",
                                "action": "Open Application",
                                "path": str(main_exe),
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }
                except Exception:
                    pass
                
                try:
                    icon_path = app_info.get("icon", "")
                    if icon_path and icon_path.endswith(".lnk"):
                        os.startfile(icon_path)
                        return {
                            "status": "success",
                            "message": f"Opened {display_name}",
                            "action": "Open Application",
                            "path": icon_path,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                except Exception:
                    pass
    except Exception:
        pass
    
    # Try direct command
    direct_commands = {
        "vscode": "code", "visual studio code": "code",
        "notepad": "notepad", "calculator": "calc",
        "paint": "mspaint", "file explorer": "explorer",
        "explorer": "explorer", "task manager": "Taskmgr",
        "cmd": "cmd", "command prompt": "cmd",
        "powershell": "powershell",
    }
    direct_cmd = direct_commands.get(app_name)
    if direct_cmd:
        try:
            subprocess.Popen(direct_cmd, shell=True)
            return {
                "status": "success",
                "message": f"Opened {app_name}",
                "action": "Open Application",
                "path": direct_cmd,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception:
            pass
    
    # Try 'where' command
    try:
        result = subprocess.run(["where", app_name], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            exe_path = result.stdout.strip().split("\n")[0].strip()
            subprocess.Popen(exe_path, shell=True)
            return {
                "status": "success",
                "message": f"Opened {app_name}",
                "action": "Open Application",
                "path": exe_path,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    except Exception:
        pass
    
    return {
        "status": "failed",
        "message": f"{app_name} is not recognized. The application may not be installed.",
        "action": "Open Application",
        "path": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _open_app_linux(app_name):
    """Open an application on Linux."""
    # Try 'which' for command-line apps
    try:
        result = subprocess.run(["which", app_name], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            exe_path = result.stdout.strip()
            subprocess.Popen([exe_path])
            return {
                "status": "success",
                "message": f"Opened {app_name}",
                "action": "Open Application",
                "path": exe_path,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    except Exception:
        pass
    
    # Try xdg-open with .desktop file
    try:
        result = subprocess.run(["gtk-launch", app_name], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Opened {app_name}",
                "action": "Open Application",
                "path": app_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    except Exception:
        pass
    
    return {
        "status": "failed",
        "message": f"Could not find or open '{app_name}'. Make sure it's installed.",
        "action": "Open Application",
        "path": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def close_application(app_name):
    """Close an application by name (cross-platform)."""
    app_name = app_name.lower().strip()
    current_os = platform.system()
    
    if current_os == "Darwin":
        return _close_app_macos(app_name)
    elif current_os == "Windows":
        return _close_app_windows(app_name)
    else:
        return _close_app_linux(app_name)


def _close_app_macos(app_name):
    """Close an application on macOS."""
    # Get macOS app name
    mac_app = MACOS_CLOSE_NAMES.get(app_name, app_name)
    
    # Try AppleScript to quit gracefully
    try:
        result = subprocess.run(
            ["osascript", "-e", f'tell application "{mac_app}" to quit'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Closed {app_name}",
                "action": "Close Application",
                "path": mac_app,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    except Exception:
        pass
    
    # Try killall as fallback
    try:
        result = subprocess.run(
            ["killall", mac_app],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Closed {app_name}",
                "action": "Close Application",
                "path": mac_app,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    except Exception:
        pass
    
    # Try pkill
    try:
        result = subprocess.run(
            ["pkill", "-f", app_name],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Closed {app_name}",
                "action": "Close Application",
                "path": app_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    except Exception:
        pass
    
    return {
        "status": "failed",
        "message": f"Application '{app_name}' is not running or cannot be found.",
        "action": "Close Application",
        "path": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _close_app_windows(app_name):
    """Close an application on Windows."""
    exe_name = TERMINATE_PROCESSES.get(app_name)
    
    if not exe_name:
        exe_name = _get_app_exe_name(app_name)
    
    if not exe_name:
        exe_name = _find_running_exe_windows(app_name)
    
    if not exe_name:
        return {
            "status": "failed",
            "message": f"Application '{app_name}' is not running or cannot be found.",
            "action": "Close Application",
            "path": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", exe_name],
            check=False, capture_output=True, text=True
        )
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Closed {app_name}",
                "action": "Close Application",
                "path": exe_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        return {
            "status": "failed",
            "message": f"Could not close '{app_name}'. It may not be running.",
            "action": "Close Application",
            "path": exe_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": str(e),
            "action": "Close Application",
            "path": exe_name or "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def _close_app_linux(app_name):
    """Close an application on Linux."""
    # Try pkill
    try:
        result = subprocess.run(
            ["pkill", "-f", app_name],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Closed {app_name}",
                "action": "Close Application",
                "path": app_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    except Exception:
        pass
    
    # Try killall
    try:
        result = subprocess.run(
            ["killall", app_name],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Closed {app_name}",
                "action": "Close Application",
                "path": app_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
    except Exception:
        pass
    
    return {
        "status": "failed",
        "message": f"Application '{app_name}' is not running or cannot be found.",
        "action": "Close Application",
        "path": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _get_app_exe_name(app_name):
    """Get the executable name for an application using environment scanner."""
    scanner = get_scanner()
    app_info = scanner.find_app(app_name)
    if app_info:
        # Try to determine exe name from display name
        display_name = app_info.get("display_name", app_name)
        # Common patterns
        exe_name = display_name.lower().replace(" ", "").replace("-", "") + ".exe"
        # Special cases
        special_cases = {
            "visual studio code": "Code.exe",
            "google chrome": "chrome.exe",
            "microsoft edge": "msedge.exe",
            "mozilla firefox": "firefox.exe",
            "brave browser": "brave.exe",
            "vlc media player": "vlc.exe",
            "docker desktop": "Docker Desktop.exe",
            "postman runtime": "Postman.exe",
            "cursor editor": "Cursor.exe",
            "discord": "Discord.exe",
            "slack": "Slack.exe",
            "zoom": "Zoom.exe",
            "spotify": "Spotify.exe",
            "whatsapp": "WhatsApp.exe",
            "telegram desktop": "Telegram.exe",
            "microsoft teams": "Teams.exe",
            "microsoft word": "WINWORD.EXE",
            "microsoft excel": "EXCEL.EXE",
            "microsoft powerpoint": "POWERPNT.EXE",
            "microsoft outlook": "OUTLOOK.EXE",
        }
        display_lower = display_name.lower()
        for key, exe in special_cases.items():
            if key in display_lower:
                return exe
        return exe_name
    return None


def _find_running_exe_windows(app_name):
    """Search running processes for a matching exe name (Windows)."""
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None
        app_lower = app_name.lower()
        for line in result.stdout.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) >= 1:
                exe = parts[0].strip('"')
                if exe.lower() == app_lower + ".exe" or app_lower in exe.lower().replace(".exe", ""):
                    return exe
    except Exception:
        pass
    return None


def kill_process_by_pid(pid):
    """Kill a process by its PID number (cross-platform)."""
    try:
        pid_int = int(pid)
        current_os = platform.system()
        
        if current_os == "Windows":
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid_int)],
                check=False, capture_output=True, text=True
            )
        else:
            # macOS / Linux: use kill command
            result = subprocess.run(
                ["kill", "-9", str(pid_int)],
                check=False, capture_output=True, text=True
            )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": f"Killed process with PID {pid_int}",
                "action": "Kill Process",
                "path": str(pid_int),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        return {
            "status": "failed",
            "message": f"Could not kill PID {pid_int}. Process may not exist.",
            "action": "Kill Process",
            "path": str(pid_int),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except ValueError:
        return {
            "status": "failed",
            "message": f"Invalid PID: '{pid}'. Please provide a number.",
            "action": "Kill Process",
            "path": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": str(e),
            "action": "Kill Process",
            "path": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


# System/service exe names to skip (normalized: lowercase, no dots/spaces/underscores)
_SYSTEM_EXES = {
    # Core Windows
    "system", "svchost", "csrss", "lsass", "services",
    "wininit", "winlogon", "smss", "dwm", "explorer",
    "sihost", "taskhostw", "ctfmon", "fontdrvhost",
    "lsaiso", "runtimebroker", "searchhost", "shellexperiencehost",
    "startmenuexperiencehost", "textinputhost", "widgets",
    "systemsettings", "msedge", "securityhealthsystray",
    "conhost", "dllhost", "spoolsv", "wudfhost",
    "systemidleprocess", "registry", "backgroundtaskhost",
    # Windows services
    "mpdefendercoreservice", "msmpeng", "searchindexer", "unsecapp",
    "wmiprvse", "wmiregistrationservice", "dashost", "lsm", "lms",
    "wlanext", "hidmonitorsvc", "officeclicktorun", "jhiservice",
    "memorycompression", "securityhealthservice",
    # Driver/hardware
    "igfxcuiservice", "apoint", "apmsgfwd", "apremote", "wavessyssvc64",
    "rtkaudioservice64", "ravbg64", "esifuf", "pgctl", "hidfind",
    "apntex", "igfxem", "aggregatorhost", "audiodg", "nissrv",
    "wavessvc64", "rtkngui64", "setpoint", "khalmnpr",
    # Intel
    "intelcphdcpsvc", "intelcphecisvc", "iastoricon",
    # Edge/webview
    "msedgewebview2", "eoaexperiences",
    # Misc services
    "delltrusteddeviceservice", "oneappigccwinservice",
    "presentationfontcache", "searchapp", "httpd",
    "iastordatamgrsvc", "useroobebroker", "sdxhelper",
    "lockapp", "imsctadn", "comppkgsrv", "openconsole",
    "mocusocoreworker", "msdtc", "videoui", "applicationframehost",
    "onedrive", "onedrivesyncservice", "cortana", "tasklist",
    # iTop
    "itopvoicy", "itopvoicyaudio", "ivcvoiceplugin", "driverbooster",
}


def get_user_running_apps():
    """Get a filtered list of user-facing running applications (cross-platform)."""
    current_os = platform.system()
    
    if current_os == "Windows":
        return _get_user_running_apps_windows()
    else:
        return _get_user_running_apps_unix()


def _get_user_running_apps_windows():
    """Get user running apps on Windows."""
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return {"status": "failed", "message": "Failed to retrieve process list",
                    "apps": [], "total": 0}

        apps = []
        seen = set()
        for line in result.stdout.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) >= 2:
                name = parts[0].strip('"')
                pid = parts[1].strip('"')
                name_lower = name.lower()
                exe_base = name_lower.replace(".exe", "").replace(" ", "").replace(".", "").replace("_", "")
                if exe_base in _SYSTEM_EXES or name_lower in _SYSTEM_EXES:
                    continue
                if any(pat in exe_base for pat in ["setupstable", "setup-stable",
                                                    "searchprotocolhost",
                                                    "searchfilterhost"]):
                    continue
                if exe_base in seen:
                    continue
                seen.add(exe_base)
                apps.append({"name": name, "pid": pid})

        return {
            "status": "success",
            "message": f"{len(apps)} application(s) running",
            "apps": apps,
            "total": len(apps),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"status": "failed", "message": str(e), "apps": [], "total": 0}


def _get_user_running_apps_unix():
    """Get user running apps on macOS/Linux."""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return {"status": "failed", "message": "Failed to retrieve process list",
                    "apps": [], "total": 0}

        apps = []
        seen = set()
        # System processes to skip
        skip_names = {"kernel", "launchd", "syslogd", "configd", "mDNSResponder",
                      "UserEventAgent", "logd", "watchdogd", "coreduetd", "powerd",
                      "diskarbitrationd", "opendirectoryd", "securityd", "security",
                      "loginwindow", "WindowServer", "Dock", "Finder", "SystemUI",
                      "Spotlight", "mds", "mds_stores", "fseventsd", "dasd",
                      "zsh", "bash", "login", "sudo", "su", "ssh", "sshd",
                      "python", "python3", "ruby", "perl", "node"}
        
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            parts = line.split(None, 10)
            if len(parts) >= 11:
                pid = parts[1]
                name = parts[10].split()[-1] if "/" in parts[10] else parts[10]
                # Get just the executable name
                exe_name = Path(name).name
                exe_lower = exe_name.lower()
                
                # Skip system processes
                if exe_lower in skip_names or exe_lower.startswith("-"):
                    continue
                # Skip if already seen
                if exe_lower in seen:
                    continue
                seen.add(exe_lower)
                apps.append({"name": exe_name, "pid": pid})

        return {
            "status": "success",
            "message": f"{len(apps)} application(s) running",
            "apps": apps[:50],  # Limit to 50
            "total": len(apps),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"status": "failed", "message": str(e), "apps": [], "total": 0}


def list_running_processes():
    """List currently running processes (cross-platform)."""
    current_os = platform.system()
    
    if current_os == "Windows":
        return _list_processes_windows()
    else:
        return _list_processes_unix()


def _list_processes_windows():
    """List processes on Windows."""
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            processes = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) >= 2:
                    name = parts[0].strip('"')
                    pid = parts[1].strip('"')
                    processes.append({"name": name, "pid": pid})

            return {
                "status": "success",
                "message": f"Found {len(processes)} running processes",
                "action": "List Processes",
                "processes": processes[:50],
                "total": len(processes),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        return {
            "status": "failed",
            "message": "Failed to retrieve process list",
            "action": "List Processes",
            "processes": [],
            "total": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": str(e),
            "action": "List Processes",
            "processes": [],
            "total": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def _list_processes_unix():
    """List processes on macOS/Linux."""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            processes = []
            for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    pid = parts[1]
                    name = parts[10].split()[-1] if "/" in parts[10] else parts[10]
                    exe_name = Path(name).name
                    if not exe_name.startswith("-"):
                        processes.append({"name": exe_name, "pid": pid})

            return {
                "status": "success",
                "message": f"Found {len(processes)} running processes",
                "action": "List Processes",
                "processes": processes[:50],
                "total": len(processes),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        return {
            "status": "failed",
            "message": "Failed to retrieve process list",
            "action": "List Processes",
            "processes": [],
            "total": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": str(e),
            "action": "List Processes",
            "processes": [],
            "total": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


# Commands that should never be executed without explicit user confirmation
DANGEROUS_COMMANDS = [
    "format", "del ", "rmdir", "rd ", "shutdown", "restart",
    "reg delete", "diskpart", "cipher", "net stop", "sc delete",
]


def run_terminal_command(command):
    """Execute a terminal command with safety checks."""
    command_lower = command.lower().strip()

    # Safety check for dangerous commands
    for dangerous in DANGEROUS_COMMANDS:
        if command_lower.startswith(dangerous):
            return {
                "status": "blocked",
                "message": f"Command '{command}' is blocked for safety. Destructive system commands require manual execution.",
                "action": "Run Command",
                "command": command,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    try:
        result = subprocess.run(
            command, shell=True,
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip() or result.stderr.strip() or "Command executed (no output)"
        return {
            "status": "success" if result.returncode == 0 else "failed",
            "message": output[:2000],  # Limit output
            "action": "Run Command",
            "command": command,
            "return_code": result.returncode,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "message": "Command timed out after 30 seconds",
            "action": "Run Command",
            "command": command,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": str(e),
            "action": "Run Command",
            "command": command,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }