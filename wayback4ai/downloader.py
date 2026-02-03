import requests
from joblib import Parallel, delayed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Global variables
HEADERS = {
    "User-Agent": "Archive4AI Bot/1.0",
    "Accept-Encoding": "gzip, deflate, br"  # Explicitly inform server about compression support
}

# Retry configuration
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_MULTIPLIER = 1
DEFAULT_RETRY_MIN_WAIT = 2
DEFAULT_RETRY_MAX_WAIT = 10

# Parallel download configuration
DEFAULT_N_JOBS = 4
DEFAULT_BACKEND = 'threading'

# Request configuration
DEFAULT_TIMEOUT = 30


def download_url(url, headers=None, allow_redirects=True, stream=True, timeout=DEFAULT_TIMEOUT):
    """
    Generic function to download any URL using requests
    
    Args:
        url: URL to download
        headers: Request headers, defaults to global HEADERS
        allow_redirects: Whether to allow redirects, default True
        stream: Whether to use streaming download, default True (suitable for large files)
        timeout: Timeout in seconds, default DEFAULT_TIMEOUT
    
    Returns:
        requests.Response object
    
    Raises:
        requests.exceptions.RequestException: Raises exception when request fails
    """
    if headers is None:
        headers = HEADERS
    
    response = requests.get(
        url,
        headers=headers,
        allow_redirects=allow_redirects,
        stream=stream,
        timeout=timeout
    )
    
    # Equivalent to curl's --fail: raises exception if 4xx or 5xx error is returned
    response.raise_for_status()
    
    return response


def build_archive_url(timestamp, target_url):
    """
    Build Wayback Machine archive URL
    
    Args:
        timestamp: Timestamp in format like "20260101020758"
        target_url: Target URL, e.g., "https://a16z.com/"
    
    Returns:
        Constructed archive URL string
    """
    # Build special URL with id_ to get original HTML
    archive_url = f"https://web.archive.org/web/{timestamp}id_/{target_url}"
    return archive_url


@retry(
    stop=stop_after_attempt(DEFAULT_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=DEFAULT_RETRY_MULTIPLIER, min=DEFAULT_RETRY_MIN_WAIT, max=DEFAULT_RETRY_MAX_WAIT),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def download_url_with_retry(url, headers=None, allow_redirects=True, stream=True, timeout=DEFAULT_TIMEOUT):
    """
    Download URL with exponential backoff retry logic using tenacity.
    This is a wrapper around download_url with retry capabilities.
    
    Args:
        url: URL to download
        headers: Request headers, defaults to global HEADERS
        allow_redirects: Whether to allow redirects, default True
        stream: Whether to use streaming download, default True (suitable for large files)
        timeout: Timeout in seconds, default DEFAULT_TIMEOUT
    
    Returns:
        requests.Response object
    
    Raises:
        requests.exceptions.RequestException: Raises exception when request fails after retries
    """
    return download_url(url, headers=headers, allow_redirects=allow_redirects, stream=stream, timeout=timeout)


def parallel_download_urls(urls, n_jobs=DEFAULT_N_JOBS, headers=None, allow_redirects=True, stream=True, timeout=DEFAULT_TIMEOUT, backend=DEFAULT_BACKEND):
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
    
    Returns:
        List of requests.Response objects in the same order as input URLs
    
    Raises:
        requests.exceptions.RequestException: Raises exception if any download fails after retries
    """
    results = Parallel(n_jobs=n_jobs, backend=backend)(
        delayed(download_url_with_retry)(
            url,
            headers=headers,
            allow_redirects=allow_redirects,
            stream=stream,
            timeout=timeout
        )
        for url in urls
    )
    return results

