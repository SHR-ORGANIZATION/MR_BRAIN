"""
AMAZON AI - File Operation Tool
Wraps file_tasks module for file management operations.
"""
import sys
import logging
from pathlib import Path
from typing import List

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai_assistant.tools.base_tool import BaseTool, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class FileOperationTool(BaseTool):
    """
    Tool for file and folder operations.
    
    Capabilities:
    - Create files and folders
    - Delete files and folders
    - Rename files and folders
    - Move and copy files
    - Search for files
    - Read file contents
    """
    
    @property
    def name(self) -> str:
        return "file_operations"
    
    @property
    def description(self) -> str:
        return "Create, delete, rename, move, copy, and search files and folders"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="Action to perform: 'create', 'delete', 'rename', 'move', 'copy', 'search', 'read'",
                required=True
            ),
            ToolParameter(
                name="item_type",
                type="string",
                description="Type of item: 'file' or 'folder'",
                required=False,
                default="file"
            ),
            ToolParameter(
                name="name",
                type="string",
                description="Name of the file/folder",
                required=True
            ),
            ToolParameter(
                name="destination",
                type="string",
                description="Destination path (for move/copy)",
                required=False
            ),
            ToolParameter(
                name="new_name",
                type="string",
                description="New name (for rename)",
                required=False
            ),
            ToolParameter(
                name="location",
                type="string",
                description="Location: 'desktop', 'documents', 'downloads'",
                required=False,
                default="desktop"
            )
        ]
    
    @property
    def category(self) -> str:
        return "file"
    
    @property
    def requires_confirmation(self) -> bool:
        """Delete operations require confirmation."""
        return True
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute file operation."""
        try:
            action = kwargs.get("action", "").lower()
            item_type = kwargs.get("item_type", "file").lower()
            name = kwargs.get("name", "")
            destination = kwargs.get("destination")
            new_name = kwargs.get("new_name")
            location = kwargs.get("location", "desktop")
            
            if not name:
                return ToolResult(success=False, error="Name is required", message="Please provide a file/folder name")
            
            # Import file tasks
            from automation.file_tasks import (
                create_file, create_folder,
                delete_file, delete_folder,
                rename_file, rename_folder,
                move_file, move_folder,
                copy_file, copy_folder,
                search_file, search_folder,
                read_file_contents
            )
            
            # Resolve location
            base_path = self._resolve_location(location)
            
            # Execute the appropriate action
            if action == "create":
                if item_type == "folder":
                    result = create_folder(name, base_path)
                else:
                    result = create_file(name, base_path)
            
            elif action == "delete":
                if item_type == "folder":
                    result = delete_folder(name)
                else:
                    result = delete_file(name)
            
            elif action == "rename":
                if not new_name:
                    return ToolResult(success=False, error="New name required", message="Please provide a new name")
                if item_type == "folder":
                    result = rename_folder(name, new_name)
                else:
                    result = rename_file(name, new_name)
            
            elif action == "move":
                if not destination:
                    return ToolResult(success=False, error="Destination required", message="Please provide a destination")
                if item_type == "folder":
                    result = move_folder(name, destination)
                else:
                    result = move_file(name, destination)
            
            elif action == "copy":
                if not destination:
                    return ToolResult(success=False, error="Destination required", message="Please provide a destination")
                if item_type == "folder":
                    result = copy_folder(name, destination)
                else:
                    result = copy_file(name, destination)
            
            elif action == "search":
                if item_type == "folder":
                    result = search_folder(name)
                else:
                    result = search_file(name)
            
            elif action == "read":
                result = read_file_contents(name)
            
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}", message=f"Unknown action: {action}")
            
            # Convert result to ToolResult
            if isinstance(result, dict):
                success = result.get("status") == "success"
                message = result.get("message", "Done")
                return ToolResult(
                    success=success,
                    data=result,
                    message=message,
                    error=None if success else message
                )
            else:
                return ToolResult(success=True, data=result, message=str(result))
                
        except Exception as e:
            logger.error(f"File operation error: {e}")
            return ToolResult(success=False, error=str(e), message=f"Operation failed: {str(e)}")
    
    def _resolve_location(self, location: str) -> str:
        """Resolve location name to path."""
        from pathlib import Path
        home = Path.home()
        
        locations = {
            "desktop": home / "Desktop",
            "documents": home / "Documents",
            "downloads": home / "Downloads",
            "pictures": home / "Pictures",
            "music": home / "Music",
            "videos": home / "Videos",
        }
        
        return str(locations.get(location.lower(), locations["desktop"]))
