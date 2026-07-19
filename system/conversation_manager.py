"""
AMAZON AI - Conversation Manager
Handles conversational flow, follow-up questions, and context-aware responses.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


# Storage location
LEARNING_DIR = Path(__file__).resolve().parent.parent / "learning"
CONVERSATION_FILE = LEARNING_DIR / "conversation_state.json"


class ConversationManager:
    """
    Manages conversational flow with:
    - Follow-up questions
    - Context awareness
    - Multi-step interactions
    - Auto-suggestions
    """
    
    def __init__(self):
        self.active_conversation = None  # Current active conversation
        self.conversation_history = []  # Past conversations
        self.pending_questions = []  # Questions waiting for answers
        self._load_state()
    
    def _load_state(self):
        """Load conversation state from disk."""
        try:
            if CONVERSATION_FILE.exists():
                with open(CONVERSATION_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.conversation_history = state.get("history", [])
                    self.pending_questions = state.get("pending", [])
        except Exception:
            pass
    
    def _save_state(self):
        """Save conversation state to disk."""
        try:
            LEARNING_DIR.mkdir(parents=True, exist_ok=True)
            state = {
                "history": self.conversation_history[-50:],  # Keep last 50
                "pending": self.pending_questions,
                "updated_at": datetime.now().isoformat()
            }
            with open(CONVERSATION_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[ConversationManager] Error saving state: {e}")
    
    def start_conversation(self, intent: str, command: str, context: Dict = None) -> Dict:
        """Start a new conversation thread."""
        self.active_conversation = {
            "id": datetime.now().isoformat(),
            "intent": intent,
            "command": command,
            "context": context or {},
            "started_at": datetime.now().isoformat(),
            "turns": []
        }
        return self.active_conversation
    
    def ask_question(self, question: str, options: List[str] = None, 
                     context: Dict = None) -> Dict:
        """
        Ask a follow-up question and wait for user response.
        
        Args:
            question: The question to ask
            options: Optional list of suggested answers
            context: Additional context for the question
            
        Returns:
            Question object to be sent to user
        """
        question_obj = {
            "id": datetime.now().isoformat(),
            "question": question,
            "options": options or [],
            "context": context or {},
            "asked_at": datetime.now().isoformat(),
            "answered": False,
            "answer": None
        }
        
        self.pending_questions.append(question_obj)
        self._save_state()
        
        return question_obj
    
    def answer_question(self, question_id: str, answer: str) -> Dict:
        """
        Process user's answer to a pending question.
        
        Args:
            question_id: ID of the question being answered
            answer: User's answer
            
        Returns:
            Updated question object
        """
        for q in self.pending_questions:
            if q["id"] == question_id:
                q["answered"] = True
                q["answer"] = answer
                q["answered_at"] = datetime.now().isoformat()
                
                # Move to history
                self.conversation_history.append(q)
                self.pending_questions.remove(q)
                
                self._save_state()
                return q
        
        return None
    
    def get_pending_questions(self) -> List[Dict]:
        """Get all pending questions."""
        return self.pending_questions
    
    def has_pending_questions(self) -> bool:
        """Check if there are pending questions."""
        return len(self.pending_questions) > 0
    
    def clear_pending(self):
        """Clear all pending questions."""
        self.pending_questions = []
        self._save_state()
    
    def get_context_aware_suggestions(self, command: str, intent: str) -> List[str]:
        """
        Get auto-suggestions based on command and intent.
        
        Args:
            command: User's command
            intent: Classified intent
            
        Returns:
            List of suggested follow-up actions
        """
        suggestions = []
        cmd_lower = command.lower()
        
        # Document generation suggestions
        if intent == "generate_document":
            suggestions = [
                "Would you like me to save it as PDF or Word?",
                "Should I add a title page?",
                "Do you want me to include a table of contents?",
                "Would you like me to format it professionally?",
            ]
        
        # File operation suggestions
        elif intent in ["create_file", "create_folder"]:
            suggestions = [
                "Would you like me to open it after creating?",
                "Should I save it on Desktop or Documents?",
                "Do you want to add content to it?",
            ]
        
        # Email suggestions
        elif intent in ["send_email", "open_email"]:
            suggestions = [
                "Would you like me to add a subject line?",
                "Should I attach any files?",
                "Do you want to schedule it for later?",
            ]
        
        # Search suggestions
        elif intent in ["search_file", "search_folder"]:
            suggestions = [
                "Would you like me to filter by file type?",
                "Should I search in a specific location?",
                "Do you want me to sort by date?",
            ]
        
        # Delete suggestions
        elif intent in ["delete_file", "delete_folder"]:
            suggestions = [
                "Are you sure you want to delete this?",
                "Should I move it to trash instead?",
                "Do you want me to create a backup first?",
            ]
        
        return suggestions
    
    def format_question_message(self, question: str, options: List[str] = None) -> str:
        """Format a question message for display."""
        message = f"\n❓ **{question}**\n"
        
        if options:
            message += "\n**Suggestions:**\n"
            for i, option in enumerate(options, 1):
                message += f"  {i}. {option}\n"
            message += "\nJust reply with your choice or type your own answer!"
        
        return message
    
    def get_conversation_summary(self) -> Dict:
        """Get a summary of conversation activity."""
        return {
            "active_conversation": self.active_conversation is not None,
            "pending_questions": len(self.pending_questions),
            "total_history": len(self.conversation_history),
            "last_interaction": self.conversation_history[-1]["answered_at"] if self.conversation_history else None
        }


# Singleton instance
_manager_instance = None

def get_conversation_manager() -> ConversationManager:
    """Get or create the singleton conversation manager."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ConversationManager()
    return _manager_instance


def ask_follow_up(question: str, options: List[str] = None, context: Dict = None) -> Dict:
    """Ask a follow-up question."""
    manager = get_conversation_manager()
    return manager.ask_question(question, options, context)


def get_suggestions(command: str, intent: str) -> List[str]:
    """Get context-aware suggestions."""
    manager = get_conversation_manager()
    return manager.get_context_aware_suggestions(command, intent)
