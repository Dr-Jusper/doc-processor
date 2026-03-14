import base64
import json
import os
import requests
from pathlib import Path
import fitz  # pymupdf

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "anthropic/claude-haiku-4.5"

SYSTEM_PROMPT = """You are a document data extraction assistant.
Your task is to analyze the provided document image and extract key fields.

Always respond with a valid JSON object in this exact format:
{
  "document_type": "invoice | receipt | contract | act | other",
  "fields": [
    {
      "name": "field_name",
      "value": "field_value",
      "confidence": 0.95
    }
  ]
}

Common fields to extract depending on document type:
- invoice/receipt: date, total_amount, currency, vendor_name, vendor_inn, buyer_name, invoice_number, items
- contract: date, contract_number, party_1, party_2, subject, total_amount, currency
- act: date, act_number, vendor_name, buyer_name, services_description, total_amount

Rules:
- confidence is a float from 0.0 to 1.0 — how certain you are about the extracted value
- If a field is not found, do not include it
- field_name must be in snake_case English
- field_value must be a string
- Return ONLY the JSON object, no markdown, no explanation
"""


def file_to_base64(filepath: str) -> tuple[str, str]:
    """Конвертирует файл в base64. Возвращает (base64_string, media_type)."""
    path = Path(filepath)
    suffix = path.suffix.lower()

    media_types = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".gif":  "image/gif",
        ".webp": "image/webp",
    }

    media_type = media_types.get(suffix, "image/jpeg")

    with open(filepath, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    return data, media_type


def pdf_to_base64_image(filepath: str) -> tuple[str, str]:
    """Конвертирует первую страницу PDF в PNG и возвращает base64."""
    doc = fitz.open(filepath)
    page = doc[0]
    mat = fitz.Matrix(2, 2)  # масштаб 2x для лучшего качества
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
    return b64, "image/png"


def extract(filepath: str) -> dict:
    """
    Извлекает данные из документа через LLM.
    Возвращает {"document_type": ..., "fields": [...], "raw_text": ...}
    """
    suffix = Path(filepath).suffix.lower()

    if suffix == ".pdf":
        b64_data, media_type = pdf_to_base64_image(filepath)
    else:
        b64_data, media_type = file_to_base64(filepath)

    content = [
    {
        "type": "image_url",
        "image_url": {
            "url": f"data:{media_type};base64,{b64_data}"
        }
    },
    {
        "type": "text",
        "text": "Extract all key fields from this document."
    }
]

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": content},
            ]
        }
    )

    response.raise_for_status()
    raw_text = response.json()["choices"][0]["message"]["content"].strip()

    # Чистим markdown-обёртку если модель добавила
    clean = raw_text
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]
        clean = clean.rsplit("```", 1)[0]
    clean = clean.strip()

    result = json.loads(clean)

    if "fields" not in result:
        result["fields"] = []
    if "document_type" not in result:
        result["document_type"] = "other"

    return {
        "document_type": result["document_type"],
        "fields": result["fields"],
        "raw_text": raw_text,
    }