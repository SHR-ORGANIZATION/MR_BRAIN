"""
AMAZON AI - AMAZON CHAT Prompt Handler
Routes general questions and prompts to the LLM for intelligent, 
conversational responses — AMAZON CHAT mode.
"""
import logging
import re
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
        # Swahili conversational/help starters
        "nisaidie", "naomba msaada", "msaada", "nifafanulie",
        "nielezee", "nifundishe", "nawezaje", "inawezekana",
        "nionyeshe", "tafadhali nisaidie",
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

    # Swahili question/help words in first few words
    sw_question_words = {"nini", "vipi", "kwa", "nani", "wapi", "lini", "kwa nini", "nawezaje", "nisaidie"}
    if any(w in text_lower for w in sw_question_words):
        return True
    
    # Longer text that doesn't look like a command (more than 5 words, no action verbs for files/apps)
    command_keywords = {
        "open", "close", "create", "delete", "remove", "rename", "move", "copy",
        "search", "find", "empty", "launch", "exit", "read", "write file",
        "make folder", "make file", "show path", "locate",
    }

    sw_command_keywords = {
        "fungua", "funga", "tengeneza", "futa", "hamisha", "nakili", "tafuta", "onyesha njia"
    }
    
    has_command_keyword = any(kw in text_lower for kw in command_keywords)
    has_sw_command_keyword = any(kw in text_lower for kw in sw_command_keywords)
    
    if len(text_lower.split()) > 3 and not has_command_keyword and not has_sw_command_keyword:
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
        from ai_assistant.memory.conversation_memory import get_conversation_memory
        llm = get_llm_manager()
        memory = get_conversation_memory()

        detected_lang = _detect_user_language(user_message)

        direct_smalltalk = _direct_smalltalk_reply(user_message, detected_lang)
        if direct_smalltalk:
            memory.add_user_message(user_message)
            memory.add_ai_message(direct_smalltalk, intent="amazon_chat")
            return direct_smalltalk

        direct_reply = _direct_swahili_smalltalk(user_message)
        if direct_reply:
            memory.add_user_message(user_message)
            memory.add_ai_message(direct_reply, intent="amazon_chat")
            return direct_reply

        direct_practical = _direct_swahili_practical_help(user_message)
        if direct_practical:
            memory.add_user_message(user_message)
            memory.add_ai_message(direct_practical, intent="amazon_chat")
            return direct_practical

        # Persist user turn and build resource-augmented prompt
        memory.add_user_message(user_message)
        routed_message = _prepare_multilingual_prompt(user_message)
        augmented_message = _build_resource_augmented_prompt(routed_message, user_message)
        sw_prompt = detected_lang == "sw"
        
        if llm.is_available():
            # Swahili prompts perform better with clean context isolation.
            response = llm.chat(augmented_message, use_context=not sw_prompt)
            if response and response.strip():
                if sw_prompt:
                    response = _rewrite_swahili_response(llm, user_message, response)
                memory.add_ai_message(response, intent="amazon_chat")
                return response
    except Exception as e:
        logger.warning(f"LLM chat failed: {e}")
    
    # Fallback: Provide a helpful response with setup instructions
    fallback = _smart_fallback_response(user_message)
    try:
        from ai_assistant.memory.conversation_memory import get_conversation_memory
        get_conversation_memory().add_ai_message(fallback, intent="amazon_chat")
    except Exception:
        pass
    return fallback


def _direct_swahili_smalltalk(text: str) -> Optional[str]:
    """Return stable native Swahili for common short greetings/small-talk."""
    low = (text or "").strip().lower()
    if low in {"mambo", "mambo vipi", "habari", "habari yako", "hujambo", "niaje", "vipi", "shikamoo", "uko poa", "uko sawa"}:
        return "Mambo! 😊 Nipo vizuri. Naweza kukusaidia nini leo?"
    if low in {"asante", "ahsante", "thanks", "thank you"}:
        return "Karibu sana! 😊 Ukihitaji chochote, niambie."
    return None


