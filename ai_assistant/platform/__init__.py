"""
AMAZON AI - Platform Module
Cross-platform abstraction layer.
"""
from ai_assistant.platform.base_platform import BasePlatform
from ai_assistant.platform.platform_factory import PlatformFactory, get_platform
from ai_assistant.platform.macos_platform import MacOSPlatform
from ai_assistant.platform.windows_platform import WindowsPlatform
from ai_assistant.platform.linux_platform import LinuxPlatform

__all__ = [
    "BasePlatform",
    "PlatformFactory", "get_platform",
    "MacOSPlatform", "WindowsPlatform", "LinuxPlatform",
]
