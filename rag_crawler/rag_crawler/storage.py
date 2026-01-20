"""Storage layer for Markdown files with metadata.

This module handles saving extracted content as Markdown files
with YAML front matter containing metadata for RAG traceability.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from .change_detector import ChangeDetector, compute_hash
from .url_utils import url_to_filename

logger = logging.getLogger(__name__)


@dataclass
class PageMetadata:
    """Metadata for a crawled page.
    
    Attributes:
        source_url: The original URL of the page.
        title: The page title.
        crawl_timestamp: When the page was crawled.
        content_hash: SHA-256 hash of the content.
        word_count: Approximate word count.
        headings: List of heading texts.
    """
    source_url: str
    title: str
    crawl_timestamp: str
    content_hash: str
    word_count: int = 0
    headings: list = None
    
    def __post_init__(self):
        if self.headings is None:
            self.headings = []
    
    def to_yaml(self) -> str:
        """Convert metadata to YAML string.
        
        Returns:
            YAML formatted string.
        """
        data = {
            "source_url": self.source_url,
            "title": self.title,
            "crawl_timestamp": self.crawl_timestamp,
            "content_hash": self.content_hash,
            "word_count": self.word_count,
        }
        
        # Only include headings if not too many
        if self.headings and len(self.headings) <= 10:
            data["headings"] = self.headings
        
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


class MarkdownStorage:
    """Storage handler for Markdown files.
    
    This class manages saving crawled content as Markdown files
    with YAML front matter and handles change detection.
    
    Attributes:
        output_dir: Directory to save files to.
        change_detector: ChangeDetector instance for hash comparison.
    """
    
    def __init__(self, output_dir: Path) -> None:
        """Initialize the storage handler.
        
        Args:
            output_dir: Directory to save Markdown files to.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.change_detector = ChangeDetector(self.output_dir)
        
        logger.info(f"Storage initialized at {self.output_dir}")
    
    def get_filepath(self, url: str) -> Path:
        """Get the file path for a URL.
        
        Args:
            url: The source URL.
            
        Returns:
            Path to the Markdown file.
        """
        filename = url_to_filename(url) + ".md"
        return self.output_dir / filename
    
    def save(
        self,
        url: str,
        title: str,
        markdown_content: str,
        word_count: int = 0,
        headings: Optional[list] = None,
        force: bool = False
    ) -> tuple[bool, Path]:
        """Save content to a Markdown file.
        
        Args:
            url: The source URL.
            title: The page title.
            markdown_content: The Markdown content to save.
            word_count: Approximate word count.
            headings: List of heading texts.
            force: If True, save even if content hasn't changed.
            
        Returns:
            Tuple of (was_saved, filepath).
        """
        filepath = self.get_filepath(url)
        
        # Compute content hash
        content_hash = compute_hash(markdown_content)
        
        # Check for changes unless forcing
        if not force and filepath.exists():
            existing_hash = self.change_detector.get_file_hash(filepath)
            if existing_hash == content_hash:
                logger.debug(f"Skipping {filepath.name} - content unchanged")
                return (False, filepath)
        
        # Create metadata
        metadata = PageMetadata(
            source_url=url,
            title=title,
            crawl_timestamp=datetime.now(timezone.utc).isoformat(),
            content_hash=content_hash,
            word_count=word_count,
            headings=headings or []
        )
        
        # Compose full file content
        file_content = f"---\n{metadata.to_yaml()}---\n\n{markdown_content}"
        
        # Write atomically (write to temp, then rename)
        temp_filepath = filepath.with_suffix(".md.tmp")
        
        try:
            with open(temp_filepath, "w", encoding="utf-8") as f:
                f.write(file_content)
            
            # Atomic rename (works on same filesystem)
            if filepath.exists():
                filepath.unlink()
            temp_filepath.rename(filepath)
            
            logger.info(f"Saved {filepath.name} ({word_count} words)")
            return (True, filepath)
            
        except Exception as e:
            logger.error(f"Error saving {filepath.name}: {e}")
            # Clean up temp file
            if temp_filepath.exists():
                temp_filepath.unlink()
            raise
    
    def exists(self, url: str) -> bool:
        """Check if a file already exists for a URL.
        
        Args:
            url: The source URL.
            
        Returns:
            True if file exists.
        """
        return self.get_filepath(url).exists()
    
    def load_metadata(self, url: str) -> Optional[PageMetadata]:
        """Load metadata from an existing file.
        
        Args:
            url: The source URL.
            
        Returns:
            PageMetadata if file exists, None otherwise.
        """
        filepath = self.get_filepath(url)
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Parse YAML front matter
            if not content.startswith("---"):
                return None
            
            end_idx = content.find("\n---\n", 3)
            if end_idx == -1:
                return None
            
            front_matter = content[4:end_idx]
            data = yaml.safe_load(front_matter)
            
            return PageMetadata(
                source_url=data.get("source_url", url),
                title=data.get("title", ""),
                crawl_timestamp=data.get("crawl_timestamp", ""),
                content_hash=data.get("content_hash", ""),
                word_count=data.get("word_count", 0),
                headings=data.get("headings", [])
            )
            
        except Exception as e:
            logger.warning(f"Error loading metadata from {filepath}: {e}")
            return None
    
    def list_files(self) -> list[Path]:
        """List all Markdown files in the output directory.
        
        Returns:
            List of file paths.
        """
        return list(self.output_dir.glob("*.md"))
    
    def get_stats(self) -> dict:
        """Get storage statistics.
        
        Returns:
            Dictionary with file count and total size.
        """
        files = self.list_files()
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "file_count": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
