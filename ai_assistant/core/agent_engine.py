"""
AMAZON AI - Agent Engine
Main orchestration loop connecting user input to tool execution.
Coordinates planning, reasoning, memory, and tool selection.
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logger = logging.getLogger(__name__)


class AgentEngine:
    """
    Main AI Agent Engine - orchestrates all components.
    
    Architecture:
    User Input -> Intent Classification -> Planning -> Tool Selection -> Execution -> Response
                    |                           |
                    v                           v
               Memory Update            Result Evaluation
    """
    
    def __init__(self):
        self.planner = None
        self.reasoner = None
        self.memory = None
        self.tool_registry = None
        self.security = None
        self._initialized = False
        
    def initialize(self):
        """Initialize all agent components."""
        try:
            # Import components lazily to avoid circular imports
            from ai_assistant.core.planner import TaskPlanner
            from ai_assistant.core.reasoning import ReasoningEngine
            from ai_assistant.core.memory import MemoryManager
            from ai_assistant.core.security import SecurityManager
            from ai_assistant.tools.tool_registry import ToolRegistry
            
            self.planner = TaskPlanner()
            self.reasoner = ReasoningEngine()
            self.memory = MemoryManager()
            self.security = SecurityManager()
            self.tool_registry = ToolRegistry()
            
            self._initialized = True
            logger.info("Agent Engine initialized successfully")
        except Exception as e:
            logger.warning(f"Agent Engine initialization partial: {e}")
            # Continue with partial initialization
            self._initialized = True
    
    def process(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a user command through the full agent pipeline.
        
        Args:
            command: User's natural language command
            context: Optional conversation context
            
        Returns:
            Result dictionary with intent, response, and metadata
        """
        if not self._initialized:
            self.initialize()
        
        start_time = datetime.now()
        
        # Step 1: Record user input in memory
        if self.memory:
            self.memory.record_user_input(command)
        
        # Step 2: Use existing agent.py for intent classification (backward compatible)
        from agent import process_command as legacy_process
        result = legacy_process(command)
        
        # Step 3: Enhance result with agent engine features
        result["engine"] = "amazon_v2"
        result["processing_time"] = (datetime.now() - start_time).total_seconds()
        
        # Step 4: Record interaction in memory for learning
        if self.memory:
            self.memory.record_interaction(
                command=command,
                intent=result.get("intent"),
                entity=result.get("entity"),
                success=result.get("status") == "success",
                response=result.get("message", "")
            )
        
        # Step 5: Log to security audit
        if self.security:
            self.security.log_action(
                command=command,
                intent=result.get("intent"),
                status=result.get("status")
            )
        
        return result
    
    def process_with_planning(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a complex command that may require multiple steps.
        Uses the planner to decompose into sub-tasks.
        """
        if not self._initialized:
            self.initialize()
        
        # Check if command needs planning
        if self.planner and self.planner.needs_planning(command):
            plan = self.planner.create_plan(command)
            results = []
            
            for step in plan.steps:
                # Execute each step
                step_result = self.process(step.command, context)
                results.append(step_result)
                
                # Check if we should continue
                if step_result.get("status") == "failed" and not step.continue_on_failure:
                    break
            
            return {
                "intent": "compound",
                "status": "success" if all(r.get("status") == "success" for r in results) else "partial",
                "message": self._format_compound_response(results),
                "details": {"steps": results},
                "plan": plan.to_dict()
            }
        
        # Fall back to single-step processing
        return self.process(command, context)
    
    def _format_compound_response(self, results: List[Dict]) -> str:
        """Format response for multi-step execution."""
        lines = ["**Completed Tasks:**\n"]
        for i, r in enumerate(results, 1):
            status_icon = "✅" if r.get("status") == "success" else "❌"
            lines.append(f"{i}. {status_icon} {r.get('message', 'Done')}")
        return "\n".join(lines)
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent engine status."""
        return {
            "initialized": self._initialized,
            "planner": self.planner is not None,
            "reasoner": self.reasoner is not None,
            "memory": self.memory is not None,
            "tool_registry": self.tool_registry is not None,
            "security": self.security is not None,
        }


# Singleton instance
_engine_instance = None

def get_agent_engine() -> AgentEngine:
    """Get or create the singleton agent engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AgentEngine()
    return _engine_instance
