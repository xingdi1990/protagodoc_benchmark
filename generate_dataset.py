#!/usr/bin/env python3
"""
Dataset Generator for OLMoCR-Bench Style Test Cases

This script generates benchmark test cases from PDF documents using GPT-4o,
following the methodology from the OLMoCR-Bench paper Section F.

Usage:
    python generate_dataset.py --pdf_dir /path/to/pdfs --output dataset.jsonl --api_key your_key

Test Types Generated:
- present: Text that should appear in OCR output
- absent: Text that should NOT appear (headers/footers)
- order: Reading order verification between text blocks
- table: Table cell relationship tests
- math: Mathematical equation verification
"""

import argparse
import json
import os
import random
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openai import OpenAI
from tqdm import tqdm

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
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
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
    
    def generate_tests_for_pdf(self, pdf_path: str, max_tests_per_type: int = 5) -> List[Dict]:
        """Generate all types of tests for a single PDF.
        
        Args:
            pdf_path: Path to the PDF file
            max_tests_per_type: Maximum number of tests to generate per type
            
        Returns:
            List of test case dictionaries
        """
        all_tests = []
        pdf_name = Path(pdf_path).name
        
        try:
            # Get number of pages
            num_pages = self.pdf_processor.get_page_count(pdf_path)
            
            # Process each page (limit to first 3 pages for efficiency)
            pages_to_process = min(3, num_pages)
            
            for page_num in range(1, pages_to_process + 1):
                print(f"Processing {pdf_name} page {page_num}...")
                
                # Convert PDF page to image
                image_base64 = self.pdf_processor.pdf_to_image(pdf_path, page_num)
                if not image_base64:
                    continue
                
                # Generate different types of tests
                page_tests = []
                
                # Text presence/absence tests
                presence_tests = self.generators['text_presence'].generate_tests(
                    pdf_path, page_num, image_base64, max_tests_per_type // 2
                )
                page_tests.extend(presence_tests)
                
                # Reading order tests
                order_tests = self.generators['text_order'].generate_tests(
                    pdf_path, page_num, image_base64, max_tests_per_type // 2
                )
                page_tests.extend(order_tests)
                
                # Table tests
                table_tests = self.generators['table'].generate_tests(
                    pdf_path, page_num, image_base64, max_tests_per_type
                )
                page_tests.extend(table_tests)
                
                # Math tests
                math_tests = self.generators['math'].generate_tests(
                    pdf_path, page_num, image_base64, max_tests_per_type
                )
                page_tests.extend(math_tests)
                
                # Header/footer tests
                header_footer_tests = self.generators['header_footer'].generate_tests(
                    pdf_path, page_num, image_base64, max_tests_per_type // 2
                )
                page_tests.extend(header_footer_tests)
                
                all_tests.extend(page_tests)
                
        except Exception as e:
            print(f"Error processing {pdf_name}: {str(e)}")
        
        return all_tests
    
    def generate_dataset(self, pdf_dir: str, output_file: str, max_pdfs: Optional[int] = None,
                        max_tests_per_type: int = 5, num_workers: int = 4) -> None:
        """Generate a complete dataset from a directory of PDFs.
        
        Args:
            pdf_dir: Directory containing PDF files
            output_file: Output JSONL file path
            max_pdfs: Maximum number of PDFs to process (None for all)
            max_tests_per_type: Maximum tests per type per page
            num_workers: Number of parallel workers
        """
        # Find all PDF files
        pdf_files = list(Path(pdf_dir).glob("**/*.pdf"))
        if max_pdfs:
            pdf_files = pdf_files[:max_pdfs]
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        all_tests = []
        
        # Process PDFs in parallel
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks
            future_to_pdf = {
                executor.submit(self.generate_tests_for_pdf, str(pdf_path), max_tests_per_type): pdf_path
                for pdf_path in pdf_files
            }
            
            # Collect results
            for future in tqdm(as_completed(future_to_pdf), total=len(pdf_files), desc="Processing PDFs"):
                pdf_path = future_to_pdf[future]
                try:
                    tests = future.result()
                    all_tests.extend(tests)
                except Exception as e:
                    print(f"Error processing {pdf_path}: {str(e)}")
        
        # Shuffle tests to mix different types
        random.shuffle(all_tests)
        
        # Save to JSONL file
        with open(output_file, 'w', encoding='utf-8') as f:
            for test in all_tests:
                f.write(json.dumps(test, ensure_ascii=False) + '\n')
        
        print(f"Generated {len(all_tests)} test cases and saved to {output_file}")
        
        # Print summary statistics
        self._print_summary(all_tests)
    
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
    parser.add_argument("--output", required=True, help="Output JSONL file path")
    parser.add_argument("--api_key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--model", default="gpt-4o", help="GPT model to use")
    parser.add_argument("--max_pdfs", type=int, help="Maximum number of PDFs to process")
    parser.add_argument("--max_tests_per_type", type=int, default=5, help="Max tests per type per page")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key must be provided via --api_key or OPENAI_API_KEY env var")
    
    # Verify PDF directory exists
    if not os.path.isdir(args.pdf_dir):
        raise ValueError(f"PDF directory {args.pdf_dir} does not exist")
    
    # Create output directory if needed
    output_dir = os.path.dirname(args.output)
    if output_dir:  # Only create directory if there is one
        os.makedirs(output_dir, exist_ok=True)
    
    # Generate dataset
    generator = DatasetGenerator(api_key, args.model)
    generator.generate_dataset(
        pdf_dir=args.pdf_dir,
        output_file=args.output,
        max_pdfs=args.max_pdfs,
        max_tests_per_type=args.max_tests_per_type,
        num_workers=args.workers
    )


if __name__ == "__main__":
    main()
