"""Helper functions for database operations."""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from .database import ChatMessage

logger = logging.getLogger(__name__)


def add_message_to_history(
    db: Session,
    session_id: str,
    role: str,
    user_message: Optional[str] = None,
    system_message: Optional[str] = None,
    response: Optional[str] = None,
    sources: Optional[List[str]] = None,
    tokens_used: Optional[int] = None
) -> str:
    """Add a message to the database chat history
    
    Args:
        db: Database session
        session_id: Session ID (UUID string)
        role: Message role ('user' or 'assistant')
        user_message: User's message content
        system_message: System message content
        response: Assistant's response
        sources: List of source citations
        tokens_used: Number of tokens used
        
    Returns:
        str: Message ID
    """
    try:
        message_id = uuid.uuid4()
        timestamp = datetime.now(timezone.utc)
        
        # Convert session_id to UUID if it's a valid UUID string
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            # If not a valid UUID, generate one
            session_uuid = uuid.uuid4()
            logger.info(f"Generated new UUID {session_uuid} for session {session_id}")
        
        # Convert sources list to JSON string
        sources_json = json.dumps(sources) if sources else None
        
        db_message = ChatMessage(
            message_id=message_id,
            session_id=session_uuid,
            role=role,
            user_message=user_message,
            system_message=system_message,
            response=response,
            sources=sources_json,
            tokens_used=tokens_used,
            timestamp=timestamp
        )
        
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        
        logger.info(f"Added {role} message to session {session_id}")
        return str(message_id)
        
    except Exception as e:
        logger.error(f"Error adding message to history: {e}")
        db.rollback()
        raise


def get_session_history(
    db: Session,
    session_id: str,
    limit: Optional[int] = None
) -> Optional[List[ChatMessage]]:
    """Retrieve chat history for a given session from database
    
    Args:
        db: Database session
        session_id: Session ID (UUID string)
        limit: Optional limit on number of messages to retrieve
        
    Returns:
        List of ChatMessage objects or None
    """
    try:
        session_uuid = uuid.UUID(session_id)
        query = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_uuid
        ).order_by(ChatMessage.timestamp)
        
        if limit:
            query = query.limit(limit)
            
        messages = query.all()
        return messages
        
    except Exception as e:
        logger.error(f"Error retrieving session history: {e}")
        return None


def get_session_stats(db: Session, session_id: str) -> Dict[str, Any]:
    """Get statistics for a session from database
    
    Args:
        db: Database session
        session_id: Session ID (UUID string)
        
    Returns:
        Dictionary with session statistics
    """
    try:
        session_uuid = uuid.UUID(session_id)
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_uuid
        ).order_by(ChatMessage.timestamp).all()
        
        if not messages:
            return {}
        
        # Calculate total tokens used
        total_tokens = sum(msg.tokens_used or 0 for msg in messages)
        
        return {
            "total_messages": len(messages),
            "created_at": messages[0].timestamp,
            "last_updated": messages[-1].timestamp,
            "total_tokens_used": total_tokens
        }
        
    except Exception as e:
        logger.error(f"Error getting session stats: {e}")
        return {}


def delete_session_history(db: Session, session_id: str) -> int:
    """Delete all messages for a session
    
    Args:
        db: Database session
        session_id: Session ID (UUID string)
        
    Returns:
        Number of messages deleted
    """
    try:
        session_uuid = uuid.UUID(session_id)
        deleted_count = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_uuid
        ).delete()
        
        db.commit()
        logger.info(f"Deleted {deleted_count} messages for session {session_id}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error deleting session history: {e}")
        db.rollback()
        raise


def get_all_sessions(db: Session) -> List[Dict[str, Any]]:
    """Get list of all active sessions with basic stats
    
    Args:
        db: Database session
        
    Returns:
        List of session dictionaries with stats
    """
    try:
        # Get unique session IDs
        session_ids = db.query(ChatMessage.session_id).distinct().all()
        
        sessions = []
        for (session_id,) in session_ids:
            session_id_str = str(session_id)
            stats = get_session_stats(db, session_id_str)
            sessions.append({
                "session_id": session_id_str,
                **stats
            })
        
        logger.info(f"Retrieved {len(sessions)} active sessions")
        return sessions
        
    except Exception as e:
        logger.error(f"Error retrieving all sessions: {e}")
        return []


def format_session_history_for_context(
    db: Session,
    session_id: str,
    max_messages: int = 10
) -> str:
    """Format recent session history as context for the chatbot
    
    Args:
        db: Database session
        session_id: Session ID (UUID string)
        max_messages: Maximum number of recent messages to include
        
    Returns:
        Formatted conversation context string
    """
    try:
        messages = get_session_history(db, session_id, limit=max_messages)
        
        if not messages:
            return ""
        
        context_parts = []
        for msg in messages:
            if msg.role == "user" and msg.user_message:
                context_parts.append(f"User: {msg.user_message}")
            elif msg.role == "assistant" and msg.response:
                context_parts.append(f"Assistant: {msg.response}")
        
        return "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"Error formatting session history: {e}")
        return ""