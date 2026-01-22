"""
    To run the crawler, run the python script `python crawler/crawer.py`
    Incase of an error that stops execution, rerun again, the crawler will use the saved state to continue from where it left off
    To start afresh, delete the state file
"""


import os
import re
import requests
from bs4 import BeautifulSoup
import html2text
import time
from urllib.parse import urljoin, urlparse
from collections import deque
from urllib.robotparser import RobotFileParser
import hashlib
import json
import logging
from .config import Config
from .utils import is_valid_url, normalize_url

# Initialize HTML to Markdown converter
html_converter = html2text.HTML2Text()
html_converter.ignore_links = False
html_converter.ignore_images = False
html_converter.body_width = 0

os.makedirs(Config.DOCS_DIR, exist_ok=True)
os.makedirs(Config.MD_DIR, exist_ok=True)



class Crawler:
    def __init__(self, start_url, max_pages, delay=2.0):
        self.start = normalize_url(start_url)
        self.visited = set() # Set of visited pages
        self.q = deque() # A queue of pages to visit and crawl. Links in navbar are prioritized.
        # Initialize the queue
        self.q.append(self.start)
        self.max_pages = max_pages
        self.content_hashes = set() # Track duplicate content
        self.delay = delay
        self.last_request_time = 0
        self.session = self._create_session()

        # Respect robots.txt files
        # self.robot_parser = RobotFileParser()
        # self.robot_parser.set_url(urljoin(start_url, '/robots.txt'))
        # try:
        #     self.robot_parser.read()
        # except:
        #     logging.info("Could not read robots.txt")


    def _create_session(self):
        """Create configured session"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        return session
        
        
    def crawl(self, max_retries=3):
        self.load_state() # load saved state, start fresh if no saved state
        try:
            while self.q and len(self.visited) < self.max_pages:
                # Add rate limiting
                elapsed = time.time() - self.last_request_time
                if elapsed < self.delay:
                    time.sleep(self.delay - elapsed)
                    
                # pop the first page in the queue
                page = self.q.popleft()
                if page in self.visited or not is_valid_url(page, self.start):
                    continue
                
                logging.info(f"Crawling: {page}")

                html_content = self._fetch_page(page, max_retries)
                self.last_request_time = time.time()

                if html_content:
                    self.visited.add(page)
                    self.discover_links(html_content, page) # Find all the links in a given page

                # Save state after every 10 pages
                if len(self.visited) % 10 == 0:
                    self.save_state()
                    logging.info(f"Progress: {len(self.visited)}/{self.max_pages} pages")
        
        except KeyboardInterrupt:
            logging.info("crawling inttterupted by user")
            self.save_state()
            raise
        except Exception as e:
            logging.error(f"Critical Error: {e}")
            self.save_state()
            raise
        finally:
            self.session.close()
            logging.info(f"Crawl complete. Visited {len(self.visited)} pages")

    def _fetch_page(self, page, max_retries=3):
        """Retreive html content for a given page, retry incase of timeouts"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(page, timeout=Config.TIMEOUT)
                response.raise_for_status() # checking for errors 404...

                # Check content type
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    logging.info(f"Skipping non-HTML content: {page}")
                    break

                return response.text

            except requests.exceptions.Timeout:
                logging.warning(f"Timeout on {page} (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    logging.error(f"Failed after {max_retries} attempts: {page}")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [404, 403, 410]:
                    logging.info(f"Skipping {page}: {e.response.status_code}")
                    break  # Don't retry for these
                logging.warning(f"HTTP error on {page}: {e}")
            except Exception as e:
                logging.warning(f"Error crawling {page}: {e}")

            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

        logging.error(f"Failed to fetch {page} after {max_retries} attempts")
        return None
       
    # def is_allowed(self, url):
    #     return self.robot_parser.can_fetch("*", url)

    def save_state(self):
        """Save state for resuming incase of a crash"""
        state = {
            'visited': list(self.visited),
            'queue': list(self.q),
            'content_hashes': list(self.content_hashes)
        }
        with open('crawler_state.json', 'w') as f:
            json.dump(state, f)
        logging.debug("State saved")

    def load_state(self):
        """Load previous crawler state"""
        try:
            with open('crawler_state.json', 'r') as f:
                state = json.load(f)
                self.visited = set(state['visited'])
                self.q = deque(state['queue'])
                self.content_hashes = set(state['content_hashes'])
            logging.info(f"Resumed: {len(self.visited)} pages visited")
        except FileNotFoundError:
            logging.info("No Previous State found, starting fresh") 
        
    
    def discover_links(self, html_content, current_url):
        """
        Here we first find all the links that are in the navbar, and add them to the queue.
        After that we find the links that are in the specific pages.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Save the page immediately
        self.save_markdown(html_content, current_url)

        # If in the homepage, focus on the navbar first
        container = soup.find('div', class_="jkit-menu-container") if current_url == self.start else soup

        if not container:
            container = soup

        for link in container.find_all('a', href=True):
            try:
                href = link["href"]
                
                # Skip obviously problematic URLs before urljoin
                if "[" in href or "]" in href:
                    continue
                    
                url = urljoin(current_url, href)
                clean_url = normalize_url(url)

                # Skip invalid URLs that couldn't be normalized
                if clean_url is None:
                    continue

                if self.is_excluded(clean_url):
                    continue

                if any(url.endswith(ext) for ext in Config.DOCUMENT_EXTENSIONS): # Do not use the clean url here
                    self.download_files(url)
                    continue

                if is_valid_url(clean_url, self.start) and clean_url not in self.visited:
                        if clean_url not in self.q:
                            self.q.append(clean_url)
            except ValueError as e:
                logging.debug(f"Skipping invalid URL: {link.get('href', 'unknown')} - {e}")
                continue
            except Exception as e:
                logging.debug(f"Error processing link: {e}")
                continue

    
    def is_excluded(self, url):
        # Check if there are any banned patterns or extensions
        for pattern in Config.EXCLUDE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def save_markdown(self, html, url):
        soup = BeautifulSoup(html, "html.parser")

        # Find main content
        selectors = [
            ('div', {'class': 'page-content'}),
            ('main', {'id': 'content'}),
            ('article', {}),
            ('main', {}),
        ]

        for tag, attrs in selectors:
            content = soup.find(tag, attrs)
            if content:
                # Check if it has substantial content
                text = content.get_text(strip=True)
                if len(text) > 200:  # At least 200 chars
                    logging.debug(f"Found content in: <{tag} {attrs}>")

        # extract title for the filename
        title = soup.title.string if soup.title else f"{url}"
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_desc_tag.get("content", "") if meta_desc_tag else ""
        clean_title = re.sub(r'[^\w\s-]', '', title).strip().replace(" ", "_")
        clean_title = clean_title[:200]

        markdown_content = html_converter.handle(str(content))

        # Check for duplicates
        content_hash = hashlib.md5(markdown_content.encode()).hexdigest()
        if content_hash in self.content_hashes:
            logging.info(f"Duplicate content detected, skipping: {url}")
            return
        self.content_hashes.add(content_hash)

        filename = f"{clean_title}.md"
        filepath = os.path.join(Config.MD_DIR, filename)
        counter = 1
        while os.path.exists(filepath):
            filename = f"{clean_title}_{counter}.md" # Avoid file name conflicts, if they have the same name
            filepath = os.path.join(Config.MD_DIR, filename)
            counter += 1

        front = f"""---
                title: "{title}"
                source: "{url}"
                description: "{meta_desc}"
                date_crawled: "{time.strftime('%Y-%m-%d %H:%M:%S')}"
                ---

                """
        with open(os.path.join(Config.MD_DIR, filename), "w", encoding="utf-8") as f:
            f.write(front + markdown_content)

    def download_files(self, url):
        try:
            # Get filename and it's extension
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)

            filepath = os.path.join(Config.DOCS_DIR, filename)

            if os.path.exists(filepath):
                return
            
            # Stream the download
            response = self.session.get(url, timeout=20, stream=True)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8152):
                    if chunk:
                        f.write(chunk)
            
            logging.info(f"Saved Document: {filename}")
        except Exception as e:
            logging.error(f"Failed to download document {url}: {e}")


def setup_logging():
    """Setup logging configuration"""
    log_dir = os.path.join(Config.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'crawler.log')),
            logging.StreamHandler()
        ]
    )


if __name__ == "__main__":
    setup_logging()
    crawler = Crawler("https://www.odpc.go.ke/", 10000)
    crawler.crawl()