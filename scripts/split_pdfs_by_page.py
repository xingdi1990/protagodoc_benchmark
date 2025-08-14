#!/usr/bin/env python3
"""
Split all PDFs in a directory into page-wise PDFs.

Usage examples:
  python scripts/split_pdfs_by_page.py \
    --input-dir bench/orbit_data/pdfs \
    --output-dir bench/orbit_data/pdfs

By default, the script:
- Processes all .pdf files directly under the input directory
- Skips files that already look like split outputs (e.g. name_pg3.pdf)
- Writes outputs as: <stem>_pg<1-based-index>.pdf
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Iterable, List

try:
    from pypdf import PdfReader, PdfWriter
except Exception as import_error:  # pragma: no cover - informative message for missing deps
    raise SystemExit(
        "Missing dependency 'pypdf'. Install requirements first (e.g., pip install -r requirements.txt)."
    ) from import_error


SPLIT_OUTPUT_PATTERN = re.compile(r"_pg(\d+)\.pdf$", re.IGNORECASE)


def find_input_pdfs(input_dir: Path) -> List[Path]:
    """Return all PDF files in the directory, excluding already split outputs."""
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory does not exist or is not a directory: {input_dir}")

    candidates = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    # Exclude split outputs like name_pg1.pdf
    filtered = [p for p in candidates if SPLIT_OUTPUT_PATTERN.search(p.name) is None]
    return sorted(filtered)


def split_pdf_file(pdf_path: Path, output_dir: Path, force: bool = False) -> List[Path]:
    """Split a single PDF into one-file-per-page under output_dir.

    Returns a list of written file paths.
    """
    logging.info("Splitting PDF: %s", pdf_path)

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as read_error:
        logging.error("Failed to open PDF '%s': %s", pdf_path, read_error)
        return []

    num_pages = len(reader.pages)
    if num_pages == 0:
        logging.warning("PDF has 0 pages, skipping: %s", pdf_path)
        return []

    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: List[Path] = []
    for page_index in range(num_pages):
        page_number = page_index + 1  # 1-based for filenames
        writer = PdfWriter()
        writer.add_page(reader.pages[page_index])

        # Try propagating metadata when available (optional)
        try:
            if reader.metadata:
                writer.add_metadata(dict(reader.metadata))
        except Exception:
            # Metadata issues shouldn't block splitting
            pass

        out_name = f"{pdf_path.stem}_pg{page_number}.pdf"
        out_path = output_dir / out_name

        if out_path.exists() and not force:
            logging.debug("Output exists (skip): %s", out_path)
            continue

        try:
            with out_path.open("wb") as out_file:
                writer.write(out_file)
            written_files.append(out_path)
            logging.debug("Wrote: %s", out_path)
        except Exception as write_error:
            logging.error("Failed to write '%s': %s", out_path, write_error)

    logging.info("Finished '%s': wrote %d files", pdf_path.name, len(written_files))
    return written_files


def split_all_pdfs(input_dir: Path, output_dir: Path, force: bool = False) -> int:
    """Split all PDFs in input_dir. Returns count of PDFs processed (attempted)."""
    pdfs = find_input_pdfs(input_dir)
    if not pdfs:
        logging.warning("No input PDFs found under: %s", input_dir)
        return 0

    processed = 0
    for pdf_path in pdfs:
        split_pdf_file(pdf_path, output_dir, force=force)
        processed += 1
    return processed


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split PDFs into page-wise files.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("bench/orbit_data/pdfs"),
        help="Directory containing input PDFs (default: bench/orbit_data/pdfs)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write split PDFs (default: same as --input-dir)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing split files if present.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir or input_dir

    try:
        count = split_all_pdfs(input_dir=input_dir, output_dir=output_dir, force=args.force)
    except FileNotFoundError as not_found_error:
        logging.error(str(not_found_error))
        return 1
    except Exception as unexpected:
        logging.exception("Unexpected error: %s", unexpected)
        return 1

    logging.info("Processed %d PDF(s)", count)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

