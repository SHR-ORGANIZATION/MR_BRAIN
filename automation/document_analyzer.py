"""
AMAZON AI - Document Analyzer
Analyzes documents and extracts key points, summaries, and insights.
Supports PDF, DOCX, TXT, and other text-based formats.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import Counter


class DocumentAnalyzer:
    """
    Analyzes documents and extracts:
    - Summary
    - Key points
    - Main topics
    - Important statistics
    - Action items
    """
    
    def __init__(self):
        self.supported_extensions = {
            '.txt', '.pdf', '.docx', '.doc', '.md', '.csv', '.json', '.xml', '.html'
        }
    
    def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a document and return summary, key points, and insights.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with analysis results
        """
        path = Path(file_path)
        
        if not path.exists():
            return {
                "status": "error",
                "message": f"File not found: {file_path}"
            }
        
        if path.suffix.lower() not in self.supported_extensions:
            return {
                "status": "error",
                "message": f"Unsupported file type: {path.suffix}. Supported: {', '.join(self.supported_extensions)}"
            }
        
        try:
            # Extract text based on file type
            text = self._extract_text(path)
            
            if not text or len(text.strip()) < 50:
                return {
                    "status": "error",
                    "message": "Document appears to be empty or too short to analyze."
                }
            
            # Analyze the text
            analysis = self._analyze_text(text, path.name)
            
            return {
                "status": "success",
                "file_name": path.name,
                "file_path": str(path),
                "file_size": self._format_size(path.stat().st_size),
                "word_count": len(text.split()),
                "character_count": len(text),
                "analysis": analysis
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error analyzing document: {str(e)}"
            }
    
    def _extract_text(self, path: Path) -> str:
        """Extract text from document based on file type."""
        ext = path.suffix.lower()
        
        if ext == '.txt' or ext == '.md' or ext == '.csv' or ext == '.json' or ext == '.xml':
            return self._read_text_file(path)
        elif ext == '.html':
            return self._read_html_file(path)
        elif ext == '.pdf':
            return self._read_pdf_file(path)
        elif ext in ['.docx', '.doc']:
            return self._read_docx_file(path)
        else:
            return self._read_text_file(path)
    
    def _read_text_file(self, path: Path) -> str:
        """Read plain text file."""
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def _read_html_file(self, path: Path) -> str:
        """Read HTML file and extract text content."""
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', content)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _read_pdf_file(self, path: Path) -> str:
        """Read PDF file and extract text."""
        try:
            import PyPDF2
            text = ""
            with open(path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() or ""
            return text
        except ImportError:
            # Fallback: try pdfplumber
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                return text
            except ImportError:
                return "PDF reading requires PyPDF2 or pdfplumber. Please install: pip install PyPDF2"
    
    def _read_docx_file(self, path: Path) -> str:
        """Read DOCX file and extract text."""
        try:
            from docx import Document
            doc = Document(str(path))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            return "DOCX reading requires python-docx. Please install: pip install python-docx"
    
    def _analyze_text(self, text: str, filename: str) -> Dict[str, Any]:
        """Analyze text and extract insights."""
        # Clean text
        clean_text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', clean_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
        
        # Extract key points (first sentence of each paragraph or important sentences)
        key_points = self._extract_key_points(sentences, paragraphs)
        
        # Generate summary
        summary = self._generate_summary(sentences, key_points)
        
        # Extract main topics (frequent words)
        topics = self._extract_topics(clean_text)
        
        # Extract numbers/statistics
        statistics = self._extract_statistics(clean_text)
        
        # Extract action items (sentences with action verbs)
        action_items = self._extract_action_items(sentences)
        
        return {
            "summary": summary,
            "key_points": key_points[:10],  # Top 10 key points
            "main_topics": topics[:5],  # Top 5 topics
            "statistics": statistics[:5],  # Top 5 statistics
            "action_items": action_items[:5],  # Top 5 action items
            "total_sentences": len(sentences),
            "total_paragraphs": len(paragraphs)
        }
    
    def _extract_key_points(self, sentences: List[str], paragraphs: List[str]) -> List[str]:
        """Extract key points from text."""
        key_points = []
        
        # Take first sentence of each paragraph (usually topic sentences)
        for para in paragraphs[:10]:  # First 10 paragraphs
            para_sentences = re.split(r'[.!?]+', para)
            if para_sentences:
                first_sentence = para_sentences[0].strip()
                if len(first_sentence) > 30 and first_sentence not in key_points:
                    key_points.append(first_sentence)
        
        # If not enough key points, add important sentences
        if len(key_points) < 5:
            for sentence in sentences:
                if len(sentence) > 50 and sentence not in key_points:
                    # Check if sentence contains important keywords
                    important_keywords = ['important', 'key', 'main', 'primary', 'essential', 
                                         'critical', 'significant', 'major', 'must', 'should',
                                         'need', 'require', 'ensure', 'note', 'remember']
                    if any(keyword in sentence.lower() for keyword in important_keywords):
                        key_points.append(sentence)
                        if len(key_points) >= 10:
                            break
        
        return key_points
    
    def _generate_summary(self, sentences: List[str], key_points: List[str]) -> str:
        """Generate a concise summary."""
        if not sentences:
            return "No content to summarize."
        
        # Use first few sentences and key points
        summary_parts = []
        
        # Add opening (first sentence if it's introductory)
        if sentences and len(sentences[0]) < 200:
            summary_parts.append(sentences[0])
        
        # Add key points
        for point in key_points[:3]:
            if point not in summary_parts:
                summary_parts.append(point)
        
        # Join and limit length
        summary = " ".join(summary_parts)
        if len(summary) > 500:
            summary = summary[:500] + "..."
        
        return summary if summary else "Document analyzed successfully."
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics from text using word frequency."""
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'this',
                     'that', 'these', 'those', 'it', 'its', 'he', 'she', 'they', 'we',
                     'you', 'I', 'me', 'him', 'her', 'them', 'us', 'my', 'your', 'his',
                     'their', 'our', 'not', 'no', 'so', 'if', 'then', 'than', 'too', 'very'}
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        words = [w for w in words if w not in stop_words]
        
        # Count frequency
        word_freq = Counter(words)
        
        # Return top topics
        return [word for word, count in word_freq.most_common(10)]
    
    def _extract_statistics(self, text: str) -> List[str]:
        """Extract numbers and statistics from text."""
        # Find numbers with context
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:percent|%)',  # Percentages
            r'(?:about|around|approximately|over|under|more than|less than)\s+(\d+(?:,\d+)*)',  # Approximate numbers
            r'(\d+(?:,\d+)*)\s*(?:users|people|customers|employees|members)',  # User counts
            r'\$\s*(\d+(?:,\d+)*(?:\.\d+)?)',  # Dollar amounts
            r'(\d+(?:\.\d+)?)\s*(?:million|billion|thousand)',  # Large numbers
        ]
        
        statistics = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:2]:  # Top 2 per pattern
                statistics.append(match)
        
        return statistics
    
    def _extract_action_items(self, sentences: List[str]) -> List[str]:
        """Extract action items (sentences with action verbs)."""
        action_verbs = ['must', 'should', 'need to', 'have to', 'required to', 'ensure',
                       'implement', 'create', 'build', 'develop', 'design', 'test',
                       'review', 'complete', 'finish', 'submit', 'deliver', 'provide']
        
        action_items = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(verb in sentence_lower for verb in action_verbs):
                if len(sentence) > 30 and len(sentence) < 300:
                    action_items.append(sentence.strip())
                    if len(action_items) >= 10:
                        break
        
        return action_items
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"


# Singleton instance
_analyzer_instance = None

def get_analyzer() -> DocumentAnalyzer:
    """Get or create the singleton analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = DocumentAnalyzer()
    return _analyzer_instance


def analyze_document(file_path: str) -> Dict[str, Any]:
    """Analyze a document and return results."""
    analyzer = get_analyzer()
    return analyzer.analyze(file_path)
