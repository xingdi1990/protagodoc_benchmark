#!/usr/bin/env python3
"""
Dataset Generator for OLMoCR-Bench Style Test Cases

This script generates benchmark test cases from PDF documents using GPT-4o,
following the methodology from the OLMoCR-Bench paper Section F.

Usage:
    python generate_dataset.py --pdf_dir /path/to/pdfs --output /path/to/output --api_key your_key

Test Types Generated:
- present: Text that should appear in OCR output
- absent: Text that should NOT appear (headers/footers)
- order: Reading order verification between text blocks
- table: Table cell relationship tests
- math: Mathematical equation verification
"""

import argparse
import sys
import json
import os
import random
import uuid
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv

from dataset_generators import (
    PDFProcessor,
    TextPresenceGenerator,
    TextOrderGenerator,
    TableTestGenerator,
    MathTestGenerator,
    HeaderFooterGenerator
)


class DatasetGenerator:
    """Main class for generating OLMoCR-Bench style datasets."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-2024-08-06"):
        """Initialize the dataset generator.
        
        Args:
            api_key: OpenAI API key
            model: GPT model to use for generation
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.pdf_processor = PDFProcessor()
        
        # Initialize test generators
        self.generators = {
            'text_presence': TextPresenceGenerator(self.client, self.model),
            'text_order': TextOrderGenerator(self.client, self.model),
            'table': TableTestGenerator(self.client, self.model),
            'math': MathTestGenerator(self.client, self.model),
            'header_footer': HeaderFooterGenerator(self.client, self.model)
        }
    
    def generate_tests_for_pdf(self, pdf_path: str, max_tests_per_type: int = 5, relative_path: Optional[str] = None) -> List[Dict]:
        """Generate all types of tests for a single PDF.
        
        Args:
            pdf_path: Path to the PDF file
            max_tests_per_type: Maximum number of tests to generate per type
            relative_path: Relative path from base directory (includes folder)
            
        Returns:
            List of test case dictionaries
        """
        all_tests = []
        pdf_name = Path(pdf_path).name
        # Use relative path if provided, otherwise just the filename
        pdf_display_name = relative_path if relative_path else pdf_name
        # Detect split-page filename pattern: {filename}_pg{n}.pdf
        split_match = re.match(r"^(?P<base>.+?)_pg(?P<page>\d+)\.pdf$", pdf_name, flags=re.IGNORECASE)
        
        try:
            if split_match:
                # Handle split-page PDF file, e.g., {filename}_pg2.pdf
                base_name = split_match.group('base') + '.pdf'
                logical_page_num = int(split_match.group('page'))
                print(f"Processing {pdf_name} (logical {base_name} page {logical_page_num})...")

                # For split files, the actual document has only 1 page
                image_base64 = self.pdf_processor.pdf_to_image(pdf_path, 1)
                if image_base64:
                    page_tests = []

                    # Text presence/absence tests
                    presence_tests = self.generators['text_presence'].generate_tests(
                        pdf_path, 1, image_base64, max_tests_per_type
                    )
                    page_tests.extend(presence_tests)

                    # Reading order tests (disabled)
                    order_tests = self.generators['text_order'].generate_tests(
                        pdf_path, 1, image_base64, max_tests_per_type
                    )
                    page_tests.extend(order_tests)

                    # Table tests
                    table_tests = self.generators['table'].generate_tests(
                        pdf_path, 1, image_base64, max_tests_per_type
                    )
                    page_tests.extend(table_tests)

                    # # Math tests
                    # math_tests = self.generators['math'].generate_tests(
                    #     pdf_path, 1, image_base64, max_tests_per_type
                    # )
                    # page_tests.extend(math_tests)

                    # Header/footer tests
                    header_footer_tests = self.generators['header_footer'].generate_tests(
                        pdf_path, 1, image_base64, max_tests_per_type
                    )
                    page_tests.extend(header_footer_tests)

                    # Keep original filename with folder and set page to 1 for split-page PDFs
                    for t in page_tests:
                        t['pdf'] = pdf_display_name
                        t['page'] = 1

                    all_tests.extend(page_tests)
            else:
                # Handle regular multi-page PDFs
                num_pages = self.pdf_processor.get_page_count(pdf_path)
                pages_to_process = min(3, num_pages)

                for page_num in range(1, pages_to_process + 1):
                    print(f"Processing {pdf_name} page {page_num}...")

                    image_base64 = self.pdf_processor.pdf_to_image(pdf_path, page_num)
                    if not image_base64:
                        continue

                    page_tests = []

                    # Text presence/absence tests
                    presence_tests = self.generators['text_presence'].generate_tests(
                        pdf_path, page_num, image_base64, max_tests_per_type
                    )
                    page_tests.extend(presence_tests)

                    # Reading order tests (disabled)
                    order_tests = self.generators['text_order'].generate_tests(
                        pdf_path, page_num, image_base64, max_tests_per_type
                    )
                    page_tests.extend(order_tests)

                    # Table tests
                    table_tests = self.generators['table'].generate_tests(
                        pdf_path, page_num, image_base64, max_tests_per_type
                    )
                    page_tests.extend(table_tests)

                    # # Math tests
                    # math_tests = self.generators['math'].generate_tests(
                    #     pdf_path, page_num, image_base64, max_tests_per_type
                    # )
                    # page_tests.extend(math_tests)

                    # Header/footer tests
                    header_footer_tests = self.generators['header_footer'].generate_tests(
                        pdf_path, page_num, image_base64, max_tests_per_type
                    )
                    page_tests.extend(header_footer_tests)

                    # Update PDF name to include folder path if provided
                    for t in page_tests:
                        t['pdf'] = pdf_display_name

                    all_tests.extend(page_tests)

        except Exception as e:
            print(f"Error processing {pdf_name}: {str(e)}")
        
        return all_tests
    
    def generate_dataset(self, pdf_dir: str, output_dir: str, max_pdfs: Optional[int] = None,
                        max_tests_per_type: int = 5, num_workers: int = 4) -> None:
        """Generate datasets from subfolders of PDFs, creating separate JSONL files for each subfolder.
        
        Args:
            pdf_dir: Directory containing PDF subfolders
            output_dir: Directory where JSONL files will be saved
            max_pdfs: Maximum number of PDFs to process per subfolder (None for all)
            max_tests_per_type: Maximum tests per type per page
            num_workers: Number of parallel workers
        """
        pdf_dir_path = Path(pdf_dir)
        output_dir_path = Path(output_dir)
        
        # Find all subfolders that contain PDF files
        subfolders = []
        for item in pdf_dir_path.iterdir():
            if item.is_dir():
                pdf_files_in_folder = list(item.glob("*.pdf"))
                if pdf_files_in_folder:
                    subfolders.append((item.name, pdf_files_in_folder))
        
        if not subfolders:
            print(f"No subfolders with PDF files found in {pdf_dir}")
            return
        
        print(f"Found {len(subfolders)} subfolders with PDF files to process")
        
        # Process each subfolder
        for folder_name, pdf_files in subfolders:
            print(f"\nProcessing folder: {folder_name}")
            
            if max_pdfs:
                pdf_files = pdf_files[:max_pdfs]
            
            print(f"Found {len(pdf_files)} PDF files in {folder_name}")
            
            folder_tests = []
            
            # Process PDFs in parallel
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Submit all tasks
                future_to_pdf = {
                    executor.submit(
                        self.generate_tests_for_pdf, 
                        str(pdf_path), 
                        max_tests_per_type,
                        f"{folder_name}/{pdf_path.name}"  # relative path with folder
                    ): pdf_path
                    for pdf_path in pdf_files
                }
                
                # Collect results
                for future in tqdm(as_completed(future_to_pdf), total=len(pdf_files), desc=f"Processing {folder_name}"):
                    pdf_path = future_to_pdf[future]
                    try:
                        tests = future.result()
                        folder_tests.extend(tests)
                    except Exception as e:
                        print(f"Error processing {pdf_path}: {str(e)}")
            
            # Keep 'order' tests now that TextOrderGenerator is enabled. Still drop 'math' if desired.
            folder_tests = [test for test in folder_tests if test.get('type') != 'math']

            # Sort output by pdf name and then by page number
            def _to_int(value):
                try:
                    return int(value)
                except Exception:
                    return 0

            folder_tests.sort(key=lambda t: (t.get('pdf', ''), _to_int(t.get('page', 0))))
            
            # Save to JSONL file named after the folder
            output_file = output_dir_path / f"{folder_name}.jsonl"
            with open(output_file, 'w', encoding='utf-8') as f:
                for test in folder_tests:
                    f.write(json.dumps(test, ensure_ascii=False) + '\n')
            
            print(f"Generated {len(folder_tests)} test cases and saved to {output_file}")
            
            # Print summary statistics for this folder
            print(f"\nSummary for {folder_name}:")
            type_counts = {}
            for test in folder_tests:
                test_type = test.get('type', 'unknown')
                type_counts[test_type] = type_counts.get(test_type, 0) + 1
            
            print(f"  Total tests: {len(folder_tests)}")
            for test_type, count in sorted(type_counts.items()):
                print(f"    {test_type}: {count}")
    
    def _print_summary(self, tests: List[Dict]) -> None:
        """Print summary statistics of generated tests."""
        type_counts = {}
        for test in tests:
            test_type = test.get('type', 'unknown')
            type_counts[test_type] = type_counts.get(test_type, 0) + 1
        
        print("\nDataset Summary:")
        print(f"Total tests: {len(tests)}")
        for test_type, count in sorted(type_counts.items()):
            print(f"  {test_type}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Generate OLMoCR-Bench style dataset from PDFs")
    parser.add_argument("--pdf_dir", required=True, help="Directory containing PDF files")
    parser.add_argument("--output", required=True, help="Output directory for JSONL files (one file per subfolder)")
    parser.add_argument("--api_key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--model", default="gpt-4o-2024-08-06", help="GPT model to use")
    parser.add_argument("--max_pdfs", type=int, help="Maximum number of PDFs to process")
    parser.add_argument("--max_tests_per_type", type=int, default=5, help="Max tests per type per page")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    
    args = parser.parse_args()
    
    # Load environment variables from a local .env file if present
    # Use override=True so .env takes precedence over any exported var
    load_dotenv(override=True)
    
    # Get API key (trim whitespace and optional surrounding quotes)
    raw_api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    api_key = None
    if raw_api_key:
        api_key = raw_api_key.strip().strip('"').strip("'")
    if not api_key:
        raise ValueError(
            "OpenAI API key must be provided via --api_key or OPENAI_API_KEY in a .env/.env.local file"
        )

    # Fast preflight check: validate API key before heavy processing
    try:
        _client = OpenAI(api_key=api_key)
        # Listing models is lightweight and verifies the key without incurring chat costs
        _ = _client.models.list()
    except Exception as e:
        masked = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "(hidden)"
        print(
            f"Failed to validate OpenAI API key {masked}. "
            f"Error: {str(e)}\n"
            f"- Ensure your .env contains OPENAI_API_KEY without quotes or spaces.\n"
            f"- Generate a fresh key at https://platform.openai.com/account/api-keys and try again.\n"
            f"- If using Azure OpenAI, this script currently expects OpenAI platform keys."
        )
        sys.exit(1)
    
    # Verify PDF directory exists
    if not os.path.isdir(args.pdf_dir):
        raise ValueError(f"PDF directory {args.pdf_dir} does not exist")
    
    # Create output directory if needed
    os.makedirs(args.output, exist_ok=True)
    
    # Generate dataset
    generator = DatasetGenerator(api_key, args.model)
    generator.generate_dataset(
        pdf_dir=args.pdf_dir,
        output_dir=args.output,
        max_pdfs=args.max_pdfs,
        max_tests_per_type=args.max_tests_per_type,
        num_workers=args.workers
    )


if __name__ == "__main__":
    main()
