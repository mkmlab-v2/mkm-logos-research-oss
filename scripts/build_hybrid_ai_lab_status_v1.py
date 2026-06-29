#!/usr/bin/env python3
"""Aggregate hybrid + NVIDIA API lane reports into one ops JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/hybrid_ai_lab_status_v1_latest.json"

SNAPSHOTS = [
    ("nvidia_gpu_credit_ops", "reports/nvidia_gpu_credit_ops_status_v1_latest.json"),
    ("nvidia_api_primary", "reports/nvidia_api_primary_lane_v1_latest.json"),
    ("hybrid_chain", "reports/hybrid_local_nim_chain_v1_latest.json"),
    ("hybrid_ab", "reports/hybrid_local_vs_nim_ab_v1_latest.json"),
    ("nim_logos_handoff", "reports/nim_logos_research_handoff_v1_latest.json"),
    ("nim_market_news", "reports/nim_market_news_graphrag_handoff_v1_latest.json"),
    ("de_anchor_probe", "reports/ng40_de_logos_anchor_probe_v1_latest.json"),
    ("de_nim_synthesis", "reports/ng40_de_probe_nim_synthesis_v1_latest.json"),
    ("operator_paste", "reports/nvidia_hybrid_operator_paste_v1_latest.json"),
    ("hybrid_spine", "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_logos_stack_v1_latest.json"),
    ("ngc_env", "reports/ngc_env_check_v1_latest.json"),
]


def _load(rel: str) -> dict | None:
    p = ROOT / rel
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"_error": "invalid_json", "path": rel}


def _ok_flag(doc: dict | None, *keys: str) -> bool | None:
    if not doc:
        return None
    for k in keys:
        if k in doc and isinstance(doc[k], bool):
            return doc[k]
    ch = doc.get("chat")
    if isinstance(ch, dict) and "ok" in ch:
        return bool(ch["ok"])
    inf = doc.get("inference_nim")
    if isinstance(inf, dict) and "ok" in inf:
        return bool(inf["ok"])
    return None


def main() -> int:
    parts: dict[str, dict | None] = {}
    for name, rel in SNAPSHOTS:
        parts[name] = _load(rel)

    summary = {
        "nim_api": _ok_flag(parts.get("nvidia_api_primary"), "ok")
        or _ok_flag(parts.get("nvidia_gpu_credit_ops")),
        "hybrid_chain": _ok_flag(parts.get("hybrid_chain"), "ok"),
        "hybrid_ab": _ok_flag(parts.get("hybrid_ab"), "ok"),
        "logos_handoff": _ok_flag(parts.get("nim_logos_handoff")),
        "market_news_handoff": _ok_flag(parts.get("nim_market_news")),
        "de_probe_present": parts.get("de_anchor_probe") is not None,
        "de_nim_synthesis": _ok_flag(parts.get("de_nim_synthesis"))
        or (parts.get("de_nim_synthesis") is not None),
        "operator_paste": parts.get("operator_paste") is not None,
    }
    doc = {
        "schema": "hybrid_ai_lab_status_v1",
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "b_track_infra",
        "summary": summary,
        "snapshots": {k: (v is not None) for k, v in parts.items()},
        "recommended_next": [
            "reports/nvidia_hybrid_operator_paste_v1_latest.txt — commander review",
            "LUT sign-off: draft_pending_commander_signoff (no codec wire until approved)",
            "Innovation Lab email → Brev train GPU",
        ],
        "artifacts": {name: rel for name, rel in SNAPSHOTS},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    missing = [n for n, v in parts.items() if v is None]
    return 0 if not missing or summary.get("nim_api") else 2


if __name__ == "__main__":
    raise SystemExit(main())
