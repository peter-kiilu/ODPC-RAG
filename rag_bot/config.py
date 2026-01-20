"""Configuration settings for RAG Bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "rag_crawler" / "output_single"
    DOWNLOADS_DIR: Path = DATA_DIR / "downloads"
    VECTOR_DB_DIR: Path = BASE_DIR / "rag_bot" / "chroma_db"
    
    # Embedding settings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    
    # LLM settings
    LLM_MODEL: str = "gpt-4o-mini"
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
        if not cls.OPENAI_API_KEY:
            print("Error: OPENAI_API_KEY not set in environment")
            return False
        return True


# Global config instance
config = Config()
