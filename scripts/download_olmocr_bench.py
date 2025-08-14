#!/usr/bin/env python3
"""
Download script for olmOCR-bench dataset with rate limiting handling.

This script downloads the olmOCR-bench dataset from HuggingFace with proper
rate limiting, retry logic, and authentication support to avoid 429 errors.

Usage:
    python download_olmocr_bench.py --output-dir ./olmOCR-bench [--token YOUR_HF_TOKEN] [--max-workers 2]
"""

import argparse
import os
import time
from pathlib import Path
from typing import Optional, List

from huggingface_hub import snapshot_download, HfApi
from huggingface_hub.utils import HfHubHTTPError
import requests


def count_pdfs(directory: str) -> int:
    """Count PDF files in a directory recursively."""
    pdf_files = list(Path(directory).rglob("*.pdf"))
    return len(pdf_files)


def get_pdf_categories(directory: str) -> List[str]:
    """Get list of PDF categories (subdirectories) in bench_data/pdfs."""
    pdfs_dir = Path(directory) / "bench_data" / "pdfs"
    if not pdfs_dir.exists():
        return []
    return [d.name for d in pdfs_dir.iterdir() if d.is_dir()]


def check_download_completeness(directory: str) -> tuple[bool, str]:
    """
    Check if the download is complete by looking for expected categories.
    
    Returns:
        (is_complete, status_message)
    """
    expected_categories = [
        "arxiv_math", "headers_footers", "long_tiny_text", 
        "multi_column", "old_scans", "old_scans_math", "table_tests"
    ]
    
    actual_categories = get_pdf_categories(directory)
    missing_categories = set(expected_categories) - set(actual_categories)
    pdf_count = count_pdfs(directory)
    
    if not missing_categories and pdf_count >= 1000:  # Should be ~1403 total
        return True, f"Complete: {pdf_count} PDFs across all {len(actual_categories)} categories"
    elif missing_categories:
        return False, f"Incomplete: Missing categories {sorted(missing_categories)}, {pdf_count} PDFs found"
    else:
        return False, f"Incomplete: Only {pdf_count} PDFs found (expected ~1403)"


def download_with_retry(
    repo_id: str,
    local_dir: str,
    token: Optional[str] = None,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_workers: int = 2,
    resume_download: bool = True,
    force_complete: bool = True,
) -> str:
    """
    Download HuggingFace dataset with exponential backoff retry logic.
    
    Args:
        repo_id: HuggingFace repository ID (e.g., "allenai/olmOCR-bench")
        local_dir: Local directory to download to
        token: HuggingFace API token (optional but recommended for higher rate limits)
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_workers: Number of concurrent downloads (keep low to avoid rate limits)
        resume_download: Whether to resume partial downloads
        
    Returns:
        Path to downloaded directory
    """
    
    for attempt in range(max_retries + 1):
        try:
            print(f"Attempt {attempt + 1}/{max_retries + 1}: Downloading {repo_id}...")
            
            # Use lower concurrency to avoid overwhelming the server
            result = snapshot_download(
                repo_id=repo_id,
                repo_type="dataset",
                local_dir=local_dir,
                token=token,
                resume_download=resume_download,
                max_workers=max_workers,  # Reduced from default to avoid rate limits
                tqdm_class=None if attempt > 0 else None,  # Hide progress bar on retries
            )
            
            print(f"Successfully downloaded {repo_id} to {local_dir}")
            return result
            
        except HfHubHTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Rate limited (429). Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    print("Max retries reached. Consider:")
                    print("1. Using a HuggingFace token for higher rate limits")
                    print("2. Running the script later when traffic is lower")
                    print("3. Reducing --max-workers further")
                    
                    # Check if we have a partial download that we can work with
                    if os.path.exists(local_dir) and force_complete:
                        pdf_count = count_pdfs(local_dir)
                        if pdf_count > 0:
                            print(f"Found {pdf_count} PDFs in partial download.")
                            print("You can try running the script again later to resume download.")
                        return local_dir
                    raise
            else:
                print(f"HTTP error {e.response.status_code}: {e}")
                raise
                
        except Exception as e:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"Error: {e}. Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
                continue
            else:
                print(f"Failed after {max_retries + 1} attempts: {e}")
                raise


