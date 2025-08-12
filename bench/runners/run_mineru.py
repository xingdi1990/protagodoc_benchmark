#!/usr/bin/env python3
"""
MinerU Runner for protagodoc_benchmark

This runner integrates MinerU with the benchmark framework.
"""

import os
import sys
import subprocess
import tempfile
import json
from pathlib import Path
import argparse


def mineru_ocr(pdf_path: str, **kwargs) -> str:
    """
    Process a PDF with MinerU and return markdown.
    
    Args:
        pdf_path: Path to the PDF file
        **kwargs: Additional arguments (unused but kept for compatibility)
        
    Returns:
        str: Markdown content extracted from the PDF
    """
    pdf_path = Path(pdf_path)
    
    # Create temporary directory for MinerU output
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_output = Path(temp_dir) / "output"
        temp_output.mkdir(exist_ok=True)
        
        try:
            # Run MinerU command
            cmd = [
                "magic-pdf",
                "-p", str(pdf_path),
                "-o", str(temp_output),
                "-m", "ocr"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                print(f"MinerU failed for {pdf_path}: {result.stderr}")
                return ""
            
            # Find the markdown file in the output
            pdf_stem = pdf_path.stem
            markdown_files = list(temp_output.rglob(f"{pdf_stem}*.md"))
            
            if not markdown_files:
                # Try to find any markdown file
                markdown_files = list(temp_output.rglob("*.md"))
            
            if markdown_files:
                with open(markdown_files[0], 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"No markdown output found for {pdf_path}")
                return ""
                
        except subprocess.TimeoutExpired:
            print(f"MinerU timed out for {pdf_path}")
            return ""
        except Exception as e:
            print(f"Error processing {pdf_path} with MinerU: {e}")
            return ""


def main():
    """Command-line interface for MinerU runner."""
    parser = argparse.ArgumentParser(description="Run MinerU on PDFs")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--output", help="Output path for markdown file")
    
    args = parser.parse_args()
    
    # Process the PDF
    markdown_content = mineru_ocr(args.pdf_path)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Saved markdown to: {args.output}")
    else:
        print(markdown_content)


if __name__ == "__main__":
    main()