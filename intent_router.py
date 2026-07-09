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
    empty_trash,
    move_file,
    move_folder,
    open_file,
    open_folder,
    read_file_contents,
    rename_file,
    rename_folder,
    search_file,
    search_folder,
    universal_search,
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
    """Delete a file - with smart fuzzy matching."""
    name = _resolve_path(parsed)
    if name:
        log_action(intent, name, "deleting file")
        result = delete_file(name)
        
        # If delete failed because file not found, try smart search
        if result.get("status") == "failed" and "couldn't find" in result.get("message", "").lower():
            # Extract just the filename from the entity
            entity = parsed.get("entity", "")
            
            # Try to find similar files
            from automation.file_tasks import smart_search
            similar_files = smart_search(entity, max_results=5)
            
            if similar_files:
                # Found similar files - return them as suggestions
                lines = [f"I couldn't find '{entity}' exactly, but here are similar files:"]
                for f in similar_files[:5]:
                    lines.append(f"  • {f}")
                lines.append("")
                lines.append("💡 **Tip:** Click on a file path above to open it, or tell me the exact name to delete.")
                
                return make_result(
                    intent, entity, "failed",
                    "\n".join(lines),
                    {"file_list": similar_files}
                )
        
        return make_result(intent, name, result.get("status", "failed"),
                           result.get("message", ""), result)
    return make_result(intent, None, "failed",
                       "Which file would you like to delete? Try: 'delete file [name]'")


def _handle_empty_trash(intent, command, parsed):
    """Empty the trash/recycle bin."""
    log_action(intent, "trash", "emptying trash")
    result = empty_trash()
    return make_result(intent, "trash", result.get("status", "failed"),
                       result.get("message", ""), result)


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


