"""
CDX API Python Client

A Python wrapper for the Wayback Machine CDX Server API.
"""

from .cdx_api import (
    CDXClient,
    CDXQuery,
    CDXRecord,
    CDXResponse,
    CDXError,
    MatchType,
    SortType,
    OutputFormat,
    search,
    get_latest,
    get_oldest,
)

__version__ = "1.0.0"
__all__ = [
    "CDXClient",
    "CDXQuery",
    "CDXRecord",
    "CDXResponse",
    "CDXError",
    "MatchType",
    "SortType",
    "OutputFormat",
    "search",
    "get_latest",
    "get_oldest",
]
