"""
AMAZON AI - Auto Typo Corrector
Automatically detects and corrects common typos in user commands.
"""
import re
from typing import Dict, List, Tuple, Optional


# Common typo mappings: typo -> correction
TYPO_CORRECTIONS = {
    # Document generation typos
    "invetatin": "invitation",
    "invetation": "invitation",
    "invtation": "invitation",
    "leter": "letter",
    "wrtie": "write",
    "wriet": "write",
    "genrate": "generate",
    "generat": "generate",
    "docuemnt": "document",
    "documet": "document",
    "reprot": "report",
    "repot": "report",
    "asignment": "assignment",
    "assignemnt": "assignment",
    "essy": "essay",
    "esay": "essay",
    "artical": "article",
    "aritcle": "article",
    
    # Common action typos
    "creat": "create",
    "delet": "delete",
    "opn": "open",
    "cls": "close",
    "serch": "search",
    "findi": "find",
    "fina": "find",
    "tafuta": "search",  # Swahili
    "tengeneza": "create",  # Swahili
    "futa": "delete",  # Swahili
    "nakili": "copy",  # Swahili
    "hamisha": "move",  # Swahili
    
    # File/folder typos
    "foler": "folder",
    "flder": "folder",
    "filder": "folder",
    "fiel": "file",
    "flie": "file",
    "fille": "file",
    
    # Application typos
    "chrom": "chrome",
    "chrme": "chrome",
    "vscode": "vs code",
    "vscod": "vs code",
    "notpad": "notepad",
    "notepd": "notepad",
    "calcualtor": "calculator",
    "calclator": "calculator",
    
    # Common word typos
    "teh": "the",
    "adn": "and",
    "fo": "for",
    "ot": "to",
    "in": "in",
    "is": "is",
    "ti": "it",
    "wiht": "with",
    "htis": "this",
    "thsi": "this",
    "taht": "that",
    "whcih": "which",
    "waht": "what",
    "hwat": "what",
    "whre": "where",
    "were": "where",
    "howa": "how",
    "whn": "when",
    "wehn": "when",
    
    # Email typos
    "emial": "email",
    "eamil": "email",
    "mail": "email",
    "gmail": "gmail",
    "outlok": "outlook",
    "outloook": "outlook",
    
    # System typos
    "comuter": "computer",
    "comupter": "computer",
    "pc": "computer",
    "lptop": "laptop",
    "laptp": "laptop",
    "systeem": "system",
    "sytem": "system",
    
    # Trash typos
    "tras": "trash",
    "trsh": "trash",
    "recylce": "recycle",
    "recylcle": "recycle",
    
    # Other common typos
    "pleas": "please",
    "plz": "please",
    "thx": "thanks",
    "thanx": "thanks",
    "ok": "okay",
    "k": "okay",
}


class TypoCorrector:
    """Automatically corrects common typos in user commands."""
    
    def __init__(self):
        self.corrections = TYPO_CORRECTIONS
        self.correction_log = []  # Track what was corrected
    
    def correct(self, command: str) -> Tuple[str, List[Dict]]:
        """
        Correct typos in a command.
        
        Args:
            command: The original command
            
        Returns:
            Tuple of (corrected_command, list_of_corrections_made)
        """
        if not command:
            return command, []
        
        corrections_made = []
        corrected = command
        
        # Sort by length (longer first) to avoid partial replacements
        sorted_typos = sorted(self.corrections.keys(), key=len, reverse=True)
        
        for typo in sorted_typos:
            correction = self.corrections[typo]
            
            # Use word boundary matching to avoid partial replacements
            pattern = r'\b' + re.escape(typo) + r'\b'
            
            if re.search(pattern, corrected, re.IGNORECASE):
                # Count occurrences
                matches = list(re.finditer(pattern, corrected, re.IGNORECASE))
                count = len(matches)
                
                if count > 0:
                    # Replace all occurrences
                    corrected = re.sub(pattern, correction, corrected, flags=re.IGNORECASE)
                    
                    corrections_made.append({
                        "typo": typo,
                        "correction": correction,
                        "count": count
                    })
        
        self.correction_log = corrections_made
        return corrected, corrections_made
    
    def has_typos(self, command: str) -> bool:
        """Check if command has any typos."""
        _, corrections = self.correct(command)
        return len(corrections) > 0
    
    def get_correction_summary(self) -> str:
        """Get a summary of corrections made."""
        if not self.correction_log:
            return ""
        
        parts = []
        for corr in self.correction_log:
            parts.append(f"'{corr['typo']}' → '{corr['correction']}'")
        
        return ", ".join(parts)


# Singleton instance
_corrector_instance = None

def get_corrector() -> TypoCorrector:
    """Get or create the singleton corrector instance."""
    global _corrector_instance
    if _corrector_instance is None:
        _corrector_instance = TypoCorrector()
    return _corrector_instance


def auto_correct(command: str) -> Tuple[str, List[Dict]]:
    """Auto-correct typos in a command."""
    corrector = get_corrector()
    return corrector.correct(command)