def _handle_find_anything(intent, command, parsed):
    """Universal search - find files, folders, or apps. Always returns clickable paths."""
    query = parsed.get("search_query") or parsed.get("entity")
    if query:
        # Clean up query - remove filler words that don't help with search
        import re
        # Remove common filler words/phrases
        filler_patterns = [
            r'\bany\b\s*',  # "any"
            r'\babout\b\s*',  # "about"
            r'\bsomething\b\s*',  # "something"
            r'\banything\b\s*',  # "anything"
        ]
        cleaned_query = query
        for pattern in filler_patterns:
            cleaned_query = re.sub(pattern, '', cleaned_query, flags=re.I)
        cleaned_query = cleaned_query.strip()
        
        # Use cleaned query if it's not empty, otherwise use original
        search_query = cleaned_query if cleaned_query else query
        
        log_action(intent, search_query, "searching for anything")
        result = universal_search(search_query)
        
        # Always enhance with clickable paths if files/folders were found
        if result.get("results"):
            results = result["results"]
            all_paths = []
            
            # Collect all file and folder paths
            if results.get("files"):
                all_paths.extend(results["files"])
            if results.get("folders"):
                all_paths.extend(results["folders"])
            
            # Add paths to details for UI to render as clickable
            if all_paths:
                if result.get("details") is None:
                    result["details"] = {}
                result["details"]["file_list"] = all_paths
                
                # Store in conversation context for "it" references
                try:
                    from system.conversation_manager import conversation_manager
                    conversation_manager.active_conversation = {
                        "last_found_paths": all_paths,
                        "last_query": query,
                        "last_intent": intent
                    }
                except:
                    pass
        
        # Pass the details sub-dict (which contains file_list) to make_result
        details = result.get("details") if result else None
        return make_result(intent, query, result.get("status", "failed"),
                           result.get("message", ""), details)
    return make_result(intent, None, "failed", "What are you looking for? Try: 'find [name]' or 'search for [name]'")


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
    """Generate a document (Word/Excel/PDF). Supports structured documents (assignment, research proposal, report, schedule)."""
    from agent import DEFAULT_BASE_DIR
    import re
    
    cmd_lower = command.lower().strip()
    
    # Step 1: Detect document format from command (pdf, excel, word, docx)
    doc_format = "docx"  # default
    if re.search(r'\b(pdf|pdf document|pdf file)\b', cmd_lower):
        doc_format = "pdf"
    elif re.search(r'\b(excel|spreadsheet|xlsx)\b', cmd_lower):
        doc_format = "xlsx"
    elif re.search(r'\b(word document|word file|docx)\b', cmd_lower):
        doc_format = "docx"
    
    # Step 2: Extract filename from "name it as X", "named X", "save as X", "call it X"
    filename = None
    name_patterns = [
        r'(?:name\s+(?:it\s+)?as|named?|call\s+(?:it\s+)?|save\s+(?:it\s+)?as|save\s+as)\s+([\w\s-]+?)(?:\s+(?:also|then|and|but|with|about|on|regarding)|\s*$)',
    ]
    for pattern in name_patterns:
        m = re.search(pattern, cmd_lower, re.I)
        if m:
            filename = m.group(1).strip()
            # Clean up filename - remove trailing words that aren't part of name
            for stop_word in ["also", "then", "and", "but", "with", "write", "create", "about", "on", "regarding"]:
                filename = re.sub(r'\s+' + stop_word + r'\b.*$', '', filename, flags=re.I).strip()
            break
    
    # Step 3: Extract topic from "about X", "on X", "regarding X", "content about X"
    topic = None
    topic_patterns = [
        r'(?:content\s+)?(?:about|on|regarding)\s+(.+?)(?:\s*$)',
        r'(?:write|generate|create|make)\s+(?:.+?)\s+(?:about|on|regarding)\s+(.+?)(?:\s*$)',
        r'(?:to learn|for learning|learn)\s+(.+?)(?:\s*$)',
    ]
    for pattern in topic_patterns:
        m = re.search(pattern, cmd_lower, re.I)
        if m:
            topic = m.group(1).strip()
            # Clean up topic
            for stop_word in ["also", "then", "and", "but", "save", "name"]:
                topic = re.sub(r'\s+' + stop_word + r'\b.*$', '', topic, flags=re.I).strip()
            if topic:
                break
    
    # Step 4: Detect structured document type (assignment, proposal, report, schedule)
    doc_type = None
    if re.search(r'\bassignment\b', cmd_lower):
        doc_type = "assignment"
    elif re.search(r'\bresearch\s+proposal\b|\bproposal\b', cmd_lower):
        doc_type = "research_proposal"
    elif re.search(r'\breport\b', cmd_lower):
        doc_type = "report"
    elif re.search(r'\bschedule\b|\bschedules\b|\bplan\b|\bratiba\b', cmd_lower):  # ratiba = schedule in Swahili
        doc_type = "schedule"
    
    # Step 4b: For schedule commands, extract topic from the command itself if not found
    if not topic and doc_type == "schedule":
        # Check for patterns like "professional training schedules", "work schedule", etc.
        schedule_topic_match = re.search(r'(?:create|make|generate|write)\s+([\w\s]+?)\s*(?:schedules?|schedule|plan|ratiba)', cmd_lower, re.I)
        if schedule_topic_match:
            topic = schedule_topic_match.group(1).strip()
            # Remove filler words
            for filler in ["a", "an", "the", "my", "our"]:
                topic = re.sub(r'\b' + filler + r'\b', '', topic, flags=re.I).strip()
            if topic:
                topic = topic.title()
        # Fallback: if still no topic, use a default
        if not topic:
            topic = "Training Schedule"
    
    # Step 5: Extract person name for schedules (e.g., "Leo schedule", "schedule for Shakira")
    person_name = None
    if doc_type == "schedule":
        # Pattern 1: "create [Name] schedule" - capitalized names only
        name_match = re.search(r'(?:create|make|generate|write)\s+([A-Z][a-z]+(?:\s+[a-z]+)?)\s+(?:schedule|plan|ratiba)', cmd_lower)
        # Pattern 2: "schedule for [Name]" - capitalized names only
        if not name_match:
            name_match = re.search(r'(?:schedule|plan|ratiba|schedules)\s+(?:for|ya|wa|kwa)\s+([A-Z][a-z]+(?:\s+[a-z]+)?)', cmd_lower)
        # Pattern 3: Swahili: "nataka schedule ya [Name]"
        if not name_match:
            name_match = re.search(r'(?:nataka|taka)\s+(?:schedule|ratiba|schedules)\s+(?:ya|wa|kwa)\s+([A-Z][a-z]+(?:\s+[a-z]+)?)', cmd_lower)
        # Pattern 4: "schedule for [Name]" - two lowercase words
        if not name_match:
            name_match = re.search(r'(?:schedule|plan|schedules)\s+(?:for|ya|wa)\s+([a-z]+\s+[a-z]+)', cmd_lower, re.I)
        # Pattern 5: "schedule for [Name]" - single lowercase word (catches "Leo", "hamisi" etc.)
        if not name_match:
            name_match = re.search(r'(?:schedule|plan|schedules)\s+(?:for|ya|wa)\s+([a-z]+)(?:\s|$|\.)', cmd_lower, re.I)
        if name_match:
            person_name = name_match.group(1).strip().title()  # Capitalize name
            # Update topic with person name
            if topic and ("to learn" in topic.lower() or "about" in topic.lower() or person_name.lower() not in topic.lower()):
                # Clean topic if it contains "to learn" or "about"
                topic = re.sub(r'to\s+learn\s+', '', topic, flags=re.I).strip()
                topic = re.sub(r'about\s+', '', topic, flags=re.I).strip()
                if person_name.lower() not in topic.lower():
                    topic = f"{person_name}'s {topic.title()}"
    
    # Step 5b: Extract topic from "about X", "to learn X", "for learning X"
    # This refines the topic if a person name was found
    if person_name:
        topic_match = re.search(r'(?:about|to learn|for learning|on)\s+(.+?)(?:\s*$)', cmd_lower, re.I)
        if topic_match:
            topic_text = topic_match.group(1).strip()
            # Clean up topic - remove "to learn" prefix if present
            topic_text = re.sub(r'^to\s+learn\s+', '', topic_text, flags=re.I).strip()
            topic_text = re.sub(r'^for\s+learning\s+', '', topic_text, flags=re.I).strip()
            # Clean up topic
            for stop_word in ["also", "then", "and", "but", "save", "name"]:
                topic_text = re.sub(r'\s+' + stop_word + r'\b.*$', '', topic_text, flags=re.I).strip()
            if topic_text:
                topic = f"{person_name}'s {topic_text.title()} Training Schedule"
        else:
            # No "about/to learn" topic found - ensure topic ends with "Schedule"
            _generic_topics = {"work", "training", "professional", "personal", "daily", "weekly"}
            current_base = topic.replace(f"{person_name}'s ", "").strip().lower() if topic else ""
            if current_base in _generic_topics or not topic:
                # Use "<Name>'s <Topic> Schedule" format
                base_topic = topic.replace(f"{person_name}'s ", "").strip() if topic else "Training"
                topic = f"{person_name}'s {base_topic.title()} Schedule"
            elif not topic.lower().endswith("schedule"):
                # Topic exists but doesn't end with "Schedule" - add it
                base_topic = topic.replace(f"{person_name}'s ", "").strip()
                topic = f"{person_name}'s {base_topic.title()} Schedule"
    
    # Step 6: Fallback topic extraction
    if not topic:
        if doc_type == "schedule":
            topic = "Training Schedule"
        else:
            topic = "document"
    
    # Step 7: Build output path
    def _safe_filename(name):
        """Sanitize a string for use as a filename."""
        safe = re.sub(r"['\u2018\u2019`]", '', name)  # remove apostrophes
        safe = re.sub(r'[^\w\s-]', '', safe)  # remove other special chars
        safe = re.sub(r'\s+', '_', safe).strip('_')
        return safe[:60]
    
    if filename:
        # User specified filename - use it with correct extension
        if not Path(filename).suffix:
            filename = f"{filename}.{doc_format}"
        else:
            # Replace extension with correct format if needed
            ext = Path(filename).suffix.lower()
            if doc_format == "pdf" and ext != ".pdf":
                filename = Path(filename).stem + ".pdf"
            elif doc_format == "xlsx" and ext not in [".xlsx", ".xlsm"]:
                filename = Path(filename).stem + ".xlsx"
            elif doc_format == "docx" and ext not in [".docx", ".doc"]:
                filename = Path(filename).stem + ".docx"
        output_path = str(DEFAULT_BASE_DIR / filename)
    elif doc_type == "assignment":
        output_path = str(DEFAULT_BASE_DIR / f"{_safe_filename(topic)}_Assignment.docx")
    elif doc_type == "research_proposal":
        output_path = str(DEFAULT_BASE_DIR / f"{_safe_filename(topic)}_Proposal.docx")
    elif doc_type == "report":
        output_path = str(DEFAULT_BASE_DIR / f"{_safe_filename(topic)}_Report.docx")
    elif doc_type == "schedule":
        # Don't add _Schedule suffix if topic already contains "Schedule"
        safe_topic = _safe_filename(topic)
        if topic.lower().endswith("schedule"):
            output_path = str(DEFAULT_BASE_DIR / f"{safe_topic}.docx")
        else:
            output_path = str(DEFAULT_BASE_DIR / f"{safe_topic}_Schedule.docx")
    else:
        output_path = str(DEFAULT_BASE_DIR / f"{_safe_filename(topic)}.{doc_format}")
    
    # Step 8: Generate document
    log_action(intent, f"{topic} ({doc_format})", f"generating {doc_type or 'document'}")
    
    if doc_type == "assignment":
        result = generate_document(output_path, topic=topic, doc_type="assignment")
    elif doc_type == "research_proposal":
        result = generate_document(output_path, topic=topic, doc_type="research_proposal")
    elif doc_type == "report":
        result = generate_document(output_path, topic=topic, doc_type="report")
    elif doc_type == "schedule":
        # Generate schedule - topic already includes person name if extracted
        result = generate_document(output_path, topic=topic, doc_type="schedule")
    else:
        # For PDF/Excel/Word, generate with content
        research = research_topic(topic)
        content = None
        if research:
            content = f"{topic.title()}\n\n{research}\n\nGenerated by AMAZON AI Assistant.\n"
        result = generate_document(output_path, topic=topic, content=content)
    
    # Store the saved path in details for UI to display
    if result.get("status") == "success":
        saved_path = result.get("path", output_path)
        # Ensure details dict exists before assigning
        if result.get("details") is None:
            result["details"] = {}
        result["details"]["saved_path"] = saved_path
        result["details"]["topic"] = topic
    
    return make_result(intent, topic, result.get("status", "failed"), result.get("message", ""), result)


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
    """Run a terminal command - with auto-learning."""
    cmd = command
    for prefix in ["run command ", "execute command ", "run terminal command ",
                    "execute system command ", "run "]:
        if cmd.lower().startswith(prefix):
            cmd = cmd[len(prefix):].strip()
            break
    log_action(intent, cmd, "executing terminal command")
    result = run_terminal_command(cmd)
    
    # Auto-learn: record OS command usage
    try:
        from system.auto_learner import learn_os_command_usage
        learn_os_command_usage(cmd, "run_command", result.get("status") == "success")
    except:
        pass
    
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
    """Respond to greeting with friendly, conversational tone and environment info."""
    import random
    from system.environment_scanner import get_environment_stats
    
    # Get environment stats to show user
    try:
        stats = get_environment_stats()
        apps_count = stats.get('apps', 0)
        drives_count = stats.get('drives', 0)
        folders_count = stats.get('folders', 0)
        
        greeting_responses = [
            f"Hello!  I'm AMAZON, your desktop assistant. I've discovered {apps_count} apps and {drives_count} drives on your system. How can I help you today?",
            f"Hi there! 😊 Ready to help! Your system has {apps_count} applications installed. What would you like to do?",
            f"Hey! 🌟 I've scanned your computer and found {folders_count} important folders. I'm here to make your work easier!",
            f"Hello! 🎉 I'm AMAZON, your personal digital assistant. I can help you manage files, open apps, search your computer, and much more. What do you need?",
            f"Hi! ✨ Great to see you! I've checked your computer environment and everything looks good. How can I assist you today?",
            f"Hey there! 🚀 I'm ready to help you operate your computer more efficiently. What would you like to accomplish?",
        ]
    except Exception:
        greeting_responses = [
            "Hello! 👋 I'm AMAZON, your desktop assistant. How can I help you today?",
            "Hi there! 😊 Ready to help! What would you like to do?",
            "Hey!  I'm here to make your work easier. What do you need?",
            "Hello!  I'm AMAZON, your personal digital assistant. What can I do for you?",
            "Hi! ✨ Great to see you! How can I assist you today?",
            "Hey there! 🚀 I'm ready to help you get things done. What would you like to accomplish?",
        ]
    
    return make_result(
        intent, None, "success",
        random.choice(greeting_responses),
    )


