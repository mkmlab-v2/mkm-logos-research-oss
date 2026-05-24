#!/usr/bin/env python3
"""Human-review packet for Logos RAG B-track promotion tiers (JSON + MD)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports/constitution" / "btrack_pilot"
DEFAULT_GATE = ART / "logos_rag_btrack_promotion_gate_v1_latest.json"
DEFAULT_OUT_JSON = ART / "logos_rag_btrack_promotion_review_packet_v1_latest.json"
DEFAULT_OUT_MD = ART / "logos_rag_btrack_promotion_review_packet_v1_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    gate_path = args.gate_json if args.gate_json.is_absolute() else ROOT / args.gate_json
    if not gate_path.is_file():
        raise SystemExit(f"Missing gate: {gate_path}")

    gate = _load(gate_path)
    tiers = gate.get("tiers") or {}
    metrics = gate.get("metrics") or {}
    l1 = tiers.get("L1_btrack_lab_bundle") or {}
    l2 = tiers.get("L2_track_c_shadow_ingest") or {}

    lines = [
        "# Logos RAG B-track — promotion review packet",
        "",
        f"- Generated (UTC): `{_utc_now()}`",
        f"- Recommended action: **{gate.get('recommended_commander_action')}**",
        "",
        "## Metrics (Fact-Lock)",
        f"- KO mean top1: `{metrics.get('ko_mean_top1')}`",
        f"- Weak gold hit@1 / hit@3 (KO): `{metrics.get('weak_gold_hit_at_1')}` / `{metrics.get('weak_gold_hit_at_3')}`",
        f"- Bridge rag_evidence: `{metrics.get('bridge_rag_evidence_n')}`",
        f"- ST index rows: `{metrics.get('st_index_rows')}`",
        f"- Gold: filled `{ (metrics.get('gold_stats') or {}).get('filled_n') }`, "
        f"auto_top1 `{ (metrics.get('gold_stats') or {}).get('auto_top1_n') }`, "
        f"human_signed `{ (metrics.get('gold_stats') or {}).get('human_signed_n') }`",
        "",
        "## L1 — B-track lab bundle freeze",
        f"- **Passed:** {l1.get('passed')}",
        f"- **Approval ready:** {l1.get('approval_ready')}",
        "",
        "승인 시: `py scripts/record_logos_rag_btrack_promotion_human_approval_v1.py --tier L1`",
        "",
        "## L2 — Track C shadow / premium bridge ingest",
        f"- **Passed:** {l2.get('passed')}",
        f"- **Approval ready:** {l2.get('approval_ready')}",
        "",
        "차단 사유(일반): weak_gold hit@3 미달 또는 gold가 auto top-1 정렬 상태.",
        "",
        "승인 시: `py scripts/record_logos_rag_btrack_promotion_human_approval_v1.py --tier L2`",
        "",
        "## L3 — Production ST index (명시 주문만)",
        "- 스크립트 기본 **차단**. A-contract ANN 교체는 별도 지휘.",
        "",
        "## 격벽",
        "- prophecy_promotion_gates / Track A compression / gematria bridge **미접촉**",
        "",
        f"- Gate SSOT: `{gate_path.relative_to(ROOT).as_posix()}`",
        f"- Adjudication pack: `reports/constitution/btrack_pilot/logos_rag_human_adjudication_pack_latest.json`",
    ]

    packet: dict[str, Any] = {
        "schema": "logos_rag_btrack_promotion_review_packet_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "gate_json": str(gate_path.relative_to(ROOT)),
        "recommended_commander_action": gate.get("recommended_commander_action"),
        "tiers_summary": {
            k: {"passed": (v or {}).get("passed"), "approval_ready": (v or {}).get("approval_ready")}
            for k, v in tiers.items()
        },
        "metrics": metrics,
        "approval_commands": {
            "L1": "py scripts/record_logos_rag_btrack_promotion_human_approval_v1.py --tier L1",
            "L2": "py scripts/record_logos_rag_btrack_promotion_human_approval_v1.py --tier L2",
            "L3": "py scripts/record_logos_rag_btrack_promotion_human_approval_v1.py --tier L3",
        },
        "track_wall": gate.get("track_wall"),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "action": packet["recommended_commander_action"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
