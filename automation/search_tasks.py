import os
import socket
import urllib.parse
import urllib.request
import json
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
    search_paths = [Path(os.environ.get("ProgramFiles", "C:/Program Files")), Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))]
    matches = []
    try:
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
        return _build_result("Search Applications", query or "all", "success", f"Found {len(matches)} installed application(s)", "Application", extra=matches)
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
