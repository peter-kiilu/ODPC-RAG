"""Vector store using ChromaDB."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import torch
import chromadb
from chromadb.config import Settings

from .config import config
from .chunker import Chunk
from .embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB-based vector store for document chunks."""
    
    COLLECTION_NAME = "odpc_documents"
    
    def __init__(self, persist_dir: Optional[Path] = None):
        """Initialize the vector store.
        
        Args:
            persist_dir: Directory to persist the database.
        """
        self.persist_dir = persist_dir or config.VECTOR_DB_DIR
        self.persist_dir = Path(self.persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "ODPC Kenya document embeddings", "hnsw:space": "cosine"}
        )
        
        # Embedding generator with GPU support
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedder = EmbeddingGenerator(device=device)
        
        logger.info(f"Vector store initialized at {self.persist_dir}")
        logger.info(f"Collection has {self.collection.count()} documents")
    
    def add_chunks(self, chunks: List[Chunk]) -> None:
        """Add chunks to the vector store.
        
        Args:
            chunks: List of chunks to add.
        """
        if not chunks:
            logger.warning("No chunks to add")
            return
        
        logger.info(f"Adding {len(chunks)} chunks to vector store...")
        
        # Prepare data
        ids = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{chunk.metadata.get('file_path', 'doc')}_{chunk.chunk_index}"
            # Sanitize ID
            chunk_id = chunk_id.replace("\\", "_").replace("/", "_").replace(":", "_")
            
            ids.append(chunk_id)
            documents.append(chunk.content)
            metadatas.append(chunk.metadata)
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = self.embedder.embed_texts(documents)
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            
            self.collection.add(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )
            
            logger.debug(f"Added batch {i // batch_size + 1}")
        
        logger.info(f"Added {len(chunks)} chunks. Total: {self.collection.count()}")

    def _distance_to_score(self, distance: float) -> float:
        """
        Convert distance to similarity score.
        
        For cosine distance: distance = 1 - cosine_similarity
        So: similarity = 1 - distance
        Clamp to [0, 1] range.
        """
        score = 1.0 - distance
        return max(0.0, min(1.0, score))
    
    def search(
        self,
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents.
        
        Args:
            query: The search query.
            top_k: Number of results to return.
            
        Returns:
            List of results with content, metadata, and score.
        """
        top_k = top_k or config.TOP_K
        
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        
        # Search collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                    "score": self._distance_to_score(results["distances"][0][i])
                })
        
        return formatted
    
    def clear(self) -> None:
        """Clear all documents from the collection."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self.collection = self.client.create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "ODPC Kenya document embeddings", "hnsw:space": "cosine" }
        )
        logger.info("Vector store cleared")
    
    @property
    def count(self) -> int:
        """Get number of documents in the collection."""
        return self.collection.count()