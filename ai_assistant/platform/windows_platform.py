"""
AMAZON AI - Windows Platform
Windows-specific implementations.
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List

from ai_assistant.platform.base_platform import BasePlatform

logger = logging.getLogger(__name__)


class WindowsPlatform(BasePlatform):
    """Windows platform implementation."""
    
    @property
    def name(self) -> str:
        return "Windows"
    
    @property
    def is_supported(self) -> bool:
        import platform
        return platform.system() == "Windows"
    
    def get_user_dirs(self) -> Dict[str, Path]:
        """Get standard Windows user directories."""
        home = Path.home()
        return {
            "desktop": home / "Desktop",
            "documents": home / "Documents",
            "downloads": home / "Downloads",
            "pictures": home / "Pictures",
            "music": home / "Music",
            "videos": home / "Videos",
        }
    
    def open_file_with_default(self, path: str) -> bool:
        """Open file with default application using os.startfile."""
        try:
            os.startfile(path)
            return True
        except Exception as e:
            logger.error(f"Failed to open file: {e}")
            return False
    
    def open_folder(self, path: str) -> bool:
        """Open folder in Windows Explorer."""
        try:
            subprocess.Popen(["explorer", path])
            return True
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")
            return False
    
    def get_installed_apps(self) -> List[Dict[str, str]]:
        """Get installed applications from Windows Registry."""
        apps = []
        try:
            import winreg
            
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            
            for hkey, path in registry_paths:
                try:
                    with winreg.OpenKey(hkey, path) as key:
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                        install_loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                        if name and name.strip():
                                            apps.append({
                                                "name": name.strip(),
                                                "path": install_loc.strip() if install_loc else "",
                                                "type": "application"
                                            })
                                    except (FileNotFoundError, OSError):
                                        pass
                                i += 1
                            except OSError:
                                break
                except Exception as e:
                    logger.debug(f"Registry read error: {e}")
        except ImportError:
            pass
        
        return apps
    
    def launch_app(self, app_name: str) -> bool:
        """Launch an application on Windows."""
        try:
            # Try using 'start' command
            subprocess.Popen(f'start {app_name}', shell=True)
            return True
        except Exception as e:
            logger.error(f"Failed to launch app: {e}")
            return False
    
    def close_app(self, app_name: str) -> bool:
        """Close an application using taskkill."""
        try:
            subprocess.run(["taskkill", "/IM", f"{app_name}.exe", "/F"], timeout=10)
            return True
        except Exception as e:
            logger.error(f"Failed to close app: {e}")
            return False
    
    def get_running_apps(self) -> List[Dict[str, Any]]:
        """Get running applications."""
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
        """Get Windows system information."""
        import platform
        import psutil
        
        info = {
            "os": "Windows",
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "cpu_cores": psutil.cpu_count(logical=True),
        }
        
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
        """Empty the Windows Recycle Bin."""
        try:
            # Use PowerShell to empty recycle bin
            subprocess.run(
                ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                timeout=30
            )
            return True
        except Exception as e:
            logger.error(f"Failed to empty recycle bin: {e}")
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
        return "powershell"
