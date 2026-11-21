from __future__ import annotations

from collections import defaultdict

from neo4j import GraphDatabase

from .config import Settings, settings
from .models import Entity, ExtractionResult, GraphBundle, Relation
from .utils import normalize_symbol


def merge_extractions(results: list[ExtractionResult]) -> GraphBundle:
    entity_groups: dict[str, list[Entity]] = defaultdict(list)
    relation_groups: dict[tuple[str, str, str], list[Relation]] = defaultdict(list)
    for result in results:
        for entity in result.entities:
            entity_groups[entity.entity_id].append(entity)
        for relation in result.relations:
            key = (relation.source_id, relation.relation_type, relation.target_id)
            relation_groups[key].append(relation)

    entities = [_merge_entity(group) for group in entity_groups.values()]
    valid_ids = {entity.entity_id for entity in entities}
    relations = [
        _merge_relation(group)
        for (source_id, _, target_id), group in relation_groups.items()
        if source_id in valid_ids and target_id in valid_ids
    ]
    return GraphBundle(
        sources=[result.source for result in results],
        entities=sorted(entities, key=lambda item: item.entity_id),
        relations=sorted(relations, key=lambda item: (item.source_id, item.relation_type, item.target_id)),
    )


def _merge_entity(group: list[Entity]) -> Entity:
    base = group[0]
    aliases = sorted({alias for item in group for alias in item.aliases})
    source_refs = sorted({ref for item in group for ref in item.source_refs})
    properties = {key: value for item in group for key, value in item.properties.items()}
    return base.model_copy(
        update={
            "aliases": aliases,
            "source_refs": source_refs,
            "properties": properties,
            "confidence": max(item.confidence for item in group),
        }
    )


def _merge_relation(group: list[Relation]) -> Relation:
    base = group[0]
    source_refs = sorted({ref for item in group for ref in item.source_refs})
    properties = {key: value for item in group for key, value in item.properties.items()}
    return base.model_copy(
        update={
            "source_refs": source_refs,
            "properties": properties,
            "confidence": max(item.confidence for item in group),
        }
    )


class Neo4jGraphStore:
    def __init__(self, config: Settings = settings) -> None:
        config.require_neo4j()
        self.driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_username, config.neo4j_password),
        )

    def close(self) -> None:
        self.driver.close()

    def import_bundle(self, bundle: GraphBundle) -> None:
        with self.driver.session() as session:
            session.run(
                "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
                "FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE"
            )
            for entity in bundle.entities:
                label = normalize_symbol(entity.entity_type, "ENTITY")
                session.run(
                    f"MERGE (n:Entity:`{label}` {{entity_id: $entity_id}}) "
                    "SET n.name = $name, n.entity_type = $entity_type, n.aliases = $aliases, "
                    "n.source_refs = $source_refs, n.confidence = $confidence, n += $properties",
                    entity_id=entity.entity_id,
                    name=entity.name,
                    entity_type=entity.entity_type,
                    aliases=entity.aliases,
                    source_refs=entity.source_refs,
                    confidence=entity.confidence,
                    properties=entity.properties,
                )
            for relation in bundle.relations:
                relation_type = normalize_symbol(relation.relation_type, "RELATED_TO")
                session.run(
                    "MATCH (a:Entity {entity_id: $source_id}) "
                    "MATCH (b:Entity {entity_id: $target_id}) "
                    f"MERGE (a)-[r:`{relation_type}`]->(b) "
                    "SET r.source_refs = $source_refs, r.confidence = $confidence, r += $properties",
                    source_id=relation.source_id,
                    target_id=relation.target_id,
                    source_refs=relation.source_refs,
                    confidence=relation.confidence,
                    properties=relation.properties,
                )

    def retrieve(self, terms: list[str], limit: int) -> list[dict[str, object]]:
        cleaned = [term.strip().lower() for term in terms if term.strip()]
        if not cleaned:
            return []
        query = """
        MATCH (a:Entity)-[r]-(b:Entity)
        WHERE any(term IN $terms WHERE
            toLower(a.name) CONTAINS term OR
            toLower(b.name) CONTAINS term OR
            any(alias IN coalesce(a.aliases, []) WHERE toLower(alias) CONTAINS term) OR
            any(alias IN coalesce(b.aliases, []) WHERE toLower(alias) CONTAINS term))
        RETURN a.name AS subject, type(r) AS predicate, b.name AS object,
               coalesce(r.source_refs, []) AS source_refs
        LIMIT $limit
        """
        with self.driver.session() as session:
            return session.run(query, terms=cleaned, limit=limit).data()

