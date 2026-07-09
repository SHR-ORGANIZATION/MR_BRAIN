"""
AMAZON AI - File Discovery Intelligence (Type A: Metadata Search)
Finds files based on filename patterns, extensions, dates, and locations.
No AI/embeddings — pure filesystem intelligence.
Supports all drives/volumes on Windows, macOS, and Linux.
"""
import os
import platform
from pathlib import Path
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
#  Cross-platform drive/volume discovery
# ---------------------------------------------------------------------------

def get_all_drives():
    """
    Discover all available drives/volumes on the current OS.
    Returns a list of Path objects representing searchable root locations.
    """
    drives = []
    os_type = platform.system()

    try:
        if os_type == "Windows":
            # Windows: enumerate drive letters A-Z
            import string
            for letter in string.ascii_uppercase:
                drive = Path(f"{letter}:\\")
                if drive.exists():
                    drives.append(drive)
            # Also check psutil for mounted/network drives
            try:
                import psutil
                for p in psutil.disk_partitions(all=False):
                    dp = Path(p.mountpoint)
                    if dp.exists() and dp not in drives:
                        drives.append(dp)
            except ImportError:
                pass

        elif os_type == "Darwin":
            # macOS: root + /Volumes/*
            drives.append(Path("/"))
            volumes = Path("/Volumes")
            if volumes.exists():
                for vol in volumes.iterdir():
                    if vol.is_dir() and not vol.name.startswith("."):
                        drives.append(vol)

        else:
            # Linux: root + /media/* + /mnt/* + /run/media/*
            drives.append(Path("/"))
            for mount_base in [Path("/media"), Path("/mnt"), Path("/run/media")]:
                if mount_base.exists():
                    for vol in mount_base.iterdir():
                        if vol.is_dir() and not vol.name.startswith("."):
                            drives.append(vol)
    except Exception:
        # Fallback: at least search home
        drives.append(Path.home())

    return sorted(set(drives))


def get_user_dirs():
    """Get standard user home directories."""
    home = Path.home()
    dirs = []
    for name in ["Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music"]:
        d = home / name
        if d.exists():
            dirs.append(d)
    return dirs


# Directories to search (ordered by priority) — user home dirs
_SEARCH_DIRS = get_user_dirs()

# All drives available for full-computer search
_ALL_DRIVES = get_all_drives()

# Keyword groups for discovery types (FILES)
DISCOVERY_KEYWORDS = {
    "latest_assignment": [
        "assignment", "coursework", "homework", "lab", "exercise",
        "tut", "tutorial", "quiz", "exam", "test",
    ],
    "latest_proposal": [
        "proposal", "research proposal", "project proposal",
    ],
    "latest_report": [
        "report", "lab report", "annual report", "summary",
    ],
}

# Keyword groups for FOLDER discovery types
FOLDER_DISCOVERY_KEYWORDS = {
    "latest_project_folder": [
        "project", "projects", "workspace", "repo",
    ],
    "latest_assignment_folder": [
        "assignment", "coursework", "homework", "lab",
    ],
    "latest_folder": [],  # Generic: most recent folder (no keyword match)
}

# File extensions to consider as "files" (exclude system/temp files)
_VALID_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".txt", ".csv", ".json", ".xml", ".py", ".js", ".html", ".css",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
    ".mp3", ".mp4", ".avi", ".mkv", ".zip", ".rar", ".7z",
    ".md", ".rtf", ".odt", ".ods", ".odp",
}

# Temp/system file patterns to skip
_SKIP_PATTERNS = {"thumbs.db", "desktop.ini", ".ds_store", "~$"}

# System folders to skip
_SKIP_FOLDERS = {
    # Common
    "__pycache__", ".git", "node_modules", ".vscode", ".idea",
    "venv", "env", ".venv", "temp", "tmp",
    # macOS
    "system", "library", "private", "cores", "opt", "usr",
    # Windows
    "windows", "programdata", "program files", "program files (x86)",
    "$recycle.bin", "system volume information", "appdata",
    "$windows.~bt", "$windows.~ws", "recovery",
    # Linux
    "proc", "sys", "dev", "run", "snap",
}


def _is_valid_file(path: Path) -> bool:
    """Check if a file is a real user file (not temp/system)."""
    if not path.is_file():
        return False
    name_lower = path.name.lower()
    # Skip temp/system files
    for pattern in _SKIP_PATTERNS:
        if pattern in name_lower:
            return False
    # Skip hidden files
    if name_lower.startswith("."):
        return False
    # Must have a recognized extension
    if path.suffix.lower() not in _VALID_EXTENSIONS:
        return False
    return True


