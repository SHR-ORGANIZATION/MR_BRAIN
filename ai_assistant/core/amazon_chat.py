"""
AMAZON AI - AMAZON CHAT Prompt Handler
Routes general questions and prompts to the LLM for intelligent, 
conversational responses — AMAZON CHAT mode.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def is_amazon_chat_prompt(text: str) -> bool:
    """
    Determine if the user input is an AMAZON CHAT prompt/question 
    rather than a system command.
    """
    text_lower = text.lower().strip()
    
    # Question patterns
    question_starters = [
        "what is", "what are", "what was", "what were",
        "who is", "who are", "who was", "who were",
        "where is", "where are", "where did",
        "when did", "when was", "when is",
        "why is", "why are", "why did", "why do",
        "how does", "how do", "how did", "how can", "how to",
        "can you", "could you", "would you",
        "do you", "does", "did",
        "is it", "are they", "was it",
        "tell me about", "explain", "describe",
        "what do you think", "what's your opinion",
        "help me with", "i need help",
        "write a", "write an", "write me",
        "give me", "generate", "create a",
        "summarize", "translate",
        "what does", "what happened",
        "how many", "how much", "how far",
        "what if", "suppose", "imagine",
    ]
    
    # Check if starts with question pattern
    for starter in question_starters:
        if text_lower.startswith(starter):
            return True
    
    # Ends with question mark
    if text_lower.rstrip().endswith("?"):
        return True
    
    # Contains question words in first few words
    words = text_lower.split()[:5]
    question_words = {"what", "who", "where", "when", "why", "how", "which", "whose", "whom"}
    if question_words.intersection(set(words)):
        return True
    
    # Longer text that doesn't look like a command (more than 5 words, no action verbs for files/apps)
    command_keywords = {
        "open", "close", "create", "delete", "remove", "rename", "move", "copy",
        "search", "find", "empty", "launch", "exit", "read", "write file",
        "make folder", "make file", "show path", "locate",
    }
    
    has_command_keyword = any(kw in text_lower for kw in command_keywords)
    
    if len(text_lower.split()) > 5 and not has_command_keyword:
        return True
    
    return False


def get_llm_response(user_message: str, conversation_history: Optional[list] = None) -> str:
    """
    Get an intelligent AMAZON CHAT response from the LLM.
    
    Args:
        user_message: The user's question or prompt
        conversation_history: Optional list of previous messages
        
    Returns:
        AI response string
    """
    try:
        from ai_assistant.models.llm_manager import get_llm_manager
        llm = get_llm_manager()
        
        if llm.is_available():
            response = llm.chat(user_message, use_context=True)
            if response and response.strip():
                return response
    except Exception as e:
        logger.warning(f"LLM chat failed: {e}")
    
    # Fallback: Provide a helpful response with setup instructions
    return _smart_fallback_response(user_message)


def _smart_fallback_response(user_message: str) -> str:
    """
    Provide a smart fallback response when LLM is not available.
    """
    text_lower = user_message.lower().strip()
    
    # For questions, offer to search
    if any(text_lower.startswith(w) for w in ["what", "who", "where", "when", "why", "how", "is", "are", "do", "does", "did", "can"]):
        return (
            f"That's a great question! I'd love to give you a detailed answer.\n\n"
            f"💡 **Tip:** Install Ollama to enable AMAZON CHAT mode:\n"
            f"   1. Download from: https://ollama.com\n"
            f"   2. Run: `ollama pull llama3.2`\n"
            f"   3. Restart AMAZON AI\n\n"
            f"With Ollama, AMAZON CHAT can answer any question — directly on your machine!"
        )
    
    # For creative/generation requests
    if any(text_lower.startswith(w) for w in ["write", "create", "generate", "make me", "give me"]):
        return (
            f"I'd love to help you with that!\n\n"
            f"To generate content like essays, stories, or creative writing, "
            f"I need AMAZON CHAT mode running.\n\n"
            f"💡 **Enable AMAZON CHAT:**\n"
            f"   1. Install Ollama: https://ollama.com\n"
            f"   2. Run: `ollama pull llama3.2`\n"
            f"   3. Restart AMAZON AI\n\n"
            f"Then AMAZON CHAT can write anything you need — essays, emails, code, stories, and more!"
        )
    
    # General fallback
    return (
        f"I appreciate you chatting with me! I want to give you a great response.\n\n"
        f"Right now, AMAZON CHAT isn't running. To unlock full conversation mode:\n\n"
        f"💡 **Quick setup:**\n"
        f"   1. Install Ollama: https://ollama.com\n"
        f"   2. Open terminal and run: `ollama pull llama3.2`\n"
        f"   3. Restart AMAZON AI\n\n"
        f"Once set up, AMAZON CHAT can answer any question, write content, explain topics, "
        f"and have discussions — all running locally on your machine!"
    )


def handle_amazon_chat_prompt(command: str) -> Dict[str, Any]:
    """
    Handle an AMAZON CHAT prompt and return a result dict 
    compatible with the existing agent system.
    """
    from intent_router import make_result
    
    # Get the LLM response
    response = get_llm_response(command)
    
    return make_result(
        "amazon_chat",
        None,
        "success",
        response,
        {"engine": "llm" if _is_llm_available() else "fallback"}
    )


def _is_llm_available() -> bool:
    """Check if LLM is available."""
    try:
        from ai_assistant.models.llm_manager import get_llm_manager
        return get_llm_manager().is_available()
    except Exception:
        return False
