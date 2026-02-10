"""Intelligence module for smart chatbot features."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from .config import config

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classify user intent from queries."""
    
    INTENTS = {
        "complaint": ["complaint", "complain", "report", "violation", "my data was", "misuse", "abuse", "harass"],
        "registration": ["register", "registration", "sign up", "apply", "certificate", "renew", "data controller", "data processor"],
        "rights": ["my rights", "right to", "access my data", "delete my data", "correct my data", "data subject", "erasure", "portability"],
        "breach": ["breach", "leak", "hack", "stolen", "exposed", "compromised", "incident", "unauthorized access"],
        "info": ["what is", "who is", "explain", "tell me about", "define", "meaning", "how does"]
    }
    
    @classmethod
    def classify(cls, query: str) -> str:
        """Classify query intent. Returns intent name or 'info' as default."""
        query_lower = query.lower()
        
        # Check each intent's keywords
        for intent, keywords in cls.INTENTS.items():
            if intent == "info":  # Skip info, it's the default
                continue
            for keyword in keywords:
                if keyword in query_lower:
                    logger.info(f"Classified intent: {intent} (matched: {keyword})")
                    return intent
        
        return "info"


class FAQMatcher:
    """Match queries to cached FAQ answers."""
    
    def __init__(self, cache_path: Path = None):
        self.cache_path = cache_path or Path(config.DATA_DIR).parent / "faq_cache.json"
        self.faqs = self._load_cache()
    
    def _load_cache(self) -> List[Dict]:
        """Load FAQ cache from JSON file."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data.get('faqs', []))} FAQs from cache")
                    return data.get("faqs", [])
            except Exception as e:
                logger.warning(f"Failed to load FAQ cache: {e}")
        return []
    
    def match(self, query: str) -> Optional[Dict]:
        """Find matching FAQ for query. Returns FAQ dict or None."""
        query_lower = query.lower().strip()
        
        for faq in self.faqs:
            for keyword in faq.get("keywords", []):
                if keyword in query_lower or query_lower in keyword:
                    logger.info(f"FAQ match found: {faq['id']}")
                    return faq
        
        return None
    
    def get_follow_ups(self, faq_id: str) -> List[str]:
        """Get follow-up questions for a FAQ."""
        for faq in self.faqs:
            if faq.get("id") == faq_id:
                return faq.get("follow_ups", [])
        return []


class ConversationTracker:
    """Track conversation topics to avoid repetition."""
    
    def __init__(self):
        self.topics_covered: Set[str] = set()
        self.info_provided: Dict[str, bool] = {
            "offices": False,
            "contact": False,
            "registration_fees": False,
            "complaint_process": False
        }
    
    def mark_topic(self, topic: str) -> None:
        """Mark a topic as covered."""
        self.topics_covered.add(topic)
        if topic in self.info_provided:
            self.info_provided[topic] = True
        logger.info(f"Marked topic as covered: {topic}")
    
    def is_covered(self, topic: str) -> bool:
        """Check if topic was already covered."""
        return topic in self.topics_covered
    
    def get_summary(self) -> str:
        """Get summary of topics covered."""
        if not self.topics_covered:
            return ""
        return f"Topics already discussed: {', '.join(self.topics_covered)}"
    
    def should_include_offices(self) -> bool:
        """Check if we should include office info (not already provided)."""
        return not self.info_provided.get("offices", False)
    
    def should_include_contact(self) -> bool:
        """Check if we should include contact info (not already provided)."""
        return not self.info_provided.get("contact", False)
    
    def reset(self) -> None:
        """Reset tracker for new conversation."""
        self.topics_covered.clear()
        for key in self.info_provided:
            self.info_provided[key] = False


class GuidanceGenerator:
    """Generate proactive guidance for unclear queries."""
    
    GUIDANCE_MENU = """I can help you with:
1. File a complaint about data misuse
2. Register as a data controller/processor
3. Understand your data rights
4. Report a data breach
5. Learn about data protection in Kenya

What would you like help with?"""
    
    @classmethod
    def needs_guidance(cls, query: str, intent: str) -> bool:
        """Check if query is unclear and needs guidance."""
        query_clean = query.strip()
        
        # Very short queries (less than 3 words, not a greeting)
        if len(query_clean.split()) < 3:
            greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
            if query_clean.lower() not in greetings:
                return True
        
        # Single word queries
        if len(query_clean.split()) == 1:
            return True
        
        # Queries that are just punctuation or very vague
        if query_clean in ["?", "help", "help me", "i need help", "assist"]:
            return True
        
        return False
    
    @classmethod
    def get_guidance(cls) -> str:
        """Get the guidance menu."""
        return cls.GUIDANCE_MENU


class IntelligenceEngine:
    """Main intelligence engine combining all features."""
    
    def __init__(self):
        self.faq_matcher = FAQMatcher()
        self.conversation_tracker = ConversationTracker()
    
    def process_query(self, query: str) -> Dict:
        """
        Process a query through all intelligence features.
        
        Returns dict with:
        - intent: classified intent
        - faq_match: matching FAQ if found
        - needs_guidance: whether to show help menu
        - follow_ups: suggested follow-up questions
        - skip_rag: whether to skip RAG retrieval
        """
        result = {
            "intent": "info",
            "faq_match": None,
            "needs_guidance": False,
            "follow_ups": [],
            "skip_rag": False,
            "guidance_text": ""
        }
        
        # 1. Classify intent
        result["intent"] = IntentClassifier.classify(query)
        
        # 2. Check if guidance is needed (unclear query)
        if GuidanceGenerator.needs_guidance(query, result["intent"]):
            result["needs_guidance"] = True
            result["guidance_text"] = GuidanceGenerator.get_guidance()
            result["skip_rag"] = True
            return result
        
        # 3. Check FAQ cache
        faq_match = self.faq_matcher.match(query)
        if faq_match:
            result["faq_match"] = faq_match
            result["follow_ups"] = faq_match.get("follow_ups", [])
            result["skip_rag"] = True  # Use cached answer instead of RAG
            
            # Track topic
            self.conversation_tracker.mark_topic(faq_match.get("id", "unknown"))
        
        return result
    
    def format_follow_ups(self, follow_ups: List[str]) -> str:
        """Format follow-up questions for display."""
        if not follow_ups:
            return ""
        
        lines = ["\n---", "**Related questions:**"]
        for q in follow_ups[:3]:  # Max 3 follow-ups
            lines.append(f"• {q}")
        
        return "\n".join(lines)
    
    def reset_conversation(self) -> None:
        """Reset conversation state."""
        self.conversation_tracker.reset()
