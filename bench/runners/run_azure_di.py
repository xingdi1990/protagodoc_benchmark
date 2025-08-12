#!/usr/bin/env python3
"""
Azure Document Intelligence Runner for protagodoc_benchmark

This runner integrates Azure Document Intelligence with the benchmark framework.
"""

import os
import sys
from pathlib import Path
import argparse
from dotenv import load_dotenv
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentContentFormat
from azure.core.credentials import AzureKeyCredential


def azure_di_ocr(pdf_path: str, **kwargs) -> str:
    """
    Process a PDF with Azure Document Intelligence and return markdown.
    
    Args:
        pdf_path: Path to the PDF file
        **kwargs: Additional arguments (unused but kept for compatibility)
        
    Returns:
        str: Markdown content extracted from the PDF
    """
    # Load environment variables
    load_dotenv()
    
    endpoint = os.getenv("AZURE_DI_ENDPOINT")
    key = os.getenv("AZURE_DI_KEY")
    
    if not endpoint or not key:
        raise ValueError("Azure Document Intelligence credentials not found in environment variables")
    
    # Initialize Azure client
    client = DocumentIntelligenceClient(
        endpoint=endpoint, 
        credential=AzureKeyCredential(key)
    )
    
    try:
        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document(
                "prebuilt-layout",
                body=f,
                content_type="application/pdf",
                output_content_format=DocumentContentFormat.MARKDOWN
            )
        
        result = poller.result()
        return result.content if result.content else ""
        
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return ""


def main():
    """Command-line interface for Azure DI runner."""
    parser = argparse.ArgumentParser(description="Run Azure Document Intelligence on PDFs")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--output", help="Output path for markdown file")
    
    args = parser.parse_args()
    
    # Process the PDF
    markdown_content = azure_di_ocr(args.pdf_path)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Saved markdown to: {args.output}")
    else:
        print(markdown_content)


if __name__ == "__main__":
    main()