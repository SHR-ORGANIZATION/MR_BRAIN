import os
import re
import shutil
import difflib
from pathlib import Path
from datetime import datetime

DESKTOP_DIR = Path.home() / "Desktop"

# Common user directories to search when resolving bare filenames
COMMON_USER_DIRS = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.home() / "Pictures",
    Path.home() / "Music",
    Path.home() / "Videos",
]


def _build_result(action, path, status, message, item_type="File", destination=None, extra=None):
    result = {
        "action": action,
        "name": Path(path).name if path else "",
        "path": str(Path(path).expanduser().resolve()) if path else "",
        "type": item_type,
        "status": status,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if destination:
        result["destination"] = str(Path(destination).expanduser().resolve())
    if extra:
        result["details"] = extra
    return result


def _extract_drive_letter(text):
    """Extract drive letter from natural language like 'new volume(D:)', 'disk E:', 'drive F'."""
    text = text.strip().rstrip("\\").rstrip("/")
    # Pattern: [prefix] volume/disk/drive (X:) or X:
    # Note: longer words first in alternation to prevent partial matches (vol matching volume)
    m = re.search(
        r'(?:(?:local|new|the|my|our|external|internal)\s+)?'
        r'(?:partition|volume|drive|disk|vol)\b\s*'
        r'[\(\[]?([a-zA-Z]):?[\)\]]?',
        text, re.I
    )
    if m:
        return f"{m.group(1).upper()}:\\"
    m = re.search(r'[\(\[]?([a-zA-Z]):[\)\]]?\s*$', text)
    if m:
        return f"{m.group(1).upper()}:\\"
    return None


def _get_available_drives():
    """Return list of available drive root paths."""
    drives = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        p = Path(f"{letter}:\\")
        if p.exists():
            drives.append(p)
    return drives


def _normalize_reference(text):
    if not text:
        return text
    cleaned = str(text).strip().strip('"\'')

    # Protect file extensions before stripping keywords (e.g., .docx → __EXT_0__)
    ext_map = {}
    ext_parts = re.findall(r'\.\w+', cleaned)
    for i, ext in enumerate(ext_parts):
        placeholder = f'__EXT_{i}__'
        ext_map[placeholder] = ext
        cleaned = cleaned.replace(ext, placeholder, 1)

    cleaned = re.sub(r"\b(named|called|name|folder|file|document|directory|path|at|to)\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for pattern in [" on desktop", " in desktop", " on documents", " in documents", " on downloads", " in downloads", " on pictures", " in pictures", " on music", " in music", " on videos", " in videos"]:
        cleaned = cleaned.replace(pattern, "")
    cleaned = cleaned.strip()

    # Restore file extensions
    for placeholder, ext in ext_map.items():
        cleaned = cleaned.replace(placeholder, ext)

    return cleaned


def _find_on_desktop(name, item_type="file"):
    if not DESKTOP_DIR.exists() or not name:
        return None

    normalized_name = str(name).strip()
    # Try exact match first (recursive on Desktop)
    try:
        for item in DESKTOP_DIR.rglob(normalized_name):
            if item_type == "folder" and item.is_dir():
                return item
            if item_type == "file" and item.is_file():
                return item
    except Exception:
        pass

    # Try case-insensitive partial match
    lower_name = normalized_name.lower()
    try:
        for item in DESKTOP_DIR.rglob("*"):
            if item_type == "folder" and item.is_dir() and lower_name in item.name.lower():
                return item
            if item_type == "file" and item.is_file() and lower_name in item.name.lower():
                return item
    except Exception:
        pass

    return None


def _find_in_directory(name, directory, item_type="file"):
    """Search for an item by name in a specific directory (non-recursive only for speed)."""
    if not directory or not Path(directory).exists() or not name:
        return None

    dir_path = Path(directory)
    normalized_name = str(name).strip()

    # Direct check - exact path in directory
    direct = dir_path / normalized_name
    if direct.exists():
        if item_type == "folder" and direct.is_dir():
            return direct
        if item_type == "file" and direct.is_file():
            return direct

    # Case-insensitive search in directory (non-recursive only - fast)
    lower_name = normalized_name.lower()
    try:
        for item in dir_path.iterdir():
            if item_type == "folder" and item.is_dir() and lower_name in item.name.lower():
                return item
            if item_type == "file" and item.is_file() and lower_name in item.name.lower():
                return item
    except Exception:
        pass

    # Fuzzy matching fallback (typo tolerance)
    best_match = None
    best_ratio = 0
    try:
        for item in dir_path.iterdir():
            is_correct_type = (item_type == "folder" and item.is_dir()) or \
                              (item_type == "file" and item.is_file())
            if is_correct_type:
                ratio = difflib.SequenceMatcher(None, lower_name, item.name.lower()).ratio()
                if ratio > best_ratio and ratio >= 0.7:
                    best_ratio = ratio
                    best_match = item
    except Exception:
        pass

    return best_match


def _resolve_source_path(source, item_type="file", base_dir=None):
    """Resolve a source name to a full path. Searches all common directories with fuzzy matching."""
    source_text = _normalize_reference(source)
    path = Path(source_text).expanduser()

    # If it's an absolute path that exists, use directly
    if path.is_absolute() and path.exists():
        return path

    # If a base_dir is provided, search there first
    if base_dir:
        found = _find_in_directory(source_text, base_dir, item_type)
        if found:
            return found

    # Search Desktop (recursive for exact, then fuzzy)
    desktop_match = _find_on_desktop(path.name, item_type)
    if desktop_match:
        return desktop_match

    # Search common user directories (Documents, Downloads, Pictures, etc.)
    for common_dir in COMMON_USER_DIRS:
        if common_dir == DESKTOP_DIR:
            continue  # Already searched above
        found = _find_in_directory(path.name, common_dir, item_type)
        if found:
            return found

    # Search current working directory
    cwd = Path.cwd()
    cwd_match = _find_in_directory(path.name, cwd, item_type)
    if cwd_match:
        return cwd_match

    # Search home directory (non-recursive)
    home_dir = Path.home()
    home_match = _find_in_directory(path.name, home_dir, item_type)
    if home_match:
        return home_match

    # Search available drive roots (D:\, E:\, etc.) — non-recursive top-level only
    for drive_root in _get_available_drives():
        if drive_root == Path("C:\\"):
            continue  # Already covered by Desktop/Documents/Downloads
        found = _find_in_directory(path.name, drive_root, item_type)
        if found:
            return found

    # Return the path as-is (will trigger "not found" in the operation function)
    if path.is_absolute():
        return path
    return path


def _resolve_destination_path(destination, source_path=None):
    dest_text = _normalize_reference(destination)

    # Check if destination is a drive letter reference (e.g. "new volume(D:)", "disk E:")
    drive = _extract_drive_letter(dest_text)
    if drive:
        return Path(drive)

    path = Path(dest_text).expanduser()
    if path.is_absolute():
        return path

    # Check if destination name matches an existing folder in common directories
    # E.g., "copy file.docx to MADAM" should find existing MADAM folder on Desktop
    for common_dir in COMMON_USER_DIRS:
        if not common_dir.exists():
            continue
        candidate = common_dir / path.name
        if candidate.exists() and candidate.is_dir():
            return candidate
        # Case-insensitive search
        try:
            for item in common_dir.iterdir():
                if item.is_dir() and item.name.lower() == path.name.lower():
                    return item
        except Exception:
            continue

    # Check drive roots for existing folder (e.g. D:\MADAM)
    for drive_root in _get_available_drives():
        if drive_root == Path("C:\\"):
            continue
        try:
            for item in drive_root.iterdir():
                if item.is_dir() and item.name.lower() == path.name.lower():
                    return item
        except Exception:
            continue

    # Default: place next to source, or on Desktop
    if source_path and source_path.exists():
        return source_path.parent / path.name
    return DESKTOP_DIR / path.name


def _is_folder_locked(folder_path):
    """Check if a folder is the CWD or parent of CWD (locked by the running process)."""
    try:
        resolved = Path(folder_path).resolve()
        cwd = Path.cwd().resolve()
        # Check if CWD is inside this folder (folder is an ancestor of CWD)
        if cwd == resolved or str(cwd).startswith(str(resolved) + os.sep):
            return True
    except Exception:
        pass
    return False


def create_folder(folder_name):
    path = Path(folder_name).expanduser().resolve()
    try:
        # Ensure parent directory exists
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return _build_result("Create Folder", str(path), "failed",
                                f"Folder already exists at: {path}", "Folder")
        path.mkdir(parents=True, exist_ok=False)
        return _build_result("Created Folder", str(path), "success",
                            f"Folder created at: {path}", "Folder")
    except PermissionError:
        return _build_result("Create Folder", str(path), "failed",
                            f"Access denied. Cannot create folder at: {path}", "Folder")
    except Exception as e:
        return _build_result("Create Folder", str(path), "failed", str(e), "Folder")


def delete_folder(folder_name):
    path = Path(folder_name).expanduser().resolve()
    try:
        if not path.exists():
            return _build_result("Delete Folder", str(path), "failed",
                                f"I couldn't find a folder called '{path.name}'. Is the name spelled correctly?", "Folder")
        if not path.is_dir():
            return _build_result("Delete Folder", str(path), "failed",
                                f"'{path.name}' is a file, not a folder. Did you mean 'delete file'?", "Folder")
        if _is_folder_locked(path):
            return _build_result(
                "Delete Folder", str(path), "failed",
                f"Cannot delete '{path.name}' — it is the current working directory or contains the running application. "
                f"Close NOVA AI first, then delete the folder manually.",
                "Folder")
        shutil.rmtree(str(path))
        return _build_result("Deleted Folder", str(path), "success",
                            f"Folder deleted: {path}", "Folder")
    except PermissionError:
        return _build_result("Delete Folder", str(path), "failed",
                            f"Access denied. Try running as administrator or close any open files in the folder.", "Folder")
    except Exception as e:
        return _build_result("Delete Folder", str(path), "failed", str(e), "Folder")


def rename_folder(source, destination, base_dir=None):
    src = _resolve_source_path(source, item_type="folder", base_dir=base_dir)
    dst = _resolve_destination_path(destination, src)
    # If base_dir provided and dst is just a name, place it in base_dir
    if base_dir and not Path(destination).is_absolute():
        dst_name = _normalize_reference(destination)
        base_path = Path(base_dir).expanduser()
        if base_path.exists():
            dst = base_path / dst_name
    try:
        if not src.exists() or not src.is_dir():
            return _build_result("Rename Folder", src, "failed",
                                f"I couldn't find a folder called '{source}'. Check the name and try again.",
                                "Folder", destination=dst)
        if dst.exists():
            return _build_result("Rename Folder", dst, "failed",
                                f"A folder called '{dst.name}' already exists. Choose a different name.",
                                "Folder", destination=dst)
        if _is_folder_locked(src):
            return _build_result(
                "Rename Folder", src, "failed",
                f"Cannot rename '{src.name}' — it is the current working directory or contains the running application. "
                f"Close NOVA AI first, then rename the folder manually.",
                "Folder", destination=dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        return _build_result("Renamed Folder", src, "success", f"Folder renamed to: {dst}", "Folder", destination=dst)
    except PermissionError:
        return _build_result(
            "Rename Folder", src, "failed",
            f"Access denied. The folder '{src.name}' may be in use by another process. "
            f"Close any programs using it and try again.",
            "Folder", destination=dst)
    except Exception as e:
        return _build_result("Rename Folder", src, "failed", str(e), "Folder", destination=dst)


def move_folder(source, destination, base_dir=None):
    src = _resolve_source_path(source, item_type="folder", base_dir=base_dir)
    dst = _resolve_destination_path(destination, src)
    if base_dir and not Path(destination).is_absolute():
        dst_name = _normalize_reference(destination)
        base_path = Path(base_dir).expanduser()
        if base_path.exists():
            dst = base_path / dst_name
    try:
        if not src.exists() or not src.is_dir():
            return _build_result("Move Folder", src, "failed",
                                f"I couldn't find a folder called '{source}'. Check the name and try again.",
                                "Folder", destination=dst)
        if _is_folder_locked(src):
            return _build_result(
                "Move Folder", src, "failed",
                f"Cannot move '{src.name}' — it is the current working directory or contains the running application. "
                f"Close NOVA AI first, then move the folder manually.",
                "Folder", destination=dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return _build_result("Moved Folder", src, "success", f"Folder moved to: {dst}", "Folder", destination=dst)
    except PermissionError:
        return _build_result(
            "Move Folder", src, "failed",
            f"Access denied. The folder '{src.name}' may be in use by another process.",
            "Folder", destination=dst)
    except Exception as e:
        return _build_result("Move Folder", src, "failed", str(e), "Folder", destination=dst)


def search_folder(query, root=None, max_results=50):
    root_path = Path(root or Path.cwd()).expanduser()
    matches = []

    # Search directories in priority order: root first, then common dirs
    search_dirs = [root_path] if root_path.exists() else []
    for d in COMMON_USER_DIRS:
        if d.exists() and d not in search_dirs:
            search_dirs.append(d)

    try:
        for search_root in search_dirs:
            for item in search_root.rglob("*"):
                if item.is_dir() and query.lower() in item.name.lower():
                    full_path = str(item.resolve())
                    if full_path not in matches:
                        matches.append(full_path)
                        if len(matches) >= max_results:
                            break
            if len(matches) >= max_results:
                break

        message = f"Found {len(matches)} folder(s) matching '{query}'"
        return _build_result("Search Folder", root_path, "success", message, "Folder", extra=matches)
    except Exception as e:
        return _build_result("Search Folder", root_path, "failed", str(e), "Folder", extra=[])


def open_folder(folder_name):
    path = Path(folder_name).expanduser()
    try:
        if not path.exists() or not path.is_dir():
            return _build_result("Open Folder", path, "failed",
                                f"I couldn't find a folder called '{path.name}'. Is the name spelled correctly?", "Folder")
        os.startfile(str(path))
        return _build_result("Opened Folder", path, "success", f"Opened folder: {path}", "Folder")
    except Exception as e:
        return _build_result("Open Folder", path, "failed", str(e), "Folder")


def create_file(file_name, content=""):
    path = Path(file_name).expanduser().resolve()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return _build_result("Create File", str(path), "failed",
                                f"File already exists at: {path}", "File")
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return _build_result("Created File", str(path), "success",
                            f"File created at: {path}", "File")
    except PermissionError:
        return _build_result("Create File", str(path), "failed",
                            f"Access denied. Cannot create file at: {path}", "File")
    except Exception as e:
        return _build_result("Create File", str(path), "failed", str(e), "File")


def delete_file(file_name):
    path = Path(file_name).expanduser().resolve()
    try:
        if not path.exists():
            return _build_result("Delete File", str(path), "failed",
                                f"I couldn't find a file called '{path.name}'. Is the name spelled correctly?", "File")
        if not path.is_file():
            return _build_result("Delete File", str(path), "failed",
                                f"'{path.name}' is a folder, not a file. Did you mean 'delete folder'?", "File")
        path.unlink()
        return _build_result("Deleted File", str(path), "success",
                            f"File deleted: {path}", "File")
    except PermissionError:
        return _build_result("Delete File", str(path), "failed",
                            f"This file is being used by another program. Close it and try again.", "File")
    except Exception as e:
        return _build_result("Delete File", str(path), "failed", str(e), "File")


def rename_file(source, destination, base_dir=None):
    src = _resolve_source_path(source, item_type="file", base_dir=base_dir)
    dst = _resolve_destination_path(destination, src)
    if base_dir and not Path(destination).is_absolute():
        dst_name = _normalize_reference(destination)
        base_path = Path(base_dir).expanduser()
        if base_path.exists():
            dst = base_path / dst_name
    try:
        if not src.exists() or not src.is_file():
            return _build_result("Rename File", src, "failed",
                                f"I couldn't find a file called '{source}'. Check the name and try again.",
                                "File", destination=dst)
        if dst.exists():
            return _build_result("Rename File", dst, "failed",
                                f"A file called '{dst.name}' already exists. Choose a different name.",
                                "File", destination=dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        return _build_result("Renamed File", src, "success", f"File renamed to: {dst}", "File", destination=dst)
    except Exception as e:
        return _build_result("Rename File", src, "failed", str(e), "File", destination=dst)


def move_file(source, destination, base_dir=None):
    src = _resolve_source_path(source, item_type="file", base_dir=base_dir)
    dst = _resolve_destination_path(destination, src)
    if base_dir and not Path(destination).is_absolute():
        dst_name = _normalize_reference(destination)
        base_path = Path(base_dir).expanduser()
        if base_path.exists():
            dst = base_path / dst_name
    try:
        if not src.exists() or not src.is_file():
            return _build_result("Move File", src, "failed",
                                f"I couldn't find a file called '{source}'. Check the name and try again.",
                                "File", destination=dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return _build_result("Moved File", src, "success", f"File moved to: {dst}", "File", destination=dst)
    except Exception as e:
        return _build_result("Move File", src, "failed", str(e), "File", destination=dst)


def copy_file(source, destination, base_dir=None):
    src = _resolve_source_path(source, item_type="file", base_dir=base_dir)
    dst = _resolve_destination_path(destination, src)
    if base_dir and not Path(destination).is_absolute():
        dst_name = _normalize_reference(destination)
        base_path = Path(base_dir).expanduser()
        if base_path.exists():
            dst = base_path / dst_name
    try:
        if not src.exists() or not src.is_file():
            return _build_result("Copy File", src, "failed",
                                f"I couldn't find a file called '{source}'. Check the name and try again.",
                                "File", destination=dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        return _build_result("Copied File", src, "success", f"File copied to: {dst}", "File", destination=dst)
    except Exception as e:
        return _build_result("Copy File", src, "failed", str(e), "File", destination=dst)


def search_file(query, root=None, max_results=50):
    root_path = Path(root or Path.cwd()).expanduser()
    matches = []

    # Search directories in priority order: root first, then common dirs
    search_dirs = [root_path] if root_path.exists() else []
    for d in COMMON_USER_DIRS:
        if d.exists() and d not in search_dirs:
            search_dirs.append(d)

    try:
        for search_root in search_dirs:
            for item in search_root.rglob("*"):
                if item.is_file() and query.lower() in item.name.lower():
                    full_path = str(item.resolve())
                    if full_path not in matches:
                        matches.append(full_path)
                        if len(matches) >= max_results:
                            break
            if len(matches) >= max_results:
                break

        message = f"Found {len(matches)} file(s) matching '{query}'"
        return _build_result("Search File", root_path, "success", message, "File", extra=matches)
    except Exception as e:
        return _build_result("Search File", root_path, "failed", str(e), "File", extra=[])


def open_file(file_name):
    path = Path(file_name).expanduser()
    try:
        if not path.exists() or not path.is_file():
            return _build_result("Open File", path, "failed",
                                f"I couldn't find a file called '{path.name}'. Is the name spelled correctly?", "File")
        os.startfile(str(path))
        return _build_result("Opened File", path, "success", f"Opened file: {path}", "File")
    except Exception as e:
        return _build_result("Open File", path, "failed", str(e), "File")


def read_file_contents(file_name, max_chars=3200):
    path = Path(file_name).expanduser()
    try:
        if not path.exists() or not path.is_file():
            return _build_result("Read File", path, "failed",
                                f"I couldn't find a file called '{path.name}'. Is the name spelled correctly?", "File")
        with open(path, "r", encoding="utf-8", errors="replace") as file:
            data = file.read(max_chars)
        snippet = data if len(data) < max_chars else data + "\n... (truncated)"
        return _build_result("Read File", path, "success", f"Read file contents from: {path}", "File", extra={"contents": snippet})
    except Exception as e:
        return _build_result("Read File", path, "failed", str(e), "File")
