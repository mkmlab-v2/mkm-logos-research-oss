#!/usr/bin/env python3
"""Sync compression_hybrid_router_spec_v1.json from hybrid router spike report.

Reads reports/compression_hybrid_router_spike_v1_latest.json and merges route fields
into docs/final/artifacts/compression_hybrid_router_spec_v1.json (preserves corpus_tag,
input_path, sku_class). research_only · SEND_GATE HOLD · no ACTIVE mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SPIKE = ROOT / "reports/compression_hybrid_router_spike_v1_latest.json"
DEFAULT_SPEC = ROOT / "docs/final/artifacts/compression_hybrid_router_spec_v1.json"
CANDIDATE_ARTIFACT = (
    "docs/final/artifacts/compression_candidate_pool_on_track_a_candidate_v1_latest.json"
)

SPIKE_TO_SPEC_BACKEND: dict[str, str] = {
    "llmlingua2": "llmlingua2",
    "mkm_candidate_pool": "mkm_candidate_pool",
    "mkm_economy_shortcap": "mkm_v2_economy_shortcap",
    "mkm_economy": "mkm_v2_economy_stateless",
    "mkm_v2_economy_stateless": "mkm_v2_economy_stateless",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def binding_table_digest(bindings: list[dict[str, Any]]) -> str:
    pairs = sorted((b["corpus_id"], b["backend"]) for b in bindings)
    return hashlib.sha256(json.dumps(pairs, sort_keys=True).encode()).hexdigest()[:16]


def _route_fields(route: dict[str, Any]) -> dict[str, Any]:
    backend_raw = str(route.get("backend") or "")
    backend = SPIKE_TO_SPEC_BACKEND.get(backend_raw, backend_raw)
    out: dict[str, Any] = {
        "backend": backend,
        "reason": route.get("reason"),
    }
    for key in (
        "routing_profile",
        "enable_candidate_pool_expansion",
        "compression_profile",
        "short_context_token_threshold",
        "short_context_max_saving_rate",
        "must_keep_overlay_json",
    ):
        if route.get(key) is not None:
            out[key] = route[key]
    if backend == "mkm_candidate_pool":
        out["candidate_artifact"] = CANDIDATE_ARTIFACT
        out.setdefault("routing_profile", "candidate_pool_on")
        out.setdefault("enable_candidate_pool_expansion", True)
    if route.get("corpus_id") == "open_structured_long_v1":
        out["kpi_saving_eligible"] = False
        out.setdefault("token_proxy_caveat", "minified JSON whitespace proxy artifact")
    return out


def sync_spec(
    *,
    spike_path: Path,
    spec_path: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    spike = json.loads(spike_path.read_text(encoding="utf-8"))
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    routes = {
        str(r["corpus_id"]): r
        for r in (spike.get("routing_policy") or {}).get("routes") or []
        if isinstance(r, dict) and r.get("corpus_id")
    }
    bindings: list[dict[str, Any]] = []
    for row in spec.get("corpus_bindings") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("corpus_id") or "")
        merged = dict(row)
        if cid in routes:
            merged.update(_route_fields(routes[cid]))
        bindings.append(merged)
    spec["corpus_bindings"] = bindings
    spec["generated_at_utc"] = _utc()
    spec["sync_from_spike"] = {
        "spike_path": spike_path.relative_to(ROOT).as_posix(),
        "spike_generated_at_utc": spike.get("generated_at_utc"),
        "binding_table_digest": binding_table_digest(bindings),
        "sync_script": "scripts/sync_compression_hybrid_router_spec_from_spike_v1.py",
    }
    tier = spike.get("tier_a_gate")
    if isinstance(tier, dict):
        spec["tier_a_gate"] = tier
    spec["boundary_ack"] = (
        "Corpus-tag bindings synced from hybrid spike; v2 stub applies MKM routes including candidate_pool_on."
    )
    spec["v2_stub_binding_status"] = "partial_stub_metadata"
    if not dry_run:
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "binding_table_digest": spec["sync_from_spike"]["binding_table_digest"],
        "corpus_count": len(bindings),
        "dry_run": dry_run,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync hybrid router spec from spike report")
    ap.add_argument("--spike", type=Path, default=DEFAULT_SPIKE)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.spike.is_file():
        print(f"MISSING spike: {args.spike}", file=sys.stderr)
        return 1
    if not args.spec.is_file():
        print(f"MISSING spec: {args.spec}", file=sys.stderr)
        return 1
    result = sync_spec(spike_path=args.spike, spec_path=args.spec, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
