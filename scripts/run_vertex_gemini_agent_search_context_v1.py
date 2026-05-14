#!/usr/bin/env python3
"""Vertex Gemini answer using Agent Search (Discovery Engine) hits as explicit context.

This avoids the flaky retrieval-tool grounding path: we run SearchServiceClient first,
then pass retrieved snippets/chunks into Gemini as plain text (reliable RAG pattern).

Context modes:
  documents — default; optional snippet_spec (PDFs often return NO_SNIPPET_AVAILABLE).
  chunks    — CHUNKS search_result_mode; chunk.content is often short but non-empty.
  hybrid    — documents + snippets first; if usable snippet text is tiny, append chunk hits.

Optional --pull-gcs-pdf-text: resolve gs:// from document hit link, or from GetDocument
  via first chunk hit (chunks mode), then download (google-cloud-storage) +
  extract text (pypdf or PyPDF2). Not installed => skipped with stderr note.

--skip-gemini: print retrieval + context only (no generate_content; good for quick checks).

Prereqs:
  py -m pip install "google-genai>=1.0.0" "google-cloud-discoveryengine>=0.11.0"
  gcloud auth application-default login

Vertex Gemini region: many models are served from us-central1; datastore/engine stay
locations/global. Override with --vertex-location or GOOGLE_CLOUD_LOCATION.

Example:
  py scripts/run_vertex_gemini_agent_search_context_v1.py \\
    --project mkm-lab-agi-2025 --engine-id b2g-search-mkm-lab-agi-2025 \\
    --query MKM --question "한 문장으로 무슨 파일이 검색됐는지 말해 줘."
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from typing import Any, List

from google.protobuf.json_format import MessageToDict


def _serving_config(project: str, location: str, engine_id: str) -> str:
    return (
        f"projects/{project}/locations/{location}/collections/default_collection/"
        f"engines/{engine_id}/servingConfigs/default_serving_config"
    )


def _snippet_spec() -> Any:
    from google.cloud.discoveryengine_v1.types import SearchRequest

    return SearchRequest.ContentSearchSpec.SnippetSpec(
        return_snippet=True,
        max_snippet_count=5,
        reference_only=False,
    )


def _collect_hits_documents(
    project: str,
    location: str,
    engine_id: str,
    query: str,
    top_k: int,
    *,
    with_snippets: bool,
) -> List[dict[str, Any]]:
    from google.cloud.discoveryengine_v1 import SearchServiceClient
    from google.cloud.discoveryengine_v1.types import SearchRequest

    serving = _serving_config(project, location, engine_id)
    client = SearchServiceClient()
    cs: Any = None
    if with_snippets:
        cs = SearchRequest.ContentSearchSpec(snippet_spec=_snippet_spec())
    req = SearchRequest(
        serving_config=serving,
        query=query,
        page_size=top_k,
        content_search_spec=cs,
    )
    out: List[dict[str, Any]] = []
    for hit in client.search(request=req):
        d = MessageToDict(hit._pb, preserving_proto_field_name=True)  # type: ignore[attr-defined]
        out.append(d)
        if len(out) >= top_k:
            break
    return out


def _collect_hits_chunks(
    project: str,
    location: str,
    engine_id: str,
    query: str,
    top_k: int,
) -> List[dict[str, Any]]:
    from google.cloud.discoveryengine_v1 import SearchServiceClient
    from google.cloud.discoveryengine_v1.types import SearchRequest

    serving = _serving_config(project, location, engine_id)
    client = SearchServiceClient()
    cs = SearchRequest.ContentSearchSpec(
        search_result_mode=SearchRequest.ContentSearchSpec.SearchResultMode.CHUNKS,
        chunk_spec=SearchRequest.ContentSearchSpec.ChunkSpec(
            num_previous_chunks=0,
            num_next_chunks=0,
        ),
    )
    req = SearchRequest(
        serving_config=serving,
        query=query,
        page_size=top_k,
        content_search_spec=cs,
    )
    out: List[dict[str, Any]] = []
    for hit in client.search(request=req):
        d = MessageToDict(hit._pb, preserving_proto_field_name=True)  # type: ignore[attr-defined]
        out.append(d)
        if len(out) >= top_k:
            break
    return out


def _usable_snippet_chars(hits: List[dict[str, Any]]) -> int:
    n = 0
    for h in hits:
        doc = (h.get("document") or {}) if isinstance(h, dict) else {}
        dsd = doc.get("derived_struct_data") or {}
        for sn in dsd.get("snippets") or []:
            if not isinstance(sn, dict):
                continue
            if sn.get("snippet_status") == "NO_SNIPPET_AVAILABLE":
                continue
            body = (sn.get("snippet") or "").strip()
            if body and "No snippet is available" not in body:
                n += len(body)
    return n


def _doc_id_from_chunk_name(chunk_name: str) -> str:
    m = re.search(r"/documents/([^/]+)/chunks/", chunk_name)
    return m.group(1) if m else ""


def _append_chunk_lines(lines: List[str], chunk_hits: List[dict[str, Any]], label: str) -> None:
    lines.append(label)
    for j, h in enumerate(chunk_hits, 1):
        ch = (h.get("chunk") or {}) if isinstance(h, dict) else {}
        cname = ch.get("name") or ""
        cid = ch.get("id") or ""
        content = (ch.get("content") or "").strip()
        doc_id = _doc_id_from_chunk_name(cname)
        lines.append(f"[c{j}] doc_id={doc_id} chunk_id={cid}\ncontent={content}\n")


def _hits_to_context_block(
    hits: List[dict[str, Any]],
    *,
    max_chars: int = 12000,
    chunk_hits: List[dict[str, Any]] | None = None,
) -> str:
    lines: List[str] = []
    for i, h in enumerate(hits, 1):
        doc = (h.get("document") or {}) if isinstance(h, dict) else {}
        did = doc.get("id", "")
        dsd = doc.get("derived_struct_data") or {}
        title = dsd.get("title") or did or f"hit_{i}"
        link = dsd.get("link") or ""
        lines.append(f"[{i}] id={did}\ntitle={title}\nlink={link}")
        snips: List[str] = []
        for sn in dsd.get("snippets") or []:
            if not isinstance(sn, dict):
                continue
            if sn.get("snippet_status") == "NO_SNIPPET_AVAILABLE":
                continue
            body = (sn.get("snippet") or "").strip()
            if body and "No snippet is available" not in body:
                snips.append(body)
        if snips:
            lines.append("snippets:\n" + "\n---\n".join(snips))
        lines.append("")
    if chunk_hits:
        _append_chunk_lines(
            lines,
            chunk_hits,
            "--- chunk retrieval (same query) ---",
        )
    text = "\n".join(lines)
    return text[:max_chars]


def _first_gs_uri(hits: List[dict[str, Any]]) -> str:
    for h in hits:
        doc = (h.get("document") or {}) if isinstance(h, dict) else {}
        dsd = doc.get("derived_struct_data") or {}
        link = (dsd.get("link") or "").strip()
        if link.startswith("gs://"):
            return link
    return ""


def _document_name_from_chunk_resource(chunk_name: str) -> str:
    """Strip /chunks/N suffix so name is valid for DocumentService.GetDocument."""
    if "/chunks/" not in chunk_name:
        return ""
    return chunk_name.split("/chunks/", 1)[0]


def _gs_uri_from_chunk_hits(chunk_hits: List[dict[str, Any]]) -> str:
    """Resolve gs:// from indexed Document.content.uri (chunks mode has no link in hit)."""
    if not chunk_hits:
        return ""
    ch0 = (chunk_hits[0].get("chunk") or {}) if isinstance(chunk_hits[0], dict) else {}
    cname = (ch0.get("name") or "").strip()
    doc_name = _document_name_from_chunk_resource(cname)
    if not doc_name:
        return ""
    try:
        from google.cloud.discoveryengine_v1 import DocumentServiceClient
    except ImportError:
        return ""
    try:
        client = DocumentServiceClient()
        doc = client.get_document(name=doc_name)
        d = MessageToDict(doc._pb, preserving_proto_field_name=True)  # type: ignore[attr-defined]
        uri = ((d.get("content") or {}) or {}).get("uri") or ""
        uri = str(uri).strip()
        if uri.startswith("gs://"):
            return uri
    except Exception:
        return ""
    return ""


