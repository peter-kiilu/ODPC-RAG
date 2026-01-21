import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from .chat import ChatBot
from .vector_store import VectorStore
from .config import config
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI
app = FastAPI(title="ODPC Kenya Bot")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# 2. Add the middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          
    allow_credentials=True,
    allow_methods=["*"],            
    allow_headers=["*"],            
)

# Initialize the Bot globally so it doesn't reload on every message
# This keeps the vector store and memory in place
bot = ChatBot()

# Data Models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    tokens_used: int

# Endpoints
@app.get('/health')
def health_check():
    """Check if the API and Vector Store are ready"""
    vs = VectorStore()
    return {
        "Status": "Active",
        "indexed_chunks": vs.count,
        "config_valid": config.validate()
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Receive a message and return the response"""
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
    
        result = bot.chat(request.message)

        return ChatResponse(
            response=result["response"],
            sources=result["sources"],
            tokens_used=result["tokens_used"]
        )
    except Exception as e:
        logging.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/clear")
async def clear_chat():
    """Endpoint to reset conversation history."""
    bot.clear_history()
    return {"status": "success", "message": "Conversation history cleared"}