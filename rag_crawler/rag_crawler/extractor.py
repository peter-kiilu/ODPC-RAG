"""Content extractor using BeautifulSoup.

This module extracts meaningful content from HTML pages,
removing boilerplate elements like navigation, ads, and scripts.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Set

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Container for extracted page content.
    
    Attributes:
        title: The page title.
        content_html: The cleaned HTML content.
        headings: List of heading texts for structure analysis.
        word_count: Approximate word count of the content.
    """
    title: str
    content_html: str
    headings: List[str]
    word_count: int


class ContentExtractor:
    """Extractor for meaningful content from HTML pages.
    
    This class uses BeautifulSoup to parse HTML and extract
    only the meaningful content, removing boilerplate elements.
    
    Attributes:
        remove_tags: Set of tag names to remove completely.
        remove_classes: Set of class name patterns to remove.
        remove_ids: Set of ID patterns to remove.
    """
    
    # Tags to remove completely (including their content)
    DEFAULT_REMOVE_TAGS: Set[str] = {
        "script", "style", "noscript", "iframe", "frame",
        "object", "embed", "applet", "form", "input",
        "button", "select", "textarea", "svg", "canvas",
        "audio", "video", "source", "track", "map", "area"
    }
    
    # Semantic tags that typically contain navigation/boilerplate
    BOILERPLATE_TAGS: Set[str] = {
        "nav", "header", "footer", "aside", "menu", "menuitem"
    }
    
    # Common class/id patterns for boilerplate content
    BOILERPLATE_PATTERNS: List[str] = [
        r"nav(igation)?",
        r"menu",
        r"header",
        r"footer",
        r"sidebar",
        r"widget",
        r"comment",
        r"share",
        r"social",
        r"advert(isement)?",
        r"ads?[-_]?",
        r"banner",
        r"popup",
        r"modal",
        r"overlay",
        r"cookie",
        r"consent",
        r"newsletter",
        r"subscribe",
        r"related[-_]?posts?",
        r"breadcrumb",
        r"pagination",
        r"author[-_]?bio",
        r"meta[-_]?info",
    ]
    
    def __init__(
        self,
        remove_tags: Optional[Set[str]] = None,
        include_boilerplate_tags: bool = False,
        custom_boilerplate_patterns: Optional[List[str]] = None
    ) -> None:
        """Initialize the content extractor.
        
        Args:
            remove_tags: Additional tags to remove (merged with defaults).
            include_boilerplate_tags: If True, don't remove nav/header/footer.
            custom_boilerplate_patterns: Additional patterns for boilerplate detection.
        """
        self.remove_tags = self.DEFAULT_REMOVE_TAGS.copy()
        if remove_tags:
            self.remove_tags.update(remove_tags)
        
        if not include_boilerplate_tags:
            self.remove_tags.update(self.BOILERPLATE_TAGS)
        
        patterns = self.BOILERPLATE_PATTERNS.copy()
        if custom_boilerplate_patterns:
            patterns.extend(custom_boilerplate_patterns)
        
        self._boilerplate_regex = re.compile(
            "|".join(patterns),
            re.IGNORECASE
        )
    
    def extract(self, html: str, url: str = "") -> ExtractedContent:
        """Extract meaningful content from HTML.
        
        Args:
            html: The raw HTML string.
            url: The source URL (for logging).
            
        Returns:
            ExtractedContent with the cleaned content.
        """
        soup = BeautifulSoup(html, "lxml")
        
        # Extract title before cleaning
        title = self._extract_title(soup)
        
        # Remove unwanted elements
        self._remove_unwanted_elements(soup)
        
        # Find the main content area
        main_content = self._find_main_content(soup)
        
        # Clean up the content
        self._clean_content(main_content)
        
        # Extract headings for structure
        headings = self._extract_headings(main_content)
        
        # Get cleaned HTML
        content_html = str(main_content)
        
        # Calculate word count
        text_content = main_content.get_text(separator=" ", strip=True)
        word_count = len(text_content.split())
        
        logger.debug(f"Extracted {word_count} words from {url}")
        
        return ExtractedContent(
            title=title,
            content_html=content_html,
            headings=headings,
            word_count=word_count
        )
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title.
        
        Args:
            soup: BeautifulSoup object.
            
        Returns:
            The page title string.
        """
        # Try <title> tag first
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
            # Often titles have " | Site Name" - take first part
            if " | " in title:
                title = title.split(" | ")[0].strip()
            elif " - " in title:
                title = title.split(" - ")[0].strip()
            return title
        
        # Try <h1> as fallback
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        
        return "Untitled"
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements from the soup.
        
        Args:
            soup: BeautifulSoup object to modify in place.
        """
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove specified tags
        for tag_name in self.remove_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # Remove elements with boilerplate class/id patterns
        for element in soup.find_all(self._is_boilerplate):
            element.decompose()
    
    def _is_boilerplate(self, tag: Tag) -> bool:
        """Check if a tag is likely boilerplate content.
        
        Args:
            tag: The BeautifulSoup tag to check.
            
        Returns:
            True if the tag appears to be boilerplate.
        """
        if not isinstance(tag, Tag):
            return False
        
        # Check class attribute
        classes = tag.get("class", [])
        if isinstance(classes, list):
            class_str = " ".join(classes)
        else:
            class_str = str(classes)
        
        if self._boilerplate_regex.search(class_str):
            return True
        
        # Check id attribute
        tag_id = tag.get("id", "")
        if tag_id and self._boilerplate_regex.search(tag_id):
            return True
        
        # Check role attribute
        role = tag.get("role", "")
        if role in ("navigation", "banner", "contentinfo", "complementary"):
            return True
        
        return False
    
    def _find_main_content(self, soup: BeautifulSoup) -> Tag:
        """Find the main content area of the page.
        
        Args:
            soup: BeautifulSoup object.
            
        Returns:
            The main content Tag, or body if not found.
        """
        # Priority order for content containers
        # Includes WordPress, Elementor, and common CMS patterns
        selectors = [
            # Standard semantic elements
            ("main", {}),
            ("article", {}),
            ("div", {"role": "main"}),
            # WordPress patterns
            ("div", {"class": re.compile(r"entry-content", re.I)}),
            ("div", {"class": re.compile(r"post-content", re.I)}),
            ("div", {"class": re.compile(r"page-content", re.I)}),
            ("div", {"class": re.compile(r"article-content", re.I)}),
            ("div", {"class": re.compile(r"content-area", re.I)}),
            # Elementor patterns (WordPress page builder)
            ("div", {"class": re.compile(r"elementor-section-wrap", re.I)}),
            ("div", {"class": re.compile(r"elementor-widget-wrap", re.I)}),
            ("div", {"class": re.compile(r"elementor", re.I)}),
            # Generic patterns
            ("div", {"id": re.compile(r"^(main|content|article|primary)", re.I)}),
            ("div", {"class": re.compile(r"^(main|content|article|primary)", re.I)}),
            ("section", {"class": re.compile(r"content", re.I)}),
        ]
        
        for tag_name, attrs in selectors:
            element = soup.find(tag_name, attrs)
            # Lower threshold for content detection (was 100)
            if element and len(element.get_text(strip=True)) > 50:
                return element
        
        # Try to find the largest text-containing div
        body = soup.find("body")
        if body:
            divs = body.find_all("div")
            if divs:
                # Find div with most text content
                max_div = max(divs, key=lambda d: len(d.get_text(strip=True)), default=None)
                if max_div and len(max_div.get_text(strip=True)) > 50:
                    return max_div
            return body
        
        # Last resort: return the whole soup
        return soup
    
    def _clean_content(self, content: Tag) -> None:
        """Clean up the content element.
        
        Args:
            content: The Tag to clean in place.
        """
        # Remove empty elements
        for element in content.find_all():
            if isinstance(element, Tag):
                # Keep elements with meaningful content
                if element.name in ("br", "hr", "img"):
                    continue
                
                text = element.get_text(strip=True)
                if not text and not element.find(["img", "table", "pre", "code"]):
                    element.decompose()
        
        # Remove excessive whitespace in text nodes
        for text_node in content.find_all(string=True):
            if isinstance(text_node, NavigableString) and not isinstance(text_node, Comment):
                cleaned = re.sub(r"\s+", " ", str(text_node))
                text_node.replace_with(cleaned)
    
    def _extract_headings(self, content: Tag) -> List[str]:
        """Extract all headings from the content.
        
        Args:
            content: The content Tag.
            
        Returns:
            List of heading texts.
        """
        headings = []
        for level in range(1, 7):
            for heading in content.find_all(f"h{level}"):
                text = heading.get_text(strip=True)
                if text:
                    headings.append(text)
        return headings
