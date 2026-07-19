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

from ml.nlu_model import AMAZONNLU
from system.environment_scanner import initialize_environment, get_scanner

# AMAZON CHAT handler for general questions and conversations
try:
    from ai_assistant.core.amazon_chat import is_amazon_chat_prompt, handle_amazon_chat_prompt
    AMAZON_CHAT_AVAILABLE = True
except ImportError:
    AMAZON_CHAT_AVAILABLE = False

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

# Dynamically add all mounted drives/volumes to LOCATION_DIRS
try:
    from automation.file_discovery import get_all_drives
    for drive_path in get_all_drives():
        drive_name = drive_path.name.lower() if drive_path.name else ""
        if not drive_name:
            # Root filesystem — use OS-specific name
            import platform as _plat
            if _plat.system() == "Darwin":
                drive_name = "macintosh hd"
            elif _plat.system() == "Windows":
                drive_name = str(drive_path).rstrip("\\").lower()
            else:
                drive_name = "root"
        if drive_name and drive_name not in LOCATION_DIRS:
            LOCATION_DIRS[drive_name] = drive_path
except Exception:
    pass

# =====================================================================
#  SYNONYM & KEYWORD TABLES
# =====================================================================

INTENT_SYNONYMS = {
    # File creation
    "create file": "create_file", "makes file": "create_file",
    "new file": "create_file", "create text file": "create_file",
    "creat file": "create_file", "creat new file": "create_file",
    "creates file": "create_file", "creating file": "create_file",
    # Folder creation
    "create folder": "create_folder", "make folder": "create_folder",
    "new folder": "create_folder", "creat folder": "create_folder",
    "create directory": "create_folder", "make directory": "create_folder",
    "create a folder": "create_folder", "create new folder": "create_folder",
    "creates folder": "create_folder", "creating folder": "create_folder",
    # Delete file
    "delete file": "delete_file", "remove file": "delete_file",
    "erase file": "delete_file", "del file": "delete_file",
    "kill file": "delete_file", "destroy file": "delete_file",
    "wipe file": "delete_file", "trash file": "delete_file",
    # Delete folder
    "delete folder": "delete_folder", "remove folder": "delete_folder",
    "erase folder": "delete_folder", "del folder": "delete_folder",
    "kill folder": "delete_folder", "destroy folder": "delete_folder",
    "wipe folder": "delete_folder", "trash folder": "delete_folder",
    # Empty trash
    "empty trash": "empty_trash", "clear trash": "empty_trash",
    "empty recycle bin": "empty_trash", "clear recycle bin": "empty_trash",
    "empty the trash": "empty_trash", "clear the trash": "empty_trash",
    "empty bin": "empty_trash", "clear bin": "empty_trash",
    "delete trash": "empty_trash", "remove trash": "empty_trash",
    "clean trash": "empty_trash", "clean bin": "empty_trash",
    "purge trash": "empty_trash", "flush trash": "empty_trash",
    "force delete trash": "empty_trash", "force empty trash": "empty_trash",
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
    # Path/location queries (context-aware)
    "give me path": "show_path", "show path": "show_path",
    "where is it": "show_path", "show me path": "show_path",
    "give me the path": "show_path", "show the path": "show_path",
    "path for it": "show_path", "path of it": "show_path",
    "where can i find it": "show_path", "show location": "show_path",
    # Universal search (find anything)
    "find": "find_anything", "look for": "find_anything",
    "locate": "find_anything",
    "find anything": "find_anything", "search anything": "find_anything",
    "help me find": "find_anything", "help me to find": "find_anything",
    "find any": "find_anything", "find any about": "find_anything",
    "search for any": "find_anything", "look for any": "find_anything",
    "find something": "find_anything", "search for something": "find_anything",
    # Web
    "search web": "search_web", "search for": "search_web",
    "google": "search_web", "search": "search_web",
    "open website": "open_website", "visit website": "open_website",
    # Documents
    "generate document": "generate_document", "create report": "generate_document",
    "generate report": "generate_document", "create document": "generate_document",
    "creates document": "generate_document", "creating document": "generate_document",
    "create assignment": "generate_document", "make assignment": "generate_document",
    "generate assignment": "generate_document", "create research proposal": "generate_document",
    "make research proposal": "generate_document", "generate research proposal": "generate_document",
    "create a report": "generate_document", "make a report": "generate_document",
    "write document": "generate_document", "write doc": "generate_document",
    "write a document": "generate_document", "write a doc": "generate_document",
    "write document about": "generate_document", "write a document about": "generate_document",
    "write doc about": "generate_document", "write a doc about": "generate_document",
    "create word document": "generate_document", "make word doc": "generate_document",
    "creates word document": "generate_document", "creating word document": "generate_document",
    "write word document": "generate_document", "generate word doc": "generate_document",
    "create word document about": "generate_document", "make word doc about": "generate_document",
    "creates word document about": "generate_document", "creating word doc about": "generate_document",
    "write about": "generate_document", "generate about": "generate_document",
    "create pdf": "generate_document", "make pdf": "generate_document",
    "creates pdf": "generate_document", "creating pdf": "generate_document",
    "write pdf": "generate_document", "generate pdf": "generate_document",
    "create excel": "generate_document", "make excel": "generate_document",
    "creates excel": "generate_document", "creating excel": "generate_document",
    "write excel": "generate_document", "generate spreadsheet": "generate_document",
    # Schedule / plan documents
    "create schedule": "generate_document", "make schedule": "generate_document",
    "generate schedule": "generate_document", "write schedule": "generate_document",
    "training schedule": "generate_document", "work schedule": "generate_document",
    "create plan": "generate_document", "make plan": "generate_document",
    "generate plan": "generate_document", "write plan": "generate_document",
    # Plural forms
    "create schedules": "generate_document", "make schedules": "generate_document",
    "generate schedules": "generate_document", "write schedules": "generate_document",
    "training schedules": "generate_document", "work schedules": "generate_document",
    "professional schedule": "generate_document", "professional schedules": "generate_document",
    # Mixed language (Swahili/English) patterns
    "nataka schedule": "generate_document", "nataka document": "generate_document",
    "nataka report": "generate_document", "nataka assignment": "generate_document",
    "nataka schedules": "generate_document", "taka schedule": "generate_document",
    "taka ratiba": "generate_document", "taka document": "generate_document",
    # Person name + document type patterns
    "schedule for": "generate_document", "plan for": "generate_document",
    "report for": "generate_document", "document for": "generate_document",
    "schedules for": "generate_document", "training for": "generate_document",
    # List commands / recommendations
    "list commands": "list_commands", "show commands": "list_commands",
    "all commands": "list_commands", "what can you do": "list_commands",
    "your commands": "list_commands", "available commands": "list_commands",
    "help": "list_commands", "command list": "list_commands",
    "recommend": "list_commands", "suggestions": "list_commands",
    "what do you support": "list_commands", "full list": "list_commands",
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
    # System Info
    "system info": "system_info", "system information": "system_info",
    "computer info": "system_info", "computer information": "system_info",
    "show system": "system_info", "show computer": "system_info",
    "my computer": "system_info", "about my computer": "system_info",
    "show my computer": "system_info", "tell me about my computer": "system_info",
    "specs": "system_info", "specifications": "system_info",
    "hardware info": "system_info", "hardware information": "system_info",
    "what are my specs": "system_info", "show my specs": "system_info",
    "what is my computer": "system_info", "check my computer": "system_info",
    "computer specs": "system_info", "pc info": "system_info",
    "laptop info": "system_info", "machine info": "system_info",
    # OS Commands (auto-learned)
    "disk usage": "os_command", "disk space": "os_command",
    "memory usage": "os_command", "ram usage": "os_command",
    "cpu info": "os_command", "cpu usage": "os_command",
    "network info": "os_command", "ip address": "os_command",
    "wifi networks": "os_command", "wifi list": "os_command",
    "running processes": "os_command", "top processes": "os_command",
    "ping test": "os_command", "dns flush": "os_command",
    "clear cache": "os_command", "disk cleanup": "os_command",
    "installed apps": "os_command", "running apps": "os_command",
    "installed applications": "os_command", "running applications": "os_command",
    "list installed apps": "os_command", "list installed applications": "os_command",
    "lists installed apps": "os_command", "lists installed applications": "os_command",
    "listing installed apps": "os_command", "listing installed applications": "os_command",
    "show installed apps": "os_command", "show installed applications": "os_command",
    "show all apps": "os_command", "show all applications": "os_command",
    "take screenshot": "os_command", "screenshot": "os_command",
    "public ip": "os_command", "external ip": "os_command",
    "open ports": "os_command", "port scan": "os_command",
    "update system": "os_command", "system update": "os_command",
    "check disk": "os_command", "repair disk": "os_command",
    "show me disk usage": "os_command", "show memory": "os_command",
    "show network": "os_command", "show cpu": "os_command",
    "list processes": "os_command", "list all processes": "os_command",
    "show processes": "os_command", "show running processes": "os_command",
    # Computer scan commands
    "scan computer": "computer_scan", "scan my computer": "computer_scan",
    "scan system": "computer_scan", "scan my system": "computer_scan",
    "hardware scan": "computer_scan", "hardware info": "computer_scan",
    "system scan": "computer_scan", "full scan": "computer_scan",
    "scan hardware": "computer_scan", "scan peripherals": "computer_scan",
    "usb devices": "computer_scan", "bluetooth devices": "computer_scan",
    "connected devices": "computer_scan", "all devices": "computer_scan",
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
    # Email intents
    "send email": "send_email", "send mail": "send_email",
    "compose email": "send_email", "compose mail": "send_email",
    "write email": "send_email", "write mail": "send_email",
    "create email": "send_email", "new email": "send_email",
    "email to": "send_email", "mail to": "send_email",
    "send mail to": "send_email", "send email to": "send_email",
    "open email": "open_email", "open gmail": "open_email",
    "open outlook": "open_email", "open mail": "open_email",
    "check email": "open_email", "check mail": "open_email",
    "open my email": "open_email", "open my mail": "open_email",
    # Model training intents
    "retrain model": "retrain_model", "train model": "retrain_model",
    "retrain": "retrain_model", "train ai": "retrain_model",
    "update model": "retrain_model", "learn new commands": "retrain_model",
    "improve model": "retrain_model", "retrain ai": "retrain_model",
    "merge training data": "merge_training_data", "export learned data": "merge_training_data",
    # Common typos for document generation
    "write invetatin leter": "generate_document", "write invitation leter": "generate_document",
    "write invetation letter": "generate_document", "write invtation letter": "generate_document",
    "write invetatin": "generate_document", "write invitation": "generate_document",
    "wrtie document": "generate_document", "wriet document": "generate_document",
    "genrate document": "generate_document", "generat document": "generate_document",
    "create docuemnt": "generate_document", "create documet": "generate_document",
    "make docuemnt": "generate_document", "make documet": "generate_document",
    "write docuemnt": "generate_document", "write documet": "generate_document",
    "write reprot": "generate_document", "write repot": "generate_document",
    "write asignment": "generate_document", "write assignemnt": "generate_document",
    "write essy": "generate_document", "write esay": "generate_document",
    "write artical": "generate_document", "write aritcle": "generate_document",
    # Document analysis / summarization
    "analyze document": "analyze_document", "analyse document": "analyze_document",
    "summarize document": "analyze_document", "summarise document": "analyze_document",
    "summary of": "analyze_document", "summarize": "analyze_document",
    "key points": "analyze_document", "key points of": "analyze_document",
    "extract key points": "analyze_document", "get key points": "analyze_document",
    "analyze this": "analyze_document", "analyse this": "analyze_document",
    "read and summarize": "analyze_document", "read and analyse": "analyze_document",
    "document analysis": "analyze_document", "document summary": "analyze_document",
    "what is this document about": "analyze_document", "explain this document": "analyze_document",
    "give me summary": "analyze_document", "give summary": "analyze_document",
    "brief summary": "analyze_document", "short summary": "analyze_document",
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

    # Guard: document-generation research commands should not be treated
    # as semantic file discovery (e.g., "create research about cocacola").
    if re.search(r'\b(write|generate|create|make)\b.*\b(research|assignment|report|proposal|document|doc|essay|article|profile|blueprint|strategy|plan)\b', cmd, re.I):
        return None

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
            m = re.search(r'\b(?:open|find|search)\s+(?:the\s+|any\s+)?(?:folder|project)\s+with\s+(.+?)(?:\s+folder|\s+file)?\s*$', cmd_lower)
            if m:
                result["semantic_query"] = m.group(1).strip()
                result["entity"] = result["semantic_query"]
            else:
                m = re.search(r'\b(?:search|find)\s+(?:my\s+)?computer\s+(?:for\s+)?(.+?)(?:\s+folder|\s+file|\s+document)?\s*$', cmd_lower)
                if m:
                    result["semantic_query"] = m.group(1).strip()
                    result["entity"] = result["semantic_query"]
            # Also try: "find any file about X", "find file about X", "search for X"
            if not result.get("semantic_query"):
                m = re.search(r'\b(?:find|search)\s+(?:any\s+)?(?:file|files|document|documents|folder|folders)\s+(?:about|on|for|named|called)\s+(.+?)\s*$', cmd_lower)
                if m:
                    result["semantic_query"] = m.group(1).strip()
                    result["entity"] = result["semantic_query"]
            # Fallback: extract everything after "find" or "search"
            if not result.get("semantic_query"):
                m = re.search(r'\b(?:find|search)\s+(?:any\s+|my\s+|the\s+)?(?:file|files|document|documents|folder|folders)?\s*(?:about|on|for)?\s*(.+?)\s*$', cmd_lower)
                if m:
                    query = m.group(1).strip()
                    # Filter out common words that aren't part of the query
                    stop_words = {'any', 'file', 'files', 'document', 'documents', 'folder', 'folders', 'about', 'on', 'for', 'my', 'the'}
                    query_words = [w for w in query.split() if w.lower() not in stop_words]
                    if query_words:
                        result["semantic_query"] = ' '.join(query_words)
                        result["entity"] = result["semantic_query"]
        # Return early for discovery - don't overwrite entity with app name
        # Step 1: Extract location context (in/from <location>)
        cleaned, base_dir = _extract_location_context(original)
        result["base_dir"] = base_dir
        result["entity"] = result.get("semantic_query") or result.get("entity")
        return result

    # Early check: semantic query patterns ("about AI", "discussing subnetting", etc.)
    # BUT skip if this is clearly a document generation command
    _is_doc_gen = bool(re.search(r'\b(write|generate|create|make)\b.*\b(document|doc|report|assignment|proposal|research|essay|article|word|pdf|excel|schedule|schedules|plan|plans|profile|blueprint|strategy)\b', original, re.I))
    if not _is_doc_gen:
        # Also catch: "schedule for X", "plan for X", "training schedule", etc.
        _is_doc_gen = bool(re.search(r'\b(schedule|schedules|plan|plans|ratiba)\b.*\b(for|ya|wa|kwa)\b', original, re.I))
    if not _is_doc_gen:
        _is_doc_gen = bool(re.search(r'\b(training|work|professional)\s+(schedule|schedules|plan|plans)\b', original, re.I))
    if not _is_doc_gen:
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
    elif intent == "open_website":
        site_target = _extract_website_target_internal(original)
        if site_target:
            result["entity"] = site_target

    # Step 7: Special handling for document generation
    if intent == "generate_document":
        doc_cmd_lower = original.lower()
        # Extract "save as" filename if present
        save_as_match = re.search(r'\b(?:save\s+(?:as|it\s+as)|named?|called)\s+(.+?)$', doc_cmd_lower, re.I)
        if save_as_match:
            result["save_as"] = save_as_match.group(1).strip()
            # Remove the save-as part from the entity
            original_before_save = doc_cmd_lower[:save_as_match.start()].strip()
            # Re-extract topic from the part before "save as"
            topic_match = re.search(r'\b(?:about|on|regarding)\s+(.+?)$', original_before_save, re.I)
            if topic_match:
                result["entity"] = topic_match.group(1).strip()
            else:
                # Use whatever is left after removing action words
                cleaned_save = re.sub(r'\b(write|generate|create|make)\b', '', original_before_save, flags=re.I).strip()
                cleaned_save = re.sub(r'\b(document|doc|report|assignment|proposal|essay|article|word|pdf|excel)\b', '', cleaned_save, flags=re.I).strip()
                cleaned_save = re.sub(r'\s+', ' ', cleaned_save).strip()
                if cleaned_save:
                    result["entity"] = cleaned_save
        else:
            # Extract topic from "about <topic>", "on <topic>", "regarding <topic>"
            topic_match = re.search(r'\b(?:about|on|regarding)\s+(.+?)$', doc_cmd_lower, re.I)
            if topic_match:
                result["entity"] = topic_match.group(1).strip()
            elif result.get("entity"):
                # Clean up entity to just be the topic
                entity = result["entity"]
                entity = re.sub(r'\b(write|generate|create|make)\b', '', entity, flags=re.I).strip()
                entity = re.sub(r'\b(document|doc|report|assignment|proposal|essay|article|word|pdf|excel)\b', '', entity, flags=re.I).strip()
                entity = re.sub(r'\b(about|on|regarding)\b', '', entity, flags=re.I).strip()
                entity = re.sub(r'\s+', ' ', entity).strip()
                if entity:
                    result["entity"] = entity

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
    "chrome", "google chrome", "chrome browser", "notepad", "calculator", "paint", "vscode", "vs code",
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
    # Design & graphics apps
    "corel draw", "coreldraw", "photoshop", "illustrator",
    "indesign", "lightroom", "after effects", "premiere", "premiere pro",
    "sketch", "affinity photo", "affinity designer", "affinity publisher",
    # Productivity apps
    "onenote", "publisher", "access", "visio", "project",
    "notes", "reminders", "calendar", "maps", "photos",
    "music", "podcasts", "tv", "app store",
    "system preferences", "system settings",
    "activity monitor", "disk utility", "time machine",
    "siri", "facetime", "face time", "imessage", "messages",
    "mail", "quicktime", "quicktime player",
    "automator", "script editor", "console",
    "keychain", "keychain access",
}


