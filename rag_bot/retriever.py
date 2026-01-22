"""Retriever for fetching relevant context."""

import logging
from typing import List, Dict, Any
import torch
from groq import Groq
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
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = "llama-3.1-8b-instant"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def _transform_query(self, original_query: str) -> str:
        """
        Takes the user's raw Swahili/Sheng query and converts it into 
        a precise English Legal Search Query.
        """
        system_instruction = (
            "You rewrite user questions into concise English search queries. "
            "Preserve the original meaning exactly. "
            "Do NOT add new legal concepts. "
            "Do NOT guess intent. "
            "Do NOT expand abbreviations unless explicitly stated. "
            "If unsure, translate literally. "
            "Output ONE short English search query only. No explanation."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": original_query}
                ],
                temperature=0,
                top_p=1.0,
                max_tokens=50
            )
            transformed_query = response.choices[0].message.content.strip()
            logger.info(f"Query Transform: '{original_query}' -> '{transformed_query}'")
            return transformed_query
        except Exception as e:
            logger.warning(f"Query transformation failed: {e}")
            return original_query
    
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

        opt_query = self._transform_query(query)
        
        results = self.vector_store.search(opt_query, top_k=top_k)
        
        # Filter by minimum relevance score if needed
        filtered = [r for r in results if r.get("score", 0) > 0.25]
        
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
            return ""
        
        context_parts = []
        sources = set()
        
        for i, result in enumerate(results, 1):
            content = result["content"]
            source = result["metadata"].get("source", "Unknown")
            title = result["metadata"].get("title", "Untitled")
            
            context_parts.append(
                f"[Source {i}: {title} | {source}]\n{content}"
            )
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