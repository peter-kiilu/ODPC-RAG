"""Rate limiter for respectful web crawling.

This module provides rate limiting functionality to ensure
crawlers don't overwhelm target servers.
"""

import logging
import time
from threading import Lock
from typing import Dict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Per-domain rate limiter using a simple delay mechanism.
    
    This class tracks the last request time per domain and ensures
    a minimum delay between consecutive requests to the same domain.
    
    Attributes:
        default_delay: Default delay between requests in seconds.
        domain_delays: Optional per-domain delay overrides.
    """
    
    def __init__(self, default_delay: float = 1.0) -> None:
        """Initialize the rate limiter.
        
        Args:
            default_delay: Default delay between requests in seconds.
        """
        self.default_delay = default_delay
        self._last_request: Dict[str, float] = {}
        self._domain_delays: Dict[str, float] = {}
        self._lock = Lock()
    
    def set_domain_delay(self, domain: str, delay: float) -> None:
        """Set a custom delay for a specific domain.
        
        Args:
            domain: The domain to set the delay for.
            delay: The delay in seconds.
        """
        with self._lock:
            self._domain_delays[domain] = delay
    
    def get_delay(self, domain: str) -> float:
        """Get the configured delay for a domain.
        
        Args:
            domain: The domain to check.
            
        Returns:
            The delay in seconds for this domain.
        """
        with self._lock:
            return self._domain_delays.get(domain, self.default_delay)
    
    def wait(self, domain: str) -> float:
        """Wait if necessary to respect rate limits.
        
        This method blocks until enough time has passed since
        the last request to the same domain.
        
        Args:
            domain: The domain being requested.
            
        Returns:
            The actual time waited in seconds.
        """
        with self._lock:
            now = time.time()
            delay = self._domain_delays.get(domain, self.default_delay)
            last_request = self._last_request.get(domain, 0)
            
            time_since_last = now - last_request
            wait_time = max(0, delay - time_since_last)
            
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
                # Release lock while sleeping
                self._lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self._lock.acquire()
            
            # Update last request time
            self._last_request[domain] = time.time()
            
            return wait_time
    
    def record_request(self, domain: str) -> None:
        """Record that a request was made to a domain.
        
        Use this when you've made a request without calling wait().
        
        Args:
            domain: The domain that was requested.
        """
        with self._lock:
            self._last_request[domain] = time.time()
    
    def time_until_allowed(self, domain: str) -> float:
        """Get the time until the next request is allowed.
        
        Args:
            domain: The domain to check.
            
        Returns:
            Seconds until the next request is allowed (0 if allowed now).
        """
        with self._lock:
            now = time.time()
            delay = self._domain_delays.get(domain, self.default_delay)
            last_request = self._last_request.get(domain, 0)
            
            time_since_last = now - last_request
            return max(0, delay - time_since_last)
