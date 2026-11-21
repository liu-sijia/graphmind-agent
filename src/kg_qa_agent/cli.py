from __future__ import annotations

import argparse
from pathlib import Path

from .extractor import extract_document
from .graph import Neo4jGraphStore, merge_extractions
from .ingest import discover_documents, load_source
from .llm import ChatClient
from .models import ExtractionResult, GraphBundle
from .qa import answer_question
from .utils import read_json, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generic knowledge graph and grounded QA agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract a graph bundle from local documents")
    extract_parser.add_argument("--input", type=Path, required=True)
    extract_parser.add_argument("--output", type=Path, default=Path("output/graph_bundle.json"))
    extract_parser.add_argument("--max-chars", type=int, default=30000)

    import_parser = subparsers.add_parser("import", help="Import a graph bundle into Neo4j")
    import_parser.add_argument("--bundle", type=Path, required=True)

    ask_parser = subparsers.add_parser("ask", help="Answer a question using graph evidence")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--output", type=Path)
    return parser


def run_extract(input_path: Path, output_path: Path, max_chars: int) -> None:
    client = ChatClient()
    root = input_path if input_path.is_dir() else input_path.parent
    results: list[ExtractionResult] = []
    for path in discover_documents(input_path):
        source, text = load_source(path, root=root)
        results.append(extract_document(source, text[:max_chars], client))
    bundle = merge_extractions(results)
    write_json(output_path, bundle.model_dump(mode="json"))
    print(f"Documents: {len(bundle.sources)}")
    print(f"Entities: {len(bundle.entities)}")
    print(f"Relations: {len(bundle.relations)}")
    print(f"Output: {output_path}")


def run_import(bundle_path: Path) -> None:
    bundle = GraphBundle.model_validate(read_json(bundle_path))
    store = Neo4jGraphStore()
    try:
        store.import_bundle(bundle)
    finally:
        store.close()
    print(f"Imported entities: {len(bundle.entities)}")
    print(f"Imported relations: {len(bundle.relations)}")


def run_ask(question: str, output_path: Path | None) -> None:
    client = ChatClient()
    store = Neo4jGraphStore()
    try:
        answer = answer_question(question, store, client)
    finally:
        store.close()
    print(answer.answer)
    if output_path:
        write_json(output_path, answer.model_dump(mode="json"))
        print(f"Evidence output: {output_path}")


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "extract":
        run_extract(args.input, args.output, args.max_chars)
    elif args.command == "import":
        run_import(args.bundle)
    elif args.command == "ask":
        run_ask(args.question, args.output)


if __name__ == "__main__":
    main()

