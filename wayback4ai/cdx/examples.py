"""
CDX API Python Client - Usage Examples

This file demonstrates various ways to use the CDX API client.
"""

from cdx_api import CDXClient, CDXQuery, MatchType, SortType, CDXError


def example_basic_search():
    """Basic search example."""
    print("=" * 50)
    print("Example: Basic Search")
    print("=" * 50)
    
    client = CDXClient()
    
    # Simple search for a URL
    results = client.search("archive.org", limit=5)
    
    print(f"Found {len(results)} captures:")
    for record in results:
        print(f"  [{record.timestamp}] {record.original} - {record.statuscode}")
    print()


def example_query_builder():
    """Using the fluent query builder."""
    print("=" * 50)
    print("Example: Query Builder")
    print("=" * 50)
    
    client = CDXClient()
    
    # Build a complex query fluently
    query = (client.query("archive.org")
             .match_type(MatchType.EXACT)
             .from_date("2020")
             .to_date("2021")
             .filter("statuscode:200")
             .limit(5))
    
    results = client.execute(query)
    
    print(f"Captures from 2020-2021 with status 200:")
    for record in results:
        print(f"  [{record.timestamp}] {record.mimetype}")
    print()


def example_time_range():
    """Filter by time range."""
    print("=" * 50)
    print("Example: Time Range Filter")
    print("=" * 50)
    
    client = CDXClient()
    
    results = client.search(
        url="example.com",
        from_date="20200101",
        to_date="20201231",
        limit=5
    )
    
    print(f"Captures from 2020:")
    for record in results:
        print(f"  [{record.timestamp}] {record.original}")
    print()


def example_prefix_search():
    """Search all URLs under a prefix."""
    print("=" * 50)
    print("Example: Prefix Search")
    print("=" * 50)
    
    client = CDXClient()
    
    # Find all pages under /about/
    results = client.search(
        url="archive.org/about/",
        match_type=MatchType.PREFIX,
        limit=10
    )
    
    print(f"Pages under /about/:")
    for record in results:
        print(f"  {record.original}")
    print()


def example_domain_search():
    """Search all subdomains."""
    print("=" * 50)
    print("Example: Domain Search (with subdomains)")
    print("=" * 50)
    
    client = CDXClient()
    
    # Find captures from all subdomains
    results = client.search(
        url="archive.org",
        match_type=MatchType.DOMAIN,
        limit=10,
        collapse=["urlkey"]  # One per unique URL
    )
    
    print(f"Unique URLs from *.archive.org:")
    for record in results:
        print(f"  {record.original}")
    print()


def example_filtering():
    """Filter results using regex."""
    print("=" * 50)
    print("Example: Filtering with Regex")
    print("=" * 50)
    
    client = CDXClient()
    
    # Only HTML pages with 200 status
    results = client.search(
        url="archive.org",
        filters=[
            "statuscode:200",
            "mimetype:text/html"
        ],
        limit=5
    )
    
    print(f"HTML pages with 200 status:")
    for record in results:
        print(f"  [{record.statuscode}] {record.mimetype} - {record.original}")
    print()
    
    # Exclude 404 errors
    results = client.search(
        url="archive.org",
        filters=["!statuscode:404"],
        limit=5
    )
    
    print(f"Excluding 404 errors:")
    for record in results:
        print(f"  [{record.statuscode}] {record.original}")
    print()


def example_deduplication():
    """Deduplicate results."""
    print("=" * 50)
    print("Example: Deduplication (Collapse)")
    print("=" * 50)
    
    client = CDXClient()
    
    # One capture per day
    results = client.search(
        url="archive.org",
        collapse=["timestamp:8"],  # First 8 digits = YYYYMMDD
        limit=10
    )
    
    print(f"One capture per day:")
    for record in results:
        date = record.timestamp[:8]
        print(f"  {date} - {record.original}")
    print()
    
    # Unique content only (by digest)
    results = client.search(
        url="archive.org",
        collapse=["digest"],
        limit=5
    )
    
    print(f"Unique content (by digest):")
    for record in results:
        print(f"  {record.digest[:16]}... - {record.timestamp}")
    print()


def example_latest_oldest():
    """Get latest and oldest captures."""
    print("=" * 50)
    print("Example: Latest and Oldest")
    print("=" * 50)
    
    client = CDXClient()
    
    # Most recent capture
    latest = client.get_latest("archive.org")
    if latest:
        print(f"Latest capture: {latest.timestamp} - {latest.original}")
    
    # Oldest capture
    oldest = client.get_oldest("archive.org")
    if oldest:
        print(f"Oldest capture: {oldest.timestamp} - {oldest.original}")
    print()


def example_closest():
    """Find captures closest to a timestamp."""
    print("=" * 50)
    print("Example: Closest to Timestamp")
    print("=" * 50)
    
    client = CDXClient()
    
    # Find capture closest to January 1, 2015
    results = client.get_closest("archive.org", "20150101", limit=3)
    
    print(f"Captures closest to 2015-01-01:")
    for record in results:
        print(f"  {record.timestamp} - {record.original}")
    print()


def example_pagination():
    """Paginate through results."""
    print("=" * 50)
    print("Example: Pagination")
    print("=" * 50)
    
    client = CDXClient()
    
    # Get total pages (may not work on all servers)
    try:
        num_pages = client.get_num_pages("archive.org")
        print(f"Total pages: {num_pages}")
    except CDXError as e:
        print(f"Pagination not supported: {e}")
    print()


def example_custom_fields():
    """Select specific output fields."""
    print("=" * 50)
    print("Example: Custom Output Fields")
    print("=" * 50)
    
    client = CDXClient()
    
    # Only return specific fields
    results = client.search(
        url="archive.org",
        fields=["timestamp", "original", "statuscode"],
        limit=5
    )
    
    print(f"Custom fields (timestamp, original, statuscode):")
    for record in results:
        print(f"  {record.timestamp} | {record.statuscode} | {record.original}")
    print()


def example_error_handling():
    """Handle errors gracefully."""
    print("=" * 50)
    print("Example: Error Handling")
    print("=" * 50)
    
    client = CDXClient()
    
    try:
        # This might fail with certain parameters
        results = client.search("nonexistent-domain-12345.invalid", limit=1)
        print(f"Found {len(results)} results")
    except CDXError as e:
        print(f"CDX Error: {e}")
        if e.status_code:
            print(f"HTTP Status: {e.status_code}")
    print()


def example_context_manager():
    """Use client as context manager."""
    print("=" * 50)
    print("Example: Context Manager")
    print("=" * 50)
    
    with CDXClient() as client:
        results = client.search("archive.org", limit=3)
        print(f"Found {len(results)} captures")
        for record in results:
            print(f"  {record.timestamp}")
    
    print("Client connection closed automatically")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 50)
    print("CDX API Python Client Examples")
    print("=" * 50 + "\n")
    
    examples = [
        example_basic_search,
        example_query_builder,
        example_time_range,
        example_prefix_search,
        # example_domain_search,  # May be slow
        example_filtering,
        example_deduplication,
        example_latest_oldest,
        example_closest,
        # example_pagination,  # May not work on all servers
        example_custom_fields,
        example_error_handling,
        example_context_manager,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Example failed: {e}\n")


if __name__ == "__main__":
    main()
