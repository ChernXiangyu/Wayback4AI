"""
Wayback Machine CDX API client for collecting archived URLs.

This module provides a simple interface for collecting Wayback Machine URLs.
"""

from typing import Optional, Dict, Any

try:
    from .cdx import search, CDXError, CDXRecord
except ImportError:
    # When running as a script directly
    from cdx import search, CDXError, CDXRecord


def _normalize_url(url: str) -> str:
    """Normalize URL by adding https:// if protocol is missing."""
    normalized = url.strip()
    if not normalized.startswith(('http://', 'https://')):
        normalized = f"https://{normalized}"
    return normalized


def _build_wayback_url(timestamp: str, original_url: str) -> str:
    """Build a Wayback Machine URL from timestamp and original URL."""
    return f"https://web.archive.org/web/{timestamp}/{original_url}"


def _record_to_dict(record: CDXRecord, normalized_url: str) -> Dict[str, Any]:
    """Convert a CDX record to a dictionary."""
    timestamp = record.timestamp
    return {
        "wayback_url": _build_wayback_url(timestamp, normalized_url),
        "timestamp": timestamp,
        "original_url": normalized_url,
        "mimetype": record.mimetype or "",
        "statuscode": record.statuscode or "",
        "digest": record.digest or "",
        "length": record.length or "",
        "year": timestamp[:4] if len(timestamp) >= 4 else "",
        "date": timestamp[:8] if len(timestamp) >= 8 else timestamp,
    }


def get_wayback_metadata(
    url: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    collapse: Optional[str] = "timestamp:4"
) -> Dict[str, Any]:
    """
    Get Wayback Machine snapshot metadata for a URL and return as a dictionary.
    
    Args:
        url: The URL to search for in Wayback Machine
        from_date: Start date in format YYYYMMDDhhss (optional, can omit trailing digits)
        to_date: End date in format YYYYMMDDhhss (optional, can omit trailing digits)
        collapse: Limit snapshot count to reduce overhead (default "timestamp:4" for yearly)
            - "timestamp:4" - At most one snapshot per year
            - "timestamp:6" - At most one snapshot per month
            - "timestamp:8" - At most one snapshot per day
    
    Returns:
        Dictionary containing:
            - url: The normalized URL
            - snapshots_count: Number of snapshots found
            - snapshots: List of snapshot dictionaries
            - latest: Dictionary of the latest snapshot (or None)
            - oldest: Dictionary of the oldest snapshot (or None)
    
    Example:
        >>> metadata = get_wayback_metadata("https://a16z.com/")
        >>> print(f"Found {metadata['snapshots_count']} snapshots")
        >>> if metadata['latest']:
        ...     print(f"Latest: {metadata['latest']['year']} - {metadata['latest']['wayback_url']}")
    """
    normalized_url = _normalize_url(url)
    
    # Convert collapse string to list format expected by CDX API
    collapse_list = [collapse] if collapse else None
    
    try:
        response = search(
            url=normalized_url,
            from_date=from_date,
            to_date=to_date,
            collapse=collapse_list,
        )
    except CDXError as e:
        raise Exception(f"CDX API error for URL {normalized_url}: {e}")
    
    # Convert CDX records to dictionaries
    snapshots = [
        _record_to_dict(record, normalized_url)
        for record in response
        if record.timestamp
    ]
    
    # Build result dictionary
    result = {
        "url": normalized_url,
        "snapshots_count": len(snapshots),
        "snapshots": snapshots,
        "latest": snapshots[-1] if snapshots else None,
        "oldest": snapshots[0] if snapshots else None,
    }
    
    return result


