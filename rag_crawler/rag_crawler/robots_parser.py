"""Robots.txt parser and checker.

This module provides functionality to fetch, parse, and check robots.txt
rules for respectful web crawling.
"""

import logging
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Checker for robots.txt compliance.
    
    This class fetches and caches robots.txt files per domain,
    and provides methods to check if a URL can be crawled.
    
    Attributes:
        user_agent: The user agent string to check rules against.
        timeout: Request timeout for fetching robots.txt.
        cache: Dictionary cache of parsed robots.txt per domain.
    """
    
    def __init__(self, user_agent: str, timeout: int = 10) -> None:
        """Initialize the robots checker.
        
        Args:
            user_agent: The user agent string to use for checking rules.
            timeout: Timeout in seconds for fetching robots.txt.
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self._cache: Dict[str, Optional[RobotFileParser]] = {}
    
    def _get_robots_url(self, url: str) -> str:
        """Get the robots.txt URL for a given page URL.
        
        Args:
            url: The page URL.
            
        Returns:
            The robots.txt URL for the domain.
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    def _fetch_robots(self, url: str) -> Optional[RobotFileParser]:
        """Fetch and parse robots.txt for a URL's domain.
        
        Args:
            url: A page URL from the domain.
            
        Returns:
            A RobotFileParser if successful, None if robots.txt doesn't exist.
        """
        robots_url = self._get_robots_url(url)
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Check cache first
        if domain in self._cache:
            return self._cache[domain]
        
        try:
            response = requests.get(
                robots_url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent}
            )
            
            if response.status_code == 200:
                rp = RobotFileParser()
                rp.parse(response.text.splitlines())
                self._cache[domain] = rp
                logger.debug(f"Loaded robots.txt for {domain}")
                return rp
            else:
                # No robots.txt or error - allow all
                logger.debug(f"No robots.txt for {domain} (status {response.status_code})")
                self._cache[domain] = None
                return None
                
        except requests.RequestException as e:
            logger.warning(f"Error fetching robots.txt for {domain}: {e}")
            self._cache[domain] = None
            return None
    
    def can_fetch(self, url: str) -> bool:
        """Check if a URL can be fetched according to robots.txt.
        
        Args:
            url: The URL to check.
            
        Returns:
            True if the URL can be fetched, False otherwise.
        """
        rp = self._fetch_robots(url)
        
        if rp is None:
            # No robots.txt - allow all
            return True
        
        return rp.can_fetch(self.user_agent, url)
    
    def get_crawl_delay(self, url: str) -> Optional[float]:
        """Get the crawl delay specified in robots.txt.
        
        Args:
            url: A URL from the domain to check.
            
        Returns:
            The crawl delay in seconds, or None if not specified.
        """
        rp = self._fetch_robots(url)
        
        if rp is None:
            return None
        
        try:
            delay = rp.crawl_delay(self.user_agent)
            return float(delay) if delay else None
        except Exception:
            return None
    
    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._cache.clear()
