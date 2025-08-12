# Set your OpenAI API key as an environment variable
# export OPENAI_API_KEY="your-api-key-here"
# Or create a .env file with: OPENAI_API_KEY=your-api-key-here

# python generate_dataset.py --pdf_dir /path/to/pdfs --output dataset.jsonl

# python generate_dataset.py --pdf_dir /path/to/pdfs --output dataset.jsonl --model gpt-4o

# # Use older model if needed
# python generate_dataset.py --pdf_dir /path/to/pdfs --output dataset.jsonl --model gpt-4o-2024-08-06

# # Use different model
# python generate_dataset.py --pdf_dir /path/to/pdfs --output dataset.jsonl --model gpt-4-turbo


python generate_dataset.py --pdf_dir bench/orbit_data/pdfs --output dataset.jsonl --api_key $OPENAI_API_KEY