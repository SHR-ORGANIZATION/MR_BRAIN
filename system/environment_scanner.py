"""
Environment Discovery Engine for NOVA AI
Automatically discovers drives, applications, folders, and builds a local knowledge base.
"""
import os
import sys
import json
import winreg
import psutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Cache file location
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
CACHE_FILE = CACHE_DIR / "environment_index.json"


class EnvironmentScanner:
    """Scans the local environment to build a knowledge base of drives, apps, and folders."""
    
    def __init__(self):
        self.drives: List[str] = []
        self.apps: Dict[str, Dict[str, Any]] = {}
        self.folders: Dict[str, str] = {}
        self.user_projects: List[str] = []
        self.last_scan: Optional[str] = None
        
    def discover_drives(self) -> List[str]:
        """Discover all available drives on the system."""
        drives = []
        try:
            partitions = psutil.disk_partitions(all=True)
            for p in partitions:
                drive = p.mountpoint.rstrip('\\')
                if drive and drive not in drives:
                    drives.append(drive)
        except Exception as e:
            print(f"[EnvironmentScanner] Error discovering drives: {e}")
            # Fallback: check common drive letters
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
        
        self.drives = sorted(drives)
        return self.drives
    
    def discover_apps_from_registry(self) -> Dict[str, Dict[str, Any]]:
        """Discover installed applications from Windows Registry."""
        apps = {}
        
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
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
                                    install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                    display_icon, _ = winreg.QueryValueEx(subkey, "DisplayIcon")
                                    
                                    if name and name.strip():
                                        name_lower = name.lower().strip()
                                        apps[name_lower] = {
                                            "display_name": name.strip(),
                                            "install_location": install_location.strip() if install_location else "",
                                            "icon": display_icon.strip() if display_icon else "",
                                            "source": "registry",
                                        }
                                except (FileNotFoundError, OSError):
                                    pass
                            i += 1
                        except OSError:
                            break
            except Exception as e:
                print(f"[EnvironmentScanner] Error reading registry {path}: {e}")
        
        return apps
    
    def discover_apps_from_start_menu(self) -> Dict[str, Dict[str, Any]]:
        """Discover applications from Start Menu shortcuts."""
        apps = {}
        
        start_menu_paths = [
            Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "Microsoft\\Windows\\Start Menu\\Programs",
            Path(os.environ.get("APPDATA", "")) / "Microsoft\\Windows\\Start Menu\\Programs",
        ]
        
        for start_menu in start_menu_paths:
            if not start_menu.exists():
                continue
            try:
                for shortcut in start_menu.rglob("*.lnk"):
                    try:
                        name = shortcut.stem
                        if name and name.strip():
                            name_lower = name.lower().strip()
                            apps[name_lower] = {
                                "display_name": name.strip(),
                                "install_location": str(shortcut.parent),
                                "icon": str(shortcut),
                                "source": "start_menu",
                            }
                    except Exception:
                        pass
            except Exception as e:
                print(f"[EnvironmentScanner] Error scanning start menu: {e}")
        
        return apps
    
    def discover_apps_from_program_files(self) -> Dict[str, Dict[str, Any]]:
        """Discover applications from Program Files directories."""
        apps = {}
        
        program_files_dirs = [
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")),
        ]
        
        for pf_dir in program_files_dirs:
            if not pf_dir.exists():
                continue
            try:
                for item in pf_dir.iterdir():
                    if item.is_dir():
                        name = item.name
                        if name and not name.startswith("."):
                            name_lower = name.lower().strip()
                            # Look for .exe files in the directory
                            exe_files = list(item.glob("*.exe"))
                            exe_path = str(exe_files[0]) if exe_files else ""
                            
                            apps[name_lower] = {
                                "display_name": name.strip(),
                                "install_location": str(item),
                                "icon": exe_path,
                                "source": "program_files",
                            }
            except Exception as e:
                print(f"[EnvironmentScanner] Error scanning program files: {e}")
        
        return apps
    
    def discover_apps(self) -> Dict[str, Dict[str, Any]]:
        """Discover all installed applications from multiple sources."""
        apps = {}
        
        # Collect from all sources
        registry_apps = self.discover_apps_from_registry()
        start_menu_apps = self.discover_apps_from_start_menu()
        program_files_apps = self.discover_apps_from_program_files()
        
        # Merge: prefer registry > start_menu > program_files
        for source in [program_files_apps, start_menu_apps, registry_apps]:
            for name, info in source.items():
                if name not in apps:
                    apps[name] = info
                else:
                    # Update with more specific info if available
                    if info.get("install_location") and not apps[name].get("install_location"):
                        apps[name]["install_location"] = info["install_location"]
                    if info.get("icon") and not apps[name].get("icon"):
                        apps[name]["icon"] = info["icon"]
        
        # Add aliases for common apps
        aliases = {
            "vscode": ["visual studio code", "code"],
            "chrome": ["google chrome"],
            "brave": ["brave browser"],
            "firefox": ["mozilla firefox"],
            "edge": ["microsoft edge"],
            "vlc": ["vlc media player", "videolan"],
            "docker": ["docker desktop"],
            "postman": ["postman runtime"],
            "cursor": ["cursor editor"],
            "android studio": ["android studio"],
            "visual studio": ["visual studio"],
            "pycharm": ["pycharm community", "pycharm professional"],
            "intellij": ["intellij idea"],
            "word": ["microsoft word"],
            "excel": ["microsoft excel"],
            "powerpoint": ["microsoft powerpoint"],
            "teams": ["microsoft teams"],
            "slack": ["slack"],
            "discord": ["discord"],
            "spotify": ["spotify"],
            "whatsapp": ["whatsapp"],
            "telegram": ["telegram desktop"],
            "zoom": ["zoom"],
            "obs": ["obs studio"],
            "blender": ["blender"],
            "figma": ["figma"],
            "canva": ["canva"],
            "winrar": ["winrar"],
            "7zip": ["7-zip", "7zip"],
            "notepad": ["notepad", "notepad++"],
            "calculator": ["calculator"],
            "paint": ["paint"],
            "file explorer": ["file explorer", "explorer"],
            "task manager": ["task manager"],
            "cmd": ["command prompt", "cmd"],
            "powershell": ["powershell"],
            "git": ["git"],
            "node": ["node.js"],
            "npm": ["npm"],
            "python": ["python"],
            "mysql": ["mysql"],
            "mongodb": ["mongodb"],
            "postgresql": ["postgresql"],
            "pgadmin": ["pgadmin 4"],
            "xampp": ["xampp"],
            "wamp": ["wamp server"],
            "anydesk": ["anydesk"],
            "putty": ["putty"],
            "wireshark": ["wireshark"],
            "steam": ["steam"],
            "epic games": ["epic games launcher"],
            "netflix": ["netflix"],
            "youtube": ["youtube"],
            "gmail": ["gmail"],
            "outlook": ["microsoft outlook"],
            "github": ["github desktop"],
            "reddit": ["reddit"],
            "twitch": ["twitch"],
            "linkedin": ["linkedin"],
            "chatgpt": ["chatgpt"],
            "claude": ["claude"],
            "gemini": ["gemini"],
            "tiktok": ["tiktok"],
            "instagram": ["instagram"],
            "facebook": ["facebook"],
            "twitter": ["twitter"],
            "bing": ["bing"],
            "wikipedia": ["wikipedia"],
            "amazon": ["amazon"],
            "ebay": ["ebay"],
            "skype": ["skype"],
        }
        
        # Create alias mappings
        for canonical, alias_list in aliases.items():
            for alias in alias_list:
                alias_lower = alias.lower()
                if alias_lower in apps:
                    apps[canonical] = apps[alias_lower]
                    break
        
        self.apps = apps
        return apps
    
    def discover_common_folders(self) -> Dict[str, str]:
        """Discover common user folders."""
        folders = {}
        
        home = Path.home()
        common_folders = {
            "desktop": home / "Desktop",
            "documents": home / "Documents",
            "downloads": home / "Downloads",
            "pictures": home / "Pictures",
            "music": home / "Music",
            "videos": home / "Videos",
        }
        
        for name, path in common_folders.items():
            if path.exists() and path.is_dir():
                folders[name] = str(path)
        
        # Also scan for additional user-created folders in common locations
        scan_locations = [home, home / "Desktop", home / "Documents"]
        for scan_dir in scan_locations:
            if not scan_dir.exists():
                continue
            try:
                for item in scan_dir.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        folder_name = item.name.lower()
                        if folder_name not in folders:
                            folders[folder_name] = str(item)
            except Exception:
                pass
        
        self.folders = folders
        return folders
    
    def discover_user_projects(self) -> List[str]:
        """Discover user project folders."""
        projects = []
        
        home = Path.home()
        project_indicators = ["project", "projects", "workspace", "repo", "repos", "code", "coding"]
        
        scan_locations = [home, home / "Desktop", home / "Documents"]
        
        for scan_dir in scan_locations:
            if not scan_dir.exists():
                continue
            try:
                for item in scan_dir.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        name_lower = item.name.lower()
                        # Check if folder name suggests it's a project
                        if any(indicator in name_lower for indicator in project_indicators):
                            projects.append(str(item))
                        # Check if it contains project indicators (like .git, package.json, etc.)
                        elif any((item / indicator).exists() for indicator in [".git", "package.json", "requirements.txt", "pom.xml", "build.gradle"]):
                            projects.append(str(item))
            except Exception:
                pass
        
        self.user_projects = sorted(projects)
        return self.user_projects
    
    def build_environment_index(self, force_rescan: bool = False) -> Dict[str, Any]:
        """Build complete environment index. Uses cache if available and not forced to rescan."""
        
        # Try to load from cache first
        if not force_rescan and CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    # Check if cache is from today
                    cache_date = cache_data.get("scan_date", "")
                    if cache_date == datetime.now().strftime("%Y-%m-%d"):
                        self.drives = cache_data.get("drives", [])
                        self.apps = cache_data.get("apps", {})
                        self.folders = cache_data.get("folders", {})
                        self.user_projects = cache_data.get("user_projects", [])
                        self.last_scan = cache_date
                        return self.get_index()
            except Exception as e:
                print(f"[EnvironmentScanner] Error loading cache: {e}")
        
        # Perform fresh scan
        print("[EnvironmentScanner] Scanning environment...")
        self.discover_drives()
        self.discover_apps()
        self.discover_common_folders()
        self.discover_user_projects()
        self.last_scan = datetime.now().strftime("%Y-%m-%d")
        
        # Save to cache
        self._save_cache()
        
        return self.get_index()
    
    def _save_cache(self):
        """Save environment index to cache file."""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_data = {
                "scan_date": self.last_scan,
                "drives": self.drives,
                "apps": self.apps,
                "folders": self.folders,
                "user_projects": self.user_projects,
            }
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[EnvironmentScanner] Error saving cache: {e}")
    
    def get_index(self) -> Dict[str, Any]:
        """Get the current environment index."""
        return {
            "drives": self.drives,
            "apps": self.apps,
            "folders": self.folders,
            "user_projects": self.user_projects,
            "last_scan": self.last_scan,
            "stats": {
                "total_drives": len(self.drives),
                "total_apps": len(self.apps),
                "total_folders": len(self.folders),
                "total_projects": len(self.user_projects),
            }
        }
    
    def get_app_info(self, app_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific application."""
        name_lower = app_name.lower().strip()
        return self.apps.get(name_lower)
    
    def find_app(self, query: str) -> Optional[Dict[str, Any]]:
        """Find an app by partial name match."""
        query_lower = query.lower().strip()
        
        # Exact match first
        if query_lower in self.apps:
            return self.apps[query_lower]
        
        # Partial match
        for name, info in self.apps.items():
            if query_lower in name or name in query_lower:
                return info
        
        # Fuzzy match
        from difflib import get_close_matches
        matches = get_close_matches(query_lower, self.apps.keys(), n=1, cutoff=0.6)
        if matches:
            return self.apps[matches[0]]
        
        return None
    
    def get_folder_path(self, folder_name: str) -> Optional[str]:
        """Get the full path of a folder by name."""
        name_lower = folder_name.lower().strip()
        return self.folders.get(name_lower)
    
    def find_folder(self, query: str) -> Optional[str]:
        """Find a folder by partial name match."""
        query_lower = query.lower().strip()
        
        # Exact match
        if query_lower in self.folders:
            return self.folders[query_lower]
        
        # Partial match
        for name, path in self.folders.items():
            if query_lower in name or name in query_lower:
                return path
        
        # Fuzzy match
        from difflib import get_close_matches
        matches = get_close_matches(query_lower, self.folders.keys(), n=1, cutoff=0.6)
        if matches:
            return self.folders[matches[0]]
        
        return None


# Global scanner instance
_scanner = EnvironmentScanner()


def get_scanner() -> EnvironmentScanner:
    """Get the global environment scanner instance."""
    return _scanner


def initialize_environment(force_rescan: bool = False) -> Dict[str, Any]:
    """Initialize the environment index. Call this at NOVA startup."""
    scanner = get_scanner()
    return scanner.build_environment_index(force_rescan=force_rescan)


def get_available_drives() -> List[str]:
    """Get list of available drives."""
    scanner = get_scanner()
    if not scanner.drives:
        scanner.discover_drives()
    return scanner.drives


def get_installed_apps() -> Dict[str, Dict[str, Any]]:
    """Get dictionary of installed applications."""
    scanner = get_scanner()
    if not scanner.apps:
        scanner.discover_apps()
    return scanner.apps


def find_app(query: str) -> Optional[Dict[str, Any]]:
    """Find an application by name."""
    scanner = get_scanner()
    if not scanner.apps:
        scanner.discover_apps()
    return scanner.find_app(query)


def get_common_folders() -> Dict[str, str]:
    """Get dictionary of common folders."""
    scanner = get_scanner()
    if not scanner.folders:
        scanner.discover_common_folders()
    return scanner.folders


def find_folder(query: str) -> Optional[str]:
    """Find a folder by name."""
    scanner = get_scanner()
    if not scanner.folders:
        scanner.discover_common_folders()
    return scanner.find_folder(query)


def get_user_projects() -> List[str]:
    """Get list of user project folders."""
    scanner = get_scanner()
    if not scanner.user_projects:
        scanner.discover_user_projects()
    return scanner.user_projects


def get_environment_stats() -> Dict[str, int]:
    """Get statistics about the environment."""
    scanner = get_scanner()
    index = scanner.get_index()
    return index.get("stats", {})


if __name__ == "__main__":
    # Test the environment scanner
    print("=" * 60)
    print("NOVA Environment Discovery Engine - Test")
    print("=" * 60)
    
    scanner = EnvironmentScanner()
    
    print("\n[1] Discovering Drives...")
    drives = scanner.discover_drives()
    print(f"Found {len(drives)} drives: {drives}")
    
    print("\n[2] Discovering Applications...")
    apps = scanner.discover_apps()
    print(f"Found {len(apps)} applications")
    print("Sample apps:", list(apps.keys())[:10])
    
    print("\n[3] Discovering Common Folders...")
    folders = scanner.discover_common_folders()
    print(f"Found {len(folders)} folders")
    for name, path in list(folders.items())[:5]:
        print(f"  {name}: {path}")
    
    print("\n[4] Discovering User Projects...")
    projects = scanner.discover_user_projects()
    print(f"Found {len(projects)} projects")
    for proj in projects[:5]:
        print(f"  {proj}")
    
    print("\n[5] Building Environment Index...")
    index = scanner.build_environment_index()
    print(f"Index built successfully")
    print(f"Stats: {index['stats']}")
    
    print("\n[6] Testing App Search...")
    test_queries = ["brave", "vscode", "chrome", "docker", "postman"]
    for query in test_queries:
        result = scanner.find_app(query)
        if result:
            print(f"  '{query}' -> {result['display_name']} ({result.get('install_location', 'N/A')})")
        else:
            print(f"  '{query}' -> NOT FOUND")
    
    print("\n" + "=" * 60)
    print("Discovery Complete!")
    print("=" * 60)