def _handle_help_request(intent, command, parsed):
    """Handle help requests with friendly, detailed response."""
    return make_result(
        intent, None, "success",
        "Of course! I'm here to help! 😊 Here's what I can do for you:\n\n"
        "📁 **Files & Folders**\n"
        "   • Create, rename, move, copy, or delete files and folders\n"
        "   • Search for files or folders on your computer\n"
        "   • Open files and folders\n\n"
        " **Apps & System**\n"
        "   • Open any app (Chrome, VS Code, Spotify, etc.)\n"
        "   • Close apps\n"
        "   • Empty trash, lock screen, take screenshots\n\n"
        "🌐 **Web & Documents**\n"
        "   • Search the web\n"
        "   • Generate Word, Excel, or PDF documents\n"
        "   • Open websites\n\n"
        "Just tell me what you need in plain English, and I'll take care of it! 🎯",
    )


def _handle_list_commands(intent, command, parsed):
    """List all supported commands with examples."""
    return make_result(
        intent, None, "success",
        "Here are all the commands I support! 😊\n\n"
        "📁 **FILES & FOLDERS**\n"
        "   • create file [name] - Create a new file\n"
        "   • create folder [name] - Create a new folder\n"
        "   • delete file [name] - Delete a file\n"
        "   • delete folder [name] - Delete a folder\n"
        "   • rename file [old] to [new] - Rename a file\n"
        "   • rename folder [old] to [new] - Rename a folder\n"
        "   • copy file [name] to [location] - Copy a file\n"
        "   • copy folder [name] to [location] - Copy a folder\n"
        "   • move file [name] to [location] - Move a file\n"
        "   • move folder [name] to [location] - Move a folder\n"
        "   • open file [name] - Open a file\n"
        "   • open folder [name] - Open a folder\n"
        "   • search file [name] - Search for a file\n"
        "   • search folder [name] - Search for a folder\n\n"
        " **APPS & SYSTEM**\n"
        "   • open [app name] - Open any application\n"
        "   • close [app name] - Close an application\n"
        "   • list apps - Show running applications\n"
        "   • empty trash - Empty the trash/recycle bin\n"
        "   • lock screen - Lock your computer\n"
        "   • take screenshot - Capture screen\n"
        "   • volume up/down/mute - Control volume\n"
        "   • brightness up/down - Control brightness\n\n"
        "🌐 **WEB & DOCUMENTS**\n"
        "   • search web [topic] - Search the internet\n"
        "   • open website [url] - Open a website\n"
        "   • generate document [topic] - Create Word doc\n"
        "   • create pdf [topic] - Create PDF document\n"
        "   • create excel [topic] - Create spreadsheet\n\n"
        "💡 **EXAMPLES**\n"
        "   • \"open vs code\"\n"
        "   • \"create folder Projects\"\n"
        "   • \"search for my photos\"\n"
        "   • \"empty the trash\"\n"
        "   • \"write a document about AI\"\n\n"
        "Just tell me what you need in plain English! ✨",
    )


