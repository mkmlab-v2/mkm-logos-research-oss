#!/usr/bin/env python3
"""Saturation handoff pack — aggregates SSOT artifacts for next-stage planning ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUTO = ROOT / "docs/final/artifacts/logos_candidate_edge_auto_progress_v1_latest.json"
MAINT = ROOT / "docs/final/artifacts/logos_candidate_edge_post_saturation_maintenance_v1_latest.json"
QUEUE = ROOT / "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json"
ACK = ROOT / "docs/final/artifacts/logos_track_l_commander_external_send_ack_v1_latest.json"
BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/logos_candidate_edge_saturation_handoff_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/logos_candidate_edge_saturation_handoff_v1_latest.md"
SCHEMA = "logos_candidate_edge_saturation_handoff_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _gold_pass(maint: dict[str, Any]) -> bool | None:
    if maint.get("gold_required_all_pass") is not None:
        return bool(maint.get("gold_required_all_pass"))
    for step in maint.get("steps") or []:
        if step.get("step") == "gold_query_eval" and step.get("exit_code") == 0:
            tail = str(step.get("tail") or "")
            if "gold_required_all_pass\": true" in tail or "gold_required_all_pass': true" in tail:
                return True
    gold = _read_json(ROOT / "reports/logos_gold_query_eval_v1_latest.json")
    summary = gold.get("summary") if isinstance(gold.get("summary"), dict) else {}
    val = summary.get("gold_required_all_pass")
    return bool(val) if val is not None else None


def _render_md(payload: dict[str, Any]) -> str:
    g = payload.get("canonical_graph") or {}
    q = payload.get("queue_stats") or {}
    lines = [
        "# Logos candidate-edge — Saturation handoff",
        "",
        f"- generated: `{payload.get('generated_at_utc')}`",
        "- tags: `[HYPO]` · `[NON_GATING]` · research_only · bulk offline_4d **blocked**",
        "",
        "## Canonical graph",
        "",
        f"- nodes: **{g.get('nodes_line_count', 'n/a')}** · edges: **{g.get('edges_line_count', 'n/a')}**",
        f"- saturation_reached: **{payload.get('saturation_reached')}**",
        f"- gold_required_all_pass: **{payload.get('gold_required_all_pass')}**",
        f"- l9_l12_ok: **{payload.get('l9_l12_ok')}**",
        f"- ready_for_external_send: **{payload.get('ready_for_external_send')}** (commander ack: `{payload.get('commander_decision')}`)",
        "",
        "## Human review queue",
        "",
        f"| lane | count |",
        f"|------|------:|",
        f"| ann_lite primary (approved) | {q.get('approved_count', 'n/a')} |",
        f"| offline_4d only (pending) | {q.get('offline_4d_only', 'n/a')} |",
        f"| total pending | {q.get('pending_count', 'n/a')} |",
        "",
        "## Recommended next (manual)",
        "",
        "1. Covenant 15 subset — `reports/logos_covenant_convergence_review_pack_v1_latest.md`",
        "2. offline_4d 500 — **no bulk merge**; LoRA/full-corpus strict 소배치만",
        "3. Canonical growth stalled — spike 파라미터 실험은 B-track 별도; Track A 합선 금지",
        "4. External send — legal sign-off 전 `ready_for_external_send: false` 유지",
        "",
        "## One-click ops",
        "",
        "- `pwsh -File scripts/Run-LogosCandidateEdgeAutoProgress_v1.ps1`",
        "- `py scripts/run_logos_candidate_edge_post_saturation_maintenance_v1.py`",
        "",
        "## Evidence paths",
        "",
    ]
    for k, v in (payload.get("evidence_paths") or {}).items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    auto = _read_json(AUTO)
    maint = _read_json(MAINT)
    queue = _read_json(QUEUE)
    ack = _read_json(ACK)
    bundle = _read_json(BUNDLE)
    gf = bundle.get("graph_files") if isinstance(bundle.get("graph_files"), dict) else {}
    qstats = queue.get("stats") if isinstance(queue.get("stats"), dict) else maint.get("queue_stats") or {}

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "saturation_reached": auto.get("saturation_reached"),
        "total_appended_last_auto_run": auto.get("total_appended"),
        "canonical_graph": maint.get("canonical_graph") or {
            "nodes_line_count": gf.get("nodes_line_count"),
            "edges_line_count": gf.get("edges_line_count"),
        },
        "gold_required_all_pass": _gold_pass(maint),
        "l9_l12_ok": maint.get("l9_l12_ok"),
        "ready_for_external_send": False,
        "commander_decision": ack.get("decision"),
        "queue_stats": qstats,
        "evidence_paths": {
            "auto_progress": str(AUTO.relative_to(ROOT)).replace("\\", "/"),
            "maintenance": str(MAINT.relative_to(ROOT)).replace("\\", "/"),
            "human_review_queue": str(QUEUE.relative_to(ROOT)).replace("\\", "/"),
            "covenant_pack_md": "reports/logos_covenant_convergence_review_pack_v1_latest.md",
            "commander_ack": str(ACK.relative_to(ROOT)).replace("\\", "/"),
        },
    }

    out_json = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_md = args.out_md if args.out_md.is_absolute() else ROOT / args.out_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(_render_md(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(out_json), "out_md": str(out_md)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
