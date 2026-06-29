#!/usr/bin/env python3
"""Run Job reading-pack verify chain: pack3 → pack2 → pack1 ([HYPO]).

Reproducible:
  py scripts/run_logos_job_reading_pack_verify_chain_v1.py
  py scripts/run_logos_job_reading_pack_verify_chain_v1.py --with-ingest
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_INPUT = ROOT / "data/logos/topology_sidecar_job_suffering_hypo_v1.seed.json"
CHAIN_REPORT = ROOT / "reports/logos_job_reading_pack_verify_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def run_chain(*, with_ingest: bool, input_path: Path) -> dict[str, Any]:
    steps: dict[str, Any] = {}
    errors: list[str] = []

    if with_ingest:
        from scripts.run_logos_topology_sidecar_ingest_chain_v1 import run_chain as ingest_chain

        ingest = ingest_chain(input_path=input_path)
        steps["topology_ingest"] = {"ok": ingest.get("ok"), "send_gate": ingest.get("send_gate")}
        if not ingest.get("ok"):
            errors.append("topology sidecar ingest chain failed")

    from scripts.verify_logos_job_literal_council_v1 import verify as verify_pack3
    from scripts.verify_logos_job_scope_reset_v1 import verify as verify_pack2
    from scripts.verify_logos_job_bridge_lemma_v1 import verify as verify_pack1

    pack3 = verify_pack3(
        corpus=ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl",
        topology_path=ROOT / "docs/final/artifacts/logos_topology_sidecar_job_suffering_reason_v1_latest.json",
    )
    pack2 = verify_pack2(
        corpus=ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl",
        topology_path=ROOT / "docs/final/artifacts/logos_topology_sidecar_job_suffering_reason_v1_latest.json",
        theme_path=ROOT / "docs/research/logos_metaphor_db_v1/theme_39_job_suffering.json",
    )
    pack1 = verify_pack1(
        corpus=ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl",
        topology_path=ROOT / "docs/final/artifacts/logos_topology_sidecar_job_suffering_reason_v1_latest.json",
        router_path=ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json",
    )

    for pack_id, report, out_name in (
        ("literal_council_only", pack3, "logos_job_literal_council_verify_v1_latest.json"),
        ("scope_reset_no_why", pack2, "logos_job_scope_reset_verify_v1_latest.json"),
        ("integrated_topology", pack1, "logos_job_bridge_lemma_verify_v1_latest.json"),
    ):
        out_path = ROOT / "reports" / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        steps[pack_id] = {
            "ok": report.get("ok"),
            "artifact": _rel(out_path),
            "errors": report.get("errors") or [],
        }
        if not report.get("ok"):
            errors.extend(report.get("errors") or [f"{pack_id} verify failed"])

    ok = not errors
    chain = {
        "schema": "logos_job_reading_pack_verify_chain_v1",
        "ok": ok,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "query_id": "job_suffering_reason",
        "reading_pack_order": ["literal_council_only", "scope_reset_no_why", "integrated_topology"],
        "steps": steps,
        "errors": errors,
        "reproduce": (
            "py scripts/run_logos_job_reading_pack_verify_chain_v1.py --with-ingest"
            if with_ingest
            else "py scripts/run_logos_job_reading_pack_verify_chain_v1.py"
        ),
    }
    CHAIN_REPORT.parent.mkdir(parents=True, exist_ok=True)
    CHAIN_REPORT.write_text(json.dumps(chain, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return chain


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--with-ingest", action="store_true", help="Run topology sidecar ingest before verify")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = ap.parse_args()
    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    if args.with_ingest and not input_path.is_file():
        print(f"Missing input: {input_path}", file=sys.stderr)
        return 2
    chain = run_chain(with_ingest=args.with_ingest, input_path=input_path)
    print(f"WROTE: {CHAIN_REPORT}")
    print(f"  ok={chain['ok']} packs={len(chain['reading_pack_order'])}")
    if not chain["ok"]:
        print("\n".join(chain["errors"]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