def _handle_unknown(intent, command, parsed):
    """Handle unknown intent - check for follow-up responses first."""
    # Check if this is a follow-up response to a pending question
    try:
        from system.conversation_manager import get_conversation_manager
        manager = get_conversation_manager()
        
        if manager.has_pending_questions():
            # Try to match the response to a pending question
            cmd_lower = command.lower().strip()
            
            # Check for numbered responses: "number 1", "do 1", "option 1", etc.
            import re
            number_match = re.search(r'(?:number|option|do|choose|pick|select)\s*(\d+)', cmd_lower)
            
            if number_match:
                option_num = int(number_match.group(1))
                pending = manager.get_pending_questions()
                
                if pending and option_num > 0:
                    # Get the last pending question
                    last_question = pending[-1]
                    options = last_question.get("options", [])
                    
                    if option_num <= len(options):
                        selected_option = options[option_num - 1]
                        
                        # Clear the pending question
                        manager.clear_pending()
                        
                        # Handle the selected option
                        return _handle_follow_up_option(intent, command, selected_option, last_question)
            
            # Check for yes/no responses
            if cmd_lower in ["yes", "y", "yeah", "sure", "ok", "okay"]:
                manager.clear_pending()
                return make_result(
                    "follow_up", command, "success",
                    "Great! Let me help you with that. What would you like me to do?"
                )
            elif cmd_lower in ["no", "n", "nope", "nah"]:
                manager.clear_pending()
                return make_result(
                    "follow_up", command, "success",
                    "No problem! Let me know if you need anything else."
                )
    except Exception as e:
        print(f"[Follow-up] Error: {e}")
    
    # Original unknown handler
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


def _handle_follow_up_option(intent, command, selected_option, question_context):
    """Handle a selected follow-up option."""
    option_lower = selected_option.lower()
    
    # Document generation follow-ups
    if "pdf" in option_lower or "word" in option_lower:
        if "pdf" in option_lower:
            return make_result(
                "follow_up", command, "success",
                "I'll convert it to PDF for you! The PDF version will be saved alongside the Excel file."
            )
        else:
            return make_result(
                "follow_up", command, "success",
                "I'll create a Word version for you! The Word document will be saved alongside the Excel file."
            )
    
    elif "title page" in option_lower:
        return make_result(
            "follow_up", command, "success",
            "I'll add a professional title page with the document name and date!"
        )
    
    elif "table of contents" in option_lower:
        return make_result(
            "follow_up", command, "success",
            "I'll include a table of contents to help navigate the document!"
        )
    
    elif "format" in option_lower or "professionally" in option_lower:
        return make_result(
            "follow_up", command, "success",
            "I'll format it professionally with proper headings, spacing, and styling!"
        )
    
    # Generic follow-up
    return make_result(
        "follow_up", command, "success",
        f"Got it! I'll {selected_option.lower()}. Let me work on that for you!"
    )


