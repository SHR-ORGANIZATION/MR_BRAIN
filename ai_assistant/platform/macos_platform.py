"""
AMAZON AI - macOS Platform
macOS-specific implementations.
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List

from ai_assistant.platform.base_platform import BasePlatform

logger = logging.getLogger(__name__)


class MacOSPlatform(BasePlatform):
    """macOS platform implementation."""
    
    @property
    def name(self) -> str:
        return "macOS"
    
    @property
    def is_supported(self) -> bool:
        import platform
        return platform.system() == "Darwin"
    
    def get_user_dirs(self) -> Dict[str, Path]:
        """Get standard macOS user directories."""
        home = Path.home()
        return {
            "desktop": home / "Desktop",
            "documents": home / "Documents",
            "downloads": home / "Downloads",
            "pictures": home / "Pictures",
            "music": home / "Music",
            "videos": home / "Videos",
            "applications": Path("/Applications"),
            "user_applications": home / "Applications",
        }
    
    def open_file_with_default(self, path: str) -> bool:
        """Open file with default application using 'open' command."""
        try:
            subprocess.Popen(["open", path])
            return True
        except Exception as e:
            logger.error(f"Failed to open file: {e}")
            return False
    
    def open_folder(self, path: str) -> bool:
        """Open folder in Finder."""
        try:
            subprocess.Popen(["open", "-R", path])
            return True
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")
            return False
    
    def get_installed_apps(self) -> List[Dict[str, str]]:
        """Get installed applications from /Applications."""
        apps = []
        app_dirs = [Path("/Applications"), Path.home() / "Applications"]
        
        for app_dir in app_dirs:
            if app_dir.exists():
                for item in app_dir.iterdir():
                    if item.suffix == ".app":
                        apps.append({
                            "name": item.stem,
                            "path": str(item),
                            "type": "application"
                        })
        
        return apps
    
    def launch_app(self, app_name: str) -> bool:
        """Launch an application using 'open -a'."""
        try:
            # Try direct app name first
            subprocess.Popen(["open", "-a", app_name])
            return True
        except Exception:
            # Try finding in /Applications
            app_dirs = [Path("/Applications"), Path.home() / "Applications"]
            for app_dir in app_dirs:
                if app_dir.exists():
                    for item in app_dir.iterdir():
                        if item.suffix == ".app" and app_name.lower() in item.stem.lower():
                            try:
                                subprocess.Popen(["open", str(item)])
                                return True
                            except Exception:
                                continue
        return False
    
    def close_app(self, app_name: str) -> bool:
        """Close an application using AppleScript."""
        try:
            script = f'tell application "{app_name}" to quit'
            subprocess.run(["osascript", "-e", script], timeout=10)
            return True
        except Exception as e:
            logger.error(f"Failed to close app: {e}")
            return False
    
    def get_running_apps(self) -> List[Dict[str, Any]]:
        """Get running applications using psutil."""
        try:
            import psutil
            apps = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    info = proc.info
                    apps.append({
                        "pid": info['pid'],
                        "name": info['name']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return apps
        except Exception as e:
            logger.error(f"Failed to get running apps: {e}")
            return []
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get macOS system information."""
        import platform
        import psutil
        
        info = {
            "os": "macOS",
            "os_version": platform.mac_ver()[0],
            "architecture": platform.machine(),
            "hostname": platform.node(),
        }
        
        # CPU info
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            info["cpu"] = result.stdout.strip()
        except Exception:
            info["cpu"] = platform.processor() or "Unknown"
        
        info["cpu_cores"] = psutil.cpu_count(logical=True)
        
        # Memory info
        ram = psutil.virtual_memory()
        info["ram_total_gb"] = round(ram.total / (1024**3), 2)
        info["ram_available_gb"] = round(ram.available / (1024**3), 2)
        
        return info
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information."""
        import psutil
        return {
            "cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "percent": psutil.cpu_percent(interval=0.5),
        }
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information."""
        import psutil
        ram = psutil.virtual_memory()
        return {
            "total_gb": round(ram.total / (1024**3), 2),
            "available_gb": round(ram.available / (1024**3), 2),
            "used_gb": round(ram.used / (1024**3), 2),
            "percent": ram.percent
        }
    
    def empty_trash(self) -> bool:
        """Empty the macOS Trash."""
        try:
            # Use AppleScript to empty trash
            script = 'tell application "Finder" to empty trash'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to empty trash: {e}")
            # Fallback: manually delete trash contents
            try:
                trash_path = Path.home() / ".Trash"
                if trash_path.exists():
                    for item in trash_path.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            import shutil
                            shutil.rmtree(item, ignore_errors=True)
                    return True
            except Exception as e2:
                logger.error(f"Fallback trash empty failed: {e2}")
            return False
    
    def run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Run a shell command."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_shell_type(self) -> str:
        """Get the default shell type."""
        return os.environ.get("SHELL", "/bin/zsh").split("/")[-1]
