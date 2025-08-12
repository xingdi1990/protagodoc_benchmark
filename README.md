
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
