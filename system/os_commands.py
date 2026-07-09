"""
OS-Specific Commands Database for AMAZON AI
Contains common commands for macOS, Windows, and Linux that the AI can learn and execute.
"""

# macOS Commands
MACOS_COMMANDS = {
    # System Information
    "system info": "system_profiler SPHardwareDataType",
    "os version": "sw_vers",
    "disk usage": "df -h",
    "memory usage": "vm_stat",
    "cpu info": "sysctl -n machdep.cpu.brand_string",
    "network info": "networksetup -listallnetworkservices",
    "wifi networks": "/System/Library/PrivateFrameworks/Apple80211.framework/Resources/airport -s",
    "ip address": "ipconfig getifaddr en0",
    "public ip": "curl -s ifconfig.me",
    
    # File Operations
    "list files": "ls -la",
    "hidden files": "ls -la",
    "file size": "du -sh",
    "find large files": "find . -type f -size +100M",
    "recent files": "find . -type f -mtime -7",
    "disk cleanup": "sudo tmutil thinlocalsnapshots / 100000000000 4",
    
    # Process Management
    "running processes": "ps aux",
    "top processes": "ps aux | head -20",
    "cpu hogs": "ps aux --sort=-%cpu | head -10",
    "memory hogs": "ps aux --sort=-%mem | head -10",
    "kill process": "kill -9",
    
    # Network
    "ping test": "ping -c 4 google.com",
    "dns flush": "sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder",
    "network reset": "sudo ifconfig en0 down && sudo ifconfig en0 up",
    "open ports": "lsof -i -P | grep LISTEN",
    
    # Apps & Services
    "installed apps": "ls /Applications",
    "running apps": "osascript -e 'tell application \"System Events\" to get name of every process whose background only is false'",
    "restart finder": "killall Finder",
    "clear dns": "sudo dscacheutil -flushcache",
    
    # Screenshots
    "take screenshot": "screencapture -x ~/Desktop/screenshot.png",
    "screenshot area": "screencapture -i -x ~/Desktop/screenshot.png",
    "screenshot window": "screencapture -w -x ~/Desktop/screenshot.png",
    
    # System Maintenance
    "clear cache": "sudo rm -rf ~/Library/Caches/*",
    "repair permissions": "diskutil repairPermissions /",
    "safe mode": "sudo nvram boot-args=-x",
    "normal mode": "sudo nvram -d boot-args",
    
    # Homebrew (if installed)
    "update brew": "brew update && brew upgrade",
    "install brew": '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
    "brew list": "brew list",
}

# Windows Commands
WINDOWS_COMMANDS = {
    # System Information
    "system info": "systeminfo",
    "os version": "ver",
    "disk usage": "wmic logicaldisk get size,freespace,caption",
    "memory usage": "systeminfo | findstr /C:\"Total Physical Memory\"",
    "cpu info": "wmic cpu get name",
    "network info": "ipconfig /all",
    "wifi networks": "netsh wlan show networks",
    "ip address": "ipconfig",
    "public ip": "curl ifconfig.me",
    
    # File Operations
    "list files": "dir",
    "hidden files": "dir /a:h",
    "file size": "forfiles /p . /s /m * /c \"cmd /c echo @fsize @path\"",
    "find large files": "forfiles /p . /s /m * /c \"cmd /c if @fsize GEQ 104857600 echo @path @fsize\"",
    "recent files": "forfiles /p . /s /m * /d +01/01/2024 /c \"cmd /c echo @path\"",
    "disk cleanup": "cleanmgr /d C",
    
    # Process Management
    "running processes": "tasklist",
    "top processes": "tasklist /FO CSV | sort",
    "cpu hogs": "wmic process get name,workingsetsize /format:list",
    "kill process": "taskkill /F /IM",
    
    # Network
    "ping test": "ping -n 4 google.com",
    "dns flush": "ipconfig /flushdns",
    "network reset": "netsh winsock reset",
    "open ports": "netstat -ano | findstr LISTENING",
    
    # System Maintenance
    "clear cache": "del /q /s %TEMP%\\*",
    "check disk": "chkdsk C: /f",
    "system file check": "sfc /scannow",
}