def _resolve_gs_uri_for_pull(
    hits_doc: List[dict[str, Any]],
    chunk_hits: List[dict[str, Any]] | None,
) -> str:
    u = _first_gs_uri(hits_doc)
    if u:
        return u
    if chunk_hits:
        return _gs_uri_from_chunk_hits(chunk_hits)
    return ""


def _gcs_pdf_text(gs_uri: str, max_chars: int) -> str:
    if not gs_uri.startswith("gs://") or max_chars <= 0:
        return ""
    rest = gs_uri[len("gs://") :]
    if "/" not in rest:
        return ""
    bucket_name, blob_path = rest.split("/", 1)
    try:
        from google.cloud import storage  # type: ignore
    except ImportError:
        print(
            "Optional: py -m pip install google-cloud-storage for --pull-gcs-pdf-text",
            file=sys.stderr,
        )
        return ""
    try:
        import pypdf  # type: ignore
    except ImportError:
        try:
            import PyPDF2 as pypdf  # type: ignore
        except ImportError:
            print(
                "Optional: py -m pip install pypdf for --pull-gcs-pdf-text",
                file=sys.stderr,
            )
            return ""
    import logging

    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_path)
    data = blob.download_as_bytes()
    log_pdf = logging.getLogger("pypdf")
    prev = log_pdf.level
    log_pdf.setLevel(logging.CRITICAL)
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        parts: List[str] = []
        for page in reader.pages[:8]:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t.strip())
        out = "\n\n".join(parts).strip()
        return out[:max_chars]
    finally:
        log_pdf.setLevel(prev)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", required=True)
    ap.add_argument("--search-location", default="global")
    ap.add_argument("--engine-id", required=True)
    ap.add_argument("--query", required=True, help="Search query for Agent Search")
    ap.add_argument(
        "--question",
        default="Summarize what the top hit is about in one Korean sentence. Cite the title.",
    )
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument(
        "--context-mode",
        choices=("documents", "chunks", "hybrid"),
        default="hybrid",
        help="documents=metadata+snippet_spec; chunks=CHUNKS only; hybrid=documents then chunks if snippets empty",
    )
    ap.add_argument(
        "--hybrid-snippet-threshold",
        type=int,
        default=40,
        help="In hybrid mode, if usable snippet chars < this, append chunk hits",
    )
    ap.add_argument(
        "--chunk-top-k",
        type=int,
        default=12,
        help="Max chunk hits when context-mode=chunks or hybrid backfill",
    )
    ap.add_argument(
        "--vertex-location",
        default="",
        help="Vertex region for Gemini (default: GOOGLE_CLOUD_LOCATION or us-central1)",
    )
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument(
        "--pull-gcs-pdf-text",
        action="store_true",
        help="Append text from first gs:// PDF hit (needs google-cloud-storage + pypdf)",
    )
    ap.add_argument(
        "--gcs-text-max-chars",
        type=int,
        default=6000,
        help="Cap for --pull-gcs-pdf-text extracted body",
    )
    ap.add_argument(
        "--skip-gemini",
        action="store_true",
        help="Stop after printing retrieval + context (no Vertex generate_content)",
    )
    args = ap.parse_args()

    vloc = (
        (args.vertex_location or "").strip()
        or (os.environ.get("GOOGLE_CLOUD_LOCATION") or "").strip()
        or "us-central1"
    )

    chunk_hits: List[dict[str, Any]] | None = None
    hits_for_print: List[dict[str, Any]]
    chunks_for_gs_pull: List[dict[str, Any]] | None = None
    if args.context_mode == "chunks":
        chunk_only = _collect_hits_chunks(
            args.project,
            args.search_location,
            args.engine_id,
            args.query,
            args.chunk_top_k,
        )
        hits = []
        hits_for_print = chunk_only
        ctx = _hits_to_context_block([], chunk_hits=chunk_only)
        chunks_for_gs_pull = chunk_only
    else:
        hits = _collect_hits_documents(
            args.project,
            args.search_location,
            args.engine_id,
            args.query,
            args.top_k,
            with_snippets=True,
        )
        hits_for_print = list(hits)
        if args.context_mode == "hybrid" and _usable_snippet_chars(hits) < int(
            args.hybrid_snippet_threshold
        ):
            chunk_hits = _collect_hits_chunks(
                args.project,
                args.search_location,
                args.engine_id,
                args.query,
                args.chunk_top_k,
            )
        ctx = _hits_to_context_block(hits, chunk_hits=chunk_hits)
        chunks_for_gs_pull = chunk_hits

    if args.context_mode == "chunks":
        if not hits_for_print:
            print("No chunk hits; check engine id and indexed data.", file=sys.stderr)
            return 1
    elif not hits:
        print("No search hits; check engine id and indexed data.", file=sys.stderr)
        return 1
    extra = ""
    if args.pull_gcs_pdf_text:
        gs = _resolve_gs_uri_for_pull(hits, chunks_for_gs_pull)
        if gs.lower().endswith(".pdf"):
            tx = _gcs_pdf_text(gs, int(args.gcs_text_max_chars))
            if tx:
                extra = f"\n--- gcs pdf text ({gs}) ---\n{tx}\n"
            else:
                print(
                    "--pull-gcs-pdf-text: object readable but extract_text() returned empty "
                    "(image-only PDF, encoding, or parser limits).",
                    file=sys.stderr,
                )
        elif gs:
            print(
                f"--pull-gcs-pdf-text: first gs uri is not .pdf ({gs!r}); skip",
                file=sys.stderr,
            )
    ctx = (ctx + extra)[:20000]

    print(
        "--- retrieval (Agent Search) ---\n"
        + json.dumps(hits_for_print, ensure_ascii=False, indent=2)[:8000]
    )
    if chunk_hits is not None:
        print(
            "\n--- chunk backfill ---\n"
            + json.dumps(chunk_hits, ensure_ascii=False, indent=2)[:8000]
        )
    print("\n--- context block (trimmed) ---\n" + ctx[:6000])

    if args.skip_gemini:
        return 0

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print('Install: py -m pip install "google-genai>=1.0.0"', file=sys.stderr)
        return 2

    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", args.project)
    client = genai.Client(vertexai=True, project=args.project, location=vloc)
    sys_msg = (
        "You are a careful assistant. Answer ONLY using the EXCERPTS block. "
        "If excerpts are insufficient, say what is missing. Do not invent URLs."
    )
    user_msg = f"EXCERPTS:\n{ctx}\n\nQUESTION:\n{args.question}\n"
    r = client.models.generate_content(
        model=args.model,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=sys_msg,
            temperature=0.2,
            max_output_tokens=512,
        ),
    )
    print("\n--- Gemini (Vertex) ---\n" + (r.text or "").strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
