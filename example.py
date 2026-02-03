"""
Example usage of wayback4ai library.

This file demonstrates how to use the wayback4ai library to:
1. Get Wayback Machine metadata for URLs
2. Download archived content from Wayback Machine
"""

import json
import os
from pathlib import Path
from urllib.parse import urlparse
from wayback4ai.wayback import get_wayback_metadata
from wayback4ai.downloader import download_url, build_archive_url, parallel_download_urls, convert_to_id_url

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


def example_parallel_download_multiple_years():
    """Example: Parallel download archived content from multiple years and save to disk"""
    print("\n" + "=" * 70)
    print("Wayback4AI - Example: Parallel download multiple years and save to disk")
    print("=" * 70)
    
    target_url = "https://a16z.com/"
    output_dir = "downloaded_archives"
    
    try:
        # Get metadata with yearly snapshots (one per year)
        print(f"\nFetching metadata for: {target_url}")
        metadata = get_wayback_metadata(target_url, collapse="timestamp:4")
        
        print(f"Found {metadata['snapshots_count']} snapshots across multiple years")
        
        if metadata['snapshots_count'] == 0:
            print("No snapshots found!")
            return
        
        # Convert Wayback URLs to id_ format for faster downloads
        print("\nConverting URLs to id_ format for faster downloads...")
        id_urls = []
        snapshots_info = []
        
        for snapshot in metadata['snapshots']:
            wayback_url = snapshot['wayback_url']
            id_url = convert_to_id_url(wayback_url)
            id_urls.append(id_url)
            snapshots_info.append({
                'id_url': id_url,
                'timestamp': snapshot['timestamp'],
                'year': snapshot['year'],
                'date': snapshot['date'],
                'original_url': snapshot['original_url']
            })
        
        print(f"Prepared {len(id_urls)} URLs for parallel download")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        print(f"\nOutput directory: {output_path.absolute()}")
        
        # Parallel download all URLs
        print("\nStarting parallel downloads...")
        responses = parallel_download_urls(id_urls, n_jobs=2)
        
        # Save each response to disk
        print("\nSaving files to disk...")
        saved_files = []
        
        for i, response in enumerate(responses):
            snapshot_info = snapshots_info[i]
            
            # Generate filename from URL and timestamp
            parsed_url = urlparse(snapshot_info['original_url'])
            domain = parsed_url.netloc.replace(':', '_').replace('.', '_')
            filename = f"{domain}_{snapshot_info['year']}_{snapshot_info['timestamp']}.html"
            filepath = output_path / filename
            
            # Save content to file
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            saved_files.append({
                'filepath': str(filepath),
                'year': snapshot_info['year'],
                'timestamp': snapshot_info['timestamp'],
                'size': len(response.content),
                'status_code': response.status_code
            })
            
            print(f"  [{snapshot_info['year']}] Saved: {filename} ({len(response.content)} bytes)")
        
        # Print summary
        print("\n" + "-" * 70)
        print("Download Summary:")
        print("-" * 70)
        total_size = sum(f['size'] for f in saved_files)
        print(f"Total files downloaded: {len(saved_files)}")
        print(f"Total size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
        print(f"Output directory: {output_path.absolute()}")
        
        # Save metadata JSON
        metadata_file = output_path / "download_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'target_url': target_url,
                'download_info': saved_files,
                'snapshots_metadata': metadata['snapshots']
            }, f, indent=2, ensure_ascii=False)
        print(f"\nMetadata saved to: {metadata_file}")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all examples"""
    # example_get_wayback_metadata()
    # example_download_archive()
    example_parallel_download_multiple_years()


if __name__ == "__main__":
    main()
