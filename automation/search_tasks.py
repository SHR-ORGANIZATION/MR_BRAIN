import os
import socket
import urllib.parse
import urllib.request
import json
import platform
from pathlib import Path
from datetime import datetime


def _build_result(action, path, status, message, item_type="Search", extra=None):
    return {
        "action": action,
        "name": Path(path).name if path else "",
        "path": str(Path(path).expanduser().resolve()) if path else "",
        "type": item_type,
        "status": status,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "details": extra,
    }


def _has_internet(timeout=2):
    try:
        socket.create_connection(("8.8.8.8", 53), timeout)
        return True
    except OSError:
        return False


def _try_fetch_json(url, timeout=8):
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None


def search_file(query, root=None, max_results=50):
    root_path = Path(root or Path.cwd()).expanduser()
    matches = []
    try:
        if not root_path.exists():
            return _build_result("Search File", root_path, "failed", "Search root does not exist", "File", extra=[])
        for item in root_path.rglob("*"):
            if item.is_file() and query.lower() in item.name.lower():
                matches.append(str(item.resolve()))
                if len(matches) >= max_results:
                    break
        return _build_result("Search File", root_path, "success", f"Found {len(matches)} file(s) matching '{query}'", "File", extra=matches)
    except Exception as e:
        return _build_result("Search File", root_path, "failed", str(e), "File", extra=[])


def search_folder(query, root=None, max_results=50):
    root_path = Path(root or Path.cwd()).expanduser()
    matches = []
    try:
        if not root_path.exists():
            return _build_result("Search Folder", root_path, "failed", "Search root does not exist", "Folder", extra=[])
        for item in root_path.rglob("*"):
            if item.is_dir() and query.lower() in item.name.lower():
                matches.append(str(item.resolve()))
                if len(matches) >= max_results:
                    break
        return _build_result("Search Folder", root_path, "success", f"Found {len(matches)} folder(s) matching '{query}'", "Folder", extra=matches)
    except Exception as e:
        return _build_result("Search Folder", root_path, "failed", str(e), "Folder", extra=[])


def search_applications(query=None, max_results=50):
    """Search for installed applications (cross-platform)."""
    current_os = platform.system()
    matches = []
    
    try:
        if current_os == "Darwin":
            # macOS: search /Applications and ~/Applications
            search_paths = [Path("/Applications"), Path("/System/Applications"), Path.home() / "Applications"]
            for search_path in search_paths:
                if not search_path.exists():
                    continue
                for item in search_path.rglob("*.app"):
                    if query is None or query.lower() in item.stem.lower():
                        matches.append(str(item.resolve()))
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
        
        elif current_os == "Windows":
            # Windows: search Program Files
            search_paths = [
                Path(os.environ.get("ProgramFiles", "C:/Program Files")),
                Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
            ]
            for root in search_paths:
                if not root.exists():
                    continue
                for item in root.rglob("*.exe"):
                    if query is None or query.lower() in item.stem.lower():
                        matches.append(str(item.resolve()))
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
        else:
            # Linux: search /usr/share/applications and /usr/bin
            desktop_paths = [Path("/usr/share/applications"), Path("/usr/local/share/applications"),
                             Path.home() / ".local/share/applications"]
            for root in desktop_paths:
                if not root.exists():
                    continue
                for item in root.glob("*.desktop"):
                    if query is None or query.lower() in item.stem.lower():
                        matches.append(str(item.resolve()))
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
            
            # Also search /usr/bin for command-line apps
            bin_paths = [Path("/usr/bin"), Path("/usr/local/bin")]
            for bin_path in bin_paths:
                if not bin_path.exists():
                    continue
                for item in bin_path.iterdir():
                    if item.is_file() and os.access(str(item), os.X_OK):
                        if query is None or query.lower() in item.name.lower():
                            matches.append(str(item.resolve()))
                            if len(matches) >= max_results:
                                break
                if len(matches) >= max_results:
                    break
        
        return _build_result("Search Applications", query or "all", "success",
                            f"Found {len(matches)} installed application(s)", "Application", extra=matches)
    except Exception as e:
        return _build_result("Search Applications", query or "all", "failed", str(e), "Application", extra=[])


def research_topic(topic):
    if not topic:
        return ""
    if not _has_internet():
        return ""
    query = urllib.parse.quote(topic)
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1&skip_disambig=1"
    data = _try_fetch_json(url)
    if not data:
        return ""
    abstract = data.get("AbstractText") or ""
    if abstract:
        return abstract
    related = data.get("RelatedTopics") or []
    if isinstance(related, list) and related:
        first = related[0]
        if isinstance(first, dict):
            return first.get("Text", "")
    return ""
