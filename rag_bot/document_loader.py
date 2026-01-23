"""Document loader for markdown and PDF files."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """A document with content and metadata."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def source(self) -> str:
        return self.metadata.get("source", "unknown")
    
    @property
    def title(self) -> str:
        return self.metadata.get("title", "Untitled")


class DocumentLoader:
    """Load documents from markdown and PDF files."""
    
    def __init__(self, data_dir: Path, downloads_dir: Optional[Path] = None):
        """Initialize the document loader.
        
        Args:
            data_dir: Directory containing markdown files.
            downloads_dir: Directory containing PDF files.
        """
        self.data_dir = Path(data_dir)
        self.downloads_dir = Path(downloads_dir) if downloads_dir else None
        
    def load_all(self) -> List[Document]:
        """Load all documents from configured directories.
        
        Returns:
            List of Document objects.
        """
        documents = []
        
        # Load markdown files
        documents.extend(self._load_markdown_files())
        
        # Load PDF files
        if self.downloads_dir and self.downloads_dir.exists():
            documents.extend(self._load_pdf_files())
        
        logger.info(f"Loaded {len(documents)} documents total")
        return documents
    
    def _load_markdown_files(self) -> List[Document]:
        """Load all markdown files from data directory."""
        documents = []
        
        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {self.data_dir}")
            return documents
        
        for md_file in self.data_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                
                # Extract title from first heading or filename
                title = self._extract_title(content, md_file.stem)
                
                # Extract source URL from metadata if present
                source_url = self._extract_source_url(content, md_file.name)
                
                doc = Document(
                    content=content,
                    metadata={
                        "source": source_url,
                        "title": title,
                        "file_path": str(md_file),
                        "file_type": "markdown"
                    }
                )
                documents.append(doc)
                
            except Exception as e:
                logger.error(f"Error loading {md_file}: {e}")
        
        logger.info(f"Loaded {len(documents)} markdown files")
        return documents
    
    def _load_pdf_files(self) -> List[Document]:
        """Load all PDF files from downloads directory."""
        documents = []
        
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not installed. Skipping PDF files.")
            return documents
        
        for pdf_file in self.downloads_dir.glob("*.pdf"):
            try:
                doc = fitz.open(pdf_file)
                text_parts = []
                
                for page in doc:
                    text_parts.append(page.get_text())
                
                content = "\n".join(text_parts)
                doc.close()
                
                if content.strip():
                    document = Document(
                        content=content,
                        metadata={
                            "source": pdf_file.name,
                            "title": pdf_file.stem.replace("-", " ").replace("_", " "),
                            "file_path": str(pdf_file),
                            "file_type": "pdf"
                        }
                    )
                    documents.append(document)
                    
            except Exception as e:
                logger.error(f"Error loading PDF {pdf_file}: {e}")
        
        logger.info(f"Loaded {len(documents)} PDF files")
        return documents
    
    def _extract_title(self, content: str, fallback: str) -> str:
        """Extract title from markdown content."""
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return fallback.replace("_", " ").replace("-", " ")
    
    def _extract_source_url(self, content: str, filename: str) -> str:
        """Extract source URL from markdown metadata or filename."""
        # Try to find URL in frontmatter or content
        for line in content.split("\n")[:10]:
            if "source:" in line.lower() or "url:" in line.lower():
                parts = line.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()
        
        # Fallback: convert filename to URL-like format
        return filename.replace("_", "/").replace(".md", "")