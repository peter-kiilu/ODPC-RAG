import re
import os
import hashlib
from urllib.parse import urlparse

def normalize_url(url):
    # Normalize urls to remove the trailing '/' and # section names
    url = url.split('#')[0]
    
    url = url.rstrip('/')
    
    # owercase everything to be safe
    return url.lower()

def is_valid_url(url, start_url):
    if not url:
        return False
    
    # FIX: Block URLs with brackets that trigger IPv6 errors
    if "[" in url or "]" in url:
        return False

    try:
        parsed = urlparse(url)
        base_parsed = urlparse(start_url)
        
        # Ensure it's not a mailto:, tel:, or javascript: link
        if parsed.scheme not in ["http", "https"]:
            return False
            
        return parsed.netloc == base_parsed.netloc
    except:
        return False