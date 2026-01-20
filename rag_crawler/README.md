# RAG Web Crawler

A production-grade Python web crawler designed for RAG (Retrieval Augmented Generation) system content ingestion. It extracts meaningful content from websites, converts it to clean Markdown, and prepares it for vector embedding and semantic retrieval.

## Features

- **Recursive Web Crawling**: Crawls all internal links within the same domain
- **Smart Content Extraction**: Removes boilerplate (navigation, ads, footers) using BeautifulSoup
- **Markdown Conversion**: Converts HTML to clean, structured Markdown using markdownify
- **Change Detection**: SHA-256 content hashing - only saves changed content
- **RAG-Ready Output**: YAML front matter with metadata for traceability
- **Respectful Crawling**: robots.txt compliance and configurable rate limiting
- **Error Handling**: Graceful handling of timeouts, redirects, and HTTP errors

## Installation

```bash
cd rag_crawler
pip install -r requirements.txt
```

## Quick Start

```bash
# Basic crawl
python main.py --url https://docs.python.org/3/library/urllib.html --depth 2

# With custom output and rate limit
python main.py --url https://example.com --output ./data --rate-limit 0.5 --depth 3

# Verbose mode with log file
python main.py --url https://example.com -v --log-file crawl.log
```

## Command Line Options

| Option         | Short | Default    | Description                         |
| -------------- | ----- | ---------- | ----------------------------------- |
| `--url`        | `-u`  | (required) | Base URL to start crawling          |
| `--output`     | `-o`  | `output`   | Output directory for Markdown files |
| `--depth`      | `-d`  | `3`        | Maximum crawl depth                 |
| `--rate-limit` | `-r`  | `1.0`      | Seconds between requests            |
| `--timeout`    | `-t`  | `30`       | Request timeout in seconds          |
| `--no-robots`  |       | `False`    | Ignore robots.txt (not recommended) |
| `--verbose`    | `-v`  | `False`    | Enable debug logging                |
| `--log-file`   |       |            | Write logs to file                  |

## Output Format

Each crawled page is saved as a Markdown file with YAML front matter:

```markdown
---
source_url: https://example.com/docs/getting-started
title: Getting Started Guide
crawl_timestamp: 2026-01-20T06:30:00Z
content_hash: a3f2b8c9d1e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8
word_count: 1250
headings:
  - Getting Started Guide
  - Installation
  - Configuration
---

# Getting Started Guide

Welcome to the documentation...
```

## Architecture

```
rag_crawler/
├── config.py           # Configuration dataclasses
├── url_utils.py        # URL normalization and deduplication
├── robots_parser.py    # robots.txt compliance
├── rate_limiter.py     # Request throttling
├── extractor.py        # BeautifulSoup content extraction
├── converter.py        # HTML to Markdown conversion
├── change_detector.py  # Content hash comparison
├── storage.py          # Markdown file storage
└── crawler.py          # Main crawler orchestration
```

## Programmatic Usage

```python
from rag_crawler.crawler import crawl_website

# Simple usage
stats = crawl_website(
    url="https://example.com/docs",
    output_dir="./output",
    max_depth=3,
    rate_limit=1.0
)

print(f"Crawled {stats.pages_crawled} pages")
print(f"Saved {stats.pages_saved} files")
```

### Advanced Usage

```python
from pathlib import Path
from rag_crawler.config import CrawlerConfig
from rag_crawler.crawler import WebCrawler

config = CrawlerConfig(
    base_url="https://docs.example.com",
    output_dir=Path("./data"),
    max_depth=5,
    rate_limit=0.5,
    timeout=60,
    respect_robots_txt=True,
    excluded_patterns={"/login", "/admin", "/search"}
)

crawler = WebCrawler(config)
stats = crawler.crawl()
```

## RAG Integration

The output is designed for easy chunking and embedding:

1. **Section-Based Structure**: Headings preserved for semantic chunking
2. **Metadata Traceability**: Source URL in front matter for citation
3. **Content Hash**: Enables incremental re-crawling
4. **Clean Markdown**: No HTML artifacts or navigation remnants

### Example: Loading for Embeddings

```python
import yaml
from pathlib import Path

def load_documents(output_dir: str):
    """Load crawled documents for RAG ingestion."""
    documents = []

    for filepath in Path(output_dir).glob("*.md"):
        with open(filepath) as f:
            content = f.read()

        # Parse front matter
        _, front_matter, body = content.split("---", 2)
        metadata = yaml.safe_load(front_matter)

        documents.append({
            "content": body.strip(),
            "metadata": metadata
        })

    return documents
```

## Best Practices

1. **Start with low depth**: Test with `--depth 1` before deep crawls
2. **Respect rate limits**: Default 1s delay is a good starting point
3. **Check robots.txt**: Don't use `--no-robots` on production sites
4. **Monitor logs**: Use `-v` or `--log-file` for debugging
5. **Incremental crawling**: Re-run to only update changed content

## Common Pitfalls

- **Infinite loops**: Avoided via URL normalization and deduplication
- **JavaScript content**: Static crawler - won't execute JS (use Playwright for SPAs)
- **Login-required pages**: Won't work - add session/cookie support if needed
- **Very large sites**: Set appropriate depth limits

## License

MIT License
