"""
AMAZON AI - Base Tool
Abstract interface for all AI tools.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # "string", "integer", "boolean", "array"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    data: Any = None
    message: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error": self.error
        }


class BaseTool(ABC):
    """
    Abstract base class for all AI tools.
    
    All tools must implement:
    - name: Unique identifier
    - description: What the tool does
    - parameters: List of parameters
    - execute(): Main execution method
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the tool."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """List of parameters the tool accepts."""
        pass
    
    @property
    def category(self) -> str:
        """Category of the tool (file, system, web, etc)."""
        return "general"
    
    @property
    def requires_confirmation(self) -> bool:
        """Whether this tool requires user confirmation before execution."""
        return False
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Returns:
            ToolResult with success status and data
        """
        pass
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate and normalize parameters."""
        validated = {}
        
        for param in self.parameters:
            value = kwargs.get(param.name)
            
            if value is None:
                if param.required and param.default is None:
                    raise ValueError(f"Missing required parameter: {param.name}")
                value = param.default
            
            # Type conversion
            if value is not None:
                if param.type == "integer":
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        raise ValueError(f"Parameter {param.name} must be an integer")
                elif param.type == "boolean":
                    value = bool(value)
            
            validated[param.name] = value
        
        return validated
    
    def get_schema(self) -> Dict:
        """Get tool schema for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.type,
                        "description": p.description
                    }
                    for p in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required]
            }
        }
