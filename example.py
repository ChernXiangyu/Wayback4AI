"""
Example usage of wayback4ai library.

This file demonstrates how to use the wayback4ai library to:
1. Get Wayback Machine metadata for URLs
2. Download archived content from Wayback Machine
"""

import json
from wayback4ai.wayback import get_wayback_metadata
from wayback4ai.downloader import download_url, build_archive_url


def example_get_wayback_metadata():
    """Example: Get Wayback Machine metadata for a16z.com"""
    print("=" * 70)
    print("Wayback4AI - Example: Getting metadata for a16z.com")
    print("=" * 70)
    
    try:
        # Get metadata for a16z.com
        metadata = get_wayback_metadata("https://a16z.com/")
        
        # Display summary
        print(f"\nURL: {metadata['url']}")
        print(f"Found {metadata['snapshots_count']} snapshots")
        
        # Display latest snapshot
        if metadata['latest']:
            latest = metadata['latest']
            print("\n" + "-" * 70)
            print("Latest Snapshot:")
            print("-" * 70)
            print(f"  Year:        {latest['year']}")
            print(f"  Date:        {latest['date']}")
            print(f"  Timestamp:   {latest['timestamp']}")
            print(f"  MIME Type:   {latest['mimetype']}")
            print(f"  Status Code: {latest['statuscode']}")
            print(f"  Wayback URL: {latest['wayback_url']}")
        
        # Display oldest snapshot
        if metadata['oldest']:
            oldest = metadata['oldest']
            print("\n" + "-" * 70)
            print("Oldest Snapshot:")
            print("-" * 70)
            print(f"  Year:        {oldest['year']}")
            print(f"  Date:        {oldest['date']}")
            print(f"  Timestamp:   {oldest['timestamp']}")
            print(f"  Wayback URL: {oldest['wayback_url']}")
        
        # Display all snapshots summary
        print("\n" + "-" * 70)
        print("All Snapshots:")
        print("-" * 70)
        for snapshot in metadata['snapshots']:
            print(f"  [{snapshot['year']}] {snapshot['date']} - {snapshot['wayback_url']}")
        
        # Print full JSON (formatted)
        print("\n" + "=" * 70)
        print("Full JSON Output:")
        print("=" * 70)
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def example_download_archive():
    """Example: Download archived content from Wayback Machine"""
    print("\n" + "=" * 70)
    print("Wayback4AI - Example: Downloading archived content")
    print("=" * 70)
    
    timestamp = "20260101020758"
    target_url = "https://a16z.com/"
    
    try:
        # Build archive URL
        archive_url = build_archive_url(timestamp, target_url)
        print(f"\nArchive URL: {archive_url}")
        
        # Download content
        response = download_url(archive_url)
        
        # Print content info instead of writing to file
        print(f"\nDownload successful!")
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"Content-Length: {response.headers.get('Content-Length', 'N/A')} bytes")
        
        # Print first 500 characters of content as preview
        content_preview = response.text[:500]
        print("\n" + "-" * 70)
        print("Content Preview (first 500 characters):")
        print("-" * 70)
        print(content_preview)
        if len(response.text) > 500:
            print(f"\n... (truncated, total length: {len(response.text)} characters)")
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all examples"""
    example_get_wayback_metadata()
    example_download_archive()


if __name__ == "__main__":
    main()
