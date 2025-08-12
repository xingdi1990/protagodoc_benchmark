import json
from typing import Literal

import httpx

from olmocr.bench.prompts import (
    build_basic_prompt,
    build_openai_silver_data_prompt_no_document_anchoring,
)
from olmocr.data.renderpdf import render_pdf_to_base64png
from olmocr.prompts.anchor import get_anchor_text
from olmocr.prompts.prompts import (
    PageResponse,
    build_finetuning_prompt,
    build_openai_silver_data_prompt,
)


async def run_server(
    pdf_path: str,
    page_num: int = 1,
    server: str = "localhost:30000",
    model: str = "allenai/olmOCR-7B-0225-preview",
    temperature: float = 0.1,
    target_longest_image_dim: int = 1024,
    prompt_template: Literal["full", "full_no_document_anchoring", "basic", "finetune"] = "finetune",
    response_template: Literal["plain", "json"] = "json",
) -> str:
    """
    Convert page of a PDF file to markdown by calling a request
    running against an openai compatible server.

    You can use this for running against vllm, sglang, servers
    as well as mixing and matching different model's.

    It will only make one direct request, with no retries or error checking.

    Returns:
        str: The OCR result in markdown format.
    """
    # Convert the first page of the PDF to a base64-encoded PNG image.
    image_base64 = render_pdf_to_base64png(pdf_path, page_num=page_num, target_longest_image_dim=target_longest_image_dim)
    anchor_text = get_anchor_text(pdf_path, page_num, pdf_engine="pdfreport")

    if prompt_template == "full":
        prompt = build_openai_silver_data_prompt(anchor_text)
    elif prompt_template == "full_no_document_anchoring":
        prompt = build_openai_silver_data_prompt_no_document_anchoring(anchor_text)
    elif prompt_template == "finetune":
        prompt = build_finetuning_prompt(anchor_text)
    elif prompt_template == "basic":
        prompt = build_basic_prompt()
    else:
        raise ValueError("Unknown prompt template")

    request = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                ],
            }
        ],
        "temperature": temperature,
        "max_tokens": 3000,
    }

    # Make request and get response using httpx
    url = f"http://{server}/v1/chat/completions"

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(url, json=request)

        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        assert (
            choice["finish_reason"] == "stop"
        ), "Response from server did not finish with finish_reason stop as expected, this is probably going to lead to bad data"

        if response_template == "json":
            page_data = json.loads(choice["message"]["content"])
            page_response = PageResponse(**page_data)
            return page_response.natural_text
        elif response_template == "plain":
            return choice["message"]["content"]
