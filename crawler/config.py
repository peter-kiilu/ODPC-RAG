# Configuration
import os

class Config:
    # Crawler settings
    MAX_PAGES = 1000
    DELAY = 2.0  # seconds between requests
    MAX_RETRIES = 3
    TIMEOUT = 30
    
    # Directories
    BASE_DIR = "data"
    DOCS_DIR = os.path.join(BASE_DIR, "documents")
    MD_DIR = os.path.join(BASE_DIR, "markdown")

    # File extensions
    DOCUMENT_EXTENSIONS = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]
    
    # Exclude patterns
    EXCLUDE_PATTERNS = [
        r"\.xml$", r"\.rss$", r"\.json$", r"\.js$", r"\.css$",
        r"/cdn-cgi/", r"/search", r"/account", r"/cart", r"/checkout",
        r"\/tagged\/", r"\/users\/", r"\/login", r"\/signup", r"\/logout",
        r"\.mp3$", r"\.wav$", r"\.mp4$", r"\.webp$", r"\.svg$", r"\.ico$",
        # Strict Image Exclusion
        r"\.(jpg|jpeg|png|gif|bmp|tiff|jfif)$",
        # WordPress specific
        r"/wp-admin/", r"/wp-includes/", r"/wp-content/plugins/",
        r"/wp-content/themes/.*\.(css|js)$",
        r"/feed/", r"/trackback/", r"\?replytocom=", r"/page/\d+/"
    ]

    # In your Config class
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
