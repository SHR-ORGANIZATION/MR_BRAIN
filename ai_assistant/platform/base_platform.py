"""
AMAZON AI - Base Platform
Abstract interface for OS-specific operations.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class BasePlatform(ABC):
    """
    Abstract base class for platform-specific operations.
    
    Each OS (Windows, macOS, Linux) implements this interface
    to provide consistent cross-platform functionality.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name."""
        pass
    
    @property
    @abstractmethod
    def is_supported(self) -> bool:
        """Whether this platform is currently supported."""
        pass
    
    # -------------------------------------------------------------------------
    # File System Operations
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def get_user_dirs(self) -> Dict[str, Path]:
        """Get standard user directories (Desktop, Documents, etc)."""
        pass
    
    @abstractmethod
    def open_file_with_default(self, path: str) -> bool:
        """Open a file with the default application."""
        pass
    
    @abstractmethod
    def open_folder(self, path: str) -> bool:
        """Open a folder in the file explorer."""
        pass
    
    # -------------------------------------------------------------------------
    # Application Management
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def get_installed_apps(self) -> List[Dict[str, str]]:
        """Get list of installed applications."""
        pass
    
    @abstractmethod
    def launch_app(self, app_name: str) -> bool:
        """Launch an application by name."""
        pass
    
    @abstractmethod
    def close_app(self, app_name: str) -> bool:
        """Close an application by name."""
        pass
    
    @abstractmethod
    def get_running_apps(self) -> List[Dict[str, Any]]:
        """Get list of running applications."""
        pass
    
    # -------------------------------------------------------------------------
    # System Information
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        pass
    
    @abstractmethod
    def get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information."""
        pass
    
    @abstractmethod
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information."""
        pass
    
    # -------------------------------------------------------------------------
    # Trash / Recycle Bin
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def empty_trash(self) -> bool:
        """Empty the trash/recycle bin."""
        pass
    
    # -------------------------------------------------------------------------
    # Terminal / Shell
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Run a shell command."""
        pass
    
    @abstractmethod
    def get_shell_type(self) -> str:
        """Get the default shell type."""
        pass
