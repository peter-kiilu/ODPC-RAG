"""Main web crawler engine.

This module orchestrates the crawling process, bringing together
URL handling, content extraction, conversion, and storage.
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Set
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import CrawlerConfig
from .converter import convert_to_markdown
from .extractor import ContentExtractor, ExtractedContent
from .rate_limiter import RateLimiter
from .robots_parser import RobotsChecker
from .storage import MarkdownStorage
from .url_utils import (
    URLQueue,
    get_domain,
    get_url_extension,
    is_same_domain,
    is_valid_url,
    normalize_url,
    resolve_url,
)

logger = logging.getLogger(__name__)


@dataclass
class CrawlStats:
    """Statistics for a crawl session.
    
    Attributes:
        pages_crawled: Number of pages successfully crawled.
        pages_saved: Number of pages saved (new or changed).
        pages_skipped: Number of pages skipped (unchanged).
        pages_failed: Number of pages that failed.
        total_words: Total word count across all pages.
        start_time: When the crawl started.
        end_time: When the crawl ended.
    """
    pages_crawled: int = 0
    pages_saved: int = 0
    pages_skipped: int = 0
    pages_failed: int = 0
    total_words: int = 0
    start_time: float = 0
    end_time: float = 0
    errors: list = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Get crawl duration in seconds."""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0
    
    def to_dict(self) -> dict:
        """Convert stats to dictionary."""
        return {
            "pages_crawled": self.pages_crawled,
            "pages_saved": self.pages_saved,
            "pages_skipped": self.pages_skipped,
            "pages_failed": self.pages_failed,
            "total_words": self.total_words,
            "duration_seconds": round(self.duration_seconds, 2),
            "errors_count": len(self.errors)
        }


