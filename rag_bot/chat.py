"""Chat interface with controlled RAG workflow and database history support."""

import logging
from typing import List, Dict, Any
from groq import Groq

from .config import config
from .retriever import Retriever
from .prompts import SYSTEM_PROMPT, format_qa_prompt
from .intelligence import IntelligenceEngine

logger = logging.getLogger(__name__)


class ChatBot:
    """RAG-powered chatbot for ODPC queries using Groq."""
    
    def __init__(self):
        """Initialize the chatbot."""
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.retriever = Retriever()
        self.conversation_history: List[Dict[str, str]] = []
        self.model = config.LLM_MODEL
        self.intelligence = IntelligenceEngine()
    
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
        # Step 1: Process through intelligence engine
        intel = self.intelligence.process_query(user_message)
        follow_ups = intel.get("follow_ups", [])
        
        # Step 2: Handle proactive guidance for unclear queries
        if intel.get("needs_guidance"):
            guidance_response = intel.get("guidance_text", "How can I help you?")
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": guidance_response})
            return {
                "response": guidance_response,
                "sources": [],
                "tokens_used": 0,
                "intent": intel.get("intent"),
                "from_cache": False
            }
        
        # Step 3: Check FAQ cache for instant answer
        faq_match = intel.get("faq_match")
        if faq_match:
            cached_answer = faq_match.get("answer", "")
            # Add follow-up suggestions
            if follow_ups:
                cached_answer += self.intelligence.format_follow_ups(follow_ups)
            
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": cached_answer})
            
            logger.info(f"Using cached FAQ answer: {faq_match.get('id')}")
            return {
                "response": cached_answer,
                "sources": [],
                "tokens_used": 0,
                "intent": intel.get("intent"),
                "from_cache": True
            }
        
        # Step 4: Check for greetings
        is_greeting = self.retriever.priority_loader.is_greeting(user_message)
        
        if is_greeting:
            rag_query = user_message
            context = ""
            sources = []
            logger.info("Detected greeting - skipping RAG retrieval")
        else:
            # Build context-aware query for RAG retrieval
            rag_query = user_message
            if len(self.conversation_history) >= 2:
                last_user = self.conversation_history[-2].get("content", "") if len(self.conversation_history) >= 2 else ""
                
                if len(user_message.split()) < 10:
                    rag_query = f"Previous question: {last_user[:150]} Current question: {user_message}"
                    logger.info("Enhanced RAG query with context for follow-up question")
            
            context = self.retriever.get_context(rag_query)
            sources = self.retriever.get_sources(user_message)
        
        # Step 5: Format the prompt with context
        qa_prompt = format_qa_prompt(context, user_message)
        
        # Step 6: Build messages for API call
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        
        for msg in self.conversation_history[-8:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": qa_prompt})
        
        try:
            # Step 7: Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS
            )
            
            assistant_message = response.choices[0].message.content
            
            # Step 8: Append follow-up suggestions if available
            if follow_ups and not is_greeting:
                assistant_message += self.intelligence.format_follow_ups(follow_ups)
            
            # Step 9: Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            return {
                "response": assistant_message,
                "sources": sources,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "intent": intel.get("intent"),
                "from_cache": False
            }
            
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            return {
                "response": f"I encountered an error processing your request: {str(e)}",
                "sources": [],
                "error": str(e)
            }
    
    def clear_history(self) -> None:
        """Clear conversation history and reset intelligence engine."""
        self.conversation_history = []
        self.intelligence.reset_conversation()
        logger.info("Conversation history cleared")
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self.conversation_history.copy()