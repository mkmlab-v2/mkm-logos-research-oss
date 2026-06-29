#!/usr/bin/env python3
"""Track L L4/L5 readiness: lemma layer (L4) + GraphRAG evidence pack (L5)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
L3_SCRIPT = ROOT / "scripts/run_logos_track_l_l3_readiness_v1.py"
EVIDENCE_BUILDER = ROOT / "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_l_l4_l5_readiness_v1_latest.json"

LEMMA_JSONL = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
LEMMA_MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"
EVIDENCE_PACK = ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json"
REPLAY_SUMMARY = ROOT / "reports/subgraph_router_replay_summary_latest.json"
LEMMA_BUILDER = ROOT / "scripts/build_logos_lemma_verse_edges_v1.py"
GOLD_EVAL = ROOT / "reports/logos_gold_query_eval_v1_latest.json"


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


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _count_jsonl_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def build_report(*, skip_l3: bool, skip_lemma_pytest: bool) -> dict[str, Any]:
    l3: dict[str, Any]
    if skip_l3:
        l3_doc = _read_json(ROOT / "docs/final/artifacts/logos_track_l_l3_readiness_v1_latest.json")
        l3 = {"skipped": True, "l3_ok": bool(l3_doc.get("l3_ok"))}
    else:
        rc, tail = _run_py([str(L3_SCRIPT)], timeout=360)
        l3_doc = _read_json(ROOT / "docs/final/artifacts/logos_track_l_l3_readiness_v1_latest.json")
        l3 = {"exit_code": rc, "l3_ok": bool(l3_doc.get("l3_ok")) and rc == 0, "tail": tail}

    lemma_build: dict[str, Any] = {"skipped": True, "ok": LEMMA_JSONL.is_file()}
    if not LEMMA_JSONL.is_file() and LEMMA_BUILDER.is_file():
        rc_lemma, tail_lemma = _run_py([str(LEMMA_BUILDER)], timeout=120)
        lemma_build = {
            "exit_code": rc_lemma,
            "ok": rc_lemma == 0 and LEMMA_JSONL.is_file(),
            "tail": tail_lemma,
        }

    lemma_manifest_doc = _read_json(LEMMA_MANIFEST)
    edge_count_manifest = int(lemma_manifest_doc.get("edge_count") or 0)
    edge_count_effective_jsonl = _count_jsonl_rows(LEMMA_JSONL)
    edge_count_mismatch = edge_count_manifest != edge_count_effective_jsonl
    l4_checks = {
        "lemma_jsonl": {"ok": LEMMA_JSONL.is_file(), "path": _rel(LEMMA_JSONL)},
        "lemma_manifest": {"ok": LEMMA_MANIFEST.is_file(), "path": _rel(LEMMA_MANIFEST)},
        "manifest_schema_ok": lemma_manifest_doc.get("schema") == "logos_lemma_verse_edges_v1",
        "edge_count_manifest": edge_count_manifest,
        "edge_count_effective_jsonl": edge_count_effective_jsonl,
        "edge_count_mismatch": edge_count_mismatch,
    }
    l4_ok = bool(
        l4_checks["lemma_jsonl"]["ok"]
        and l4_checks["lemma_manifest"]["ok"]
        and l4_checks["manifest_schema_ok"]
        and edge_count_manifest > 0
        and edge_count_effective_jsonl > 0
        and not edge_count_mismatch
    )

    lemma_pytest = {"skipped": True, "ok": True}
    if not skip_lemma_pytest:
        rc, tail = _run_py(
            ["-m", "pytest", "tests/test_build_logos_lemma_verse_edges_v1.py", "-q", "--tb=short"],
            timeout=120,
        )
        lemma_pytest = {"exit_code": rc, "ok": rc == 0, "tail": tail}
        l4_ok = l4_ok and lemma_pytest["ok"]

    rc_pack, tail_pack = _run_py([str(EVIDENCE_BUILDER)], timeout=120)
    pack_doc = _read_json(EVIDENCE_PACK)
    replay_doc = _read_json(REPLAY_SUMMARY)
    gold_doc = _read_json(GOLD_EVAL)
    gold_summary = gold_doc.get("summary") if isinstance(gold_doc.get("summary"), dict) else {}

    l5_checks = {
        "evidence_pack_builder": {"exit_code": rc_pack, "ok": rc_pack == 0, "tail": tail_pack},
        "evidence_pack_schema_ok": pack_doc.get("schema") == "logos_graphrag_bridge_evidence_pack_v1",
        "ready_for_external_send_false": pack_doc.get("ready_for_external_send") is False,
        "replay_pass": bool(replay_doc.get("pass")),
        "replay_pass_count": replay_doc.get("pass_count"),
        "gold_eval_optional": {
            "exists": GOLD_EVAL.is_file(),
            "gold_required_all_pass": gold_summary.get("gold_required_all_pass"),
        },
    }
    l5_ok = bool(
        l5_checks["evidence_pack_builder"]["ok"]
        and l5_checks["evidence_pack_schema_ok"]
        and l5_checks["ready_for_external_send_false"]
        and l5_checks["replay_pass"]
    )

    l4_l5_ok = bool((l3.get("skipped") or l3.get("l3_ok")) and l4_ok and l5_ok)

    return {
        "schema": "logos_track_l_l4_l5_readiness_v1",
        "generated_at_utc": _utc_now(),
        "track_wall": {
            "logos_non_gating": True,
            "a_track_auto_promote": False,
            "live_trading_trigger": False,
            "graphrag_research_only": True,
            "ready_for_external_send": False,
        },
        "l4_ok": l4_ok,
        "l5_ok": l5_ok,
        "l4_l5_ok": l4_l5_ok,
        "checks": {
            "l3_prerequisite": l3,
            "l4_lemma_layer": {**l4_checks, "lemma_build": lemma_build, "lemma_pytest": lemma_pytest},
            "l5_evidence_pack": l5_checks,
        },
        "evidence_pack_path": _rel(EVIDENCE_PACK),
        "pointer": "docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md §L3–L5",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Track L L4/L5 GraphRAG bridge readiness")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-l3", action="store_true")
    ap.add_argument("--skip-lemma-pytest", action="store_true")
    args = ap.parse_args(argv)

    doc = build_report(skip_l3=args.skip_l3, skip_lemma_pytest=args.skip_lemma_pytest)
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["l4_l5_ok"], "l4_ok": doc["l4_ok"], "l5_ok": doc["l5_ok"], "wrote": str(out)}, ensure_ascii=False))
    return 0 if doc["l4_l5_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
