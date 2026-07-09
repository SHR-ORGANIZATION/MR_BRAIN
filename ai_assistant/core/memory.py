"""
AMAZON AI - Memory Manager
Unified interface for short-term, long-term, and semantic memory.
Integrates with existing learning/ JSON storage and FAISS semantic index.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Memory storage paths
MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "learning"
SHORT_TERM_FILE = MEMORY_DIR / "short_term_memory.json"
LONG_TERM_FILE = MEMORY_DIR / "long_term_memory.json"
USER_PREFS_FILE = MEMORY_DIR / "user_preferences.json"


class MemoryManager:
    """
    Unified memory management system.
    
    Memory Types:
    - Short-term: Current conversation context (last N messages)
    - Long-term: Learned patterns, successful commands
    - Semantic: Vector embeddings for knowledge retrieval
    - User preferences: Personalization data
    """
    
    def __init__(self):
        self.short_term: List[Dict] = []
        self.long_term: Dict[str, Any] = {}
        self.user_preferences: Dict[str, Any] = {}
        self.conversation_id: str = ""
        self.max_short_term = 50  # Keep last 50 messages
        
        # Load existing memory
        self._load_memory()
    
    def _load_memory(self):
        """Load memory from disk."""
        try:
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            
            # Short-term memory
            if SHORT_TERM_FILE.exists():
                with open(SHORT_TERM_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.short_term = data.get("messages", [])
                    self.conversation_id = data.get("conversation_id", "")
            
            # Long-term memory
            if LONG_TERM_FILE.exists():
                with open(LONG_TERM_FILE, 'r', encoding='utf-8') as f:
                    self.long_term = json.load(f)
            
            # User preferences
            if USER_PREFS_FILE.exists():
                with open(USER_PREFS_FILE, 'r', encoding='utf-8') as f:
                    self.user_preferences = json.load(f)
                    
        except Exception as e:
            logger.warning(f"Error loading memory: {e}")
    
    def _save_memory(self):
        """Save memory to disk."""
        try:
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            
            # Short-term memory
            with open(SHORT_TERM_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "conversation_id": self.conversation_id,
                    "messages": self.short_term[-self.max_short_term:]
                }, f, indent=2)
            
            # Long-term memory
            with open(LONG_TERM_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.long_term, f, indent=2)
            
            # User preferences
            with open(USER_PREFS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Error saving memory: {e}")
    
    # -------------------------------------------------------------------------
    # Short-term Memory (Conversation Context)
    # -------------------------------------------------------------------------
    
    def record_user_input(self, command: str):
        """Record user input in short-term memory."""
        self.short_term.append({
            "role": "user",
            "content": command,
            "timestamp": datetime.now().isoformat()
        })
        self._trim_short_term()
        self._save_memory()
    
    def record_ai_response(self, response: str, intent: str = None):
        """Record AI response in short-term memory."""
        self.short_term.append({
            "role": "assistant",
            "content": response,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        })
        self._trim_short_term()
        self._save_memory()
    
    def get_conversation_context(self, n: int = 5) -> List[Dict]:
        """Get the last N messages for context."""
        return self.short_term[-n:]
    
    def clear_conversation(self):
        """Clear short-term conversation memory."""
        self.short_term = []
        self.conversation_id = ""
        self._save_memory()
    
    def _trim_short_term(self):
        """Keep only recent messages in short-term memory."""
        if len(self.short_term) > self.max_short_term:
            self.short_term = self.short_term[-self.max_short_term:]
    
    # -------------------------------------------------------------------------
    # Long-term Memory (Learned Patterns)
    # -------------------------------------------------------------------------
    
    def record_interaction(
        self,
        command: str,
        intent: str,
        entity: str,
        success: bool,
        response: str = ""
    ):
        """Record an interaction for long-term learning."""
        # Update statistics
        if "statistics" not in self.long_term:
            self.long_term["statistics"] = {
                "total_commands": 0,
                "successful_commands": 0,
                "failed_commands": 0,
                "intent_counts": {}
            }
        
        stats = self.long_term["statistics"]
        stats["total_commands"] += 1
        if success:
            stats["successful_commands"] += 1
        else:
            stats["failed_commands"] += 1
        
        # Track intent frequency
        if intent:
            stats["intent_counts"][intent] = stats["intent_counts"].get(intent, 0) + 1
        
        # Store successful patterns
        if success and command and intent:
            if "successful_patterns" not in self.long_term:
                self.long_term["successful_patterns"] = []
            
            pattern = {
                "command": command.lower(),
                "intent": intent,
                "entity": entity,
                "timestamp": datetime.now().isoformat()
            }
            self.long_term["successful_patterns"].append(pattern)
            
            # Keep only recent patterns
            if len(self.long_term["successful_patterns"]) > 500:
                self.long_term["successful_patterns"] = self.long_term["successful_patterns"][-500:]
        
        self._save_memory()
    
    def get_successful_patterns(self, intent: str = None) -> List[Dict]:
        """Get successful command patterns, optionally filtered by intent."""
        patterns = self.long_term.get("successful_patterns", [])
        if intent:
            patterns = [p for p in patterns if p.get("intent") == intent]
        return patterns
    
    def get_statistics(self) -> Dict:
        """Get memory statistics."""
        return self.long_term.get("statistics", {})
    
    # -------------------------------------------------------------------------
    # User Preferences
    # -------------------------------------------------------------------------
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        self.user_preferences[key] = value
        self._save_memory()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self.user_preferences.get(key, default)
    
    def get_all_preferences(self) -> Dict:
        """Get all user preferences."""
        return self.user_preferences.copy()
    
    # -------------------------------------------------------------------------
    # Semantic Memory (Integration with FAISS)
    # -------------------------------------------------------------------------
    
    def search_semantic(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search using semantic similarity (FAISS)."""
        try:
            from automation.semantic_search import search_by_content
            results = search_by_content(query, top_k=top_k)
            return results
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []
    
    # -------------------------------------------------------------------------
    # Memory Management
    # -------------------------------------------------------------------------
    
    def clear_all_memory(self):
        """Clear all memory (use with caution)."""
        self.short_term = []
        self.long_term = {}
        self.user_preferences = {}
        self.conversation_id = ""
        self._save_memory()
    
    def export_memory(self) -> Dict:
        """Export all memory for backup."""
        return {
            "short_term": self.short_term,
            "long_term": self.long_term,
            "user_preferences": self.user_preferences,
            "exported_at": datetime.now().isoformat()
        }
    
    def import_memory(self, data: Dict):
        """Import memory from backup."""
        self.short_term = data.get("short_term", [])
        self.long_term = data.get("long_term", {})
        self.user_preferences = data.get("user_preferences", {})
        self._save_memory()


# Singleton instance
_memory_instance = None

def get_memory_manager() -> MemoryManager:
    """Get or create the singleton memory manager."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemoryManager()
    return _memory_instance
