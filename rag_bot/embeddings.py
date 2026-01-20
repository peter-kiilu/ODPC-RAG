"""Embedding generation using HuggingFace BAAI/bge-small-en-v1.5."""

import logging
from typing import List
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using HuggingFace BAAI/bge-small-en-v1.5 model."""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", device: str = "cpu", batch_size: int = 8):
        """Initialize the embedding generator.
        
        Args:
            model_name: HuggingFace model to use for embeddings.
            device: Device to run the model on ('cpu' or 'cuda').
            batch_size: Batch size for embedding generation.
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        
        # Initialize the HuggingFace embedding model
        self.embed_model = HuggingFaceEmbedding(
            model_name=self.model_name,
            device=self.device,
            embed_batch_size=self.batch_size,
        )
        logger.info(f"Initialized HuggingFace embedding model: {self.model_name}")
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []
        
        all_embeddings = []
        
        try:
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                
                # Get embeddings for each text in the batch
                batch_embeddings = [
                    self.embed_model.get_text_embedding(text) for text in batch
                ]
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(f"Generated embeddings for batch {i // self.batch_size + 1}")
                
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
        try:
            embedding = self.embed_model.get_query_embedding(query)
            return embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise
    
    def get_embed_model(self):
        """Return the underlying HuggingFace embedding model for use with llama_index Settings."""
        return self.embed_model
