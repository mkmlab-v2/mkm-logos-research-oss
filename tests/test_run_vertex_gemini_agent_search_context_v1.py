"""Unit tests for Agent Search -> context helpers (no GCP calls)."""

from __future__ import annotations

import scripts.run_vertex_gemini_agent_search_context_v1 as m


def test_usable_snippet_chars_skips_no_snippet() -> None:
    hits = [
        {
            "document": {
                "derived_struct_data": {
                    "snippets": [
                        {
                            "snippet": "No snippet is available for this page.",
                            "snippet_status": "NO_SNIPPET_AVAILABLE",
                        }
                    ]
                }
            }
        }
    ]
    assert m._usable_snippet_chars(hits) == 0


def test_usable_snippet_chars_counts_body() -> None:
    hits = [
        {
            "document": {
                "derived_struct_data": {
                    "snippets": [{"snippet": "  hello world  ", "snippet_status": "OK"}]
                }
            }
        }
    ]
    assert m._usable_snippet_chars(hits) == len("hello world")


def test_doc_id_from_chunk_name() -> None:
    name = (
        "projects/1/locations/global/collections/default_collection/"
        "dataStores/x/branches/0/documents/abc123/chunks/7"
    )
    assert m._doc_id_from_chunk_name(name) == "abc123"
    assert m._doc_id_from_chunk_name("nope") == ""


def test_hits_to_context_block_snippets_and_chunks() -> None:
    doc_hits = [
        {
            "document": {
                "id": "d1",
                "derived_struct_data": {
                    "title": "T",
                    "link": "gs://b/x.pdf",
                    "snippets": [{"snippet": "alpha", "snippet_status": "OK"}],
                },
            }
        }
    ]
    chunk_hits = [
        {
            "chunk": {
                "name": "projects/1/locations/global/collections/default_collection/"
                "dataStores/x/branches/0/documents/d1/chunks/1",
                "id": "1",
                "content": "chunkline",
            }
        }
    ]
    ctx = m._hits_to_context_block(doc_hits, chunk_hits=chunk_hits)
    assert "title=T" in ctx
    assert "snippets:" in ctx and "alpha" in ctx
    assert "chunk retrieval" in ctx
    assert "chunkline" in ctx


def test_document_name_from_chunk_resource() -> None:
    cname = (
        "projects/1/locations/global/collections/default_collection/"
        "dataStores/ds/branches/0/documents/abc/chunks/3"
    )
    assert (
        m._document_name_from_chunk_resource(cname)
        == "projects/1/locations/global/collections/default_collection/"
        "dataStores/ds/branches/0/documents/abc"
    )
    assert m._document_name_from_chunk_resource("no-chunks") == ""


def test_resolve_gs_uri_for_pull_from_document_hit() -> None:
    hits = [{"document": {"derived_struct_data": {"link": "gs://my-bucket/docs/a.pdf"}}}]
    assert m._resolve_gs_uri_for_pull(hits, None) == "gs://my-bucket/docs/a.pdf"


def test_resolve_gs_uri_for_pull_empty() -> None:
    assert m._resolve_gs_uri_for_pull([], None) == ""


def test_first_gs_uri() -> None:
    hits = [
        {
            "document": {
                "derived_struct_data": {"link": "https://example.com", "title": "x"}
            }
        },
        {
            "document": {
                "derived_struct_data": {"link": "gs://my-bucket/path/file.pdf"}
            }
        },
    ]
    assert m._first_gs_uri(hits) == "gs://my-bucket/path/file.pdf"
