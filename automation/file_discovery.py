"""
AMAZON AI - File Discovery Intelligence (Type A: Metadata Search)
Finds files based on filename patterns, extensions, dates, and locations.
No AI/embeddings — pure filesystem intelligence.
"""
import os
from pathlib import Path
from datetime import datetime, timedelta


# Directories to search (ordered by priority)
_SEARCH_DIRS = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.home() / "Pictures",
    Path.home() / "Videos",
    Path.home() / "Music",
]

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
    "desktop", "documents", "downloads", "pictures", "videos", "music",
    "__pycache__", ".git", "node_modules", ".vscode", ".idea",
    "venv", "env", ".venv", "temp", "tmp",
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
        # Fallback: search filesystem if index is missing or no results
        if not computer_results:
            try:
                from pathlib import Path
                from datetime import datetime
                
                q_lower = q.lower()
                q_words = [w for w in q_lower.split() if len(w) >= 2]  # Filter short words
                
                # Search in common user directories first (faster)
                search_dirs = [
                    Path.home() / "Desktop",
                    Path.home() / "Documents",
                    Path.home() / "Downloads",
                    Path.home() / "Pictures",
                ]
                
                # Then search all drives if needed
                try:
                    from system.environment_scanner import get_scanner
                    scanner = get_scanner()
                    drives = scanner.discover_drives()
                    for drive in drives:
                        drive_path = Path(drive)
                        if drive_path.exists() and drive_path not in search_dirs:
                            search_dirs.append(drive_path)
                except Exception:
                    pass
                
                # Search with smart matching
                max_results = 15
                max_items_per_dir = 1000  # Limit per directory
                
                for search_dir in search_dirs:
                    if len(computer_results) >= max_results:
                        break
                    if not search_dir.exists() or not search_dir.is_dir():
                        continue
                    
                    items_checked = 0
                    try:
                        for item in search_dir.rglob("*"):
                            if len(computer_results) >= max_results or items_checked >= max_items_per_dir:
                                break
                            items_checked += 1
                            try:
                                if not item.exists():
                                    continue
                                name_lower = item.name.lower()
                                # Smart matching: check if query is in name OR any word matches
                                matches = False
                                if q_lower in name_lower:
                                    matches = True
                                elif q_words:
                                    # Check if all significant words are in the name
                                    if all(w in name_lower for w in q_words):
                                        matches = True
                                    # Or if any word matches and it's a significant word (len >= 4)
                                    elif any(w in name_lower for w in q_words if len(w) >= 4):
                                        matches = True
                                
                                if matches:
                                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                                    computer_results.append({
                                        "name": item.name,
                                        "path": str(item.resolve()),
                                        "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                                        "type": "folder" if item.is_dir() else "file",
                                    })
                            except (PermissionError, OSError):
                                continue
                    except (PermissionError, OSError):
                        continue
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
        # No exact matches - try fuzzy/partial matching
        try:
            from difflib import SequenceMatcher
            fuzzy_matches = []
            q_words = q_lower.split()
            for drive in drives:
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
                            if not item.exists():
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
                                        "drive": drive,
                                        "type": "folder" if item.is_dir() else "file",
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
