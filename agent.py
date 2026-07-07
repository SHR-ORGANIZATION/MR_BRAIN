"""
AMAZON AI - Smart Desktop Agent
Parses natural language commands into file/app/web operations.
Uses ML intent classification + smart entity extraction + keyword overrides.
"""
import os
import sys
import re
import difflib
from pathlib import Path
from intent_router import make_result, route_intent

BASE_DIR = Path(__file__).resolve().parent

# Add project root to path for ml module import
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml.nlu_model import NOVANLU
from system.environment_scanner import initialize_environment, get_scanner

DEFAULT_BASE_DIR = Path(os.path.expanduser("~")) / "Desktop"

# Initialize environment knowledge base at startup
ENV_INDEX = initialize_environment()

LOCATION_DIRS = {
    "desktop": Path(os.path.expanduser("~")) / "Desktop",
    "documents": Path(os.path.expanduser("~")) / "Documents",
    "downloads": Path(os.path.expanduser("~")) / "Downloads",
    "pictures": Path(os.path.expanduser("~")) / "Pictures",
    "music": Path(os.path.expanduser("~")) / "Music",
    "videos": Path(os.path.expanduser("~")) / "Videos",
}

# =====================================================================
#  SYNONYM & KEYWORD TABLES
# =====================================================================

INTENT_SYNONYMS = {
    # File creation
    "create file": "create_file", "make file": "create_file",
    "new file": "create_file", "create text file": "create_file",
    "creat file": "create_file", "creat new file": "create_file",
    # Folder creation
    "create folder": "create_folder", "make folder": "create_folder",
    "new folder": "create_folder", "creat folder": "create_folder",
    "create directory": "create_folder", "make directory": "create_folder",
    "create a folder": "create_folder", "create new folder": "create_folder",
    # Delete file
    "delete file": "delete_file", "remove file": "delete_file",
    "erase file": "delete_file", "del file": "delete_file",
    # Delete folder
    "delete folder": "delete_folder", "remove folder": "delete_folder",
    "erase folder": "delete_folder", "del folder": "delete_folder",
    # Rename
    "rename file": "rename_file", "rename folder": "rename_folder",
    "change name": "rename_file", "change file name": "rename_file",
    "change folder name": "rename_folder",
    # Move
    "move file": "move_file", "move folder": "move_folder",
    "transfer file": "move_file", "transfer folder": "move_folder",
    "put file": "move_file", "put folder": "move_folder",
    # Copy
    "copy file": "copy_file", "copy folder": "copy_folder",
    "duplicate file": "copy_file", "duplicate folder": "copy_folder",
    # Open
    "open file": "open_file", "open folder": "open_folder",
    "open app": "open_app", "launch app": "open_app",
    "close app": "close_app", "exit app": "close_app",
    # Search
    "search file": "search_file", "find file": "search_file",
    "look for file": "search_file", "locate file": "search_file",
    "search folder": "search_folder", "find folder": "search_folder",
    "where is file": "search_file", "where is folder": "search_folder",
    "show me file": "search_file", "show me folder": "search_folder",
    "show file": "search_file", "show folder": "search_folder",
    # Web
    "search web": "search_web", "search for": "search_web",
    "google": "search_web", "search": "search_web",
    "open website": "open_website", "visit website": "open_website",
    # Documents
    "generate document": "generate_document", "create report": "generate_document",
    "generate report": "generate_document", "create document": "generate_document",
    "create assignment": "generate_document", "make assignment": "generate_document",
    "generate assignment": "generate_document", "create research proposal": "generate_document",
    "make research proposal": "generate_document", "generate research proposal": "generate_document",
    "create a report": "generate_document", "make a report": "generate_document",
    # Apps (direct name triggers)
    "open chrome": "open_app", "close chrome": "close_app",
    "open notepad": "open_app", "close notepad": "close_app",
    "open vscode": "open_app", "close vscode": "close_app",
    "open calculator": "open_app", "open paint": "open_app",
    "open word": "open_app", "open excel": "open_app",
    "open powerpoint": "open_app",
    "kill process": "close_app",
    # System
    "list processes": "list_processes",
    "running processes": "list_processes",
    # Apps
    "which apps are running": "list_processes",
    "running apps": "list_processes",
    "what apps are running": "list_processes",
    "what applications are running": "list_processes",
    "which applications are running": "list_processes",
    "apps that are running": "list_processes",
    "applications that are running": "list_processes",
    # Show
    "show running apps": "list_processes",
    "show running applications": "list_processes",
    "show me running apps": "list_processes",
    "show me running applications": "list_processes",
    "show active apps": "list_processes",
    "show active applications": "list_processes",
    "show open apps": "list_processes",
    "show open applications": "list_processes",
    # List
    "list running apps": "list_processes",
    "list running applications": "list_processes",
    "list active apps": "list_processes",
    "list active applications": "list_processes",
    "list open apps": "list_processes",
    "list open applications": "list_processes",
    # Check
    "check running apps": "list_processes",
    "check running applications": "list_processes",
    "check active apps": "list_processes",
    "check open apps": "list_processes",
    # Currently running
    "currently running apps": "list_processes",
    "currently running applications": "list_processes",
    "what is running": "list_processes",
    "what's running": "list_processes",
    "what programs are running": "list_processes",
    "which programs are running": "list_processes",
    # Open programs
    "open programs": "list_processes",
    "opened programs": "list_processes",
    "show open programs": "list_processes",
    "list open programs": "list_processes",
    # Active processes
    "active processes": "list_processes",
    "running tasks": "list_processes",
    "show running tasks": "list_processes",
    "list running tasks": "list_processes",
    # Computer status
    "what is running on my computer": "list_processes",
    "what apps are open": "list_processes",
    "which apps are open": "list_processes",
    "what applications are open": "list_processes",
    "which applications are open": "list_processes",
    "show me what is running": "list_processes",
    "tell me what is running": "list_processes",
    # Software
    "what software is running": "list_processes",
    "which software is running": "list_processes",
    "show running software": "list_processes",
    "list running software": "list_processes",
    # Projects
    "create project": "create_project", "generate project": "create_project",
    "make project": "create_project",
    # Swahili keywords
    "tengeneza faili": "create_file", "tengeneza folder": "create_folder",
    "tengeneza kabrasha": "create_folder", "futa faili": "delete_file",
    "futa folder": "delete_folder", "futa kabrasha": "delete_folder",
    "nakili faili": "copy_file", "nakili folder": "copy_folder",
    "nakili kabrasha": "copy_folder",
    "hamisha faili": "move_file", "hamisha folder": "move_folder",
    "hamisha kabrasha": "move_folder",
    "badilisha jina": "rename_file",
    "tafuta faili": "search_file", "tafuta folder": "search_folder",
    "tafuta kabrasha": "search_folder",
    "fungua programu": "open_app", "fungua app": "open_app",
    "funga programu": "close_app",
    # Single Swahili words (matched by phrase + single-word fallback)
    "tengeneza": "create_file", "futa": "delete_file",
    "nakili": "copy_file", "hamisha": "move_file",
    "tafuta": "search_file", "tafutia": "search_file",
    "findi": "search_file", "fina": "create_folder",
}

