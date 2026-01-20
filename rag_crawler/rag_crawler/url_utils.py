"""URL utilities for normalization, validation, and deduplication.

This module provides utilities for handling URLs in a consistent manner,
including normalization to prevent duplicate crawling and domain checking.
"""

import hashlib
import re
from collections import deque
from threading import Lock
from typing import Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize a URL for consistent comparison and deduplication.
    
    Normalization includes:
    - Lowercasing the scheme and host
    - Removing fragments (#...)
    - Removing trailing slashes from paths
    - Sorting query parameters
    - Removing default ports (80 for HTTP, 443 for HTTPS)
    
    Args:
        url: The URL to normalize.
        
    Returns:
        The normalized URL string.
        
    Example:
        >>> normalize_url("HTTPS://Example.Com/Path/?b=2&a=1#section")
        'https://example.com/Path?a=1&b=2'
    """
    parsed = urlparse(url)
    
    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    
    # Remove default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    
    # Normalize path (remove trailing slash, but keep root)
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if not path:
        path = "/"
    
    # Sort query parameters
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    sorted_query = urlencode(
        sorted(
            [(k, v[0] if len(v) == 1 else v) for k, v in query_params.items()]
        ),
        doseq=True
    )
    
    # Reconstruct URL without fragment
    normalized = urlunparse((
        scheme,
        netloc,
        path,
        parsed.params,
        sorted_query,
        ""  # Remove fragment
    ))
    
    return normalized


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs belong to the same domain.
    
    Args:
        url1: First URL to compare.
        url2: Second URL to compare.
        
    Returns:
        True if both URLs have the same domain (including subdomains).
        
    Example:
        >>> is_same_domain("https://example.com/page1", "https://example.com/page2")
        True
        >>> is_same_domain("https://sub.example.com", "https://example.com")
        False
    """
    parsed1 = urlparse(url1)
    parsed2 = urlparse(url2)
    
    return parsed1.netloc.lower() == parsed2.netloc.lower()


def get_domain(url: str) -> str:
    """Extract the domain (netloc) from a URL.
    
    Args:
        url: The URL to extract the domain from.
        
    Returns:
        The domain string (lowercase).
    """
    return urlparse(url).netloc.lower()


def is_valid_url(url: str) -> bool:
    """Check if a URL is valid and has HTTP/HTTPS scheme.
    
    Args:
        url: The URL to validate.
        
    Returns:
        True if the URL is valid and uses HTTP or HTTPS.
    """
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def resolve_url(base_url: str, relative_url: str) -> str:
    """Resolve a relative URL against a base URL.
    
    Args:
        base_url: The base URL to resolve against.
        relative_url: The relative URL to resolve.
        
    Returns:
        The absolute URL.
        
    Example:
        >>> resolve_url("https://example.com/docs/", "../api/")
        'https://example.com/api/'
    """
    return urljoin(base_url, relative_url)


def url_to_filename(url: str, max_length: int = 100) -> str:
    """Convert a URL to a safe filename for storage.
    
    Args:
        url: The URL to convert.
        max_length: Maximum length of the filename (excluding extension).
        
    Returns:
        A safe filename string.
        
    Example:
        >>> url_to_filename("https://example.com/docs/getting-started")
        'example_com_docs_getting-started'
    """
    parsed = urlparse(url)
    
    # Combine host and path
    parts = [parsed.netloc] + [p for p in parsed.path.split("/") if p]
    
    # Create slug
    slug = "_".join(parts)
    
    # Remove unsafe characters
    slug = re.sub(r"[^\w\-]", "_", slug)
    
    # Remove multiple underscores
    slug = re.sub(r"_+", "_", slug)
    
    # Truncate if necessary
    if len(slug) > max_length:
        # Keep a hash suffix for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        slug = slug[: max_length - 9] + "_" + url_hash
    
    return slug.strip("_")


def get_url_extension(url: str) -> str:
    """Get the file extension from a URL path.
    
    Args:
        url: The URL to extract extension from.
        
    Returns:
        The file extension including the dot, or empty string.
        
    Example:
        >>> get_url_extension("https://example.com/document.pdf")
        '.pdf'
        >>> get_url_extension("https://example.com/page")
        ''
    """
    parsed = urlparse(url)
    path = parsed.path
    
    # Find the last dot in the path
    if "." in path.split("/")[-1]:
        return "." + path.split(".")[-1].lower()
    
    return ""


class URLQueue:
    """Thread-safe URL queue with deduplication.
    
    This class provides a queue for URLs to be crawled, with automatic
    deduplication based on normalized URLs.
    
    Attributes:
        queue: Internal deque for URL storage.
        seen: Set of already-seen normalized URLs.
        lock: Threading lock for thread safety.
    """
    
    def __init__(self) -> None:
        """Initialize an empty URL queue."""
        self._queue: deque[Tuple[str, int]] = deque()  # (url, depth)
        self._seen: Set[str] = set()
        self._lock = Lock()
    
    def add(self, url: str, depth: int = 0) -> bool:
        """Add a URL to the queue if not already seen.
        
        Args:
            url: The URL to add.
            depth: The crawl depth of this URL.
            
        Returns:
            True if the URL was added, False if it was already seen.
        """
        normalized = normalize_url(url)
        
        with self._lock:
            if normalized not in self._seen:
                self._seen.add(normalized)
                self._queue.append((url, depth))
                return True
            return False
    
    def get(self) -> Optional[Tuple[str, int]]:
        """Get the next URL from the queue.
        
        Returns:
            A tuple of (url, depth) or None if the queue is empty.
        """
        with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None
    
    def mark_seen(self, url: str) -> None:
        """Mark a URL as seen without adding it to the queue.
        
        Args:
            url: The URL to mark as seen.
        """
        normalized = normalize_url(url)
        with self._lock:
            self._seen.add(normalized)
    
    def is_seen(self, url: str) -> bool:
        """Check if a URL has already been seen.
        
        Args:
            url: The URL to check.
            
        Returns:
            True if the URL has been seen.
        """
        normalized = normalize_url(url)
        with self._lock:
            return normalized in self._seen
    
    def __len__(self) -> int:
        """Return the number of URLs in the queue."""
        with self._lock:
            return len(self._queue)
    
    @property
    def seen_count(self) -> int:
        """Return the total number of URLs seen."""
        with self._lock:
            return len(self._seen)
