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
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
        return all_chunks
