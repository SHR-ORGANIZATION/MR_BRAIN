import os
import re
import shutil
import subprocess
import platform
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


def _open_with_system(path_str):
    """Open a file or folder using the system's default handler (cross-platform)."""
    system = platform.system()
    if system == "Windows":
        os.startfile(path_str)
    elif system == "Darwin":
        subprocess.Popen(["open", path_str])
    else:
        subprocess.Popen(["xdg-open", path_str])


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
    """Return list of available drive root paths (cross-platform)."""
    drives = []
    if platform.system() == "Windows":
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            p = Path(f"{letter}:\\")
            if p.exists():
                drives.append(p)
    else:
        # macOS / Linux: root + mounted volumes
        root = Path("/")
        if root.exists():
            drives.append(root)
        volumes = Path("/Volumes")
        if volumes.exists():
            try:
                for v in volumes.iterdir():
                    if v.is_dir() and v not in drives:
                        drives.append(v)
            except Exception:
                pass
        # Also check /mnt for Linux
        mnt = Path("/mnt")
        if mnt.exists():
            try:
                for m in mnt.iterdir():
                    if m.is_dir() and m not in drives:
                        drives.append(m)
            except Exception:
                pass
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
    """Delete a folder with force option if needed (cross-platform)."""
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
                f"Close AMAZON AI first, then delete the folder manually.",
                "Folder")
        
        # Try normal deletion first
        try:
            shutil.rmtree(str(path))
            return _build_result("Deleted Folder", str(path), "success",
                                f"Folder deleted: {path}", "Folder")
        except PermissionError:
            # Try force deletion based on OS
            current_os = platform.system()
            if current_os == "Darwin":  # macOS
                result = subprocess.run(
                    ["rm", "-rf", str(path)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    return _build_result("Deleted Folder", str(path), "success",
                                        f"Folder deleted (force): {path}", "Folder")
            elif current_os == "Windows":
                result = subprocess.run(
                    ["cmd", "/c", "rmdir", "/s", "/q", str(path)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    return _build_result("Deleted Folder", str(path), "success",
                                        f"Folder deleted (force): {path}", "Folder")
            else:  # Linux
                result = subprocess.run(
                    ["rm", "-rf", str(path)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    return _build_result("Deleted Folder", str(path), "success",
                                        f"Folder deleted (force): {path}", "Folder")
            
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
                f"Close AMAZON AI first, then rename the folder manually.",
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
                f"Close AMAZON AI first, then move the folder manually.",
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
    """Search for folders anywhere on the PC (cross-platform). Searches ALL drives."""
    import time
    matches = []
    start_time = time.time()
    timeout = 15

    # Directories to skip
    _SKIP_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
        ".idea", ".vscode", "dist", "build", ".gradle", ".m2",
        ".npm", ".cache", ".cargo", "target", "Pods",
        ".Trash", ".fseventsd", ".Spotlight-V100",
    }

    def _should_skip(dir_path):
        parts = dir_path.parts
        for part in parts:
            if part in _SKIP_DIRS:
                return True
            if part.startswith(".") and part not in {".git", ".github"}:
                return True
        return False

    # Build search directories
    search_dirs = []
    all_drives = _get_available_drives()

    if root:
        root_path = Path(root).expanduser()
        if root_path.exists():
            search_dirs.append(root_path)
    else:
        # Volumes first
        for drive in all_drives:
            if drive == Path("/"):
                continue
            if drive.exists() and drive not in search_dirs:
                search_dirs.append(drive)
        # Then home
        home = Path.home()
        if home.exists():
            search_dirs.append(home)
        for d in COMMON_USER_DIRS:
            if d.exists() and d not in search_dirs:
                search_dirs.append(d)

    query_lower = query.lower().strip()
    max_per_dir = 5

    try:
        for search_root in search_dirs:
            if time.time() - start_time > timeout:
                break
            dir_matches = 0
            try:
                for item in search_root.rglob("*"):
                    if time.time() - start_time > timeout:
                        break
                    if not item.is_dir():
                        continue
                    if _should_skip(item) or _should_skip(item.parent):
                        continue
                    if query_lower in item.name.lower():
                        full_path = str(item.resolve())
                        if full_path not in matches:
                            matches.append(full_path)
                            dir_matches += 1
                            if len(matches) >= max_results:
                                break
                            if dir_matches >= max_per_dir:
                                break
            except PermissionError:
                continue
            if len(matches) >= max_results:
                break

        message = f"Found {len(matches)} folder(s) matching '{query}' across all drives"
        return _build_result("Search Folder", root or "all drives", "success", message, "Folder", extra=matches)
    except Exception as e:
        return _build_result("Search Folder", root or "all drives", "failed", str(e), "Folder", extra=[])


def open_folder(folder_name):
    path = Path(folder_name).expanduser()
    try:
        if not path.exists() or not path.is_dir():
            return _build_result("Open Folder", path, "failed",
                                f"I couldn't find a folder called '{path.name}'. Is the name spelled correctly?", "Folder")
        _open_with_system(str(path))
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
    """Delete a file with force option if needed (cross-platform)."""
    path = Path(file_name).expanduser().resolve()
    try:
        if not path.exists():
            return _build_result("Delete File", str(path), "failed",
                                f"I couldn't find a file called '{path.name}'. Is the name spelled correctly?", "File")
        if not path.is_file():
            return _build_result("Delete File", str(path), "failed",
                                f"'{path.name}' is a folder, not a file. Did you mean 'delete folder'?", "File")
        
        # Try normal deletion first
        try:
            path.unlink()
            return _build_result("Deleted File", str(path), "success",
                                f"File deleted: {path}", "File")
        except PermissionError:
            # Try force deletion based on OS
            current_os = platform.system()
            if current_os == "Darwin":  # macOS
                result = subprocess.run(
                    ["rm", "-f", str(path)],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return _build_result("Deleted File", str(path), "success",
                                        f"File deleted (force): {path}", "File")
            elif current_os == "Windows":
                result = subprocess.run(
                    ["cmd", "/c", "del", "/f", "/q", str(path)],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return _build_result("Deleted File", str(path), "success",
                                        f"File deleted (force): {path}", "File")
            else:  # Linux
                result = subprocess.run(
                    ["rm", "-f", str(path)],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return _build_result("Deleted File", str(path), "success",
                                        f"File deleted (force): {path}", "File")
            
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
    """Search for files anywhere on the PC (cross-platform). Searches ALL drives."""
    import time
    matches = []
    start_time = time.time()
    timeout = 15  # Timeout for comprehensive search

    # Directories to ALWAYS skip (dev artifacts, system, caches)
    _SKIP_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
        ".idea", ".vscode", "dist", "build", ".gradle", ".m2",
        ".npm", ".cache", ".cargo", "target", "Pods",
        ".Trash", ".fseventsd", ".Spotlight-V100",
    }

    def _should_skip_dir(dir_path):
        """Check if directory should be skipped entirely."""
        parts = dir_path.parts
        for part in parts:
            if part in _SKIP_DIRS:
                return True
            if part.startswith(".") and part not in {".git", ".github"}:
                return True
        return False

    def _get_drive_name(file_path, all_drives):
        """Get which drive/volume a file belongs to."""
        fp = str(file_path)
        for drive in all_drives:
            ds = str(drive)
            if ds != "/" and fp.startswith(ds):
                return drive.name or ds
        # Must be on root/Macintosh HD
        home = str(Path.home())
        if fp.startswith(home):
            return "Macintosh HD"
        return "Macintosh HD"

    # Build search directories in priority order
    search_dirs = []
    all_drives = _get_available_drives()

    if root:
        root_path = Path(root).expanduser()
        if root_path.exists():
            search_dirs.append(root_path)
    else:
        # Add volumes FIRST (user's external drives like MAC, OFFICE, etc.)
        for drive in all_drives:
            drive_str = str(drive).lower()
            if any(skip in drive_str for skip in ["onedrive", "icloud", "dropbox", "google drive"]):
                continue
            if drive == Path("/"):
                continue  # Skip root filesystem
            if drive.exists() and drive not in search_dirs:
                search_dirs.append(drive)
        
        # Then add common user dirs
        home = Path.home()
        common_dirs = [
            home / "Desktop",
            home / "Documents",
            home / "Downloads",
            home / "Pictures",
            home / "Videos",
            home / "Music",
            home / "Movies",
            home / "Recent",
            home / "Applications",
            home / "Library",
            
        ]
        for d in common_dirs:
            if d.exists() and d not in search_dirs:
                search_dirs.append(d)
        
        # Add home directory
        if home.exists() and home not in search_dirs:
            search_dirs.append(home)
        
        # Add other common dirs
        for d in COMMON_USER_DIRS:
            if d.exists() and d not in search_dirs:
                search_dirs.append(d)

    query_lower = query.lower().strip()
    max_per_dir = 5  # Limit results per search root to get diverse results

    try:
        for search_root in search_dirs:
            if time.time() - start_time > timeout:
                break
            dir_matches = 0
            try:
                for item in search_root.rglob("*"):
                    if time.time() - start_time > timeout:
                        break
                    # Skip unwanted directories during traversal
                    if item.is_dir():
                        continue
                    # Skip if parent path contains skip dirs
                    if _should_skip_dir(item.parent):
                        continue
                    # Match query in filename
                    if query_lower in item.name.lower():
                        full_path = str(item.resolve())
                        if full_path not in matches:
                            matches.append(full_path)
                            dir_matches += 1
                            if len(matches) >= max_results:
                                break
                            if dir_matches >= max_per_dir:
                                break  # Move to next search root
            except PermissionError:
                continue
            except OSError:
                continue
            if len(matches) >= max_results:
                break

        if matches:
            # Build message with drive info
            drive_counts = {}
            for m in matches:
                dname = _get_drive_name(m, all_drives)
                drive_counts[dname] = drive_counts.get(dname, 0) + 1
            
            drive_summary = ", ".join(f"{c} on {d}" for d, c in drive_counts.items())
            message = f"Found {len(matches)} file(s) matching '{query}' — {drive_summary}"
            return _build_result("Search File", root or "all drives", "success", message, "File", extra=matches)
        else:
            return _build_result("Search File", root or "all drives", "failed",
                                f"Couldn't find any file matching '{query}' on any drive.", "File", extra=[])
    except Exception as e:
        return _build_result("Search File", root or "all drives", "failed", str(e), "File", extra=[])


def open_file(file_name):
    path = Path(file_name).expanduser()
    try:
        if not path.exists() or not path.is_file():
            return _build_result("Open File", path, "failed",
                                f"I couldn't find a file called '{path.name}'. Is the name spelled correctly?", "File")
        _open_with_system(str(path))
        return _build_result("Opened File", path, "success", f"Opened file: {path}", "File")
    except Exception as e:
        return _build_result("Open File", path, "failed", str(e), "File")


def smart_search(query, max_results=10):
    """Smart search with fuzzy matching - helps when user forgets exact name/location."""
    import time
    import difflib
    
    start_time = time.time()
    timeout = 8
    matches = []
    
    # Extract keywords from query (remove common words)
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'my', 'find', 'search', 'look', 'locate'}
    keywords = [w.lower() for w in query.split() if w.lower() not in stop_words and len(w) > 2]
    
    if not keywords:
        keywords = [query.lower()]
    
    # Search directories
    search_dirs = []
    home = Path.home()
    common_dirs = [
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        home / "Pictures",
    ]
    for d in common_dirs:
        if d.exists():
            search_dirs.append(d)
    if home.exists() and home not in search_dirs:
        search_dirs.append(home)
    
    try:
        for search_root in search_dirs:
            if time.time() - start_time > timeout:
                break
            try:
                for item in search_root.rglob("*"):
                    if time.time() - start_time > timeout:
                        break
                    if not item.is_file():
                        continue
                    
                    item_name = item.name.lower()
                    
                    # Check if ANY keyword matches (partial match)
                    keyword_match = any(kw in item_name for kw in keywords)
                    
                    # Also check similarity (fuzzy match)
                    similarity = difflib.SequenceMatcher(None, query.lower(), item_name).ratio()
                    
                    if keyword_match or similarity > 0.4:
                        full_path = str(item.resolve())
                        if full_path not in matches:
                            matches.append(full_path)
                            if len(matches) >= max_results:
                                break
            except PermissionError:
                continue
            if len(matches) >= max_results:
                break
        
        return matches
    except Exception as e:
        return []


def universal_search(query, max_results=30):
    """Search for anything - files, folders, apps. Returns combined results."""
    import time
    from automation.search_tasks import search_applications
    
    start_time = time.time()
    timeout = 10  # Reduced from 20 to 10 seconds for faster response
    
    results = {
        "files": [],
        "folders": [],
        "apps": []
    }
    
    # Search files (with shorter timeout)
    file_result = search_file(query, max_results=10)
    if file_result.get("status") == "success":
        results["files"] = file_result.get("extra", [])
    
    # Check timeout
    if time.time() - start_time < timeout:
        # Search folders (with shorter timeout)
        folder_result = search_folder(query, max_results=10)
        if folder_result.get("status") == "success":
            results["folders"] = folder_result.get("extra", [])
    
    # Check timeout - only search apps if we have time left
    if time.time() - start_time < 5:  # Only if we have 5+ seconds left
        try:
            app_result = search_applications(query)
            if app_result.get("status") == "success":
                results["apps"] = app_result.get("extra", [])
        except:
            pass
    
    # Build response
    total = len(results["files"]) + len(results["folders"]) + len(results["apps"])
    
    if total == 0:
        # Try smart/fuzzy search as fallback
        smart_matches = smart_search(query, max_results=5)
        if smart_matches:
            lines = [f"I didn't find an exact match, but here are similar files:"]
            for file in smart_matches[:5]:
                lines.append(f"  • {file}")
            lines.append(f"\n Tip: Try using fewer keywords or check the spelling!")
            return {
                "status": "success",
                "message": "\n".join(lines),
                "results": {"files": smart_matches, "folders": [], "apps": []}
            }
        
        return {
            "status": "failed",
            "message": f"I couldn't find anything matching '{query}'. Try:\n  • Checking the spelling\n  • Using a different keyword\n  • Searching in a specific location",
            "results": results
        }
    
    # Build formatted message
    lines = [f"Found {total} result(s) for '{query}':"]
    
    if results["folders"]:
        lines.append(f"\n📁 Folders ({len(results['folders'])}):")
        for folder in results["folders"][:5]:
            lines.append(f"  • {folder}")
    
    if results["files"]:
        lines.append(f"\n📄 Files ({len(results['files'])}):")
        for file in results["files"][:10]:
            lines.append(f"  • {file}")
    
    if results["apps"]:
        lines.append(f"\n Applications ({len(results['apps'])}):")
        for app in results["apps"][:5]:
            lines.append(f"  • {app}")
    
    return {
        "status": "success",
        "message": "\n".join(lines),
        "results": results
    }


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


def empty_trash():
    """Empty the trash/recycle bin (cross-platform)."""
    current_os = platform.system()
    
    try:
        if current_os == "Darwin":
            # macOS: Use AppleScript with Finder (most reliable method)
            # This uses the system's built-in trash emptying functionality
            result = subprocess.run(
                ["osascript", "-e", 
                 'tell application "Finder" to empty the trash'],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode == 0:
                return _build_result("Empty Trash", "", "success",
                                    "Trash has been emptied successfully.", "System")
            
            # Fallback: Try with admin privileges
            result = subprocess.run(
                ["osascript", "-e",
                 'do shell script "rm -rf ~/.Trash/*" with administrator privileges'],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode == 0:
                return _build_result("Empty Trash", "", "success",
                                    "Trash has been emptied successfully.", "System")
            
            # Last resort: Try direct rm without admin
            trash_path = Path.home() / ".Trash"
            subprocess.run(
                f"rm -rf {trash_path}/* 2>/dev/null || true",
                shell=True, capture_output=True, text=True, timeout=30
            )
            subprocess.run(
                f"rm -rf {trash_path}/.* 2>/dev/null || true",
                shell=True, capture_output=True, text=True, timeout=30
            )
            
            return _build_result("Empty Trash", "", "success",
                                "Trash empty command executed. Some protected items may need manual deletion via Finder.", "System")
        
        elif current_os == "Windows":
            # Windows: Use PowerShell to clear recycle bin
            result = subprocess.run(
                ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return _build_result("Empty Trash", "", "success",
                                    "Recycle Bin has been emptied successfully.", "System")
            else:
                return _build_result("Empty Trash", "", "failed",
                                    f"Could not empty Recycle Bin: {result.stderr}", "System")
        
        else:
            # Linux: Try to empty trash using standard methods
            trash_paths = [
                Path.home() / ".local/share/Trash/files",
                Path.home() / ".local/share/Trash",
                Path.home() / ".Trash",
            ]
            emptied = False
            for trash_path in trash_paths:
                if trash_path.exists():
                    try:
                        shutil.rmtree(str(trash_path))
                        trash_path.mkdir(parents=True, exist_ok=True)
                        emptied = True
                    except Exception:
                        pass
            
            if emptied:
                return _build_result("Empty Trash", "", "success",
                                    "Trash has been emptied successfully.", "System")
            else:
                return _build_result("Empty Trash", "", "failed",
                                    "Could not find or empty trash folder.", "System")
    
    except subprocess.TimeoutExpired:
        return _build_result("Empty Trash", "", "failed",
                            "Operation timed out.", "System")
    except Exception as e:
        return _build_result("Empty Trash", "", "failed", str(e), "System")
