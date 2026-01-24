"""Chat interface with controlled RAG workflow and database history support."""

import logging
from typing import List, Dict, Any
from groq import Groq

from .config import config
from .retriever import Retriever
from .prompts import SYSTEM_PROMPT, format_qa_prompt

logger = logging.getLogger(__name__)


class ChatBot:
    """RAG-powered chatbot for ODPC queries using Groq."""
    
    def __init__(self):
        """Initialize the chatbot."""
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.retriever = Retriever()
        self.conversation_history: List[Dict[str, str]] = []
        self.model = config.LLM_MODEL
    
    def load_history_from_db(self, db_messages):
        """Load conversation history from database messages into memory.
        
        Args:
            db_messages: List of ChatMessage objects from database
        """
        # Clear existing history first
        self.conversation_history = []
        
        # Convert database messages to chat format
        for msg in db_messages:
            if msg.role == "user" and msg.user_message:
                self.conversation_history.append({
                    "role": "user",
                    "content": msg.user_message
                })
            elif msg.role == "assistant" and msg.response:
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": msg.response
                })
        
        logger.info(f"Loaded {len(self.conversation_history)} messages into memory")
        
    def chat(self, user_message: str) -> Dict[str, any]:
        """Process a user message and generate a response.
        
        Args:
            user_message: The user's question or message.
            
        Returns:
            Dict with response, sources, and metadata.
        """
        # CRITICAL FIX: Build context-aware query for RAG retrieval
        # If user asks follow-up questions like "explain that", include recent context
        rag_query = user_message
        if len(self.conversation_history) >= 2:
            # Get last Q&A pair for context
            last_user = self.conversation_history[-2].get("content", "") if len(self.conversation_history) >= 2 else ""
            last_assistant = self.conversation_history[-1].get("content", "") if len(self.conversation_history) >= 1 else ""
            
            # For short follow-up questions, include context
            if len(user_message.split()) < 10:  # Short question likely a follow-up
                rag_query = f"Previous question: {last_user[:150]} Current question: {user_message}"
                logger.info(f"Enhanced RAG query with context for follow-up question")
        
        # Step 1: Retrieve relevant context from vector store using enhanced query
        context = self.retriever.get_context(rag_query)
        sources = self.retriever.get_sources(rag_query)
        
        # Step 2: Format the prompt with context
        qa_prompt = format_qa_prompt(context, user_message)
        
        # Step 3: Build messages for API call
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        
        # Add conversation history (last 4 exchanges = 8 messages)
        for msg in self.conversation_history[-8:]:
            messages.append(msg)
        
        # Add current question with RAG context
        messages.append({"role": "user", "content": qa_prompt})
        
        try:
            # Step 4: Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS
            )
            
            assistant_message = response.choices[0].message.content
            
            # Step 5: Update conversation history with plain messages
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            return {
                "response": assistant_message,
                "sources": sources,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            return {
                "response": f"I encountered an error processing your request: {str(e)}",
                "sources": [],
                "error": str(e)
            }
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self.conversation_history.copy()