def _extract_app_name_internal(command):
    """Internal app name extraction."""
    command_lower = command.lower()

    # Strong disambiguation for Chrome phrases
    if "google chrome" in command_lower or "chrome browser" in command_lower:
        return "chrome"
    
    # Check for multi-word app names first (longest match)
    for app in sorted(KNOWN_APP_NAMES, key=len, reverse=True):
        if app in command_lower:
            # Normalize app names
            if app in ["vscode", "vs code", "visual studio code"]:
                return "vscode"
            if app in ["google chrome", "chrome browser"]:
                return "chrome"
            return app
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


def _extract_website_target_internal(command):
    """Extract website/domain target from natural-language web commands."""
    text = (command or "").strip()
    if not text:
        return ""

    lowered = text.lower().strip()
    prefixes = [
        "open website ", "visit website ", "go to ", "visit ", "open ",
        "learn from ", "study from ", "jifunze kutoka ",
    ]
    for prefix in prefixes:
        if lowered.startswith(prefix):
            text = text[len(prefix):].strip()
            break

    # Capture URL/domain anywhere in the command.
    match = re.search(
        r'(https?://[^\s]+|www\.[^\s]+|\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?)',
        text,
        flags=re.I,
    )
    if match:
        return match.group(1).rstrip('.,!?;:')

    return text.strip()


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
    prefixes = [
        "open website ", "visit website ",
        "go to ", "visit ", "open ",
        "search for ", "search ",
        "learn from ", "study from ", "jifunze kutoka ",
    ]
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


