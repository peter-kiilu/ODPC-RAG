"""Text chunker for splitting documents into smaller pieces."""

import logging
from typing import List, Optional
from dataclasses import dataclass, field
from .document_loader import Document

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A chunk of text with metadata."""
    content: str
    metadata: dict = field(default_factory=dict)
    chunk_index: int = 0
    
    @property
    def source(self) -> str:
        return self.metadata.get("source", "unknown")


class TextChunker:
    """Split documents into chunks for embedding."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        min_chunk_size: int = 50
    ):
        """Initialize the chunker.
        
        Args:
            chunk_size: Target size of each chunk in characters.
            chunk_overlap: Overlap between consecutive chunks.
            min_chunk_size: Minimum size to keep a chunk.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # Try to use tiktoken for accurate token counting
        try:
            import tiktoken
            self.encoder = tiktoken.get_encoding("cl100k_base")
            self.use_tokens = True
        except ImportError:
            self.encoder = None
            self.use_tokens = False
            logger.warning("tiktoken not installed. Using character-based chunking.")
    
    def chunk_documents(self, documents: List[Document]) -> List[Chunk]:
        """Split all documents into chunks.
        
        Args:
            documents: List of documents to chunk.
            
        Returns:
            List of Chunk objects.
        """
        all_chunks = []
        
        for doc in documents:
            chunks = self._chunk_document(doc)
            all_chunks.extend(chunks)
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
        return all_chunks
    
    def _chunk_document(self, document: Document) -> List[Chunk]:
        """Split a single document into chunks."""
        text = document.content
        chunks = []
        
        # Split by paragraphs first
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Check if adding this paragraph exceeds chunk size
            test_chunk = current_chunk + "\n\n" + para if current_chunk else para
            
            if self._get_size(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # Save current chunk if it's big enough
                if current_chunk and self._get_size(current_chunk) >= self.min_chunk_size:
                    chunks.append(self._create_chunk(
                        current_chunk, document.metadata, chunk_index
                    ))
                    chunk_index += 1
                
                # Handle paragraph that's too long
                if self._get_size(para) > self.chunk_size:
                    sub_chunks = self._split_long_text(para)
                    for sub_chunk in sub_chunks:
                        if self._get_size(sub_chunk) >= self.min_chunk_size:
                            chunks.append(self._create_chunk(
                                sub_chunk, document.metadata, chunk_index
                            ))
                            chunk_index += 1
                    current_chunk = ""
                else:
                    # Start new chunk with overlap
                    overlap = self._get_overlap(current_chunk)
                    current_chunk = overlap + para if overlap else para
        
        # Don't forget the last chunk
        if current_chunk and self._get_size(current_chunk) >= self.min_chunk_size:
            chunks.append(self._create_chunk(
                current_chunk, document.metadata, chunk_index
            ))
        
        return chunks
    
    def _create_chunk(self, content: str, doc_metadata: dict, index: int) -> Chunk:
        """Create a chunk with metadata."""
        metadata = doc_metadata.copy()
        metadata["chunk_index"] = index
        return Chunk(content=content, metadata=metadata, chunk_index=index)
    
    def _get_size(self, text: str) -> int:
        """Get size of text in tokens or characters."""
        if self.use_tokens and self.encoder:
            return len(self.encoder.encode(text))
        return len(text)
    
    def _get_overlap(self, text: str) -> str:
        """Get the overlap portion from the end of text."""
        if not text or self.chunk_overlap <= 0:
            return ""
        
        if self.use_tokens and self.encoder:
            tokens = self.encoder.encode(text)
            overlap_tokens = tokens[-self.chunk_overlap:]
            return self.encoder.decode(overlap_tokens)
        else:
            return text[-self.chunk_overlap:]
    
    def _split_long_text(self, text: str) -> List[str]:
        """Split a long text into smaller pieces."""
        chunks = []
        
        # Try splitting by sentences
        sentences = text.replace(". ", ".\n").split("\n")
        current = ""
        
        for sentence in sentences:
            test = current + " " + sentence if current else sentence
            if self._get_size(test) <= self.chunk_size:
                current = test
            else:
                if current:
                    chunks.append(current.strip())
                current = sentence
        
        if current:
            chunks.append(current.strip())
        
        return chunks
