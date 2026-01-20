"""Browser-based page fetcher using Playwright.

This module provides asynchronous page fetching using a headless browser,
enabling extraction of JavaScript-rendered content.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, List

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of a page fetch operation.
    
    Attributes:
        url: The final URL after redirects.
        html: The rendered HTML content.
        status: HTTP status code.
        error: Error message if failed.
        text_content: Plain text content extracted via JS.
        title: Page title.
        headings: List of heading texts.
    """
    url: str
    html: str
    status: int
    error: Optional[str] = None
    text_content: str = ""
    title: str = ""
    headings: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Check if fetch was successful."""
        return self.error is None and 200 <= self.status < 400


class BrowserFetcher:
    """Headless browser-based page fetcher.
    
    Uses Playwright to render JavaScript-heavy pages and extract
    the fully rendered HTML content.
    """
    
    def __init__(
        self,
        user_agent: str = "RAGCrawler/1.0 (Playwright)",
        timeout: int = 30000,
        wait_after_load: int = 3000,
        headless: bool = True
    ) -> None:
        """Initialize the browser fetcher."""
        self.user_agent = user_agent
        self.timeout = timeout
        self.wait_after_load = wait_after_load
        self.headless = headless
        
        self._browser: Optional[Browser] = None
        self._playwright = None
    
    async def start(self) -> None:
        """Start the browser instance."""
        if self._browser is not None:
            return
        
        logger.info("Starting Playwright browser...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless
        )
        logger.info("Browser started successfully")
    
    async def stop(self) -> None:
        """Stop the browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        
        logger.info("Browser stopped")
    
    async def _scroll_page(self, page: Page) -> None:
        """Scroll through the page to trigger lazy loading."""
        try:
            height = await page.evaluate("document.body.scrollHeight")
            viewport_height = 1080
            
            current = 0
            while current < height:
                await page.evaluate(f"window.scrollTo(0, {current})")
                await page.wait_for_timeout(200)
                current += viewport_height // 2
                height = await page.evaluate("document.body.scrollHeight")
            
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
            
        except Exception as e:
            logger.debug(f"Scroll failed: {e}")
    
    async def _extract_content_js(self, page: Page) -> dict:
        """Extract content directly using JavaScript.
        
        This is a fallback for sites where HTML extraction doesn't work well.
        """
        extraction_script = """
        () => {
            // Get title
            const title = document.title || '';
            
            // Get all headings
            const headings = [];
            document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
                const text = h.innerText.trim();
                if (text) headings.push(text);
            });
            
            // Find main content area
            const mainSelectors = [
                'main',
                'article', 
                '.page-content',
                '.entry-content',
                '.post-content',
                '.elementor-section-wrap',
                '.site-main',
                '#content',
                '.content'
            ];
            
            let mainContent = null;
            for (const sel of mainSelectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText.trim().length > 100) {
                    mainContent = el;
                    break;
                }
            }
            
            // Fallback to body
            if (!mainContent) {
                mainContent = document.body;
            }
            
            // Extract text with structure
            const extractText = (element) => {
                const blocks = [];
                const walkNodes = (el) => {
                    // Skip hidden elements and boilerplate
                    const tag = el.tagName?.toLowerCase();
                    if (['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript'].includes(tag)) {
                        return;
                    }
                    
                    // Check for hidden
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') {
                        return;
                    }
                    
                    // Block-level elements that contain text
                    if (['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'blockquote', 'pre'].includes(tag)) {
                        const text = el.innerText.trim();
                        if (text) {
                            if (tag.startsWith('h')) {
                                const level = parseInt(tag[1]);
                                blocks.push('#'.repeat(level) + ' ' + text);
                            } else if (tag === 'li') {
                                blocks.push('• ' + text);
                            } else if (tag === 'blockquote') {
                                blocks.push('> ' + text);
                            } else if (tag === 'pre') {
                                blocks.push('```\\n' + text + '\\n```');
                            } else {
                                blocks.push(text);
                            }
                        }
                        return; // Don't recurse into these
                    }
                    
                    // Recurse into container elements
                    for (const child of el.children) {
                        walkNodes(child);
                    }
                };
                
                walkNodes(element);
                return blocks.join('\\n\\n');
            };
            
            const textContent = extractText(mainContent);
            
            return {
                title: title,
                headings: headings,
                textContent: textContent,
                wordCount: textContent.split(/\\s+/).filter(w => w).length
            };
        }
        """
        
        try:
            result = await page.evaluate(extraction_script)
            return result
        except Exception as e:
            logger.warning(f"JS extraction failed: {e}")
            return {"title": "", "headings": [], "textContent": "", "wordCount": 0}
    
    async def fetch(self, url: str) -> FetchResult:
        """Fetch and render a page with content extraction."""
        if self._browser is None:
            await self.start()
        
        page: Optional[Page] = None
        context = None
        
        try:
            context = await self._browser.new_context(
                user_agent=self.user_agent,
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            
            response = await page.goto(
                url,
                timeout=self.timeout,
                wait_until="domcontentloaded"
            )
            
            if response is None:
                return FetchResult(
                    url=url,
                    html="",
                    status=0,
                    error="No response received"
                )
            
            # Wait for network idle
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeout:
                logger.debug(f"Network idle timeout for {url}")
            
            # Scroll to trigger lazy loading
            await self._scroll_page(page)
            
            # Wait for JS rendering
            await page.wait_for_timeout(self.wait_after_load)
            
            # Wait for Elementor content
            try:
                await page.wait_for_selector(".elementor-widget-container", timeout=3000)
            except PlaywrightTimeout:
                pass
            
            # Get final URL
            final_url = page.url
            
            # Get HTML
            html = await page.content()
            
            # Extract content using JavaScript
            extracted = await self._extract_content_js(page)
            
            logger.debug(f"Fetched {url} -> {extracted.get('wordCount', 0)} words")
            
            return FetchResult(
                url=final_url,
                html=html,
                status=response.status,
                text_content=extracted.get("textContent", ""),
                title=extracted.get("title", ""),
                headings=extracted.get("headings", [])
            )
            
        except PlaywrightTimeout:
            logger.warning(f"Timeout fetching {url}")
            return FetchResult(url=url, html="", status=0, error="Page load timeout")
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return FetchResult(url=url, html="", status=0, error=str(e))
            
        finally:
            if page:
                await page.close()
            if context:
                await context.close()
    
    async def fetch_many(self, urls: list[str], concurrency: int = 3) -> list[FetchResult]:
        """Fetch multiple pages concurrently."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def fetch_with_limit(url: str) -> FetchResult:
            async with semaphore:
                return await self.fetch(url)
        
        tasks = [fetch_with_limit(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    async def __aenter__(self) -> "BrowserFetcher":
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()


def fetch_page_sync(url: str, timeout: int = 30000) -> FetchResult:
    """Synchronous wrapper for fetching a single page."""
    async def _fetch():
        async with BrowserFetcher(timeout=timeout) as fetcher:
            return await fetcher.fetch(url)
    
    return asyncio.run(_fetch())
