#!/usr/bin/env python3
"""Run a test query against a Discovery Engine (Agent Search) search engine.

  pip install "google-cloud-discoveryengine>=0.11.0"
  gcloud auth application-default login

Example:

  py scripts/query_agent_search_engine_v1.py --project mkm-lab-agi-2025 \\
    --engine-id b2g-search-mkm-lab-agi-2025 --query smoke

  Snippets are requested by default (``snippet_spec``); use ``--no-snippets`` to omit.
"""

from __future__ import annotations

import argparse
import json
import sys


def _serving_config(project: str, location: str, engine_id: str) -> str:
    return (
        f"projects/{project}/locations/{location}/collections/default_collection/"
        f"engines/{engine_id}/servingConfigs/default_serving_config"
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", required=True)
    p.add_argument("--location", default="global")
    p.add_argument("--engine-id", required=True)
    p.add_argument("--query", default="MKM")
    p.add_argument("--page-size", type=int, default=5)
    p.add_argument(
        "--no-snippets",
        action="store_true",
        help="Omit snippet_spec (default: return_snippet=True for parity with run_vertex_gemini_agent_search_context_v1)",
    )
    args = p.parse_args()

    try:
        from google.cloud.discoveryengine_v1 import SearchServiceClient
        from google.cloud.discoveryengine_v1.types import SearchRequest
    except ImportError:
        print(
            'Missing dependency: py -m pip install "google-cloud-discoveryengine>=0.11.0"',
            file=sys.stderr,
        )
        return 2

    serving = _serving_config(args.project, args.location, args.engine_id)
    client = SearchServiceClient()
    cs = None
    if not args.no_snippets:
        cs = SearchRequest.ContentSearchSpec(
            snippet_spec=SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True,
                max_snippet_count=5,
                reference_only=False,
            ),
        )
    req = SearchRequest(
        serving_config=serving,
        query=args.query,
        page_size=args.page_size,
        content_search_spec=cs,
    )
    print(f"serving_config={serving!r}\nquery={args.query!r}\n---")
    from google.protobuf.json_format import MessageToDict

    n_hits = 0
    for hit in client.search(request=req):
        n_hits += 1
        d = MessageToDict(hit._pb, preserving_proto_field_name=True)  # type: ignore[attr-defined]
        print(json.dumps(d, ensure_ascii=False, indent=2)[:12000])
        if n_hits >= args.page_size:
            break
    if n_hits == 0:
        print("(no hits — indexing may still be running, or query has no match)")
    else:
        print(f"---\nPrinted {n_hits} hit(s) (page_size cap={args.page_size}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