def _handle_system_info(intent, command, parsed):
    """Show detailed system information."""
    import platform
    import psutil
    from system.environment_scanner import get_scanner, get_environment_stats, initialize_environment
    
    try:
        # Ensure environment is initialized
        scanner = get_scanner()
        if not scanner.drives or not scanner.apps:
            # Initialize if empty
            initialize_environment()
        
        stats = get_environment_stats()
        
        # OS Info
        os_name = platform.system()
        os_version = platform.version()
        os_release = platform.release()
        
        # Hardware Info
        cpu_count = psutil.cpu_count(logical=True)
        ram_total = psutil.virtual_memory().total / (1024**3)  # GB
        ram_used = psutil.virtual_memory().used / (1024**3)  # GB
        ram_percent = psutil.virtual_memory().percent
        
        # Disk Info
        disk_usage = psutil.disk_usage('/')
        disk_total = disk_usage.total / (1024**3)  # GB
        disk_free = disk_usage.free / (1024**3)  # GB
        disk_percent = disk_usage.percent
        
        # Environment Stats
        apps_count = stats.get('total_apps', 0)
        drives_count = stats.get('total_drives', 0)
        folders_count = stats.get('total_folders', 0)
        
        message = (
            f"**System Information**\n\n"
            f"**Operating System:** {os_name} {os_release} (Version: {os_version})\n\n"
            f"**Hardware:**\n"
            f"  • CPU Cores: {cpu_count}\n"
            f"  • RAM: {ram_used:.1f} GB / {ram_total:.1f} GB ({ram_percent}% used)\n"
            f"  • Disk: {disk_free:.1f} GB free / {disk_total:.1f} GB ({disk_percent}% used)\n\n"
            f"**Environment:**\n"
            f"  • Installed Apps: {apps_count}\n"
            f"  • Available Drives: {drives_count}\n"
            f"  • Important Folders: {folders_count}\n\n"
            f"If you want, I can also help optimize this process or show more details about any specific area."
        )
        
        return make_result(intent, None, "success", message)
    except Exception as e:
        return make_result(intent, None, "failed", f"Couldn't retrieve system info: {str(e)}")


def _handle_troubleshoot(intent, command, parsed):
    """Handle troubleshooting and diagnostic requests."""
    import platform
    import psutil
    
    cmd_lower = command.lower()
    
    # Analyze the issue
    issues = []
    suggestions = []
    
    # Check RAM usage
    ram = psutil.virtual_memory()
    if ram.percent > 85:
        issues.append(f"High RAM usage: {ram.percent}%")
        suggestions.append("Close unnecessary applications to free up memory")
    
    # Check disk space
    disk = psutil.disk_usage('/')
    if disk.percent > 90:
        issues.append(f"Low disk space: {disk.percent}% used")
        suggestions.append("Delete unnecessary files or empty trash")
    elif disk.percent > 80:
        suggestions.append(f"Disk usage at {disk.percent}% - consider cleaning up old files")
    
    # Check CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 90:
        issues.append(f"High CPU usage: {cpu_percent}%")
        suggestions.append("Check for resource-intensive processes")
    
    # Check running processes count
    proc_count = len(psutil.pids())
    if proc_count > 300:
        suggestions.append(f"Many processes running ({proc_count}) - consider closing unused apps")
    
    # Build response
    if issues:
        message = "⚠️ **Diagnostic Results**\n\n"
        message += "**Issues Found:**\n"
        for issue in issues:
            message += f"  • {issue}\n"
        message += "\n**Recommendations:**\n"
        for sug in suggestions:
            message += f"  • {sug}\n"
    else:
        message = "✅ **System Health Check**\n\n"
        message += "Your computer appears to be running normally.\n\n"
        message += "**Current Status:**\n"
        message += f"  • RAM: {ram.percent}% used\n"
        message += f"  • Disk: {disk.percent}% used\n"
        message += f"  • CPU: {cpu_percent}%\n"
        message += f"  • Processes: {proc_count}\n\n"
        if suggestions:
            message += "**Tips:**\n"
            for sug in suggestions:
                message += f"  • {sug}\n"
    
    message += "\nWould you like me to help with any specific issue?"
    
    return make_result(intent, None, "success", message)


def _handle_automation_task(intent, command, parsed):
    """Handle automation and organization tasks."""
    cmd_lower = command.lower()
    
    # Determine the type of automation
    if any(w in cmd_lower for w in ["organize", "cleanup", "clean up", "tidy"]):
        message = ("🗂️ **File Organization**\n\n"
                   "I can help you organize your files! Here's what I can do:\n\n"
                   "**Available Actions:**\n"
                   "  • Sort files by type (documents, images, videos)\n"
                   "  • Move files to appropriate folders\n"
                   "  • Clean up Desktop or Downloads\n"
                   "  • Find and remove duplicate files\n\n"
                   "**Example commands:**\n"
                   "  • 'organize my desktop'\n"
                   "  • 'clean up downloads folder'\n"
                   "  • 'find duplicate photos'\n\n"
                   "What would you like me to organize?")
    elif any(w in cmd_lower for w in ["duplicate", "similar"]):
        message = ("🔍 **Duplicate Finder**\n\n"
                   "I can help you find duplicate files!\n\n"
                   "**What I can search for:**\n"
                   "  • Duplicate photos\n"
                   "  • Duplicate documents\n"
                   "  • Files with same content\n\n"
                   "**Example:** 'find duplicate photos in Pictures folder'\n\n"
                   "Where should I search for duplicates?")
    elif any(w in cmd_lower for w in ["sort", "arrange", "categorize"]):
        message = (" **File Sorting**\n\n"
                   "I can sort your files automatically!\n\n"
                   "**Sorting options:**\n"
                   "  • By file type (PDF, DOCX, JPG, etc.)\n"
                   "  • By date (today, this week, this month)\n"
                   "  • By size (small, medium, large)\n\n"
                   "Which folder would you like me to sort?")
    else:
        message = (" **Automation Assistant**\n\n"
                   "I can help automate repetitive tasks!\n\n"
                   "**What I can automate:**\n"
                   "  • File organization\n"
                   "  • Document generation\n"
                   "  • Batch renaming\n"
                   "  • Regular backups\n\n"
                   "Tell me what task you'd like to automate.")
    
    return make_result(intent, None, "success", message)