def _is_valid_folder(path: Path) -> bool:
    """Check if a folder is a real user folder (not system/hidden)."""
    if not path.is_dir():
        return False
    name_lower = path.name.lower()
    if name_lower in _SKIP_FOLDERS:
        return False
    if name_lower.startswith("."):
        return False
    return True


def _get_all_files(search_dirs=None, extensions=None, since=None):
    """
    Collect all valid user files from search directories.

    Args:
        search_dirs: list of Path objects to search
        extensions: optional set of extensions to filter
        since: optional datetime — only return files modified after this time

    Returns:
        list of (Path, mtime) tuples sorted by mtime descending
    """
    dirs = search_dirs or _SEARCH_DIRS
    files = []
    seen = set()

    for d in dirs:
        if not d.exists():
            continue
        try:
            for item in d.rglob("*"):
                if not _is_valid_file(item):
                    continue
                if extensions and item.suffix.lower() not in extensions:
                    continue
                # Deduplicate by resolved path
                try:
                    resolved = str(item.resolve())
                except (OSError, RuntimeError):
                    continue
                if resolved in seen:
                    continue
                seen.add(resolved)
                # Check modification time
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                except OSError:
                    continue
                if since and mtime < since:
                    continue
                files.append((item, mtime))
        except (PermissionError, OSError):
            continue

    # Sort by modification time, newest first
    files.sort(key=lambda x: x[1], reverse=True)
    return files


def _get_all_folders(search_dirs=None, since=None):
    """
    Collect all valid user folders from search directories (non-recursive: top-level only).

    Args:
        search_dirs: list of Path objects to search (default: _SEARCH_DIRS)
        since: optional datetime — only return folders modified after this time

    Returns:
        list of (Path, mtime) tuples sorted by mtime descending
    """
    dirs = search_dirs or _SEARCH_DIRS
    folders = []
    seen = set()

    for d in dirs:
        if not d.exists():
            continue
        try:
            for item in d.iterdir():  # Non-recursive: top-level only
                if not _is_valid_folder(item):
                    continue
                resolved = str(item.resolve())
                if resolved in seen:
                    continue
                seen.add(resolved)
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                except OSError:
                    continue
                if since and mtime < since:
                    continue
                folders.append((item, mtime))
        except PermissionError:
            continue

    folders.sort(key=lambda x: x[1], reverse=True)
    return folders


def _match_keywords(filename: str, keywords: list) -> bool:
    """Check if filename contains any of the keywords (case-insensitive)."""
    name_lower = filename.lower()
    for kw in keywords:
        if kw in name_lower:
            return True
    return False


# =====================================================================
#  DISCOVERY FUNCTIONS
# =====================================================================

def find_recent_files(limit=1):
    """
    Find the most recently modified files across all search directories.

    Returns:
        list of dicts: [{"name", "path", "modified", "extension"}]
    """
    files = _get_all_files()
    results = []
    for path, mtime in files[:limit]:
        results.append({
            "name": path.name,
            "path": str(path),
            "modified": mtime.strftime("%Y-%m-%d %H:%M"),
            "extension": path.suffix,
        })
    return results


def find_latest_by_keyword(discovery_type):
    """
    Find the most recent file matching a discovery type's keywords.

    Args:
        discovery_type: e.g. "latest_assignment", "latest_proposal", "latest_report"

    Returns:
        dict with file info, or None if not found
    """
    keywords = DISCOVERY_KEYWORDS.get(discovery_type, [])
    if not keywords:
        return None

    files = _get_all_files()
    for path, mtime in files:
        if _match_keywords(path.stem, keywords):
            return {
                "name": path.name,
                "path": str(path),
                "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                "extension": path.suffix,
                "discovery_type": discovery_type,
            }
    return None


def find_downloaded_files_today(extensions=None):
    """
    Find files downloaded today.

    Args:
        extensions: optional set of extensions to filter (e.g. {'.pdf'})

    Returns:
        list of dicts with file info
    """
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Focus on Downloads directory
    download_dir = [Path.home() / "Downloads"]
    files = _get_all_files(search_dirs=download_dir, extensions=extensions, since=today_start)
    results = []
    for path, mtime in files:
        results.append({
            "name": path.name,
            "path": str(path),
            "modified": mtime.strftime("%Y-%m-%d %H:%M"),
            "extension": path.suffix,
        })
    return results


def find_downloaded_pdfs_today():
    """Find PDFs downloaded today."""
    return find_downloaded_files_today(extensions={".pdf"})


