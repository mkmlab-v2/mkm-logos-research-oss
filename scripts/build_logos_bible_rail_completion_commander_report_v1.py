#!/usr/bin/env python3
"""Commander one-pager: Bible/Logos Track B rail completion (P9) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/logos_bible_rail_completion_gate_v1_latest.json"
OUT_JSON = ROOT / "reports/logos_bible_rail_completion_commander_report_v1_latest.json"
OUT_MD = ROOT / "reports/logos_bible_rail_completion_commander_report_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    gate = _load(GATE)
    p7 = _load(ROOT / "docs/final/artifacts/entry_13_post_promotion_gate_v1_latest.json")
    audit = _load(ROOT / "reports/psalms_entry_12_13_cross_lane_audit_v1_latest.json")
    relabel = _load(ROOT / "reports/cross_ref_entry_13_shadow_verse_relabel_sidecar_v1_latest.json")
    reg = _load(ROOT / "reports/shadow_4q_ps5_witness_registry_v1_latest.json")
    sm = reg.get("summary") or {}

    apply_log = _load(ROOT / "reports/cross_ref_entry_12_13_apply_log_v1_latest.json")
    va_pkt = _load(ROOT / "reports/entry_13_ps5_2_verified_anchor_evidence_packet_v1_latest.json")

    return {
        "schema": "logos_bible_rail_completion_commander_report_v1",
        "version": "2.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "bible_rail_status": gate.get("bible_rail_status"),
        "completion_gate_ok": gate.get("gate_ok"),
        "phases_closed": ["P5", "P6", "P7", "P8", "P9"],
        "entry_12": "mt_only · 11Q5 retired · CROSS_REF applied",
        "entry_13": {
            "status": "commander_verified_shadow_witness",
            "scroll": relabel.get("scroll") or "4Q98b",
            "shadow_verse_anchor": relabel.get("shadow_verse_anchor"),
            "bench_label": relabel.get("cross_ref_bench_label"),
        },
        "commander_verified_rows": sm.get("commander_verified_rows"),
        "canon_31k_clean": (p7.get("checks") or {}).get("canon_31k_clean", {}).get("passed"),
        "cross_ref_entry_12_13_applied": not apply_log.get("dry_run") and len(apply_log.get("applied") or []) == 2,
        "verified_anchor_achieved": va_pkt.get("verified_anchor_achieved") is True,
        "human_gates_completed": gate.get("human_gates_completed") or [],
        "future_research_open": gate.get("future_research_open") or [],
        "pilot_verses": [v.get("verse_id") for v in audit.get("verses") or []],
        "reproduce": "py scripts/run_logos_bible_rail_p9_closure_chain_v1.py",
    }


def _md(doc: dict[str, Any]) -> str:
    e13 = doc.get("entry_13") or {}
    lines = [
        "# Bible/Logos Track B — 레일 완료 보고 (P9)",
        "",
        f"- 생성: {doc.get('generated_at_utc')}",
        f"- 상태: **{doc.get('bible_rail_status')}** · completion gate: **{doc.get('completion_gate_ok')}**",
        f"- SEND: **{doc.get('send_gate')}** · non_gating · research_only",
        "",
        "## 닫힌 단계",
        "",
        "- P5–P8 · **P9** CROSS_REF apply · verified_anchor 갭 문서화 · Turnstile 완료 · JSONL 스킵",
        "",
        "## ENTRY_12 / ENTRY_13",
        "",
        f"- ENTRY_12: {doc.get('entry_12')}",
        f"- ENTRY_13: {e13.get('status')} · {e13.get('scroll')} · shadow **{e13.get('shadow_verse_anchor')}** (bench {e13.get('bench_label')})",
        f"- commander verified rows: **{doc.get('commander_verified_rows')}**",
        f"- CROSS_REF ENTRY_12/13 applied: **{doc.get('cross_ref_entry_12_13_applied')}**",
        "",
        "## 격벽 (유지)",
        "",
        "- canon 31k/41k 미합입 · auto_verified=0 · SEND HOLD",
        "- verified_anchor(Ps.5.2 v.2 직접 행) **미달성** — 갭 패킷으로 종료",
        "",
        "## 인간 게이트 (처리 완료)",
        "",
    ]
    for item in doc.get("human_gates_completed") or []:
        lines.append(f"- {item.get('id')}: **{item.get('status')}**")
    lines.append("")
    lines.append("## 향후 연구 (선택)")
    lines.append("")
    for item in doc.get("future_research_open") or []:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## 재현",
            "",
            "```powershell",
            "py scripts/run_logos_bible_rail_p9_closure_chain_v1.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "bible_rail_status": doc.get("bible_rail_status")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
