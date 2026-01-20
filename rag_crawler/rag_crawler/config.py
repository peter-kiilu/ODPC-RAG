"""Configuration management for the RAG web crawler.

This module provides dataclass-based configuration with sensible defaults
for crawling, rate limiting, and output settings.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Set


@dataclass
class CrawlerConfig:
    """Configuration for the web crawler.
    
    Attributes:
        base_url: The starting URL for crawling.
        max_depth: Maximum depth to crawl from the base URL.
        rate_limit: Minimum seconds between requests to the same domain.
        output_dir: Directory to save Markdown files.
        user_agent: User agent string for HTTP requests.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retries for failed requests.
        respect_robots_txt: Whether to respect robots.txt rules.
        allowed_extensions: File extensions to consider as crawlable pages.
        excluded_patterns: URL patterns to exclude from crawling.
    """
    
    base_url: str
    max_depth: int = 3
    rate_limit: float = 1.0  # seconds between requests
    output_dir: Path = field(default_factory=lambda: Path("output"))
    user_agent: str = "RAGCrawler/1.0 (+https://github.com/rag-crawler)"
    timeout: int = 30
    max_retries: int = 3
    respect_robots_txt: bool = True
    allowed_extensions: Set[str] = field(
        default_factory=lambda: {".html", ".htm", ".php", ".asp", ".aspx", ""}
    )
    excluded_patterns: Set[str] = field(
        default_factory=lambda: {
            "/login", "/logout", "/signin", "/signout",
            "/admin", "/wp-admin", "/cart", "/checkout"
        }
    )
    
    def __post_init__(self) -> None:
        """Validate and normalize configuration after initialization."""
        # Ensure output_dir is a Path object
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Normalize base_url (remove trailing slash)
        self.base_url = self.base_url.rstrip("/")
        
        # Validate rate limit
        if self.rate_limit < 0:
            raise ValueError("rate_limit must be non-negative")
        
        # Validate max_depth
        if self.max_depth < 0:
            raise ValueError("max_depth must be non-negative")


@dataclass
class ExtractorConfig:
    """Configuration for content extraction.
    
    Attributes:
        remove_tags: HTML tags to remove completely.
        content_tags: HTML tags to extract content from.
        preserve_attributes: Whether to preserve certain HTML attributes.
    """
    
    remove_tags: Set[str] = field(
        default_factory=lambda: {
            "script", "style", "nav", "header", "footer", "aside",
            "noscript", "iframe", "form", "button", "input",
            "advertisement", "cookie-banner", "popup"
        }
    )
    content_tags: Set[str] = field(
        default_factory=lambda: {
            "h1", "h2", "h3", "h4", "h5", "h6",
            "p", "ul", "ol", "li", "dl", "dt", "dd",
            "table", "thead", "tbody", "tr", "th", "td",
            "pre", "code", "blockquote",
            "article", "section", "main", "div"
        }
    )
    preserve_attributes: bool = False


@dataclass
class ConverterConfig:
    """Configuration for Markdown conversion.
    
    Attributes:
        heading_style: Style for headings (ATX or SETEXT).
        code_language: Default language for code blocks.
        strip_empty_lines: Whether to strip excessive empty lines.
        wrap_width: Line wrap width (0 for no wrapping).
    """
    
    heading_style: str = "ATX"  # ATX uses # symbols
    code_language: str = ""
    strip_empty_lines: bool = True
    wrap_width: int = 0  # No wrapping by default
