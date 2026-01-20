"""RAG Web Crawler - Command Line Interface.

A production-grade web crawler for RAG system content ingestion.
Supports both static pages (requests) and JavaScript-rendered pages (Playwright).

Usage:
    # Static pages (default)
    python main.py --url https://example.com --depth 3

    # JavaScript-heavy sites (use --browser)
    python main.py --url https://www.odpc.go.ke --depth 2 --browser
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from rag_crawler.config import CrawlerConfig


def setup_logging(verbose: bool = False, log_file: str = None) -> None:
    """Configure logging for the crawler."""
    level = logging.DEBUG if verbose else logging.INFO
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="RAG Web Crawler - Extract website content for RAG ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Static website
  %(prog)s --url https://docs.python.org/3/ --depth 2
  
  # JavaScript-heavy website (use browser)
  %(prog)s --url https://www.odpc.go.ke --depth 2 --browser
  
  # Custom output and rate limit
  %(prog)s --url https://example.com --output ./data --rate-limit 0.5
        """
    )
    
    parser.add_argument(
        "--url", "-u",
        required=True,
        help="Base URL to start crawling from"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="Output directory for Markdown files (default: output)"
    )
    
    parser.add_argument(
        "--depth", "-d",
        type=int,
        default=3,
        help="Maximum crawl depth from base URL (default: 3)"
    )
    
    parser.add_argument(
        "--rate-limit", "-r",
        type=float,
        default=1.0,
        help="Minimum seconds between requests (default: 1.0)"
    )
    
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--browser", "-b",
        action="store_true",
        help="Use headless browser (Playwright) for JavaScript-heavy sites"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window (only with --browser)"
    )
    
    parser.add_argument(
        "--no-robots",
        action="store_true",
        help="Ignore robots.txt rules (not recommended)"
    )
    
    parser.add_argument(
        "--user-agent",
        default="RAGCrawler/1.0 (+https://github.com/rag-crawler)",
        help="User agent string for requests"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (debug) logging"
    )
    
    parser.add_argument(
        "--log-file",
        help="Write logs to file"
    )
    
    parser.add_argument(
        "--download-files",
        action="store_true",
        help="Download PDFs and documents linked from pages"
    )
    
    return parser.parse_args()


def progress_callback(crawled: int, total_seen: int, current_url: str) -> None:
    """Print crawl progress."""
    display_url = current_url
    if len(display_url) > 60:
        display_url = display_url[:57] + "..."
    
    print(f"\r[{crawled}/{total_seen}] Crawling: {display_url:<65}", end="", flush=True)


def run_static_crawler(config: CrawlerConfig) -> dict:
    """Run the static (requests-based) crawler."""
    from rag_crawler.crawler import WebCrawler
    
    crawler = WebCrawler(config)
    stats = crawler.crawl(progress_callback=progress_callback)
    return stats, crawler.storage.get_stats()


def run_browser_crawler(config: CrawlerConfig, headless: bool = True, download_files: bool = False) -> dict:
    """Run the browser-based (Playwright) crawler."""
    from rag_crawler.async_crawler import AsyncWebCrawler
    
    async def _crawl():
        crawler = AsyncWebCrawler(config, headless=headless, download_files=download_files)
        stats = await crawler.crawl(progress_callback=progress_callback)
        storage_stats = crawler.storage.get_stats()
        # Add file download stats
        if crawler.file_downloader:
            storage_stats['files_downloaded'] = crawler.file_downloader.download_count
            storage_stats['downloads_dir'] = str(crawler.file_downloader.downloads_dir)
        # Add link extraction stats
        link_stats = crawler.link_extractor.get_statistics()
        storage_stats['link_stats'] = link_stats
        return stats, storage_stats
    
    return asyncio.run(_crawl())


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    setup_logging(verbose=args.verbose, log_file=args.log_file)
    logger = logging.getLogger(__name__)
    
    mode = "Browser (Playwright)" if args.browser else "Static (Requests)"
    
    print(f"\n{'='*60}")
    print("RAG Web Crawler")
    print(f"{'='*60}")
    print(f"URL:        {args.url}")
    print(f"Depth:      {args.depth}")
    print(f"Output:     {args.output}")
    print(f"Rate Limit: {args.rate_limit}s")
    print(f"Mode:       {mode}")
    print(f"{'='*60}\n")
    
    try:
        config = CrawlerConfig(
            base_url=args.url,
            output_dir=Path(args.output),
            max_depth=args.depth,
            rate_limit=args.rate_limit,
            timeout=args.timeout,
            respect_robots_txt=not args.no_robots,
            user_agent=args.user_agent
        )
        
        if args.browser:
            stats, storage_stats = run_browser_crawler(
                config,
                headless=not args.no_headless,
                download_files=args.download_files
            )
        else:
            stats, storage_stats = run_static_crawler(config)
        
        print("\n\n")
        print(f"{'='*60}")
        print("Crawl Complete!")
        print(f"{'='*60}")
        print(f"Pages Crawled:  {stats.pages_crawled}")
        print(f"Pages Saved:    {stats.pages_saved}")
        print(f"Pages Skipped:  {stats.pages_skipped} (unchanged)")
        print(f"Pages Failed:   {stats.pages_failed}")
        print(f"Total Words:    {stats.total_words:,}")
        print(f"Duration:       {stats.duration_seconds:.1f} seconds")
        print(f"{'='*60}")
        
        print(f"\nOutput Directory: {args.output}")
        print(f"Files Created:    {storage_stats['file_count']}")
        print(f"Total Size:       {storage_stats['total_size_mb']} MB")
        
        if stats.errors:
            print(f"\n{len(stats.errors)} errors occurred (see log for details)")
        
        # Show download info
        if 'files_downloaded' in storage_stats and storage_stats['files_downloaded'] > 0:
            print(f"\nPDFs/Documents Downloaded: {storage_stats['files_downloaded']}")
            print(f"Downloads Directory: {storage_stats['downloads_dir']}")
        
        # Show link extraction info
        if 'link_stats' in storage_stats:
            ls = storage_stats['link_stats']
            print(f"\nLinks Extracted (saved to links.json):")
            print(f"  Internal Links: {ls.get('total_internal_links', 0)}")
            print(f"  External Links: {ls.get('total_external_links', 0)}")
            print(f"  Video Links:    {ls.get('total_video_links', 0)}")
            print(f"  PDF Links:      {ls.get('total_pdf_links', 0)}")
            if ls.get('total_social_platforms'):
                print(f"  Social Media:   {', '.join(ls['total_social_platforms'])}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nCrawl interrupted by user")
        return 1
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.exception(f"Fatal error: {e}")
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
