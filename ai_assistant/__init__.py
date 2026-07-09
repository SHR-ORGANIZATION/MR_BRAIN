"""
AMAZON AI - Advanced AI Assistant Platform
A comprehensive AI desktop assistant with local LLM support,
modular tools, and cross-platform compatibility.

Modules:
- core: Agent engine, planner, reasoning, memory, security
- models: Local LLM integration (Ollama, Transformers)
- tools: Modular tool system for file, system, web operations
- platform: Cross-platform abstraction (macOS, Windows, Linux)
- memory: RAG knowledge base and conversation memory
"""
from ai_assistant.bridge import get_bridge, process_command

__version__ = "2.0.0"
__author__ = "AMAZON AI Team"

__all__ = [
    "get_bridge",
    "process_command",
]
