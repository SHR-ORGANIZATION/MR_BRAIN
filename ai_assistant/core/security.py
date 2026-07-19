"""
AMAZON AI - Security Manager
Permission checking, audit logging, and command risk classification.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Audit log location
AUDIT_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "database"
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "audit_log.json"


class RiskLevel(Enum):
    """Command risk classification."""
    SAFE = "safe"           # Read-only operations
    LOW = "low"             # Minor changes (create file)
    MEDIUM = "medium"       # Moderate changes (move, rename)
    HIGH = "high"           # Destructive (delete)
    CRITICAL = "critical"   # System-level (format, shutdown)


class SecurityManager:
    """
    Security and permission management.
    
    Features:
    - Command risk classification
    - Permission checking before execution
    - Audit logging for all actions
    - Confirmation requirements
    """
    
    # Risk classification for intents
    INTENT_RISK_LEVELS = {
        # Safe (read-only)
        "search_file": RiskLevel.SAFE,
        "search_folder": RiskLevel.SAFE,
        "search_app": RiskLevel.SAFE,
        "search_web": RiskLevel.SAFE,
        "read_file": RiskLevel.SAFE,
        "list_processes": RiskLevel.SAFE,
        "system_info": RiskLevel.SAFE,
        "greeting": RiskLevel.SAFE,
        "help_request": RiskLevel.SAFE,
        
        # Low risk (creation)
        "create_file": RiskLevel.LOW,
        "create_folder": RiskLevel.LOW,
        "create_project": RiskLevel.LOW,
        "generate_document": RiskLevel.LOW,
        "open_file": RiskLevel.LOW,
        "open_folder": RiskLevel.LOW,
        "open_app": RiskLevel.LOW,
        "open_website": RiskLevel.LOW,
        
        # Medium risk (modification)
        "rename_file": RiskLevel.MEDIUM,
        "rename_folder": RiskLevel.MEDIUM,
        "move_file": RiskLevel.MEDIUM,
        "move_folder": RiskLevel.MEDIUM,
        "copy_file": RiskLevel.MEDIUM,
        "copy_folder": RiskLevel.MEDIUM,
        "close_app": RiskLevel.MEDIUM,
        "run_command": RiskLevel.MEDIUM,
        
        # High risk (destruction)
        "delete_file": RiskLevel.HIGH,
        "delete_folder": RiskLevel.HIGH,
        "empty_trash": RiskLevel.HIGH,
        
        # Critical (system-level)
        "shutdown": RiskLevel.CRITICAL,
        "restart": RiskLevel.CRITICAL,
    }
    
    # Commands that ALWAYS require confirmation
    ALWAYS_CONFIRM_INTENTS = {
        "delete_file", "delete_folder", "empty_trash",
        "run_command", "close_app"
    }
    
    def __init__(self):
        self.audit_log: List[Dict] = []
        self.max_log_entries = 1000
        self._load_audit_log()
    
    def _load_audit_log(self):
        """Load existing audit log."""
        try:
            AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
            if AUDIT_LOG_FILE.exists():
                with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
                    self.audit_log = json.load(f)
        except Exception as e:
            logger.warning(f"Error loading audit log: {e}")
    
    def _save_audit_log(self):
        """Save audit log to disk."""
        try:
            AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
            # Keep only recent entries
            self.audit_log = self.audit_log[-self.max_log_entries:]
            with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.audit_log, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving audit log: {e}")
    
    def classify_risk(self, intent: str, command: str = "") -> RiskLevel:
        """Classify the risk level of a command."""
        # Check intent-based risk
        risk = self.INTENT_RISK_LEVELS.get(intent, RiskLevel.LOW)
        
        # Upgrade risk for certain command patterns
        cmd_lower = command.lower()
        
        # System commands are higher risk
        if any(word in cmd_lower for word in ['rm -rf', 'format', 'del /s', 'shutdown', 'restart']):
            return RiskLevel.CRITICAL
        
        # Multiple file operations are higher risk
        if 'all' in cmd_lower or 'everything' in cmd_lower:
            if risk in [RiskLevel.HIGH, RiskLevel.MEDIUM]:
                return RiskLevel.CRITICAL
        
        return risk
    
    def requires_confirmation(self, intent: str, risk_level: RiskLevel) -> bool:
        """Determine if an action requires user confirmation."""
        # Always confirm high-risk operations
        if intent in self.ALWAYS_CONFIRM_INTENTS:
            return True
        
        # Confirm medium+ risk operations
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return True
        
        return False
    
    def get_confirmation_message(self, intent: str, entity: str, risk_level: RiskLevel) -> str:
        """Generate appropriate confirmation message based on risk level."""
        if risk_level == RiskLevel.CRITICAL:
            return f"⚠️ **CRITICAL ACTION**\n\nThis action could cause permanent damage to your system.\n\n**Command:** {intent.replace('_', ' ')}\n**Target:** {entity}\n\nAre you absolutely sure you want to proceed?"
        
        elif risk_level == RiskLevel.HIGH:
            return f"⚠️ **Confirm Deletion**\n\nThis action cannot be undone.\n\n**Action:** {intent.replace('_', ' ').title()}\n**Target:** {entity}\n\nDo you want to proceed?"
        
        elif risk_level == RiskLevel.MEDIUM:
            return f"**Confirm Action**\n\n**Action:** {intent.replace('_', ' ').title()}\n**Target:** {entity}\n\nProceed?"
        
        else:
            return f"Confirm: {intent.replace('_', ' ').title()} - {entity}?"
    
    def log_action(
        self,
        command: str,
        intent: str,
        status: str,
        entity: str = None,
        details: Dict = None
    ):
        """Log an action to the audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "intent": intent,
            "entity": entity,
            "status": status,
            "risk_level": self.classify_risk(intent, command).value,
            "details": details
        }
        
        self.audit_log.append(entry)
        self._save_audit_log()
    
    def get_audit_history(self, n: int = 20) -> List[Dict]:
        """Get recent audit log entries."""
        return self.audit_log[-n:]
    
    def get_risk_summary(self) -> Dict:
        """Get summary of risk levels in recent actions."""
        recent = self.audit_log[-100:]
        summary = {
            "safe": 0,
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0
        }
        
        for entry in recent:
            risk = entry.get("risk_level", "low")
            if risk in summary:
                summary[risk] += 1
        
        return summary
    
    def check_permission(self, intent: str, entity: str = None) -> Dict:
        """
        Check if an action is permitted.
        
        Returns:
            Dict with 'permitted', 'requires_confirmation', 'message'
        """
        risk_level = self.classify_risk(intent)
        requires_confirm = self.requires_confirmation(intent, risk_level)
        
        return {
            "permitted": True,  # All actions permitted if confirmed
            "requires_confirmation": requires_confirm,
            "risk_level": risk_level.value,
            "confirmation_message": self.get_confirmation_message(
                intent, entity or "unknown", risk_level
            ) if requires_confirm else None
        }
    
    def clear_audit_log(self):
        """Clear the audit log (admin only)."""
        self.audit_log = []
        self._save_audit_log()


# Singleton instance
_security_instance = None

def get_security_manager() -> SecurityManager:
    """Get or create the singleton security manager."""
    global _security_instance
    if _security_instance is None:
        _security_instance = SecurityManager()
    return _security_instance
