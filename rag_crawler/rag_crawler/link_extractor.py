"""Link and resource extractor for RAG systems.

This module extracts all important links and resources from crawled pages
and saves them in a structured format for RAG bot access.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ExtractedLinks:
    """Container for extracted links and resources from a page.
    
    Attributes:
        source_url: The page these links were extracted from.
        internal_links: Links within the same domain.
        external_links: Links to other domains.
        pdf_links: Links to PDF documents.
        document_links: Links to Word, Excel, etc.
        video_links: Links to videos (YouTube, Vimeo, etc.).
        social_links: Social media profile links.
        email_links: Email addresses found.
        phone_links: Phone numbers found.
        event_links: Links that appear to be events/calendars.
    """
    source_url: str
    title: str = ""
    internal_links: List[str] = field(default_factory=list)
    external_links: List[str] = field(default_factory=list)
    pdf_links: List[str] = field(default_factory=list)
    document_links: List[str] = field(default_factory=list)
    video_links: List[str] = field(default_factory=list)
    social_links: Dict[str, str] = field(default_factory=dict)
    email_links: List[str] = field(default_factory=list)
    phone_links: List[str] = field(default_factory=list)
    event_links: List[str] = field(default_factory=list)
    image_links: List[str] = field(default_factory=list)
    extracted_at: str = ""
    
    def __post_init__(self):
        if not self.extracted_at:
            self.extracted_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @property
    def total_links(self) -> int:
        return (len(self.internal_links) + len(self.external_links) + 
                len(self.pdf_links) + len(self.video_links))


class LinkExtractor:
    """Extracts and categorizes all links from HTML pages.
    
    Designed to capture all resources for RAG bot access.
    """
    
    # Video platforms
    VIDEO_DOMAINS = {
        "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
        "facebook.com/watch", "twitter.com/i/status", "tiktok.com"
    }
    
    # Social media platforms
    SOCIAL_PLATFORMS = {
        "facebook.com": "facebook",
        "twitter.com": "twitter",
        "x.com": "twitter",
        "linkedin.com": "linkedin",
        "instagram.com": "instagram",
        "tiktok.com": "tiktok",
        "youtube.com": "youtube",
        "github.com": "github",
        "pinterest.com": "pinterest",
    }
    
    # Document extensions
    DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".txt", ".rtf"}
    
    # Event-related keywords in URLs
    EVENT_KEYWORDS = {"event", "calendar", "schedule", "workshop", "conference", "seminar", "webinar", "training"}
    
    def __init__(self, output_dir: Path) -> None:
        """Initialize the link extractor.
        
        Args:
            output_dir: Directory to save extracted links.
        """
        self.output_dir = Path(output_dir)
        self.links_file = self.output_dir / "links.json"
        self.all_links: List[Dict] = []
        
        # Load existing links if file exists
        if self.links_file.exists():
            try:
                with open(self.links_file, "r", encoding="utf-8") as f:
                    self.all_links = json.load(f)
            except Exception:
                self.all_links = []
        
        logger.info(f"Link extractor initialized at {self.output_dir}")
    
    def extract(self, html: str, source_url: str, title: str = "") -> ExtractedLinks:
        """Extract all links from HTML content.
        
        Args:
            html: The HTML content.
            source_url: The URL of the page.
            title: The page title.
            
        Returns:
            ExtractedLinks with categorized links.
        """
        soup = BeautifulSoup(html, "lxml")
        base_domain = urlparse(source_url).netloc.lower()
        
        links = ExtractedLinks(source_url=source_url, title=title)
        
        seen_urls: Set[str] = set()
        
        # Extract all <a> tags
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            
            # Skip empty, anchor, and javascript links
            if not href or href.startswith(("#", "javascript:")):
                continue
            
            # Handle mailto and tel links
            if href.startswith("mailto:"):
                email = href.replace("mailto:", "").split("?")[0]
                if email and email not in links.email_links:
                    links.email_links.append(email)
                continue
            
            if href.startswith("tel:"):
                phone = href.replace("tel:", "")
                if phone and phone not in links.phone_links:
                    links.phone_links.append(phone)
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(source_url, href)
            
            # Skip duplicates
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)
            
            # Parse URL
            parsed = urlparse(absolute_url)
            url_domain = parsed.netloc.lower()
            url_path = parsed.path.lower()
            
            # Categorize the link
            self._categorize_link(links, absolute_url, url_domain, url_path, base_domain)
        
        # Extract embedded videos (iframes)
        for iframe in soup.find_all("iframe", src=True):
            src = iframe["src"]
            if src and any(domain in src for domain in self.VIDEO_DOMAINS):
                if src not in links.video_links:
                    links.video_links.append(src)
        
        # Extract images (for reference)
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if src and not src.startswith("data:"):
                absolute_src = urljoin(source_url, src)
                if absolute_src not in links.image_links:
                    links.image_links.append(absolute_src)
        
        return links
    
    def _categorize_link(
        self,
        links: ExtractedLinks,
        url: str,
        url_domain: str,
        url_path: str,
        base_domain: str
    ) -> None:
        """Categorize a link into the appropriate category."""
        
        # Check for documents
        for ext in self.DOC_EXTENSIONS:
            if url_path.endswith(ext):
                if ext == ".pdf":
                    if url not in links.pdf_links:
                        links.pdf_links.append(url)
                else:
                    if url not in links.document_links:
                        links.document_links.append(url)
                return
        
        # Check for videos
        if any(domain in url_domain for domain in self.VIDEO_DOMAINS):
            if url not in links.video_links:
                links.video_links.append(url)
            return
        
        # Check for social media
        for domain, platform in self.SOCIAL_PLATFORMS.items():
            if domain in url_domain:
                links.social_links[platform] = url
                return
        
        # Check for events
        if any(keyword in url_path for keyword in self.EVENT_KEYWORDS):
            if url not in links.event_links:
                links.event_links.append(url)
            # Also add to appropriate link category
        
        # Internal vs external
        if base_domain in url_domain or url_domain in base_domain:
            if url not in links.internal_links:
                links.internal_links.append(url)
        else:
            if url not in links.external_links:
                links.external_links.append(url)
    
    def save(self, links: ExtractedLinks) -> None:
        """Save extracted links to the links.json file.
        
        Args:
            links: The extracted links to save.
        """
        try:
            # Check if this source_url already exists
            existing_idx = None
            for i, item in enumerate(self.all_links):
                if not isinstance(item, dict):
                    logger.warning(f"Removing invalid item at index {i}: {type(item)}")
                    continue
                    
                if item.get("source_url") == links.source_url:
                    existing_idx = i
                    break
            
            if existing_idx is not None:
                self.all_links[existing_idx] = links.to_dict()
            else:
                self.all_links.append(links.to_dict())
            
            # Filter out any non-dict items before saving
            self.all_links = [x for x in self.all_links if isinstance(x, dict)]
            
            # Write to file
            with open(self.links_file, "w", encoding="utf-8") as f:
                json.dump(self.all_links, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved links from {links.source_url}")
            
        except Exception as e:
            logger.error(f"Error saving links for {links.source_url}: {e}")
    
    def get_all_videos(self) -> List[str]:
        """Get all video links from all crawled pages."""
        videos = []
        for page in self.all_links:
            videos.extend(page.get("video_links", []))
        return list(set(videos))
    
    def get_all_external_links(self) -> List[str]:
        """Get all external links from all crawled pages."""
        external = []
        for page in self.all_links:
            external.extend(page.get("external_links", []))
        return list(set(external))
    
    def get_statistics(self) -> dict:
        """Get statistics about extracted links."""
        stats = {
            "pages_processed": len(self.all_links),
            "total_internal_links": 0,
            "total_external_links": 0,
            "total_pdf_links": 0,
            "total_video_links": 0,
            "total_social_platforms": set(),
            "total_emails": 0,
            "total_events": 0,
        }
        
        for page in self.all_links:
            stats["total_internal_links"] += len(page.get("internal_links", []))
            stats["total_external_links"] += len(page.get("external_links", []))
            stats["total_pdf_links"] += len(page.get("pdf_links", []))
            stats["total_video_links"] += len(page.get("video_links", []))
            stats["total_events"] += len(page.get("event_links", []))
            stats["total_emails"] += len(page.get("email_links", []))
            
            for platform in page.get("social_links", {}).keys():
                stats["total_social_platforms"].add(platform)
        
        stats["total_social_platforms"] = list(stats["total_social_platforms"])
        
        return stats
        
    def deduplicate_links(self) -> int:
        """Remove duplicate links within each category for all pages.
        
        Also removes duplicate pages if they exist (though save() handles that).
        
        Returns:
            Total number of duplicate links removed.
        """
        duplicates_removed = 0
        unique_pages = {}
        
        # Deduplicate pages based on source_url
        for i, page in enumerate(self.all_links):
            if not isinstance(page, dict):
                logger.warning(f"Skipping invalid page entry at index {i}: {type(page)}")
                continue
                
            source_url = page.get("source_url")
            if source_url:
                unique_pages[source_url] = page
        
        # Check if pages were removed
        if len(unique_pages) < len(self.all_links):
            duplicates_removed += (len(self.all_links) - len(unique_pages))
            self.all_links = list(unique_pages.values())
        
        # Deduplicate links within each page
        for page in self.all_links:
            try:
                for key, value in page.items():
                    if isinstance(value, list) and key.endswith("_links") and key != "social_links":
                        original_len = len(value)
                        # Deduplicate while preserving order
                        try:
                            unique_items = list(dict.fromkeys(value))
                            if len(unique_items) < original_len:
                                page[key] = unique_items
                                duplicates_removed += (original_len - len(unique_items))
                        except Exception as e:
                            logger.error(f"Error deduplicating list {key}: {e}")
            except Exception as e:
                logger.error(f"Error processing page: {e}")
        
        # Save updates back to file
        with open(self.links_file, "w", encoding="utf-8") as f:
            json.dump(self.all_links, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Link deduplication complete. Removed {duplicates_removed} duplicates.")
        return duplicates_removed