ACTION_WORDS = [
    "create", "creat", "make", "generate", "build",
    "delete", "remove", "erase", "del", "destroy",
    "rename", "change name",
    "move", "transfer", "put", "relocate", "send",
    "copy", "duplicate", "clone", "replicate",
    "open", "launch", "start", "run", "opei", "open up",
    "close", "exit", "quit", "kill", "stop",
    "find", "search", "locate", "look for", "look up",
    "read", "show", "display", "view",
    "list", "execute",
    # Natural language prefixes
    "can you", "could you", "would you", "please",
    "show me", "where is", "find me", "search for",
    "look for", "look up",
    # Swahili action words
    "tengeneza", "futa", "nakili", "hamisha", "badilisha jina",
    "tafuta", "tafutia", "fungua", "funga", "findi", "fina",
]

FILLER_WORDS = {
    "called", "named", "known as", "titled", "as",
    "the", "a", "an", "this", "that", "these", "those",
    "new", "old", "here", "there", "please",
    "show me", "for me", "me", "where is", "find me",
    "locate", "look for", "search for",
    # "my" removed - too aggressive, breaks names like "My Project"
}

LOCATION_SYNONYMS = {
    "desktop": "desktop", "desk top": "desktop", "dsktop": "desktop", "desktp": "desktop",
    "documents": "documents", "document": "documents", "documnts": "documents",
    "documets": "documents", "documens": "documents", "docs": "documents",
    "downloads": "downloads", "download": "downloads", "dwnloads": "downloads",
    "downlads": "downloads", "downlaods": "downloads",
    "pictures": "pictures", "picture": "pictures", "pics": "pictures", "picturs": "pictures",
    "photos": "pictures", "images": "pictures",
    "music": "music", "musc": "music", "songs": "music",
    "videos": "videos", "video": "videos", "vids": "videos", "vido": "videos",
}

# Two-target intents (source -> destination)
TWO_TARGET_INTENTS = {"rename_file", "rename_folder", "move_file", "move_folder", "copy_file", "copy_folder"}

# =====================================================================
#  FILE DISCOVERY DETECTION (Type A: Metadata Search)
# =====================================================================

# Maps natural language phrases to discovery_type values
_DISCOVERY_PATTERNS = {
    # --- File discovery ---
    "my last file": "latest_file",
    "my latest file": "latest_file",
    "most recent file": "latest_file",
    "last file": "latest_file",
    "my last assignment": "latest_assignment",
    "my latest assignment": "latest_assignment",
    "last assignment": "latest_assignment",
    "my last coursework": "latest_assignment",
    "my last homework": "latest_assignment",
    "my last proposal": "latest_proposal",
    "my latest proposal": "latest_proposal",
    "last proposal": "latest_proposal",
    "my last report": "latest_report",
    "my latest report": "latest_report",
    "last report": "latest_report",
    "pdfs downloaded today": "pdfs_today",
    "pdf downloaded today": "pdfs_today",
    "pdfs today": "pdfs_today",
    "downloaded today": "pdfs_today",
    "today downloads": "pdfs_today",
    # --- Folder discovery ---
    "my last folder": "latest_folder",
    "my latest folder": "latest_folder",
    "last folder": "latest_folder",
    "my last project folder": "latest_project_folder",
    "my latest project folder": "latest_project_folder",
    "my last project": "latest_project_folder",
    "my latest project": "latest_project_folder",
    "last project folder": "latest_project_folder",
    "my last assignment folder": "latest_assignment_folder",
    "my latest assignment folder": "latest_assignment_folder",
    # --- Discovery with topic keywords ---
    "folder with networking": "find_anywhere",
    "folder with": "find_anywhere",
    "project with networking": "find_anywhere",
    "project with": "find_anywhere",
    # --- Full computer search ---
    "find anywhere": "find_anywhere",
    "find anywhere on computer": "find_anywhere",
    "search computer": "search_computer",
    "search my computer": "search_computer",
    "find on computer": "search_computer",
    "search all drives": "search_computer",
}

# Words that indicate folder discovery (not file)
_FOLDER_HINT_WORDS = {"folder", "directory", "dir", "project", "projects", "workspace", "repo"}


def _detect_discovery_type(command):
    """Check if command contains a file/folder discovery pattern. Returns discovery_type or None."""
    cmd_lower = command.lower()
    # Check longest patterns first (folder patterns are typically longer, so they win)
    for phrase, dtype in sorted(_DISCOVERY_PATTERNS.items(), key=lambda x: len(x[0]), reverse=True):
        if phrase in cmd_lower:
            return dtype
    # Pattern: "open folder with <topic>", "folder with <topic>", "find folder with <topic>"
    m = re.search(r'\b(?:open|find|search)\s+(?:the\s+)?folder\s+with\s+(.+?)(?:\s+folder|\s+file)?\s*$', cmd_lower)
    if m:
        query = m.group(1).strip()
        if query:
            return "find_anywhere"
    # Pattern: "folder <topic>", "project <topic>" where <topic> is not already matched
    m = re.search(r'\b(?:open|find|search)\s+(?:the\s+)?(?:folder|project|workspace)\s+(?!with\b)(\w+)\s*$', cmd_lower)
    if m:
        query = m.group(1).strip()
        if query and len(query) > 2:
            return "find_anywhere"
    # Regex fallback: "my last/ latest <keyword>"
    m = re.search(r'\bmy\s+(?:last|latest)\s+(\w+)\b', cmd_lower)
    if m:
        word = m.group(1).lower()
        # Check folder keywords first if folder hint word follows
        has_folder_hint = any(hw in cmd_lower for hw in _FOLDER_HINT_WORDS)
        if has_folder_hint:
            from automation.file_discovery import FOLDER_DISCOVERY_KEYWORDS
            for dtype, keywords in FOLDER_DISCOVERY_KEYWORDS.items():
                if word in keywords:
                    return dtype
            if has_folder_hint:
                return "latest_folder"
        # Check file keywords
        from automation.file_discovery import DISCOVERY_KEYWORDS
        for dtype, keywords in DISCOVERY_KEYWORDS.items():
            if word in keywords:
                return dtype
    # Regex fallback for computer-wide search: "search my computer for X", "find X on computer"
    m = re.search(r'\b(?:search|find)\s+(?:my\s+)?computer\s+(?:for\s+)?(.+?)(?:\s+folder|\s+file|\s+document)?\s*$', cmd_lower)
    if m:
        query = m.group(1).strip()
        if query and not any(q in query for q in ["folder", "directory", "dir"]):
            return "search_computer"
    return None


# =====================================================================
#  SEMANTIC QUERY DETECTION (Type B: Content-Based Discovery)
# =====================================================================

# Regex patterns that extract a topic from natural language
_SEMANTIC_PATTERNS = [
    # "about <topic>" at end of command
    re.compile(r'\babout\s+(.+?)(?:\s+file|\s+folder|\s+document|\s+report|\s+proposal|$)', re.I),
    # "discussing <topic>"
    re.compile(r'\bdiscussing\s+(.+?)(?:\s+file|\s+folder|\s+document|\s+report|\s+proposal|$)', re.I),
    # "related to <topic>"
    re.compile(r'\brelated\s+to\s+(.+?)(?:\s+file|\s+folder|\s+document|\s+report|\s+proposal|$)', re.I),
    # "covering <topic>"
    re.compile(r'\bcovering\s+(.+?)(?:\s+file|\s+folder|\s+document|\s+report|\s+proposal|$)', re.I),
    # "on the topic of <topic>"
    re.compile(r'\bon\s+the\s+topic\s+of\s+(.+?)(?:\s+file|\s+folder|\s+document|\s+report|\s+proposal|$)', re.I),
    # "on <topic>" (only after document-type nouns to avoid false positives)
    re.compile(r'\b(?:notes?|report|document|proposal|presentation|assignment)\s+on\s+(.+)', re.I),
]

