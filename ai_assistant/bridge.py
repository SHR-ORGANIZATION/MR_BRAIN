"""
AMAZON AI - Integration Bridge
Connects the new ai_assistant modules with the existing agent.py system.
Provides backward compatibility and graceful degradation.
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class AMAZONBridge:
    """
    Bridge between the new AI platform and the existing agent system.
    
    Features:
    - Backward compatibility with existing agent.py
    - Graceful degradation when new modules unavailable
    - Unified interface for the UI layer
    """
    
    def __init__(self):
        self._agent_engine = None
        self._llm_manager = None
        self._memory = None
        self._tool_registry = None
        self._platform = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize all available components."""
        try:
            # Try to initialize agent engine
            try:
                from ai_assistant.core.agent_engine import get_agent_engine
                self._agent_engine = get_agent_engine()
                logger.info("Agent engine initialized")
            except Exception as e:
                logger.warning(f"Agent engine not available: {e}")
            
            # Try to initialize LLM manager
            try:
                from ai_assistant.models.llm_manager import get_llm_manager
                self._llm_manager = get_llm_manager()
                logger.info(f"LLM manager initialized (available: {self._llm_manager.is_available()})")
            except Exception as e:
                logger.warning(f"LLM manager not available: {e}")
            
            # Try to initialize memory
            try:
                from ai_assistant.core.memory import get_memory_manager
                self._memory = get_memory_manager()
                logger.info("Memory manager initialized")
            except Exception as e:
                logger.warning(f"Memory manager not available: {e}")
            
            # Try to initialize tool registry
            try:
                from ai_assistant.tools.tool_registry import get_tool_registry
                self._tool_registry = get_tool_registry()
                logger.info("Tool registry initialized")
            except Exception as e:
                logger.warning(f"Tool registry not available: {e}")
            
            # Try to initialize platform
            try:
                from ai_assistant.platform.platform_factory import get_platform
                self._platform = get_platform()
                logger.info(f"Platform initialized: {self._platform.name}")
            except Exception as e:
                logger.warning(f"Platform not available: {e}")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Bridge initialization error: {e}")
            return False
    
    def process_command(self, command: str) -> Dict[str, Any]:
        """
        Process a user command using the best available system.
        
        Tries the new agent engine first, falls back to legacy agent.py.
        """
        if not self._initialized:
            self.initialize()
        
        # Try new agent engine first
        if self._agent_engine:
            try:
                result = self._agent_engine.process(command)
                if result.get("status") != "unknown":
                    return result
            except Exception as e:
                logger.warning(f"Agent engine failed: {e}")
        
        # Fall back to legacy agent.py
        try:
            from agent import process_command as legacy_process
            return legacy_process(command)
        except Exception as e:
            logger.error(f"Legacy agent failed: {e}")
            return {
                "intent": "unknown",
                "status": "failed",
                "message": f"Error processing command: {str(e)}"
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of all components."""
        status = {
            "initialized": self._initialized,
            "agent_engine": self._agent_engine is not None,
            "llm_manager": self._llm_manager is not None,
            "memory": self._memory is not None,
            "tool_registry": self._tool_registry is not None,
            "platform": self._platform.name if self._platform else None,
        }
        
        # Add LLM details if available
        if self._llm_manager:
            status["llm_details"] = self._llm_manager.get_status()
        
        return status
    
    def is_llm_available(self) -> bool:
        """Check if local LLM is available."""
        if self._llm_manager:
            return self._llm_manager.is_available()
        return False
    
    def chat_with_llm(self, message: str) -> str:
        """Send a message to the local LLM if available."""
        if self._llm_manager and self._llm_manager.is_available():
            return self._llm_manager.chat(message)
        return ""
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information using the platform module."""
        if self._platform:
            return self._platform.get_system_info()
        return {}
    
    def get_available_tools(self) -> list:
        """Get list of available tools."""
        if self._tool_registry:
            return self._tool_registry.list_tool_names()
        return []


# Singleton instance
_bridge_instance = None

def get_bridge() -> AMAZONBridge:
    """Get or create the singleton bridge."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = AMAZONBridge()
    return _bridge_instance


# Convenience function for backward compatibility
def process_command(command: str) -> Dict[str, Any]:
    """Process a command using the bridge."""
    bridge = get_bridge()
    return bridge.process_command(command)
