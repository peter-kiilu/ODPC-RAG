import logging
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from .chat import ChatBot
from .vector_store import VectorStore
from .config import config
from .database import init_db, get_db, test_connection, ChatMessage
from .db_helpers import (
    add_message_to_history,
    get_session_history,
    get_session_stats,
    delete_session_history,
    get_all_sessions,
    format_session_history_for_context
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="ODPC Kenya Bot",
    version="1.0.0",
    description="AI Assistant for Office of the Data Protection Commissioner Kenya"
)

origins = [
    "https://3000-w-rickmwasofficial-mkpfbulw.cluster-s5xdz26smvgniwoeurkaozovss.cloudworkstations.dev",
]

# 2. Add the middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and test connection on startup"""
    logger.info("Starting ODPC Kenya API....")

    try:
        # initialize the db
        init_db()

        # Test database connection
        if test_connection():
            logger.info("Database connection successful")
        else:
            logger.error("Database connection failed!")
            
    except Exception as e:
        logger.error(f"Startup error: {e}")

# Initialize the Bot globally so it doesn't reload on every message
# This keeps the vector store and memory in place
bot = ChatBot()

# Data Models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What are my data protection rights in Kenya?",
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    tokens_used: int
    session_id: str
    message_id: str
    timestamp: str

class ChatHistoryMessage(BaseModel):
    message_id: str
    role: str
    user_message: Optional[str] = None
    response: Optional[str] = None
    sources: Optional[List[str]] = None
    tokens_used: Optional[int] = None
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatHistoryMessage]
    total_messages: int
    total_tokens_used: int
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None


class SessionInfo(BaseModel):
    session_id: str
    total_messages: int
    total_tokens_used: int
    created_at: datetime
    last_updated: datetime


# Endpoints
@app.get('/health')
def health_check(db: Session = Depends(get_db)):
    """Check if the API and Vector Store are ready"""
    try:
        vs = VectorStore()
        
        # Test database connection
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "indexed_chunks": vs.count,
            "config_valid": config.validate(),
            "database_connected": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """Receive a message and return the response"""
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        # Generate or use provided session ID
        if not request.session_id:
            request.session_id = str(uuid.uuid4())
            logger.info(f"Generated new session ID: {request.session_id}")

        # Load database history into bot's memory for this session
        past_messages = get_session_history(db, request.session_id, limit=10)
        if past_messages:
            # Load the database history into the bot
            bot.load_history_from_db(past_messages)
            logger.info(f"Loaded {len(past_messages)} past messages for session {request.session_id}")
        
        # Save user message to database
        user_message_id = add_message_to_history(
            db=db,
            session_id=request.session_id,
            role="user",
            user_message=request.message
        )

        # Get bot response (will use loaded history as context)
        result = bot.chat(request.message)

        # Save assistant response to database
        assistant_message_id = add_message_to_history(
            db=db,
            session_id=request.session_id,
            role="assistant",
            response=result["response"],
            sources=result["sources"],
            tokens_used=result["tokens_used"]
        )

        logger.info(f"Successfully processed message for session {request.session_id}")
        
        return ChatResponse(
            response=result["response"],
            sources=result["sources"],
            tokens_used=result["tokens_used"],
            session_id=request.session_id,
            message_id=assistant_message_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")  

@app.post("/clear")
async def clear_chat(db: Session = Depends(get_db)):
    """Clear conversation history for the bot (in-memory only)"""
    try:
        bot.clear_history()
        return {
            "status": "success",
            "message": "In-memory conversation history cleared (database history preserved)"
        }
    except Exception as e:
        logger.error(f"Error clearing chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    """Retrieve chat history for a specific session ID from database"""
    try:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid session_id format. Must be a valid UUID."
            )
        
        logger.info(f"Chat history requested for session: {session_id}")
        
        # Get session history from database
        session_messages = get_session_history(db, session_id)
        
        if not session_messages:
            raise HTTPException(
                status_code=404,
                detail=f"No chat history found for session ID: {session_id}"
            )
        
        # Get session statistics
        stats = get_session_stats(db, session_id)
        
        # Convert to response format
        messages = []
        for msg in session_messages:
            # Parse sources from JSON string
            sources_list = None
            if msg.sources:
                try:
                    sources_list = json.loads(msg.sources)
                except:
                    sources_list = None
            
            messages.append(ChatHistoryMessage(
                message_id=str(msg.message_id),
                role=msg.role,
                user_message=msg.user_message,
                response=msg.response,
                sources=sources_list,
                tokens_used=msg.tokens_used,
                timestamp=msg.timestamp
            ))
        
        response = ChatHistoryResponse(
            session_id=session_id,
            messages=messages,
            total_messages=stats.get("total_messages", len(messages)),
            total_tokens_used=stats.get("total_tokens_used", 0),
            created_at=stats.get("created_at"),
            last_updated=stats.get("last_updated")
        )
        
        logger.info(f"Returning {len(messages)} messages for session: {session_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chat history for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving chat history: {str(e)}"
        )


@app.get("/chat/sessions", response_model=List[SessionInfo])
async def get_all_sessions_endpoint(db: Session = Depends(get_db)):
    """Get list of all active sessions with basic stats from database"""
    try:
        sessions = get_all_sessions(db)
        
        # Convert to response format
        session_infos = []
        for session in sessions:
            if session.get("total_messages", 0) > 0:  # Only include sessions with messages
                session_infos.append(SessionInfo(
                    session_id=session["session_id"],
                    total_messages=session.get("total_messages", 0),
                    total_tokens_used=session.get("total_tokens_used", 0),
                    created_at=session.get("created_at"),
                    last_updated=session.get("last_updated")
                ))
        
        logger.info(f"Returning {len(session_infos)} active sessions")
        return session_infos
        
    except Exception as e:
        logger.error(f"Error retrieving sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving sessions: {str(e)}"
        )


@app.delete("/chat/history/{session_id}")
async def delete_chat_history_endpoint(session_id: str, db: Session = Depends(get_db)):
    """Delete chat history for a specific session ID from database"""
    try:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid session_id format. Must be a valid UUID."
            )
        
        # Delete session history
        deleted_count = delete_session_history(db, session_id)
        
        if deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No chat history found for session ID: {session_id}"
            )
        
        logger.info(f"Deleted chat history for session: {session_id}")
        return {
            "message": f"Successfully deleted chat history for session {session_id}",
            "deleted_messages": deleted_count,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat history for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting chat history: {str(e)}"
        )


@app.get("/")
async def welcome():
    """Welcome endpoint with API information"""
    return {
        "message": "Welcome to the ODPC Kenya Bot API",
        "version": "1.0.0",
        "description": "AI Assistant for the Office of the Data Protection Commissioner Kenya",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "clear_memory": "/clear",
            "get_history": "/chat/history/{session_id}",
            "get_sessions": "/chat/sessions",
            "delete_history": "/chat/history/{session_id}"
        },
        "features": [
            "Multi-language support (English, Swahili, Sheng)",
            "Persistent conversation history",
            "Session-based context tracking",
            "Source citation",
            "PostgreSQL database integration"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)