def _natural_language_understand(command):
    """Understand natural language commands and extract intent.
    This is a fallback for when keyword matching fails."""
    cmd = command.lower().strip()
    
    # Remove common filler phrases that don't change meaning
    filler_phrases = [
        r'\b(on|in|with|using)\s+(a\s+)?new\s+window\b',
        r'\b(on|in|with|using)\s+(a\s+)?new\s+instance\b',
        r'\b(on|in|with|using)\s+(a\s+)?separate\s+window\b',
        r'\bplease\b', r'\bcan you\b', r'\bcould you\b',
        r'\bi want to\b', r'\bi need to\b', r'\bi\'d like to\b',
        r'\bwould you kindly\b', r'\bkindly\b',
    ]
    for phrase in filler_phrases:
        cmd = re.sub(phrase, '', cmd, flags=re.I).strip()
    
    # Action verbs and their corresponding intents
    ACTION_PATTERNS = {
        # Document generation (check BEFORE file operations - more specific patterns first)
        r'\b(write|writes|writing|generate|generates|generating|create|creates|creating|make|makes|making)\b.*\b(word document|word doc|pdf document|pdf file|excel sheet|excel file|spreadsheet)\b': 'generate_document',
        r'\b(write|writes|writing|generate|generates|generating|create|creates|creating|make|makes|making)\b.*\b(word|pdf|excel)\b.*\b(document|doc|file)\b': 'generate_document',
        r'\b(write|writes|writing|generate|generates|generating|create|creates|creating|make|makes|making)\b.*\b(document|doc|report|assignment|proposal|essay|article)\b.*\b(about|on|regarding)\b': 'generate_document',
        r'\b(create|creates|creating|make|makes|making|generate|generates|generating)\b.*\b(word|pdf|excel|spreadsheet)\b.*\b(about|on|regarding)\b': 'generate_document',
        
        # File operations (less specific - after document generation)
        r'\b(create|creates|creating|make|makes|making|generate|generates|generating|new)\b.*\b(file|txt)\b(?!.*\b(document|doc|report|assignment)\b)': 'create_file',
        r'\b(create|creates|creating|make|makes|making|generate|generates|generating|new)\b.*\b(folder|directory)\b': 'create_folder',
        r'\b(delete|remove|erase|destroy|wipe|trash)\b.*\b(file|document)\b': 'delete_file',
        r'\b(delete|remove|erase|destroy|wipe|trash)\b.*\b(folder|directory)\b': 'delete_folder',
        r'\b(copy|duplicate|clone|replicate)\b.*\b(file|document)\b': 'copy_file',
        r'\b(copy|duplicate|clone|replicate)\b.*\b(folder|directory)\b': 'copy_folder',
        r'\b(move|transfer|relocate|send)\b.*\b(file|document)\b': 'move_file',
        r'\b(move|transfer|relocate|send)\b.*\b(folder|directory)\b': 'move_folder',
        r'\b(rename|change name)\b.*\b(file|document)\b': 'rename_file',
        r'\b(rename|change name)\b.*\b(folder|directory)\b': 'rename_folder',
        r'\b(open|view|read|show)\b.*\b(file|document)\b': 'open_file',
        r'\b(open|view|read|show)\b.*\b(folder|directory)\b': 'open_folder',
        r'\b(find|search|locate|look for)\b.*\b(file|document)\b': 'search_file',
        r'\b(find|search|locate|look for)\b.*\b(folder|directory)\b': 'search_folder',
        
        # App operations
        r'\b(open|launch|start|run)\b.*\b(app|application|program|software)\b': 'open_app',
        r'\b(close|quit|exit|kill|stop|terminate)\b.*\b(app|application|program|software)\b': 'close_app',
        r'\b(list|show|what)\b.*\b(running|active|open)\b.*\b(app|application|program|process)\b': 'list_processes',
        
        # OS Commands (system info, disk, network, etc.)
        r'\b(list|lists|listing|show|shows|showing|display|get)\b.*\b(installed|running|active)\b.*\b(app|application|program|process)\b': 'os_command',
        r'\b(disk|memory|ram|cpu|network|wifi)\b.*\b(usage|info|information|space|statistics)\b': 'os_command',
        r'\b(show|get|give me|display)\b.*\b(disk|memory|ram|cpu|network|wifi|ip|ports)\b': 'os_command',
        r'\b(take|capture|screenshot)\b.*\b(screenshot|screen|capture)\b': 'os_command',
        r'\b(clear|flush|clean)\b.*\b(dns|cache|temp)\b': 'os_command',
        r'\b(update|upgrade)\b.*\b(system|packages|apps)\b': 'os_command',
        r'\b(check|repair|verify)\b.*\b(disk|permissions|system)\b': 'os_command',
        r'\b(ping|test|check)\b.*\b(internet|connection|network)\b': 'os_command',
        r'\b(list|show|get)\b.*\b(ip address|public ip|external ip)\b': 'os_command',
        r'\b(list|show|get)\b.*\b(open ports|listening ports)\b': 'os_command',
        
        # Trash operations
        r'\b(empty|clear|clean)\b.*\b(trash|bin|recycle)\b': 'empty_trash',
        
        # System operations
        r'\b(lock|lock screen)\b': 'lock_screen',
        r'\b(shutdown|shut down|power off|turn off)\b': 'shutdown',
        r'\b(restart|reboot)\b': 'restart',
        r'\b(screenshot|screen capture|capture screen)\b': 'take_screenshot',
        r'\b(volume up|increase volume|louder)\b': 'volume_up',
        r'\b(volume down|decrease volume|quieter)\b': 'volume_down',
        r'\b(mute|silence)\b': 'volume_mute',
        r'\b(brightness up|brighter)\b': 'brightness_up',
        r'\b(brightness down|dimmer)\b': 'brightness_down',
        r'\b(sleep|hibernate)\b': 'sleep',
        r'\b(logout|log out|sign out)\b': 'logout',
    }
    
    # Check patterns
    for pattern, intent in ACTION_PATTERNS.items():
        if re.search(pattern, cmd):
            return intent
    
    # Question patterns
    if re.search(r'\b(what|which|where|when|how)\b', cmd):
        if re.search(r'\b(running|active|open)\b', cmd):
            return 'list_processes'
        if re.search(r'\b(file|folder)\b', cmd):
            return 'search_file'
        if re.search(r'\b(app|application|program)\b', cmd):
            return 'search_app'
    
    # If we can't understand, return None
    return None