# =====================================================================
#  FOLDER DISCOVERY FUNCTIONS
# =====================================================================

def find_recent_folders(limit=1):
    """
    Find the most recently modified folders across all search directories.

    Returns:
        list of dicts: [{"name", "path", "modified"}]
    """
    folders = _get_all_folders()
    results = []
    for path, mtime in folders[:limit]:
        results.append({
            "name": path.name,
            "path": str(path),
            "modified": mtime.strftime("%Y-%m-%d %H:%M"),
        })
    return results


def find_latest_folder_by_keyword(discovery_type):
    """
    Find the most recent folder matching a folder discovery type's keywords.

    Args:
        discovery_type: e.g. "latest_project_folder", "latest_assignment_folder"

    Returns:
        dict with folder info, or None if not found
    """
    keywords = FOLDER_DISCOVERY_KEYWORDS.get(discovery_type, [])
    if not keywords:
        return None

    folders = _get_all_folders()
    for path, mtime in folders:
        if _match_keywords(path.name, keywords):
            return {
                "name": path.name,
                "path": str(path),
                "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                "discovery_type": discovery_type,
            }
    return None


# =====================================================================
#  UNIFIED DISCOVERY ROUTER
# =====================================================================

def resolve_discovery(discovery_type, query=None):
    """
    Unified entry point for file and folder discovery.

    Args:
        discovery_type: one of "latest_file", "latest_assignment",
                       "latest_proposal", "latest_report", "pdfs_today",
                       "latest_folder", "latest_project_folder",
                       "latest_assignment_folder", "semantic",
                       "search_computer", "find_anywhere"
        query: search query string (used for semantic search)

    Returns:
        dict with "status", "path", "name", "item_type", "message" etc.
    """
    # --- FULL COMPUTER SEARCH (Type C) ---
    if discovery_type in ("search_computer", "find_anywhere"):
        q = query or ""
        computer_results = []
        # Try computer index first (fast)
        try:
            from automation.computer_indexer import search_files_semantic, is_index_ready
            if is_index_ready():
                computer_results = search_files_semantic(q, limit=10)
        except Exception:
            pass
        # Fallback: search filesystem across ALL drives if index is missing or no results
        if not computer_results:
            try:
                # Use universal all-drives search
                computer_results = search_all_drives(q, limit=15)
            except Exception:
                pass
        if computer_results:
            top = computer_results[0]
            lines = [f"Found {len(computer_results)} result(s) for '{q}':"]
            for r in computer_results[:5]:
                path_str = r.get('path', '')
                mod = r.get('modified', '')
                lines.append(f"  - {r['name']} ({mod}) [{path_str}]")
            return {
                "status": "found",
                "path": top["path"],
                "name": top["name"],
                "item_type": "file",
                "files": computer_results,
                "message": "\n".join(lines),
            }
        # No exact matches - try fuzzy/partial matching across all drives
        try:
            from difflib import SequenceMatcher
            fuzzy_matches = []
            q_words = q.lower().split()
            all_drives = _ALL_DRIVES if _ALL_DRIVES else [Path("/")]
            for drive in all_drives:
                if len(fuzzy_matches) >= 5:
                    break
                try:
                    drive_path = Path(drive)
                    if not drive_path.exists() or not drive_path.is_dir():
                        continue
                    for item in drive_path.rglob("*"):
                        if len(fuzzy_matches) >= 5:
                            break
                        try:
                            if not item.is_file():
                                continue
                            name_lower = item.name.lower()
                            # Check if any word in query matches partially
                            for word in q_words:
                                if len(word) >= 3 and any(SequenceMatcher(None, word, w).ratio() > 0.6 for w in name_lower.split()):
                                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                                    fuzzy_matches.append({
                                        "name": item.name,
                                        "path": str(item.resolve()),
                                        "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                                        "drive": str(drive),
                                        "type": "file",
                                    })
                                    break
                        except (PermissionError, OSError):
                            continue
                except (PermissionError, OSError):
                    continue
            if fuzzy_matches:
                top = fuzzy_matches[0]
                lines = [f"No exact matches for '{q}'. Did you mean:"]
                for r in fuzzy_matches[:5]:
                    path_str = r.get('path', '')
                    mod = r.get('modified', '')
                    lines.append(f"  - {r['name']} ({mod}) [{path_str}]")
                return {
                    "status": "not_found",
                    "path": top["path"],
                    "name": top["name"],
                    "item_type": "file",
                    "files": fuzzy_matches,
                    "message": "\n".join(lines),
                }
        except Exception:
            pass
        return {
            "status": "not_found",
            "item_type": "file",
            "message": f"No results found for '{q}'. Try building a computer index with 'index my computer' for faster search."
        }

    # --- FILE DISCOVERY ---
    if discovery_type == "latest_file":
        results = find_recent_files(limit=1)
        if results:
            f = results[0]
            return {
                "status": "found",
                "path": f["path"],
                "name": f["name"],
                "item_type": "file",
                "message": f"Found your most recent file: {f['name']} (modified {f['modified']})",
            }
        return {"status": "not_found", "item_type": "file", "message": "No files found in common directories."}

    if discovery_type in DISCOVERY_KEYWORDS:
        result = find_latest_by_keyword(discovery_type)
        if result:
            return {
                "status": "found",
                "path": result["path"],
                "name": result["name"],
                "item_type": "file",
                "message": f"Found: {result['name']} (modified {result['modified']})",
            }
        label = discovery_type.replace("latest_", "")
        return {"status": "not_found", "item_type": "file", "message": f"No {label} found in common directories."}

    if discovery_type == "pdfs_today":
        results = find_downloaded_pdfs_today()
        if results:
            return {
                "status": "found",
                "path": results[0]["path"],
                "name": results[0]["name"],
                "item_type": "file",
                "files": results,
                "message": f"Found {len(results)} PDF(s) downloaded today.",
            }
        return {"status": "not_found", "item_type": "file", "message": "No PDFs downloaded today."}

    # --- FOLDER DISCOVERY ---
    if discovery_type == "latest_folder":
        results = find_recent_folders(limit=1)
        if results:
            f = results[0]
            return {
                "status": "found",
                "path": f["path"],
                "name": f["name"],
                "item_type": "folder",
                "message": f"Found your most recent folder: {f['name']} (modified {f['modified']})",
            }
        return {"status": "not_found", "item_type": "folder", "message": "No folders found in common directories."}

    if discovery_type in FOLDER_DISCOVERY_KEYWORDS:
        result = find_latest_folder_by_keyword(discovery_type)
        if result:
            return {
                "status": "found",
                "path": result["path"],
                "name": result["name"],
                "item_type": "folder",
                "message": f"Found: {result['name']} (modified {result['modified']})",
            }
        label = discovery_type.replace("latest_", "").replace("_folder", "")
        return {"status": "not_found", "item_type": "folder", "message": f"No {label} folder found in common directories."}

    # --- SEMANTIC DISCOVERY (Type B, fallback to Type C if index missing) ---
    if discovery_type == "semantic":
        if not query:
            return {"status": "not_found", "item_type": "file", "message": "No search query provided for semantic search."}
        # First try FAISS semantic search (content-based)
        try:
            from automation.semantic_search import search as semantic_search, is_index_ready as sem_ready
            if sem_ready():
                results = semantic_search(query, top_k=5)
                if results:
                    top = results[0]
                    return {
                        "status": "found",
                        "path": top["path"],
                        "name": top["name"],
                        "item_type": "file",
                        "files": results,
                        "message": f"Semantic match: {top['name']} (score: {top['score']})",
                    }
        except Exception:
            pass
        # Fallback to computer-wide name-based search
        try:
            from automation.computer_indexer import search_files_semantic, is_index_ready as idx_ready
            if idx_ready():
                results = search_files_semantic(query, limit=5)
                if results:
                    top = results[0]
                    return {
                        "status": "found",
                        "path": top["path"],
                        "name": top["name"],
                        "item_type": "file",
                        "files": results,
                        "message": f"Found: {top['name']} ({top.get('modified','')}) [{top.get('drive','')}]",
                    }
        except Exception:
            pass
        return {"status": "not_found", "item_type": "file",
                "message": f"No files found matching '{query}'.\n\nTry:\n  - Use shorter keywords (e.g., 'azampay' instead of 'azampay document')\n  - Check if the file is on your Desktop, Documents, or Downloads\n  - Build a full index with 'index my computer' for better search"}

    return {"status": "not_found", "item_type": "file", "message": f"Unknown discovery type: {discovery_type}"}


