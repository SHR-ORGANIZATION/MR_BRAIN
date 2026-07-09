"""
AMAZON AI - LLM Manager
Abstract interface for local LLM engines with automatic selection.
"""
import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class LLMEngine(Enum):
    """Supported LLM engines."""
    OLLAMA = "ollama"
    TRANSFORMERS = "transformers"
    NONE = "none"


class LLMManager:
    """
    Manages local LLM engines and provides unified interface.
    
    Features:
    - Automatic engine detection
    - Model selection based on hardware
    - Graceful fallback when no LLM available
    - Conversation context management
    """
    
    def __init__(self):
        self._engine: Optional[LLMEngine] = None
        self._client = None
        self._conversation_history: List[Dict] = []
        self._max_history = 10
        
        # Try to initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize the best available LLM engine."""
        # Try Ollama first (easiest to set up)
        try:
            from ai_assistant.models.ollama_client import get_ollama_client
            client = get_ollama_client()
            if client.is_available():
                self._engine = LLMEngine.OLLAMA
                self._client = client
                logger.info("Using Ollama as LLM engine")
                return
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
        
        # Fall back to no LLM (use existing keyword/ML routing)
        self._engine = LLMEngine.NONE
        logger.info("No local LLM available - using keyword/ML routing")
    
    def is_available(self) -> bool:
        """Check if any LLM engine is available."""
        return self._engine is not None and self._engine != LLMEngine.NONE
    
    def chat(self, message: str, use_context: bool = True) -> str:
        """
        Send a message to the LLM and get a response.
        
        Args:
            message: User's message
            use_context: Whether to include conversation history
            
        Returns:
            AI response
        """
        if not self.is_available():
            return self._fallback_response(message)
        
        # Get context if enabled
        context = None
        if use_context:
            context = self._conversation_history[-self._max_history:]
        
        # Route to appropriate engine
        if self._engine == LLMEngine.OLLAMA:
            response = self._client.chat(message, context)
        
        # Record in history
        self._conversation_history.append({"role": "user", "content": message})
        self._conversation_history.append({"role": "assistant", "content": response})
        
        # Trim history
        if len(self._conversation_history) > self._max_history * 2:
            self._conversation_history = self._conversation_history[-self._max_history * 2:]
        
        return response
    
    def _fallback_response(self, message: str) -> str:
        """Provide a response when no LLM is available."""
        # This will be handled by the existing agent.py routing
        return ""
    
    def get_status(self) -> Dict[str, Any]:
        """Get LLM manager status."""
        status = {
            "engine": self._engine.value if self._engine else "none",
            "available": self.is_available(),
            "conversation_history": len(self._conversation_history)
        }
        
        if self._engine == LLMEngine.OLLAMA and self._client:
            status["ollama"] = self._client.get_status()
        
        return status
    
    def get_models(self) -> List[str]:
        """Get list of available models."""
        if self._engine == LLMEngine.OLLAMA and self._client:
            return self._client.get_model_names()
        return []
    
    def select_model(self, model_name: str) -> bool:
        """Select a specific model to use."""
        if self._engine == LLMEngine.OLLAMA and self._client:
            return self._client.select_model(model_name)
        return False
    
    def clear_conversation(self):
        """Clear conversation history."""
        self._conversation_history = []
    
    def get_hardware_recommendation(self) -> Dict[str, Any]:
        """Get hardware-based model recommendations."""
        try:
            from ai_assistant.models.hardware_detector import get_hardware_detector
            detector = get_hardware_detector()
            return detector.get_model_recommendation()
        except Exception as e:
            logger.warning(f"Hardware detection failed: {e}")
            return {"error": str(e)}


# Singleton instance
_llm_manager_instance = None

def get_llm_manager() -> LLMManager:
    """Get or create the singleton LLM manager."""
    global _llm_manager_instance
    if _llm_manager_instance is None:
        _llm_manager_instance = LLMManager()
    return _llm_manager_instance
