#!/usr/bin/env python3
"""Build showroom v6 subgraph + wire audit panel manifest ([HYPO], NON_GATING)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MVP = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
DEFAULT_REPLAY = ROOT / "reports/subgraph_router_replay_summary_latest.json"
DEFAULT_WIRE_ART = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
DEFAULT_WIRE_SHOWROOM = MVP / "showroom_logos_graph_wire_rag_poc_v1.json"
DEFAULT_V6_HTML = MVP / "public_showroom_logos_oracle_v6.html"
DEFAULT_ROUTER = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_showroom_v6_subgraph_audit_panel_v1_latest.json"
DEFAULT_SHOWROOM_COPY = MVP / "showroom_logos_subgraph_audit_panel_v1.json"
DEFAULT_SUBGRAPH_SLICE = MVP / "showroom_logos_subgraph_audit_slice_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def build(
    *,
    replay_path: Path,
    wire_showroom_path: Path,
    wire_art_path: Path,
    v6_html_path: Path,
    router_path: Path,
    copy_showroom_json: bool,
) -> dict[str, Any]:
    replay = _read(replay_path)
    wire_showroom = _read(wire_showroom_path)
    wire_art = _read(wire_art_path)
    router = _read(router_path)
    wire_doc = wire_showroom if wire_showroom else wire_art
    wire_metrics = (wire_doc.get("wire") or {}).get("honest_metrics") if isinstance(wire_doc.get("wire"), dict) else {}

    v6_html_ok = v6_html_path.is_file()
    wire_url_ok = False
    wire_audit_ui_ok = False
    subgraph_audit_ui_ok = False
    subgraph_slice_ok = DEFAULT_SUBGRAPH_SLICE.is_file()
    if v6_html_ok:
        html = v6_html_path.read_text(encoding="utf-8")
        wire_url_ok = "showroom_logos_graph_wire_rag_poc_v1.json" in html
        wire_audit_ui_ok = "wire-audit" in html and "renderWireAuditPanel" in html
        subgraph_audit_ui_ok = (
            "subgraph-audit" in html
            and "renderSubgraphAuditPanel" in html
            and "showroom_logos_subgraph_audit_slice_v1.json" in html
        )

    rows = [r for r in (replay.get("rows") or []) if isinstance(r, dict)]
    pass_count = sum(1 for r in rows if r.get("pass"))
    q01_row = next((r for r in rows if r.get("query_id") == "q01"), None)

    doc = {
        "schema": "logos_showroom_v6_subgraph_audit_panel_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "send_gate": "HOLD",
        "showroom_v6_html": _rel(v6_html_path),
        "showroom_wire_poc_json": _rel(wire_showroom_path),
        "subgraph_replay_summary": _rel(replay_path),
        "subgraph_router_latest": _rel(router_path),
        "subgraph_replay_pass": replay.get("pass") is True,
        "subgraph_replay_pass_count": pass_count,
        "subgraph_replay_query_count": int(replay.get("query_count") or len(rows)),
        "router_q01_bridges_matched": (q01_row or {}).get("bridges_matched"),
        "router_latest_bridges_matched": router.get("bridges_matched"),
        "router_latest_paths": len(router.get("paths") or []),
        "wire_audit_panel": {
            "v6_html_present": v6_html_ok,
            "wire_poc_url_embedded": wire_url_ok,
            "wire_audit_ui_present": wire_audit_ui_ok,
            "subgraph_audit_ui_present": subgraph_audit_ui_ok,
            "subgraph_audit_slice_present": subgraph_slice_ok,
            "honest_metrics": wire_metrics,
            "payload_savings_ratio": wire_metrics.get("payload_savings_ratio"),
        },
        "era_metric_boundary": (
            "MS era text_blind ~4.3% applies to chronology eval only; "
            "subgraph router replay is not era hit-rate and not Track A."
        ),
        "policy": {
            "no_prophecy_hit_rate_claim": True,
            "no_track_a_merge": True,
            "showroom_product_url": "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1",
        },
    }

    if copy_showroom_json:
        DEFAULT_SHOWROOM_COPY.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_SHOWROOM_COPY.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        doc["showroom_audit_panel_copy"] = _rel(DEFAULT_SHOWROOM_COPY)

    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replay-json", type=Path, default=DEFAULT_REPLAY)
    ap.add_argument("--wire-showroom-json", type=Path, default=DEFAULT_WIRE_SHOWROOM)
    ap.add_argument("--wire-artifact-json", type=Path, default=DEFAULT_WIRE_ART)
    ap.add_argument("--v6-html", type=Path, default=DEFAULT_V6_HTML)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--copy-showroom-json", action="store_true", default=True)
    ap.add_argument("--no-copy-showroom-json", action="store_false", dest="copy_showroom_json")
    args = ap.parse_args()

    doc = build(
        replay_path=args.replay_json,
        wire_showroom_path=args.wire_showroom_json,
        wire_art_path=args.wire_artifact_json,
        v6_html_path=args.v6_html,
        router_path=args.router_json,
        copy_showroom_json=args.copy_showroom_json,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "replay_pass": doc["subgraph_replay_pass"],
                "out": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
