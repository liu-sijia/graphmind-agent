from __future__ import annotations

from typing import Any

from .llm import ChatClient
from .models import Entity, ExtractionResult, Relation, SourceDocument
from .utils import extract_json_object, normalize_symbol, stable_id


EXTRACTION_SYSTEM_PROMPT = """You extract a domain-neutral knowledge graph from documents.
Return JSON only. Use only facts explicitly supported by the supplied text. Do not infer missing facts.
Entity types and relation types must be concise English UPPER_SNAKE_CASE labels."""


def build_extraction_prompt(source: SourceDocument, text: str) -> str:
    return f"""Extract entities and relations from the document below.

Required JSON schema:
{{
  "entities": [
    {{"name": "", "entity_type": "", "aliases": [], "properties": {{}}, "confidence": 1.0}}
  ],
  "relations": [
    {{"source": "", "relation_type": "", "target": "", "properties": {{"evidence": ""}}, "confidence": 1.0}}
  ]
}}

Rules:
- Relation source and target must exactly match an entity name in the entities array.
- Preserve short textual evidence in relation properties when available.
- Omit uncertain items instead of inventing them.
- Return no text outside the JSON object.

Title: {source.title}
Source type: {source.source_type}

Document:
{text}
"""


def extract_document(source: SourceDocument, text: str, client: ChatClient) -> ExtractionResult:
    response = client.complete(
        [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": build_extraction_prompt(source, text)},
        ],
        temperature=0.0,
    )
    return extraction_from_payload(source, extract_json_object(response))


def extraction_from_payload(source: SourceDocument, payload: dict[str, Any]) -> ExtractionResult:
    entities: list[Entity] = []
    by_name: dict[str, Entity] = {}
    for item in payload.get("entities", []):
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        entity_type = normalize_symbol(str(item.get("entity_type", "")), "ENTITY")
        entity = Entity(
            entity_id=stable_id("entity", f"{entity_type}:{name}"),
            name=name,
            entity_type=entity_type,
            aliases=[str(value).strip() for value in item.get("aliases", []) if str(value).strip()],
            properties=dict(item.get("properties") or {}),
            source_refs=[source.document_id],
            confidence=float(item.get("confidence", 1.0)),
        )
        entities.append(entity)
        by_name[name] = entity

    relations: list[Relation] = []
    for item in payload.get("relations", []):
        source_name = str(item.get("source", "")).strip()
        target_name = str(item.get("target", "")).strip()
        if source_name not in by_name or target_name not in by_name:
            continue
        relations.append(
            Relation(
                source_id=by_name[source_name].entity_id,
                relation_type=normalize_symbol(str(item.get("relation_type", "")), "RELATED_TO"),
                target_id=by_name[target_name].entity_id,
                properties=dict(item.get("properties") or {}),
                source_refs=[source.document_id],
                confidence=float(item.get("confidence", 1.0)),
            )
        )
    return ExtractionResult(source=source, entities=entities, relations=relations)

