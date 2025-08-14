# Set your OpenAI API key as an environment variable
# export OPENAI_API_KEY="your-api-key-here"
# Or create a .env file with: OPENAI_API_KEY=your-api-key-here

# python generate_dataset.py --pdf_dir /path/to/pdfs --output dataset.jsonl

# python generate_dataset.py --pdf_dir /path/to/pdfs --output dataset.jsonl --model gpt-4o

# # Use older model if needed
# python generate_dataset.py --pdf_dir /path/to/pdfs --output dataset.jsonl --model gpt-4o-2024-08-06

# # Use different model
# python generate_dataset.py --pdf_dir /path/to/pdfs --output dataset.jsonl --model gpt-4-turbo



# python scripts/split_pdfs_by_page.py --input-dir datasets/orbit_v1/pdf --output-dir bench/orbit_data/pdfs_by_pages
# python scripts/split_pdfs_by_page.py --input-dir datasets/orbit_v2/pdf --output-dir bench/orbit_data/pdfs_by_pages
# python scripts/split_pdfs_by_page.py --input-dir datasets/orbit_v3/pdf --output-dir bench/orbit_data/pdfs_by_pages

python scripts/split_pdfs_by_page.py --input-dir datasets/cornercase --output-dir bench/orbit_data/pdfs_by_pages

python scripts/filter_language.py --input-dir bench/orbit_data/pdfs_by_pages \
    --output-dir bench/orbit_data/pdfs \
    --samples-per-language 3 \
    --max-files 100 \
    --seed 777

python generate_dataset.py --pdf_dir bench/orbit_data/pdfs --output bench/orbit_data --max_tests_per_type 2 --model gpt-4o-2024-08-06