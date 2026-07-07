import subprocess
import webbrowser
import os
import sys
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


def open_application(app_name):
    app_name = app_name.lower().strip()

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

    # Try discovered apps from environment scanner
    scanner = get_scanner()
    app_info = scanner.find_app(app_name)
    
    if app_info:
        install_location = app_info.get("install_location", "")
        display_name = app_info.get("display_name", app_name)
        
        # Strategy 1: If we have an install location with an exe, try to find and launch it
        if install_location:
            # Look for .exe files in the install location
            try:
                exe_files = list(Path(install_location).rglob("*.exe"))
                if exe_files:
                    # Prefer the main executable (same name as folder or app)
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
            
            # Strategy 2: Try to launch from start menu shortcut
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
        
        # Strategy 3: Try direct command (for apps in PATH like code, notepad, etc.)
        direct_commands = {
            "vscode": "code",
            "visual studio code": "code",
            "notepad": "notepad",
            "calculator": "calc",
            "paint": "mspaint",
            "file explorer": "explorer",
            "explorer": "explorer",
            "task manager": "Taskmgr",
            "cmd": "cmd",
            "command prompt": "cmd",
            "powershell": "powershell",
        }
        direct_cmd = direct_commands.get(app_name)
        if direct_cmd:
            try:
                subprocess.Popen(direct_cmd, shell=True)
                return {
                    "status": "success",
                    "message": f"Opened {display_name}",
                    "action": "Open Application",
                    "path": direct_cmd,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            except Exception:
                pass
        
        # Strategy 4: Try using where command as fallback
        try:
            result = subprocess.run(
                ["where", app_name],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                exe_path = result.stdout.strip().split("\n")[0].strip()
                subprocess.Popen(exe_path, shell=True)
                return {
                    "status": "success",
                    "message": f"Opened {display_name}",
                    "action": "Open Application",
                    "path": exe_path,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
        except Exception:
            pass
        
        return {
            "status": "failed",
            "message": f"Found '{display_name}' in system but could not launch it automatically.",
            "action": "Open Application",
            "path": install_location or app_info.get("icon", ""),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    return {
        "status": "failed",
        "message": f"{app_name} is not recognized. The application may not be installed or may not have been discovered.",
        "action": "Open Application",
        "path": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def close_application(app_name):
    """Close an application by name. Falls back to searching running processes."""
    app_name = app_name.lower().strip()
    exe_name = TERMINATE_PROCESSES.get(app_name)

    # Try environment scanner for discovered apps
    if not exe_name:
        exe_name = _get_app_exe_name(app_name)

    # Fallback: search running processes for a matching exe
    if not exe_name:
        exe_name = _find_running_exe(app_name)

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


def _find_running_exe(app_name):
    """Search running processes for a matching exe name."""
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
                # Match: app_name.exe, or app_name contained in exe name
                if exe.lower() == app_lower + ".exe" or app_lower in exe.lower().replace(".exe", ""):
                    return exe
    except Exception:
        pass
    return None


def kill_process_by_pid(pid):
    """Kill a process by its PID number."""
    try:
        pid_int = int(pid)
        result = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid_int)],
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
    """Get a filtered list of user-facing running applications (skip system processes)."""
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
                # Get base exe name (without extension, no spaces) for filtering
                exe_base = name_lower.replace(".exe", "").replace(" ", "").replace(".", "").replace("_", "")
                # Skip system/service processes
                if exe_base in _SYSTEM_EXES or name_lower in _SYSTEM_EXES:
                    continue
                # Skip installer temp processes and known service patterns
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


def list_running_processes():
    """List currently running processes."""
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
                "processes": processes[:50],  # Limit to top 50
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