def _keyword_intent_override(command):
    """Check if command matches a known keyword pattern and return the intent.
    Supports multi-word phrases AND single action words with type detection."""
    cmd_lower = command.lower()

    # Early check for system info queries (before other checks)
    _early_system_info = [
        "show my computer", "show computer", "my computer", "computer info",
        "system info", "computer specs", "my specs", "show specs",
        "what is my computer", "check my computer", "about my computer",
        "pc info", "laptop info", "machine info",
    ]
    for phrase in _early_system_info:
        if phrase in cmd_lower:
            return "system_info"

    # Early check for troubleshooting queries
    _early_troubleshoot = [
        "computer is slow", "my computer is slow", "pc is slow",
        "laptop is slow", "machine is slow",
        "computer is lagging", "my computer is lagging",
        "computer is freezing", "my computer is freezing",
        "fix error", "fix this error", "resolve error",
        "computer problem", "my computer problem",
    ]
    for phrase in _early_troubleshoot:
        if phrase in cmd_lower:
            return "troubleshoot"

    # Early check for automation tasks
    _early_automation = [
        "organize my files", "organize my desktop", "organize my downloads",
        "clean up my files", "cleanup my files",
        "find duplicates", "find duplicate files", "find duplicate photos",
        "sort my files", "arrange my files",
    ]
    for phrase in _early_automation:
        if phrase in cmd_lower:
            return "automation_task"

    # Early check for academic exam-design prompts (can be long instructions without action verbs)
    if re.search(r'\b(exam|examination|assessment|question\s*paper|test)\b', cmd_lower):
        if re.search(r'\b(design|draft|construct|prepare|set|intellectually rigorous|year\s*3|undergraduate|learning outcomes?|marking scheme|rubric|model answers?)\b', cmd_lower):
            return "generate_document"
    if re.search(r'\b(marking scheme|grading rubric|model answers?|examiner\'s notes|common mistakes)\b', cmd_lower):
        return "generate_document"

    # Early check for greetings (English + Swahili)
    _early_greetings = [
        "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
        "habari", "habari yako", "mambo", "vipi", "niaje", "hujambo", "shikamoo",
    ]
    def _has_greeting(text, greetings):
        for g in greetings:
            g = g.strip().lower()
            if not g:
                continue
            if " " in g:
                if re.search(rf'(?<!\w){re.escape(g)}(?!\w)', text):
                    return True
            else:
                if re.search(rf'\b{re.escape(g)}\b', text):
                    return True
        return False

    if _has_greeting(cmd_lower, _early_greetings):
        return "greeting"

    # Early check for conversational Swahili prompts -> AMAZON CHAT
    _early_amazon_chat_sw = [
        "nawezaje", "nisaidie", "naomba msaada", "nifafanulie", "nielezee",
        "nifundishe", "naomba unisaidie", "naomba unielezee",
    ]
    if any(p in cmd_lower for p in _early_amazon_chat_sw):
        # Keep explicit action commands in automation path
        action_markers = ["fungua", "funga", "tengeneza", "futa", "hamisha", "nakili", "tafuta"]
        if not any(a in cmd_lower for a in action_markers):
            return "amazon_chat"

    # Learning + document request in one sentence:
    # "learn from <url> then create a doc about ..."
    if re.search(r'\b(learn|study|jifunze)\s+(from|kutoka)\b', cmd_lower):
        has_url = bool(re.search(r'(https?://|\bwww\.|\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})', cmd_lower))
        has_doc_request = bool(re.search(r'\b(create|make|generate|write)\b.*\b(doc|document|report|proposal|research|assignment|profile|blueprint|strategy|plan)\b', cmd_lower))
        has_topic = bool(re.search(r'\b(about|on|regarding)\b', cmd_lower))
        if has_doc_request or has_topic:
            return "generate_document"
        if has_url:
            return "open_website"
        return "search_web"

    # Research document requests: "create research about X"
    if re.search(r'\b(write|generate|create|make)\b.*\bresearch\b.*\b(about|on|regarding)\b', cmd_lower):
        return "generate_document"

    # Generic document requests: "create a nice doc about ...", "make document on ..."
    if re.search(r'\b(write|generate|create|make|andaa|tengeneza)\b.*\b(doc|document|report|proposal|assignment|essay|article|profile|blueprint|strategy|plan|exam|test|paper|mtihani)\b', cmd_lower):
        if not re.search(r'\b(file|folder|directory)\b', cmd_lower):
            return "generate_document"

    # Fuzzy matching for document generation with typos
    _doc_gen_patterns = [
        r'\b(write|wrtie|wriet|genrate|generat)\b.*\b(invitation|invetatin|invetation|invtation)\b.*\b(letter|leter)\b',
        r'\b(write|wrtie|wriet)\b.*\b(invitation|invetatin|invetation)\b',
        r'\b(write|wrtie|wriet|genrate|generat)\b.*\b(document|docuemnt|documet)\b',
        r'\b(create|make)\b.*\b(document|docuemnt|documet)\b',
        r'\b(write|wrtie)\b.*\b(report|reprot|repot)\b',
        r'\b(write|wrtie)\b.*\b(assignment|asignment|assignemnt)\b',
        r'\b(write|wrtie)\b.*\b(essay|essy|esay)\b',
        r'\b(write|wrtie)\b.*\b(article|artical|aritcle)\b',
    ]
    for pattern in _doc_gen_patterns:
        if re.search(pattern, cmd_lower):
            return "generate_document"

    # Priority check: "open <app>" / "launch <app>" should always be open_app
    # unless the target has a file extension or contains "file"/"folder"
    for action in ["open ", "launch ", "start ", "fungua "]:
        if cmd_lower.startswith(action):
            target = cmd_lower[len(action):].strip()
            # Remove trailing phrases that don't change intent
            trailing_phrases = [
                r'\s+(on|in|with|using)\s+(a\s+)?new\s+window.*$',
                r'\s+(on|in|with|using)\s+(a\s+)?new\s+instance.*$',
                r'\s+(on|in|with|using)\s+(a\s+)?separate\s+window.*$',
                r'\s+please.*$',
            ]
            for phrase in trailing_phrases:
                target = re.sub(phrase, '', target, flags=re.I).strip()
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

    # Advanced intent classification for system info, troubleshooting, etc.
    # System Information queries
    _system_info_patterns = [
        r'\b(system|computer|pc|laptop|machine)\s+(info|information|specs|specifications|details|status)\b',
        r'\b(show|display|tell|what|check|get)\b.*\b(system|computer|pc|laptop|machine)\b',
        r'\b(show|display|tell|what|check|get)\b.*\b(info|specs|specifications|ram|cpu|disk|storage|memory|processor)\b',
        r'\b(what|which)\b.*\b(os|operating system|windows|macos|linux)\b.*\b(am|i|using|version)\b',
        r'\b(how much|check|show)\b.*\b(ram|memory|storage|disk space|cpu)\b',
        r'\b(my|the)\b.*\b(computer|pc|laptop|machine)\b.*\b(specs|specifications|info|information)\b',
        r'\babout\s+(my|this|the)\b.*\b(computer|pc|laptop|machine)\b',
        r'\bhardware\b.*\b(info|information|details|specs)\b',
        r'\b(show|what|check)\b.*\b(drives|disks|volumes|partitions)\b',
        r'\bcomputer\b',  # Simple "computer" alone
        r'\bsystem\s+info\b',
        r'\bmy\s+specs\b',
    ]
    for pattern in _system_info_patterns:
        if re.search(pattern, cmd_lower):
            return "system_info"

    # Troubleshooting / diagnostic queries
    _troubleshoot_patterns = [
        r'\b(my|the)\s+(computer|pc|laptop|machine)\s+is\s+(slow|lagging|freezing|crashing|not working)\b',
        r'\b(fix|resolve|solve|help with)\b.*\b(error|issue|problem|bug|crash)\b',
        r'\b(why is|what is causing)\b.*\b(slow|lag|freeze|crash|error)\b',
        r'\b(computer|pc|laptop)\s+(problems?|issues?|troubleshooting)\b',
        r'\b(diagnose|diagnostic|check)\b.*\b(health|status|performance)\b',
    ]
    for pattern in _troubleshoot_patterns:
        if re.search(pattern, cmd_lower):
            return "troubleshoot"

    # Automation / organization tasks
    _automation_patterns = [
        r'\b(organize|cleanup|clean up|tidy)\b.*\b(my|the)\b.*\b(files|folders|desktop|documents)\b',
        r'\b(find|locate)\b.*\b(duplicate|duplicates|similar)\b.*\b(files|photos|images)\b',
        r'\b(sort|arrange|categorize)\b.*\b(files|documents|photos|downloads)\b',
        r'\b(automate|automatic)\b.*\b(task|work|process|backup)\b',
    ]
    for pattern in _automation_patterns:
        if re.search(pattern, cmd_lower):
            return "automation_task"

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
        "rename": ("rename_file", "rename_folder"),
        "change": ("rename_file", "rename_folder"),
        "create": ("create_file", "create_folder"),
        "make": ("create_file", "create_folder"),
        "new": ("create_file", "create_folder"),
        "open": ("open_file", "open_folder"),
        "show": ("open_file", "open_folder"),
        "find": ("search_file", "search_folder"),
        "search": ("search_file", "search_folder"),
        "locate": ("search_file", "search_folder"),
        "where": ("search_file", "search_folder"),
        "read": ("read_file", "read_file"),
        "edit": ("open_file", "open_file"),
        "view": ("open_file", "open_file"),
        "kill": ("close_app", "close_app"),
        "quit": ("close_app", "close_app"),
        "exit": ("close_app", "close_app"),
        "stop": ("close_app", "close_app"),
        "terminate": ("close_app", "close_app"),
        "launch": ("open_app", "open_app"),
        "start": ("open_app", "open_app"),
        "run": ("open_app", "run_command"),
        "empty": ("empty_trash", "empty_trash"),
        "clear": ("empty_trash", "empty_trash"),
        "clean": ("empty_trash", "empty_trash"),
    }
    
    # Extract action word from command
    words = cmd_lower.split()
    for word in words:
        word_clean = re.sub(r'[^a-z]', '', word)
        if word_clean in ACTION_TYPE_MAP:
            file_intent, folder_intent = ACTION_TYPE_MAP[word_clean]
            # Detect if it's a file or folder from context
            if any(w in cmd_lower for w in ["folder", "directory", "dir"]):
                return folder_intent
            elif any(w in cmd_lower for w in ["file", "document", "doc", "txt", "pdf"]):
                return file_intent
            else:
                # Default to file for most actions, folder for create/make
                if word_clean in ["create", "make", "new"]:
                    return folder_intent  # Default to folder for creation
                return file_intent
    
    # Natural language understanding fallback
    # Try to understand free-form text
    return _natural_language_understand(cmd_lower)


