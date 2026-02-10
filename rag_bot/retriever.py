"""Retriever for fetching relevant context with priority data support."""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from groq import Groq
from .vector_store import VectorStore
from .config import config

logger = logging.getLogger(__name__)


class PriorityDataLoader:
    """Load and manage priority data for consistent responses."""
    
    def __init__(self, data_dir: Path = None):
        """Initialize the priority data loader."""        
        self.data_dir = data_dir or Path(config.DATA_DIR).parent
        self.priority_file = self.data_dir / "priority_data.json"
        self.priority_data = self._load_priority_data()
        
    def _load_priority_data(self) -> Dict:
        """Load priority data from JSON file."""
        if self.priority_file.exists():
            try:
                with open(self.priority_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded priority data from {self.priority_file}")
                    return data
            except Exception as e:
                logger.warning(f"Failed to load priority data: {e}")
        return {}
    
    def is_greeting(self, query: str) -> bool:
        """Check if query is a greeting."""
        query_lower = query.lower().strip()
        greetings = self.priority_data.get("keywords", {}).get("greetings", [])
        # Check if query starts with or is a greeting
        for greeting in greetings:
            if query_lower == greeting or query_lower.startswith(greeting + " "):
                return True
        return False
    
    def is_office_query(self, query: str) -> bool:
        """Check if query is about office locations."""
        query_lower = query.lower()
        keywords = self.priority_data.get("keywords", {}).get("offices", [])
        return any(kw in query_lower for kw in keywords)
    
    def is_contact_query(self, query: str) -> bool:
        """Check if query is about contact information."""
        query_lower = query.lower()
        keywords = self.priority_data.get("keywords", {}).get("contact", [])
        return any(kw in query_lower for kw in keywords)
    
    def get_offices_context(self) -> str:
        """Get formatted office locations context."""
        offices = self.priority_data.get("offices", {})
        if not offices:
            return ""
        
        context_parts = ["## ODPC Office Locations\n"]
        
        # Head office
        head = offices.get("head_office", {})
        if head:
            context_parts.append(f"**1. {head.get('name', 'Head Office')}**")
            context_parts.append(f"   Address: {head.get('address', '')}")
            context_parts.append(f"   Email: {head.get('email', '')}\n")
        
        # Regional offices
        for i, office in enumerate(offices.get("regional_offices", []), 2):
            context_parts.append(f"**{i}. {office.get('name', '')}**")
            context_parts.append(f"   Address: {office.get('address', '')}")
            context_parts.append(f"   Email: {office.get('email', '')}\n")
        
        return "\n".join(context_parts)
    
    def get_contact_context(self) -> str:
        """Get formatted contact information context."""
        contact = self.priority_data.get("contact", {})
        if not contact:
            return ""
        
        phones = ", ".join(contact.get("phone", []))
        return f"""## ODPC Contact Information
- Phone: {phones}
- Email: {contact.get('email', '')}
- Website: {contact.get('website', '')}
- Office Hours: {contact.get('office_hours', '')}
- Training inquiries: {contact.get('training_email', '')}
- Complaints: {contact.get('complaints_email', '')}
- Registration: {contact.get('registration_email', '')}
"""
    
    def get_priority_context(self, query: str) -> Tuple[str, bool]:
        """
        Get priority context for query if applicable.
        
        Returns:
            Tuple of (context_string, skip_sources_flag)
            skip_sources_flag is True for greetings/office queries where we don't want to show sources
        """
        if self.is_greeting(query):
            return "", True  # No extra context needed for greetings, skip sources
        
        context_parts = []
        skip_sources = False
        
        if self.is_office_query(query):
            context_parts.append(self.get_offices_context())
            context_parts.append(self.get_contact_context())
            skip_sources = True  # Don't show sources for office location queries
        elif self.is_contact_query(query):
            context_parts.append(self.get_contact_context())
            skip_sources = True  # Don't show sources for contact queries
        
        return "\n".join(context_parts), skip_sources



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
        self.priority_loader = PriorityDataLoader()

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

        # Optionally transform query
        # opt_query = self._transform_query(query)
        
        results = self.vector_store.search(query, top_k=top_k)
        
        # Filter by minimum relevance score
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
        context, _ = self.get_context_with_sources(query, max_tokens)
        return context
    
    def get_context_with_sources(self, query: str, max_tokens: int = 2000) -> Tuple[str, bool]:
        """Get formatted context string for LLM with source control.
        
        Args:
            query: The user's question.
            max_tokens: Maximum context length.
            
        Returns:
            Tuple of (formatted context string, skip_sources flag)
        """
        # Check for priority data first
        priority_context, skip_sources = self.priority_loader.get_priority_context(query)
        
        # For greetings, return early with no context
        if self.priority_loader.is_greeting(query):
            return "", True
        
        results = self.retrieve(query)
        
        context_parts = []
        
        # Add priority data at the beginning if available
        if priority_context:
            context_parts.append(f"[PRIORITY DATA - USE THIS FOR OFFICE/CONTACT QUERIES]\n{priority_context}")
        
        if results:
            for i, result in enumerate(results, 1):
                content = result["content"]
                source = result["metadata"].get("source", "Unknown")
                title = result["metadata"].get("title", "Untitled")
                
                context_parts.append(
                    f"[Source {i}: {title} | {source}]\n{content}"
                )
        
        context = "\n\n---\n\n".join(context_parts) if context_parts else ""
        
        return context, skip_sources
    
    def get_sources(self, query: str) -> List[str]:
        """Get source citations for a query.
        
        Args:
            query: The user's question.
            
        Returns:
            List of source URLs only. Empty list for greetings/office/contact queries.
        """
        # Check if we should skip sources for this query type
        _, skip_sources = self.priority_loader.get_priority_context(query)
        if skip_sources:
            return []  # Return empty sources for greetings, office, and contact queries
        
        results = self.retrieve(query)
        sources = []
        
        for result in results:
            source = result["metadata"].get("source", "")
            # Only include URLs, not document filenames
            if source.startswith("http") and source not in sources:
                sources.append(source)
        
        return sources