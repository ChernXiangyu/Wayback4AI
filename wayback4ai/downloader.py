import asyncio
import re
from pathlib import Path
from typing import Optional, Union, List

from joblib import Parallel, delayed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from tqdm.auto import tqdm
except ImportError:
    # Fallback if tqdm is not installed
    tqdm = None

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, ProxyConfig
except ImportError:
    AsyncWebCrawler = None
    BrowserConfig = None
    CrawlerRunConfig = None
    CacheMode = None
    ProxyConfig = None

# Global variables
HEADERS = {
    "User-Agent": "Archive4AI Bot/1.0",
    "Accept-Encoding": "gzip, deflate, br"  # Explicitly inform server about compression support
}

# Retry configuration (exponential backoff for transient errors like ERR_CONNECTION_REFUSED, rate limiting)
DEFAULT_RETRY_ATTEMPTS = 6
DEFAULT_RETRY_MULTIPLIER = 2
DEFAULT_RETRY_MIN_WAIT = 3
DEFAULT_RETRY_MAX_WAIT = 60

# Parallel download configuration
DEFAULT_N_JOBS = 4
DEFAULT_BACKEND = 'threading'

# Request configuration
DEFAULT_TIMEOUT = 30

# Default proxies file (relative to project root)
DEFAULT_PROXIES_FILE = "proxies.txt"


def load_proxies(
    filepath: Union[str, Path] = DEFAULT_PROXIES_FILE,
) -> List["ProxyConfig"]:
    """
    Load proxy configurations from a file.

    Each line should be in format: host:port:username:password
    (e.g. 92.112.137.37:5980:user:pass). Empty lines and # comments are ignored.

    Args:
        filepath: Path to proxies file, default "proxies.txt"

    Returns:
        List of ProxyConfig objects. Empty list if file not found or ProxyConfig unavailable.
    """
    if ProxyConfig is None:
        return []

    path = Path(filepath)
    if not path.exists():
        return []

    configs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            configs.append(ProxyConfig.from_string(line))
        except Exception:
            continue
    return configs


def _resolve_proxy(
    proxy: Optional[Union[str, Path, List, "ProxyConfig"]],
    index: int = 0,
) -> Optional["ProxyConfig"]:
    """Resolve proxy parameter to a single ProxyConfig or None."""
    if proxy is None:
        return None
    if ProxyConfig is None:
        return None

    if isinstance(proxy, (str, Path)):
        path = Path(proxy)
        if path.suffix == ".txt" or path.exists():
            configs = load_proxies(path)
            return configs[index % len(configs)] if configs else None
        return ProxyConfig.from_string(str(proxy))
    if isinstance(proxy, list):
        if not proxy:
            return None
        item = proxy[index % len(proxy)]
        if isinstance(item, str):
            return ProxyConfig.from_string(item)
        return item
    return proxy


class _HeadersAdapter:
    """Adapter providing requests-style headers.get() interface."""

    def __init__(self, headers: Optional[dict] = None):
        self._headers = headers or {}

    def get(self, key: str, default=None):
        # Case-insensitive lookup (HTTP headers are case-insensitive)
        key_lower = key.lower()
        for k, v in self._headers.items():
            if k.lower() == key_lower:
                return v
        return default


class _Crawl4AIResponse:
    """Response adapter mimicking requests.Response for compatibility with existing callers."""

    def __init__(self, html: str, status_code: int, response_headers: Optional[dict] = None):
        self._html = html or ""
        self.status_code = status_code or 0
        self.headers = _HeadersAdapter(response_headers)

    @property
    def text(self) -> str:
        return self._html

    @property
    def content(self) -> bytes:
        return self._html.encode("utf-8")

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise CrawlError(
                f"HTTP {self.status_code}",
                status_code=self.status_code,
                response=self,
            )


class CrawlError(Exception):
    """Raised when crawl4ai fails to fetch a URL."""

    def __init__(self, message: str, status_code: Optional[int] = None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


async def _crawl_url_async(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = DEFAULT_TIMEOUT,
    proxy_config: Optional["ProxyConfig"] = None,
) -> _Crawl4AIResponse:
    """Fetch URL using crawl4ai AsyncWebCrawler (async implementation)."""
    if AsyncWebCrawler is None:
        raise ImportError("crawl4ai is required for downloads. Install with: uv add crawl4ai")

    hdrs = headers or HEADERS
    browser_config = BrowserConfig(
        headless=True,
        user_agent=hdrs.get("User-Agent", "Archive4AI Bot/1.0"),
        headers=hdrs,
    )
    run_config_kwargs: dict = {
        "cache_mode": CacheMode.BYPASS,
        "page_timeout": timeout * 1000,  # crawl4ai uses milliseconds
    }
    if proxy_config is not None:
        run_config_kwargs["proxy_config"] = proxy_config
    run_config = CrawlerRunConfig(**run_config_kwargs)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)

    if not result.success:
        raise CrawlError(
            result.error_message or "Crawl failed",
            status_code=result.status_code,
            response=_Crawl4AIResponse(
                result.html or "",
                result.status_code or 0,
                result.response_headers,
            ),
        )

    response = _Crawl4AIResponse(
        result.html,
        result.status_code or 200,
        result.response_headers,
    )
    response.raise_for_status()
    return response


