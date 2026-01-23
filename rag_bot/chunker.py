"""Text chunker for splitting documents into smaller pieces."""

import logging
from typing import List
from dataclasses import dataclass, field
from llama_index.core.node_parser import TokenTextSplitter
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
    """Split documents into chunks using LlamaIndex TokenTextSplitter."""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100
    ):
        """Initialize the chunker with token-based limits."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Reference pattern: LlamaIndex native splitter handles the math
        self.splitter = TokenTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separator="\n"
        )
    
    def chunk_documents(self, documents: List[Document]) -> List[Chunk]:
        """Split all documents into chunks."""
        all_chunks = []
        
        for doc in documents:
            # Use the splitter to get clean strings
            text_chunks = self.splitter.split_text(doc.content)
            
            for i, text in enumerate(text_chunks):
                # Build metadata including the index for incremental updates
                metadata = doc.metadata.copy()
                metadata["chunk_index"] = i
                
                all_chunks.append(Chunk(
                    content=text,
                    metadata=metadata,
                    chunk_index=i
                ))
        
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
