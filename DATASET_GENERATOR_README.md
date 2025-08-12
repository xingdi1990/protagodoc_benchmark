# Dataset Generator for OLMoCR-Bench Style Test Cases

This toolkit generates benchmark test cases from PDF documents using GPT-4o, following the methodology from Section F of the OLMoCR-Bench paper.

## Overview

The generator creates 5 types of test cases:

1. **Text Presence Tests** (`present`): Verify specific text appears in OCR output
2. **Text Absence Tests** (`absent`): Ensure headers/footers/metadata don't appear  
3. **Reading Order Tests** (`order`): Check text blocks appear in correct sequence
4. **Table Relationship Tests** (`table`): Validate table cell relationships
5. **Mathematical Equation Tests** (`math`): Verify LaTeX equations are preserved

## Quick Start

### 1. Setup

```bash
# Install dependencies
python setup_generator.py

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

### 2. Run Example

```bash
# Generate test cases from sample PDFs
python example_generate.py
```

### 3. Custom Generation

```bash
# Generate from your own PDFs
python generate_dataset.py --pdf_dir /path/to/your/pdfs --output my_dataset.jsonl
```

## Detailed Usage

### Command Line Options

```bash
python generate_dataset.py \
    --pdf_dir /path/to/pdfs \           # Directory with PDF files
    --output dataset.jsonl \            # Output JSONL file
    --api_key your_key \                # OpenAI API key (or use env var)
    --model gpt-4o \                    # GPT model to use (default)
    --max_pdfs 10 \                     # Max PDFs to process
    --max_tests_per_type 5 \            # Max tests per type per page
    --workers 4                         # Parallel workers
```

### Programmatic Usage

```python
from generate_dataset import DatasetGenerator

# Initialize generator
generator = DatasetGenerator(api_key="your-key")

# Generate dataset
generator.generate_dataset(
    pdf_dir="path/to/pdfs",
    output_file="dataset.jsonl",
    max_tests_per_type=5
)
```

## Test Case Format

The generator creates test cases in JSONL format matching the OLMoCR-Bench structure:

### Text Presence Test
```json
{
    "pdf": "document.pdf",
    "page": 1,
    "id": "document_present_abc123",
    "type": "present", 
    "text": "The quick brown fox jumps over the lazy dog.",
    "max_diffs": 2
}
```

### Text Absence Test  
```json
{
    "pdf": "document.pdf",
    "page": 1,
    "id": "document_absent_def456",
    "type": "absent",
    "text": "Page 1"
}
```

### Reading Order Test
```json
{
    "pdf": "document.pdf", 
    "page": 1,
    "id": "document_order_ghi789",
    "type": "order",
    "before": "First sentence in reading order.",
    "after": "Second sentence that should follow.",
    "max_diffs": 3
}
```

### Table Relationship Test
```json
{
    "pdf": "document.pdf",
    "page": 1, 
    "id": "document_table_jkl012",
    "type": "table",
    "cell": "3.32T",
    "left": "3.71T",
    "top_heading": "Words"
}
```

### Math Equation Test
```json
{
    "pdf": "document.pdf",
    "page": 1,
    "id": "document_math_mno345", 
    "type": "math",
    "math": "e^{i \\pi} + 1 = 0"
}
```

## How It Works

### 1. PDF Processing
- Converts each PDF page to high-resolution image (2048px)
- Extracts text content for context
- Processes pages in parallel for efficiency

### 2. GPT-4o Analysis
- Sends page image + prompts to GPT-4o
- Uses structured output format for consistent JSON
- Employs different prompts for each test type

### 3. Test Generation Pipeline

#### Text Presence/Absence
1. Extract meaningful sentences from main content
2. Identify headers/footers/metadata to exclude
3. Generate presence tests for content, absence tests for metadata

#### Reading Order  
1. Analyze document layout and reading flow
2. Extract sentence pairs in natural reading order
3. Create order tests with fuzzy matching tolerance

#### Table Relationships
1. Detect tables in document images
2. For each table cell, query relationships (up/down/left/right/headings)
3. Generate relationship tests with cell positions

#### Mathematical Equations
1. Identify mathematical expressions in document
2. Convert to proper LaTeX format for KaTeX compatibility
3. Create equation tests for OCR math preservation

### 4. Quality Controls
- Fuzzy matching with configurable tolerance (`max_diffs`)
- Sentence length and quality filters
- Duplicate detection and removal
- Parallel processing with error handling

## Configuration

### Test Generation Parameters

- **max_tests_per_type**: Controls number of tests generated per type per page
- **max_diffs**: Fuzzy matching tolerance (auto-calculated based on text length)
- **target_dim**: Image resolution for PDF conversion (default: 2048px)
- **temperature**: GPT model temperature (default: 0.1 for consistency)

### Performance Tuning

- **num_workers**: Parallel processing threads (balance speed vs API rate limits)
- **max_pdfs**: Limit PDFs processed (useful for testing)
- **pages_per_pdf**: Process first N pages only (default: 3)

## API Usage and Costs

### Rate Limits
- Uses OpenAI **GPT-4o** API with vision capabilities (latest model)
- Recommended: 2-4 workers to avoid rate limits
- Each page requires 2-5 API calls depending on content

### Cost Estimation
- ~$0.01-0.05 per PDF page processed
- Varies based on image size and response length
- Table-heavy documents cost more due to additional analysis
- **GPT-4o** provides better accuracy and reasoning than older models

## Output Validation

The generator includes validation for:
- JSON format correctness
- Required field presence
- Text length and quality
- LaTeX equation syntax (for math tests)
- Relationship consistency (for table tests)

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Install missing dependencies
python setup_generator.py
```

**API Key Issues**
```bash
# Set environment variable
export OPENAI_API_KEY="your-key"

# Or pass directly
python generate_dataset.py --api_key your-key ...
```

**PDF Processing Errors**
- Ensure PyMuPDF is installed: `pip install PyMuPDF`
- Check PDF file permissions and corruption
- Try reducing `target_dim` for large files

**Rate Limit Errors**
- Reduce `num_workers` (try 1-2)
- Add delays between requests
- Check your OpenAI API tier limits

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Extending the Generator

### Adding New Test Types

1. Create new generator class inheriting from `BaseTestGenerator`
2. Implement `generate_tests()` method
3. Add to `DatasetGenerator.generators` dict
4. Update test type enum and validation

### Custom Prompts

Modify prompts in each generator class:
- `TextPresenceGenerator._extract_sentences()`
- `TableTestGenerator._generate_table_relationships()`
- etc.

### Custom Validation

Add validation logic in:
- `BaseTestGenerator._make_gpt_request()`
- Individual generator classes
- Main `DatasetGenerator` class

## Examples

See the `bench/sample_data/dataset.jsonl` file for examples of the expected output format.

## Contributing

When adding features:
1. Follow the existing code structure
2. Add appropriate error handling
3. Update this README
4. Test with sample PDFs

## License

This tool follows the same license as the main protagodoc_benchmark project.
