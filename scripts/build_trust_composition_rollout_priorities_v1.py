#!/usr/bin/env python3
"""Build Trust Composition rollout priority queue (design surfaces).

Writes reports/trust_composition_rollout_priorities_v1_latest.json
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
OUT = ROOT / "reports/trust_composition_rollout_priorities_v1_latest.json"
CLINIC_GATE = ROOT / "reports/clinic_km_mmp_landing_gate_v1_latest.json"
PUBLIC_COPY = ROOT / "projects/no1kmedi/marketing-site/public-copy.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_gate(script_rel: str) -> tuple[bool, int]:
    script = ROOT / script_rel.replace("/", "\\")
    if not script.is_file():
        return False, 127
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0, proc.returncode


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _hub_has_trust_wedge() -> bool:
    doc = _read_json(PUBLIC_COPY)
    if not doc:
        return False
    for loc in ("ko", "en"):
        block = (doc.get("hub_discover") or {}).get(loc) or {}
        wedge = str(block.get("trust_wedge") or "").strip()
        if len(wedge) < 8:
            return False
    return True


def _clinician_footer_has_trust_line() -> bool:
    path = ROOT / "projects/no1kmedi/src/components/ClinicianPilotDisclaimerFooter.tsx"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return "artifact" in text and "게이트" in text


def _personadiary_trust_wedge_present() -> bool:
    path = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryOpsHome.tsx"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return 'data-trust-wedge="trust_composition_v1"' in text and "artifact" in text


def _mkmlife_trust_wedge_present() -> bool:
    vocab = ROOT / "projects/mkm/mkm-life/lib/mkmlife-consumer-vocabulary-v1.ts"
    experience = ROOT / "projects/mkm/mkm-life/components/magic-orb/MagicOrbExperience.tsx"
    if not vocab.is_file() or not experience.is_file():
        return False
    vocab_text = vocab.read_text(encoding="utf-8")
    exp_text = experience.read_text(encoding="utf-8")
    return "trustWedge" in vocab_text and "magic-orb-trust-wedge" in exp_text


def _magic_orb_design_chain_ok() -> bool:
    chain = _read_json(ROOT / "reports/magic_orb_design_readiness_chain_v1_latest.json")
    return bool(chain and chain.get("ok"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    clinic_gate = _read_json(CLINIC_GATE) or {}
    clinic_ok = clinic_gate.get("decision") == "PASS" and clinic_gate.get("ok") is True

    surfaces: list[dict[str, Any]] = [
        {
            "rank": 1,
            "surface_id": "clinic_loi_landing",
            "label_ko": "Clinic LOI pre-sell 랜딩",
            "roi_score": 95,
            "impact": "high",
            "effort": "done",
            "gate_script": "scripts/check_clinic_km_mmp_landing_gate_v1.py",
            "gate_status": "PASS" if clinic_ok else "GAP",
            "action": "baseline_complete",
            "paths": [
                "reports/clinic_km_mmp_loi_preview_v1.html",
                "reports/clinic_km_mmp_landing_tokens_v2.dtcg.json",
            ],
            "send_gate": "HOLD",
            "lane_status": "frozen_deferred",
        },
        {
            "rank": 2,
            "surface_id": "jema_hub_discover_v3",
            "label_ko": "jema-ai.com /hub discover v3",
            "roi_score": 88,
            "impact": "high",
            "effort": "low",
            "gate_script": "scripts/Invoke-MkmDesignLaneRoutine_v1.ps1",
            "trust_wedge_present": _hub_has_trust_wedge(),
            "action": "trust_wedge_hero_single_cta_focus",
            "paths": [
                "projects/no1kmedi/marketing-site/public-copy.json",
                "projects/no1kmedi/src/components/shell/UniverseCenterAskV2.tsx",
            ],
        },
        {
            "rank": 3,
            "surface_id": "clinician_chat_first",
            "label_ko": "app.jema-ai.com/clinician Chat-First",
            "roi_score": 82,
            "impact": "high",
            "effort": "low",
            "gate_script": "projects/no1kmedi npm run check:design-tokens",
            "trust_footer_present": _clinician_footer_has_trust_line(),
            "action": "trust_footer_artifact_gate_line",
            "paths": [
                "projects/no1kmedi/src/components/ClinicianPilotDisclaimerFooter.tsx",
            ],
        },
        {
            "rank": 4,
            "surface_id": "mkmlife_consumer_portal",
            "label_ko": "mkmlife.com consumer portal",
            "roi_score": 70,
            "impact": "medium",
            "effort": "medium",
            "action": "phase2_magic_orb_commander_visual",
            "paths": ["projects/mkm/mkm-life"],
            "trust_wedge_present": _mkmlife_trust_wedge_present(),
            "design_readiness_chain_ok": _magic_orb_design_chain_ok(),
            "defer": not (_mkmlife_trust_wedge_present() and _magic_orb_design_chain_ok()),
        },
        {
            "rank": 5,
            "surface_id": "personadiary_ops",
            "label_ko": "personadiary.com/ops",
            "roi_score": 62,
            "impact": "medium",
            "effort": "medium",
            "action": "phase2_non_prediction_contract_only",
            "paths": [
                "projects/no1kmedi/src/components/personadiary/PersonadiaryOpsHome.tsx",
            ],
            "trust_wedge_present": _personadiary_trust_wedge_present(),
            "defer": not _personadiary_trust_wedge_present(),
        },
    ]

    top3 = surfaces[:3]
    pending_actions = [
        s["surface_id"]
        for s in top3
        if s.get("action") != "baseline_complete"
        and not s.get("trust_wedge_present")
        and not s.get("trust_footer_present")
    ]

    # Re-evaluate pending after wedge/footer flags
    pending_actions = []
    for s in top3:
        if s["surface_id"] == "clinic_loi_landing":
            if not clinic_ok:
                pending_actions.append(s["surface_id"])
        elif s["surface_id"] == "jema_hub_discover_v3":
            if not s.get("trust_wedge_present"):
                pending_actions.append(s["surface_id"])
        elif s["surface_id"] == "clinician_chat_first":
            if not s.get("trust_footer_present"):
                pending_actions.append(s["surface_id"])

    pending_phase2 = [
        s["surface_id"]
        for s in surfaces
        if s.get("defer")
    ]

    doc = {
        "schema": "trust_composition_rollout_priorities_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ssot": "docs/final/MKM_TRUST_COMPOSITION_DESIGN_PIPELINE_V1.md",
        "policy_ko": "전면 리디자인 금지 — Top3+Phase2 점진 적용 · gate exit 0 = 해당 surface 완료",
        "top3": top3,
        "all_surfaces": surfaces,
        "pending_top3_actions": pending_actions,
        "pending_phase2_actions": pending_phase2,
        "reproduce": "py scripts/build_trust_composition_rollout_priorities_v1.py",
        "phase2_chain": "powershell -File scripts/Run-TrustCompositionRolloutPriorities_v1.ps1 -IncludeMagicOrbChain",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "pending_top3": pending_actions,
                "pending_phase2": pending_phase2,
                "clinic_gate": clinic_gate.get("decision"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
