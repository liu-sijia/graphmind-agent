from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def normalize_symbol(value: str, fallback: str) -> str:
    cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value.strip())
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", cleaned).strip("_").upper()
    if not cleaned:
        return fallback
    if cleaned[0].isdigit():
        cleaned = f"N_{cleaned}"
    return cleaned


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_html(raw_html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", raw_html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_text(html.unescape(text))


def read_document(path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="ignore")
    return strip_html(content) if path.suffix.lower() in {".html", ".htm"} else normalize_text(content)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_json_object(text: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.I)
    candidate = fenced.group(1) if fenced else text
    decoder = json.JSONDecoder()
    for index, char in enumerate(candidate):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(candidate[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("LLM response does not contain a valid JSON object")

