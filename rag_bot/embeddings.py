"""Embedding generation using OpenAI."""

import logging
from typing import List
from openai import OpenAI

from .config import config

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using OpenAI API."""
    
    def __init__(self, model: str = None):
        """Initialize the embedding generator.
        
        Args:
            model: OpenAI embedding model to use.
        """
        self.model = model or config.EMBEDDING_MODEL
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []
        
        # OpenAI API has a limit on batch size
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                # Sort by index to maintain order
                embeddings = [item.embedding for item in sorted(
                    response.data, key=lambda x: x.index
                )]
                all_embeddings.extend(embeddings)
                
                logger.debug(f"Generated embeddings for batch {i // batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                raise
        
        logger.info(f"Generated {len(all_embeddings)} embeddings")
        return all_embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query.
        
        Args:
            query: The query text.
            
        Returns:
            Embedding vector.
        """
        embeddings = self.embed_texts([query])
        return embeddings[0] if embeddings else []
