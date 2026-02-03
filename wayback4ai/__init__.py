"""
Wayback4AI - A data harvester for the Internet Archive.

Combines Wayback Machine's CDX/Availability APIs with Crawl4AI to capture,
extract, and convert historical web pages into LLM-ready Markdown.
"""

from .wayback import get_wayback_metadata

__version__ = "0.1.0"
__all__ = [
    "get_wayback_metadata",
]
