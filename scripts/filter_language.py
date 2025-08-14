#!/usr/bin/env python3
"""
PDF Language Detection and Uniform Distribution Sampling Script

This script detects the language of PDF files and samples them uniformly
across different languages, organizing them into language-specific directories.
"""

import os
import sys
import argparse
import shutil
import random
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import logging
import contextlib
import io

# PDF processing imports
try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not found. Installing...")
    os.system("pip install PyMuPDF")
    import fitz

# Suppress PyMuPDF warning messages for cleaner output
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="fitz")

# Language detection imports  
try:
    import langid
except ImportError:
    print("langid not found. Installing...")
    os.system("pip install langid")
    import langid

# Configure langid for better accuracy (optional - comment out to use all supported languages)
# langid.set_languages(['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar', 'hi', 'th', 'vi', 'nl', 'sv', 'no', 'da', 'fi'])

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@contextlib.contextmanager
def suppress_stderr():
    """Context manager to suppress stderr output (for MuPDF error messages)."""
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr


def extract_text_from_pdf(pdf_path: str, max_pages: int = 3) -> str:
    """
    Extract text from PDF file using PyMuPDF, limiting to first few pages for efficiency.
    
    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to process for language detection
        
    Returns:
        Extracted text content
    """
    doc = None
    try:
        # Open PDF with PyMuPDF with error handling for widget issues
        # Suppress stderr to prevent MuPDF error messages from cluttering output
        try:
            with suppress_stderr():
                doc = fitz.open(pdf_path)
        except Exception as open_error:
            # Handle common PyMuPDF errors including widget appearance errors
            error_msg = str(open_error).lower()
            if any(keyword in error_msg for keyword in ["widget", "appearance", "stream", "form"]):
                logger.debug(f"Skipping PDF with widget/form issues: {pdf_path}")
            else:
                logger.debug(f"Error opening PDF {pdf_path}: {open_error}")
            return ""
        
        text = ""
        
        # Process up to max_pages for language detection
        pages_to_process = min(len(doc), max_pages)
        
        for page_num in range(pages_to_process):
            try:
                with suppress_stderr():
                    page = doc[page_num]
                    # Use different text extraction methods to handle various PDF types
                    try:
                        page_text = page.get_text()
                    except Exception as text_error:
                        # Try alternative text extraction if standard method fails
                        try:
                            page_text = page.get_text("text")
                        except Exception:
                            logger.debug(f"Failed to extract text from page {page_num} in {pdf_path}: {text_error}")
                            continue
                    
                    text += page_text + "\n"
                
            except Exception as page_error:
                logger.debug(f"Error processing page {page_num} from {pdf_path}: {page_error}")
                continue
        
        return text.strip()
        
    except Exception as e:
        logger.warning(f"Unexpected error reading PDF {pdf_path}: {e}")
        return ""
    
    finally:
        # Ensure document is always closed to prevent resource leaks
        if doc is not None:
            try:
                with suppress_stderr():
                    doc.close()
            except Exception as close_error:
                logger.debug(f"Error closing document {pdf_path}: {close_error}")


def detect_language(text: str, min_length: int = 50) -> str:
    """
    Detect the language of the given text using langid.
    
    Args:
        text: Text to analyze
        min_length: Minimum text length required for detection
        
    Returns:
        Detected language code or 'unknown'
    """
    if not text or len(text.strip()) < min_length:
        return 'unknown'
    
    try:
        # Clean text for better detection
        clean_text = text.replace('\n', ' ').replace('\t', ' ')
        clean_text = ' '.join(clean_text.split())
        
        if len(clean_text) < min_length:
            return 'unknown'
            
        # langid.classify returns (language, confidence)
        language, confidence = langid.classify(clean_text)
        
        # Log confidence for debugging
        logger.debug(f"Language detection: {language} (confidence: {confidence:.3f})")
        
        # langid returns negative log probabilities - closer to 0 is better
        # Accept languages with reasonable confidence (> -50000 for very low threshold)
        if confidence > -50000:
            return language
        else:
            return 'unknown'
        
    except Exception as e:
        logger.warning(f"Error detecting language: {e}")
        return 'unknown'


def get_pdf_files(input_dir: str) -> List[str]:
    """
    Get all PDF files from the input directory recursively.
    
    Args:
        input_dir: Input directory path
        
    Returns:
        List of PDF file paths
    """
    pdf_files = []
    input_path = Path(input_dir)
    
    if not input_path.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return []
    
    # Find all PDF files recursively
    for pdf_file in input_path.rglob("*.pdf"):
        if pdf_file.is_file():
            pdf_files.append(str(pdf_file))
    
    logger.info(f"Found {len(pdf_files)} PDF files in {input_dir}")
    return pdf_files


def sample_uniform_distribution(language_files: Dict[str, List[str]], 
                              samples_per_language: int = None) -> Dict[str, List[str]]:
    """
    Sample files uniformly across languages.
    
    Args:
        language_files: Dictionary mapping languages to file lists
        samples_per_language: Number of samples per language (None for auto)
        
    Returns:
        Dictionary with sampled files per language
    """
    if not language_files:
        return {}
    
    # Calculate samples per language if not specified
    if samples_per_language is None:
        # Use the minimum count across languages, or a reasonable default
        min_files = min(len(files) for files in language_files.values() if files)
        samples_per_language = min(min_files, 100)  # Cap at 100 files per language
    
    logger.info(f"Sampling {samples_per_language} files per language")
    
    sampled_files = {}
    for language, files in language_files.items():
        if len(files) <= samples_per_language:
            # Take all files if we have fewer than requested
            sampled_files[language] = files.copy()
        else:
            # Random sample without replacement
            sampled_files[language] = random.sample(files, samples_per_language)
    
    return sampled_files


