from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    document_id: str
    title: str
    source_type: str = "document"
    source_ref: str


class Entity(BaseModel):
    entity_id: str
    name: str
    entity_type: str
    aliases: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class Relation(BaseModel):
    source_id: str
    relation_type: str
    target_id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class ExtractionResult(BaseModel):
    source: SourceDocument
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)


class GraphBundle(BaseModel):
    sources: list[SourceDocument] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)


class Evidence(BaseModel):
    subject: str
    predicate: str
    object: str
    source_refs: list[str] = Field(default_factory=list)


class Answer(BaseModel):
    question: str
    answer: str
    evidence: list[Evidence] = Field(default_factory=list)

