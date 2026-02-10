"""Configuration settings for RAG Bot."""

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

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
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", 384))
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", 8))
    
    # LLM settings (Groq)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", 0.7))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", 1000))
    
    # Chunking settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", 500))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", 100))
    
    # Retrieval settings
    TOP_K: int = int(os.getenv("TOP_K", 7))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.GROQ_API_KEY:
            print("Error: GROQ_API_KEY not set in environment")
            return False
        return True


# Global config instance
config = Config()
