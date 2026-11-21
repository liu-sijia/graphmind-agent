from __future__ import annotations

from pathlib import Path

from .models import SourceDocument
from .utils import read_document, stable_id


SUPPORTED_SUFFIXES = {".txt", ".md", ".html", ".htm"}


def discover_documents(input_path: Path) -> list[Path]:
    if input_path.is_file():
        candidates = [input_path]
    elif input_path.is_dir():
        candidates = [path for path in input_path.rglob("*") if path.is_file()]
    else:
        raise FileNotFoundError(f"Input path does not exist: {input_path}")
    return sorted(path for path in candidates if path.suffix.lower() in SUPPORTED_SUFFIXES)


def load_source(path: Path, root: Path | None = None) -> tuple[SourceDocument, str]:
    source_ref = str(path.relative_to(root)) if root and path.is_relative_to(root) else path.name
    source = SourceDocument(
        document_id=stable_id("doc", source_ref),
        title=path.stem,
        source_type=path.suffix.lower().lstrip(".") or "document",
        source_ref=source_ref,
    )
    return source, read_document(path)