# Words that should NOT trigger semantic detection (common prepositions etc.)
_SEMANTIC_BLOCK_WORDS = {"the", "a", "an", "it", "this", "that", "my", "your", "our"}


def _detect_semantic_query(command):
    """
    Detect if command contains a semantic search pattern (content-based).
    Returns the extracted topic string, or None.

    Examples:
        "open the proposal about AI" → "AI"
        "show the document discussing subnetting" → "subnetting"
        "find files related to networking" → "networking"
    """
    cmd = command.strip()
    for pattern in _SEMANTIC_PATTERNS:
        m = pattern.search(cmd)
        if m:
            topic = m.group(1).strip().rstrip("?!. ")
            # Validate: topic must have meaningful content
            words = topic.split()
            if words and words[0].lower() not in _SEMANTIC_BLOCK_WORDS:
                return topic
            elif len(words) > 1:  # "the AI" is still valid if multi-word
                return topic
    return None


# =====================================================================
#  SMART PARSER (replaces 20+ extract functions)
# =====================================================================

def _correct_location_name(name):
    """Correct common misspellings of location names."""
    if not name:
        return name
    name_lower = name.lower().strip()
    if name_lower in LOCATION_SYNONYMS:
        return LOCATION_SYNONYMS[name_lower]
    best_match, best_ratio = None, 0
    for correct in LOCATION_DIRS:
        ratio = difflib.SequenceMatcher(None, name_lower, correct).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = correct
    return best_match if best_ratio >= 0.6 else name_lower


def _extract_location_context(command):
    """Extract location context from command. Handles:
    - 'in c:\\path' / 'from c:\\path' (absolute paths)
    - 'in local disk D' / 'on drive D' / 'in disk D' (drive letters by name)
    - 'in documents' / 'from this pc\\documents' (named locations, typo-tolerant)
    Returns (cleaned_command, base_dir) tuple.
    """
    base_dir = None
    cleaned = command

    # 1. Match "in c:\\path" or "from c:\\path" (absolute paths)
    loc_match = re.search(r'\b(?:in|from)\s+([a-zA-Z]:\\[\w\\/. -]+)', command, re.I)
    if loc_match:
        path_text = loc_match.group(1).strip().rstrip('.')
        # Convert trailing "in folder/dir X" into a path component
        path_text = re.sub(r'\s+in\s+(folder|directory|dir)\s+([\w\\/. -]+)$', r'\\\2', path_text, flags=re.I).rstrip()
        base_dir = path_text
        cleaned = command[:loc_match.start()].strip()
        return cleaned, base_dir

    # 2. Match "in/from/on <drive letter name>" with optional subpath
    #    e.g. "in local disk D", "in new volume (E:)", "on drive D:\data", "in D", "in E:"
    #    BUT NOT "in Documents" (D is part of the word)
    drive_match = re.search(
        r'\b(?:in|from|on)\s+(?:(?:local|new|the|my|our|external|internal)\s+)?(?:disk|drive|vol|volume|partition)?\s*'
        r'[\(\[]?([a-zA-Z]):[\)\]]?'
        r'(\\[\w\\/. -]+)?',
        command, re.I
    )
    if drive_match:
        letter = drive_match.group(1).upper()
        raw_subpath = (drive_match.group(2) or "")
        # Strip trailing natural-language connectors like "in folder/dir X" from subpath
        raw_subpath = re.sub(r'\s+in\s+(folder|directory|dir)\s+([\w\\/. -]+)$', r'\\\2', raw_subpath, flags=re.I)
        raw_subpath = raw_subpath.rstrip(". ")
        base_dir = f"{letter}:\\" if not raw_subpath else f"{letter}:\\{raw_subpath.lstrip(chr(92))}"
        before = drive_match.start()
        after_text = command[drive_match.end():].lstrip()
        # Check for trailing "in folder/dir X" → append to base_dir as subpath
        subfolder_match = re.match(r'in\s+(?:folder|directory|dir)\s+([\w\\/. -]+)', after_text, re.I)
        if subfolder_match:
            extra = subfolder_match.group(1).rstrip(". ")
            base_dir = str(Path(base_dir) / extra)
            after_text = after_text[subfolder_match.end():].lstrip()
        cleaned_before = command[:before].rstrip()
        cleaned = (cleaned_before + " " + after_text).strip() if cleaned_before and after_text else (cleaned_before + after_text).strip()
        return cleaned, base_dir

    # 3. Match "in/from <named location>" with flexible prefix (typo-tolerant)
    named_match = re.search(
        r'\b(?:in|from)\s+(?:this\s*\w*[\\/]?)?(?:the\s+|my\s+|computer[\\/]?)?'
        r'(desktop|documents|downloads|pictures|music|videos|document|download|picture|documnts|dsktop|dwnloads)\b',
        command, re.I
    )
    if named_match:
        raw_loc = named_match.group(1)
        loc_name = _correct_location_name(raw_loc)
        if loc_name in LOCATION_DIRS:
            base_dir = str(LOCATION_DIRS[loc_name])
            before = command[:named_match.start()].rstrip()
            after = command[named_match.end():].lstrip()
            cleaned = (before + " " + after).strip() if before and after else (before + after).strip()
            return cleaned, base_dir

    return cleaned, base_dir


def _protect_extensions(text):
    """Replace file extensions with placeholders to protect from keyword stripping."""
    ext_map = {}
    ext_parts = re.findall(r'\.\w+', text)
    for i, ext in enumerate(ext_parts):
        placeholder = f'__EXT{i}__'
        ext_map[placeholder] = ext
        text = text.replace(ext, placeholder, 1)
    return text, ext_map


def _restore_extensions(text, ext_map):
    """Restore file extensions from placeholders."""
    for placeholder, ext in ext_map.items():
        text = text.replace(placeholder, ext)
    return text


TYPE_WORDS = {"file", "files", "folder", "folders", "directory", "directories", "document", "documents", "text file"}


def _strip_action_words(text):
    """Remove action words AND type words from the beginning of text.
    Loops to handle chained prefixes like 'can you open folder named X'.
    """
    max_iterations = 3  # prevent infinite loops
    for _ in range(max_iterations):
        lower = text.lower().strip()
        matched = False
        for word in sorted(ACTION_WORDS, key=len, reverse=True):
            if lower.startswith(word + " ") or lower.startswith(word + "\t"):
                text = text[len(word):].strip()
                # Also strip type words (file, folder, etc.) after action word
                remaining_lower = text.lower()
                for tw in sorted(TYPE_WORDS, key=len, reverse=True):
                    if remaining_lower.startswith(tw + " "):
                        text = text[len(tw):].strip()
                        # Strip connector words after type word (named, called, titled)
                        rem_lower = text.lower()
                        for connector in ["named ", "called ", "titled ", "known as "]:
                            if rem_lower.startswith(connector):
                                text = text[len(connector):].strip()
                                break
                        break
                matched = True
                break
            if lower == word:
                return ""
        if not matched:
            break
    return text


