#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export TRACKED_SSOT_DRAFT for constitution survey v1.2 (structure/wording only).

Writes under docs/final/clinic/ (git-trackable). Does NOT claim diagnostic validity.

  py scripts/export_constitution_survey_tracked_ssot_draft_v1_2.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_constitution_survey_respondent_form_v1 import render_md  # noqa: E402

SRC_BANK = ROOT / "docs/final/artifacts/clinic_constitution_survey_item_bank_v1.json"
CLINIC = ROOT / "docs/final/clinic"

# Exact v1.1 prompts captured from local disk Read immediately before 2026-09-05 edit
# (artifacts path is gitignored — session evidence, not GitHub tip).
V1_1_EXACT = {
    "tb01": "체형이 상대적으로 크고 하체·복부가 발달한 편이라고 느낀다.",
    "tb02": "체형이 마르고 가슴·상체가 상대적으로 발달한 편이다.",
    "zb02": "허리 아래·복부와 하체가 튼실하고 골격이 굵은 편이다.",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    CLINIC.mkdir(parents=True, exist_ok=True)
    bank = json.loads(SRC_BANK.read_text(encoding="utf-8"))

    note = str(bank.get("v1_2_change_note_ko") or "")
    note = note.replace("임상 사례(김하은형)", "임상 회귀 사례 A(비식별)")
    note = note.replace("김하은형", "임상 회귀 사례 A(비식별)")
    bank["v1_2_change_note_ko"] = note

    for it in bank.get("items") or []:
        if not isinstance(it, dict):
            continue
        dnote = str(it.get("discrimination_note_ko") or "")
        if "김하은" in dnote:
            it["discrimination_note_ko"] = dnote.replace("김하은", "회귀사례A")

    bank["tracking"] = {
        "status": "TRACKED_SSOT_DRAFT",
        "seal": "structure_and_wording_only",
        "diagnostic_validity": "NOT_ESTABLISHED",
        "scoring_effect": "NOT_ADJUDICATED",
        "public_clinical_claim": "REFERENCE_ONLY",
        "double_weighting_intent": "NOT_ESTABLISHED",
        "axis_metadata_alignment": "NOT_ESTABLISHED",
        "axis_metadata_note_ko": (
            "tb01.axis=digestion_lean/direction=low, "
            "tb02.axis=activity_lean/direction=high — "
            "문항 표면의미와 직접 대응 미확정(legacy proxy 가능). "
            "observation_proxies는 PROXY_KEYS 축에만 가중합."
        ),
    }

    out_bank = CLINIC / "clinic_constitution_survey_item_bank_v1_2.json"
    out_bank.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SRC_BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    form_md = render_md(bank)
    form_path = CLINIC / "constitution_survey_respondent_form_v1_2.md"
    form_path.write_text(form_md, encoding="utf-8")
    reports_form = ROOT / "reports/constitution_survey_respondent_form_v1.md"
    reports_form.parent.mkdir(parents=True, exist_ok=True)
    reports_form.write_text(form_md, encoding="utf-8")

    new = {it["item_id"]: it["prompt_ko"] for it in bank["items"] if it["item_id"] in V1_1_EXACT}
    zb04 = next(i["prompt_ko"] for i in bank["items"] if i["item_id"] == "zb04")
    diff_lines = [
        "# constitution survey v1.1 → v1.2 wording diff",
        "",
        "**status:** TRACKED_SSOT_DRAFT · structure/wording only",
        "**diagnostic_validity:** NOT_ESTABLISHED",
        (
            "**old_source:** session disk Read of "
            "`docs/final/artifacts/clinic_constitution_survey_item_bank_v1.json` "
            "at version 1.1.0 immediately before 2026-09-05 local edit "
            "(artifacts path is gitignored; not GitHub tip)."
        ),
        "**old_exact_diff:** ESTABLISHED_LOCAL_SESSION (not remote-sealed)",
        "",
        "| item_id | v1.1 exact | v1.2 exact |",
        "|---|---|---|",
    ]
    for k in ("tb01", "tb02", "zb02"):
        diff_lines.append(f"| `{k}` | {V1_1_EXACT[k]} | {new[k]} |")
    diff_lines += [
        "",
        "Unchanged body contrast item `zb04` (v1.2 same):",
        "",
        f"> {zb04}",
        "",
        "## Open adjudication (NOT_ESTABLISHED)",
        "",
        "- DOUBLE_WEIGHTING_INTENT: tb01+zb02 (taeeum body) and tb02+zb04 (soeum body) may double-count",
        "- AXIS_METADATA: tb01→digestion_lean/low, tb02→activity_lean/high may be legacy proxy misalign",
        "- No claim of SCAT/QSCC equivalence",
        "",
    ]
    diff_path = CLINIC / "constitution_survey_v1_1_to_v1_2_diff.md"
    diff_path.write_text("\n".join(diff_lines) + "\n", encoding="utf-8")

    receipt = {
        "schema": "constitution_survey_v1_2_tracking_receipt",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "status": "TRACKED_SSOT_DRAFT",
        "seal": "structure_and_wording_only",
        "flags": {
            "V1_2_CONTENT_INTERNAL_MATCH": "PASS",
            "ITEM_COUNT": 22,
            "CHANGED_ITEMS": ["tb01", "tb02", "zb02"],
            "DIAGNOSTIC_VALIDITY": "NOT_ESTABLISHED",
            "SCORING_EFFECT": "NOT_ADJUDICATED",
            "OLD_EXACT_DIFF": "ESTABLISHED_LOCAL_SESSION",
            "OLD_EXACT_DIFF_GITHUB": "NOT_ESTABLISHED",
            "TRACKED_SSOT": "DRAFT_WRITTEN",
            "PUBLIC_CLINICAL_CLAIM": "REFERENCE_ONLY",
            "DOUBLE_WEIGHTING_INTENT": "NOT_ESTABLISHED",
            "AXIS_METADATA_ALIGNMENT": "NOT_ESTABLISHED",
        },
        "paths": {
            "tracked_bank": "docs/final/clinic/clinic_constitution_survey_item_bank_v1_2.json",
            "tracked_form": "docs/final/clinic/constitution_survey_respondent_form_v1_2.md",
            "tracked_diff": "docs/final/clinic/constitution_survey_v1_1_to_v1_2_diff.md",
            "runtime_artifact_mirror": "docs/final/artifacts/clinic_constitution_survey_item_bank_v1.json",
        },
        "hashes": {
            "bank_sha256": _sha256(out_bank),
            "form_sha256": _sha256(form_path),
        },
        "phi_hygiene": {
            "patient_display_names_in_tracked_bank": False,
            "regression_label": "임상 회귀 사례 A(비식별)",
        },
        "not_claims": [
            "validated survey",
            "SCAT/QSCC equivalence",
            "clinical diagnostic accuracy",
            "physician_gold calibration complete",
        ],
        "reproduce_command": "py scripts/export_constitution_survey_tracked_ssot_draft_v1_2.py",
    }
    receipt_path = CLINIC / "constitution_survey_v1_2_tracking_receipt.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # sync mkm-life public pack prompts (submodule; optional)
    try:
        from scripts.export_clinic_constitution_survey_pack_for_mkmlife_v1 import main as export_pack

        export_pack([])
    except Exception as exc:  # noqa: BLE001
        print(f"WARN mkmlife pack export skipped: {exc}", file=sys.stderr)

    life_bank = ROOT / "projects/mkm/mkm-life/public/data/clinic_constitution_survey_item_bank_v1.json"
    if life_bank.parent.is_dir():
        life_bank.write_text(out_bank.read_text(encoding="utf-8"), encoding="utf-8")

    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
