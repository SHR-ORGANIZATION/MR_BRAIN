"""
AMAZON AI - Code Analysis Tool
Analyzes code projects and provides insights.
"""
import sys
import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai_assistant.tools.base_tool import BaseTool, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class CodeAnalysisTool(BaseTool):
    """
    Tool for analyzing code projects.
    
    Capabilities:
    - Detect programming languages
    - Analyze project structure
    - Count lines of code
    - Identify frameworks
    - Find dependencies
    """
    
    # Language detection by file extension
    LANGUAGE_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "JavaScript (React)",
        ".tsx": "TypeScript (React)",
        ".java": "Java",
        ".cpp": "C++",
        ".c": "C",
        ".cs": "C#",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".md": "Markdown",
        ".sql": "SQL",
        ".sh": "Shell",
        ".bash": "Bash",
    }
    
    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "React": ["react", "react-dom", "from 'react'"],
        "Vue": ["vue", "createApp", "from 'vue'"],
        "Angular": ["@angular/core", "ngModule"],
        "Django": ["django", "from django"],
        "Flask": ["flask", "from flask"],
        "FastAPI": ["fastapi", "from fastapi"],
        "Express": ["express", "require('express')"],
        "Laravel": ["laravel", "use Illuminate"],
        "Spring": ["@SpringBootApplication", "spring-boot"],
        "Next.js": ["next", "from 'next'"],
        "Nuxt": ["nuxt", "from 'nuxt'"],
    }
    
    @property
    def name(self) -> str:
        return "code_analysis"
    
    @property
    def description(self) -> str:
        return "Analyze code projects - detect languages, frameworks, and structure"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="Action: 'analyze_project', 'count_lines', 'detect_framework'",
                required=True
            ),
            ToolParameter(
                name="path",
                type="string",
                description="Path to project directory or file",
                required=True
            ),
            ToolParameter(
                name="include_hidden",
                type="boolean",
                description="Include hidden files/folders",
                required=False,
                default=False
            )
        ]
    
    @property
    def category(self) -> str:
        return "development"
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute code analysis."""
        try:
            action = kwargs.get("action", "").lower()
            path = kwargs.get("path", "")
            include_hidden = kwargs.get("include_hidden", False)
            
            if not path:
                return ToolResult(
                    success=False,
                    error="Path required",
                    message="Please provide a path to analyze"
                )
            
            path_obj = Path(path).expanduser()
            if not path_obj.exists():
                return ToolResult(
                    success=False,
                    error=f"Path not found: {path}",
                    message=f"The path '{path}' does not exist"
                )
            
            if action == "analyze_project":
                return self._analyze_project(path_obj, include_hidden)
            elif action == "count_lines":
                return self._count_lines(path_obj, include_hidden)
            elif action == "detect_framework":
                return self._detect_framework(path_obj)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    message=f"Unknown action: {action}"
                )
        
        except Exception as e:
            logger.error(f"Code analysis error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Analysis failed: {str(e)}"
            )
    
    def _analyze_project(self, path: Path, include_hidden: bool) -> ToolResult:
        """Analyze a project directory."""
        if not path.is_dir():
            return ToolResult(
                success=False,
                error="Not a directory",
                message=f"'{path}' is not a directory"
            )
        
        # Collect statistics
        languages = defaultdict(int)
        frameworks = set()
        total_files = 0
        total_lines = 0
        file_types = defaultdict(int)
        
        # Skip patterns
        skip_dirs = {
            "node_modules", ".git", "__pycache__", "venv", ".venv",
            "env", ".env", "dist", "build", ".idea", ".vscode"
        }
        
        for root, dirs, files in os.walk(path):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in skip_dirs and (include_hidden or not d.startswith("."))]
            
            for file in files:
                file_path = Path(root) / file
                
                # Skip hidden files if not included
                if not include_hidden and file.startswith("."):
                    continue
                
                total_files += 1
                ext = file_path.suffix.lower()
                
                if ext in self.LANGUAGE_MAP:
                    lang = self.LANGUAGE_MAP[ext]
                    file_types[ext] += 1
                    
                    # Count lines
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = sum(1 for _ in f)
                            languages[lang] += lines
                            total_lines += lines
                    except Exception:
                        pass
                    
                    # Detect frameworks
                    if ext in ['.js', '.ts', '.jsx', '.tsx', '.py', '.php', '.java']:
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read(5000)  # Read first 5KB
                                for framework, patterns in self.FRAMEWORK_PATTERNS.items():
                                    if any(p in content for p in patterns):
                                        frameworks.add(framework)
                        except Exception:
                            pass
        
        # Build result
        result = {
            "path": str(path),
            "total_files": total_files,
            "total_lines": total_lines,
            "languages": dict(languages),
            "frameworks": list(frameworks),
            "file_types": dict(file_types)
        }
        
        # Format message
        lines = [f"📊 **Project Analysis:** {path.name}\n"]
        lines.append(f"**Total Files:** {total_files}")
        lines.append(f"**Total Lines:** {total_lines:,}\n")
        
        if languages:
            lines.append("**Languages:**")
            sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
            for lang, line_count in sorted_langs[:5]:
                pct = (line_count / total_lines * 100) if total_lines > 0 else 0
                lines.append(f"  • {lang}: {line_count:,} lines ({pct:.1f}%)")
            lines.append("")
        
        if frameworks:
            lines.append("**Frameworks Detected:**")
            for fw in frameworks:
                lines.append(f"  • {fw}")
            lines.append("")
        
        return ToolResult(
            success=True,
            data=result,
            message="\n".join(lines)
        )
    
    def _count_lines(self, path: Path, include_hidden: bool) -> ToolResult:
        """Count lines of code in a file or directory."""
        if path.is_file():
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = sum(1 for _ in f)
                return ToolResult(
                    success=True,
                    data={"path": str(path), "lines": lines},
                    message=f"📄 **{path.name}**: {lines:,} lines"
                )
            except Exception as e:
                return ToolResult(success=False, error=str(e), message=f"Error reading file: {e}")
        
        # Directory - count all code files
        total = 0
        by_extension = defaultdict(int)
        
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", "__pycache__", "venv"}]
            
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in self.LANGUAGE_MAP:
                    try:
                        file_path = Path(root) / file
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = sum(1 for _ in f)
                            total += lines
                            by_extension[ext] += lines
                    except Exception:
                        pass
        
        return ToolResult(
            success=True,
            data={"path": str(path), "total_lines": total, "by_extension": dict(by_extension)},
            message=f"📊 **{path.name}**: {total:,} total lines of code"
        )
    
    def _detect_framework(self, path: Path) -> ToolResult:
        """Detect frameworks used in a project."""
        frameworks = set()
        
        # Check package.json for JS frameworks
        package_json = path / "package.json"
        if package_json.exists():
            try:
                import json
                with open(package_json, 'r') as f:
                    pkg = json.load(f)
                    deps = list(pkg.get("dependencies", {}).keys())
                    deps += list(pkg.get("devDependencies", {}).keys())
                    
                    if "react" in deps:
                        frameworks.add("React")
                    if "vue" in deps:
                        frameworks.add("Vue")
                    if "@angular/core" in deps:
                        frameworks.add("Angular")
                    if "next" in deps:
                        frameworks.add("Next.js")
                    if "express" in deps:
                        frameworks.add("Express")
            except Exception:
                pass
        
        # Check requirements.txt for Python frameworks
        requirements = path / "requirements.txt"
        if requirements.exists():
            try:
                with open(requirements, 'r') as f:
                    content = f.read().lower()
                    if "django" in content:
                        frameworks.add("Django")
                    if "flask" in content:
                        frameworks.add("Flask")
                    if "fastapi" in content:
                        frameworks.add("FastAPI")
            except Exception:
                pass
        
        # Check composer.json for PHP
        composer = path / "composer.json"
        if composer.exists():
            try:
                import json
                with open(composer, 'r') as f:
                    cmp = json.load(f)
                    deps = list(cmp.get("require", {}).keys())
                    if any("laravel" in d for d in deps):
                        frameworks.add("Laravel")
            except Exception:
                pass
        
        if frameworks:
            msg = "🛠️ **Frameworks Detected:**\n"
            for fw in frameworks:
                msg += f"  • {fw}\n"
        else:
            msg = "No frameworks detected in this project."
        
        return ToolResult(
            success=True,
            data={"frameworks": list(frameworks)},
            message=msg
        )