def _strip_filler_words(text):
    """Remove filler words from text, but never strip the last remaining word.
    Skips entirely if text is a file path (contains \\ or :)."""
    if not text:
        return text
    text = text.strip().strip("'\"").strip()
    # If text looks like a file path, don't touch it
    if "\\" in text or ":" in text:
        return text
    lower = text.lower()
    for filler in sorted(FILLER_WORDS, key=len, reverse=True):
        pattern = filler + " "
        if lower.startswith(pattern):
            remaining = text[len(filler):].strip()
            if remaining:  # don't strip if it leaves nothing
                text = remaining
                lower = text.lower()
        # Only strip filler if it's not the only word left
        cleaned = re.sub(r'\b' + re.escape(filler) + r'\b', '', text, flags=re.I)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if cleaned:  # only apply if something remains
            text = cleaned
    return text.strip().strip("'\"").strip()


def _strip_location_phrases(text):
    """Remove location phrases like 'on desktop', 'in documents' from text."""
    if not text:
        return text, None
    text_lower = text.lower()
    for loc in LOCATION_DIRS:
        for preposition in ["on", "in", "from", "at"]:
            phrase = f"{preposition} {loc}"
            if phrase in text_lower:
                loc_idx = text_lower.index(phrase)
                text = (text[:loc_idx] + text[loc_idx + len(phrase):]).strip()
                return text.strip(), str(LOCATION_DIRS[loc])
    return text.strip(), None


def _split_two_targets(text):
    """Split text into source and destination on separator words (to, as, ->)."""
    for sep in [" to ", " as ", " -> ", " 2 "]:
        if sep in text.lower():
            idx = text.lower().index(sep)
            source = text[:idx].strip()
            dest = text[idx + len(sep):].strip()
            return source, dest
    return text.strip(), None


def smart_parse_command(command):
    """Universal command parser. Replaces all extract_* functions.

    Returns dict:
        entity: str or None        -- primary target (file/folder name)
        source: str or None        -- for two-target ops
        destination: str or None   -- for two-target ops
        base_dir: str or None      -- resolved location path
        app_name: str or None      -- for app operations
        search_query: str or None  -- for search operations
    """
    result = {
        "entity": None, "source": None, "destination": None,
        "base_dir": None, "app_name": None, "search_query": None,
        "location_hint": None, "discovery_type": None,
        "semantic_query": None,
    }

    if not command or not command.strip():
        return result

    original = command.strip()

    # Early check: file/folder discovery patterns ("my last file", "pdfs downloaded today", etc.)
    discovery = _detect_discovery_type(original)
    if discovery:
        result["discovery_type"] = discovery
        # For find_anywhere/search_computer, extract the actual search query
        if discovery in ("find_anywhere", "search_computer"):
            cmd_lower = original.lower()
            # Extract topic from "open folder with <topic>", "search my computer for <topic>", etc.
            m = re.search(r'\b(?:open|find|search)\s+(?:the\s+)?(?:folder|project)\s+with\s+(.+?)(?:\s+folder|\s+file)?\s*$', cmd_lower)
            if m:
                result["semantic_query"] = m.group(1).strip()
                result["entity"] = result["semantic_query"]
            else:
                m = re.search(r'\b(?:search|find)\s+(?:my\s+)?computer\s+(?:for\s+)?(.+?)(?:\s+folder|\s+file|\s+document)?\s*$', cmd_lower)
                if m:
                    result["semantic_query"] = m.group(1).strip()
                    result["entity"] = result["semantic_query"]
        # Return early for discovery - don't overwrite entity with app name
        # Step 1: Extract location context (in/from <location>)
        cleaned, base_dir = _extract_location_context(original)
        result["base_dir"] = base_dir
        result["entity"] = result.get("semantic_query") or result.get("entity")
        return result

    # Early check: semantic query patterns ("about AI", "discussing subnetting", etc.)
    semantic_q = _detect_semantic_query(original)
    if semantic_q:
        result["discovery_type"] = "semantic"
        result["semantic_query"] = semantic_q
        # Return early for semantic discovery
        cleaned, base_dir = _extract_location_context(original)
        result["base_dir"] = base_dir
        return result
    
    # Step 1: Extract location context (in/from <location>)
    cleaned, base_dir = _extract_location_context(original)
    result["base_dir"] = base_dir

    # Step 2: Detect intent to know how to parse
    intent = _keyword_intent_override(original)

    # Step 3: Check for app names
    app_name = _extract_app_name_internal(cleaned)
    if app_name:
        result["app_name"] = app_name
        result["entity"] = app_name

    # Step 4: For two-target intents, split on separator
    if intent in TWO_TARGET_INTENTS:
        # Strip the action keyword prefix
        remaining = _strip_action_words(cleaned)
        remaining, loc = _strip_location_phrases(remaining)
        if loc and not result["base_dir"]:
            result["base_dir"] = loc

        # Protect extensions before splitting
        protected, ext_map = _protect_extensions(remaining)
        src_text, dst_text = _split_two_targets(protected)
        src_text = _restore_extensions(src_text, ext_map)
        dst_text = _restore_extensions(dst_text, ext_map) if dst_text else None

        src_text = _strip_filler_words(src_text)
        if dst_text:
            dst_text = _strip_filler_words(dst_text)

        result["source"] = src_text if src_text else None
        result["destination"] = dst_text
        result["entity"] = src_text if src_text else None
        return result

    # Step 5: Single-target extraction
    remaining = _strip_action_words(cleaned)

    # Protect extensions
    protected, ext_map = _protect_extensions(remaining)
    protected = _strip_filler_words(protected)
    protected = _restore_extensions(protected, ext_map)

    # Strip location phrases
    protected, loc = _strip_location_phrases(protected)
    if loc and not result["base_dir"]:
        result["base_dir"] = loc

    # Clean up
    protected = re.sub(r'\b(folder|file|document|directory|path|at)\b', '', protected, flags=re.I)
    protected = re.sub(r'\s+', ' ', protected).strip().strip("'\"").strip()

    # Remove trailing dots/whitespace
    protected = protected.rstrip('. ')

    if protected:
        result["entity"] = protected

    # Step 5b: Extract location hint from entity (e.g. "shakira in project" → entity="shakira", hint="project")
    if result["entity"]:
        entity_text = result["entity"]
        hint_match = re.search(
            r'\b(?:in|inside|under)\s+(?:my\s+|the\s+|our\s+)?(?:folder\s+|directory\s+|dir\s+)?([a-zA-Z][\w\s-]{1,})\s*$',
            entity_text, re.I
        )
        if hint_match:
            hint_raw = hint_match.group(1).strip()
            # Clean filler words from the hint
            for filler in ["folder", "directory", "dir"]:
                hint_raw = re.sub(r'\b' + filler + r'\b', '', hint_raw, flags=re.I).strip()
            hint_raw = re.sub(r'\s+', ' ', hint_raw).strip()
            if hint_raw and len(hint_raw) >= 2:
                result["entity"] = entity_text[:hint_match.start()].rstrip()
                result["location_hint"] = hint_raw

    # Step 6: Handle search queries specially
    if intent in ("search_file", "search_folder", "search_web"):
        result["search_query"] = _extract_search_query_internal(original)

    return result


# =====================================================================
#  LOCATION RESOLVER (filesystem-based path resolution)
# =====================================================================

