"""Explicit source/claim/receipt locator ontology for bounded file-native retrieval.

The ontology is intentionally non-inferential: indexed files become SOURCE
entities, while CLAIM/RECEIPT/ARTIFACT entities and semantic edges must be
provided explicitly by the caller. No authority, truth, support, or runtime
reachability is inferred from file contents.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class EntityKind(str, Enum):
    SOURCE = "SOURCE"
    CLAIM = "CLAIM"
    RECEIPT = "RECEIPT"
    ARTIFACT = "ARTIFACT"


class EdgeKind(str, Enum):
    REFERENCES = "REFERENCES"
    DERIVED_FROM = "DERIVED_FROM"
    SUPPORTS = "SUPPORTS"
    VERIFIES = "VERIFIES"


@dataclass(frozen=True)
class LocatorEntity:
    entity_id: str
    kind: EntityKind
    locator: str
    source_hash: str | None = None
    declared_state: str | None = None

    def __post_init__(self) -> None:
        if not self.entity_id.strip():
            raise ValueError("entity_id must be non-empty")
        if not self.locator.strip():
            raise ValueError("locator must be non-empty")
        if self.source_hash is not None and not self.source_hash.strip():
            raise ValueError("source_hash must be non-empty when provided")
        if self.declared_state is not None and not self.declared_state.strip():
            raise ValueError("declared_state must be non-empty when provided")
        if self.kind is EntityKind.SOURCE and self.source_hash is None:
            raise ValueError("SOURCE entities require source_hash")


@dataclass(frozen=True)
class OntologyEdge:
    source_id: str
    target_id: str
    kind: EdgeKind
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.target_id.strip():
            raise ValueError("edge endpoints must be non-empty")
        if not self.evidence_ref.strip():
            raise ValueError("semantic edges require explicit evidence_ref")


class OntologyGraph:
    """Append-only explicit locator graph with typed edge constraints."""

    def __init__(
        self,
        entities: Iterable[LocatorEntity] = (),
        edges: Iterable[OntologyEdge] = (),
    ) -> None:
        self._entities: dict[str, LocatorEntity] = {}
        self._edges: list[OntologyEdge] = []
        for entity in entities:
            self.add_entity(entity)
        for edge in edges:
            self.add_edge(edge)

    @property
    def entity_ids(self) -> tuple[str, ...]:
        return tuple(self._entities)

    @property
    def edges(self) -> tuple[OntologyEdge, ...]:
        return tuple(self._edges)

    def get(self, entity_id: str) -> LocatorEntity:
        try:
            return self._entities[entity_id]
        except KeyError as exc:
            raise KeyError(f"unknown entity_id: {entity_id}") from exc

    def add_entity(self, entity: LocatorEntity) -> None:
        if entity.entity_id in self._entities:
            raise ValueError(f"duplicate entity_id: {entity.entity_id}")
        self._entities[entity.entity_id] = entity

    def add_edge(self, edge: OntologyEdge) -> None:
        source = self.get(edge.source_id)
        target = self.get(edge.target_id)
        if edge in self._edges:
            raise ValueError("duplicate ontology edge")
        if edge.kind is EdgeKind.VERIFIES:
            if source.kind is not EntityKind.RECEIPT or target.kind is not EntityKind.CLAIM:
                raise ValueError("VERIFIES requires RECEIPT -> CLAIM")
        elif edge.kind is EdgeKind.SUPPORTS:
            if source.kind not in {EntityKind.SOURCE, EntityKind.ARTIFACT} or target.kind is not EntityKind.CLAIM:
                raise ValueError("SUPPORTS requires SOURCE/ARTIFACT -> CLAIM")
        self._edges.append(edge)

    def packet(self) -> dict[str, list[dict[str, str | None]]]:
        entities = [
            {
                "entity_id": entity.entity_id,
                "kind": entity.kind.value,
                "locator": entity.locator,
                "source_hash": entity.source_hash,
                "declared_state": entity.declared_state,
            }
            for entity in sorted(self._entities.values(), key=lambda item: item.entity_id)
        ]
        edges = [
            {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "kind": edge.kind.value,
                "evidence_ref": edge.evidence_ref,
            }
            for edge in sorted(
                self._edges,
                key=lambda item: (item.source_id, item.target_id, item.kind.value, item.evidence_ref),
            )
        ]
        return {"entities": entities, "edges": edges}


def graph_from_retrieval_records(
    records: Iterable[dict],
    *,
    declarations: Iterable[LocatorEntity] = (),
    edges: Iterable[OntologyEdge] = (),
) -> OntologyGraph:
    """Build a locator ontology without inferring claims/receipts from text."""

    graph = OntologyGraph()
    for row in sorted(records, key=lambda item: item["id"]):
        graph.add_entity(
            LocatorEntity(
                entity_id=f"source:{row['id']}",
                kind=EntityKind.SOURCE,
                locator=row["source_path"],
                source_hash=row["source_hash"],
            )
        )
    for entity in declarations:
        graph.add_entity(entity)
    for edge in edges:
        graph.add_edge(edge)
    return graph
