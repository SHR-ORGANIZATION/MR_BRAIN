"""
AMAZON AI - Tool Registry
Central registration and discovery of all AI tools.
"""
import logging
from typing import Dict, List, Optional, Any
from ai_assistant.tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all AI tools.
    
    Features:
    - Tool registration and discovery
    - Tool selection by name or category
    - Tool schema generation for LLM function calling
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register the default set of tools."""
        # System Monitor
        try:
            from ai_assistant.tools.system_monitor_tool import SystemMonitorTool
            self.register(SystemMonitorTool())
        except Exception as e:
            logger.warning(f"Could not register SystemMonitorTool: {e}")
        
        # File Operations
        try:
            from ai_assistant.tools.file_operation_tool import FileOperationTool
            self.register(FileOperationTool())
        except Exception as e:
            logger.warning(f"Could not register FileOperationTool: {e}")
        
        # Web Browser
        try:
            from ai_assistant.tools.web_browser_tool import WebBrowserTool
            self.register(WebBrowserTool())
        except Exception as e:
            logger.warning(f"Could not register WebBrowserTool: {e}")
        
        # Code Analysis
        try:
            from ai_assistant.tools.code_analysis_tool import CodeAnalysisTool
            self.register(CodeAnalysisTool())
        except Exception as e:
            logger.warning(f"Could not register CodeAnalysisTool: {e}")
        
        # Email
        try:
            from ai_assistant.tools.email_tool import EmailTool
            self.register(EmailTool())
        except Exception as e:
            logger.warning(f"Could not register EmailTool: {e}")
    
    def register(self, tool: BaseTool):
        """Register a new tool."""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def unregister(self, tool_name: str):
        """Unregister a tool."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
    
    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)
    
    def get_by_category(self, category: str) -> List[BaseTool]:
        """Get all tools in a category."""
        return [t for t in self._tools.values() if t.category == category]
    
    def list_tools(self) -> List[Dict]:
        """List all registered tools with their schemas."""
        return [tool.get_schema() for tool in self._tools.values()]
    
    def list_tool_names(self) -> List[str]:
        """List all tool names."""
        return list(self._tools.keys())
    
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool not found: {tool_name}",
                message=f"Tool '{tool_name}' is not available"
            )
        
        try:
            # Validate parameters
            validated = tool.validate_parameters(**kwargs)
            # Execute
            return tool.execute(**validated)
        except ValueError as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Invalid parameters: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Tool execution failed: {str(e)}"
            )
    
    def get_function_schemas(self) -> List[Dict]:
        """Get function calling schemas for all tools (for LLM integration)."""
        return [tool.get_schema() for tool in self._tools.values()]
    
    def select_tool_for_intent(self, intent: str) -> Optional[str]:
        """Select the best tool for a given intent."""
        # Map intents to tools
        intent_tool_map = {
            # System operations
            "system_info": "system_monitor",
            "list_processes": "system_monitor",
            "troubleshoot": "system_monitor",
            
            # File operations
            "create_file": "file_operations",
            "create_folder": "file_operations",
            "delete_file": "file_operations",
            "delete_folder": "file_operations",
            "rename_file": "file_operations",
            "rename_folder": "file_operations",
            "move_file": "file_operations",
            "move_folder": "file_operations",
            "copy_file": "file_operations",
            "copy_folder": "file_operations",
            "search_file": "file_operations",
            "search_folder": "file_operations",
            "read_file": "file_operations",
            
            # Web browser
            "open_website": "web_browser",
            "search_web": "web_browser",
            
            # Code analysis
            "analyze_project": "code_analysis",
            "count_lines": "code_analysis",
            "detect_framework": "code_analysis",
            
            # Email
            "send_email": "email",
            "compose_email": "email",
            "open_email": "email",
        }
        
        tool_name = intent_tool_map.get(intent)
        if tool_name and tool_name in self._tools:
            return tool_name
        
        return None


# Singleton instance
_registry_instance = None

def get_tool_registry() -> ToolRegistry:
    """Get or create the singleton tool registry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance
