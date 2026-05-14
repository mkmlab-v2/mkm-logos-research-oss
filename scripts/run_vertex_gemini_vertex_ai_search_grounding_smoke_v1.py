#!/usr/bin/env python3
"""Vertex AI Gemini smoke: grounding via Vertex AI Search (Discovery Engine).

Uses google-genai on Vertex (ADC / project billing), not the Developer API key.

Prereqs:
  py -m pip install "google-genai>=1.0.0"
  gcloud auth application-default login
  gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT

  IAM (calling principal needs Discovery Engine access for retrieval), see:
  https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-vertex-ai-search

Examples:
  py scripts/run_vertex_gemini_vertex_ai_search_grounding_smoke_v1.py --project mkm-lab-agi-2025

  py scripts/run_vertex_gemini_vertex_ai_search_grounding_smoke_v1.py \\
    --project mkm-lab-agi-2025 --engine-id b2g-search-mkm-lab-agi-2025 \\
    --client vertex_global_http

Docs:
  https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-vertex-ai-search

If grounding_chunks stays empty despite good Search hits, use explicit RAG:
  scripts/run_vertex_gemini_agent_search_context_v1.py (SearchServiceClient -> prompt).
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _engine_resource(project: str, location: str, engine_id: str) -> str:
    return (
        f"projects/{project}/locations/{location}/collections/default_collection/"
        f"engines/{engine_id}"
    )


def _data_store_resource(project: str, location: str, data_store_id: str) -> str:
    return (
        f"projects/{project}/locations/{location}/collections/default_collection/"
        f"dataStores/{data_store_id}"
    )


def _build_client(
    *,
    project: str,
    vertex_location: str,
    client_mode: str,
):
    from google import genai
    from google.genai import types

    if client_mode == "vertex_global_http":
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
        os.environ["GOOGLE_CLOUD_PROJECT"] = project
        os.environ["GOOGLE_CLOUD_LOCATION"] = vertex_location
        return genai.Client(http_options=types.HttpOptions(api_version="v1"))

    if client_mode == "vertex":
        return genai.Client(vertexai=True, project=project, location=vertex_location)

    raise ValueError(f"Unknown --client {client_mode!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", default="", help="GCP project id (or set GOOGLE_CLOUD_PROJECT)")
    ap.add_argument(
        "--vertex-location",
        default="global",
        help='Vertex / GenAI request location (default: "global"; aligns with global data stores)',
    )
    ap.add_argument(
        "--search-location",
        default="global",
        help="Discovery Engine path segment for engine/dataStore resource (default: global)",
    )
    ap.add_argument(
        "--engine-id",
        default="",
        help="If set, use VertexAISearch.engine (mutually exclusive with --data-store-id)",
    )
    ap.add_argument(
        "--data-store-id",
        default="",
        help="If set, use VertexAISearch.datastore (mutually exclusive with --engine-id)",
    )
    ap.add_argument(
        "--client",
        choices=("vertex", "vertex_global_http"),
        default="vertex_global_http",
        help="vertex_global_http matches Cloud doc (HttpOptions v1 + env). "
        "vertex uses genai.Client(vertexai=True, …).",
    )
    ap.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Vertex publisher model id (default: gemini-2.5-flash)",
    )
    ap.add_argument(
        "--prompt",
        default=(
            "Using only retrieved documents from the search tool: "
            "what is the document title or gs:// URI you see? Answer in one short Korean sentence."
        ),
    )
    args = ap.parse_args()

    project = (args.project or os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
    if not project:
        print("Pass --project or set GOOGLE_CLOUD_PROJECT.", file=sys.stderr)
        return 1

    eng = (args.engine_id or "").strip()
    ds = (args.data_store_id or "").strip()
    if eng and ds:
        print("Use only one of --engine-id or --data-store-id.", file=sys.stderr)
        return 1
    if not eng and not ds:
        if project == "mkm-lab-agi-2025":
            ds = "b2g-rag-mkm-lab-agi-2025"
        else:
            print(
                "Pass --data-store-id or --engine-id (no default for this project).",
                file=sys.stderr,
            )
            return 1

    vloc = (args.vertex_location or "").strip() or "global"

    try:
        from google.genai import types
    except ImportError:
        print('Install: py -m pip install "google-genai>=1.0.0"', file=sys.stderr)
        return 2

    if eng:
        target = types.VertexAISearch(
            engine=_engine_resource(project, args.search_location, eng),
            max_results=10,
        )
    else:
        target = types.VertexAISearch(
            datastore=_data_store_resource(project, args.search_location, ds),
            max_results=10,
        )

    tools = [types.Tool(retrieval=types.Retrieval(vertex_ai_search=target))]

    client = _build_client(project=project, vertex_location=vloc, client_mode=args.client)
    r = client.models.generate_content(
        model=args.model,
        contents=args.prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=512,
            tools=tools,
        ),
    )

    text = (getattr(r, "text", None) or "").strip()
    print(text or "(empty text)")
    cand0 = (r.candidates or [None])[0]
    gm = getattr(cand0, "grounding_metadata", None) if cand0 else None

    weak = not text
    d: dict = {}
    if gm:
        try:
            d = gm.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
            blob = json.dumps(d, ensure_ascii=False, indent=2)[:12000]
            print("\n--- grounding_metadata (JSON) ---\n" + blob)
            weak = weak or not (d.get("grounding_chunks") or d.get("grounding_supports"))
        except Exception:
            print("\n--- grounding_metadata (repr) ---\n" + repr(gm)[:8000])
            weak = True
    else:
        weak = True

    if weak:
        _print_troubleshooting(project, eng or ds, vloc, args.client)

    return 0


def _print_troubleshooting(project: str, store_or_engine: str, vloc: str, client_mode: str) -> None:
    print(
        "\n--- note ---\n"
        "If the answer ignores your corpus or grounding_metadata is empty, typical causes are:\n"
        "- IAM: principal needs roles/discoveryengine.viewer (or editor) and Vertex AI User on the project.\n"
        "- AI Applications / data store not fully onboarded; complete console onboarding once.\n"
        "- Try the other --client mode (vertex vs vertex_global_http) or match --vertex-location "
        f"to your setup (now {vloc!r}, client={client_mode!r}).\n"
        "- Confirm Search API returns hits: py scripts/query_agent_search_engine_v1.py "
        f"--project {project} --engine-id b2g-search-mkm-lab-agi-2025 --query MKM\n",
        file=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