def resolve_location(hint, base_dir=None):
    """Resolve a location hint to a full filesystem path.

    Searches for a folder matching the hint in priority order:
    base_dir -> Desktop -> Documents -> Downloads -> Home

    Args:
        hint: Natural language location hint (e.g. "project", "my research")
        base_dir: Optional base directory to search first

    Returns:
        Full path string to the resolved directory
    """
    if not hint:
        return base_dir or str(DEFAULT_BASE_DIR)

    # Clean the hint: strip possessives, articles, and type words
    clean_hint = hint.strip()
    for word in ["my", "the", "our", "a", "an"]:
        clean_hint = re.sub(r'\b' + word + r'\b', '', clean_hint, flags=re.I).strip()
    for word in ["folder", "directory", "dir"]:
        clean_hint = re.sub(r'\b' + word + r'\b', '', clean_hint, flags=re.I).strip()
    clean_hint = re.sub(r'\s+', ' ', clean_hint).strip()

    if not clean_hint:
        return base_dir or str(DEFAULT_BASE_DIR)

    # Search directories in priority order
    search_dirs = []
    if base_dir and Path(base_dir).is_dir():
        search_dirs.append(Path(base_dir))
    search_dirs.extend([
        Path(os.path.expanduser("~")) / "Desktop",
        Path(os.path.expanduser("~")) / "Documents",
        Path(os.path.expanduser("~")) / "Downloads",
        Path(os.path.expanduser("~")),
    ])

    # Try case-insensitive exact folder match in each search directory
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        try:
            for item in search_dir.iterdir():
                if item.is_dir() and item.name.lower() == clean_hint.lower():
                    return str(item)
        except PermissionError:
            continue

    # Try partial match (folder name contains the hint or hint contains folder name)
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        try:
            for item in search_dir.iterdir():
                if item.is_dir():
                    name_lower = item.name.lower()
                    hint_lower = clean_hint.lower()
                    if hint_lower in name_lower or name_lower in hint_lower:
                        return str(item)
        except PermissionError:
            continue

    # Fallback: assume user wants to create in base_dir/hint or Desktop/hint
    fallback_base = base_dir if base_dir else str(DEFAULT_BASE_DIR)
    return str(Path(fallback_base) / clean_hint)


# =====================================================================
#  PUBLIC API (backward-compatible wrappers)
# =====================================================================

# Known app names for intent detection (system apps + web apps + dev tools)
KNOWN_APP_NAMES = {
    # System apps
    "chrome", "notepad", "calculator", "paint", "vscode",
    "visual studio code", "word", "excel", "powerpoint", "powershell",
    "file explorer", "explorer", "task manager", "cmd", "command prompt",
    # Developer tools
    "pgadmin", "anydesk", "docker", "git", "node", "npm",
    "xampp", "wamp", "postman", "android studio", "intellij",
    "pycharm", "eclipse", "netbeans", "xampp control panel",
    "mysql", "mongodb", "sqlite", "wireshark", "putty",
    # Web/social apps (opened in browser)
    "tiktok", "youtube", "spotify", "instagram", "facebook", "twitter",
    "whatsapp", "telegram", "netflix", "discord", "slack", "zoom",
    "gmail", "outlook", "github", "reddit", "twitch", "linkedin",
    "google", "bing", "wikipedia", "amazon", "ebay",
    "chatgpt", "claude", "gemini",
    # Communication / productivity
    "teams", "skype", "obs", "vlc", "winrar", "7zip",
    "steam", "epic games", "blender", "figma", "canva",
}


def _extract_app_name_internal(command):
    """Internal app name extraction."""
    command_lower = command.lower()
    for app in sorted(KNOWN_APP_NAMES, key=len, reverse=True):
        if app in command_lower:
            return "vscode" if app == "visual studio code" else app
    return None


def _extract_search_query_internal(command):
    """Internal search query extraction. Strips filler words like 'folder named', 'file called'."""
    cmd_lower = command.lower().strip()
    prefixes = [
        "search for ", "search ", "find ", "locate ",
        "look for ", "look up ", "search web ",
        "google ", "search google for ",
        # Natural language prefixes
        "where is ", "show me ", "find me ", "show ",
        # Swahili prefixes
        "tafuta ", "tafutia ",
    ]
    for prefix in prefixes:
        if cmd_lower.startswith(prefix):
            cmd_lower = cmd_lower[len(prefix):].strip()
            break

    # Strip type + filler combos: "folder named X", "file called X", "folder X"
    search_filler_patterns = [
        r'^folder\s+named\s+', r'^file\s+named\s+', r'^folder\s+called\s+',
        r'^file\s+called\s+', r'^folder\s+titled\s+', r'^file\s+titled\s+',
        r'^directory\s+named\s+', r'^directory\s+called\s+',
        r'^named\s+', r'^called\s+', r'^titled\s+',
        r'^folder\s+', r'^file\s+', r'^directory\s+',
    ]
    for pattern in search_filler_patterns:
        cmd_lower = re.sub(pattern, '', cmd_lower, flags=re.I).strip()

    return cmd_lower if cmd_lower else command.lower().strip()


def extract_app_name(command):
    """Extract application name from command."""
    return _extract_app_name_internal(command)


def extract_folder_name(command):
    """Extract folder name from command (for create/open folder)."""
    parsed = smart_parse_command(command)
    name = parsed.get("entity")
    base_dir = parsed.get("base_dir")
    location_hint = parsed.get("location_hint")
    if name:
        # If it's already a full path, use as-is
        if "\\" in name or "/" in name or ":" in name:
            return name
        # If location_hint was extracted, resolve it via filesystem search
        if location_hint:
            resolved = resolve_location(location_hint, base_dir)
            return str(Path(resolved) / name)
        # If base_dir was extracted (e.g. "in local disk D"), use it
        if base_dir:
            return str(Path(base_dir) / name)
        # Default to Desktop
        return str(DEFAULT_BASE_DIR / name)
    return None


def extract_delete_folder_name(command):
    """Extract folder name for deletion."""
    parsed = smart_parse_command(command)
    return parsed.get("entity")


def extract_file_name(command):
    """Extract file name from command (for create/open/read/delete file)."""
    parsed = smart_parse_command(command)
    name = parsed.get("entity")
    base_dir = parsed.get("base_dir")
    location_hint = parsed.get("location_hint")
    if name:
        # If it's already a full path, use as-is
        if "\\" in name or "/" in name or ":" in name:
            return name
        # If location_hint was extracted, resolve it via filesystem search
        if location_hint:
            resolved = resolve_location(location_hint, base_dir)
            return str(Path(resolved) / name)
        # If base_dir was extracted (e.g. "in local disk D"), use it
        if base_dir:
            return str(Path(base_dir) / name)
        # Default to Desktop
        return str(DEFAULT_BASE_DIR / name)
    return None


def extract_delete_file_name(command):
    """Extract file name for deletion."""
    parsed = smart_parse_command(command)
    return parsed.get("entity")


def extract_entity(command):
    """Extract generic entity (for web search, open website, etc.)."""
    command = command.lower().strip()
    prefixes = ["go to ", "visit ", "open ", "search for ", "search "]
    for prefix in prefixes:
        if command.startswith(prefix):
            return command[len(prefix):].strip()
    return command


def extract_rename_args(command):
    """Extract (source, destination, base_dir) for rename operations."""
    parsed = smart_parse_command(command)
    return (
        parsed.get("source") or parsed.get("entity"),
        parsed.get("destination"),
        parsed.get("base_dir"),
    )


def extract_move_args(command):
    """Extract (source, destination, base_dir) for move operations."""
    parsed = smart_parse_command(command)
    return (
        parsed.get("source") or parsed.get("entity"),
        parsed.get("destination"),
        parsed.get("base_dir"),
    )


def extract_copy_args(command):
    """Extract (source, destination, base_dir) for copy operations."""
    parsed = smart_parse_command(command)
    return (
        parsed.get("source") or parsed.get("entity"),
        parsed.get("destination"),
        parsed.get("base_dir"),
    )


