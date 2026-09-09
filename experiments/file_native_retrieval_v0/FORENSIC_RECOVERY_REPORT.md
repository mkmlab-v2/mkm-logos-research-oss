# File-native retrieval recovery

Scope: local source recovery and isolated DEV engineering. This is a targeted
component audit, not an exhaustive audit of every file in the workspace.
SSOT remains current disk and internal Gitea. No model API calls are required.

## Recovered evidence

- scripts/build_workspace_postit_index_v1.py: make_item, collect_files. Real
  path/tag index; tests/test_build_workspace_postit_index_v1.py exists.
  workspace_postit_index_latest.json exists (10,459,168 bytes at inspection).
  Track, status, and evidence fields are inferred from paths, not adjudicated facts.
- scripts/run_workspace_postit_search_v1.py: apply_filter. Real preset/filter
  search, not a general semantic search engine. Standard library dependencies.
- scripts/mkm_ops_memory_index_lib_v1.py: NodeSpec, build_node_entry,
  query_match_tokens, route_nodes_by_field_tags, verify_index_sha_drift.
  Anchors, JSON pointers, hash-prefix verification and compact resume assembly
  exist. tests/test_mkm_ops_memory_index_v1.py exists. Curated node scope.
- scripts/build_context_note_memory_index_v1.py and
  scripts/query_context_note_memory_index_v1.py: SQLite FTS5, dense/lexical/hybrid
  queries, path priors. Four local SQLite files observed. Builder unlinks the
  previous database before rebuild: presence of hashes is not incremental update.
  tests/test_context_note_memory_index_v1.py exists. Embedding dependencies apply
  to dense mode; hash stub explicitly is NOT semantic retrieval.
- scripts/build_mkm_core_coordinate_map_v1.py: build, static COORDS resolve map.
  tests/test_mkm_core_coordinate_map_v1.py exists. Historical checker receipt
  reports ok=true, 14 coordinates, dated 2026-07-10; not a new test result.
- scripts/build_a2a_tp03_chain_ref_pilot_v1.py: pointer + SHA fingerprint packets.
  tests/test_build_a2a_tp03_chain_ref_pilot_v1.py and output artifact exist.
  scripts/mkm_a2a_compress_pilot_lib_v1.py contains compress_plaintext_v2, which
  calls a supplied client. No compressor or paid endpoint was executed here.
- scripts/validate_postit_pointer_v1.py: domain pointer validation, schema-based
  IDs; tests/test_validate_postit_pointer_v1.py exists. Domain-specific, not a
  universal repository locator implementation.
- scripts/query_mkm_structural_retrieval_v0.py: graph_structural, source_baseline,
  hybrid. Existing comparator takes expected_source_path/expected_symbols into
  candidate selection. It cannot establish blind retrieval quality as written.

Evidence level for callable source above: FACT for existence and static behavior;
runtime readiness of old components: NOT_ESTABLISHED in this mission.
Existing artifacts are historical evidence, not new validations.

## Boundaries

The Qdrant fossil archive receipt reports ARCHIVED_HOLD. No fossil data was opened,
ingested, restored or migrated. No valid separate live Qdrant comparator was
established. Qdrant comparison and any relative advantage remain NOT_ESTABLISHED.

Substantial existing pieces justify G2 glue, not product-wide replacement.
The prototype reuses the existing ops tokenizer and existing pointer/hash design;
it does not invoke legacy index builders with mutable latest output paths.
New limitations: explicit finite file list; whole-file token postings; Python
symbols only; literal path reference edges only; no semantic claims or authority
inference. Relation presence is not proof of runtime reachability.