# Load DistilBERT NLU model
nlu = AMAZONNLU()


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
    
    # Special case: "find and delete" or "find and remove" should NOT be split
    # These are single operations: find the file, then delete it
    cmd_lower = command.lower()

    # Special case: "learn from <url> then create/generate/write doc ..."
    # Keep as one command so URL can be used as document source material.
    if re.search(r'\b(learn|study|jifunze)\s+(from|kutoka)\b.*\b(then|and then|kisha|halafu)\b.*\b(create|make|generate|write)\b.*\b(doc|document|report|proposal|research|assignment|profile|blueprint|strategy|plan)\b', cmd_lower):
        return [command]

    # Special case: exam instructions with clauses like "... and a separate marking scheme ..."
    # Keep as one command to avoid accidentally treating trailing clause as file/folder action.
    if re.search(r'\b(exam|examination|assessment|question\s*paper|test)\b', cmd_lower) and \
       re.search(r'\b(marking scheme|rubric|model answers?|examiner\'s notes|common mistakes)\b', cmd_lower):
        return [command]

    if re.match(r'^\s*find\s+.*\s+and\s+(delete|remove|erase)\s+', cmd_lower):
        return [command]  # Don't split - treat as single command
    
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


def _make_friendly_response(command, result):
    """Make AI responses friendly and conversational like ChatGPT."""
    import random
    
    message = result.get("message", "")
    status = result.get("status", "")
    intent = result.get("intent", "")
    
    # Pass through AMAZON CHAT responses without modification — they're already well-formed
    if intent == "amazon_chat":
        return message
    
    cmd_lower = command.lower().strip()
    
    # --- CASUAL CONVERSATION HANDLING (before action results) ---
    
    # Greetings — route to LLM for natural AMAZON CHAT responses when available
    greeting_words = [
        "hello", "hi ", "hi!", "hey", "howdy", "greetings", "good morning",
        "good afternoon", "good evening", "what's up", "sup", "hola",
        "habari", "habari yako", "mambo", "vipi", "niaje", "hujambo", "shikamoo",
    ]
    simple_greetings = {
        "hi", "hello", "hey", "hola", "habari", "habari yako",
        "mambo", "vipi", "niaje", "hujambo", "shikamoo",
        "nisema habari", "mambo vipi",
    }
    def _contains_greeting_token(text, words):
        for w in words:
            t = w.strip().lower()
            if not t:
                continue
            if " " in t:
                if re.search(rf'(?<!\w){re.escape(t)}(?!\w)', text):
                    return True
            else:
                if re.search(rf'\b{re.escape(t)}\b', text):
                    return True
        return False

    is_greeting_message = _contains_greeting_token(cmd_lower, greeting_words) or cmd_lower in ["hi", "hello", "hey"]
    if is_greeting_message and intent in {"greeting", "amazon_chat", "unknown", "question"}:
        greeting_responses = [
            "Hello! 👋 How can I help you today?",
            "Hi there! 😊 What can I do for you?",
            "Hey! 🌟 Ready to help you with anything you need!",
            "Hello! 🎉 I'm here and ready to assist. What would you like to do?",
            "Hi! ✨ Great to see you! How can I make your day easier?",
            "Hey there! 🚀 What can I help you accomplish today?",
        ]
        sw_greeting_responses = [
            "Habari! 👋 Karibu — naweza kukusaidia nini leo?",
            "Mambo! 😊 Nipo tayari kukusaidia.",
            "Hujambo! ✨ Leo ungependa nikusaidie nini?",
            "Niaje! 🚀 Niko hapa kukusaidia kazi zako.",
        ]
        sw_greeting_words = {"habari", "habari yako", "mambo", "vipi", "niaje", "hujambo", "shikamoo", "nisema habari", "mambo vipi"}

        # If greeting is Swahili, keep response in Swahili consistently.
        if any(w in cmd_lower for w in sw_greeting_words):
            return random.choice(sw_greeting_responses)

        # For short greetings, reply instantly without calling LLM.
        if cmd_lower in simple_greetings:
            return random.choice(greeting_responses)

        if AMAZON_CHAT_AVAILABLE:
            try:
                from ai_assistant.core.amazon_chat import get_llm_response
                llm_response = get_llm_response(command)
                if llm_response and llm_response.strip():
                    return llm_response
            except Exception:
                pass
        return random.choice(greeting_responses)
    
    # How are you / how do you feel — route to LLM when available
    casual_phrases = ["how are you", "how do you feel", "how is it going", 
                      "what's going on", "whats up", "how you doing", "how r u",
                      "are you okay", "you good", "how have you been"]
    if any(phrase in cmd_lower for phrase in casual_phrases):
        if AMAZON_CHAT_AVAILABLE:
            try:
                from ai_assistant.core.amazon_chat import get_llm_response
                llm_response = get_llm_response(command)
                if llm_response and llm_response.strip():
                    return llm_response
            except Exception:
                pass
        casual_responses = [
            "I'm doing great, thanks for asking! 😊 How can I help you today?",
            "I'm wonderful! Ready to assist you with anything you need! 🌟",
            "Feeling fantastic! 🚀 What can I do for you?",
            "I'm excellent! Thanks for checking in. What would you like to work on? ✨",
            "All systems running smoothly! 😄 How can I make your day easier?",
        ]
        return random.choice(casual_responses)
    
    # Thanks / appreciation
    thanks_phrases = ["thank you", "thanks", "thank u", "thx", "appreciate it", 
                      "much appreciated", "that's kind", "good job", "well done",
                      "nice work", "great job", "awesome work"]
    if any(phrase in cmd_lower for phrase in thanks_phrases):
        thanks_responses = [
            "You're welcome! 😊 Happy to help anytime!",
            "Anytime! That's what I'm here for! 🌟",
            "Glad I could help! Don't hesitate to ask if you need anything else! ✨",
            "My pleasure! 🎉 I'm always here when you need me!",
            "No problem at all! Keep up the great work! 🚀",
        ]
        return random.choice(thanks_responses)
    
    # Apologies
    apology_phrases = ["sorry", "my bad", "apologies", "i apologize", "my mistake",
                       "i was wrong", "forgive me"]
    if any(phrase in cmd_lower for phrase in apology_phrases):
        apology_responses = [
            "No worries at all! 😊 I'm here to help whenever you're ready.",
            "That's completely fine! No need to apologize. What can I help with? 🌟",
            "It's all good! ✨ Let me know what you'd like to do next.",
            "Don't worry about it! 🚀 I'm here whenever you need me.",
        ]
        return random.choice(apology_responses)
    
    # Name questions
    name_phrases = ["your name", "who are you", "what are you", "what's your name",
                    "what is your name", "tell me about yourself"]
    if any(phrase in cmd_lower for phrase in name_phrases):
        name_responses = [
            "I'm AMAZON, your AI desktop assistant! 🤖 I'm here to help you manage files, open apps, search the web, generate documents, and much more! ✨",
            "I'm AMAZON! 🌟 Your personal AI assistant powered by machine learning. I can help with files, apps, documents, web searches, and more!",
            "My name is AMAZON!  I'm your smart desktop assistant. Think of me as your helpful companion for getting things done on your computer! ",
        ]
        return random.choice(name_responses)
    
    # Goodbye
    goodbye_phrases = ["goodbye", "bye", "see you", "see ya", "good night", "goodnight",
                       "take care", "catch you later", "talk later"]
    if any(phrase in cmd_lower for phrase in goodbye_phrases):
        goodbye_responses = [
            "Goodbye! Have a wonderful day! Come back anytime you need help! 😊",
            "See you later!  It was great helping you! Take care! ✨",
            "Bye!  Don't hesitate to come back if you need anything! Have a great one! 🎉",
            "Take care!  I'll be here whenever you need me! Goodbye! 👋",
        ]
        return random.choice(goodbye_responses)
    
    # Jokes / fun
    joke_phrases = ["tell me a joke", "make me laugh", "say something funny", "joke"]
    if any(phrase in cmd_lower for phrase in joke_phrases):
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs! 🐛😄",
            "Why was the computer cold? It left its Windows open! 🪟😂",
            "What's a computer's favorite snack? Microchips! 🍟😄",
            "Why did the AI go to therapy? It had too many deep issues! 🤖😂",
            "What do you call a computer that sings? A-Dell! 🎤😄",
        ]
        return random.choice(jokes)
    
    # Casual conversation / reactions ("really?", "wow", "okay", etc.)
    casual_reaction_phrases = ["really", "seriously", "wow", "hmm", "hmmm",
                               "okay", "ok ", "sure", "alright", "cool", "nice",
                               "interesting", "i see", "got it", "understood", "makes sense",
                               "that's cool", "that's great", "awesome", "amazing", "incredible",
                               "unbelievable", "no way", "for real", "legit", "true", "facts",
                               "yep", "yeah", "yup", "nope", "nah", "definitely", "absolutely",
                               "of course", "why not", "sounds good", "perfect", "excellent"]
    if any(phrase in cmd_lower for phrase in casual_reaction_phrases):
        casual_reactions = [
            "Yep! What else can I help you with?",
            "Absolutely! Just let me know what you need!",
            "That's right! I'm here whenever you need me!",
            "Glad you think so! What would you like to do next?",
            "I know, right? Is there anything else I can help with?",
            "For sure! Just ask if you need anything!",
            "Exactly! Feel free to ask me anything!",
            "You got it! What's next on your list?",
        ]
        return random.choice(casual_reactions)
    
    # Short affirmations
    if cmd_lower in ["yes", "yeah", "yep", "yup", "sure", "ok", "okay", "alright"]:
        affirmations = [
            "Great! What would you like me to do?",
            "Awesome! Just tell me what you need!",
            "Perfect! I'm ready when you are!",
            "Sounds good! What's next?",
        ]
        return random.choice(affirmations)
    
    # Short negatives
    if cmd_lower in ["no", "nope", "nah", "not really", "never mind", "forget it", "cancel"]:
        negatives = [
            "No problem! Let me know if you change your mind!",
            "All good! I'm here whenever you need me!",
            "Sure thing! Just ask if you need anything else!",
            "Got it! I'll be here if you need help!",
        ]
        return random.choice(negatives)
    
    # --- ACTION RESULT HANDLING ---
    
    # Friendly conversational additions
    friendly_closers = [
        " Let me know if you need anything else!",
        " Is there anything else I can help you with?",
        " Feel free to ask if you need more help!",
        " I'm here if you need anything else!",
        " Just let me know if there's more I can do!",
        " What else can I help you with today?",
        " Need anything else? Just ask!",
    ]
    
    # For document generation, keep message minimal (UI handles formatting)
    if intent == "generate_document" and status == "success":
        return message
    
    # For successful actions, add friendly tone
    if status == "success":
        friendly_openers = [
            "Sure! ", "Of course! ", "Happy to help! ", "No problem! ",
            "Absolutely! ", "You got it! ", "Done! ", "All set! ",
            "Perfect! ", "Great! ", "Awesome! ",
        ]
        # Add friendly opener if message doesn't already start with one
        if not any(message.lower().startswith(opener.lower()) for opener in friendly_openers):
            opener = random.choice(friendly_openers)
            message = opener + message[0].lower() + message[1:] if message else opener
        
        # Add friendly closer for some actions
        if intent in ["open_app", "open_file", "open_folder", "create_file", "create_folder",
                      "delete_file", "delete_folder", "empty_trash", "copy_file", "copy_folder",
                      "move_file", "move_folder", "rename_file", "rename_folder"]:
            if random.random() < 0.4:  # 40% chance to add friendly closer
                message += random.choice(friendly_closers)
    
    # For failed actions, be empathetic
    elif status == "failed":
        empathetic_phrases = [
            "I'm sorry, but ", "Oops! ", "Hmm, ", "Unfortunately, ",
            "I wasn't able to do that. ", "Let me try to help - ",
            "No worries, ", "That's okay, ",
        ]
        if not any(message.lower().startswith(phrase.lower()) for phrase in empathetic_phrases):
            phrase = random.choice(empathetic_phrases)
            message = phrase + message[0].lower() + message[1:] if message else phrase
        
        # Add helpful suggestion
        if "don't know" in message.lower() or "not found" in message.lower():
            message += " You can try rephrasing or check if the name is correct."
        
        # Add encouraging closer
        if random.random() < 0.5:
            message += " Don't worry, we can try again!"
    
    # For unknown commands, be conversational and friendly
    elif intent == "unknown":
        # Check if it might be a typo for document generation
        cmd_lower_check = command.lower()
        doc_typos = [
            ("invetatin", "invitation"), ("invetation", "invitation"), ("invtation", "invitation"),
            ("leter", "letter"), ("wrtie", "write"), ("wriet", "write"),
            ("genrate", "generate"), ("generat", "generate"),
            ("docuemnt", "document"), ("documet", "document"),
            ("reprot", "report"), ("repot", "report"),
            ("asignment", "assignment"), ("assignemnt", "assignment"),
            ("essy", "essay"), ("esay", "essay"),
            ("artical", "article"), ("aritcle", "article"),
        ]
            
        detected_typos = []
        for typo, correct in doc_typos:
            if typo in cmd_lower_check:
                detected_typos.append((typo, correct))
            
        if detected_typos:
            # Suggest the corrected command
            suggestions = []
            for typo, correct in detected_typos[:3]:  # Show up to 3 corrections
                suggestions.append(f"'{typo}' → '{correct}'")
                
            message = (
                f"I think you might have some typos! I detected:\n"
                f"  • {', '.join(suggestions)}\n\n"
                f"Did you mean to generate a document? Try:\n"
                f"  • \"write invitation letter\"\n"
                f"  • \"create document\"\n"
                f"  • \"generate report\"\n\n"
                f"Or just tell me what you'd like to create! "
            )
        else:
            conversational_responses = [
                f"I'm not quite sure what you mean by '{command}'. Could you rephrase that? I'm here to help! 😊",
                f"Hmm, I didn't quite catch that. Could you try saying it differently? I want to make sure I understand! ",
                f"I'm still learning! I didn't understand '{command}'. Can you try again? I'm getting better every day! 🚀",
                f"I'm not sure I understood that. Could you help me by rephrasing? I appreciate your patience! ✨",
                f"That's a new one for me! Could you explain what you'd like me to do? I'm eager to learn! ",
            ]
            message = random.choice(conversational_responses)
    
    return message


