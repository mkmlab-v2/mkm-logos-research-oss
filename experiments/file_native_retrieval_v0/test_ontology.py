from __future__ import annotations

import pytest

from experiments.file_native_retrieval_v0.ontology import (
    EdgeKind,
    EntityKind,
    LocatorEntity,
    OntologyEdge,
    OntologyGraph,
    graph_from_retrieval_records,
)


def _record(identity: str = "a.py") -> dict:
    return {
        "id": identity,
        "source_path": identity,
        "source_hash": "a" * 64,
        "symbols": [],
        "keywords": [],
        "relations": [],
        "kind": ".py",
        "state": "LOCATOR_ONLY",
    }


def test_retrieval_records_become_source_locators_only() -> None:
    graph = graph_from_retrieval_records([_record("claim_notes.md")])
    entity = graph.get("source:claim_notes.md")
    assert entity.kind is EntityKind.SOURCE
    assert entity.locator == "claim_notes.md"
    assert graph.edges == ()


def test_filename_does_not_infer_claim_or_receipt_kind() -> None:
    graph = graph_from_retrieval_records([_record("receipt.json"), _record("claim.md")])
    assert graph.get("source:receipt.json").kind is EntityKind.SOURCE
    assert graph.get("source:claim.md").kind is EntityKind.SOURCE


def test_source_entity_requires_hash() -> None:
    with pytest.raises(ValueError, match="SOURCE entities require source_hash"):
        LocatorEntity("source:x", EntityKind.SOURCE, "x.py")


def test_explicit_claim_and_receipt_can_be_declared() -> None:
    graph = graph_from_retrieval_records(
        [_record()],
        declarations=(
            LocatorEntity("claim:c1", EntityKind.CLAIM, "claims.json#/c1", declared_state="NOT_ADJUDICATED"),
            LocatorEntity("receipt:r1", EntityKind.RECEIPT, "receipts.json#/r1"),
        ),
        edges=(OntologyEdge("receipt:r1", "claim:c1", EdgeKind.VERIFIES, "receipts.json#/r1"),),
    )
    assert graph.get("claim:c1").declared_state == "NOT_ADJUDICATED"
    assert graph.edges[0].kind is EdgeKind.VERIFIES


def test_verifies_requires_receipt_to_claim() -> None:
    graph = OntologyGraph(
        [
            LocatorEntity("source:s", EntityKind.SOURCE, "s.py", source_hash="b" * 64),
            LocatorEntity("claim:c", EntityKind.CLAIM, "claims.json#/c"),
        ]
    )
    with pytest.raises(ValueError, match="VERIFIES requires RECEIPT -> CLAIM"):
        graph.add_edge(OntologyEdge("source:s", "claim:c", EdgeKind.VERIFIES, "explicit:test"))


def test_supports_requires_source_or_artifact_to_claim() -> None:
    graph = OntologyGraph(
        [
            LocatorEntity("receipt:r", EntityKind.RECEIPT, "r.json"),
            LocatorEntity("claim:c", EntityKind.CLAIM, "c.json"),
        ]
    )
    with pytest.raises(ValueError, match="SUPPORTS requires SOURCE/ARTIFACT -> CLAIM"):
        graph.add_edge(OntologyEdge("receipt:r", "claim:c", EdgeKind.SUPPORTS, "explicit:test"))


def test_semantic_edges_require_explicit_evidence_pointer() -> None:
    with pytest.raises(ValueError, match="explicit evidence_ref"):
        OntologyEdge("source:s", "claim:c", EdgeKind.SUPPORTS, "")


def test_missing_edge_endpoint_rejects() -> None:
    graph = OntologyGraph([LocatorEntity("claim:c", EntityKind.CLAIM, "claims.json#/c")])
    with pytest.raises(KeyError, match="unknown entity_id"):
        graph.add_edge(OntologyEdge("receipt:missing", "claim:c", EdgeKind.VERIFIES, "explicit:test"))


def test_duplicate_entity_ids_reject() -> None:
    entity = LocatorEntity("claim:c", EntityKind.CLAIM, "claims.json#/c")
    graph = OntologyGraph([entity])
    with pytest.raises(ValueError, match="duplicate entity_id"):
        graph.add_entity(entity)


