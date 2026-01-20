"""Retriever for fetching relevant context."""

import logging
from typing import List, Dict, Any

from .vector_store import VectorStore
from .config import config

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieve relevant context for queries."""
    
    def __init__(self, vector_store: VectorStore = None):
        """Initialize the retriever.
        
        Args:
            vector_store: Vector store to search.
        """
        self.vector_store = vector_store or VectorStore()
    
    def retrieve(
        self,
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query.
        
        Args:
            query: The user's question.
            top_k: Number of results to return.
            
        Returns:
            List of relevant document chunks with metadata.
        """
        top_k = top_k or config.TOP_K
        
        results = self.vector_store.search(query, top_k=top_k)
        
        # Filter by minimum relevance score if needed
        filtered = [r for r in results if r.get("score", 0) > 0.3]
        
        logger.info(f"Retrieved {len(filtered)} relevant chunks for: {query[:50]}...")
        return filtered
    
    def get_context(self, query: str, max_tokens: int = 2000) -> str:
        """Get formatted context string for LLM.
        
        Args:
            query: The user's question.
            max_tokens: Maximum context length.
            
        Returns:
            Formatted context string with sources.
        """
        results = self.retrieve(query)
        
        if not results:
            return "No relevant information found in the knowledge base."
        
        context_parts = []
        sources = set()
        
        for i, result in enumerate(results, 1):
            content = result["content"]
            source = result["metadata"].get("source", "Unknown")
            title = result["metadata"].get("title", "Untitled")
            
            context_parts.append(f"[Source {i}: {title}]\n{content}")
            sources.add(source)
        
        context = "\n\n---\n\n".join(context_parts)
        
        return context
    
    def get_sources(self, query: str) -> List[str]:
        """Get source citations for a query.
        
        Args:
            query: The user's question.
            
        Returns:
            List of source URLs/names.
        """
        results = self.retrieve(query)
        sources = []
        
        for result in results:
            source = result["metadata"].get("source", "Unknown")
            if source not in sources:
                sources.append(source)
        
        return sources