def _handle_send_email(command, parsed):
    """Handle send_email intent - compose and send email."""
    try:
        from ai_assistant.tools import EmailTool
        
        # Extract email details from command
        to_email = parsed.get("to", "")
        subject = parsed.get("subject", "")
        body = parsed.get("body", "")
        
        # Try to extract email from command
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, command)
        if emails and not to_email:
            to_email = emails[0]
        
        # Extract subject if mentioned
        subject_match = re.search(r'(?:subject|title)\s+(?:is\s+)?["\']?([^"\']+)["\']?', command, re.IGNORECASE)
        if subject_match and not subject:
            subject = subject_match.group(1).strip()
        
        email_tool = EmailTool()
        result = email_tool.execute(
            action="compose",
            to=to_email,
            subject=subject,
            body=body
        )
        
        if result.success:
            message = f"📧 {result.message}"
            return make_result("send_email", result.data, "success", message)
        else:
            return make_result("send_email", None, "error", f"❌ Failed to compose email: {result.error}")
    
    except Exception as e:
        return make_result("send_email", None, "error", f"❌ Email error: {str(e)}")


def _handle_open_email(command, parsed):
    """Handle open_email intent - open email client."""
    try:
        from ai_assistant.tools import EmailTool
        
        # Determine which email client to open
        cmd_lower = command.lower()
        client = "default"
        
        if "gmail" in cmd_lower:
            client = "gmail"
        elif "outlook" in cmd_lower:
            client = "outlook"
        elif "yahoo" in cmd_lower:
            client = "yahoo"
        
        email_tool = EmailTool()
        
        if client == "default":
            result = email_tool.execute(action="open_client")
        else:
            result = email_tool.execute(action="open_webmail", client=client)
        
        if result.success:
            message = f"📧 {result.message}"
            return make_result("open_email", result.data, "success", message)
        else:
            return make_result("open_email", None, "error", f"❌ Failed to open email: {result.error}")
    
    except Exception as e:
        return make_result("open_email", None, "error", f"❌ Email error: {str(e)}")


def _handle_retrain_model(command, parsed):
    """Handle retrain_model intent - retrain the NLU model."""
    try:
        from system.auto_learner import force_retrain, get_learning_report
        
        # Get current learning stats
        report = get_learning_report()
        
        # Force retrain
        result = force_retrain()
        
        message = (
            "🧠 **Model Retraining Started**\n\n"
            f"**Learning Stats:**\n"
            f"  • Total commands learned: {report.get('total_commands', 0)}\n"
            f"  • Successful commands: {report.get('successful_commands', 0)}\n"
            f"  • Patterns learned: {report.get('learned_patterns_count', 0)}\n\n"
            f"**Status:** {result.get('message', 'Retraining in background')}\n\n"
            "The model will improve from your usage patterns."
        )
        
        return make_result("retrain_model", result, "success", message)
    
    except Exception as e:
        return make_result("retrain_model", None, "error", f"❌ Retrain error: {str(e)}")


def _handle_merge_training_data(command, parsed):
    """Handle merge_training_data intent - merge learned patterns into dataset."""
    try:
        from system.auto_learner import merge_learned_patterns_to_dataset
        
        result = merge_learned_patterns_to_dataset()
        
        if result.get("status") == "success":
            message = (
                "📊 **Training Data Merged**\n\n"
                f"**New samples added:** {result.get('new_samples_added', 0)}\n"
                f"**Dataset:** {result.get('dataset_path', 'ml/dataset.csv')}\n\n"
                "Run 'retrain model' to update the AI with new data."
            )
            return make_result("merge_training_data", result, "success", message)
        else:
            return make_result("merge_training_data", None, "error", f"❌ Merge error: {result.get('message', 'Unknown error')}")
    
    except Exception as e:
        return make_result("merge_training_data", None, "error", f"❌ Merge error: {str(e)}")


def _handle_analyze_document(command, parsed):
    """Handle analyze_document intent - analyze and summarize documents."""
    try:
        from automation.document_analyzer import analyze_document
        
        # Extract file path from command or parsed data
        file_path = parsed.get("path") or parsed.get("entity") or ""
        
        # If no path in parsed data, try to extract from command
        if not file_path:
            import re
            # Look for file paths in the command
            path_patterns = [
                r'(?:analyze|summarize|read)\s+(?:this|the|my)?\s*(?:file|document|doc)?\s*[:\-]?\s*(.+)',
                r'(?:path|file|document)\s+is\s+(.+)',
                r'(.+\.\w+)',  # Any file with extension
            ]
            for pattern in path_patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    file_path = match.group(1).strip()
                    break
        
        if not file_path:
            return make_result(
                "analyze_document", None, "failed",
                "📄 **Document Analysis**\n\n"
                "Please provide a document to analyze. You can:\n"
                "  • Drag and drop a file\n"
                "  • Type the file path\n"
                "  • Say 'analyze this document' after opening a file\n\n"
                "**Supported formats:** PDF, DOCX, TXT, MD, CSV, JSON, XML, HTML"
            )
        
        # Analyze the document
        result = analyze_document(file_path)
        
        if result.get("status") == "success":
            analysis = result.get("analysis", {})
            
            # Build formatted response
            message_parts = [
                "📊 **Document Analysis Complete**\n",
                f"**File:** {result.get('file_name', 'Unknown')}",
                f"**Size:** {result.get('file_size', 'Unknown')}",
                f"**Words:** {result.get('word_count', 0):,}",
                "",
                "📝 **Summary:**",
                analysis.get("summary", "No summary available."),
                "",
                " **Key Points:**",
            ]
            
            # Add key points
            key_points = analysis.get("key_points", [])
            if key_points:
                for i, point in enumerate(key_points[:7], 1):
                    message_parts.append(f"  {i}. {point}")
            else:
                message_parts.append("  • No key points extracted.")
            
            # Add main topics if available
            topics = analysis.get("main_topics", [])
            if topics:
                message_parts.append("")
                message_parts.append("🏷️ **Main Topics:**")
                message_parts.append("  • " + ", ".join(topics[:5]))
            
            # Add action items if available
            action_items = analysis.get("action_items", [])
            if action_items:
                message_parts.append("")
                message_parts.append("✅ **Action Items:**")
                for i, item in enumerate(action_items[:5], 1):
                    message_parts.append(f"  {i}. {item}")
            
            message = "\n".join(message_parts)
            
            return make_result("analyze_document", result, "success", message)
        else:
            return make_result(
                "analyze_document", None, "failed",
                f"❌ {result.get('message', 'Failed to analyze document')}"
            )
    
    except Exception as e:
        return make_result("analyze_document", None, "error", f"❌ Analysis error: {str(e)}")