def process_command(command):
    """Main entry point: parse command, classify intent, route to handler.
    Supports compound commands (e.g. 'open X and create Y')."""
    command = command.strip()

    if not command:
        return make_result(None, None, "failed", "Empty command")

    # Auto-correct typos
    try:
        from system.typo_corrector import auto_correct
        corrected_command, corrections = auto_correct(command)
        if corrections:
            # Store corrections for potential display
            _last_corrections = corrections
            command = corrected_command
    except Exception:
        pass  # Don't let typo correction errors affect command processing

    # Special handling: "find and delete X" or "find and remove X"
    # This is a single operation: search for the file, then delete it
    cmd_lower = command.lower()
    
    # Pattern 1: "find and delete [entity]" or "find and remove [entity]"
    find_delete_match = re.match(
        r'^\s*find\s+and\s+(?:delete|remove|erase)\s+(.+?)\s*$',
        cmd_lower
    )
    
    # Pattern 2: "find [entity] and delete" or "find [entity] and remove"
    if not find_delete_match:
        find_delete_match = re.match(
            r'^\s*find\s+(?:this\s+|the\s+|a\s+|an\s+|any\s+)?(.+?)\s+and\s+(?:delete|remove|erase)(?:\s+(?:this|the|it))?\s*$',
            cmd_lower
        )
    
    if find_delete_match:
        # Extract the full filename/entity
        entity = find_delete_match.group(1).strip()
        # Clean up filler words but preserve the full name
        entity = re.sub(r'\b(this|the|a|an|any)\b', '', entity, flags=re.I).strip()
        entity = re.sub(r'\s+', ' ', entity).strip()
        
        if entity:
            # Step 1: Search for the file
            from automation.file_tasks import search_file
            search_result = search_file(entity)
            
            if search_result.get("status") == "success":
                # File found - get the path
                found_path = search_result.get("details", {}).get("path") or search_result.get("path")
                if found_path:
                    # Step 2: Delete the found file
                    from automation.file_tasks import delete_file
                    delete_result = delete_file(found_path)
                    
                    if delete_result.get("status") == "success":
                        return make_result(
                            "delete_file", entity, "success",
                            f"Found and deleted: {entity}\nFile removed: {found_path}",
                            delete_result.get("details")
                        )
                    else:
                        return make_result(
                            "delete_file", entity, "failed",
                            f"Found the file but couldn't delete it: {delete_result.get('message', '')}",
                            delete_result.get("details")
                        )
                else:
                    return make_result(
                        "search_file", entity, "failed",
                        f"Found '{entity}' but couldn't get the file path.",
                        search_result.get("details")
                    )
            else:
                return make_result(
                    "search_file", entity, "failed",
                    f"Couldn't find '{entity}' on your device. Try checking the name or location.",
                    search_result.get("details")
                )
        return make_result(None, None, "failed", "What file would you like me to find and delete?")

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

    # Handle None result
    if result is None:
        result = make_result(None, None, "failed", "Command processing failed. Please try again.")

    # Update entity memory for pronoun resolution
    # Track on any result with a valid entity (not just success — "already exists" still means correct entity)
    if result.get("entity"):
        _last_entity["entity"] = result["entity"]
        _last_entity["intent"] = result.get("intent")
        if isinstance(result.get("details"), dict):
            _last_entity["path"] = result["details"].get("path")

    # Auto-learning: Record interaction for future improvement
    try:
        from system.auto_learner import record_interaction
        record_interaction(
            command=command,
            intent=result.get("intent", "unknown"),
            entity=result.get("entity", ""),
            success=result.get("status") == "success",
            response=result.get("message", "")
        )
    except Exception:
        pass  # Don't let learning errors affect command execution

    # Make response friendly and conversational
    if result and isinstance(result, dict):
        result["message"] = _make_friendly_response(command, result)

        # Add auto-suggestions for successful actions
        if result.get("status") == "success" and result.get("intent") != "unknown":
            try:
                from system.conversation_manager import get_suggestions
                intent = result.get("intent", "")
                suggestions = get_suggestions(command, intent)
                if suggestions:
                    # Add first suggestion as a follow-up
                    result["suggestions"] = suggestions
                    result["message"] += "\n\n💡 **What's next?**\n"
                    for i, suggestion in enumerate(suggestions[:3], 1):
                        result["message"] += f"  {i}. {suggestion}\n"
                    
                    # Store as pending question for follow-up handling
                    try:
                        from system.conversation_manager import ask_follow_up
                        ask_follow_up(
                            "What's next?",
                            options=suggestions[:3],
                            context={"intent": intent, "command": command}
                        )
                    except Exception:
                        pass  # Don't let suggestion errors affect response
            except Exception:
                pass  # Don't let suggestion errors affect response

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

        # Keyword overrides (check FIRST - more reliable than ML for specific patterns)
        kw_intent = _keyword_intent_override(command)

        # Decision logic:
        # - If keyword pattern matches → ALWAYS use keyword (most reliable)
        # - If no keyword + ML confident (>= 45%) → trust ML
        # - If no keyword + ML uncertain → show "not sure"
        if kw_intent:
            intent = kw_intent
            print(f"Keyword override: {kw_intent} (ML: {ml_intent} {max_confidence:.0%})")
        elif max_confidence >= 0.45:
            intent = ml_intent
            print(f"ML prediction: {ml_intent} ({max_confidence:.0%})")
        elif ml_intent == "unknown":
            # ML model thinks this is an unsupported command
            # Route to AMAZON CHAT for intelligent conversation
            if AMAZON_CHAT_AVAILABLE and is_amazon_chat_prompt(command):
                print(f"Routing to AMAZON CHAT (unknown intent, looks like a prompt/question)")
                return handle_amazon_chat_prompt(command)
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
                # Route questions to AMAZON CHAT for intelligent answers
                if AMAZON_CHAT_AVAILABLE:
                    print(f"Routing question to AMAZON CHAT")
                    return handle_amazon_chat_prompt(command)
                return make_result(
                    "question", None, "unsupported",
                    f"That sounds like a question! I'm here to help you with your computer. 😊\n\n"
                    f"I can help you with things like:\n"
                    f"• Creating, organizing, or finding files and folders\n"
                    f"• Opening apps like Chrome, VS Code, or any app you have\n"
                    f"• Searching the web or generating documents\n"
                    f"• Managing your system (empty trash, lock screen, etc.)\n\n"
                    f"Just tell me what you'd like to do, or type 'help' to see all my skills! ✨",
                )
            else:
                # Check if user is asking for help or commands
                help_phrases = ["help", "need help", "can you help", "assist me", "what can you do",
                               "your commands", "list commands", "show commands", "what commands",
                               "how to use", "guide me", "what do you know", "i need your",
                               "show me", "tell me what", "capabilities"]
                if any(phrase in cmd_lower for phrase in help_phrases):
                    return make_result(
                        "help_request", None, "success",
                        f"Of course! I'm here to help! 😊 Here's what I can do for you:\n\n"
                        f"📁 **Files & Folders**\n"
                        f"   • Create, rename, move, copy, or delete files and folders\n"
                        f"   • Search for files or folders on your computer\n"
                        f"   • Open files and folders\n\n"
                        f"🚀 **Apps & System**\n"
                        f"   • Open any app (Chrome, VS Code, Spotify, etc.)\n"
                        f"   • Close apps\n"
                        f"   • Empty trash, lock screen, take screenshots\n\n"
                        f"🌐 **Web & Documents**\n"
                        f"   • Search the web\n"
                        f"   • Generate Word, Excel, or PDF documents\n"
                        f"   • Open websites\n\n"
                        f"Just tell me what you need in plain English, and I'll take care of it! 🎯",
                    )
                else:
                    # Route unrecognized prompts to AMAZON CHAT
                    if AMAZON_CHAT_AVAILABLE and is_amazon_chat_prompt(command):
                        print(f"Routing unrecognized prompt to AMAZON CHAT")
                        return handle_amazon_chat_prompt(command)
                    return make_result(
                        ml_intent, None, "unsupported",
                        f"I'm not quite sure what you mean, but I'm here to help! 😊\n\n"
                        f"Could you try rephrasing that? For example:\n"
                        f"• \"Create a file called report.txt\"\n"
                        f"• \"Open Chrome\" or \"Launch VS Code\"\n"
                        f"• \"Search for my photos\"\n"
                        f"• \"Empty the trash\"\n\n"
                        f"Or just tell me what you'd like to do, and I'll figure it out! 🚀",
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