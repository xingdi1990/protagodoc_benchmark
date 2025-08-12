
# Setup

## Environment Configuration

This project uses Azure Document Intelligence API. You'll need to set up your credentials:

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual Azure credentials:**
   - Get your endpoint and API key from [Azure Portal](https://portal.azure.com)
   - Replace the placeholder values in `.env`:
     ```bash
     AZURE_DI_ENDPOINT=https://your-actual-resource.cognitiveservices.azure.com/
     AZURE_DI_KEY=your-actual-api-key-here
     ```

3. **Never commit `.env` to git** - it's already in `.gitignore` for security.

4. **Install required dependencies:**
   ```bash
   pip install python-dotenv azure-ai-documentintelligence
   ```

5. **Your notebook is ready!** The `azure_markdown.ipynb` script will automatically load your environment variables and securely connect to Azure Document Intelligence.

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

### MinerU Table Extraction

```bash
mkdir -p outputs/
mkdir -p logs/
magic-pdf -p inputs/orbit_v1/pdf -o outputs/orbit_v1_mineru133_outputs -m ocr > logs/orbit_v1_mineru133_outputs.log 2>&1
```

If you meet the error "MemoryError", you can try to change the following in "magic_pdf/tools/cli.py". This will disable the batch processing and process the file one by one.
```python
    if os.path.isdir(path):
        for doc_path in Path(path).glob('*'):
            if doc_path.suffix in pdf_suffixes + image_suffixes + ms_office_suffixes:
                parse_doc(doc_path)
    else:
        parse_doc(Path(path))
        
    # if os.path.isdir(path):
    #     doc_paths = []
    #     for doc_path in Path(path).glob('*'):
    #         if doc_path.suffix in pdf_suffixes + image_suffixes + ms_office_suffixes:
                # if doc_path.suffix in ms_office_suffixes:
                #     convert_file_to_pdf(str(doc_path), temp_dir)
                #     doc_path = Path(os.path.join(temp_dir, f'{doc_path.stem}.pdf'))
                # elif doc_path.suffix in image_suffixes:
                #     with open(str(doc_path), 'rb') as f:
                #         bits = f.read()
                #         pdf_bytes = fitz.open(stream=bits).convert_to_pdf()
                #     fn = os.path.join(temp_dir, f'{doc_path.stem}.pdf')
                #     with open(fn, 'wb') as f:
                #         f.write(pdf_bytes)
                #     doc_path = Path(fn)
                # doc_paths.append(doc_path)
        # datasets = batch_build_dataset(doc_paths, 4, lang)
        # batch_do_parse(output_dir, [str(doc_path.stem) for doc_path in doc_paths], datasets, method, debug_able, lang=lang)
    # else:
    #     parse_doc(Path(path))
```

### Table Extraction

After downloading the dataset, you can run the following command to extract the tables from the PDF documents.

```bash
mkdir -p comparison
bash extract.sh
```

In particular,  You can check the `extract.sh` file to see the detailed command. After running the script, you will get the following files:

```
comparison_results
|-- orbit100_azure_outputs_tables
|---- f_0AibR1dz.pages.tables.json
|---- ...
|-- orbit_v1_mineru133_outputs_tables
|---- f_0AibR1dz.tables.json
|---- ...
```

### Comparisons

```bash
bash comparison.sh
```

Check the "comparison.sh" for output destination and more result details. The json file should contains something similar to the following:

```json
    "summary": {
        "total_files_processed": 176,
        "overall_average_similarity": 0.5377033703165067,
        "overall_average_structure_similarity": 0.9299762187917149,
        "files_with_tables": 176,
        "overall_average_similarity_tables_only": 0.5377033703165067,
        "overall_average_structure_similarity_tables_only": 0.9299762187917149,
        "timestamp": "20250429_153454"
    },
```


















# Reference

[1] MinerU:https://github.com/opendatalab/MinerU

[2] SlANET https://arxiv.org/pdf/2210.05391 

[3] PaddleX: https://github.com/PaddlePaddle/PaddleX
