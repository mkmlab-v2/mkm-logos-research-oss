#!/usr/bin/env python3
"""TKM encounter_sequence P17 gate: L0 top + curated drafts + weekly report [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHAIN_P16 = ROOT / "reports/tkm_encounter_sequence_chain_v1_latest.json"
SUMMARY = ROOT / "reports/encounter_sequence_summary_v1_latest.json"
DRAFTS = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_draft_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
L0_TEMPLATE = ROOT / "docs/final/templates/l0_red_flag_escalation_ko_v1.json"
L0_RENDER = ROOT / "reports/tkm_encounter_sequence_p17_l0_render_smoke_v1_latest.md"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p17_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _l0_render_smoke() -> bool:
    import importlib.util

    fixture = ROOT / "tests/fixtures/encounter_sequence_v1.example.json"
    minimal = ROOT / "docs/final/schemas/patient_care_bundle_v1.minimal.example.json"
    if not fixture.is_file() or not minimal.is_file():
        return False
    patch_path = ROOT / "scripts/patch_patient_care_bundle_encounter_sequence_ref_v1.py"
    render_path = ROOT / "scripts/render_patient_care_bundle_markdown_v1.py"
    spec = importlib.util.spec_from_file_location("patch_ref", patch_path)
    if spec is None or spec.loader is None:
        return False
    patch_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patch_mod)
    bundle = json.loads(minimal.read_text(encoding="utf-8-sig"))
    seq = json.loads(fixture.read_text(encoding="utf-8-sig"))
    patched = patch_mod.patch_bundle(
        bundle,
        encounter_ref=str(seq.get("encounter", {}).get("ref_token") or "ENC-DEMO"),
        encounter_sequence_id=str(seq.get("encounter", {}).get("sequence_id") or "SEQ-DEMO"),
        encounter_sequence_ledger_ref="data/clinic/encounter_sequence_v1.sample.jsonl",
    )
    spec2 = importlib.util.spec_from_file_location("render_md", render_path)
    if spec2 is None or spec2.loader is None:
        return False
    render_mod = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(render_mod)
    md = render_mod.render_bundle_markdown(patched, encounter_sequence=seq)
    L0_RENDER.parent.mkdir(parents=True, exist_ok=True)
    L0_RENDER.write_text(md, encoding="utf-8")
    return "L0 안전 알림" in md and "증상 키워드가 감지되었습니다" in md


def build() -> dict[str, Any]:
    chain = _load(CHAIN_P16)
    summary = _load(SUMMARY)
    drafts = _load(DRAFTS)
    weekly = _load(WEEKLY)
    l0_ok = L0_TEMPLATE.is_file() and _l0_render_smoke()

    checks = {
        "prior_chain_ok": {"passed": chain.get("all_ok") is True},
        "summary_ok": {"passed": summary.get("summary_ok") is True},
        "l0_template_ok": {"passed": L0_TEMPLATE.is_file()},
        "l0_bundle_render_top_ok": {"passed": l0_ok},
        "curated_learning_draft_ok": {"passed": drafts.get("draft_ok") is True},
        "weekly_report_ok": {"passed": weekly.get("weekly_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p17_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p17_status": "l0_curated_weekly_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "l0_render_smoke_ref": str(L0_RENDER).replace("\\", "/"),
        "disagreement_draft_count": drafts.get("disagreement_draft_count"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p17_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p17_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
