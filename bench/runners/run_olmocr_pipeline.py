import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

# Import necessary components from olmocr
from olmocr.pipeline import (
    MetricsKeeper,
    PageResult,
    WorkerTracker,
    process_page,
    sglang_server_host,
    sglang_server_ready,
)

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("olmocr_runner")


# Basic configuration
@dataclass
class Args:
    model: str = "allenai/olmOCR-7B-0225-preview"
    model_chat_template: str = "qwen2-vl"
    model_max_context: int = 8192
    target_longest_image_dim: int = 1024
    target_anchor_text_len: int = 6000
    max_page_retries: int = 8
    max_page_error_rate: float = 0.004


server_check_lock = asyncio.Lock()


async def run_olmocr_pipeline(pdf_path: str, page_num: int = 1, model: str = "allenai/olmOCR-7B-0225-preview") -> Optional[str]:
    """
    Process a single page of a PDF using the official olmocr pipeline's process_page function

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to process (1-indexed)

    Returns:
        The extracted text from the page or None if processing failed
    """
    # Ensure global variables are initialized
    global metrics, tracker
    if "metrics" not in globals() or metrics is None:
        metrics = MetricsKeeper(window=60 * 5)
    if "tracker" not in globals() or tracker is None:
        tracker = WorkerTracker()

    args = Args()
    args.model = model
    semaphore = asyncio.Semaphore(1)
    worker_id = 0  # Using 0 as default worker ID

    # Ensure server is running
    async with server_check_lock:
        _server_task = None
        try:
            await asyncio.wait_for(sglang_server_ready(), timeout=5)
            logger.info("Using existing sglang server")
        except Exception:
            logger.info("Starting new sglang server")
            _server_task = asyncio.create_task(sglang_server_host(args.model, args, semaphore))
            await sglang_server_ready()

    try:
        # Process the page using the pipeline's process_page function
        # Note: process_page expects both original path and local path
        # In our case, we're using the same path for both
        page_result: PageResult = await process_page(args=args, worker_id=worker_id, pdf_orig_path=pdf_path, pdf_local_path=pdf_path, page_num=page_num)

        # Return the natural text from the response
        if page_result and page_result.response and not page_result.is_fallback:
            return page_result.response.natural_text
        return None

    except Exception as e:
        logger.error(f"Error processing page: {type(e).__name__} - {str(e)}")
        return None

    finally:
        # We leave the server running for potential reuse
        pass


async def main():
    # Example usage
    pdf_path = "your_pdf_path.pdf"
    page_num = 1

    result = await run_olmocr_pipeline(pdf_path, page_num)
    if result:
        print(f"Extracted text: {result[:200]}...")  # Print first 200 chars
    else:
        print("Failed to extract text from the page")


if __name__ == "__main__":
    asyncio.run(main())