def test_packet_is_deterministic_and_sorted() -> None:
    graph = OntologyGraph(
        [
            LocatorEntity("claim:z", EntityKind.CLAIM, "z.json"),
            LocatorEntity("claim:a", EntityKind.CLAIM, "a.json"),
            LocatorEntity("receipt:r", EntityKind.RECEIPT, "r.json"),
        ],
        [
            OntologyEdge("receipt:r", "claim:z", EdgeKind.VERIFIES, "r.json#/z"),
            OntologyEdge("receipt:r", "claim:a", EdgeKind.VERIFIES, "r.json#/a"),
        ],
    )
    packet = graph.packet()
    assert [row["entity_id"] for row in packet["entities"]] == ["claim:a", "claim:z", "receipt:r"]
    assert [row["target_id"] for row in packet["edges"]] == ["claim:a", "claim:z"]


def test_declared_state_is_metadata_not_authorization() -> None:
    entity = LocatorEntity("claim:c", EntityKind.CLAIM, "claims.json#/c", declared_state="FACT")
    graph = OntologyGraph([entity])
    packet = graph.packet()
    assert packet["entities"][0]["declared_state"] == "FACT"
    assert packet["edges"] == []


def test_valid_raw_entity_kind_string_coercion() -> None:
    entity = LocatorEntity("claim:c", "CLAIM", "claims.json#/c")
    assert entity.kind is EntityKind.CLAIM


def test_invalid_entity_kind_rejection() -> None:
    with pytest.raises(ValueError, match="invalid EntityKind"):
        LocatorEntity("claim:c", "claim", "claims.json#/c")


def test_valid_raw_edge_kind_string_coercion() -> None:
    edge = OntologyEdge("receipt:r", "claim:c", "VERIFIES", "explicit:test")
    assert edge.kind is EdgeKind.VERIFIES


def test_invalid_edge_kind_rejection() -> None:
    with pytest.raises(ValueError, match="invalid EdgeKind"):
        OntologyEdge("receipt:r", "claim:c", "verifies", "explicit:test")


def test_raw_verifies_cannot_bypass_receipt_to_claim() -> None:
    graph = OntologyGraph(
        [
            LocatorEntity("source:s", EntityKind.SOURCE, "s.py", source_hash="b" * 64),
            LocatorEntity("claim:c", EntityKind.CLAIM, "claims.json#/c"),
        ]
    )
    with pytest.raises(ValueError, match="VERIFIES requires RECEIPT -> CLAIM"):
        graph.add_edge(OntologyEdge("source:s", "claim:c", "VERIFIES", "explicit:test"))


def test_raw_supports_cannot_bypass_source_or_artifact_to_claim() -> None:
    graph = OntologyGraph(
        [
            LocatorEntity("receipt:r", EntityKind.RECEIPT, "r.json"),
            LocatorEntity("claim:c", EntityKind.CLAIM, "c.json"),
        ]
    )
    with pytest.raises(ValueError, match="SUPPORTS requires SOURCE/ARTIFACT -> CLAIM"):
        graph.add_edge(OntologyEdge("receipt:r", "claim:c", "SUPPORTS", "explicit:test"))


def test_raw_source_still_requires_hash_after_coercion() -> None:
    with pytest.raises(ValueError, match="SOURCE entities require source_hash"):
        LocatorEntity("source:s", "SOURCE", "s.py")


def test_packet_emits_canonical_strings_after_raw_kind_coercion() -> None:
    graph = OntologyGraph(
        [
            LocatorEntity("receipt:r", "RECEIPT", "r.json"),
            LocatorEntity("claim:c", "CLAIM", "c.json"),
        ],
        [OntologyEdge("receipt:r", "claim:c", "VERIFIES", "r.json#/c")],
    )
    packet = graph.packet()
    assert [row["kind"] for row in packet["entities"]] == ["CLAIM", "RECEIPT"]
    assert packet["edges"][0]["kind"] == "VERIFIES"
