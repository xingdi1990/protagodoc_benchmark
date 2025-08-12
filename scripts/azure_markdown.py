#!/usr/bin/env python3
"""
Azure Document Intelligence PDF Analyzer

This script analyzes PDF documents using Azure Document Intelligence API
and saves the complete results as pickle files along with markdown content.

Usage:
    python azure_markdown.py input.pdf output_folder
    
Example:
    python azure_markdown.py documents/sample.pdf results/
"""

import argparse
import pickle
import sys
from pathlib import Path
import os
from dotenv import load_dotenv
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentContentFormat
from azure.core.credentials import AzureKeyCredential


def analyze_pdf(pdf_path: Path, output_folder: Path):
    """
    Analyze a PDF document using Azure Document Intelligence.
    
    Args:
        pdf_path: Path to the input PDF file
        output_folder: Path to the output directory
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # 🔒 Don't hardcode secrets; use env vars instead
    endpoint = os.getenv("AZURE_DI_ENDPOINT")
    key = os.getenv("AZURE_DI_KEY")
    
    if not endpoint or not key:
        print("❌ Error: Azure Document Intelligence credentials not found!")
        print("Please set AZURE_DI_ENDPOINT and AZURE_DI_KEY in your .env file")
        sys.exit(1)
    
    if endpoint == "https://<your-resource>.cognitiveservices.azure.com/" or key == "<your-key>":
        print("❌ Error: Please update your .env file with actual Azure credentials")
        sys.exit(1)
    
    print(f"📄 Analyzing PDF: {pdf_path}")
    print(f"📁 Output folder: {output_folder}")
    
    # Create Azure Document Intelligence client
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    
    # Analyze the document
    try:
        with pdf_path.open("rb") as f:
            poller = client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=f,  # file handle as body parameter
                output_content_format=DocumentContentFormat.MARKDOWN,
            )
        
        print("🔄 Processing document...")
        result = poller.result()
        
        # Get API version from result
        api_version = getattr(result, 'api_version', None) or result.get("apiVersion", "unknown")
        
        # Create output directory with API version
        versioned_output_dir = output_folder / f"azure_pkl_{api_version}"
        versioned_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save complete result as pickle file
        pkl_file = versioned_output_dir / f"{pdf_path.stem}.pkl"
        with pkl_file.open("wb") as f:
            pickle.dump(result, f)
        
        print(f"✅ Saved complete result to: {pkl_file}")
        
        # Also save markdown content for reference
        if result.content:
            out_md = versioned_output_dir / f"{pdf_path.stem}.md"
            out_md.write_text(result.content, encoding="utf-8")
            print(f"✅ Saved Markdown content to: {out_md}")
        
        print("🎉 Analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        sys.exit(1)


def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze PDF documents using Azure Document Intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python azure_markdown.py document.pdf output/
  python azure_markdown.py /path/to/file.pdf /path/to/output/
        """
    )
    
    parser.add_argument(
        "pdf", 
        type=str,
        help="Path to the input PDF file"
    )
    
    parser.add_argument(
        "output_folder",
        type=str, 
        help="Path to the output directory"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Convert to Path objects and validate
    pdf_path = Path(args.pdf)
    output_folder = Path(args.output_folder)
    
    # Validate input file
    if not pdf_path.exists():
        print(f"❌ Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    if not pdf_path.is_file():
        print(f"❌ Error: Path is not a file: {pdf_path}")
        sys.exit(1)
        
    if pdf_path.suffix.lower() != '.pdf':
        print(f"❌ Error: File is not a PDF: {pdf_path}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Analyze the PDF
    analyze_pdf(pdf_path, output_folder)


if __name__ == "__main__":
    main()
