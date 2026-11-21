from pathlib import Path

from kg_qa_agent.extractor import extraction_from_payload
from kg_qa_agent.graph import merge_extractions
from kg_qa_agent.ingest import load_source
from kg_qa_agent.models import SourceDocument
from kg_qa_agent.qa import answer_question
from kg_qa_agent.utils import extract_json_object, normalize_symbol, stable_id


def test_stable_id_is_deterministic() -> None:
    assert stable_id("entity", "Example") == stable_id("entity", "example")


def test_normalize_symbol() -> None:
    assert normalize_symbol("located in", "RELATED_TO") == "LOCATED_IN"
    assert normalize_symbol("", "RELATED_TO") == "RELATED_TO"


def test_extract_json_from_fenced_response() -> None:
    payload = extract_json_object('Result:\n```json\n{"entities": [], "relations": []}\n```')
    assert payload == {"entities": [], "relations": []}


def test_extraction_drops_relations_with_unknown_endpoints() -> None:
    source = SourceDocument(document_id="doc_1", title="Document", source_ref="document.txt")
    result = extraction_from_payload(
        source,
        {
            "entities": [{"name": "Alpha", "entity_type": "Concept"}],
            "relations": [
                {"source": "Alpha", "relation_type": "RELATED_TO", "target": "Missing"}
            ],
        },
    )
    assert len(result.entities) == 1
    assert result.relations == []


def test_merge_extractions_deduplicates_entities() -> None:
    source = SourceDocument(document_id="doc_1", title="Document", source_ref="document.txt")
    payload = {
        "entities": [{"name": "Alpha", "entity_type": "Concept"}],
        "relations": [],
    }
    bundle = merge_extractions(
        [extraction_from_payload(source, payload), extraction_from_payload(source, payload)]
    )
    assert len(bundle.entities) == 1


def test_load_source_keeps_only_relative_reference(tmp_path: Path) -> None:
    document = tmp_path / "document.txt"
    document.write_text("  Example   text  ", encoding="utf-8")
    source, text = load_source(document, root=tmp_path)
    assert source.source_ref == "document.txt"
    assert str(tmp_path) not in source.source_ref
    assert text == "Example text"


def test_answer_without_evidence_does_not_call_generation() -> None:
    class EmptyStore:
        def retrieve(self, terms: list[str], limit: int) -> list[dict[str, object]]:
            return []

    class StubClient:
        calls = 0

        def complete(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
            self.calls += 1
            return '{"terms": ["Alpha"]}'

    client = StubClient()
    answer = answer_question("What is Alpha?", EmptyStore(), client)  # type: ignore[arg-type]
    assert answer.evidence == []
    assert "not contain enough evidence" in answer.answer
    assert client.calls == 1

