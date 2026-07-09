"""
AMAZON AI - Ollama Client
HTTP client for Ollama REST API for local LLM inference.
"""
import json
import logging
import requests
from typing import Dict, Any, Optional, List, Generator
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default Ollama server URL
DEFAULT_OLLAMA_URL = "http://localhost:11434"

# AMAZON AI System Prompt
AMAZON_SYSTEM_PROMPT = """You are AMAZON, an advanced AI desktop assistant. You are:
- Intelligent and helpful
- Friendly and conversational
- Professional but approachable
- Focused on helping users with computer tasks

Your capabilities include:
- File management (create, delete, move, copy, rename files and folders)
- Application control (open, close apps)
- System monitoring (CPU, RAM, disk usage)
- Web search and browsing
- Document generation
- Code assistance

Always respond in a clear, structured format using:
- Bullet points for lists
- Bold for important items
- Code blocks for commands
- Status icons (✅ for success, ❌ for errors, ⚠️ for warnings)

When performing tasks, explain what you're doing step by step.
Never say "I will try" - instead say "I'm doing X" or "I've completed X".
"""


@dataclass
class OllamaModel:
    """Represents an Ollama model."""
    name: str
    size: float  # GB
    modified_at: str
    digest: str
    family: str
    
    @property
    def size_gb(self) -> float:
        return self.size / (1024**3) if self.size > 1000 else self.size


class OllamaClient:
    """
    Client for Ollama REST API.
    
    Features:
    - Model listing and selection
    - Chat completion with streaming
    - System prompt management
    - Connection health checking
    """
    
    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL):
        self.base_url = base_url.rstrip('/')
        self._available = None
        self._models: List[OllamaModel] = []
        self.current_model: Optional[str] = None
    
    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        if self._available is not None:
            return self._available
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            self._available = response.status_code == 200
            if self._available:
                self._load_models()
        except requests.exceptions.ConnectionError:
            self._available = False
        except Exception as e:
            logger.warning(f"Ollama connection error: {e}")
            self._available = False
        
        return self._available
    
    def _load_models(self):
        """Load available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self._models = []
                for model_data in data.get("models", []):
                    self._models.append(OllamaModel(
                        name=model_data.get("name", ""),
                        size=model_data.get("size", 0),
                        modified_at=model_data.get("modified_at", ""),
                        digest=model_data.get("digest", ""),
                        family=self._extract_family(model_data.get("name", ""))
                    ))
                logger.info(f"Found {len(self._models)} Ollama models")
        except Exception as e:
            logger.warning(f"Error loading Ollama models: {e}")
    
    def _extract_family(self, model_name: str) -> str:
        """Extract model family from name."""
        name_lower = model_name.lower()
        if "llama" in name_lower:
            return "llama"
        elif "mistral" in name_lower:
            return "mistral"
        elif "phi" in name_lower:
            return "phi"
        elif "codellama" in name_lower:
            return "codellama"
        elif "qwen" in name_lower:
            return "qwen"
        return "unknown"
    
    def get_models(self) -> List[OllamaModel]:
        """Get list of available models."""
        if not self._models:
            self._load_models()
        return self._models
    
    def get_model_names(self) -> List[str]:
        """Get list of model names."""
        return [m.name for m in self.get_models()]
    
    def select_model(self, model_name: str) -> bool:
        """Select a model to use for chat."""
        available = self.get_model_names()
        if model_name in available:
            self.current_model = model_name
            logger.info(f"Selected Ollama model: {model_name}")
            return True
        logger.warning(f"Model not available: {model_name}")
        return False
    
    def chat(
        self,
        message: str,
        context: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> str:
        """
        Send a chat message to Ollama.
        
        Args:
            message: User's message
            context: Conversation history
            stream: Whether to stream the response
            
        Returns:
            AI response text
        """
        if not self.is_available():
            return "Ollama is not running. Please start Ollama to use local LLM features."
        
        if not self.current_model:
            models = self.get_models()
            if models:
                self.current_model = models[0].name
            else:
                return "No Ollama models found. Please pull a model first."
        
        # Build messages array
        messages = [{"role": "system", "content": AMAZON_SYSTEM_PROMPT}]
        
        if context:
            messages.extend(context)
        
        messages.append({"role": "user", "content": message})
        
        try:
            payload = {
                "model": self.current_model,
                "messages": messages,
                "stream": stream
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
                stream=stream
            )
            
            if response.status_code != 200:
                return f"Ollama error: {response.status_code}"
            
            if stream:
                return self._handle_stream_response(response)
            else:
                data = response.json()
                return data.get("message", {}).get("content", "No response")
                
        except requests.exceptions.Timeout:
            return "Ollama request timed out. The model might be loading or processing."
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return f"Error communicating with Ollama: {str(e)}"
    
    def _handle_stream_response(self, response) -> str:
        """Handle streaming response from Ollama."""
        full_response = []
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    full_response.append(content)
                except json.JSONDecodeError:
                    continue
        return "".join(full_response)
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None
    ) -> str:
        """
        Generate text from a prompt (non-chat mode).
        
        Args:
            prompt: The prompt to generate from
            system: Optional system prompt override
            
        Returns:
            Generated text
        """
        if not self.is_available():
            return "Ollama is not running."
        
        if not self.current_model:
            return "No model selected."
        
        try:
            payload = {
                "model": self.current_model,
                "prompt": prompt,
                "system": system or AMAZON_SYSTEM_PROMPT,
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                return f"Error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            return f"Error: {str(e)}"
    
    def pull_model(self, model_name: str) -> bool:
        """Pull/download a model from Ollama."""
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=600  # 10 minute timeout for downloads
            )
            if response.status_code == 200:
                self._load_models()
                return True
            return False
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get Ollama connection status."""
        return {
            "available": self.is_available(),
            "models_count": len(self._models),
            "current_model": self.current_model,
            "base_url": self.base_url
        }


# Singleton instance
_client_instance = None

def get_ollama_client() -> OllamaClient:
    """Get or create the singleton Ollama client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = OllamaClient()
    return _client_instance