def extract_search_query(command):
    """Extract search query from command."""
    return _extract_search_query_internal(command)


def extract_project_args(command):
    """Extract project name and framework from command."""
    command_lower = command.lower().strip()
    frameworks = ["react", "angular", "laravel", "python", "node", "html", "django", "vue", "next"]
    keywords = ["create project", "generate project", "make project",
                "create a project", "generate a project", "make a project"]

    framework = None
    for fw in frameworks:
        if fw in command_lower:
            framework = fw
            break

    if framework:
        for kw in [f"create {framework} project", f"generate {framework} project",
                    f"make {framework} project", f"create a {framework} project"]:
            if kw in command_lower:
                idx = command_lower.index(kw) + len(kw)
                name = command_lower[idx:].strip().strip("'\"")
                return name or framework + "_project", framework
        return framework + "_project", framework

    for kw in keywords:
        if kw in command_lower:
            idx = command_lower.index(kw) + len(kw)
            name = command_lower[idx:].strip().strip("'\"")
            return name or "my_project", "python"

    return None, None


# =====================================================================
#  ML MODEL & INTENT CLASSIFICATION
# =====================================================================

CONFIDENCE_THRESHOLD = 0.25

QUESTION_PATTERNS = [
    "what is", "what's", "who is", "who are", "where is", "how do", "how to",
    "why is", "why are", "when did", "when will", "can you explain",
    "tell me about", "what does", "what are", "how does", "how are",
]

GREETING_WORDS = [
    "hello", "hi", "hey", "hola", "good morning", "good afternoon",
    "good evening", "howdy", "sup", "yo", "greetings", "habari",
    "mambo", "sasa", "vipi",
]

# Build keyword intents from synonym table
KEYWORD_INTENTS = dict(INTENT_SYNONYMS)


# Common file extensions for type detection
KNOWN_EXTENSIONS = {
    ".docx", ".doc", ".pdf", ".txt", ".xlsx", ".xls", ".pptx", ".ppt",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".mp3", ".mp4",
    ".avi", ".mkv", ".zip", ".rar", ".7z", ".py", ".js", ".html", ".css",
    ".csv", ".json", ".xml", ".exe", ".msi", ".bat", ".ps1", ".sh",
}


def _has_file_extension(text):
    """Check if text contains a recognizable file extension."""
    if not text:
        return False
    # Check the part before any separator (to, as, ->)
    for sep in [" to ", " as ", " -> ", " 2 "]:
        idx = text.lower().find(sep)
        if idx >= 0:
            text = text[:idx]
            break
    lower = text.lower().strip()
    for ext in KNOWN_EXTENSIONS:
        if lower.endswith(ext):
            return True
    return False


def _keyword_intent_override(command):
    """Check if command matches a known keyword pattern and return the intent.
    Supports multi-word phrases AND single action words with type detection."""
    cmd_lower = command.lower()

    # Priority check: "open <app>" / "launch <app>" should always be open_app
    # unless the target has a file extension or contains "file"/"folder"
    for action in ["open ", "launch ", "start ", "fungua "]:
        if cmd_lower.startswith(action):
            target = cmd_lower[len(action):].strip()
            # Remove filler words
            for filler in ["the", "app", "application", "program"]:
                target = re.sub(r'\b' + filler + r'\b', '', target, flags=re.I).strip()
            # If target has file extension or mentions file/folder, skip this check
            if _has_file_extension(target) or "file" in target or "folder" in target or "directory" in target or "website" in target or "site" in target:
                break
            # Check if target matches a known app name
            for app_name in KNOWN_APP_NAMES:
                if app_name in target:
                    return "open_app"
            # If target is just a name with no file/folder context, it's likely an app
            if target and not _has_file_extension(target):
                return "open_app"

    # Priority check: any mention of apps/processes/software/programs + running/open/active → list_processes
    _entity_words = r'\b(applications?|apps?|processes?|software|programs?|tasks?)\b'
    _state_words = r'\b(running|active|open|opened|currently)\b'
    if re.search(_entity_words + r'.*' + _state_words, cmd_lower) or \
       re.search(_state_words + r'.*' + _entity_words, cmd_lower):
        return "list_processes"
    # Bare questions: "what is running", "what's running", "what's open"
    if re.search(r"\bwhat('s| is)?\b.*\b(running|open|active)\b", cmd_lower):
        return "list_processes"

    # Try longest phrase matches first (use word boundaries for short keywords)
    for keyword, intent in sorted(KEYWORD_INTENTS.items(), key=lambda x: len(x[0]), reverse=True):
        if len(keyword.split()) == 1 and len(keyword) <= 4:
            # Short single words need word boundary matching to avoid false positives
            if re.search(r'\b' + re.escape(keyword) + r'\b', cmd_lower):
                return intent
        elif keyword in cmd_lower:
            return intent

    # Single action word fallback — detect file vs folder from context
    ACTION_TYPE_MAP = {
        "copy": ("copy_file", "copy_folder"),
        "duplicate": ("copy_file", "copy_folder"),
        "clone": ("copy_file", "copy_folder"),
        "replicate": ("copy_file", "copy_folder"),
        "delete": ("delete_file", "delete_folder"),
        "remove": ("delete_file", "delete_folder"),
        "erase": ("delete_file", "delete_folder"),
        "del": ("delete_file", "delete_folder"),
        "move": ("move_file", "move_folder"),
        "transfer": ("move_file", "move_folder"),
        "put": ("move_file", "move_folder"),
        "relocate": ("move_file", "move_folder"),
        "send": ("move_file", "move_folder"),
        "rename": ("rename_file", "rename_folder"),
        "open": ("open_file", "open_folder"),
        "find": ("search_file", "search_folder"),
        "locate": ("search_file", "search_folder"),
        "launch": ("open_app", None),
        "start": ("open_app", None),
        # Close/kill actions
        "close": ("close_app", None),
        "exit": ("close_app", None),
        "quit": ("close_app", None),
        "kill": ("close_app", None),
        "stop": ("close_app", None),
        # Swahili action words
        "tengeneza": ("create_file", "create_folder"),
        "futa": ("delete_file", "delete_folder"),
        "nakili": ("copy_file", "copy_folder"),
        "hamisha": ("move_file", "move_folder"),
        "tafuta": ("search_file", "search_folder"),
        "tafutia": ("search_file", "search_folder"),
        "findi": ("search_file", "search_folder"),
        "fungua": ("open_file", "open_folder"),
        "funga": ("close_app", None),
    }

    for word, (file_intent, folder_intent) in ACTION_TYPE_MAP.items():
        if re.search(r'\b' + re.escape(word) + r'\b', cmd_lower):
            if folder_intent:
                # If the source/target has a file extension, it's ALWAYS a file operation
                if _has_file_extension(cmd_lower):
                    return file_intent
                # For 'open'/'fungua': if the target matches a known app, return open_app
                if word in ("open", "fungua", "launch", "start"):
                    # Extract what comes after the action word
                    action_pos = cmd_lower.find(word)
                    target = cmd_lower[action_pos + len(word):].strip()
                    # Remove filler words
                    for filler in ["the", "app", "application", "program"]:
                        target = re.sub(r'\b' + filler + r'\b', '', target, flags=re.I).strip()
                    # Check if target matches a known app
                    for app_name in KNOWN_APP_NAMES:
                        if app_name in target:
                            return "open_app"
                    # If no file extension and no "file"/"folder" keyword,
                    # trust the ML model — default to open_app
                    if not _has_file_extension(target):
                        after_open = cmd_lower[action_pos + len(word):]
                        if "file" not in after_open and "folder" not in after_open and "directory" not in after_open:
                            return "open_app"
                # Determine type by which keyword appears FIRST after the action word
                action_pos = cmd_lower.find(word)
                after_action = cmd_lower[action_pos + len(word):]
                file_pos = after_action.find("file")
                folder_pos = after_action.find("folder")
                dir_pos = after_action.find("directory")
                if folder_pos >= 0 and (file_pos < 0 or folder_pos < file_pos):
                    return folder_intent
                if dir_pos >= 0 and (file_pos < 0 or dir_pos < file_pos):
                    return folder_intent
            return file_intent

    return None


