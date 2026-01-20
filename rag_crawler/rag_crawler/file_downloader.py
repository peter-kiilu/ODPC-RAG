"""PDF and file downloader for the crawler.

This module handles downloading PDFs and other documents
linked from crawled pages.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FileDownloader:
    """Downloader for PDFs and other documents.
    
    Attributes:
        output_dir: Directory to save downloaded files.
        allowed_extensions: File extensions to download.
    """
    
    DEFAULT_EXTENSIONS: Set[str] = {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", 
        ".ppt", ".pptx", ".csv", ".txt", ".rtf"
    }
    
    def __init__(
        self,
        output_dir: Path,
        allowed_extensions: Optional[Set[str]] = None,
        timeout: int = 60
    ) -> None:
        """Initialize the downloader.
        
        Args:
            output_dir: Directory to save files to.
            allowed_extensions: Extensions to download (default: PDFs and docs).
            timeout: Download timeout in seconds.
        """
        self.output_dir = Path(output_dir)
        self.downloads_dir = self.output_dir / "downloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        self.allowed_extensions = allowed_extensions or self.DEFAULT_EXTENSIONS
        self.timeout = timeout
        self._downloaded: Set[str] = set()
        self._downloaded_files: Set[str] = set()
        
        # Load existing downloaded files (persistence across runs)
        self._load_existing_files()
        
        logger.info(f"File downloader initialized at {self.downloads_dir}")
        if self._downloaded_files:
            logger.info(f"Found {len(self._downloaded_files)} previously downloaded files")
    
    def _load_existing_files(self) -> None:
        """Load list of already downloaded files from disk."""
        for filepath in self.downloads_dir.glob("*"):
            if filepath.is_file():
                # Store the filename (without path) for comparison
                self._downloaded_files.add(filepath.name.lower())
    
    def extract_file_links(self, html: str, base_url: str) -> List[str]:
        """Extract downloadable file links from HTML.
        
        Args:
            html: The HTML content.
            base_url: Base URL for resolving relative links.
            
        Returns:
            List of absolute URLs to downloadable files.
        """
        soup = BeautifulSoup(html, "lxml")
        file_links = []
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            
            # Skip empty or javascript links
            if not href or href.startswith(("javascript:", "mailto:", "#")):
                continue
            
            # Check extension
            parsed = urlparse(href)
            path = parsed.path.lower()
            
            for ext in self.allowed_extensions:
                if path.endswith(ext):
                    # Resolve relative URLs
                    absolute_url = urljoin(base_url, href)
                    if absolute_url not in self._downloaded:
                        file_links.append(absolute_url)
                    break
        
        return file_links
    
    def download_file(self, url: str, user_agent: str = "RAGCrawler/1.0") -> Optional[Path]:
        """Download a file from URL.
        
        Args:
            url: The file URL.
            user_agent: User agent for the request.
            
        Returns:
            Path to downloaded file, or None if failed or already exists.
        """
        if url in self._downloaded:
            logger.debug(f"Already downloaded this session: {url}")
            return None
        
        try:
            # Get filename from URL
            parsed = urlparse(url)
            filename = Path(parsed.path).name
            
            # Clean filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            if not filename:
                filename = f"download_{len(self._downloaded)}.pdf"
            
            # Check if file already exists from previous runs
            if filename.lower() in self._downloaded_files:
                logger.info(f"Skipping (already exists): {filename}")
                self._downloaded.add(url)  # Mark as processed
                return None
            
            filepath = self.downloads_dir / filename
            
            # Double-check file existence on disk
            if filepath.exists():
                logger.info(f"Skipping (file exists): {filename}")
                self._downloaded.add(url)
                self._downloaded_files.add(filename.lower())
                return None
            
            logger.info(f"Downloading: {filename}")
            
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": user_agent},
                stream=True
            )
            response.raise_for_status()
            
            # Write file
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self._downloaded.add(url)
            
            file_size = filepath.stat().st_size / 1024  # KB
            logger.info(f"Downloaded: {filename} ({file_size:.1f} KB)")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None
    
    def download_all(
        self,
        html: str,
        base_url: str,
        user_agent: str = "RAGCrawler/1.0"
    ) -> List[Path]:
        """Extract and download all files from HTML.
        
        Args:
            html: The HTML content.
            base_url: Base URL for resolving links.
            user_agent: User agent for requests.
            
        Returns:
            List of paths to downloaded files.
        """
        file_links = self.extract_file_links(html, base_url)
        
        if not file_links:
            logger.debug(f"No downloadable files found on {base_url}")
            return []
        
        logger.info(f"Found {len(file_links)} files to download from {base_url}")
        
        downloaded = []
        for url in file_links:
            filepath = self.download_file(url, user_agent)
            if filepath:
                downloaded.append(filepath)
        
        return downloaded
    
    @property
    def download_count(self) -> int:
        """Get number of files downloaded."""
        return len(self._downloaded)
    
    def get_stats(self) -> dict:
        """Get download statistics."""
        files = list(self.downloads_dir.glob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        
        return {
            "files_downloaded": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "downloads_dir": str(self.downloads_dir)
        }

    def deduplicate_files(self) -> int:
        """Remove duplicate files based on content hash.
        
        Returns:
            Number of duplicates removed.
        """
        import hashlib
        
        logger.info("Starting file deduplication...")
        hashes = {}
        removed = 0
        
        # Get all files sorted by creation time (keep oldest)
        files = sorted(
            [f for f in self.downloads_dir.glob("*") if f.is_file()],
            key=lambda x: x.stat().st_ctime
        )
        
        for filepath in files:
            try:
                # Calculate MD5 hash
                hasher = hashlib.md5()
                with open(filepath, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        hasher.update(chunk)
                file_hash = hasher.hexdigest()
                
                if file_hash in hashes:
                    # Duplicate found
                    original = hashes[file_hash]
                    logger.info(f"Removing duplicate: {filepath.name} (same as {original})")
                    filepath.unlink()
                    removed += 1
                else:
                    hashes[file_hash] = filepath.name
                    
            except Exception as e:
                logger.error(f"Error deduplicating {filepath}: {e}")
        
        # Update cache
        self._downloaded_files.clear()
        self._load_existing_files()
        
        logger.info(f"Deduplication complete. Removed {removed} files.")
        return removed
