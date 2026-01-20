"""HTML to Markdown converter.

This module converts cleaned HTML content to well-formatted Markdown
suitable for RAG system ingestion.
"""

import logging
import re
from typing import Optional

from markdownify import markdownify as md, MarkdownConverter as BaseConverter

logger = logging.getLogger(__name__)


class RAGMarkdownConverter(BaseConverter):
    """Custom Markdown converter optimized for RAG systems.
    
    This converter extends markdownify's base converter with
    custom handling for code blocks, tables, and other elements.
    """
    
    def convert_pre(self, el, text, convert_as_inline):
        """Convert <pre> elements to fenced code blocks.
        
        Args:
            el: The BeautifulSoup element.
            text: The text content.
            convert_as_inline: Whether to convert as inline.
            
        Returns:
            Formatted code block string.
        """
        if not text:
            return ""
        
        # Try to detect language from class
        code_el = el.find("code")
        language = ""
        
        if code_el:
            classes = code_el.get("class", [])
            for cls in classes:
                if cls.startswith(("language-", "lang-")):
                    language = cls.split("-", 1)[1]
                    break
                elif cls.startswith("highlight-"):
                    language = cls.split("-", 1)[1]
                    break
        
        # Clean up the text
        code_text = text.strip()
        
        return f"\n\n```{language}\n{code_text}\n```\n\n"
    
    def convert_code(self, el, text, convert_as_inline):
        """Convert <code> elements.
        
        Args:
            el: The BeautifulSoup element.
            text: The text content.
            convert_as_inline: Whether to convert as inline.
            
        Returns:
            Formatted code string.
        """
        if not text:
            return ""
        
        # Check if inside <pre> (will be handled by convert_pre)
        if el.parent and el.parent.name == "pre":
            return text
        
        # Inline code
        return f"`{text.strip()}`"
    
    def convert_table(self, el, text, convert_as_inline):
        """Convert <table> elements to Markdown tables.
        
        Args:
            el: The BeautifulSoup element.
            text: The text content (unused, we rebuild).
            convert_as_inline: Whether to convert as inline.
            
        Returns:
            Formatted Markdown table string.
        """
        rows = []
        
        # Process header row
        thead = el.find("thead")
        if thead:
            header_row = thead.find("tr")
            if header_row:
                headers = []
                for cell in header_row.find_all(["th", "td"]):
                    headers.append(cell.get_text(strip=True))
                if headers:
                    rows.append("| " + " | ".join(headers) + " |")
                    rows.append("|" + "|".join(["---"] * len(headers)) + "|")
        
        # Process body rows
        tbody = el.find("tbody") or el
        for tr in tbody.find_all("tr"):
            cells = []
            for cell in tr.find_all(["td", "th"]):
                cells.append(cell.get_text(strip=True))
            if cells:
                # Add separator if this is first row and no header
                if len(rows) == 0:
                    rows.append("| " + " | ".join(cells) + " |")
                    rows.append("|" + "|".join(["---"] * len(cells)) + "|")
                elif len(rows) == 1:
                    # This shouldn't happen often
                    rows.append("| " + " | ".join(cells) + " |")
                else:
                    rows.append("| " + " | ".join(cells) + " |")
        
        if rows:
            return "\n\n" + "\n".join(rows) + "\n\n"
        return ""


def convert_to_markdown(
    html: str,
    heading_style: str = "ATX",
    strip_tags: bool = True,
    wrap_width: int = 0
) -> str:
    """Convert HTML content to Markdown.
    
    Args:
        html: The HTML string to convert.
        heading_style: Style for headings (ATX uses #, SETEXT uses underlines).
        strip_tags: Whether to strip unknown tags.
        wrap_width: Line wrap width (0 for no wrapping).
        
    Returns:
        The converted Markdown string.
    """
    if not html or not html.strip():
        return ""
    
    # Use custom converter
    markdown = md(
        html,
        heading_style=heading_style,
        strip=["a"] if not strip_tags else None,
        convert=["p", "h1", "h2", "h3", "h4", "h5", "h6", 
                 "ul", "ol", "li", "blockquote", "pre", "code",
                 "strong", "b", "em", "i", "table", "tr", "th", "td",
                 "br", "hr", "img"],
        escape_asterisks=False,
        escape_underscores=False,
    )
    
    # Post-processing cleanup
    markdown = clean_markdown(markdown)
    
    return markdown


def clean_markdown(text: str) -> str:
    """Clean up Markdown text for better readability.
    
    Args:
        text: The Markdown text to clean.
        
    Returns:
        Cleaned Markdown text.
    """
    if not text:
        return ""
    
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Remove excessive blank lines (more than 2 consecutive)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Remove trailing whitespace on each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    
    # Ensure headings have blank line before them
    text = re.sub(r"([^\n])\n(#{1,6}\s)", r"\1\n\n\2", text)
    
    # Ensure code blocks have blank lines around them
    text = re.sub(r"([^\n])\n```", r"\1\n\n```", text)
    text = re.sub(r"```\n([^\n])", r"```\n\n\1", text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Ensure file ends with newline
    if text and not text.endswith("\n"):
        text += "\n"
    
    return text


def split_into_sections(
    markdown: str,
    max_section_length: int = 2000
) -> list[dict]:
    """Split Markdown into logical sections for chunking.
    
    This function splits content at heading boundaries,
    which is ideal for RAG embedding and retrieval.
    
    Args:
        markdown: The Markdown text to split.
        max_section_length: Maximum characters per section.
        
    Returns:
        List of section dictionaries with 'heading' and 'content' keys.
    """
    sections = []
    
    # Split by headings (keeping the heading with its content)
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    
    # Find all heading positions
    headings = list(heading_pattern.finditer(markdown))
    
    if not headings:
        # No headings - return as single section
        return [{"heading": "", "content": markdown.strip(), "level": 0}]
    
    # Add content before first heading if any
    first_heading_pos = headings[0].start()
    if first_heading_pos > 0:
        intro_content = markdown[:first_heading_pos].strip()
        if intro_content:
            sections.append({
                "heading": "",
                "content": intro_content,
                "level": 0
            })
    
    # Process each heading section
    for i, match in enumerate(headings):
        level = len(match.group(1))
        heading_text = match.group(2)
        
        # Get content until next heading or end
        start = match.end()
        if i + 1 < len(headings):
            end = headings[i + 1].start()
        else:
            end = len(markdown)
        
        content = markdown[start:end].strip()
        
        # Include the heading in content for context
        full_content = f"{'#' * level} {heading_text}\n\n{content}"
        
        sections.append({
            "heading": heading_text,
            "content": full_content,
            "level": level
        })
    
    # Split oversized sections if needed
    final_sections = []
    for section in sections:
        if len(section["content"]) <= max_section_length:
            final_sections.append(section)
        else:
            # Split by paragraphs
            paragraphs = section["content"].split("\n\n")
            current_chunk = ""
            chunk_num = 0
            
            for para in paragraphs:
                if len(current_chunk) + len(para) + 2 <= max_section_length:
                    current_chunk += ("\n\n" if current_chunk else "") + para
                else:
                    if current_chunk:
                        final_sections.append({
                            "heading": f"{section['heading']} (Part {chunk_num + 1})",
                            "content": current_chunk,
                            "level": section["level"]
                        })
                        chunk_num += 1
                    current_chunk = para
            
            if current_chunk:
                final_sections.append({
                    "heading": f"{section['heading']} (Part {chunk_num + 1})" if chunk_num > 0 else section["heading"],
                    "content": current_chunk,
                    "level": section["level"]
                })
    
    return final_sections