# ---------------------------------------------------------------------------
#  Universal Search — searches across ALL drives/volumes on any OS
# ---------------------------------------------------------------------------

def search_all_drives(query, limit=20, extensions=None):
    """
    Search for files across ALL connected drives and volumes.
    Works on Windows (all drive letters), macOS (/Volumes), and Linux (/media, /mnt).
    
    Args:
        query: filename keyword(s) to search for
        limit: maximum number of results
        extensions: optional set of extensions to filter (e.g. {'.pdf', '.docx'})
    
    Returns:
        list of dicts with file info including drive name
    """
    query_lower = query.lower().strip()
    keywords = query_lower.split()
    results = []
    seen = set()
    
    # Determine which roots to search
    search_roots = _ALL_DRIVES if _ALL_DRIVES else [Path("/")]
    
    for root_drive in search_roots:
        if len(results) >= limit:
            break
        
        drive_name = root_drive.name or str(root_drive)
        
        try:
            for item in root_drive.rglob("*"):
                if len(results) >= limit:
                    break
                
                # Skip non-files
                if not item.is_file():
                    continue
                
                # Skip hidden/system files
                if item.name.startswith(".") or item.name.startswith("~$"):
                    continue
                
                # Skip temp files
                name_lower = item.name.lower()
                if any(p in name_lower for p in _SKIP_PATTERNS):
                    continue
                
                # Extension filter
                if extensions and item.suffix.lower() not in extensions:
                    continue
                
                # Keyword match (any keyword in filename)
                if not any(kw in name_lower for kw in keywords):
                    continue
                
                # Deduplicate
                try:
                    resolved = str(item.resolve())
                except (OSError, RuntimeError):
                    continue
                if resolved in seen:
                    continue
                seen.add(resolved)
                
                # Get file info
                try:
                    stat = item.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    size = stat.st_size
                except OSError:
                    continue
                
                results.append({
                    "name": item.name,
                    "path": resolved,
                    "drive": drive_name,
                    "folder": str(item.parent),
                    "extension": item.suffix,
                    "size": size,
                    "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                })
                
        except PermissionError:
            continue
        except OSError:
            continue
    
    # Sort by modification time, newest first
    results.sort(key=lambda x: x["modified"], reverse=True)
    return results[:limit]


def search_on_drive(drive_path, query, limit=20, extensions=None):
    """
    Search for files on a specific drive/volume.
    
    Args:
        drive_path: path to the drive root (e.g. "D:\\" or "/Volumes/MyDisk")
        query: filename keyword(s)
        limit: max results
        extensions: optional extension filter
    
    Returns:
        list of file info dicts
    """
    query_lower = query.lower().strip()
    keywords = query_lower.split()
    results = []
    seen = set()
    root = Path(drive_path)
    
    if not root.exists():
        return []
    
    try:
        for item in root.rglob("*"):
            if len(results) >= limit:
                break
            if not item.is_file():
                continue
            if item.name.startswith(".") or item.name.startswith("~$"):
                continue
            name_lower = item.name.lower()
            if any(p in name_lower for p in _SKIP_PATTERNS):
                continue
            if extensions and item.suffix.lower() not in extensions:
                continue
            if not any(kw in name_lower for kw in keywords):
                continue
            try:
                resolved = str(item.resolve())
            except (OSError, RuntimeError):
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                stat = item.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                size = stat.st_size
            except OSError:
                continue
            results.append({
                "name": item.name,
                "path": resolved,
                "drive": root.name or str(root),
                "folder": str(item.parent),
                "extension": item.suffix,
                "size": size,
                "modified": mtime.strftime("%Y-%m-%d %H:%M"),
            })
    except PermissionError:
        pass
    except OSError:
        pass
    
    results.sort(key=lambda x: x["modified"], reverse=True)
    return results[:limit]


def get_drive_info():
    """
    Get information about all available drives/volumes.
    
    Returns:
        list of dicts with drive name, path, and type
    """
    import platform as _platform
    drives_info = []
    
    for drive in _ALL_DRIVES:
        info = {
            "name": drive.name or str(drive),
            "path": str(drive),
        }
        
        os_type = _platform.system()
        if os_type == "Windows":
            info["type"] = "Windows Drive"
        elif os_type == "Darwin":
            if str(drive) == "/":
                info["type"] = "Macintosh HD (System)"
            else:
                info["type"] = "Volume"
        else:
            if str(drive) == "/":
                info["type"] = "Root Filesystem"
            else:
                info["type"] = "Mounted Drive"
        
        # Try to get free space
        try:
            import shutil
            usage = shutil.disk_usage(str(drive))
            info["total_gb"] = round(usage.total / (1024**3), 1)
            info["free_gb"] = round(usage.free / (1024**3), 1)
            info["used_percent"] = round((usage.used / usage.total) * 100, 1)
        except Exception:
            pass
        
        drives_info.append(info)
    
    return drives_info