def validate_token(token: Optional[str]) -> bool:
    """Validate HuggingFace token by making a simple API call."""
    if not token:
        return False
    
    try:
        api = HfApi(token=token)
        # Simple API call to validate token
        api.whoami()
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download olmOCR-bench dataset with rate limiting protection"
    )
    parser.add_argument(
        "--output-dir",
        default="./olmOCR-bench",
        help="Output directory for downloaded dataset (default: ./olmOCR-bench)"
    )
    parser.add_argument(
        "--token",
        help="HuggingFace API token (recommended for higher rate limits)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=2,
        help="Number of concurrent downloads (default: 2, keep low to avoid rate limits)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum number of retry attempts (default: 5)"
    )
    parser.add_argument(
        "--base-delay",
        type=float,
        default=2.0,
        help="Base delay in seconds for exponential backoff (default: 2.0)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check download status without downloading"
    )
    parser.add_argument(
        "--force-restart",
        action="store_true", 
        help="Delete existing download and start fresh"
    )
    
    args = parser.parse_args()
    
    # Validate token if provided
    if args.token:
        if validate_token(args.token):
            print("✓ HuggingFace token validated successfully")
        else:
            print("⚠ Warning: HuggingFace token validation failed")
            print("  You may still be able to download public datasets")
    else:
        print("⚠ No HuggingFace token provided. You may hit rate limits more quickly.")
        print("  Consider creating a free token at https://huggingface.co/settings/tokens")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    
    # Handle force restart
    if args.force_restart and output_dir.exists():
        print(f"🗑️  Deleting existing download at: {output_dir.absolute()}")
        import shutil
        shutil.rmtree(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Handle check-only option
    if args.check_only:
        if output_dir.exists():
            is_complete, status_msg = check_download_completeness(str(output_dir))
            pdf_count = count_pdfs(str(output_dir))
            categories = get_pdf_categories(str(output_dir))
            
            print(f"📊 Download status for: {output_dir.absolute()}")
            print(f"Status: {status_msg}")
            print(f"- {pdf_count} PDF files")
            print(f"- {len(categories)} PDF categories: {categories}")
            
            if not is_complete:
                print("\nTo resume download, run without --check-only flag")
        else:
            print(f"❌ No download found at: {output_dir.absolute()}")
        return
    
    print(f"Downloading to: {output_dir.absolute()}")
    print(f"Max workers: {args.max_workers}")
    print(f"Max retries: {args.max_retries}")
    
    try:
        download_with_retry(
            repo_id="allenai/olmOCR-bench",
            local_dir=str(output_dir),
            token=args.token,
            max_retries=args.max_retries,
            base_delay=args.base_delay,
            max_workers=args.max_workers,
        )
        
        # Check if download is actually complete
        is_complete, status_msg = check_download_completeness(str(output_dir))
        
        if is_complete:
            print("\n🎉 Download completed successfully!")
            print(f"Dataset available at: {output_dir.absolute()}")
            print(f"Status: {status_msg}")
        else:
            print(f"\n⚠️  Download appears incomplete!")
            print(f"Dataset available at: {output_dir.absolute()}")
            print(f"Status: {status_msg}")
            print("\nTo resume download:")
            print(f"1. Run the script again: python {__file__} --output-dir {output_dir}")
            print("2. Consider using a HuggingFace token for higher rate limits")
            print("3. Try running during off-peak hours")
            
        # Show some basic info about what was downloaded
        pdf_count = count_pdfs(str(output_dir))
        json_count = len(list(output_dir.rglob("*.json*")))
        categories = get_pdf_categories(str(output_dir))
        
        print(f"\nDownload summary:")
        print(f"- {pdf_count} PDF files")
        print(f"- {json_count} JSON/JSONL test files")
        print(f"- {len(categories)} PDF categories: {categories}")
        
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user. Partial files will be resumed on next run.")
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Try again in a few minutes - rate limits are temporary")
        print("2. Get a free HuggingFace token: https://huggingface.co/settings/tokens")
        print("3. Reduce --max-workers (try 1)")
        print("4. Increase --base-delay (try 5.0)")


if __name__ == "__main__":
    main()