# =====================================================================
#  DISPATCH TABLE
# =====================================================================

def _handle_show_path(intent, command, parsed):
    """Show path of last found item (context-aware)."""
    # Try to get last found paths from conversation context
    try:
        from system.conversation_manager import conversation_manager
        context = conversation_manager.active_conversation or {}
        last_paths = context.get("last_found_paths", [])
        last_query = context.get("last_query", "")
        
        if last_paths:
            lines = [f"Here's the path for '{last_query}':"]
            lines.append("")
            for path in last_paths[:5]:
                lines.append(f"  • {path}")
            lines.append("")
            lines.append("💡 **Tip:** Click on any path above to open it in Finder!")
            
            return make_result(
                intent, last_query, "success",
                "\n".join(lines),
                {"file_list": last_paths}
            )
        else:
            return make_result(
                intent, None, "failed",
                "I don't have a recent search result. Try using 'find [name]' first, then ask for the path!"
            )
    except:
        return make_result(
            intent, None, "failed",
            "I couldn't retrieve the path. Try using 'find [name]' to search for the file!"
        )


def _handle_os_command(intent, command, parsed):
    """Handle OS-specific command queries (system info, disk usage, etc.)."""
    from system.os_commands import get_os_commands, get_command_for_action
    from system.auto_learner import get_os_command_suggestions
    
    # Extract the action from the command
    action = parsed.get("entity") or command
    
    # Clean up action
    for prefix in ["show ", "get ", "give me ", "display ", "run "]:
        if action.lower().startswith(prefix):
            action = action[len(prefix):].strip()
            break
    
    # Special case: List installed applications (check both command and action)
    cmd_lower = command.lower()
    if ("list" in cmd_lower and "app" in cmd_lower) or ("list" in action.lower() and "app" in action.lower()):
        print(f"[DEBUG] List apps detected! Command: {command}, Action: {action}")
        try:
            from system.environment_scanner import get_installed_apps, initialize_environment, get_scanner
                
            print("[DEBUG] Initializing environment...")
            # Ensure environment is initialized
            initialize_environment()
            
            # Debug: check scanner state
            scanner = get_scanner()
            print(f"[DEBUG] Scanner apps count after init: {len(scanner.apps)}")
                
            print("[DEBUG] Getting installed apps...")
            apps = get_installed_apps()
            print(f"[DEBUG] Found {len(apps)} apps")
            if apps:
                print(f"[DEBUG] First 3 apps: {list(apps.keys())[:3]}")
                
            if apps:
                lines = [f"📱 **Installed Applications** ({len(apps)} found):", ""]
                # Sort apps by name
                sorted_apps = sorted(apps.items(), key=lambda x: x[1].get('display_name', x[0]))
                for i, (key, app_info) in enumerate(sorted_apps[:50], 1):  # Show first 50
                    display_name = app_info.get('display_name', key)
                    lines.append(f"{i}. {display_name}")
                    
                if len(apps) > 50:
                    lines.append("")
                    lines.append(f"  ... and {len(apps) - 50} more apps")
                    
                result_message = "\n".join(lines)
                print(f"[DEBUG] Returning result with {len(lines)} lines")
                return make_result(
                    intent, action, "success",
                    result_message
                )
            else:
                print("[DEBUG] No apps found")
                return make_result(
                    intent, action, "failed",
                    "No applications found. Try clicking the refresh button (↻) to scan your system."
                )
        except Exception as e:
            print(f"[DEBUG] Error in list apps: {e}")
            import traceback
            traceback.print_exc()
            return make_result(
                intent, action, "failed",
                f"Error listing apps: {str(e)}"
            )
    
    # Try to find matching OS command
    os_cmd = get_command_for_action(action)
    
    # If no exact match, try fuzzy matching
    if not os_cmd:
        import difflib
        from system.os_commands import MACOS_COMMANDS, WINDOWS_COMMANDS, LINUX_COMMANDS, CROSS_PLATFORM_COMMANDS
        
        # Get commands for current OS
        import platform
        system = platform.system()
        if system == "Darwin":
            os_commands = {**MACOS_COMMANDS, **CROSS_PLATFORM_COMMANDS}
        elif system == "Windows":
            os_commands = {**WINDOWS_COMMANDS, **CROSS_PLATFORM_COMMANDS}
        elif system == "Linux":
            os_commands = {**LINUX_COMMANDS, **CROSS_PLATFORM_COMMANDS}
        else:
            os_commands = CROSS_PLATFORM_COMMANDS
        
        # Try to find close match
        action_lower = action.lower()
        matches = difflib.get_close_matches(action_lower, os_commands.keys(), n=1, cutoff=0.6)
        
        if matches:
            os_cmd = os_commands[matches[0]]
    
    if os_cmd:
        # Found matching command - execute it
        log_action(intent, action, f"running OS command: {os_cmd}")
        from automation.app_tasks import run_terminal_command
        result = run_terminal_command(os_cmd)
        
        # Auto-learn
        try:
            from system.auto_learner import learn_os_command_usage
            learn_os_command_usage(os_cmd, action, result.get("status") == "success")
        except:
            pass
        
        return make_result(
            intent, action, result.get("status", "failed"),
            result.get("message", ""),
            result
        )
    else:
        # No exact match - show suggestions
        suggestions = get_os_command_suggestions(action)
        
        if suggestions:
            lines = [f"I don't have an exact command for '{action}', but here are similar OS commands:"]
            lines.append("")
            for i, sug in enumerate(suggestions[:5], 1):
                lines.append(f"  {i}. **{sug['action']}** → `{sug['command']}`")
            lines.append("")
            lines.append("💡 **Tip:** Say 'run [command name]' to execute any of these!")
            
            return make_result(
                intent, action, "success",
                "\n".join(lines),
                {"suggestions": suggestions}
            )
        else:
            return make_result(
                intent, action, "failed",
                f"I don't have a specific OS command for '{action}'. Try: 'system info', 'disk usage', 'network info', etc."
            )


