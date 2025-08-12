#!/bin/bash

# Simple Azure Document Intelligence batch processor
# Processes all PDF files in orbit_v1/pdf directory

PDF_DIR="/Users/xingdi/Documents/protagodoc_benchmark/datasets/orbit_v1/pdf"
OUTPUT_DIR="/Users/xingdi/Documents/protagodoc_benchmark/datasets/orbit_v1"

# Check if PDF directory exists
if [[ ! -d "$PDF_DIR" ]]; then
    echo "Error: PDF directory not found: $PDF_DIR"
    exit 1
fi

echo "Processing PDFs from: $PDF_DIR"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Count files first
file_count=$(ls "$PDF_DIR"/*.pdf 2>/dev/null | wc -l)
echo "Found $file_count PDF files"
echo ""

# Process each PDF file
count=0
for pdf_file in "$PDF_DIR"/*.pdf; do
    if [[ -f "$pdf_file" ]]; then
        count=$((count + 1))
        filename=$(basename "$pdf_file")
        echo "[$count/$file_count] Processing: $filename"
        
        # Run Azure script
        python scripts/azure_markdown.py "$pdf_file" "$OUTPUT_DIR"
        
        echo ""
    fi
done

echo "Processing complete!"
