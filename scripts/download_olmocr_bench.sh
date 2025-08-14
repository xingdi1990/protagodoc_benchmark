#!/bin/bash
# Download olmOCR-bench dataset with rate limiting protection
# This script handles the common 429 "Too Many Requests" errors from HuggingFace

set -e  # Exit on any error

echo "🚀 Starting olmOCR-bench dataset download..."

# Default parameters
OUTPUT_DIR="./olmOCR-bench"
MAX_WORKERS=2
MAX_RETRIES=5
BASE_DELAY=2.0

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --token)
            HF_TOKEN="$2"
            shift 2
            ;;
        --max-workers)
            MAX_WORKERS="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --output-dir DIR    Output directory (default: ./olmOCR-bench)"
            echo "  --token TOKEN       HuggingFace API token (recommended)"
            echo "  --max-workers N     Number of concurrent downloads (default: 2)"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Example:"
            echo "  $0 --output-dir ./data/olmOCR-bench --token your_hf_token"
            echo ""
            echo "Get a free HuggingFace token at:"
            echo "  https://huggingface.co/settings/tokens"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if Python script exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/download_olmocr_bench.py"

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "❌ Error: Python download script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Build Python command
PYTHON_CMD="python \"$PYTHON_SCRIPT\" --output-dir \"$OUTPUT_DIR\" --max-workers $MAX_WORKERS --max-retries $MAX_RETRIES --base-delay $BASE_DELAY"

if [[ -n "${HF_TOKEN}" ]]; then
    PYTHON_CMD="$PYTHON_CMD --token \"$HF_TOKEN\""
fi

echo "📥 Using download parameters:"
echo "  Output directory: $OUTPUT_DIR"
echo "  Max workers: $MAX_WORKERS"
echo "  Max retries: $MAX_RETRIES"
echo "  Base delay: ${BASE_DELAY}s"

if [[ -n "${HF_TOKEN}" ]]; then
    echo "  Using HuggingFace token: ${HF_TOKEN:0:8}..."
else
    echo "  No HuggingFace token provided (may hit rate limits faster)"
fi

echo ""

# Run the Python download script
eval $PYTHON_CMD

echo ""
echo "✅ Download script completed!"