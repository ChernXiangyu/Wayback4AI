# CDX API Python Client

A Python wrapper for the Wayback Machine CDX Server API.

## Installation

```bash
pip install requests
```

Then copy `cdx_api.py` to your project.

## Quick Start

```python
from cdx_api import CDXClient, MatchType, SortType

# Create client
client = CDXClient("https://web.archive.org/cdx/search/cdx")

# Simple search
results = client.search("example.com", limit=10)
for record in results:
    print(f"{record.timestamp} - {record.original}")
```

## Usage Examples

### Basic Search

```python
from cdx_api import CDXClient

client = CDXClient()

# Search with various parameters
results = client.search(
    url="example.com",
    from_date="2020",
    to_date="2021",
    limit=100
)

print(f"Found {len(results)} captures")
```

### Using Query Builder

```python
from cdx_api import CDXClient, MatchType

client = CDXClient()

# Build complex queries fluently
query = (client.query("example.com")
         .match_type(MatchType.PREFIX)
         .from_date("20200101")
         .to_date("20201231")
         .filter("statuscode:200")
         .filter("mimetype:text/html")
         .collapse("digest")
         .limit(50))

results = client.execute(query)
```

### Get Latest/Oldest Capture

```python
from cdx_api import CDXClient

client = CDXClient()

# Get most recent capture
latest = client.get_latest("example.com")
if latest:
    print(f"Latest: {latest.timestamp}")

# Get oldest capture
oldest = client.get_oldest("example.com")
if oldest:
    print(f"Oldest: {oldest.timestamp}")
```

### Find Closest to Timestamp

```python
from cdx_api import CDXClient

client = CDXClient()

# Find capture closest to January 1, 2020
closest = client.get_closest("example.com", "20200101")
for record in closest:
    print(f"{record.timestamp} - {record.original}")
```

### Domain/Prefix Queries

```python
from cdx_api import CDXClient, MatchType

client = CDXClient()

# All pages under a path
results = client.search(
    url="example.com/blog/",
    match_type=MatchType.PREFIX,
    limit=100
)

# All subdomains
results = client.search(
    url="example.com",
    match_type=MatchType.DOMAIN,
    limit=100
)
```

### Filtering Results

```python
from cdx_api import CDXClient

client = CDXClient()

# Only successful HTML pages
results = client.search(
    url="example.com",
    filters=[
        "statuscode:200",
        "mimetype:text/html"
    ],
    limit=50
)

# Exclude certain status codes
results = client.search(
    url="example.com",
    filters=["!statuscode:404"],
    limit=50
)
```

### Deduplication

```python
from cdx_api import CDXClient

client = CDXClient()

# One capture per day
results = client.search(
    url="example.com",
    collapse=["timestamp:8"],
    limit=100
)

# Unique content only
results = client.search(
    url="example.com",
    collapse=["digest"],
    limit=100
)
```

### Pagination

```python
from cdx_api import CDXClient

client = CDXClient()

# Get total pages
num_pages = client.get_num_pages("example.com")
print(f"Total pages: {num_pages}")

# Iterate through pages
for page_response in client.iter_pages("example.com"):
    for record in page_response:
        print(record.original)
```

### Large Queries with Resume Key

```python
from cdx_api import CDXClient

client = CDXClient()

# Iterate through all results (handles batching automatically)
for record in client.iter_all("example.com", batch_size=10000):
    print(record.timestamp)
```

### Using with Context Manager

```python
from cdx_api import CDXClient

with CDXClient() as client:
    results = client.search("example.com", limit=10)
    for record in results:
        print(record.original)
# Connection is automatically closed
```

### Quick Functions (No Client Instance)

```python
from cdx_api import search, get_latest, get_oldest

# Quick search
results = search("example.com", limit=5)

# Get latest capture
latest = get_latest("example.com")

# Get oldest capture
oldest = get_oldest("example.com")
```

### Custom CDX Server

```python
from cdx_api import CDXClient

# Use your own CDX server
client = CDXClient(
    base_url="http://localhost:8080/cdx/search/cdx",
    timeout=60,
    auth_token="your-api-key"
)
```

## API Reference

### CDXClient

Main client class for CDX API interactions.

#### Constructor

```python
CDXClient(
    base_url="https://web.archive.org/cdx/search/cdx",
    timeout=30,
    auth_token=None,
    session=None
)
```

#### Methods

| Method | Description |
|--------|-------------|
| `search(url, **kwargs)` | Search for captures |
| `query(url)` | Create query builder |
| `execute(query)` | Execute a query |
| `get_latest(url)` | Get most recent capture |
| `get_oldest(url)` | Get oldest capture |
| `get_closest(url, timestamp)` | Get captures closest to timestamp |
| `get_num_pages(url)` | Get total page count |
| `iter_all(url, batch_size)` | Iterate all results |
| `iter_pages(url)` | Iterate through pages |

### CDXQuery (Builder)

Fluent query builder for constructing complex queries.

| Method | Description |
|--------|-------------|
| `.match_type(type)` | Set URL matching mode |
| `.from_date(date)` | Set start date |
| `.to_date(date)` | Set end date |
| `.closest(timestamp)` | Set closest timestamp |
| `.sort(type)` | Set sort order |
| `.limit(n)` | Limit results |
| `.offset(n)` | Skip results |
| `.fields(*names)` | Select output fields |
| `.filter(*filters)` | Add regex filters |
| `.collapse(*fields)` | Add collapse fields |
| `.page(n)` | Set page number |
| `.show_resume_key()` | Request resume key |
| `.resume_key(key)` | Continue from key |
| `.output_json()` | Set JSON output |

### CDXRecord

Represents a single CDX record.

| Field | Description |
|-------|-------------|
| `urlkey` | SURT-formatted URL |
| `timestamp` | Capture timestamp |
| `original` | Original URL |
| `mimetype` | MIME type |
| `statuscode` | HTTP status code |
| `digest` | Content digest |
| `length` | Content length |

### Enums

#### MatchType

- `EXACT` - Exact URL match
- `PREFIX` - URL prefix match
- `HOST` - Host match
- `DOMAIN` - Domain and subdomains

#### SortType

- `REGULAR` - Ascending by timestamp
- `REVERSE` - Descending by timestamp
- `CLOSEST` - By proximity to closest

## Error Handling

```python
from cdx_api import CDXClient, CDXError

client = CDXClient()

try:
    results = client.search("example.com")
except CDXError as e:
    print(f"CDX Error: {e}")
    print(f"Status Code: {e.status_code}")
```

## License

MIT License
