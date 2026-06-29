#!/usr/bin/env python3
"""Track L L3 readiness: GraphRAG bridge SSOT + subgraph router smoke + pytest."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
L2_SCRIPT = ROOT / "scripts/run_logos_track_l_l2_readiness_v1.py"
ROUTER = ROOT / "scripts/run_logos_subgraph_graphrag_router_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_l_l3_readiness_v1_latest.json"

BRIDGE_MD = ROOT / "docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md"
GRAPH_BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
CONCEPT_REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
LANE_CONTRACT = ROOT / "docs/final/artifacts/graph_subgraph_router_lane_contract_v1_latest.json"
ROUTER_SCHEMA = ROOT / "docs/final/schemas/logos_subgraph_graphrag_router_v1.schema.json"
ROUTER_OUT = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _run_py(args: list[str], *, timeout: int = 300) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    tail = (proc.stdout or proc.stderr or "").strip()
    return proc.returncode, tail[-1200:] if len(tail) > 1200 else tail


def _file_check(path: Path, label: str) -> dict[str, Any]:
    ok = path.is_file()
    extra: dict[str, Any] = {}
    if ok and path.suffix == ".json":
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
            if label == "graph_bundle":
                gf = doc.get("graph_files") if isinstance(doc.get("graph_files"), dict) else {}
                extra["edges_line_count"] = gf.get("edges_line_count")
                extra["nodes_line_count"] = gf.get("nodes_line_count")
            if label == "concept_registry":
                extra["bridge_count"] = len(doc.get("bridges") or doc.get("entries") or [])
        except json.JSONDecodeError:
            ok = False
            extra["error"] = "json_decode_failed"
    return {"ok": ok, "path": _rel(path), **extra}


def build_report(*, skip_l2: bool) -> dict[str, Any]:
    l2: dict[str, Any]
    if skip_l2:
        l2 = {"skipped": True, "l2_ok": True}
    else:
        rc, tail = _run_py([str(L2_SCRIPT)], timeout=240)
        l2_ok = False
        l2_path = ROOT / "docs/final/artifacts/logos_track_l_l2_readiness_v1_latest.json"
        if l2_path.is_file():
            try:
                l2_ok = bool(json.loads(l2_path.read_text(encoding="utf-8")).get("l2_ok"))
            except json.JSONDecodeError:
                l2_ok = False
        l2 = {"exit_code": rc, "l2_ok": l2_ok and rc == 0, "tail": tail}

    static = {
        "bridge_md": _file_check(BRIDGE_MD, "bridge_md"),
        "graph_bundle": _file_check(GRAPH_BUNDLE, "graph_bundle"),
        "concept_registry": _file_check(CONCEPT_REGISTRY, "concept_registry"),
        "lane_contract": _file_check(LANE_CONTRACT, "lane_contract"),
        "router_schema": _file_check(ROUTER_SCHEMA, "router_schema"),
    }

    rc_router, tail_router = _run_py([str(ROUTER), "--query-id", "q01", "--top-bridges", "3"])
    router_ok = False
    router_doc: dict[str, Any] = {}
    if ROUTER_OUT.is_file():
        try:
            router_doc = json.loads(ROUTER_OUT.read_text(encoding="utf-8-sig"))
            router_ok = (
                rc_router == 0
                and router_doc.get("schema") == "logos_subgraph_graphrag_router_v1"
                and int(router_doc.get("bridges_matched") or 0) >= 1
                and bool(router_doc.get("non_gating"))
            )
        except json.JSONDecodeError:
            router_ok = False
    router_check = {
        "exit_code": rc_router,
        "ok": router_ok,
        "query_id": router_doc.get("query_id") or router_doc.get("query"),
        "bridges_matched": router_doc.get("bridges_matched"),
        "artifact": _rel(ROUTER_OUT),
        "tail": tail_router,
    }

    rc_pytest, tail_pytest = _run_py(
        [
            "-m",
            "pytest",
            "tests/test_run_logos_subgraph_graphrag_router_v1.py",
            "tests/test_build_logos_concept_bridge_registry_v1.py",
            "-q",
            "--tb=short",
        ],
        timeout=180,
    )
    pytest_check = {"exit_code": rc_pytest, "ok": rc_pytest == 0, "tail": tail_pytest}

    l3_ok = bool(
        (l2.get("skipped") or l2.get("l2_ok"))
        and all(static[k]["ok"] for k in static)
        and router_check["ok"]
        and pytest_check["ok"]
    )

    return {
        "schema": "logos_track_l_l3_readiness_v1",
        "generated_at_utc": _utc_now(),
        "track_wall": {
            "logos_non_gating": True,
            "a_track_auto_promote": False,
            "live_trading_trigger": False,
            "graphrag_research_only": True,
        },
        "l3_ok": l3_ok,
        "checks": {
            "l2_prerequisite": l2,
            "static_artifacts": static,
            "subgraph_graphrag_router_q01": router_check,
            "graphrag_pytest": pytest_check,
        },
        "pointer": "docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md §L3–L5",
        "bridge_ssot": _rel(BRIDGE_MD),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Track L L3 GraphRAG bridge readiness")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-l2", action="store_true")
    args = ap.parse_args(argv)

    doc = build_report(skip_l2=args.skip_l2)
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["l3_ok"], "wrote": str(out)}, ensure_ascii=False))
    return 0 if doc["l3_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