def download_url(
    url,
    headers=None,
    allow_redirects=True,
    stream=True,
    timeout=DEFAULT_TIMEOUT,
    proxy=None,
):
    """
    Generic function to download any URL using crawl4ai.

    Returns a response-like object compatible with requests.Response:
    - .text, .content, .status_code, .headers.get(), .raise_for_status()

    Args:
        url: URL to download
        headers: Request headers, defaults to global HEADERS
        allow_redirects: Whether to allow redirects, default True (crawl4ai follows redirects)
        stream: Ignored (kept for API compatibility; crawl4ai fetches full content)
        timeout: Timeout in seconds, default DEFAULT_TIMEOUT
        proxy: Proxy to use. Can be:
            - Path to proxies file (str or Path), uses first proxy
            - Single proxy string (host:port:user:pass or http://user:pass@host:port)
            - List of ProxyConfig or proxy strings
            - None for no proxy

    Returns:
        Response-like object (status_code, headers, text, content, raise_for_status)

    Raises:
        CrawlError: Raises when crawl fails
    """
    if headers is None:
        headers = HEADERS
    proxy_config = _resolve_proxy(proxy, 0)

    return asyncio.run(
        _crawl_url_async(url, headers=headers, timeout=timeout, proxy_config=proxy_config)
    )


def build_archive_url(timestamp, target_url):
    """
    Build Wayback Machine archive URL

    Args:
        timestamp: Timestamp in format like "20260101020758"
        target_url: Target URL, e.g., "https://a16z.com/"

    Returns:
        Constructed archive URL string

    Note:
        The `id_` parameter in the URL is important for faster downloads. When `id_` is included,
        Internet Archive returns simplified web pages without the Wayback Machine's wrapper interface,
        which significantly speeds up download times and reduces bandwidth usage.
    """
    # Build special URL with id_ to get original HTML (simplified by Internet Archive for faster downloads)
    archive_url = f"https://web.archive.org/web/{timestamp}id_/{target_url}"
    return archive_url


def convert_to_id_url(wayback_url):
    """
    Convert a standard Wayback Machine URL to use the `id_` parameter for faster downloads.

    This function extracts the timestamp and target URL from any Wayback URL format
    (e.g., standard format, if_ format, js_ format) and converts it to the `id_` format
    which provides simplified pages for faster downloads.

    Args:
        wayback_url: Wayback Machine URL in any format, e.g.:
            - "https://web.archive.org/web/20260101020758/https://a16z.com/"
            - "https://web.archive.org/web/20260101020758if_/https://a16z.com/"
            - "https://web.archive.org/web/20260101020758id_/https://a16z.com/"

    Returns:
        Wayback URL with `id_` parameter for faster downloads

    Example:
        >>> convert_to_id_url("https://web.archive.org/web/20260101020758/https://a16z.com/")
        'https://web.archive.org/web/20260101020758id_/https://a16z.com/'

    Note:
        The `id_` parameter speeds up downloads because Internet Archive returns simplified
        web pages without the Wayback Machine's wrapper interface, reducing bandwidth usage.
    """
    # Pattern to match Wayback URLs: https://web.archive.org/web/{timestamp}[mode_]/{target_url}
    # mode_ can be empty, id_, if_, js_, etc.
    pattern = r'https://web\.archive\.org/web/(\d{14})([a-z_]*)/(.+)'

    match = re.match(pattern, wayback_url)
    if not match:
        raise ValueError(f"Invalid Wayback URL format: {wayback_url}")

    timestamp = match.group(1)
    target_url = match.group(3)

    # Build URL with id_ parameter
    return f"https://web.archive.org/web/{timestamp}id_/{target_url}"