# Load DistilBERT NLU model
nlu = NOVANLU()


# =====================================================================
#  COMMAND PROCESSING
# =====================================================================

# Tracks the last successful entity and intent for pronoun resolution
_last_entity = {"entity": None, "intent": None, "path": None}

PRONOUNS = {"it", "that", "this", "them", "the last one", "the previous one"}


# Maps intents to type words for pronoun resolution
_INTENT_TYPE_MAP = {
    "create_folder": "folder", "delete_folder": "folder", "open_folder": "folder",
    "rename_folder": "folder", "move_folder": "folder", "copy_folder": "folder",
    "search_folder": "folder",
    "create_file": "file", "delete_file": "file", "open_file": "file",
    "rename_file": "file", "move_file": "file", "copy_file": "file",
    "read_file": "file", "search_file": "file",
    "open_app": "app", "close_app": "app", "search_app": "app",
    "open_website": "website",
}


def _resolve_pronouns(command):
    """Replace pronouns like 'it', 'that', 'this' with the last referenced entity.
    Also injects the correct type word (file/folder/app) based on the last intent."""
    if not _last_entity.get("entity"):
        return command
    last_entity = _last_entity["entity"]
    last_intent = _last_entity.get("intent", "")
    type_word = _INTENT_TYPE_MAP.get(last_intent, "")

    lower = command.lower().strip()

    # Check if the entity portion of the command IS a pronoun
    # e.g. "close it" → entity part is "it"
    # e.g. "copy it to Desktop" → entity part is "it", destination is "Desktop"
    for action in sorted(ACTION_WORDS, key=len, reverse=True):
        if lower.startswith(action + " "):
            rest = lower[len(action):].strip()
            # Strip type words
            for tw in sorted(TYPE_WORDS, key=len, reverse=True):
                if rest.startswith(tw + " "):
                    rest = rest[len(tw):].strip()
                    break
            # Exact match: "close it" → rest is "it"
            if rest in PRONOUNS:
                if type_word:
                    return f"{action} {type_word} {last_entity}"
                return f"{action} {last_entity}"
            # Prefix match: "copy it to Desktop" → rest starts with "it to ..."
            for pronoun in sorted(PRONOUNS, key=len, reverse=True):
                for connector in [" to ", " from ", " as ", " on "]:
                    if rest.startswith(pronoun + connector):
                        after = rest[len(pronoun):]  # " to Desktop"
                        if type_word:
                            return f"{action} {type_word} {last_entity}{after}"
                        return f"{action} {last_entity}{after}"
            break

    # Check for pronoun at end of command (e.g. "delete it", "open that")
    for pronoun in sorted(PRONOUNS, key=len, reverse=True):
        if lower.endswith(" " + pronoun):
            prefix = command[:len(command) - len(pronoun)].rstrip()
            prefix_lower = prefix.lower()
            # Check if prefix already has a type word
            has_type = any(prefix_lower.endswith(tw) for tw in TYPE_WORDS)
            if type_word and not has_type:
                return f"{prefix} {type_word} {last_entity}"
            return f"{prefix} {last_entity}"

    return command

def split_compound_commands(command):
    """Split a compound command like 'open X and create Y' into individual commands.

    Only splits on ' and ' / ' then ' / ' also ' / ', ' when followed by a known action word.
    Returns a list of individual command strings.
    """
    ACTION_STARTERS = [
        "create", "open", "delete", "rename", "move", "copy", "close", "read",
        "search", "find", "launch", "start", "run", "generate", "list",
        "tengeneza", "futa", "nakili", "hamisha", "fungua", "funga", "tafuta",
        "can you", "could you", "would you", "please",
    ]
    separators = [" and then ", " and also ", " and ", " then ", ", then ", ", also ", ", "]

    parts = [command]
    for sep in separators:
        new_parts = []
        for part in parts:
            lower_part = part.lower()
            idx = 0
            while True:
                pos = lower_part.find(sep, idx)
                if pos == -1:
                    new_parts.append(part[idx:] if idx > 0 else part)
                    break
                after = part[pos + len(sep):].strip().lower()
                is_action = any(after.startswith(a) for a in ACTION_STARTERS)
                if is_action:
                    if idx < pos:
                        new_parts.append(part[idx:pos].strip())
                    idx = pos + len(sep)
                else:
                    idx = pos + len(sep)
        parts = new_parts

    # Clean up empty parts
    parts = [p.strip() for p in parts if p.strip()]
    return parts if len(parts) > 1 else [command]


def process_command(command):
    """Main entry point: parse command, classify intent, route to handler.
    Supports compound commands (e.g. 'open X and create Y')."""
    command = command.strip()

    if not command:
        return make_result(None, None, "failed", "Empty command")

    # Check for compound commands (e.g. "open X and create Y")
    sub_commands = split_compound_commands(command)
    if len(sub_commands) > 1:
        # Parse the first command to extract location context for inheritance
        first_parsed = smart_parse_command(sub_commands[0])
        inherited_base = first_parsed.get("base_dir")
        inherited_hint = first_parsed.get("location_hint")

        results = []
        for i, sub_cmd in enumerate(sub_commands):
            # For subsequent commands without location context, inherit from first
            if i > 0 and (inherited_base or inherited_hint):
                sub_parsed = smart_parse_command(sub_cmd)
                if not sub_parsed.get("base_dir") and not sub_parsed.get("location_hint"):
                    # Append inherited location context to the sub-command
                    if inherited_hint and inherited_base:
                        drive_letter = inherited_base.rstrip("\\").rstrip(":")
                        sub_cmd += f" in volume ({drive_letter}:) in {inherited_hint}"
                    elif inherited_base:
                        drive_letter = inherited_base.rstrip("\\").rstrip(":")
                        sub_cmd += f" in volume ({drive_letter}:)"
                    elif inherited_hint:
                        sub_cmd += f" in {inherited_hint}"
            result = _process_single_command(sub_cmd)
            results.append(result)
        # Combine results into a single response
        combined_msg = []
        combined_status = "success"
        for r in results:
            status = r.get("status", "failed")
            msg = r.get("message", "")
            if status != "success":
                combined_status = status
            combined_msg.append(msg if msg else f"{r.get('intent', 'unknown')}: {r.get('entity', '')}")

        # Update entity memory from the last sub-result with a valid entity
        for r in reversed(results):
            if r.get("entity"):
                _last_entity["entity"] = r["entity"]
                _last_entity["intent"] = r.get("intent")
                if isinstance(r.get("details"), dict):
                    _last_entity["path"] = r["details"].get("path")
                break

        return make_result(
            "compound", None, combined_status,
            "\n".join(combined_msg),
            {"sub_results": results}
        )

    result = _process_single_command(command)

    # Update entity memory for pronoun resolution
    # Track on any result with a valid entity (not just success — "already exists" still means correct entity)
    if result.get("entity"):
        _last_entity["entity"] = result["entity"]
        _last_entity["intent"] = result.get("intent")
        if isinstance(result.get("details"), dict):
            _last_entity["path"] = result["details"].get("path")

    return result


