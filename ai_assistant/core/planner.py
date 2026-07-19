"""
AMAZON AI - Task Planner
Decomposes complex commands into multi-step execution plans.
"""
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    command: str
    intent: str
    description: str
    depends_on: List[int] = field(default_factory=list)
    continue_on_failure: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "command": self.command,
            "intent": self.intent,
            "description": self.description,
            "depends_on": self.depends_on,
            "continue_on_failure": self.continue_on_failure,
        }


@dataclass
class ExecutionPlan:
    """A complete execution plan with multiple steps."""
    original_command: str
    steps: List[PlanStep]
    estimated_complexity: str  # "low", "medium", "high"
    
    def to_dict(self) -> Dict:
        return {
            "original_command": self.original_command,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_complexity": self.estimated_complexity,
        }


class TaskPlanner:
    """
    Decomposes complex user commands into executable plans.
    
    Examples:
    - "find and delete all duplicate photos" -> [search, filter duplicates, delete each]
    - "organize my downloads folder" -> [scan files, categorize, move to folders]
    - "create a python project and open it in vscode" -> [create project, open vscode]
    """
    
    # Patterns that indicate multi-step commands
    COMPOUND_PATTERNS = [
        r'\b(find|search)\s+.*\s+and\s+(delete|remove|erase)\b',
        r'\b(create|make)\s+.*\s+and\s+(open|launch|start)\b',
        r'\b(download|get)\s+.*\s+and\s+(save|store|put)\b',
        r'\b(organize|cleanup|clean up|tidy)\s+(my|the)\b',
        r'\b(move|copy)\s+.*\s+then\s+(delete|remove)\b',
        r'\b(rename|change)\s+.*\s+and\s+(move|copy)\b',
    ]
    
    # Templates for common multi-step operations
    PLAN_TEMPLATES = {
        "find_and_delete": {
            "pattern": r'find\s+(?:this\s+|the\s+|a\s+)?(.+?)\s+and\s+(?:delete|remove|erase)\s+(?:it|them|these)?',
            "steps": [
                {"command_template": "find {entity}", "intent": "search_file", "desc": "Search for files"},
                {"command_template": "delete {found_path}", "intent": "delete_file", "desc": "Delete found files"},
            ]
        },
        "create_and_open": {
            "pattern": r'create\s+(.+?)\s+and\s+open\s+(?:it\s+)?(?:in|with)\s+(.+)',
            "steps": [
                {"command_template": "create file {entity}", "intent": "create_file", "desc": "Create the file"},
                {"command_template": "open {app} {entity}", "intent": "open_app", "desc": "Open in application"},
            ]
        },
        "organize_folder": {
            "pattern": r'organize\s+(?:my\s+)?(.+?)(?:\s+folder)?$',
            "steps": [
                {"command_template": "list files in {folder}", "intent": "search_folder", "desc": "Scan folder contents"},
                {"command_template": "categorize files", "intent": "automation_task", "desc": "Categorize by type"},
                {"command_template": "move files to folders", "intent": "move_file", "desc": "Organize into subfolders"},
            ]
        },
    }
    
    def needs_planning(self, command: str) -> bool:
        """Check if a command requires multi-step planning."""
        cmd_lower = command.lower()
        
        # Check compound patterns
        for pattern in self.COMPOUND_PATTERNS:
            if re.search(pattern, cmd_lower):
                return True
        
        # Check for multiple action verbs
        action_verbs = ['create', 'delete', 'move', 'copy', 'rename', 'open', 'find', 'search', 'organize']
        found_verbs = [v for v in action_verbs if v in cmd_lower]
        if len(found_verbs) >= 2:
            return True
        
        return False
    
    def create_plan(self, command: str) -> ExecutionPlan:
        """Create an execution plan for a complex command."""
        cmd_lower = command.lower()
        
        # Try to match against templates
        for template_name, template in self.PLAN_TEMPLATES.items():
            match = re.search(template["pattern"], cmd_lower)
            if match:
                return self._build_plan_from_template(command, template, match)
        
        # Fall back to generic decomposition
        return self._generic_decomposition(command)
    
    def _build_plan_from_template(
        self, 
        command: str, 
        template: Dict, 
        match: re.Match
    ) -> ExecutionPlan:
        """Build a plan from a matched template."""
        steps = []
        entities = match.groups()
        
        for i, step_template in enumerate(template["steps"]):
            # Substitute entities into command template
            cmd = step_template["command_template"]
            for j, entity in enumerate(entities):
                cmd = cmd.replace(f"{{{['entity', 'found_path', 'folder', 'app'][j]}}}", entity or "")
            
            steps.append(PlanStep(
                command=cmd,
                intent=step_template["intent"],
                description=step_template["desc"],
                depends_on=[i-1] if i > 0 else [],
                continue_on_failure=False
            ))
        
        return ExecutionPlan(
            original_command=command,
            steps=steps,
            estimated_complexity="medium" if len(steps) <= 3 else "high"
        )
    
    def _generic_decomposition(self, command: str) -> ExecutionPlan:
        """Generic decomposition for commands without specific templates."""
        steps = []
        cmd_lower = command.lower()
        
        # Extract action verbs and their targets
        action_patterns = [
            (r'(find|search)\s+(?:for\s+)?(.+?)(?=\s+and|\s+then|$)', 'search_file', 'Search'),
            (r'(delete|remove|erase)\s+(.+?)(?=\s+and|\s+then|$)', 'delete_file', 'Delete'),
            (r'(create|make)\s+(.+?)(?=\s+and|\s+then|$)', 'create_file', 'Create'),
            (r'(open|launch)\s+(.+?)(?=\s+and|\s+then|$)', 'open_app', 'Open'),
            (r'(move|transfer)\s+(.+?)\s+to\s+(.+?)(?=\s+and|\s+then|$)', 'move_file', 'Move'),
            (r'(copy|duplicate)\s+(.+?)\s+to\s+(.+?)(?=\s+and|\s+then|$)', 'copy_file', 'Copy'),
        ]
        
        for pattern, intent, desc in action_patterns:
            match = re.search(pattern, cmd_lower)
            if match:
                groups = match.groups()
                # Build command from matched groups
                if len(groups) >= 2:
                    cmd = f"{groups[0]} {groups[1]}"
                    if len(groups) > 2:
                        cmd += f" to {groups[2]}"
                    
                    steps.append(PlanStep(
                        command=cmd,
                        intent=intent,
                        description=f"{desc} operation",
                        depends_on=[len(steps)-1] if steps else [],
                        continue_on_failure=False
                    ))
        
        # If no steps extracted, create a single-step plan
        if not steps:
            steps.append(PlanStep(
                command=command,
                intent="unknown",
                description="Execute command",
                depends_on=[],
                continue_on_failure=False
            ))
        
        return ExecutionPlan(
            original_command=command,
            steps=steps,
            estimated_complexity="low" if len(steps) == 1 else "medium"
        )