@retry(
    stop=stop_after_attempt(DEFAULT_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=DEFAULT_RETRY_MULTIPLIER, min=DEFAULT_RETRY_MIN_WAIT, max=DEFAULT_RETRY_MAX_WAIT),
    retry=retry_if_exception_type((
        CrawlError,
        OSError,
        TimeoutError,
        ConnectionError,
        asyncio.TimeoutError,
        RuntimeError,  # crawl4ai raises this on navigation failures (e.g. ERR_CONNECTION_REFUSED)
    )),
)
def download_url_with_retry(
    url,
    headers=None,
    allow_redirects=True,
    stream=True,
    timeout=DEFAULT_TIMEOUT,
    proxy=None,
):
    """
    Download URL with exponential backoff retry logic using tenacity.
    This is a wrapper around download_url with retry capabilities.

    Args:
        url: URL to download
        headers: Request headers, defaults to global HEADERS
        allow_redirects: Whether to allow redirects, default True
        stream: Whether to use streaming download, default True (suitable for large files)
        timeout: Timeout in seconds, default DEFAULT_TIMEOUT
        proxy: Proxy to use (see download_url for formats)

    Returns:
        Response-like object (status_code, headers, text, content, raise_for_status)

    Raises:
        CrawlError: Raises when crawl fails after retries
    """
    return download_url(
        url,
        headers=headers,
        allow_redirects=allow_redirects,
        stream=stream,
        timeout=timeout,
        proxy=proxy,
    )


def _proxy_server_str(proxy) -> str:
    """Safe string for logging (no credentials)."""
    s = getattr(proxy, "server", None)
    if s:
        return str(s).split("@")[-1]  # Strip embedded user:pass@ if present
    return "proxy"


def parallel_download_urls(
    urls,
    n_jobs=DEFAULT_N_JOBS,
    headers=None,
    allow_redirects=True,
    stream=True,
    timeout=DEFAULT_TIMEOUT,
    backend=DEFAULT_BACKEND,
    show_progress_bar=False,
    proxies=None,
    log_proxy_usage=True,
):
    """
    Download multiple URLs in parallel using joblib with exponential backoff retry.

    Args:
        urls: List of URLs to download
        n_jobs: Number of parallel workers, default DEFAULT_N_JOBS
        headers: Request headers, defaults to global HEADERS
        allow_redirects: Whether to allow redirects, default True
        stream: Whether to use streaming download, default True (suitable for large files)
        timeout: Timeout in seconds, default DEFAULT_TIMEOUT
        backend: Joblib backend ('threading' or 'loky'), default DEFAULT_BACKEND
        show_progress_bar: Whether to show a progress bar using tqdm, default False
        proxies: Proxies for round-robin use. Can be path to file (e.g. "proxies.txt"),
            list of proxy strings/ProxyConfig, or None for no proxy.
            URL at index i uses proxies[i % len(proxies)].
        log_proxy_usage: When True and proxies are used, print which proxy is used for each URL.
            Default True.

    Returns:
        List of response-like objects (or None for skipped failures) in the same order as input URLs.
        Failed downloads after max retries are returned as None; the process continues without raising.

    Note:
        Progress bar requires tqdm to be installed. If tqdm is not available and
        show_progress_bar=True, the function will work without displaying a progress bar.
        Each worker spawns a headless browser; consider reducing n_jobs if memory is limited.
    """
    # Build (index, url, proxy) for round-robin proxy assignment
    tasks = [
        (i, url, _resolve_proxy(proxies, i))
        for i, url in enumerate(urls)
    ]

    # Resolve proxy list for logging (path -> loaded configs)
    n_proxies = 0
    if proxies is not None:
        if isinstance(proxies, (str, Path)):
            configs = load_proxies(Path(proxies))
            n_proxies = len(configs)
        elif isinstance(proxies, list):
            n_proxies = len(proxies)
        if n_proxies > 0:
            print(f"[proxies] Using {n_proxies} proxy(ies) in round-robin")

    def _download_one(task):
        idx, url, proxy = task
        if proxy is not None and log_proxy_usage:
            server = _proxy_server_str(proxy)
            print(f"[proxies] URL {idx + 1}/{len(urls)}: switching to {server}")
        try:
            return download_url_with_retry(
                url,
                headers=headers,
                allow_redirects=allow_redirects,
                stream=stream,
                timeout=timeout,
                proxy=proxy,
            )
        except Exception:
            return None  # Skip failed URLs after max retries

    if show_progress_bar and tqdm is not None:
        pbar = tqdm(total=len(urls), desc="Downloading", unit="URL")

        def download_with_progress(task):
            result = _download_one(task)
            pbar.update(1)
            return result

        try:
            results = Parallel(n_jobs=n_jobs, backend=backend)(
                delayed(download_with_progress)(t) for t in tasks
            )
        finally:
            pbar.close()
    else:
        results = Parallel(n_jobs=n_jobs, backend=backend)(
            delayed(_download_one)(t) for t in tasks
        )
    return results
