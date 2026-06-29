#!/usr/bin/env python3
"""Discovery Engine query burst to target GenAI App Builder trial credit SKUs.

Vertex Gemini generate uses vertex_ai billing; this script stays on Discovery Engine
SearchServiceClient only (documents+snippets and/or chunks modes).

Prereqs:
  py -m pip install "google-cloud-discoveryengine>=0.11.0"
  gcloud auth application-default login

Example:
  py scripts/run_discovery_engine_app_builder_credit_burn_v1.py \\
    --project mkm-lab-agi-2025 --engine-id b2g-search-mkm-lab-agi-2025 \\
    --query-count 100 --modes documents,chunks

Optional re-import (indexing SKU):
  py scripts/run_discovery_engine_app_builder_credit_burn_v1.py ... --incremental-import
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "discovery_engine_app_builder_credit_burn_v1_latest.json"
PROBE_OUT = ROOT / "reports" / "gcp_genai_app_builder_billing_probe_latest.json"

DEFAULT_PROJECT = "mkm-lab-agi-2025"
DEFAULT_ENGINE = "b2g-search-mkm-lab-agi-2025"
DEFAULT_BUCKET = "mkm-lab-agi-2025-vertex-ai-staging"
DEFAULT_GCS_PREFIX = "agent-search-docs/"

QUERY_SEEDS = [
    "MKM compression Track A",
    "Logos candidate edge saturation",
    "Agent Search corpus offline knn",
    "Discovery Engine billing SKU",
    "GenAI App Builder trial credit",
    "Vertex grounding retrieval",
    "compression B2B pilot",
    "prophecy promotion gates",
    "regime map IMF lehman",
    "multilens ultra compression",
    "sasang myeongni lens",
    "general prophecy brier",
    "Track C showroom publish",
    "aramaic MVP survivor health",
    "control integrity golden lora",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _serving_config(project: str, location: str, engine_id: str) -> str:
    return (
        f"projects/{project}/locations/{location}/collections/default_collection/"
        f"engines/{engine_id}/servingConfigs/default_serving_config"
    )


def _expand_queries(count: int, seeds: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while len(out) < count:
        base = seeds[i % len(seeds)]
        suffix = f" probe-{len(out) + 1}"
        out.append(f"{base}{suffix}")
        i += 1
    return out


def _run_incremental_import(project: str, bucket: str, gcs_prefix: str) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "bootstrap_agent_search_datastore_gcs_v1.py"),
        "--project",
        project,
        "--bucket",
        bucket,
        "--gcs-prefix",
        gcs_prefix,
        "--skip-create",
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return {
        "step": "incremental_import",
        "exit_code": proc.returncode,
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "stdout_tail": proc.stdout[-4000:] if proc.stdout else "",
        "stderr_tail": proc.stderr[-2000:] if proc.stderr else "",
    }


def _search_once(
    client: Any,
    SearchRequest: Any,
    *,
    serving: str,
    query: str,
    page_size: int,
    mode: str,
) -> dict[str, Any]:
    cs = None
    if mode == "documents":
        cs = SearchRequest.ContentSearchSpec(
            snippet_spec=SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True,
                max_snippet_count=5,
                reference_only=False,
            ),
        )
    elif mode == "chunks":
        cs = SearchRequest.ContentSearchSpec(
            search_result_mode=SearchRequest.ContentSearchSpec.SearchResultMode.CHUNKS,
            chunk_spec=SearchRequest.ContentSearchSpec.ChunkSpec(
                num_previous_chunks=1,
                num_next_chunks=1,
            ),
        )
    else:
        raise ValueError(f"unknown mode: {mode}")

    req = SearchRequest(
        serving_config=serving,
        query=query,
        page_size=page_size,
        content_search_spec=cs,
    )
    t0 = time.perf_counter()
    hits = 0
    for _ in client.search(request=req):
        hits += 1
        if hits >= page_size:
            break
    return {
        "query": query,
        "mode": mode,
        "hits": hits,
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", default=DEFAULT_PROJECT)
    p.add_argument("--location", default="global")
    p.add_argument("--engine-id", default=DEFAULT_ENGINE)
    p.add_argument("--query-count", type=int, default=50)
    p.add_argument("--page-size", type=int, default=10)
    p.add_argument(
        "--modes",
        default="documents,chunks",
        help="Comma-separated: documents, chunks",
    )
    p.add_argument("--incremental-import", action="store_true")
    p.add_argument("--bucket", default=DEFAULT_BUCKET)
    p.add_argument("--gcs-prefix", default=DEFAULT_GCS_PREFIX)
    p.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    p.add_argument("--update-probe", action="store_true", default=True)
    p.add_argument("--no-update-probe", dest="update_probe", action="store_false")
    p.add_argument(
        "--compact",
        action="store_true",
        help="Do not store every search row (summary + errors + sample only; for 1k+ queries)",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    for m in modes:
        if m not in {"documents", "chunks"}:
            p.error(f"invalid mode {m!r}")

    queries = _expand_queries(max(1, args.query_count), QUERY_SEEDS)
    planned_calls = len(queries) * len(modes)

    payload: dict[str, Any] = {
        "schema": "discovery_engine_app_builder_credit_burn_v1",
        "generated_at_utc": _utc_now(),
        "project_id": args.project,
        "engine_id": args.engine_id,
        "billing_surface": "discovery_engine",
        "credit_target": "Trial credit for GenAI App Builder (Console SSOT; not Vertex AI)",
        "planned": {
            "query_count": len(queries),
            "modes": modes,
            "page_size": args.page_size,
            "total_search_calls": planned_calls,
            "incremental_import": bool(args.incremental_import),
        },
        "steps": [],
        "search_results": [],
        "summary": {},
        "follow_up": (
            "Re-check Billing > Credits (Trial credit for GenAI App Builder %) and "
            "Reports filtered by Discovery Engine SKU after 24–48h. "
            "Free tier: 10k search queries/account/month (Standard/Enterprise search)."
        ),
    }

    if args.dry_run:
        payload["dry_run"] = True
        payload["sample_queries"] = queries[:5]
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.incremental_import:
        step = _run_incremental_import(args.project, args.bucket, args.gcs_prefix)
        payload["steps"].append(step)
        if step["exit_code"] != 0:
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"incremental import failed exit={step['exit_code']}", file=sys.stderr)
            return step["exit_code"]

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
    ok = 0
    fail = 0
    total_hits = 0
    t_chain = time.perf_counter()
    sample_cap = 10

    for q in queries:
        for mode in modes:
            try:
                row = _search_once(
                    client,
                    SearchRequest,
                    serving=serving,
                    query=q,
                    page_size=args.page_size,
                    mode=mode,
                )
                ok += 1
                total_hits += row["hits"]
                if args.compact:
                    if len(payload["search_results"]) < sample_cap:
                        payload["search_results"].append(row)
                    elif ok % 500 == 0:
                        print(
                            f"progress search_calls_ok={ok} failed={fail} hits={total_hits}",
                            flush=True,
                        )
                else:
                    payload["search_results"].append(row)
            except Exception as exc:  # noqa: BLE001 — burn probe must continue
                fail += 1
                payload["search_results"].append(
                    {"query": q, "mode": mode, "error": str(exc)[:500]},
                )

    if args.compact:
        payload["compact"] = True
        payload["search_results_sample_cap"] = sample_cap

    payload["summary"] = {
        "search_calls_ok": ok,
        "search_calls_failed": fail,
        "total_hits": total_hits,
        "elapsed_s": round(time.perf_counter() - t_chain, 2),
        "verdict": "burn_attempted" if ok else "burn_failed",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"wrote {args.out_json.relative_to(ROOT).as_posix()}")

    if args.update_probe and PROBE_OUT.is_file():
        probe = json.loads(PROBE_OUT.read_text(encoding="utf-8-sig"))
        probe["generated_at_utc"] = _utc_now()
        probe.setdefault("live_probes_2026_06_03", {})
        probe["live_probes_2026_06_03"]["discovery_engine_credit_burn"] = {
            "artifact": str(args.out_json.relative_to(ROOT).as_posix()),
            "search_calls_ok": ok,
            "search_calls_failed": fail,
            "total_hits": total_hits,
            "billing_surface": "discovery_engine",
            "note": "Credit % still requires Console Credits UI; burn targets DE SKU not Vertex",
        }
        probe["verdict"] = {
            **probe.get("verdict", {}),
            "genai_app_builder_credit_consumed": "pending_console_recheck_24_48h",
            "last_burn_attempt_utc": _utc_now(),
        }
        PROBE_OUT.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"updated {PROBE_OUT.relative_to(ROOT).as_posix()}")

    return 0 if ok and not fail else (1 if fail and not ok else 0)


if __name__ == "__main__":
    raise SystemExit(main())
