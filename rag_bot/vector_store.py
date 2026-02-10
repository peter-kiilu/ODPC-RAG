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

from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.vector_stores.chroma import ChromaVectorStore
import os
from datetime import datetime

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
        
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        
        # Embedding generator with GPU support
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedder = EmbeddingGenerator(device=device)
        
        logger.info(f"Vector store initialized at {self.persist_dir}")
        logger.info(f"Collection has {self.collection.count()} documents")

    def get_indexed_files(self) -> Dict[str, float]:
        """Returns a map of {filename: last_modified_timestamp} for all indexed docs."""
        # We fetch all metadatas from the collection
        results = self.collection.get(include=["metadatas"])
        indexed_files = {}
        for meta in results["metadatas"]:
            if "file_path" in meta and "last_modified" in meta:
                # We keep the latest timestamp found for each file
                path = meta["file_path"]
                mtime = meta["last_modified"]
                indexed_files[path] = max(indexed_files.get(path, 0), mtime)
        return indexed_files
    
    def add_chunks(self, chunks: List[Chunk]) -> int:
        """Upserts chunks and skips unchanged files."""
        if not chunks:
            return 0
        
        # 1. Get current state to identify what needs updating
        indexed_files = self.get_indexed_files()
        
        ids, documents, metadatas = [], [], []
        skipped_count = 0

        for chunk in chunks:
            file_path = chunk.metadata.get('file_path')
            # Check if file is already indexed and hasn't changed since then
            current_mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
            indexed_mtime = indexed_files.get(file_path, 0)

            if current_mtime <= indexed_mtime and indexed_mtime != 0:
                skipped_count += 1
                continue

            # 2. Prepare for Upsert
            chunk_id = f"{file_path}_{chunk.chunk_index}".replace("\\", "_").replace("/", "_").replace(":", "_")
            
            # Add timestamp to metadata so we can check it next time
            chunk.metadata["last_modified"] = current_mtime
            
            ids.append(chunk_id)
            documents.append(chunk.content)
            metadatas.append(chunk.metadata)

        if not ids:
            logger.info(f"All {len(chunks)} chunks are already up to date. Skipping.")
            return 0

        # 3. Use upsert instead of add
        # Upsert will update existing IDs or add new ones if they don't exist
        logger.info(f"Upserting {len(ids)} chunks (skipped {skipped_count} unchanged)...")
        embeddings = self.embedder.embed_texts(documents)
        
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            self.collection.upsert(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )
        
        logger.info(f"Indexing complete. Total count: {self.collection.count()}")
        return len(ids)

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
        top_k: int = 7
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
                source = results["metadatas"][0][i].get("source", "")
                score = self._distance_to_score(results["distances"][0][i])
                    
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
