"""Configuration settings for RAG Bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from rag_bot/.env
ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(ENV_FILE)


class Config:
    """Application configuration."""
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data" / "markdown"
    DOWNLOADS_DIR: Path = BASE_DIR / 'data' / "documents"
    VECTOR_DB_DIR: Path = BASE_DIR / "rag_bot" / "chroma_db"
    
    # Embedding settings (HuggingFace BAAI/bge-small-en-v1.5)
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSIONS: int = 384  # bge-small-en-v1.5 outputs 384 dimensions
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 8
    
    # LLM settings (Groq)
    LLM_MODEL: str = "llama-3.3-70b-versatile"  # Groq's Llama 3.3 70B model
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000
    
    # Chunking settings
    CHUNK_SIZE: int = 500  # tokens
    CHUNK_OVERLAP: int = 100  # tokens
    
    # Retrieval settings
    TOP_K: int = 5  # Number of chunks to retrieve
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.GROQ_API_KEY:
            print("Error: GROQ_API_KEY not set in environment")
            return False
        return True


# Global config instance
config = Config()