def _handle_index_command():
    """Handle 'index my files' command — build semantic search index."""
    try:
        from automation.semantic_search import build_index, is_index_ready
        print("Building semantic index...")
        stats = build_index(force=True)
        indexed = stats.get("indexed", 0)
        total_vectors = stats.get("total_vectors", 0)
        skipped = stats.get("skipped", 0)
        failed = stats.get("failed", 0)
        msg = (f"Semantic index built successfully.\n"
               f"  - {total_vectors} documents indexed\n"
               f"  - {indexed} new, {skipped} unchanged, {failed} skipped\n"
               f"  - You can now say things like 'open the proposal about AI'")
        return make_result("semantic_index", None, "success", msg, stats)
    except Exception as e:
        return make_result("semantic_index", None, "failed",
                           f"Failed to build index: {str(e)}")


def _handle_computer_index_command():
    """Handle 'index my computer' command — build full computer index."""
    try:
        from automation.computer_indexer import initialize_index, is_index_ready, get_index_stats
        print("Building computer-wide index...")
        stats = initialize_index(force=True)
        total_files = stats.get("total_files", 0)
        total_drives = stats.get("total_drives", 0)
        total_size = stats.get("total_size_mb", 0)
        by_drive = stats.get("by_drive", {})
        
        lines = [f"Computer index built successfully.", 
                 f"  - {total_files} files indexed across {total_drives} drives",
                 f"  - Total size: {total_size} MB"]
        if by_drive:
            lines.append("  - By drive:")
            for drive, count in list(by_drive.items())[:5]:
                lines.append(f"      {drive}: {count} files")
        
        msg = "\n".join(lines)
        return make_result("computer_index", None, "success", msg, stats)
    except Exception as e:
        return make_result("computer_index", None, "failed",
                           f"Failed to build computer index: {str(e)}")


def _process_single_command(command):
    """Process a single command (internal). Returns a result dict."""
    command = command.strip()
    command = _resolve_pronouns(command)

    if not command:
        return make_result(None, None, "failed", "Empty command")

    # Special command: build indexes (bypasses NLU)
    _INDEX_COMMANDS = {"index my files", "index files", "rebuild index",
                       "build index", "index documents", "reindex",
                       "index my computer", "index computer", "scan my computer",
                       "build computer index", "index all drives"}
    cmd_check = command.lower().strip().rstrip("?!. ")
    if cmd_check in _INDEX_COMMANDS:
        if "computer" in cmd_check or "all drives" in cmd_check or "scan" in cmd_check:
            return _handle_computer_index_command()
        return _handle_index_command()

    # Detect discovery type early (before NLU, for override purposes)
    parsed = smart_parse_command(command)
    disc_type = parsed.get("discovery_type")

    # If discovery type is present, override intent and route directly
    if disc_type:
        if disc_type == "pdfs_today":
            intent = "search_file"
        elif disc_type == "semantic":
            intent = "open_file"
        elif disc_type == "latest_folder" or disc_type.endswith("_folder"):
            intent = "open_folder"
        elif disc_type in ("find_anywhere", "search_computer"):
            # search_computer is a search operation, find_anywhere is open
            if disc_type == "search_computer":
                intent = "search_file"
            elif "folder" in command.lower() or "project" in command.lower():
                intent = "open_folder"
            else:
                intent = "open_file"
        else:
            intent = "open_file"
        print(f"Discovery override: {intent} (discovery_type={disc_type})")
        # Pass the pre-parsed result to preserve discovery info
        return route_intent(
            intent,
            command,
            extract_app_name,
            extract_folder_name,
            extract_delete_folder_name,
            extract_file_name,
            extract_delete_file_name,
            extract_entity,
            extract_rename_args=extract_rename_args,
            extract_move_args=extract_move_args,
            extract_copy_args=extract_copy_args,
            extract_search_query=extract_search_query,
            extract_project_args=extract_project_args,
            parsed=parsed,  # Pass pre-parsed result
        )

    # Check if the user is asking a question (not giving a command)
    # But allow "where is folder X", "show me file X" etc. as commands
    cmd_lower = command.lower().rstrip("?!. ")
    ACTIONABLE_KEYWORDS = {"file", "folder", "directory", "app", "application", "document",
                           "open", "create", "delete", "rename", "copy", "move", "search",
                           "find", "show", "locate", "read", "run", "launch", "close"}
    has_actionable_keyword = any(kw in cmd_lower for kw in ACTIONABLE_KEYWORDS)

    try:
        # ML prediction (DistilBERT)
        ml_intent, max_confidence = nlu.predict(command)
        print(f"NLU Predicted: {ml_intent} (confidence: {max_confidence:.2%})")

        # Keyword overrides (fallback for low-confidence predictions)
        kw_intent = _keyword_intent_override(command)

        # Confidence-based decision:
        # - DistilBERT confident (>= 45%) → trust ML
        # - DistilBERT uncertain (< 45%) + keyword match → use keyword
        # - DistilBERT uncertain + no keyword → show "not sure"
        if max_confidence >= 0.45:
            intent = ml_intent
            if kw_intent and kw_intent != ml_intent:
                print(f"ML trusted ({ml_intent} {max_confidence:.0%}) over keyword ({kw_intent})")
        elif kw_intent:
            intent = kw_intent
            print(f"Keyword override: {kw_intent} (ML: {ml_intent} {max_confidence:.0%})")
        elif ml_intent == "unknown":
            # ML model thinks this is an unsupported command
            intent = ml_intent
        else:
            # Low confidence + no keyword fallback
            is_question = False
            if not has_actionable_keyword:
                for pattern in QUESTION_PATTERNS:
                    if cmd_lower.startswith(pattern):
                        is_question = True
                        break
            if is_question:
                return make_result(
                    "question", None, "unsupported",
                    f"That sounds like a question! I'm a desktop automation assistant.\n"
                    f"I can help you with:\n"
                    f"- File/folder management (create, rename, delete, search)\n"
                    f"- Opening apps and websites\n"
                    f"- Document generation (Word, Excel, PDF)\n"
                    f"- Web search and research\n"
                    f"- Project scaffolding\n"
                    f"Try rephrasing as a command, or type 'help' for all commands.",
                )
            else:
                return make_result(
                    ml_intent, None, "unsupported",
                    f"I'm not sure I understood that (confidence: {max_confidence:.0%}). You can try:\n"
                    f"- 'create file [name]' or 'create folder [name]'\n"
                    f"- 'open chrome', 'open notepad', etc.\n"
                    f"- 'search for [topic]' or 'search web [topic]'\n"
                    f"- Type 'help' for a full list of commands.",
                )

        # At this point we have a valid intent, route it!
        return route_intent(
            intent,
            command,
            extract_app_name,
            extract_folder_name,
            extract_delete_folder_name,
            extract_file_name,
            extract_delete_file_name,
            extract_entity,
            extract_rename_args=extract_rename_args,
            extract_move_args=extract_move_args,
            extract_copy_args=extract_copy_args,
            extract_search_query=extract_search_query,
            extract_project_args=extract_project_args,
        )
    except Exception as error:
        print("Command processing error:", error)
        return make_result(None, None, "failed", str(error))