# Linux Commands
LINUX_COMMANDS = {
    # System Information
    "system info": "uname -a",
    "os version": "cat /etc/os-release",
    "disk usage": "df -h",
    "memory usage": "free -h",
    "cpu info": "lscpu",
    "network info": "ifconfig || ip addr",
    "wifi networks": "nmcli dev wifi",
    "ip address": "hostname -I",
    "public ip": "curl -s ifconfig.me",
    
    # File Operations
    "list files": "ls -la",
    "hidden files": "ls -la",
    "file size": "du -sh",
    "find large files": "find / -type f -size +100M 2>/dev/null",
    "recent files": "find / -type f -mtime -7 2>/dev/null",
    "disk cleanup": "sudo apt-get clean && sudo apt-get autoremove",
    
    # Process Management
    "running processes": "ps aux",
    "top processes": "top -bn1 | head -20",
    "cpu hogs": "ps aux --sort=-%cpu | head -10",
    "memory hogs": "ps aux --sort=-%mem | head -10",
    "kill process": "kill -9",
    
    # Network
    "ping test": "ping -c 4 google.com",
    "dns flush": "sudo systemd-resolve --flush-caches",
    "network reset": "sudo systemctl restart networking",
    "open ports": "ss -tlnp",
    
    # Package Management
    "update system": "sudo apt-get update && sudo apt-get upgrade",
    "install package": "sudo apt-get install",
    "remove package": "sudo apt-get remove",
    "list packages": "dpkg --list",
    
    # System Maintenance
    "clear cache": "sudo rm -rf /var/cache/apt/archives/*",
    "check disk": "sudo fsck /dev/sda1",
    "view logs": "journalctl -n 50",
}

# Cross-Platform Commands (work on all OS)
CROSS_PLATFORM_COMMANDS = {
    "python version": "python --version",
    "node version": "node --version",
    "git version": "git --version",
    "java version": "java -version",
    "check internet": "ping -c 1 google.com || ping -n 1 google.com",
    "current directory": "pwd || cd",
    "hostname": "hostname",
    "date time": "date",
    "calendar": "cal",
    "who am i": "whoami",
}

# Command Categories for Better Organization
COMMAND_CATEGORIES = {
    "system_info": ["system info", "os version", "cpu info", "memory usage"],
    "disk": ["disk usage", "disk cleanup", "find large files"],
    "network": ["network info", "ip address", "ping test", "dns flush"],
    "processes": ["running processes", "top processes", "kill process"],
    "files": ["list files", "hidden files", "file size", "recent files"],
    "maintenance": ["clear cache", "repair permissions", "update system"],
    "apps": ["installed apps", "running apps", "install package"],
}

def get_os_commands():
    """Get commands for current OS."""
    import platform
    system = platform.system()
    
    if system == "Darwin":
        return {**MACOS_COMMANDS, **CROSS_PLATFORM_COMMANDS}
    elif system == "Windows":
        return {**WINDOWS_COMMANDS, **CROSS_PLATFORM_COMMANDS}
    elif system == "Linux":
        return {**LINUX_COMMANDS, **CROSS_PLATFORM_COMMANDS}
    else:
        return CROSS_PLATFORM_COMMANDS

def get_command_for_action(action):
    """Get the OS-specific command for an action."""
    import platform
    system = platform.system()
    
    action_lower = action.lower()
    
    if system == "Darwin":
        return MACOS_COMMANDS.get(action_lower)
    elif system == "Windows":
        return WINDOWS_COMMANDS.get(action_lower)
    elif system == "Linux":
        return LINUX_COMMANDS.get(action_lower)
    else:
        return CROSS_PLATFORM_COMMANDS.get(action_lower)

def get_all_actions():
    """Get all available actions for current OS."""
    import platform
    system = platform.system()
    
    if system == "Darwin":
        return list(MACOS_COMMANDS.keys()) + list(CROSS_PLATFORM_COMMANDS.keys())
    elif system == "Windows":
        return list(WINDOWS_COMMANDS.keys()) + list(CROSS_PLATFORM_COMMANDS.keys())
    elif system == "Linux":
        return list(LINUX_COMMANDS.keys()) + list(CROSS_PLATFORM_COMMANDS.keys())
    else:
        return list(CROSS_PLATFORM_COMMANDS.keys())
