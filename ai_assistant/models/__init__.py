"""
AMAZON AI - Models Module
Local LLM integration and hardware detection.
"""
from ai_assistant.models.llm_manager import LLMManager, LLMEngine, get_llm_manager
from ai_assistant.models.ollama_client import OllamaClient, OllamaModel, get_ollama_client
from ai_assistant.models.hardware_detector import HardwareDetector, HardwareProfile, get_hardware_detector

__all__ = [
    "LLMManager", "LLMEngine", "get_llm_manager",
    "OllamaClient", "OllamaModel", "get_ollama_client",
    "HardwareDetector", "HardwareProfile", "get_hardware_detector",
]
