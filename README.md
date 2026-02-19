# Wayback4AI

A data harvester for the Internet Archive. Combines Wayback Machine's CDX/Availability APIs with Crawl4AI to capture, extract, and convert historical web pages into LLM-ready Markdown.

## Features

- 🔍 **Metadata Retrieval**: Get snapshot metadata for any URL from the Wayback Machine
- 📥 **Archive Downloads**: Download archived content with retry logic and parallel processing
- 🗓️ **Date Filtering**: Filter snapshots by date range
- 📊 **CDX API Integration**: Full access to Wayback Machine's CDX Server API
- ⚡ **Parallel Processing**: Download multiple archives concurrently
- 🔄 **Automatic Retries**: Exponential backoff retry mechanism for reliable downloads
- 📦 **LLM-Ready**: Convert historical web pages into Markdown format suitable for AI/LLM processing

## Installation

```bash
pip install wayback4ai
```

### Requirements

- Python >= 3.13
- requests >= 2.32.5
- joblib >= 1.3.0
- tenacity >= 8.2.0

## Quick Start

### Get Wayback Machine Metadata

```python
from wayback4ai import get_wayback_metadata

# Get metadata for a URL
metadata = get_wayback_metadata("https://a16z.com/")

print(f"Found {metadata['snapshots_count']} snapshots")
print(f"Latest snapshot: {metadata['latest']['wayback_url']}")
print(f"Oldest snapshot: {metadata['oldest']['wayback_url']}")
```

### Download Archived Content

```python
from wayback4ai.downloader import download_url, build_archive_url

# Build archive URL
timestamp = "20260101020758"
target_url = "https://a16z.com/"
archive_url = build_archive_url(timestamp, target_url)

# Download content
response = download_url(archive_url)
print(response.text)
```

## Usage Examples

### Get Metadata with Date Filtering

```python
from wayback4ai import get_wayback_metadata

# Get snapshots from 2020 to 2021
metadata = get_wayback_metadata(
    "https://example.com/",
    from_date="20200101",
    to_date="20211231",
    collapse="timestamp:6"  # One snapshot per month
)

for snapshot in metadata['snapshots']:
    print(f"{snapshot['date']} - {snapshot['wayback_url']}")
```

### Parallel Downloads

```python
from wayback4ai.downloader import parallel_download_urls, build_archive_url

# Build multiple archive URLs
urls = [
    build_archive_url("20200101000000", "https://example.com/"),
    build_archive_url("20210101000000", "https://example.com/"),
    build_archive_url("20220101000000", "https://example.com/"),
]

# Download in parallel
responses = parallel_download_urls(urls, n_jobs=4)

for response in responses:
    print(f"Downloaded {len(response.text)} bytes")
```

### Proxy Support

Load proxies from a file (format: `host:port:username:password` per line) for round-robin use:

```python
from wayback4ai.downloader import download_url, parallel_download_urls, load_proxies

# Single download with first proxy from file
response = download_url("https://web.archive.org/...", proxy="proxies.txt")

# Parallel downloads with round-robin proxy rotation
responses = parallel_download_urls(urls, proxies="proxies.txt")

# Or use a list of proxy strings
proxies = load_proxies("proxies.txt")
responses = parallel_download_urls(urls, proxies=proxies)
```

### Advanced CDX API Usage

For advanced CDX API features, see the [CDX API documentation](wayback4ai/cdx/README.md).

```python
from wayback4ai.cdx.cdx_api import search, get_latest, get_oldest

# Quick search
results = search("example.com", limit=10)
for record in results:
    print(f"{record.timestamp} - {record.original}")

# Get latest capture
latest = get_latest("example.com")
if latest:
    print(f"Latest: {latest.timestamp} - {latest.wayback_url}")
```

## API Reference

### `get_wayback_metadata(url, from_date=None, to_date=None, collapse="timestamp:4")`

Get Wayback Machine snapshot metadata for a URL.

**Parameters:**
- `url` (str): The URL to search for in Wayback Machine
- `from_date` (str, optional): Start date in format YYYYMMDDhhss (can omit trailing digits)
- `to_date` (str, optional): End date in format YYYYMMDDhhss (can omit trailing digits)
- `collapse` (str, optional): Limit snapshot count (default: "timestamp:4" for yearly)
  - `"timestamp:4"` - At most one snapshot per year
  - `"timestamp:6"` - At most one snapshot per month
  - `"timestamp:8"` - At most one snapshot per day

**Returns:**
- `dict`: Dictionary containing:
  - `url`: The normalized URL
  - `snapshots_count`: Number of snapshots found
  - `snapshots`: List of snapshot dictionaries
  - `latest`: Dictionary of the latest snapshot (or None)
  - `oldest`: Dictionary of the oldest snapshot (or None)

### `download_url(url, headers=None, allow_redirects=True, stream=True, timeout=30)`

Download any URL using requests.

**Parameters:**
- `url` (str): URL to download
- `headers` (dict, optional): Request headers
- `allow_redirects` (bool): Whether to allow redirects (default: True)
- `stream` (bool): Whether to use streaming download (default: True)
- `timeout` (int): Timeout in seconds (default: 30)

**Returns:**
- `requests.Response`: Response object

### `build_archive_url(timestamp, target_url)`

Build Wayback Machine archive URL.

**Parameters:**
- `timestamp` (str): Timestamp in format "YYYYMMDDhhmmss"
- `target_url` (str): Target URL

**Returns:**
- `str`: Constructed archive URL

### `parallel_download_urls(urls, n_jobs=4, headers=None, allow_redirects=True, stream=True, timeout=30, backend='threading')`

Download multiple URLs in parallel with retry logic.

**Parameters:**
- `urls` (list): List of URLs to download
- `n_jobs` (int): Number of parallel workers (default: 4)
- `headers` (dict, optional): Request headers
- `allow_redirects` (bool): Whether to allow redirects (default: True)
- `stream` (bool): Whether to use streaming download (default: True)
- `timeout` (int): Timeout in seconds (default: 30)
- `backend` (str): Joblib backend ('threading' or 'loky', default: 'threading')

**Returns:**
- `list`: List of `requests.Response` objects in the same order as input URLs

## Examples

See [example.py](example.py) for complete usage examples.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

See [LICENSE](LICENSE) file for details.

## Related Projects

- [Crawl4AI](https://github.com/unclecode/crawl4ai) - Web crawling and content extraction framework
- [Internet Archive Wayback Machine](https://web.archive.org/) - Digital archive of the World Wide Web

## Acknowledgments

- Internet Archive for providing the Wayback Machine and CDX API
- All contributors who help improve this project