def _direct_smalltalk_reply(text: str, lang: str) -> Optional[str]:
    """Fast deterministic smalltalk responses by detected language."""
    low = (text or "").strip().lower()
    normalized = re.sub(r"\s+", " ", low)

    # Hard overrides independent of language detection
    if low in {"uko poa", "uko sawa", "mambo", "habari", "hujambo", "niaje", "vipi"}:
        return "Nipo poa, asante! 😊 Naweza kukusaidia nini leo?"

    # Greeting phrase handling (prevents model drift on inputs like "hello amazon")
    if re.match(r"^(hi|hello|hey)\b", normalized):
        return "Hi! 👋 How can I help you today?"
    if re.match(r"^(habari|mambo|hujambo|vipi|niaje)\b", normalized):
        return "Mambo! 😊 Nipo vizuri. Naweza kukusaidia nini leo?"

    if lang == "en":
        if low in {"are you good", "are you okay", "how are you", "how you doing", "you good"}:
            return "I'm good, thanks for asking! 😊 How can I help you today?"
        if low in {"hi", "hello", "hey"}:
            return "Hi! 👋 How can I help you today?"

    if lang == "sw":
        if low in {"uko poa", "uko sawa", "vipi", "habari", "mambo", "hujambo", "niaje"}:
            return "Nipo poa, asante! 😊 Naweza kukusaidia nini leo?"

    return None


def _direct_swahili_practical_help(text: str) -> Optional[str]:
    """Deterministic concise Swahili for common practical intents (finance first)."""
    low = (text or "").strip().lower()

    finance_markers = {"mkopo", "kukopa", "pesa", "bajeti", "akiba"}
    if any(m in low for m in finance_markers):
        if "aza" in low and ("mkopo" in low or "kukopa" in low):
            return (
                "Unaweza kuomba mkopo wa AZA kwa kufuata masharti yao rasmi.\n\n"
                "Hatua za haraka:\n"
                "• Fungua app/akaunti ya AZA na uhakiki taarifa zako.\n"
                "• Angalia kiwango cha mkopo unachostahili, riba, ada, na muda wa marejesho.\n"
                "• Chagua kiasi unachoweza kurejesha bila kubanwa.\n"
                "• Tuma ombi na fuatilia uthibitisho ndani ya app.\n\n"
                "Tahadhari: Soma masharti yote kabla ya kuthibitisha, na kopa kiasi unachoweza kurejesha kwa wakati."
            )

        if "bajeti" in low:
            return (
                "Sawa, hii ndiyo njia rahisi ya kupanga bajeti ya mwezi:\n"
                "• Andika mapato yako yote ya mwezi.\n"
                "• Gawa matumizi: muhimu (chakula, kodi, usafiri) na yasiyo muhimu.\n"
                "• Weka lengo la akiba hata kidogo (mfano 10% ya mapato).\n"
                "• Fuatilia matumizi kila wiki na rekebisha pale unapozidi."
            )

    return None


def _build_resource_augmented_prompt(routed_message: str, raw_user_message: str) -> str:
    """Inject local memory + knowledge base context so replies use built project resources."""
    memory_context = ""
    kb_context = ""

    try:
        from ai_assistant.memory.conversation_memory import get_conversation_memory
        memory_context = get_conversation_memory().get_context_string(n=4)
    except Exception:
        memory_context = ""

    try:
        from ai_assistant.memory.knowledge_retriever import get_knowledge_retriever
        kb_context = get_knowledge_retriever().get_context_for_query(raw_user_message, max_chars=1200)
    except Exception:
        kb_context = ""

    context_blocks = []
    if memory_context:
        context_blocks.append(f"Recent conversation context:\n{memory_context}")
    if kb_context:
        context_blocks.append(f"Local knowledge base context:\n{kb_context}")

    context_text = "\n\n".join(context_blocks) if context_blocks else "No extra local context available."

    return (
        "Use the local context below when relevant. If context is unrelated, answer normally. "
        "Do not invent facts from missing context.\n\n"
        f"{context_text}\n\n"
        f"User request:\n{routed_message}"
    )


