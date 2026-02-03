"""
Wayback CDX Server API Python Client

A Python wrapper for the Wayback Machine CDX Server API.
Provides a clean, Pythonic interface for querying web archive captures.

Example usage:
    from cdx_api import CDXClient
    
    client = CDXClient("https://web.archive.org/cdx/search/cdx")
    
    # Simple query
    results = client.search("example.com")
    
    # Advanced query
    results = client.search(
        url="example.com",
        match_type="prefix",
        from_date="2020",
        to_date="2021",
        limit=100,
        output="json"
    )
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Iterator, Union, Dict, Any
from urllib.parse import urlencode, urljoin
import requests
import json


class MatchType(Enum):
    """URL matching modes for CDX queries."""
    EXACT = "exact"
    PREFIX = "prefix"
    HOST = "host"
    DOMAIN = "domain"


class SortType(Enum):
    """Sort order for CDX results."""
    REGULAR = "regular"    # Ascending by timestamp
    REVERSE = "reverse"    # Descending by timestamp
    CLOSEST = "closest"    # By proximity to closest timestamp


class OutputFormat(Enum):
    """Output format for CDX results."""
    TEXT = "text"
    JSON = "json"


@dataclass
class CDXRecord:
    """Represents a single CDX record (capture)."""
    urlkey: str = ""
    timestamp: str = ""
    original: str = ""
    mimetype: str = ""
    statuscode: str = ""
    digest: str = ""
    length: str = ""
    # Optional fields that may be present
    filename: Optional[str] = None
    offset: Optional[str] = None
    dupecount: Optional[str] = None
    groupcount: Optional[str] = None
    endtimestamp: Optional[str] = None
    
    # Store any extra fields
    extra: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_list(cls, fields: List[str], field_names: List[str]) -> "CDXRecord":
        """Create a CDXRecord from a list of field values and their names."""
        record = cls()
        for i, name in enumerate(field_names):
            if i < len(fields):
                value = fields[i]
                if hasattr(record, name.lower()):
                    setattr(record, name.lower(), value)
                else:
                    record.extra[name] = value
        return record
    
    @classmethod
    def from_text_line(cls, line: str, field_names: Optional[List[str]] = None) -> "CDXRecord":
        """Create a CDXRecord from a space-separated text line."""
        if field_names is None:
            field_names = ["urlkey", "timestamp", "original", "mimetype", 
                          "statuscode", "digest", "length"]
        fields = line.split()
        return cls.from_list(fields, field_names)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        result = {
            "urlkey": self.urlkey,
            "timestamp": self.timestamp,
            "original": self.original,
            "mimetype": self.mimetype,
            "statuscode": self.statuscode,
            "digest": self.digest,
            "length": self.length,
        }
        if self.filename:
            result["filename"] = self.filename
        if self.offset:
            result["offset"] = self.offset
        if self.dupecount:
            result["dupecount"] = self.dupecount
        if self.groupcount:
            result["groupcount"] = self.groupcount
        if self.endtimestamp:
            result["endtimestamp"] = self.endtimestamp
        result.update(self.extra)
        return result


@dataclass
class CDXResponse:
    """Response from a CDX query."""
    records: List[CDXRecord]
    field_names: List[str]
    resume_key: Optional[str] = None
    num_pages: Optional[int] = None
    raw_response: Optional[str] = None
    
    def __iter__(self) -> Iterator[CDXRecord]:
        return iter(self.records)
    
    def __len__(self) -> int:
        return len(self.records)
    
    def __getitem__(self, index: int) -> CDXRecord:
        return self.records[index]
    
    def to_list(self) -> List[Dict[str, Any]]:
        """Convert all records to a list of dictionaries."""
        return [r.to_dict() for r in self.records]


class CDXError(Exception):
    """Exception raised for CDX API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class CDXQuery:
    """Builder class for constructing CDX queries."""
    
    def __init__(self, url: str):
        self.params: Dict[str, Any] = {"url": url}
    
    def match_type(self, match_type: Union[MatchType, str]) -> "CDXQuery":
        """Set URL matching mode."""
        if isinstance(match_type, MatchType):
            self.params["matchType"] = match_type.value
        else:
            self.params["matchType"] = match_type
        return self
    
    def from_date(self, date: str) -> "CDXQuery":
        """Set start date filter (format: yyyyMMddhhmmss, 1-14 digits)."""
        self.params["from"] = date
        return self
    
    def to_date(self, date: str) -> "CDXQuery":
        """Set end date filter (format: yyyyMMddhhmmss, 1-14 digits)."""
        self.params["to"] = date
        return self
    
    def closest(self, timestamp: str) -> "CDXQuery":
        """Set closest timestamp for proximity sorting."""
        self.params["closest"] = timestamp
        return self
    
    def sort(self, sort_type: Union[SortType, str]) -> "CDXQuery":
        """Set sort order."""
        if isinstance(sort_type, SortType):
            self.params["sort"] = sort_type.value
        else:
            self.params["sort"] = sort_type
        return self
    
    def limit(self, n: int) -> "CDXQuery":
        """Limit number of results. Negative value returns last N results."""
        self.params["limit"] = n
        return self
    
    def offset(self, n: int) -> "CDXQuery":
        """Skip first N results."""
        self.params["offset"] = n
        return self
    
    def fields(self, *field_names: str) -> "CDXQuery":
        """Specify which fields to return."""
        self.params["fl"] = ",".join(field_names)
        return self
    
    def filter(self, *filters: str) -> "CDXQuery":
        """Add regex filters. Format: [!][~]field:pattern"""
        self.params["filter"] = list(filters)
        return self
    
    def collapse(self, *fields: str) -> "CDXQuery":
        """Add collapse/deduplication fields. Format: field or field:N"""
        self.params["collapse"] = list(fields)
        return self
    
    def collapse_time(self, digits: int) -> "CDXQuery":
        """Collapse by timestamp prefix of N digits."""
        self.params["collapseTime"] = digits
        return self
    
    def page(self, page_num: int) -> "CDXQuery":
        """Set page number (0-based)."""
        self.params["page"] = page_num
        return self
    
    def page_size(self, size: int) -> "CDXQuery":
        """Set page size."""
        self.params["pageSize"] = size
        return self
    
    def show_num_pages(self, show: bool = True) -> "CDXQuery":
        """Request total page count."""
        self.params["showNumPages"] = str(show).lower()
        return self
    
    def show_resume_key(self, show: bool = True) -> "CDXQuery":
        """Request resume key for pagination."""
        self.params["showResumeKey"] = str(show).lower()
        return self
    
    def resume_key(self, key: str) -> "CDXQuery":
        """Continue from a previous query using resume key."""
        self.params["resumeKey"] = key
        return self
    
    def show_dupe_count(self, show: bool = True) -> "CDXQuery":
        """Show duplicate count column."""
        self.params["showDupeCount"] = str(show).lower()
        return self
    
    def resolve_revisits(self, resolve: bool = True) -> "CDXQuery":
        """Resolve revisit records."""
        self.params["resolveRevisits"] = str(resolve).lower()
        return self
    
    def fast_latest(self, fast: bool = True) -> "CDXQuery":
        """Enable fast latest optimization."""
        self.params["fastLatest"] = str(fast).lower()
        return self
    
    def gzip(self, enabled: bool) -> "CDXQuery":
        """Enable/disable gzip compression."""
        self.params["gzip"] = str(enabled).lower()
        return self
    
    def output_json(self) -> "CDXQuery":
        """Set output format to JSON."""
        self.params["output"] = "json"
        return self
    
    def build_params(self) -> Dict[str, Any]:
        """Build the final query parameters dictionary."""
        return self.params.copy()


