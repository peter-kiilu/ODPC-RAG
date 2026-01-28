"""Embedding generation using HuggingFace BAAI/bge-small-en-v1.5."""

import logging
from typing import List
import torch
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
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.batch_size = batch_size
        
        logger.info(f"Initializing HuggingFace embedding model: {self.model_name} on {self.device}")
        
        # FIX: Initialize with explicit parameters to avoid meta tensor issue
        try:
            self.embed_model = HuggingFaceEmbedding(
                model_name=self.model_name,
                device=self.device,
                embed_batch_size=self.batch_size,
                normalize=True,
                trust_remote_code=True,  # ADD THIS
            )
            
            # FIX: Force model to fully load by doing a dummy embedding
            # This ensures the model is properly initialized and not in "meta" state
            logger.info("Performing initialization test...")
            test_embedding = self.embed_model.get_text_embedding("initialization test")
            logger.info(f"✓ Model initialized successfully (embedding dim: {len(test_embedding)})")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            logger.info("Attempting fallback initialization...")
            
            # Fallback: Try with minimal settings
            self.embed_model = HuggingFaceEmbedding(
                model_name=self.model_name,
                device="cpu",  # Force CPU on fallback
            )
            
            # Test again
            test_embedding = self.embed_model.get_text_embedding("initialization test")
            logger.info(f"✓ Fallback initialization successful (embedding dim: {len(test_embedding)})")
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts using optimized batching."""
        if not texts:
            return []
        
        try:
            # LlamaIndex's built-in batch method
            # It uses the self.batch_size you defined in __init__ automatically
            all_embeddings = self.embed_model.get_text_embedding_batch(
                texts, 
                show_progress=True  # This will give you a nice progress bar!
            )
            logger.info(f"Generated {len(all_embeddings)} embeddings")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
        
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