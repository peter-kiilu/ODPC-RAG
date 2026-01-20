"""Async web crawler with Playwright support.

This module provides an asynchronous crawler that uses Playwright
to render JavaScript-heavy pages before extraction.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Set
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .browser_fetcher import BrowserFetcher, FetchResult
from .file_downloader import FileDownloader
from .link_extractor import LinkExtractor
from .config import CrawlerConfig
from .converter import convert_to_markdown
from .extractor import ContentExtractor
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
    """Statistics for a crawl session."""
    pages_crawled: int = 0
    pages_saved: int = 0
    pages_skipped: int = 0
    pages_failed: int = 0
    total_words: int = 0
    files_downloaded: int = 0
    links_extracted: int = 0
    start_time: float = 0
    end_time: float = 0
    errors: list = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0
    
    def to_dict(self) -> dict:
        return {
            "pages_crawled": self.pages_crawled,
            "pages_saved": self.pages_saved,
            "pages_skipped": self.pages_skipped,
            "pages_failed": self.pages_failed,
            "total_words": self.total_words,
            "duration_seconds": round(self.duration_seconds, 2),
            "errors_count": len(self.errors)
        }


class AsyncWebCrawler:
    """Async web crawler with Playwright for JavaScript sites.
    
    This crawler uses a headless browser to render pages before
    extracting content, making it suitable for modern JavaScript
    applications.
    """
    
    def __init__(
        self,
        config: CrawlerConfig,
        headless: bool = True,
        download_files: bool = False
    ) -> None:
        """Initialize the async crawler.
        
        Args:
            config: Crawler configuration.
            headless: Run browser in headless mode.
            download_files: Whether to download PDFs and documents.
        """
        self.config = config
        self.storage = MarkdownStorage(config.output_dir)
        self.extractor = ContentExtractor()
        self.robots_checker = RobotsChecker(config.user_agent) if config.respect_robots_txt else None
        self.rate_limiter = RateLimiter(config.rate_limit)
        
        self._queue = URLQueue()
        self._stats = CrawlStats()
        self._headless = headless
        self._download_files = download_files
        
        # File downloader
        if download_files:
            self.file_downloader = FileDownloader(config.output_dir)
            # Clean up any existing duplicates
            self.file_downloader.deduplicate_files()
        else:
            self.file_downloader = None
        
        # Link extractor (always enabled)
        self.link_extractor = LinkExtractor(config.output_dir)
        # Clean up any existing duplicate links
        self.link_extractor.deduplicate_links()
        
        logger.info(f"Async crawler initialized for {config.base_url}")
        if download_files:
            logger.info("PDF/document downloading enabled")
    
    async def crawl(
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
        
        logger.info(f"Starting async crawl from {self.config.base_url}")
        
        # Add base URL to queue
        self._queue.add(self.config.base_url, depth=0)
        
        async with BrowserFetcher(
            user_agent=self.config.user_agent,
            timeout=self.config.timeout * 1000,
            headless=self._headless
        ) as fetcher:
            try:
                while True:
                    item = self._queue.get()
                    if item is None:
                        break
                    
                    url, depth = item
                    
                    if depth > self.config.max_depth:
                        logger.debug(f"Skipping {url} - depth {depth} exceeds max")
                        continue
                    
                    if progress_callback:
                        progress_callback(
                            self._stats.pages_crawled,
                            self._queue.seen_count,
                            url
                        )
                    
                    await self._process_url(fetcher, url, depth)
                    
            except KeyboardInterrupt:
                logger.warning("Crawl interrupted by user")
            
            except Exception as e:
                logger.error(f"Crawl error: {e}")
                self._stats.errors.append(str(e))
        
        self._stats.end_time = time.time()
        
        logger.info(f"Crawl complete: {self._stats.pages_crawled} pages, "
                   f"{self._stats.pages_saved} saved, "
                   f"{self._stats.pages_skipped} unchanged, "
                   f"{self._stats.pages_failed} failed")
        
        return self._stats
    
    async def _process_url(
        self,
        fetcher: BrowserFetcher,
        url: str,
        depth: int
    ) -> None:
        """Process a single URL with the browser.
        
        Args:
            fetcher: The browser fetcher instance.
            url: The URL to process.
            depth: Current crawl depth.
        """
        domain = get_domain(url)
        
        # Check robots.txt
        if self.robots_checker and not self.robots_checker.can_fetch(url):
            logger.info(f"Blocked by robots.txt: {url}")
            return
        
        # Apply rate limiting (blocking)
        self.rate_limiter.wait(domain)
        
        # Fetch page with browser
        result = await fetcher.fetch(url)
        
        if not result.success:
            logger.warning(f"Failed to fetch {url}: {result.error}")
            self._stats.pages_failed += 1
            self._stats.errors.append(f"{url}: {result.error}")
            return
        
        # Extract and save content
        try:
            # Use JavaScript-extracted content (more reliable for JS sites)
            if result.text_content and len(result.text_content.strip()) > 50:
                markdown = result.text_content
                title = result.title or "Untitled"
                headings = result.headings or []
                word_count = len(markdown.split())
            else:
                # Fallback to HTML extraction
                extracted = self.extractor.extract(result.html, url)
                markdown = convert_to_markdown(extracted.content_html)
                title = extracted.title
                headings = extracted.headings
                word_count = extracted.word_count
            
            was_saved, filepath = self.storage.save(
                url=url,
                title=title,
                markdown_content=markdown,
                word_count=word_count,
                headings=headings
            )
            
            self._stats.pages_crawled += 1
            self._stats.total_words += word_count
            
            if was_saved:
                self._stats.pages_saved += 1
                logger.info(f"Saved: {filepath.name} ({word_count} words)")
            else:
                self._stats.pages_skipped += 1
                logger.debug(f"Skipped (unchanged): {url}")
            
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            self._stats.pages_failed += 1
            self._stats.errors.append(f"{url}: {e}")
            return
        
        # Download PDFs and documents
        if self.file_downloader and result.html:
            downloaded = self.file_downloader.download_all(
                result.html,
                url,
                self.config.user_agent
            )
            self._stats.files_downloaded += len(downloaded)
        
        # Extract and save all links
        if result.html:
            links = self.link_extractor.extract(result.html, url, title)
            self.link_extractor.save(links)
            self._stats.links_extracted += links.total_links
        
        # Discover links
        if depth < self.config.max_depth:
            self._discover_links(result.html, url, depth)
    
    def _discover_links(self, html: str, base_url: str, current_depth: int) -> None:
        """Discover and queue new links from a page."""
        soup = BeautifulSoup(html, "lxml")
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            
            absolute_url = resolve_url(base_url, href)
            
            if not is_valid_url(absolute_url):
                continue
            
            if not is_same_domain(absolute_url, self.config.base_url):
                continue
            
            ext = get_url_extension(absolute_url)
            if ext and ext not in self.config.allowed_extensions:
                continue
            
            normalized = normalize_url(absolute_url)
            if any(pattern in normalized for pattern in self.config.excluded_patterns):
                continue
            
            self._queue.add(absolute_url, current_depth + 1)


def crawl_with_browser(
    url: str,
    output_dir: str = "output",
    max_depth: int = 3,
    rate_limit: float = 1.0,
    headless: bool = True
) -> CrawlStats:
    """Convenience function to crawl a JavaScript-heavy website.
    
    Args:
        url: The base URL to crawl.
        output_dir: Directory to save Markdown files.
        max_depth: Maximum crawl depth.
        rate_limit: Seconds between requests.
        headless: Run browser in headless mode.
        
    Returns:
        CrawlStats with results.
    """
    config = CrawlerConfig(
        base_url=url,
        output_dir=Path(output_dir),
        max_depth=max_depth,
        rate_limit=rate_limit
    )
    
    crawler = AsyncWebCrawler(config, headless=headless)
    return asyncio.run(crawler.crawl())