def organize_files_by_language(input_dir: str, output_dir: str, 
                             samples_per_language: int = None, 
                             max_files_to_process: int = None):
    """
    Main function to organize PDF files by detected language.
    
    Args:
        input_dir: Input directory containing PDF files
        output_dir: Output directory for organized files
        samples_per_language: Number of samples per language
        max_files_to_process: Maximum number of files to process (for testing)
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = get_pdf_files(input_dir)
    if not pdf_files:
        logger.error("No PDF files found!")
        return
    
    # Limit files for testing if specified
    if max_files_to_process and len(pdf_files) > max_files_to_process:
        pdf_files = random.sample(pdf_files, max_files_to_process)
        logger.info(f"Processing random sample of {max_files_to_process} files")
    
    # Detect languages
    language_files = defaultdict(list)
    language_stats = Counter()
    
    logger.info("Starting language detection...")
    for i, pdf_path in enumerate(pdf_files, 1):
        if i % 50 == 0:
            logger.info(f"Processed {i}/{len(pdf_files)} files")
        
        # Extract text and detect language
        text = extract_text_from_pdf(pdf_path)
        language = detect_language(text)
        
        language_files[language].append(pdf_path)
        language_stats[language] += 1
        
        logger.debug(f"File: {Path(pdf_path).name} -> Language: {language}")
    
    # Log language statistics (including unknown for debugging)
    logger.info("\nLanguage Distribution (all detected languages):")
    for lang, count in language_stats.most_common():
        percentage = (count / len(pdf_files)) * 100
        logger.info(f"  {lang}: {count} files ({percentage:.1f}%)")
    
    # Calculate statistics excluding unknown files
    known_files_count = sum(count for lang, count in language_stats.items() if lang != 'unknown')
    unknown_count = language_stats.get('unknown', 0)
    
    if unknown_count > 0:
        logger.info(f"\nNote: {unknown_count} files with unknown language will be excluded from output")
    logger.info(f"Processing {known_files_count} files with detected languages")
    
    # Filter out unknown language files before sampling
    known_language_files = {lang: files for lang, files in language_files.items() if lang != 'unknown'}
    
    # Sample files uniformly (excluding unknown)
    sampled_files = sample_uniform_distribution(known_language_files, samples_per_language)
    
    # Copy files to output directories
    total_copied = 0
    for language, files in sampled_files.items():
        if not files or language == 'unknown':
            continue
            
        # Create language-specific directory
        lang_dir = output_path / language
        lang_dir.mkdir(exist_ok=True)
        
        logger.info(f"Copying {len(files)} files for language '{language}'")
        
        for file_path in files:
            source_path = Path(file_path)
            dest_path = lang_dir / source_path.name
            
            try:
                shutil.copy2(file_path, dest_path)
                total_copied += 1
            except Exception as e:
                logger.error(f"Error copying {file_path} to {dest_path}: {e}")
    
    logger.info(f"\nCompleted! Copied {total_copied} files to {output_dir}")
    
    # Create summary file
    summary_file = output_path / "language_summary.txt"
    
    # Filter out unknown from statistics for summary
    known_language_stats = {lang: count for lang, count in language_stats.items() if lang != 'unknown'}
    
    with open(summary_file, 'w') as f:
        f.write("PDF Language Detection Summary\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Total files processed: {len(pdf_files)}\n")
        f.write(f"Files with detected languages: {known_files_count}\n")
        if unknown_count > 0:
            f.write(f"Files with unknown language (excluded): {unknown_count}\n")
        f.write(f"Total files copied: {total_copied}\n\n")
        
        f.write("Language Distribution (before sampling, excluding unknown):\n")
        # Calculate percentages based on known files only
        for lang, count in Counter(known_language_stats).most_common():
            percentage = (count / known_files_count) * 100 if known_files_count > 0 else 0
            f.write(f"  {lang}: {count} files ({percentage:.1f}%)\n")
        
        f.write("\nSampled Distribution (after uniform sampling):\n")
        for language, files in sampled_files.items():
            f.write(f"  {language}: {len(files)} files\n")
    
    logger.info(f"Summary saved to: {summary_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Detect PDF file languages and sample uniformly across languages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/filter_language.py --input-dir bench/orbit_data/pdfs_by_pages --output-dir bench/orbit_data/pdfs_by_languages
  
  python scripts/filter_language.py --input-dir data/pdfs --output-dir data/filtered --samples-per-language 50
        """
    )
    
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Input directory containing PDF files"
    )
    
    parser.add_argument(
        "--output-dir", 
        required=True,
        help="Output directory for language-organized files"
    )
    
    parser.add_argument(
        "--samples-per-language",
        type=int,
        default=None,
        help="Number of samples per language (default: auto-detect minimum)"
    )
    
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum number of files to process (useful for testing)"
    )
    
    parser.add_argument(
        "--seed",
        type=int, 
        default=42,
        help="Random seed for reproducible sampling (default: 42)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Set random seed for reproducible results
    random.seed(args.seed)
    
    logger.info("Starting PDF language detection and filtering...")
    logger.info(f"Input directory: {args.input_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    
    # Run the main processing
    organize_files_by_language(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        samples_per_language=args.samples_per_language,
        max_files_to_process=args.max_files
    )
    
    logger.info("Processing complete!")


if __name__ == "__main__":
    main()