def _rewrite_swahili_response(llm, user_message: str, draft_response: str) -> str:
    """Second-pass rewrite for fluent, natural Kiswahili."""
    try:
        rewrite_prompt = (
            "Andika upya jibu lifuatalo kwa Kiswahili fasaha, rahisi, na cha kawaida cha Tanzania.\n"
            "Masharti muhimu:\n"
            "1) Hifadhi maana ya jibu la awali, usiongeze mada mpya.\n"
            "2) Tumia sentensi fupi na wazi.\n"
            "3) Epuka maneno ya kutatanisha au tafsiri ya moja kwa moja isiyo ya kawaida.\n"
            "4) Toa hatua 3-5 tu kama ni maelekezo.\n"
            "5) Toa jibu la moja kwa moja bila kueleza sheria hizi.\n\n"
            f"Swali la mtumiaji: {user_message}\n\n"
            "Rasimu ya jibu:\n"
            f"{draft_response}"
        )

        rewritten = llm.chat(rewrite_prompt, use_context=False)
        if rewritten and rewritten.strip():
            return rewritten.strip()
    except Exception:
        pass

    return draft_response


def _prepare_multilingual_prompt(user_message: str) -> str:
    """Add lightweight language guidance for non-English prompts (especially Swahili)."""
    text = (user_message or "").strip()
    low = text.lower()

    sw_markers = [
        "nisaidie", "tafadhali", "naomba", "habari", "mambo", "vipi", "hujambo",
        "pesa", "kazi", "elimu", "nini", "nawezaje", "nisadie", "msaada",
    ]
    if any(m in low for m in sw_markers):
        return (
            "You are assisting a Swahili-speaking user.\n"
            "RULES:\n"
            "1) Respond in natural Kiswahili sanifu (simple, clear, practical).\n"
            "2) Do NOT mistranslate or invent meanings. If unclear, ask one short clarifying question in Swahili.\n"
            "3) Keep answers concise with actionable steps/bullets.\n"
            "4) For money/loan topics, include safety note: compare interest, terms, and repayment ability.\n\n"
            "OUTPUT FORMAT (strict):\n"
            "- Sentensi 1: Jibu la moja kwa moja.\n"
            "- Kisha hatua 3-5 za vitendo (bullets).\n"
            "- Malizia na tahadhari fupi ya kifedha.\n\n"
            "Few-shot style examples:\n"
            "User: nisaidie pesa\n"
            "Assistant: Sawa. Unahitaji msaada wa kuongeza kipato, kukopa, au kupanga bajeti? Chagua moja nikusaidie hatua kwa hatua.\n\n"
            "User: nawezaje kukopa pesa kwa AZA\n"
            "Assistant: Unaweza kuomba mkopo kwa AZA kwa kufuata masharti yao rasmi. Hatua za kawaida: 1) Fungua app/akaunti, 2) Hakiki vigezo vya mkopo, 3) Chagua kiasi na muda wa marejesho, 4) Thibitisha ombi. Kabla ya kukopa, linganisha riba na hakikisha unaweza kurejesha kwa wakati.\n\n"
            f"User message: {text}"
        )

    return text


def _is_swahili_like(text: str) -> bool:
    return _detect_user_language(text) == "sw"


def _detect_user_language(text: str) -> str:
    """Very lightweight language detection for EN/SW routing."""
    low = (text or "").strip().lower()
    if not low:
        return "unknown"

    sw_markers = {
        "nawezaje", "nisaidie", "tafadhali", "habari", "mambo", "vipi", "hujambo",
        "niaje", "asante", "msaada", "mkopo", "kukopa", "pesa", "bajeti", "uko", "poa", "sawa",
        "nini", "wapi", "lini", "kwa nini", "nani",
    }
    en_markers = {
        "how", "what", "why", "where", "when", "who", "are", "you", "help",
        "loan", "money", "budget", "good", "hello", "hi", "thanks",
    }

    tokens = set(re.findall(r"[a-zA-Z']+", low))
    sw_hits = len(tokens.intersection(sw_markers))
    en_hits = len(tokens.intersection(en_markers))

    if sw_hits > en_hits and sw_hits >= 1:
        return "sw"
    if en_hits > sw_hits and en_hits >= 1:
        return "en"

    # Phrase fallback for multiword markers
    if any(p in low for p in ["kwa nini", "nawezaje", "nisaidie", "habari yako"]):
        return "sw"
    if any(p in low for p in ["how are you", "are you good", "can you help"]):
        return "en"

    return "unknown"


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
