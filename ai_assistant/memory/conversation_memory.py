"""
AMAZON AI - Conversation Memory
Manages short-term and long-term conversation context.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Storage location
MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "learning"
CONVERSATION_FILE = MEMORY_DIR / "conversation_history.json"


class ConversationMemory:
    """
    Manages conversation history and context.
    
    Features:
    - Short-term buffer (recent messages)
    - Long-term summary (compressed history)
    - Context window for LLM input
    """
    
    def __init__(self, max_short_term: int = 20, max_long_term: int = 100):
        self.short_term: List[Dict] = []
        self.long_term: List[Dict] = []
        self.max_short_term = max_short_term
        self.max_long_term = max_long_term
        self.session_id: str = ""
        
        self._load()
    
    def _load(self):
        """Load conversation history from disk."""
        try:
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            if CONVERSATION_FILE.exists():
                with open(CONVERSATION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.short_term = data.get("short_term", [])
                    self.long_term = data.get("long_term", [])
                    self.session_id = data.get("session_id", "")
        except Exception as e:
            logger.warning(f"Error loading conversation memory: {e}")
    
    def _save(self):
        """Save conversation history to disk."""
        try:
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONVERSATION_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "short_term": self.short_term,
                    "long_term": self.long_term,
                    "session_id": self.session_id,
                    "updated_at": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving conversation memory: {e}")
    
    def add_user_message(self, message: str):
        """Add a user message to memory."""
        self.short_term.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        self._trim_short_term()
        self._save()
    
    def add_ai_message(self, message: str, intent: str = None):
        """Add an AI message to memory."""
        self.short_term.append({
            "role": "assistant",
            "content": message,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        })
        self._trim_short_term()
        self._save()
    
    def get_context(self, n: int = 5) -> List[Dict]:
        """Get the last N messages for context."""
        return self.short_term[-n:]
    
    def get_context_string(self, n: int = 5) -> str:
        """Get conversation context as a formatted string."""
        messages = self.get_context(n)
        lines = []
        for msg in messages:
            role = "User" if msg["role"] == "user" else "AMAZON"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)
    
    def _trim_short_term(self):
        """Keep only recent messages in short-term memory."""
        if len(self.short_term) > self.max_short_term:
            # Move older messages to long-term
            to_move = self.short_term[:-self.max_short_term]
            self.long_term.extend(to_move)
            self.short_term = self.short_term[-self.max_short_term:]
            
            # Trim long-term
            if len(self.long_term) > self.max_long_term:
                self.long_term = self.long_term[-self.max_long_term:]
    
    def clear(self):
        """Clear all conversation memory."""
        self.short_term = []
        self.long_term = []
        self.session_id = ""
        self._save()
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        return {
            "short_term_count": len(self.short_term),
            "long_term_count": len(self.long_term),
            "session_id": self.session_id
        }
    
    def export(self) -> Dict:
        """Export conversation history."""
        return {
            "short_term": self.short_term,
            "long_term": self.long_term,
            "session_id": self.session_id,
            "exported_at": datetime.now().isoformat()
        }


# Singleton instance
_memory_instance = None

def get_conversation_memory() -> ConversationMemory:
    """Get or create the singleton conversation memory."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ConversationMemory()
    return _memory_instance
