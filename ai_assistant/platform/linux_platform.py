"""
AMAZON AI - Linux Platform
Linux-specific implementations.
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List

from ai_assistant.platform.base_platform import BasePlatform

logger = logging.getLogger(__name__)


class LinuxPlatform(BasePlatform):
    """Linux platform implementation."""
    
    @property
    def name(self) -> str:
        return "Linux"
    
    @property
    def is_supported(self) -> bool:
        import platform
        return platform.system() == "Linux"
    
    def get_user_dirs(self) -> Dict[str, Path]:
        """Get standard Linux user directories."""
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
        """Open file with default application using xdg-open."""
        try:
            subprocess.Popen(["xdg-open", path])
            return True
        except Exception as e:
            logger.error(f"Failed to open file: {e}")
            return False
    
    def open_folder(self, path: str) -> bool:
        """Open folder in file manager."""
        try:
            subprocess.Popen(["xdg-open", path])
            return True
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")
            return False
    
    def get_installed_apps(self) -> List[Dict[str, str]]:
        """Get installed applications from .desktop files."""
        apps = []
        desktop_dirs = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            Path.home() / ".local/share/applications",
        ]
        
        for desktop_dir in desktop_dirs:
            if desktop_dir.exists():
                for item in desktop_dir.glob("*.desktop"):
                    try:
                        with open(item, 'r') as f:
                            content = f.read()
                            name = ""
                            exec_cmd = ""
                            for line in content.split('\n'):
                                if line.startswith("Name="):
                                    name = line[5:].strip()
                                elif line.startswith("Exec="):
                                    exec_cmd = line[5:].strip()
                            if name:
                                apps.append({
                                    "name": name,
                                    "path": exec_cmd,
                                    "type": "application"
                                })
                    except Exception:
                        pass
        
        return apps
    
    def launch_app(self, app_name: str) -> bool:
        """Launch an application on Linux."""
        try:
            # Try direct execution
            subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            # Try finding in installed apps
            apps = self.get_installed_apps()
            for app in apps:
                if app_name.lower() in app["name"].lower():
                    try:
                        exec_cmd = app["path"].split()[0]  # Get first word (command)
                        subprocess.Popen([exec_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return True
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Failed to launch app: {e}")
        return False
    
    def close_app(self, app_name: str) -> bool:
        """Close an application using pkill."""
        try:
            subprocess.run(["pkill", "-f", app_name], timeout=10)
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
        """Get Linux system information."""
        import platform
        import psutil
        
        info = {
            "os": "Linux",
            "os_version": platform.release(),
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
        """Empty the Linux Trash."""
        try:
            trash_path = Path.home() / ".local/share/Trash"
            if trash_path.exists():
                import shutil
                files_path = trash_path / "files"
                info_path = trash_path / "info"
                if files_path.exists():
                    shutil.rmtree(files_path, ignore_errors=True)
                if info_path.exists():
                    shutil.rmtree(info_path, ignore_errors=True)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to empty trash: {e}")
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
        return os.environ.get("SHELL", "/bin/bash").split("/")[-1]