class WebCrawler:
    """Production-grade web crawler for RAG content extraction.
    
    This class orchestrates the complete crawling workflow:
    1. URL discovery and queue management
    2. robots.txt compliance
    3. Rate limiting
    4. Content extraction and conversion
    5. Storage with change detection
    
    Attributes:
        config: CrawlerConfig with crawl settings.
        storage: MarkdownStorage for saving content.
        extractor: ContentExtractor for parsing HTML.
        robots_checker: RobotsChecker for robots.txt compliance.
        rate_limiter: RateLimiter for request throttling.
        session: requests.Session for HTTP requests.
    """
    
    def __init__(self, config: CrawlerConfig) -> None:
        """Initialize the crawler.
        
        Args:
            config: Configuration for the crawler.
        """
        self.config = config
        self.storage = MarkdownStorage(config.output_dir)
        self.extractor = ContentExtractor()
        self.robots_checker = RobotsChecker(config.user_agent) if config.respect_robots_txt else None
        self.rate_limiter = RateLimiter(config.rate_limit)
        
        # Setup session with retries
        self.session = self._create_session()
        
        # URL queue
        self._queue = URLQueue()
        
        # Stats
        self._stats = CrawlStats()
        
        logger.info(f"Crawler initialized for {config.base_url}")
        logger.info(f"Max depth: {config.max_depth}, Rate limit: {config.rate_limit}s")
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry configuration.
        
        Returns:
            Configured requests.Session.
        """
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        
        return session
    
    def crawl(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> CrawlStats:
        """Start the crawl from the configured base URL.
        
        Args:
            progress_callback: Optional callback(crawled, total, current_url).
            
        Returns:
            CrawlStats with crawl results.
        """
        self._stats = CrawlStats()
        self._stats.start_time = time.time()
        
        logger.info(f"Starting crawl from {self.config.base_url}")
        
        # Add base URL to queue
        self._queue.add(self.config.base_url, depth=0)
        
        try:
            while True:
                # Get next URL from queue
                item = self._queue.get()
                if item is None:
                    break
                
                url, depth = item
                
                # Check depth limit
                if depth > self.config.max_depth:
                    logger.debug(f"Skipping {url} - depth {depth} exceeds max {self.config.max_depth}")
                    continue
                
                # Progress callback
                if progress_callback:
                    progress_callback(
                        self._stats.pages_crawled,
                        self._queue.seen_count,
                        url
                    )
                
                # Process this URL
                self._process_url(url, depth)
        
        except KeyboardInterrupt:
            logger.warning("Crawl interrupted by user")
        
        except Exception as e:
            logger.error(f"Crawl error: {e}")
            self._stats.errors.append(str(e))
        
        finally:
            self._stats.end_time = time.time()
            self.session.close()
        
        # Log summary
        logger.info(f"Crawl complete: {self._stats.pages_crawled} pages, "
                   f"{self._stats.pages_saved} saved, "
                   f"{self._stats.pages_skipped} unchanged, "
                   f"{self._stats.pages_failed} failed")
        logger.info(f"Duration: {self._stats.duration_seconds:.1f}s")
        
        return self._stats
    
    def _process_url(self, url: str, depth: int) -> None:
        """Process a single URL.
        
        Args:
            url: The URL to process.
            depth: Current crawl depth.
        """
        domain = get_domain(url)
        
        # Check robots.txt
        if self.robots_checker and not self.robots_checker.can_fetch(url):
            logger.info(f"Blocked by robots.txt: {url}")
            return
        
        # Apply rate limiting
        self.rate_limiter.wait(domain)
        
        # Fetch page
        try:
            response = self.session.get(
                url,
                timeout=self.config.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            self._stats.pages_failed += 1
            self._stats.errors.append(f"{url}: {e}")
            return
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            logger.debug(f"Skipping non-HTML content: {url}")
            return
        
        # Extract and save content
        try:
            extracted = self.extractor.extract(response.text, url)
            markdown = convert_to_markdown(extracted.content_html)
            
            was_saved, filepath = self.storage.save(
                url=url,
                title=extracted.title,
                markdown_content=markdown,
                word_count=extracted.word_count,
                headings=extracted.headings
            )
            
            self._stats.pages_crawled += 1
            self._stats.total_words += extracted.word_count
            
            if was_saved:
                self._stats.pages_saved += 1
            else:
                self._stats.pages_skipped += 1
            
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            self._stats.pages_failed += 1
            self._stats.errors.append(f"{url}: {e}")
            return
        
        # Discover links (only if not at max depth)
        if depth < self.config.max_depth:
            self._discover_links(response.text, url, depth)
    
    def _discover_links(self, html: str, base_url: str, current_depth: int) -> None:
        """Discover and queue new links from a page.
        
        Args:
            html: The HTML content.
            base_url: The base URL for resolving relative links.
            current_depth: Current crawl depth.
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "lxml")
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            
            # Skip empty, javascript, and mailto links
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            
            # Resolve relative URLs
            absolute_url = resolve_url(base_url, href)
            
            # Validation checks
            if not is_valid_url(absolute_url):
                continue
            
            # Same domain check
            if not is_same_domain(absolute_url, self.config.base_url):
                continue
            
            # Extension check
            ext = get_url_extension(absolute_url)
            if ext and ext not in self.config.allowed_extensions:
                continue
            
            # Excluded patterns check
            normalized = normalize_url(absolute_url)
            if any(pattern in normalized for pattern in self.config.excluded_patterns):
                continue
            
            # Add to queue
            self._queue.add(absolute_url, current_depth + 1)


def crawl_website(
    url: str,
    output_dir: str = "output",
    max_depth: int = 3,
    rate_limit: float = 1.0,
    respect_robots: bool = True
) -> CrawlStats:
    """Convenience function to crawl a website.
    
    Args:
        url: The base URL to crawl.
        output_dir: Directory to save Markdown files.
        max_depth: Maximum crawl depth.
        rate_limit: Seconds between requests.
        respect_robots: Whether to respect robots.txt.
        
    Returns:
        CrawlStats with results.
    """
    config = CrawlerConfig(
        base_url=url,
        output_dir=Path(output_dir),
        max_depth=max_depth,
        rate_limit=rate_limit,
        respect_robots_txt=respect_robots
    )
    
    crawler = WebCrawler(config)
    return crawler.crawl()
