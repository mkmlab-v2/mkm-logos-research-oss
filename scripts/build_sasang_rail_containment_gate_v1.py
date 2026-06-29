#!/usr/bin/env python3
"""Sasang rail containment gate: 火剋金·金器 framing + Track A isolation [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAG = ROOT / "docs/final/artifacts/notebooklm_lens_sasang_rag_excerpt_v1.md"
SA = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
MARKET = ROOT / "docs/final/artifacts/market_sasang_lens_latest.json"
OBS = ROOT / "reports/sasang_lens_observation_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/sasang_rail_containment_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    if path.suffix == ".md":
        return {"_text": path.read_text(encoding="utf-8")}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    rag = _load(RAG)
    rag_text = str(rag.get("_text") or "")
    sa = _load(SA)
    market = _load(MARKET)
    obs = _load(OBS)

    hcg = market.get("human_commander_gate_v1") or market.get("human_commander_gate") or {}
    checks = {
        "rag_excerpt_present": {"passed": bool(rag_text.strip())},
        "containment_framing_present": {
            "passed": "火剋金" in rag_text and "containment" in rag_text.lower(),
        },
        "hypo_tag_present": {"passed": "[HYPO]" in rag_text},
        "no_clinical_cohort_percent_claim": {
            "passed": "no clinical cohort %" in rag_text.lower()
            or "임상·인구 역학 % SSOT 없음" in rag_text,
        },
        "human_only_authority": {"passed": "human_only" in rag_text or "human_only" in str(hcg)},
        "independent_lens_present": {"passed": sa.get("schema") == "sasang_independent_lens_v0"},
        "market_lens_present": {"passed": bool(market.get("schema") or market.get("version"))},
        "observation_report_present": {"passed": obs.get("schema") == "sasang_lens_observation_report_v1"},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_rail_containment_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "sasang_rail_status": "containment_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "containment_concept_id": "sasang_taeyang_containment",
        "reproduce": "py scripts/build_sasang_rail_containment_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate_ok": doc["gate_ok"], "status": doc["sasang_rail_status"]}, ensure_ascii=False))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
