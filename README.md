
# ProtagoDoc Benchmark

A comprehensive benchmarking framework for evaluating OCR tools and table extraction systems, with a focus on document understanding and statistical analysis.

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Create and activate environment
conda create --name benchmark python=3.10
conda activate benchmark

# Install the benchmark system
pip install -e .[bench]
```

### 2. Run Your First Benchmark

```bash
# Test with sample data (mock results included)
python -m bench.benchmark --dir bench/sample_data --candidate marker --force

# # Convert PDFs with MinerU (when installed)
# python -m bench.convert mineru --dir bench/sample_data
```

## 📊 Benchmark System

### Features
- **Statistical Analysis** - Bootstrap confidence intervals and rigorous evaluation
- **Multiple OCR Tools** - MinerU, Azure Document Intelligence, and more
- **Table-Focused Testing** - Specialized tests for table extraction accuracy
- **Comprehensive Reporting** - Detailed HTML reports with visualizations
- **Extensible Framework** - Easy to add new OCR tools and test types

### Usage

#### Running Benchmarks
```bash
# Benchmark a specific OCR tool
python -m bench.benchmark --dir bench/sample_data --candidate mineru --force

# Compare all available results
python -m bench.benchmark --dir bench/sample_data --force

# Generate detailed HTML report
python -m bench.benchmark --dir bench/sample_data --test_report results.html
```

#### Converting Documents
```bash
# Convert PDFs with MinerU
python -m bench.convert mineru --dir bench/sample_data

