"""
AMAZON AI - Document Ingestion
Reads documents, extracts text, creates embeddings for RAG.
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of a document with metadata."""
    content: str
    source: str
    chunk_id: int
    metadata: Dict[str, Any]


class DocumentIngester:
    """
    Ingests documents for the knowledge base.
    
    Supported formats:
    - PDF files
    - Word documents (DOCX)
    - Text files (TXT, MD)
    - Code files (PY, JS, etc.)
    """
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".doc", ".txt", ".md",
        ".py", ".js", ".html", ".css", ".json", ".csv"
    }
    
    # Chunk settings
    CHUNK_SIZE = 500  # characters
    CHUNK_OVERLAP = 50  # characters
    
    def __init__(self):
        self._model = None  # Lazy-loaded sentence transformer
    
    def _get_embedding_model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return self._model
    
    def ingest_file(self, file_path: str) -> List[DocumentChunk]:
        """
        Ingest a single file into document chunks.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of DocumentChunk objects
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return []
        
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.warning(f"Unsupported file type: {path.suffix}")
            return []
        
        # Extract text based on file type
        text = self._extract_text(path)
        if not text:
            logger.warning(f"No text extracted from: {file_path}")
            return []
        
        # Split into chunks
        chunks = self._split_into_chunks(text, str(path))
        
        logger.info(f"Ingested {len(chunks)} chunks from {path.name}")
        return chunks
    
    def ingest_directory(self, dir_path: str, recursive: bool = True) -> List[DocumentChunk]:
        """
        Ingest all supported files in a directory.
        
        Args:
            dir_path: Path to the directory
            recursive: Whether to search subdirectories
            
        Returns:
            List of DocumentChunk objects
        """
        path = Path(dir_path)
        if not path.is_dir():
            logger.error(f"Not a directory: {dir_path}")
            return []
        
        all_chunks = []
        pattern = "**/*" if recursive else "*"
        
        for file_path in path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                chunks = self.ingest_file(str(file_path))
                all_chunks.extend(chunks)
        
        logger.info(f"Ingested {len(all_chunks)} total chunks from {dir_path}")
        return all_chunks
    
    def _extract_text(self, file_path: Path) -> Optional[str]:
        """Extract text from a file based on its type."""
        ext = file_path.suffix.lower()
        
        try:
            if ext == ".pdf":
                return self._extract_pdf(file_path)
            elif ext in [".docx", ".doc"]:
                return self._extract_docx(file_path)
            elif ext in [".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".csv"]:
                return self._extract_text_file(file_path)
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
        
        return None
    
    def _extract_pdf(self, file_path: Path) -> Optional[str]:
        """Extract text from PDF."""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(file_path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return None
    
    def _extract_docx(self, file_path: Path) -> Optional[str]:
        """Extract text from DOCX."""
        try:
            from docx import Document
            doc = Document(str(file_path))
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return None
    
    def _extract_text_file(self, file_path: Path) -> Optional[str]:
        """Extract text from plain text files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Text file extraction error: {e}")
            return None
    
    def _split_into_chunks(self, text: str, source: str) -> List[DocumentChunk]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk_text = text[start:end]
            
            chunks.append(DocumentChunk(
                content=chunk_text.strip(),
                source=source,
                chunk_id=chunk_id,
                metadata={
                    "start_char": start,
                    "end_char": end,
                    "char_count": len(chunk_text)
                }
            ))
            
            start = end - self.CHUNK_OVERLAP
            chunk_id += 1
        
        return chunks
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        model = self._get_embedding_model()
        embeddings = model.encode(texts)
        return embeddings.tolist()


# Singleton instance
_ingester_instance = None

def get_document_ingester() -> DocumentIngester:
    """Get or create the singleton document ingester."""
    global _ingester_instance
    if _ingester_instance is None:
        _ingester_instance = DocumentIngester()
    return _ingester_instance
