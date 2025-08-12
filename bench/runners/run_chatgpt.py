import json
import os
from typing import Literal

from openai import OpenAI

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
    openai_response_format_schema,
)


def run_chatgpt(
    pdf_path: str,
    page_num: int = 1,
    model: str = "gpt-4o-2024-08-06",
    temperature: float = 0.1,
    target_longest_image_dim: int = 2048,
    prompt_template: Literal["full", "full_no_document_anchoring", "basic", "finetune"] = "finetune",
    response_template: Literal["plain", "json"] = "json",
) -> str:
    """
    Convert page of a PDF file to markdown using the commercial openAI APIs.

    See run_server.py for running against an openai compatible server

    Args:
        pdf_path (str): The local path to the PDF file.

    Returns:
        str: The OCR result in markdown format.
    """
    # Convert the first page of the PDF to a base64-encoded PNG image.
    image_base64 = render_pdf_to_base64png(pdf_path, page_num=page_num, target_longest_image_dim=target_longest_image_dim)
    anchor_text = get_anchor_text(pdf_path, page_num, pdf_engine="pdfreport")

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("You must specify an OPENAI_API_KEY")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                ],
            }
        ],
        temperature=temperature,
        max_tokens=3000,
        response_format=openai_response_format_schema() if response_template == "json" else None,
    )

    raw_response = response.choices[0].message.content

    assert len(response.choices) > 0
    assert response.choices[0].message.refusal is None
    assert response.choices[0].finish_reason == "stop"

    if response_template == "json":
        data = json.loads(raw_response)
        data = PageResponse(**data)

        return data.natural_text
    else:
        return raw_response