def _handle_computer_scan(intent, command, parsed):
    """Handle computer scan requests - scan hardware, peripherals, OS."""
    try:
        from system.computer_scanner import scan_computer
        
        log_action(intent, "computer", "scanning full system")
        
        # Run the scan
        results = scan_computer()
        
        # Format the results
        lines = ["🖥️ **Computer Scan Complete!**"]
        lines.append("")
        lines.append(f"**Operating System:** {results['os_info']['system']} {results['os_info']['release']}")
        lines.append(f"**CPU:** {results['cpu_info']['brand']} ({results['cpu_info']['cores']} cores)")
        lines.append(f"**RAM:** {results['memory_info']['total']}")
        lines.append("")
        
        # GPU
        if results['gpu_info']:
            gpu_names = [g['name'] for g in results['gpu_info'] if g.get('name') != 'Unknown']
            if gpu_names:
                lines.append(f"**GPU:** {', '.join(gpu_names)}")
        
        # Storage
        if results['storage_info']:
            lines.append(f"**Storage:** {len(results['storage_info'])} drive(s)")
            for drive in results['storage_info'][:3]:
                lines.append(f"  • {drive.get('name', 'Unknown')}: {drive.get('total', 'Unknown')}")
        
        lines.append("")
        
        # USB Devices
        if results['usb_devices']:
            lines.append(f"**USB Devices:** {len(results['usb_devices'])} connected")
            for device in results['usb_devices'][:5]:
                lines.append(f"  • {device.get('name', 'Unknown')}")
            if len(results['usb_devices']) > 5:
                lines.append(f"  • ... and {len(results['usb_devices']) - 5} more")
        
        lines.append("")
        
        # Bluetooth
        if results['bluetooth_devices']:
            lines.append(f"**Bluetooth:** {len(results['bluetooth_devices'])} device(s)")
            for device in results['bluetooth_devices'][:5]:
                lines.append(f"  • {device.get('name', 'Unknown')}")
        
        lines.append("")
        
        # Network
        if results['network_info']:
            lines.append(f"**Network:** {len(results['network_info'])} interface(s)")
            for iface in results['network_info'][:3]:
                lines.append(f"  • {iface.get('name', 'Unknown')}")
        
        lines.append("")
        
        # Displays
        if results['display_info']:
            lines.append(f"**Displays:** {len(results['display_info'])} monitor(s)")
            for display in results['display_info'][:3]:
                lines.append(f"  • {display.get('name', 'Unknown')}")
        
        lines.append("")
        
        # Audio
        if results['audio_devices']:
            lines.append(f"**Audio:** {len(results['audio_devices'])} device(s)")
            for device in results['audio_devices'][:3]:
                lines.append(f"  • {device.get('name', 'Unknown')}")
        
        lines.append("")
        
        # Battery
        if results['battery_info'].get('present'):
            lines.append(f"**Battery:** {results['battery_info'].get('status', 'Present')}")
        
        lines.append("")
        lines.append("💡 **Tip:** Full scan results saved to `learning/computer_scan.json`")
        
        return make_result(
            intent, "computer", "success",
            "\n".join(lines),
            {"scan_results": results}
        )
    except Exception as e:
        return make_result(
            intent, "computer", "failed",
            f"❌ Scan failed: {str(e)}"
        )


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
    "empty_trash": _handle_empty_trash,
    "open_file": _handle_open_file,
    "read_file": _handle_read_file,
    "rename_file": _handle_rename_file,
    "move_file": _handle_move_file,
    "copy_file": _handle_copy_file,
    "search_file": _handle_search_file,
    "find_anything": _handle_find_anything,
    "show_path": _handle_show_path,
    "os_command": _handle_os_command,
    "computer_scan": _handle_computer_scan,
    "generate_document": _handle_generate_document,
    "open_website": _handle_open_website,
    "search_web": _handle_search_web,
    "search_app": _handle_search_app,
    "run_command": _handle_run_command,
    "list_processes": _handle_list_processes,
    "create_project": _handle_create_project,
    "greeting": _handle_greeting,
    "help_request": _handle_help_request,
    "list_commands": _handle_list_commands,
    "system_info": _handle_system_info,
    "troubleshoot": _handle_troubleshoot,
    "automation_task": _handle_automation_task,
    "send_email": _handle_send_email,
    "open_email": _handle_open_email,
    "retrain_model": _handle_retrain_model,
    "merge_training_data": _handle_merge_training_data,
    "analyze_document": _handle_analyze_document,
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