class CDXClient:
    """
    Client for querying the Wayback CDX Server API.
    
    Example:
        client = CDXClient("https://web.archive.org/cdx/search/cdx")
        
        # Simple search
        results = client.search("example.com")
        for record in results:
            print(record.timestamp, record.original)
        
        # Using query builder
        query = client.query("example.com").match_type(MatchType.PREFIX).limit(10)
        results = client.execute(query)
    """
    
    DEFAULT_FIELDS = ["urlkey", "timestamp", "original", "mimetype", 
                      "statuscode", "digest", "length"]
    
    def __init__(
        self,
        base_url: str = "https://web.archive.org/cdx/search/cdx",
        timeout: int = 30,
        auth_token: Optional[str] = None,
        session: Optional[requests.Session] = None
    ):
        """
        Initialize CDX client.
        
        Args:
            base_url: CDX server endpoint URL
            timeout: Request timeout in seconds
            auth_token: Optional API authentication token
            session: Optional requests Session for connection pooling
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_token = auth_token
        self.session = session or requests.Session()
        
        if auth_token:
            self.session.cookies.set("cdx-auth-token", auth_token)
    
    def query(self, url: str) -> CDXQuery:
        """
        Create a new query builder for the given URL.
        
        Args:
            url: The URL to query
            
        Returns:
            CDXQuery builder instance
        """
        return CDXQuery(url)
    
    def execute(self, query: CDXQuery, output: OutputFormat = OutputFormat.JSON) -> CDXResponse:
        """
        Execute a CDX query.
        
        Args:
            query: CDXQuery instance
            output: Output format (JSON recommended)
            
        Returns:
            CDXResponse containing the results
        """
        params = query.build_params()
        if output == OutputFormat.JSON and "output" not in params:
            params["output"] = "json"
        return self._execute_request(params)
    
    def search(
        self,
        url: str,
        match_type: Optional[Union[MatchType, str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        closest: Optional[str] = None,
        sort: Optional[Union[SortType, str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        fields: Optional[List[str]] = None,
        filters: Optional[List[str]] = None,
        collapse: Optional[List[str]] = None,
        output: Union[OutputFormat, str] = OutputFormat.JSON,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        show_resume_key: bool = False,
        resume_key: Optional[str] = None,
        show_dupe_count: bool = False,
        resolve_revisits: bool = False,
        fast_latest: Optional[bool] = None,
        gzip: Optional[bool] = None,
    ) -> CDXResponse:
        """
        Search for captures in the CDX index.
        
        Args:
            url: URL to search for (required)
            match_type: URL matching mode (exact, prefix, host, domain)
            from_date: Start date filter (yyyyMMddhhmmss format, 1-14 digits)
            to_date: End date filter (yyyyMMddhhmmss format, 1-14 digits)
            closest: Timestamp for proximity sorting
            sort: Sort order (regular, reverse, closest)
            limit: Maximum results (negative for last N)
            offset: Number of results to skip
            fields: List of fields to return
            filters: List of regex filters (format: [!][~]field:pattern)
            collapse: List of fields to collapse/deduplicate
            output: Output format (json or text)
            page: Page number (0-based)
            page_size: Results per page
            show_resume_key: Include resume key in response
            resume_key: Continue from previous query
            show_dupe_count: Include duplicate count
            resolve_revisits: Resolve revisit records
            fast_latest: Enable fast latest optimization
            gzip: Enable/disable gzip compression
            
        Returns:
            CDXResponse containing the results
        """
        params: Dict[str, Any] = {"url": url}
        
        if match_type:
            params["matchType"] = match_type.value if isinstance(match_type, MatchType) else match_type
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if closest:
            params["closest"] = closest
        if sort:
            params["sort"] = sort.value if isinstance(sort, SortType) else sort
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if fields:
            params["fl"] = ",".join(fields)
        if filters:
            params["filter"] = filters
        if collapse:
            params["collapse"] = collapse
        if isinstance(output, OutputFormat):
            if output == OutputFormat.JSON:
                params["output"] = "json"
        elif output == "json":
            params["output"] = "json"
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["pageSize"] = page_size
        if show_resume_key:
            params["showResumeKey"] = "true"
        if resume_key:
            params["resumeKey"] = resume_key
        if show_dupe_count:
            params["showDupeCount"] = "true"
        if resolve_revisits:
            params["resolveRevisits"] = "true"
        if fast_latest is not None:
            params["fastLatest"] = str(fast_latest).lower()
        if gzip is not None:
            params["gzip"] = str(gzip).lower()
        
        return self._execute_request(params)
    
    def get_num_pages(self, url: str, match_type: Optional[Union[MatchType, str]] = None,
                      page_size: Optional[int] = None) -> int:
        """
        Get the total number of pages for a query.
        
        Args:
            url: URL to query
            match_type: URL matching mode
            page_size: Page size
            
        Returns:
            Total number of pages
        """
        params: Dict[str, Any] = {"url": url, "showNumPages": "true"}
        if match_type:
            params["matchType"] = match_type.value if isinstance(match_type, MatchType) else match_type
        if page_size:
            params["pageSize"] = page_size
        
        response = self._make_request(params)
        return int(response.text.strip())
    
    def iter_all(
        self,
        url: str,
        batch_size: int = 10000,
        **kwargs
    ) -> Iterator[CDXRecord]:
        """
        Iterate over all results using resume keys.
        
        This is useful for large queries that would exceed server limits.
        
        Args:
            url: URL to search
            batch_size: Number of records per batch
            **kwargs: Additional search parameters
            
        Yields:
            CDXRecord instances
        """
        resume_key = None
        
        while True:
            response = self.search(
                url=url,
                limit=batch_size,
                show_resume_key=True,
                resume_key=resume_key,
                **kwargs
            )
            
            for record in response:
                yield record
            
            if not response.resume_key or len(response) < batch_size:
                break
            
            resume_key = response.resume_key
    
    def iter_pages(
        self,
        url: str,
        page_size: Optional[int] = None,
        **kwargs
    ) -> Iterator[CDXResponse]:
        """
        Iterate over all pages of results.
        
        Args:
            url: URL to search
            page_size: Results per page
            **kwargs: Additional search parameters
            
        Yields:
            CDXResponse for each page
        """
        num_pages = self.get_num_pages(url, 
                                        match_type=kwargs.get("match_type"),
                                        page_size=page_size)
        
        for page_num in range(num_pages):
            yield self.search(
                url=url,
                page=page_num,
                page_size=page_size,
                **kwargs
            )
    
    def get_latest(self, url: str) -> Optional[CDXRecord]:
        """
        Get the most recent capture of a URL.
        
        Args:
            url: URL to search
            
        Returns:
            Latest CDXRecord or None if not found
        """
        response = self.search(url=url, limit=-1, fast_latest=True)
        return response.records[0] if response.records else None
    
    def get_oldest(self, url: str) -> Optional[CDXRecord]:
        """
        Get the oldest capture of a URL.
        
        Args:
            url: URL to search
            
        Returns:
            Oldest CDXRecord or None if not found
        """
        response = self.search(url=url, limit=1)
        return response.records[0] if response.records else None
    
    def get_closest(self, url: str, timestamp: str, limit: int = 1) -> CDXResponse:
        """
        Get captures closest to a specific timestamp.
        
        Args:
            url: URL to search
            timestamp: Target timestamp (yyyyMMddhhmmss format)
            limit: Maximum number of results
            
        Returns:
            CDXResponse with closest captures
        """
        return self.search(
            url=url,
            closest=timestamp,
            sort=SortType.CLOSEST,
            limit=limit
        )
    
    def _execute_request(self, params: Dict[str, Any]) -> CDXResponse:
        """Execute a request and parse the response."""
        response = self._make_request(params)
        return self._parse_response(response, params)
    
    def _make_request(self, params: Dict[str, Any]) -> requests.Response:
        """Make HTTP request to CDX server."""
        # Handle list parameters (filter, collapse)
        query_params = []
        for key, value in params.items():
            if isinstance(value, list):
                for v in value:
                    query_params.append((key, v))
            else:
                query_params.append((key, value))
        
        url = f"{self.base_url}?{urlencode(query_params)}"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            raise CDXError(f"HTTP error: {e}", e.response.status_code if e.response else None)
        except requests.exceptions.RequestException as e:
            raise CDXError(f"Request failed: {e}")
    
    def _parse_response(self, response: requests.Response, params: Dict[str, Any]) -> CDXResponse:
        """Parse HTTP response into CDXResponse."""
        text = response.text.strip()
        
        if not text:
            return CDXResponse(records=[], field_names=self.DEFAULT_FIELDS)
        
        is_json = params.get("output") == "json"
        
        if is_json:
            return self._parse_json_response(text)
        else:
            return self._parse_text_response(text, params)
    
    def _parse_json_response(self, text: str) -> CDXResponse:
        """Parse JSON format response."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise CDXError(f"Failed to parse JSON response: {e}")
        
        if not data:
            return CDXResponse(records=[], field_names=self.DEFAULT_FIELDS)
        
        # First row is field names
        field_names = data[0] if data else self.DEFAULT_FIELDS
        records = []
        resume_key = None
        
        for row in data[1:]:
            # Empty row or resume key indicator
            if not row:
                continue
            # Resume key is a single-element array
            if len(row) == 1 and len(data) > 2:
                resume_key = row[0]
                continue
            
            record = CDXRecord.from_list(row, field_names)
            records.append(record)
        
        return CDXResponse(
            records=records,
            field_names=field_names,
            resume_key=resume_key,
            raw_response=text
        )
    
    def _parse_text_response(self, text: str, params: Dict[str, Any]) -> CDXResponse:
        """Parse plain text format response."""
        lines = text.split("\n")
        
        # Determine field names
        fl = params.get("fl")
        if fl:
            field_names = fl.split(",")
        else:
            field_names = self.DEFAULT_FIELDS
        
        records = []
        resume_key = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this might be a resume key (URL-encoded, starts with urlkey pattern)
            if "%" in line and " " not in line:
                resume_key = line
                continue
            
            record = CDXRecord.from_text_line(line, field_names)
            records.append(record)
        
        return CDXResponse(
            records=records,
            field_names=field_names,
            resume_key=resume_key,
            raw_response=text
        )
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self) -> "CDXClient":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience functions for quick queries
def search(url: str, base_url: str = "https://web.archive.org/cdx/search/cdx", **kwargs) -> CDXResponse:
    """
    Quick search function without creating a client instance.
    
    Args:
        url: URL to search
        base_url: CDX server endpoint
        **kwargs: Additional search parameters
        
    Returns:
        CDXResponse with results
    """
    with CDXClient(base_url) as client:
        return client.search(url, **kwargs)


def get_latest(url: str, base_url: str = "https://web.archive.org/cdx/search/cdx") -> Optional[CDXRecord]:
    """Get the most recent capture of a URL."""
    with CDXClient(base_url) as client:
        return client.get_latest(url)


def get_oldest(url: str, base_url: str = "https://web.archive.org/cdx/search/cdx") -> Optional[CDXRecord]:
    """Get the oldest capture of a URL."""
    with CDXClient(base_url) as client:
        return client.get_oldest(url)


if __name__ == "__main__":
    # Example usage
    client = CDXClient()
    
    # Simple search
    print("Searching for archive.org captures...")
    results = client.search("archive.org", limit=5)
    
    print(f"Found {len(results)} records:")
    for record in results:
        print(f"  {record.timestamp} - {record.original} [{record.statuscode}]")
    
    # Using query builder
    print("\nUsing query builder:")
    query = (client.query("archive.org")
             .match_type(MatchType.EXACT)
             .from_date("2020")
             .to_date("2021")
             .limit(3)
             .filter("statuscode:200"))
    
    results = client.execute(query)
    for record in results:
        print(f"  {record.timestamp} - {record.mimetype}")
