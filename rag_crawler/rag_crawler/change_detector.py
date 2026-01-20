"""Change detection using content hashing.

This module provides content hash computation and comparison
for detecting when page content has changed.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional
import re

import yaml

logger = logging.getLogger(__name__)


def compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content.
    
    Args:
        content: The content string to hash.
        
    Returns:
        Hexadecimal hash string.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def extract_hash_from_file(filepath: Path) -> Optional[str]:
    """Extract the content hash from a Markdown file's front matter.
    
    Args:
        filepath: Path to the Markdown file.
        
    Returns:
        The content hash if found, None otherwise.
    """
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for YAML front matter
        if not content.startswith("---"):
            return None
        
        # Find end of front matter
        end_match = re.search(r"\n---\n", content[3:])
        if not end_match:
            return None
        
        front_matter = content[3:end_match.start() + 3]
        
        # Parse YAML
        metadata = yaml.safe_load(front_matter)
        
        if metadata and "content_hash" in metadata:
            return metadata["content_hash"]
        
        return None
        
    except Exception as e:
        logger.warning(f"Error extracting hash from {filepath}: {e}")
        return None


class ChangeDetector:
    """Detector for content changes using hashing.
    
    This class tracks content hashes and determines whether
    content has changed since the last crawl.
    """
    
    def __init__(self, output_dir: Path) -> None:
        """Initialize the change detector.
        
        Args:
            output_dir: Directory where Markdown files are stored.
        """
        self.output_dir = output_dir
    
    def has_changed(self, filepath: Path, new_content: str) -> bool:
        """Check if content has changed compared to existing file.
        
        Args:
            filepath: Path to the existing Markdown file.
            new_content: The new content to compare.
            
        Returns:
            True if content has changed or file doesn't exist.
        """
        new_hash = compute_hash(new_content)
        existing_hash = extract_hash_from_file(filepath)
        
        if existing_hash is None:
            logger.debug(f"No existing hash for {filepath.name}")
            return True
        
        changed = new_hash != existing_hash
        
        if changed:
            logger.info(f"Content changed for {filepath.name}")
        else:
            logger.debug(f"Content unchanged for {filepath.name}")
        
        return changed
    
    def get_file_hash(self, filepath: Path) -> Optional[str]:
        """Get the stored hash for a file.
        
        Args:
            filepath: Path to the Markdown file.
            
        Returns:
            The stored hash or None.
        """
        return extract_hash_from_file(filepath)
    
    def compute_content_hash(self, content: str) -> str:
        """Compute hash for new content.
        
        Args:
            content: The content to hash.
            
        Returns:
            The content hash.
        """
        return compute_hash(content)
