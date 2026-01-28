"""Document loader for markdown and PDF files."""

import logging
import os
import json
import gc
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

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
        # Reference pattern: Define supported extensions clearly
        self.SUPPORTED_EXTENSIONS = {'.md', '.pdf'}

    def _load_pdf_metadata(self, pdf_filename: str) -> Optional[Dict[str, Any]]:
        """
            Load metadata for a pdf file
        """
        try:
            # construct path to metadata file
            metadata_dir = self.data_dir.parent / 'document_metadata'
            metadata_filename = pdf_filename.replace(".pdf", ".json")
            metadata_path = metadata_dir / metadata_filename

            if metadata_path.exists():
                with open(metadata_path, 'r', encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning(f"No metadata found for PDF: {pdf_filename}")
                return None
        except Exception as e:
            logger.error(f"Failed to load PDF metadata for {pdf_filename}: {e}")
            return None

    @lru_cache(maxsize=100)
    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """LRU Cached file reader to prevent redundant disk I/O."""
        ext = file_path.suffix.lower()
        try:
            if ext == '.md':
                return file_path.read_text(encoding="utf-8", errors='ignore')
            elif ext == '.pdf':
                import fitz
                with fitz.open(file_path) as doc:
                    return "\n".join([page.get_text() for page in doc])
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
        return None

    def _process_single_file(self, file_path: Path) -> Optional[Document]:
        """Worker function for the ThreadPoolExecutor."""
        content = self._read_file_content(file_path)
        if not content or not content.strip():
            return None

        if file_path.suffix.lower() == '.md':
            title = self._extract_title(content, file_path.stem)
            source = self._extract_source_url(content, file_path.name)
        else:
            pdf_metadata = self._load_pdf_metadata(file_path.name)
            if pdf_metadata:
                title = pdf_metadata.get('title', file_path.stem.replace("-", " ").replace("_", " "))
                source = pdf_metadata.get('source_url', file_path.name)
                logger.debug(f"Loaded PDF URL from metadata: {source}")
            else:
                title = file_path.stem.replace("-", " ").replace("_", " ")
                source = file_path.name
                logger.warning(f"Using filename as source for {file_path.name} - metadata not found")

        return Document(
            content=content,
            metadata={
                "source": source,
                "title": title,
                "file_path": str(file_path),
                "file_type": file_path.suffix.lower()[1:],
                "last_modified": os.path.getmtime(file_path)
            }
        )
        
    def load_all(self) -> List[Document]:
        """Parallel loading with batch management and GC."""
        all_files = list(self.data_dir.glob("*.md"))
        if self.downloads_dir and self.downloads_dir.exists():
            all_files.extend(self.downloads_dir.glob("*.pdf"))

        documents = []
        # Reference pattern: Parallel processing using ThreadPoolExecutor
        BATCH_SIZE = 5 
        logger.info(f"Loading {len(all_files)} files in batches of {BATCH_SIZE}...")

        with ThreadPoolExecutor(max_workers=2) as executor:
            for i in range(0, len(all_files), BATCH_SIZE):
                batch = all_files[i:i + BATCH_SIZE]
                # Process batch in parallel
                results = list(executor.map(self._process_single_file, batch))
                
                # Filter out None values and add to list
                documents.extend([doc for doc in results if doc])
                
                # Reference pattern: Explicit Garbage Collection
                gc.collect() 
                logger.info(f"Processed batch {i//BATCH_SIZE + 1}")

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