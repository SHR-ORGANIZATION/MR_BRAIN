"""
AMAZON AI - Reasoning Engine
Handles intent confidence evaluation, fallback strategies,
and context-aware decision making.
"""
import re
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """
    Reasoning engine for intelligent decision making.
    
    Responsibilities:
    - Evaluate confidence in intent classification
    - Provide fallback strategies when uncertain
    - Context-aware response generation
    - Error recovery and suggestion generation
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.85
    MEDIUM_CONFIDENCE = 0.60
    LOW_CONFIDENCE = 0.40
    
    # Intent categories for reasoning
    INTENT_CATEGORIES = {
        "file_management": [
            "create_file", "create_folder", "delete_file", "delete_folder",
            "rename_file", "rename_folder", "move_file", "move_folder",
            "copy_file", "copy_folder", "open_file", "open_folder",
            "search_file", "search_folder", "read_file", "empty_trash"
        ],
        "system_info": [
            "system_info", "troubleshoot", "list_processes"
        ],
        "application_control": [
            "open_app", "close_app", "search_app"
        ],
        "web": [
            "open_website", "search_web"
        ],
        "documents": [
            "generate_document"
        ],
        "automation": [
            "automation_task", "create_project"
        ],
        "conversation": [
            "greeting", "help_request", "unknown"
        ]
    }
    
    def __init__(self):
        self.context_history: List[Dict] = []
        self.max_context = 10  # Remember last 10 interactions
    
    def evaluate_confidence(
        self, 
        intent: str, 
        confidence: float,
        command: str
    ) -> Dict[str, Any]:
        """
        Evaluate the confidence in an intent classification.
        
        Returns:
            Dict with confidence_level, needs_clarification, suggested_action
        """
        if confidence >= self.HIGH_CONFIDENCE:
            return {
                "confidence_level": "high",
                "needs_clarification": False,
                "suggested_action": "execute",
                "message": None
            }
        elif confidence >= self.MEDIUM_CONFIDENCE:
            return {
                "confidence_level": "medium",
                "needs_clarification": False,
                "suggested_action": "execute_with_caution",
                "message": None
            }
        elif confidence >= self.LOW_CONFIDENCE:
            return {
                "confidence_level": "low",
                "needs_clarification": True,
                "suggested_action": "ask_clarification",
                "message": self._generate_clarification_request(command, intent)
            }
        else:
            return {
                "confidence_level": "very_low",
                "needs_clarification": True,
                "suggested_action": "fallback",
                "message": self._generate_fallback_response(command)
            }
    
    def get_intent_category(self, intent: str) -> str:
        """Get the category for a given intent."""
        for category, intents in self.INTENT_CATEGORIES.items():
            if intent in intents:
                return category
        return "unknown"
    
    def should_confirm_before_execute(self, intent: str, entity: str) -> bool:
        """Determine if we should ask for confirmation before executing."""
        # Always confirm destructive operations
        destructive_intents = [
            "delete_file", "delete_folder", "empty_trash",
            "move_file", "move_folder"
        ]
        
        if intent in destructive_intents:
            return True
        
        # Confirm if entity is ambiguous
        if entity and self._is_ambiguous_entity(entity):
            return True
        
        return False
    
    def generate_error_recovery(
        self, 
        command: str, 
        error: str, 
        intent: str
    ) -> Dict[str, Any]:
        """Generate recovery suggestions for failed operations."""
        error_lower = error.lower()
        
        # File not found errors
        if "not found" in error_lower or "couldn't find" in error_lower:
            return {
                "recovery_type": "search_alternative",
                "suggestions": [
                    "Check the spelling of the file name",
                    "Try searching with 'find' command first",
                    "The file might be in a different folder"
                ],
                "auto_fix": False
            }
        
        # Permission errors
        if "permission" in error_lower or "access denied" in error_lower:
            return {
                "recovery_type": "permission_issue",
                "suggestions": [
                    "You may need admin privileges for this action",
                    "Try running as administrator",
                    "Check file/folder permissions"
                ],
                "auto_fix": False
            }
        
        # App not found errors
        if "app" in error_lower and "not found" in error_lower:
            return {
                "recovery_type": "app_not_found",
                "suggestions": [
                    "Make sure the application is installed",
                    "Try the full application name",
                    "Check if the app is in your Applications folder"
                ],
                "auto_fix": False
            }
        
        # Generic error
        return {
            "recovery_type": "generic",
            "suggestions": [
                "Please try again",
                "Check your command and try again",
                "Type 'help' for available commands"
            ],
            "auto_fix": False
        }
    
    def generate_contextual_response(
        self, 
        command: str, 
        intent: str,
        previous_commands: List[str]
    ) -> Optional[str]:
        """Generate a response that takes conversation context into account."""
        if not previous_commands:
            return None
        
        # Check if this is a follow-up command
        follow_up_patterns = [
            r'^(do\s+)?(it|that|same|again)$',
            r'^(yes|yeah|yep|sure|ok)$',
            r'^(no|nope|nah|cancel)$',
        ]
        
        cmd_lower = command.lower()
        for pattern in follow_up_patterns:
            if re.match(pattern, cmd_lower):
                return self._handle_follow_up(command, intent, previous_commands)
        
        return None
    
    def _handle_follow_up(
        self, 
        command: str, 
        intent: str,
        previous_commands: List[str]
    ) -> str:
        """Handle follow-up commands like 'do it again' or 'yes'."""
        cmd_lower = command.lower()
        
        if cmd_lower in ['yes', 'yeah', 'yep', 'sure', 'ok']:
            return "confirmed"
        elif cmd_lower in ['no', 'nope', 'nah', 'cancel']:
            return "cancelled"
        elif 'again' in cmd_lower:
            return "repeat"
        
        return "acknowledge"
    
    def _generate_clarification_request(self, command: str, intent: str) -> str:
        """Generate a clarification request when confidence is low."""
        category = self.get_intent_category(intent)
        
        if category == "file_management":
            return f"I'm not sure which file operation you want. Could you clarify? For example:\n• 'create file [name]'\n• 'delete file [name]'\n• 'find [filename]'"
        elif category == "application_control":
            return f"Which application would you like me to work with? Please specify the app name."
        elif category == "web":
            return f"Would you like me to:\n• Open a website\n• Search the web for something"
        else:
            return f"I didn't quite understand that. Could you rephrase? You can type 'help' to see available commands."
    
    def _generate_fallback_response(self, command: str) -> str:
        """Generate a fallback response when intent is completely unclear."""
        return (
            "I didn't quite understand that command. You can try:\n"
            "• 'create file [name]' or 'create folder [name]'\n"
            "• 'open chrome', 'open notepad', etc.\n"
            "• 'search for [topic]' or 'search web [topic]'\n"
            "• 'list processes' or 'run command [cmd]'\n"
            "• Type 'help' for a full list of commands."
        )
    
    def _is_ambiguous_entity(self, entity: str) -> bool:
        """Check if an entity name is ambiguous (could match multiple items)."""
        # Short names are often ambiguous
        if len(entity) <= 2:
            return True
        
        # Common words that might match multiple things
        ambiguous_words = ['file', 'folder', 'document', 'image', 'photo', 'report']
        if entity.lower() in ambiguous_words:
            return True
        
        return False
    
    def record_context(self, command: str, intent: str, success: bool):
        """Record an interaction for context awareness."""
        self.context_history.append({
            "command": command,
            "intent": intent,
            "success": success,
            "timestamp": len(self.context_history)
        })
        
        # Keep only recent context
        if len(self.context_history) > self.max_context:
            self.context_history = self.context_history[-self.max_context:]
