# Bounded architecture

L0: relative path, filename, Python symbol, SHA256 exact matching.
L1: existing query_match_tokens feeds in-memory inverted postings, ranked by
token overlap. Score is an ordering heuristic, not calibrated confidence.
L2: one-hop literal references between explicitly selected paths. General claim,
receipt and runtime dependency edge extraction remains MISSING.
L2.5: explicit source/claim/receipt locator ontology. Every indexed file is a
SOURCE locator by default. CLAIM/RECEIPT/ARTIFACT entities and SUPPORTS/VERIFIES
edges are accepted only through explicit declarations with evidence pointers.
No entity kind, authority, truth, support, or runtime reachability is inferred
from file contents, filenames, or declared epistemic state.
L3: optional existing SQLite semantic mechanism is recovered but not connected.
No Qdrant backend, embedding call, or daemon is required by this prototype.

Post-it record: id/source_path/source_hash/symbols/keywords/relations/kind/state.
Symbols include line_start and line_end. No body copy or generated summary.
Keywords can expose source identifiers: this local index is not sanitized for
publication and must not be uploaded automatically. Record state is LOCATOR_ONLY.
Packets are plain JSON-serializable locator records, suitable for local handoff;
compatibility with existing A2A wire contracts is NOT_ESTABLISHED.

build(root, paths, previous) reuses unchanged records by full source SHA256;
the supplied paths are the complete desired snapshot, so removal drops records.
It still reads and hashes all selected files. Persistent watcher/large-scale
incremental performance is NOT_ESTABLISHED. Output ordering is deterministic.
search verifies source hashes at query time and labels stale/missing candidates
source_verified=false; callers must not treat those candidates as evidence.

Ontology usage is deliberately separate from retrieval ranking. Use
ontology.graph_from_retrieval_records(records, declarations=..., edges=...) to
materialize explicit locator entities. A declared claim state such as FACT is
metadata only and does not authorize promotion or imply evidentiary support.

Usage from repository root with a JSON array of approved relative paths:

    py experiments/file_native_retrieval_v0/retrieval.py --paths approved.json --query build_node_entry

DEV comparator uses the same five synthetic queries for a case-insensitive
path/body substring baseline and this prototype. Four positive queries define
Recall@k; one negative query checks abstention. Answers reach scoring only.
This tiny hand-written bank is not heldout and cannot establish superiority.

NEXT=STOP; no migration, production wiring, fresh validation, or promotion.
