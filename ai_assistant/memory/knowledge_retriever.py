"""
AMAZON AI - Knowledge Retriever
Retrieves relevant knowledge from the document index using semantic search.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Knowledge base storage
KB_DIR = Path(__file__).resolve().parent.parent.parent / "database" / "knowledge_base"
KB_INDEX_FILE = KB_DIR / "kb_index.json"
KB_VECTORS_FILE = KB_DIR / "kb_vectors.json"


@dataclass
class RetrievalResult:
    """Result from knowledge retrieval."""
    content: str
    source: str
    score: float
    metadata: Dict[str, Any]


class KnowledgeRetriever:
    """
    Retrieves relevant knowledge from ingested documents.
    
    Uses FAISS for fast similarity search over document embeddings.
    """
    
    def __init__(self):
        self._model = None
        self._index = None
        self._documents: List[Dict] = []
        self._loaded = False
    
    def _ensure_initialized(self):
        """Initialize the knowledge base if not already done."""
        if self._loaded:
            return
        
        KB_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing index
        if KB_INDEX_FILE.exists():
            try:
                with open(KB_INDEX_FILE, 'r', encoding='utf-8') as f:
                    self._documents = json.load(f)
                logger.info(f"Loaded {len(self._documents)} documents from knowledge base")
            except Exception as e:
                logger.warning(f"Error loading knowledge base: {e}")
        
        self._loaded = True
    
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
    
    def add_documents(self, chunks: List[Dict]):
        """
        Add document chunks to the knowledge base.
        
        Args:
            chunks: List of dicts with 'content', 'source', 'metadata'
        """
        self._ensure_initialized()
        
        # Add to documents list
        self._documents.extend(chunks)
        
        # Save index
        try:
            KB_DIR.mkdir(parents=True, exist_ok=True)
            with open(KB_INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._documents, f, indent=2)
            logger.info(f"Added {len(chunks)} chunks to knowledge base")
        except Exception as e:
            logger.error(f"Error saving knowledge base: {e}")
    
    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """
        Search the knowledge base for relevant documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of RetrievalResult objects
        """
        self._ensure_initialized()
        
        if not self._documents:
            return []
        
        try:
            import numpy as np
            
            # Get query embedding
            model = self._get_embedding_model()
            query_embedding = model.encode([query])[0]
            
            # Get document embeddings
            doc_texts = [doc.get("content", "") for doc in self._documents]
            doc_embeddings = model.encode(doc_texts)
            
            # Calculate cosine similarity
            similarities = np.dot(doc_embeddings, query_embedding) / (
                np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(query_embedding)
            )
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                doc = self._documents[idx]
                results.append(RetrievalResult(
                    content=doc.get("content", ""),
                    source=doc.get("source", "unknown"),
                    score=float(similarities[idx]),
                    metadata=doc.get("metadata", {})
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Knowledge search error: {e}")
            return []
    
    def get_context_for_query(self, query: str, max_chars: int = 2000) -> str:
        """
        Get relevant context for a query, formatted for LLM input.
        
        Args:
            query: User's query
            max_chars: Maximum characters of context
            
        Returns:
            Formatted context string
        """
        results = self.search(query, top_k=3)
        
        if not results:
            return ""
        
        context_parts = ["**Relevant Information:**\n"]
        total_chars = 0
        
        for i, result in enumerate(results, 1):
            if total_chars + len(result.content) > max_chars:
                break
            
            context_parts.append(f"\n--- Source {i}: {Path(result.source).name} ---")
            context_parts.append(result.content[:500])  # Limit per chunk
            total_chars += len(result.content)
        
        return "\n".join(context_parts)
    
    def clear(self):
        """Clear the knowledge base."""
        self._documents = []
        try:
            if KB_INDEX_FILE.exists():
                KB_INDEX_FILE.unlink()
            logger.info("Knowledge base cleared")
        except Exception as e:
            logger.error(f"Error clearing knowledge base: {e}")
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics."""
        self._ensure_initialized()
        
        sources = set(doc.get("source", "") for doc in self._documents)
        
        return {
            "total_chunks": len(self._documents),
            "total_sources": len(sources),
            "sources": list(sources)[:10]  # First 10 sources
        }


# Singleton instance
_retriever_instance = None

def get_knowledge_retriever() -> KnowledgeRetriever:
    """Get or create the singleton knowledge retriever."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = KnowledgeRetriever()
    return _retriever_instance
