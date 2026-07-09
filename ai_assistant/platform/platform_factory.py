"""
AMAZON AI - Platform Factory
Auto-detect and load the correct platform module.
"""
import platform
import logging
from typing import Optional

from ai_assistant.platform.base_platform import BasePlatform

logger = logging.getLogger(__name__)


class PlatformFactory:
    """Factory for creating platform-specific instances."""
    
    _instance: Optional[BasePlatform] = None
    
    @classmethod
    def get_platform(cls) -> BasePlatform:
        """Get the platform instance for the current OS."""
        if cls._instance is not None:
            return cls._instance
        
        os_type = platform.system()
        
        if os_type == "Darwin":
            from ai_assistant.platform.macos_platform import MacOSPlatform
            cls._instance = MacOSPlatform()
            logger.info("Loaded macOS platform")
        
        elif os_type == "Windows":
            from ai_assistant.platform.windows_platform import WindowsPlatform
            cls._instance = WindowsPlatform()
            logger.info("Loaded Windows platform")
        
        elif os_type == "Linux":
            from ai_assistant.platform.linux_platform import LinuxPlatform
            cls._instance = LinuxPlatform()
            logger.info("Loaded Linux platform")
        
        else:
            logger.warning(f"Unknown OS: {os_type}, using fallback")
            from ai_assistant.platform.linux_platform import LinuxPlatform
            cls._instance = LinuxPlatform()
        
        return cls._instance
    
    @classmethod
    def get_os_type(cls) -> str:
        """Get the current OS type."""
        return platform.system()
    
    @classmethod
    def is_macos(cls) -> bool:
        """Check if running on macOS."""
        return platform.system() == "Darwin"
    
    @classmethod
    def is_windows(cls) -> bool:
        """Check if running on Windows."""
        return platform.system() == "Windows"
    
    @classmethod
    def is_linux(cls) -> bool:
        """Check if running on Linux."""
        return platform.system() == "Linux"


def get_platform() -> BasePlatform:
    """Convenience function to get the platform instance."""
    return PlatformFactory.get_platform()
