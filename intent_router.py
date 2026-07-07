"""
AMAZON AI - Intent Router
Routes classified intents to the appropriate automation handler.
Uses smart_parse_command() for unified entity extraction.
"""
import os
import re
import webbrowser
import urllib.parse
from datetime import datetime
from pathlib import Path

from automation.app_tasks import (
    close_application,
    get_user_running_apps,
    kill_process_by_pid,
    list_running_processes,
    open_application,
    run_terminal_command,
)
from automation.document_tasks import generate_document
from automation.file_tasks import (
    copy_file,
    create_file,
    create_folder,
    delete_file,
    delete_folder,
    move_file,
    move_folder,
    open_file,
    open_folder,
    read_file_contents,
    rename_file,
    rename_folder,
    search_file,
    search_folder,
)
from automation.search_tasks import research_topic, search_applications
from automation.web_tasks import KNOWN_SITES, normalize, open_website


def make_result(intent, entity=None, status="success", message="", details=None):
    return {
        "intent": intent,
        "entity": entity,
        "status": status,
        "message": message,
        "details": details,
        "task_id": int(datetime.now().strftime("%Y%m%d%H%M%S")),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def log_action(intent, entity=None, action=None):
    print("\n========== AI ACTION LOG ==========")
    print(f"Intent Detected: {intent}")
    if entity:
        print(f"Entity: {entity}")
    if action:
        print(f"Action: {action}")
    print("===================================\n")


# =====================================================================
#  INTENT HANDLERS
# =====================================================================

def _resolve_path(parsed):
    """Resolve entity name with base_dir and location_hint context. Returns full path string or None."""
    name = parsed.get("entity")
    if not name:
        return None
    # Already a full path
    if "\\" in name or "/" in name or ":" in name:
        return name
    # If location_hint was extracted, resolve via filesystem search
    location_hint = parsed.get("location_hint")
    if location_hint:
        from agent import resolve_location
        resolved = resolve_location(location_hint, parsed.get("base_dir"))
        return str(Path(resolved) / name)
    base_dir = parsed.get("base_dir")
    if base_dir:
        return str(Path(base_dir) / name)
    # No location context — search common directories for existing item
    from agent import DEFAULT_BASE_DIR
    import os
    search_dirs = [
        DEFAULT_BASE_DIR,
        Path(os.path.expanduser("~")) / "Documents",
        Path(os.path.expanduser("~")) / "Downloads",
        Path(os.path.expanduser("~")),
    ]
    for d in search_dirs:
        if d.is_dir():
            try:
                for item in d.iterdir():
                    if item.name.lower() == name.lower():
                        return str(item)
            except PermissionError:
                continue
    # Not found — default to Desktop
    return str(DEFAULT_BASE_DIR / name)

def _handle_open_app(intent, command, parsed):
    """Open an application."""
    app_name = parsed.get("app_name") or parsed.get("entity")
    if app_name:
        log_action(intent, app_name, "opening application")
        result = open_application(app_name)
        return make_result(intent, app_name, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "Which app would you like to open? Try: 'open chrome', 'open notepad', etc.")


def _handle_close_app(intent, command, parsed):
    """Close an application. Supports name and PID (e.g. 'kill process 1234')."""
    import re
    app_name = parsed.get("app_name") or parsed.get("entity")
    if app_name:
        # Check if the entity is a PID (pure number)
        pid_match = re.search(r'\b(\d{2,6})\b', app_name)
        if pid_match and app_name.strip().replace("process ", "").replace("pid ", "").strip() == pid_match.group(1):
            log_action(intent, f"PID {pid_match.group(1)}", "killing process")
            result = kill_process_by_pid(pid_match.group(1))
            return make_result(intent, f"PID {pid_match.group(1)}", result.get("status", "failed"),
                               result.get("message", ""), result)
        log_action(intent, app_name, "closing application")
        result = close_application(app_name)
        return make_result(intent, app_name, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "Which app would you like to close?")


def _handle_create_folder(intent, command, parsed):
    """Create a new folder."""
    name = _resolve_path(parsed)
    if name:
        log_action(intent, name, "creating folder")
        result = create_folder(name)
        return make_result(intent, name, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "What should I name the folder? Try: 'create folder [name]'")


def _handle_delete_folder(intent, command, parsed):
    """Delete a folder."""
    name = _resolve_path(parsed)
    if name:
        log_action(intent, name, "deleting folder")
        result = delete_folder(name)
        return make_result(intent, name, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "Which folder would you like to delete? Try: 'delete folder [name]'")


def _handle_open_folder(intent, command, parsed):
    """Open a folder in File Explorer. Supports folder discovery (e.g. 'open my last project')."""
    discovery_type = parsed.get("discovery_type")
    if discovery_type:
        from automation.file_discovery import resolve_discovery
        semantic_query = parsed.get("semantic_query") or parsed.get("entity")
        log_action(intent, discovery_type, "folder discovery")
        disc = resolve_discovery(discovery_type, query=semantic_query)
        if disc.get("status") == "found":
            folder_path = disc["path"]
            log_action(intent, folder_path, "opening discovered folder")
            result = open_folder(folder_path)
            result["discovery"] = disc
            return make_result(intent, disc.get("name", folder_path),
                               result.get("status", "failed"),
                               disc["message"] + "\n" + result.get("message", ""), result)
        # Preserve the search query in entity even when not found
        return make_result(intent, semantic_query or parsed.get("entity"), "not_found",
                           disc.get("message", "Folder not found."), disc)

    name = _resolve_path(parsed)
    if name:
        log_action(intent, name, "opening folder")
        result = open_folder(name)
        return make_result(intent, name, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "Which folder would you like to open?")


def _handle_rename_folder(intent, command, parsed):
    """Rename a folder."""
    source = parsed.get("source") or parsed.get("entity")
    dest = parsed.get("destination")
    base_dir = parsed.get("base_dir")
    if source and dest:
        log_action(intent, f"{source} -> {dest}" + (f" (in {base_dir})" if base_dir else ""), "renaming folder")
        result = rename_folder(source, dest, base_dir=base_dir)
        return make_result(intent, source, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "I need both names. Try: 'rename folder [old name] to [new name]'")


def _handle_move_folder(intent, command, parsed):
    """Move a folder."""
    source = parsed.get("source") or parsed.get("entity")
    dest = parsed.get("destination")
    base_dir = parsed.get("base_dir")
    if source and dest:
        log_action(intent, f"{source} -> {dest}" + (f" (in {base_dir})" if base_dir else ""), "moving folder")
        result = move_folder(source, dest, base_dir=base_dir)
        return make_result(intent, source, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "Where should I move it? Try: 'move folder [name] to [destination]'")


def _handle_search_folder(intent, command, parsed):
    """Search for folders."""
    query = parsed.get("search_query") or parsed.get("entity")
    if query:
        log_action(intent, query, "searching folders")
        result = search_folder(query)
        return make_result(intent, query, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed", "What folder are you looking for?")


def _handle_create_file(intent, command, parsed):
    """Create a new file."""
    name = _resolve_path(parsed)
    if name:
        log_action(intent, name, "creating file")
        result = create_file(name)
        return make_result(intent, name, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "What should I name the file? Try: 'create file [name]'")


def _handle_delete_file(intent, command, parsed):
    """Delete a file."""
    name = _resolve_path(parsed)
    if name:
        log_action(intent, name, "deleting file")
        result = delete_file(name)
        return make_result(intent, name, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "Which file would you like to delete? Try: 'delete file [name]'")


def _handle_open_file(intent, command, parsed):
    """Open a file. Supports file/folder/semantic discovery."""
    discovery_type = parsed.get("discovery_type")
    if discovery_type:
        from automation.file_discovery import resolve_discovery
        semantic_query = parsed.get("semantic_query") or parsed.get("entity")
        log_action(intent, discovery_type, "file discovery")
        disc = resolve_discovery(discovery_type, query=semantic_query)
        if disc.get("status") == "found":
            file_path = disc["path"]
            log_action(intent, file_path, "opening discovered file")
            result = open_file(file_path)
            result["discovery"] = disc
            # Show all semantic matches
            if discovery_type == "semantic" and disc.get("files"):
                lines = [disc["message"]]
                for f in disc["files"][1:5]:
                    lines.append(f"  Also: {f['name']} (score: {f['score']})")
                msg = "\n".join(lines) + "\n" + result.get("message", "")
            else:
                msg = disc["message"] + "\n" + result.get("message", "")
            return make_result(intent, disc.get("name", file_path),
                               result.get("status", "failed"), msg, result)
        # Preserve the search query in entity even when not found
        return make_result(intent, semantic_query or parsed.get("entity"), "not_found",
                           disc.get("message", "Not found."), disc)

    name = _resolve_path(parsed)
    if name:
        log_action(intent, name, "opening file")
        result = open_file(name)
        return make_result(intent, name, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "Which file would you like to open?")


def _handle_read_file(intent, command, parsed):
    """Read file contents."""
    name = _resolve_path(parsed)
    if name:
        log_action(intent, name, "reading file")
        result = read_file_contents(name)
        return make_result(intent, name, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "Which file would you like me to read?")


def _handle_rename_file(intent, command, parsed):
    """Rename a file."""
    source = parsed.get("source") or parsed.get("entity")
    dest = parsed.get("destination")
    base_dir = parsed.get("base_dir")
    if source and dest:
        log_action(intent, f"{source} -> {dest}" + (f" (in {base_dir})" if base_dir else ""), "renaming file")
        result = rename_file(source, dest, base_dir=base_dir)
        return make_result(intent, source, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "I need both names. Try: 'rename file [old name] to [new name]'")


def _handle_move_file(intent, command, parsed):
    """Move a file."""
    source = parsed.get("source") or parsed.get("entity")
    dest = parsed.get("destination")
    base_dir = parsed.get("base_dir")
    if source and dest:
        log_action(intent, f"{source} -> {dest}" + (f" (in {base_dir})" if base_dir else ""), "moving file")
        result = move_file(source, dest, base_dir=base_dir)
        return make_result(intent, source, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "Where should I move it? Try: 'move file [name] to [destination]'")


def _handle_copy_file(intent, command, parsed):
    """Copy a file."""
    source = parsed.get("source") or parsed.get("entity")
    dest = parsed.get("destination")
    base_dir = parsed.get("base_dir")
    if source and dest:
        log_action(intent, f"{source} -> {dest}" + (f" (in {base_dir})" if base_dir else ""), "copying file")
        result = copy_file(source, dest, base_dir=base_dir)
        return make_result(intent, source, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "I need to know what to copy and where. Try: 'copy [file] to [new name]'")


def _handle_copy_folder(intent, command, parsed):
    """Copy a folder."""
    source = parsed.get("source") or parsed.get("entity")
    dest = parsed.get("destination")
    base_dir = parsed.get("base_dir")
    if source and dest:
        log_action(intent, f"{source} -> {dest}" + (f" (in {base_dir})" if base_dir else ""), "copying folder")
        # Folders don't have a dedicated copy function; use shutil via move logic
        import shutil
        from automation.file_tasks import _resolve_source_path, _resolve_destination_path, _normalize_reference, _build_result
        src = _resolve_source_path(source, item_type="folder", base_dir=base_dir)
        dst = _resolve_destination_path(dest, src)
        if base_dir and not Path(dest).is_absolute():
            dst_name = _normalize_reference(dest)
            base_path = Path(base_dir).expanduser()
            if base_path.exists():
                dst = base_path / dst_name
        try:
            if not src.exists() or not src.is_dir():
                r = _build_result("Copy Folder", src, "failed", "Source folder not found", "Folder", destination=dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(str(src), str(dst))
                r = _build_result("Copied Folder", src, "success", f"Folder copied to: {dst}", "Folder", destination=dst)
        except Exception as e:
            r = _build_result("Copy Folder", src, "failed", str(e), "Folder", destination=dst)
        return make_result(intent, source, r.get("status", "failed"), r.get("message", ""), r)
    return make_result(intent, None, "failed",
                       "I need to know what to copy and where. Try: 'copy folder [name] to [new name]'")


def _handle_search_file(intent, command, parsed):
    """Search for files. Supports file discovery (e.g. 'show pdfs downloaded today')."""
    discovery_type = parsed.get("discovery_type")
    if discovery_type:
        from automation.file_discovery import resolve_discovery
        semantic_query = parsed.get("semantic_query") or parsed.get("entity")
        log_action(intent, discovery_type, "file discovery")
        disc = resolve_discovery(discovery_type, query=semantic_query)
        if disc.get("status") == "found":
            files = disc.get("files", [{"name": disc.get("name"), "path": disc.get("path")}])
            lines = [disc["message"]]
            for f in files[:10]:
                # Format as clickable link
                path_str = f.get('path', '')
                lines.append(f"  - {f['name']} ({f.get('modified', '')}) [{path_str}]")
            details = disc
            details["file_list"] = [f["path"] for f in files]
            return make_result(intent, semantic_query, "success", "\n".join(lines), details)
        return make_result(intent, semantic_query, "failed", disc.get("message", "No files found."), disc)

    query = parsed.get("search_query") or parsed.get("entity")
    if query:
        log_action(intent, query, "searching files")
        result = search_file(query)
        return make_result(intent, query, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed", "What file are you looking for?")


def _detect_document_type(command):
    """Extract document type and topic from command.
    
    Returns tuple (doc_type, topic) or (None, None) if not detected.
    doc_type: 'assignment', 'research_proposal', 'report', or None
    topic: the extracted topic string
    """
    cmd_lower = command.lower()
    
    # Assignment patterns: "create assignment about X", "make assignment on X"
    assignment_match = re.search(r'\b(?:create|make|generate)\s+assignment\s+(?:about|on|on\s+the\s+topic\s+of)\s+(.+?)(?:\s+(?:file|document|doc|pdf|docx))?(?:\s*$|\s*\.|\s*file|\s*document)', cmd_lower)
    if assignment_match:
        return "assignment", assignment_match.group(1).strip()
    
    # Research proposal patterns: "create research proposal on X", "generate research proposal about X"
    proposal_match = re.search(r'\b(?:create|make|generate)\s+(?:research\s+)?proposal\s+(?:about|on|on\s+the\s+topic\s+of)\s+(.+?)(?:\s+(?:file|document|doc|pdf|docx))?(?:\s*$|\s*\.|\s*file|\s*document)', cmd_lower)
    if proposal_match:
        return "research_proposal", proposal_match.group(1).strip()
    
    # Report patterns: "create report about X", "generate report on X"
    report_match = re.search(r'\b(?:create|make|generate)\s+report\s+(?:about|on|on\s+the\s+topic\s+of)\s+(.+?)(?:\s+(?:file|document|doc|pdf|docx))?(?:\s*$|\s*\.|\s*file|\s*document)', cmd_lower)
    if report_match:
        return "report", report_match.group(1).strip()
    
    return None, None


def _handle_generate_document(intent, command, parsed):
    """Generate a document (Word/Excel/PDF). Supports structured documents (assignment, research proposal, report)."""
    from agent import DEFAULT_BASE_DIR
    
    name = parsed.get("entity")
    if not name:
        return make_result(intent, None, "failed", "What should the document be about? Try: 'create assignment about cybersecurity'")
    
    # Detect document type and extract topic
    doc_type, extracted_topic = _detect_document_type(command)
    
    if doc_type and extracted_topic:
        topic = extracted_topic
    elif doc_type and not extracted_topic:
        topic = name.rsplit(".", 1)[0] if "." in name else name
    else:
        topic = name.rsplit(".", 1)[0] if "." in name else name
    
    # Generate appropriate document type
    if doc_type == "assignment":
        log_action(intent, topic, "generating assignment")
        result = generate_document(DEFAULT_BASE_DIR / f"{topic.replace(' ', '_')}_Assignment.docx", topic=topic, doc_type="assignment")
        return make_result(intent, topic, result.get("status", "failed"), result.get("message", ""), result)
    
    if doc_type == "research_proposal":
        log_action(intent, topic, "generating research proposal")
        result = generate_document(DEFAULT_BASE_DIR / f"{topic.replace(' ', '_')}_Proposal.docx", topic=topic, doc_type="research_proposal")
        return make_result(intent, topic, result.get("status", "failed"), result.get("message", ""), result)
    
    if doc_type == "report":
        log_action(intent, topic, "generating report")
        result = generate_document(DEFAULT_BASE_DIR / f"{topic.replace(' ', '_')}_Report.docx", topic=topic, doc_type="report")
        return make_result(intent, topic, result.get("status", "failed"), result.get("message", ""), result)
    
    # Fallback to basic document generation
    if "\\" not in name and "/" not in name and ":" not in name:
        name = str(DEFAULT_BASE_DIR / name)
    log_action(intent, name, "generating document")
    research = research_topic(topic)
    content = None
    if research:
        content = f"{topic}\n\n{research}\n\nGenerated by AMAZON AI Assistant.\n"
    result = generate_document(name, topic=topic, content=content)
    return make_result(intent, name, result.get("status", "failed"), result.get("message", ""), result)


def _handle_open_website(intent, command, parsed):
    """Open a website."""
    site = parsed.get("entity") or parsed.get("search_query")
    if not site:
        # Fallback: strip common prefixes
        from agent import extract_entity
        site = extract_entity(command)
    if site:
        log_action(intent, site, "opening website")
        action_message = open_website(site)
        normalized_site = normalize(site)
        status = "success" if normalized_site in KNOWN_SITES else "partial"
        return make_result(intent, site, status, action_message)
    return make_result(intent, None, "failed", "Which website would you like to open?")


def _handle_search_web(intent, command, parsed):
    """Search the web."""
    query = parsed.get("search_query") or parsed.get("entity")
    if query:
        log_action(intent, query, "searching the web")
        encoded = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded}"
        webbrowser.open(url)
        return make_result(intent, query, "success", f"Searching Google for: {query}")
    return make_result(intent, None, "failed", "What would you like me to search for?")


def _handle_search_app(intent, command, parsed):
    """Search for installed applications."""
    query = parsed.get("search_query") or parsed.get("entity")
    if query:
        log_action(intent, query, "searching installed applications")
        result = search_applications(query)
        return make_result(intent, query, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed", "Which app are you looking for?")


def _handle_run_command(intent, command, parsed):
    """Run a terminal command."""
    cmd = command
    for prefix in ["run command ", "execute command ", "run terminal command ",
                    "execute system command ", "run "]:
        if cmd.lower().startswith(prefix):
            cmd = cmd[len(prefix):].strip()
            break
    log_action(intent, cmd, "executing terminal command")
    result = run_terminal_command(cmd)
    return make_result(intent, cmd, result.get("status", "failed"),
                       result.get("message", ""), result)


# Friendly names for common executables
_EXE_DISPLAY_NAMES = {
    "chrome.exe": "Chrome", "msedge.exe": "Edge", "firefox.exe": "Firefox",
    "code.exe": "VS Code", "notepad++.exe": "Notepad++", "notepad.exe": "Notepad",
    "winword.exe": "Word", "excel.exe": "Excel", "powerpnt.exe": "PowerPoint",
    "mspaint.exe": "Paint", "calculator.exe": "Calculator",
    "telegram.exe": "Telegram", "whatsapp.exe": "WhatsApp",
    "whatsapp.root.exe": "WhatsApp",
    "discord.exe": "Discord", "slack.exe": "Slack", "spotify.exe": "Spotify",
    "vlc.exe": "VLC", "obs64.exe": "OBS", "obs32.exe": "OBS",
    "photoshop.exe": "Photoshop", "illustrator.exe": "Illustrator",
    "cmd.exe": "Command Prompt", "powershell.exe": "PowerShell",
    "taskmgr.exe": "Task Manager", "explorer.exe": "File Explorer",
    "python.exe": "Python", "pythonw.exe": "Python",
    "qoder.exe": "Qoder", "supercopier.exe": "SuperCopier",
    "lulnchr.exe": "Logi Launcher", "logitech update.exe": "Logitech Update",
    "mysqld.exe": "MySQL", "postgres.exe": "PostgreSQL",
}


def _clean_exe_name(exe_name):
    """Convert exe name to a user-friendly display name."""
    import re
    lower = exe_name.lower()
    # Check exact match, with .exe, and without extension
    if lower in _EXE_DISPLAY_NAMES:
        return _EXE_DISPLAY_NAMES[lower]
    if lower + ".exe" in _EXE_DISPLAY_NAMES:
        return _EXE_DISPLAY_NAMES[lower + ".exe"]
    base = lower.replace(".exe", "")
    if base + ".exe" in _EXE_DISPLAY_NAMES:
        return _EXE_DISPLAY_NAMES[base + ".exe"]
    # Generic cleanup: remove .exe and title-case
    name = exe_name.replace(".exe", "").replace(".EXE", "")
    # Insert space before capital letters for camelCase
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    return name.title() if name else exe_name


def _handle_list_processes(intent, command, parsed):
    """List running processes. Shows user-facing apps when asked about 'apps'."""
    cmd_lower = command.lower()

    # If the user asks about "apps" or "applications", show filtered list
    if any(kw in cmd_lower for kw in ["app", "application"]):
        log_action(intent, None, "listing running applications")
        result = get_user_running_apps()
        apps = result.get("apps", [])
        lines = ["Running Applications:"]
        for i, a in enumerate(apps[:30], 1):
            display = _clean_exe_name(a["name"])
            lines.append(f"{i}. {display} (PID: {a['pid']})")
        lines.append(f"\nTotal: {result.get('total', len(apps))} application(s)")
        lines.append("\nTip: Say 'kill process [PID]' to stop an application.")
        details = result
        details["process_list"] = [f"{a['name']} (PID: {a['pid']})" for a in apps[:30]]
        return make_result(intent, None, result.get("status", "failed"),
                           "\n".join(lines), details)

    # Default: show all processes
    log_action(intent, None, "listing running processes")
    result = list_running_processes()
    processes = result.get("processes", [])
    lines = ["Running Processes:"]
    for i, p in enumerate(processes[:30], 1):
        display = _clean_exe_name(p["name"])
        lines.append(f"{i}. {display} (PID: {p['pid']})")
    lines.append(f"\nShowing {min(30, len(processes))} of {result.get('total', len(processes))} processes")
    lines.append("\nTip: Say 'kill process [PID]' to stop a process.")
    details = result
    details["process_list"] = [f"{p['name']} (PID: {p['pid']})" for p in processes[:30]]
    return make_result(intent, None, result.get("status", "failed"),
                       "\n".join(lines), details)


def _handle_create_project(intent, command, parsed):
    """Create a new project."""
    from agent import extract_project_args
    project_name, framework = extract_project_args(command)
    if project_name:
        log_action(intent, f"{framework}/{project_name}", "creating project")
        try:
            from automation.dev_tasks import create_project
            result = create_project(project_name, framework)
            return make_result(intent, project_name, result.get("status", "failed"),
                               result.get("message", ""), result)
        except ImportError:
            return make_result(intent, project_name, "failed",
                               "Developer assistance module not available")
    return make_result(intent, None, "failed",
                       "What kind of project? Try: 'create react project myapp'")


def _handle_greeting(intent, command, parsed):
    """Respond to greeting."""
    return make_result(
        intent, None, "success",
        "Hello! I'm AMAZON AI, your desktop assistant. I can help you with:\n"
        "- Creating, renaming, deleting files and folders\n"
        "- Opening and closing applications\n"
        "- Web search and document generation\n"
        "- Project scaffolding\n"
        "Just tell me what you need, or type 'help' for all commands!",
    )


def _handle_unknown(intent, command, parsed):
    """Handle unknown intent."""
    return make_result(
        intent, None, "unsupported",
        "I can't do that yet, but I'm learning! Here's what I can help with:\n"
        "- File/folder management (create, rename, delete, search)\n"
        "- Opening apps and websites\n"
        "- Document generation (Word, Excel, PDF)\n"
        "- Web search and research\n"
        "- Project scaffolding\n"
        "Type 'help' for all available commands.",
    )


# =====================================================================
#  DISPATCH TABLE
# =====================================================================

INTENT_HANDLERS = {
    "open_app": _handle_open_app,
    "close_app": _handle_close_app,
    "create_folder": _handle_create_folder,
    "delete_folder": _handle_delete_folder,
    "open_folder": _handle_open_folder,
    "rename_folder": _handle_rename_folder,
    "move_folder": _handle_move_folder,
    "copy_folder": _handle_copy_folder,
    "search_folder": _handle_search_folder,
    "create_file": _handle_create_file,
    "delete_file": _handle_delete_file,
    "open_file": _handle_open_file,
    "read_file": _handle_read_file,
    "rename_file": _handle_rename_file,
    "move_file": _handle_move_file,
    "copy_file": _handle_copy_file,
    "search_file": _handle_search_file,
    "generate_document": _handle_generate_document,
    "open_website": _handle_open_website,
    "search_web": _handle_search_web,
    "search_app": _handle_search_app,
    "run_command": _handle_run_command,
    "list_processes": _handle_list_processes,
    "create_project": _handle_create_project,
    "greeting": _handle_greeting,
    "unknown": _handle_unknown,
}


# =====================================================================
#  MAIN ROUTER
# =====================================================================

def route_intent(
    intent,
    command,
    extract_app_name,
    extract_folder_name,
    extract_delete_folder_name,
    extract_file_name,
    extract_delete_file_name,
    extract_entity,
    extract_rename_args=None,
    extract_move_args=None,
    extract_copy_args=None,
    extract_search_query=None,
    extract_project_args=None,
    parsed=None,
):
    """Route an intent to the appropriate handler.

    All intents now use smart_parse_command() for unified extraction.
    The extract_* parameters are kept for backward compatibility.
    """
    # Import smart parser
    from agent import smart_parse_command

    # Parse the command once (or use pre-parsed result if provided)
    if parsed is None:
        parsed = smart_parse_command(command)

    # Dispatch to handler
    handler = INTENT_HANDLERS.get(intent)
    if handler:
        return handler(intent, command, parsed)

    # Fallback for unrecognized intents
    return make_result(
        intent, None, "unsupported",
        "I didn't quite understand that command. You can try:\n"
        "- 'create file [name]' or 'create folder [name]'\n"
        "- 'open chrome', 'open notepad', etc.\n"
        "- 'search for [topic]' or 'search web [topic]'\n"
        "- 'list processes' or 'run command [cmd]'\n"
        "- 'create project [name] with [framework]'\n"
        "- Type 'help' in the chat for a full list of commands.",
    )
