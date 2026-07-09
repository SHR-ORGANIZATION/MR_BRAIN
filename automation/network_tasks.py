"""Network connectivity detection and online/offline mode handling."""

import socket
import threading
from datetime import datetime

# Global state
_is_online = True
_last_check = None
_check_interval = 30  # seconds

def check_connectivity():
    """Check if the system has internet connectivity."""
    global _is_online, _last_check
    
    # Don't check too frequently
    if _last_check and (datetime.now() - _last_check).total_seconds() < _check_interval:
        return _is_online
    
    try:
        # Try to connect to a reliable server
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        _is_online = True
    except OSError:
        _is_online = False
    
    _last_check = datetime.now()
    return _is_online


def is_online():
    """Return current online status (cached)."""
    return check_connectivity()

def is_offline():
    """Return True if offline."""
    return not check_connectivity()

def get_mode():
    """Return 'online' or 'offline' based on connectivity."""
    return "online" if is_online() else "offline"

class ConnectivityMonitor:
    """Background monitor for connectivity changes."""
    
    def __init__(self, callback=None):
        self.callback = callback
        self.running = False
        self.thread = None
        self.last_status = None
    
    def start(self):
        """Start monitoring connectivity in background."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
    
    def _monitor(self):
        """Background monitoring loop."""
        while self.running:
            current = check_connectivity()
            if current != self.last_status:
                self.last_status = current
                if self.callback:
                    try:
                        self.callback(current)
                    except Exception:
                        pass
            threading.Event().wait(10)  # Check every 10 seconds

# Singleton monitor
_monitor = None


def start_monitoring(callback=None):
    """Start background connectivity monitoring."""
    global _monitor
    if _monitor is None:
        _monitor = ConnectivityMonitor(callback)
        _monitor.start()
    return _monitor


def stop_monitoring():
    """Stop background connectivity monitoring."""
    global _monitor
    if _monitor:
        _monitor.stop()
        _monitor = None
