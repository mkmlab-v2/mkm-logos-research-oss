#!/usr/bin/env python3
"""Orchestrate Logos candidate-edge human review triage ([HYPO] B-track).

Refreshes queue/gates/pack, covenant-convergence subset, and triage summary.
Does NOT auto-merge canonical or bulk-approve offline_4d.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

QUEUE = ROOT / "scripts/build_logos_candidate_edge_human_review_queue_v1.py"
CHAIN = ROOT / "scripts/run_logos_candidate_edge_review_promotion_chain_v1.py"
PACK = ROOT / "scripts/build_logos_candidate_edge_human_review_pack_v1.py"
COVENANT = ROOT / "scripts/filter_logos_review_queue_covenant_convergence_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_review_triage_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/logos_candidate_edge_review_triage_v1_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, timeout: int = 300) -> tuple[int, str]:
    proc = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, check=False, timeout=timeout
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return int(proc.returncode), out if out else err


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _wave_plan(queue_doc: dict[str, Any]) -> list[dict[str, Any]]:
    stats = queue_doc.get("stats") or {}
    return [
        {
            "wave": 1,
            "lane_id": "ann_lite",
            "priority": "primary",
            "item_count": int(stats.get("ann_lite_primary") or 0),
            "action_ko": "휴먼 검수 → signoff → pending(완료 시 canonical 소량 merge)",
        },
        {
            "wave": 2,
            "lane_id": "offline_4d_knn",
            "priority": "secondary_4d_only",
            "item_count": int(stats.get("offline_4d_only") or 0),
            "action_ko": "포화 레인 — LoRA strict 소배치만; bulk merge 금지",
        },
    ]


def build_triage_doc(steps: list[dict[str, Any]], *, exit_code: int) -> dict[str, Any]:
    queue_doc = _read_json(ROOT / "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json")
    chain_doc = _read_json(ROOT / "docs/final/artifacts/logos_candidate_edge_review_promotion_chain_v1_latest.json")
    covenant_doc = _read_json(ROOT / "docs/final/artifacts/logos_review_queue_covenant_convergence_v1_latest.json")
    pack_doc = _read_json(ROOT / "reports/logos_candidate_edge_human_review_pack_v1_latest.json")
    ann_promo = _read_json(ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_ann_lite_v1_latest.json")
    merge_doc = _read_json(ROOT / "docs/final/artifacts/logos_candidate_edge_canonical_merge_v1_latest.json")
    bundle_doc = _read_json(ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json")

    gf = bundle_doc.get("graph_files") if isinstance(bundle_doc.get("graph_files"), dict) else {}
    return {
        "schema": "logos_candidate_edge_review_triage_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "exit_code": exit_code,
        "queue_stats": queue_doc.get("stats"),
        "gates_summary": chain_doc.get("gates_summary"),
        "wave_plan": _wave_plan(queue_doc),
        "covenant_convergence": {
            "selected_count": (covenant_doc.get("stats") or {}).get("selected_count"),
            "candidates_matched": (covenant_doc.get("stats") or {}).get("candidates_matched"),
            "artifact": "docs/final/artifacts/logos_review_queue_covenant_convergence_v1_latest.json",
        },
        "ann_lite_promotion": {
            "status": ann_promo.get("status"),
            "promoted_count": ann_promo.get("promoted_count"),
            "pending_jsonl": ann_promo.get("pending_jsonl"),
        },
        "canonical_snapshot": {
            "edges_line_count": gf.get("edges_line_count"),
            "nodes_line_count": gf.get("nodes_line_count"),
            "last_merge_appended": merge_doc.get("appended_count"),
            "last_merge_at_utc": merge_doc.get("generated_at_utc"),
        },
        "review_pack_verdict": (pack_doc.get("combined_decision") or {}).get("human_decision"),
        "recommended_next_ko": [
            "Wave1 ann_lite: commander review pack 상위 15 → approve/reject/defer",
            "승인 후 run_logos_candidate_edge_ann_lite_canonical_merge_chain_v1.py (소량 merge + gold/subgraph)",
            "Wave2 offline_4d: saturation_warning_ack + LoRA strict spike만; 500 bulk 금지",
        ],
        "steps": steps,
    }


def _render_md(doc: dict[str, Any]) -> str:
    stats = doc.get("queue_stats") or {}
    lines = [
        "# Logos candidate-edge review triage v1",
        "",
        f"- generated: `{doc.get('generated_at_utc')}`",
        f"- exit_code: `{doc.get('exit_code')}`",
        f"- research_only / non_gating: **true**",
        "",
        "## Queue",
        f"- total: **{stats.get('total_items')}** · ann_lite primary: **{stats.get('ann_lite_primary')}** · offline_4d: **{stats.get('offline_4d_only')}**",
        f"- pending: **{stats.get('pending_count')}** · approved: **{stats.get('approved_count')}**",
        "",
        "## Covenant convergence (ann_lite sample)",
    ]
    cov = doc.get("covenant_convergence") or {}
    lines.append(f"- selected: **{cov.get('selected_count')}** / matched **{cov.get('candidates_matched')}**")
    lines.append("")
    lines.append("## Waves")
    for w in doc.get("wave_plan") or []:
        lines.append(
            f"- Wave **{w.get('wave')}** `{w.get('lane_id')}` ({w.get('item_count')}): {w.get('action_ko')}"
        )
    lines.append("")
    lines.append("## Next")
    for row in doc.get("recommended_next_ko") or []:
        lines.append(f"- {row}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-queue-refresh", action="store_true")
    ap.add_argument("--covenant-max-items", type=int, default=15)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    steps: list[dict] = []
    exit_code = 0

    if not args.skip_queue_refresh:
        for label, script in (
            ("review_queue", QUEUE),
            ("promotion_chain", CHAIN),
            ("review_pack", PACK),
        ):
            code, tail = _run([sys.executable, str(script)])
            steps.append({"step": label, "exit_code": code, "tail": tail[-200:] if len(tail) > 200 else tail})
            if code != 0:
                exit_code = code
                break

    if exit_code == 0:
        code, tail = _run(
            [
                sys.executable,
                str(COVENANT),
                "--max-items",
                str(args.covenant_max_items),
            ]
        )
        steps.append({"step": "covenant_convergence_filter", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    doc = build_triage_doc(steps, exit_code=exit_code)
    out_json = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_md = args.output_md if args.output_md.is_absolute() else ROOT / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(_render_md(doc), encoding="utf-8")

    print(json.dumps({"ok": exit_code == 0, "out_json": str(out_json), "out_md": str(out_md)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