# Convert with multiple tools (when available)
python -m bench.convert mineru --dir bench/sample_data
```

### Directory Structure
```
bench/
├── benchmark.py      # Main benchmark runner
├── convert.py        # OCR conversion orchestrator
├── runners/          # OCR tool integrations
│   ├── run_mineru.py    # MinerU integration
├── sample_data/      # Test data and results
│   ├── pdfs/            # Source PDF documents
│   ├── mineru/          # MinerU results
│   └── table_tests.jsonl # Test definitions
└── tests.py         # Test evaluation logic
```

### Test Types

#### Baseline Tests
- **Content Extraction** - Verify basic text content is extracted
- **Document Structure** - Ensure proper document parsing

#### Table Tests
- **Table Detection** - Check if tables are identified
- **Cell Content** - Verify specific cell values
- **Table Structure** - Validate row/column relationships
- **Header Recognition** - Test header identification

#### Example Test Definition
```json
{"pdf": "document.pdf", "page": 1, "id": "table_test_01", "type": "table", "cell_value": "Revenue", "row_heading": "2023", "col_heading": "Category"}
```

## 🔧 Adding Your Own Data

### 1. Add PDFs
```bash
# Copy your PDFs to the test directory
cp your_documents/*.pdf bench/sample_data/pdfs/
```

### 2. Create Test Definitions
```json
# Add to bench/sample_data/your_tests.jsonl
{"pdf": "your_doc.pdf", "page": 1, "id": "custom_test", "type": "present", "text": "Expected Content"}
{"pdf": "your_doc.pdf", "page": 1, "id": "table_test", "type": "table", "cell_value": "123.45", "row_heading": "Total"}
```

### 3. Run Your Tests
```bash
python -m bench.benchmark --dir bench/sample_data --force
```

## 🛠️ Azure Document Intelligence Setup (Optional)

For Azure Document Intelligence integration:

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual Azure credentials:**
   ```bash
   AZURE_DI_ENDPOINT=https://your-actual-resource.cognitiveservices.azure.com/
   AZURE_DI_KEY=your-actual-api-key-here
   ```

3. **Install Azure dependencies:**
   ```bash
   pip install -e .[azure]
   ```

## 📈 Understanding Results

### Benchmark Output Example
```
============================================================
Final Summary with 95% Confidence Intervals:
mineru               : Average Score: 95.2% ± 3.1% (average of per-JSONL scores)
    baseline: 100.0% average pass rate over 20 tests
    present : 88.5% average pass rate over 15 tests  
    table   : 92.0% average pass rate over 12 tests

    Results by JSONL file:
        table_tests.jsonl             : 95.2% (40/42 tests)
```

### Metrics Explained
- **Average Score** - Overall performance across all test types
- **Confidence Intervals** - Statistical confidence in the results
- **Test Categories** - Performance breakdown by test type
- **Pass Rates** - Percentage of tests passed in each category

### Test Types
- **baseline** - Basic content extraction (should be ~100%)
- **present** - Text presence verification
- **table** - Table structure and content tests
- **math** - Mathematical equation rendering
- **order** - Reading order preservation

## 🔧 Advanced Usage

### Custom OCR Tool Integration

Create a new runner in `bench/runners/`:

```python
# bench/runners/run_your_tool.py
def your_tool_ocr(pdf_path: str, **kwargs) -> str:
    """
    Process PDF with your OCR tool and return markdown.
    """
    # Your OCR processing logic here
    return markdown_content
```

Update `bench/convert.py`:
```python
available_methods = {
    "your_tool": ("bench.runners.run_your_tool", "your_tool_ocr"),
    # ... other methods
}
```

### Batch Processing

```bash
# Process multiple documents
for pdf in datasets/orbit_v1/pdf/*.pdf; do
    cp "$pdf" bench/sample_data/pdfs/
done

# Run batch conversion
python -m bench.convert mineru --dir bench/sample_data

# Benchmark all results
python -m bench.benchmark --dir bench/sample_data --force
```

### Custom Test Creation

```json
{
  "pdf": "financial_report.pdf",
  "page": 1, 
  "id": "revenue_table_q4",
  "type": "table",
  "cell_value": "1,234,567",
  "row_heading": "Q4 2023",
  "col_heading": "Revenue",
  "threshold": 0.9
}
```

### Statistical Analysis Options

```bash
# Increase bootstrap samples for more precise confidence intervals
python -m bench.benchmark --dir bench/sample_data --bootstrap_samples 5000

# Change confidence level
python -m bench.benchmark --dir bench/sample_data --confidence_level 0.99

# Sample subset of tests for quick evaluation
python -m bench.benchmark --dir bench/sample_data --sample 50
```

## 🐛 Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Reinstall in development mode
pip install -e .[bench]
```

**Missing Dependencies:**
```bash
# Install all benchmark dependencies
pip install scipy pandas matplotlib seaborn beautifulsoup4 playwright fuzzywuzzy python-levenshtein tabulate fuzzysearch attrs
```

**MinerU Not Found:**
```bash
# Install MinerU following their documentation
# https://github.com/opendatalab/MinerU
```

**Empty Results:**
```bash
# Check if markdown files exist
ls bench/sample_data/mineru/

# Verify test definitions
python -c "import json; [print(json.loads(line)) for line in open('bench/sample_data/table_tests.jsonl')]"
```

## 🤝 Contributing

### Adding New Test Types

1. **Define Test Class** in `bench/tests.py`:
```python
class YourCustomTest(BasePDFTest):
    def evaluate_single_pdf(self, pdf_content: str, repeat_detector) -> Tuple[bool, str]:
        # Your test logic here
        return passed, explanation
```

2. **Update Test Loading** in `bench/tests.py`:
```python
def load_tests(test_files):
    # Add your test type to the mapping
    if test_dict["type"] == "your_type":
        return YourCustomTest(...)
```

### Performance Optimization

- Use `--parallel` flag for concurrent processing
- Implement caching in custom runners
- Use `--sample N` for quick testing during development

## 📚 References

1. **MinerU**: https://github.com/opendatalab/MinerU
2. **Azure Document Intelligence**: https://docs.microsoft.com/en-us/azure/cognitive-services/form-recognizer/
3. **Statistical Analysis**: Bootstrap confidence intervals for robust evaluation
4. **Original olmOCR Framework**: Adapted for table extraction benchmarking

# Data Preparation
### Orbit Dataset

The Orbit dataset is a collection of PDF documents with tables. There are two versions, one is a small version with 176 PDF documents, and the other is the larger version with 1000 PDF documents. All the code is tested on the small version.

You can download the datasets from Google Drive (requires sign-in):
- v1 version: [Download here](https://drive.google.com/file/d/1PzmTsmBIAXAcUXQHjWwY6o6T0IjKMtct/view?usp=drive_link)
- v2 version: [Download here](https://drive.google.com/file/d/11qRpGk8bbQfChQ6pOFdOnUqtkTZAd_yJ/view?usp=drive_link)
- v3 version: [Download here](https://drive.google.com/file/d/1Uyb-ImPfH6UirS33mSHGkAyC836pwrgf/view?usp=drive_link)

Alternatively, you can use gdown to download the datasets (requires Google Drive access):

```bash
# Install gdown if you haven't already
conda create --name benchmark python=3.10
conda activate benchmark

pip install gdown
cd scripts/
bash ./download_datasets.sh

```

> [!NOTE]
> Both download methods require access to the Google Drive files. If you don't have access, please contact the repository maintainers.

After downloading the dataset, you can unzip the files and put them in the `inputs/orbit_v1` directory. It should contains the following files:

```
inputs/orbit_v1/
├── pdf
│   ├── f_0AibR1dz.pdf
│   ├── ...
├── azure_pkl
│   ├── f_0AibR1dz.pkl
│   ├── ...
├── azure_pages
│   ├── f_0AibR1dz.pages.txt
│   ├── ... 
├── azure_blocks
│   ├── f_0AibR1dz.blocks.txt
│   ├── ...
├── index.xlsx
```
