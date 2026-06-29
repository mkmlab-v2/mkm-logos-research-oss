#!/usr/bin/env python3
"""Verify Han Vocology KM-VHI appendix ↔ JSON ↔ OKF bundle alignment."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUESTIONNAIRE = ROOT / "docs/final/artifacts/km_vhi_questionnaire_v0_1_latest.json"
APPENDIX = ROOT / "docs/research/HAN_VOCOLOGY_APPENDIX_6_KM_VHI_V0_1.md"
OKF_INSTRUMENT = ROOT / "docs/final/artifacts/okf_bundles/han_vocology/instruments/km_vhi_v0_1.md"
OUT = ROOT / "docs/final/artifacts/han_vocology_km_vhi_ssot_alignment_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _item_map(q: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for sec in q.get("sections") or []:
        for item in sec.get("items") or []:
            iid = item.get("id")
            if iid:
                out[str(iid)] = str(item.get("text_ko") or "")
    return out


def main() -> int:
    checks: list[dict[str, Any]] = []

    if not QUESTIONNAIRE.is_file():
        print(json.dumps({"ok": False, "error": "questionnaire_missing"}, ensure_ascii=False))
        return 1

    q = json.loads(QUESTIONNAIRE.read_text(encoding="utf-8"))
    items = _item_map(q)
    checks.append({"name": "questionnaire_item_count_10", "ok": len(items) == 10})

    scoring = q.get("scoring") or {}
    checks.append({"name": "scoring_max_40", "ok": scoring.get("max") == 40})
    checks.append({"name": "scoring_min_0", "ok": scoring.get("min") == 0})
    clinical = str(scoring.get("clinical_use") or "")
    checks.append({"name": "clinical_use_20pct", "ok": "20%" in clinical})

    appendix_text = APPENDIX.read_text(encoding="utf-8") if APPENDIX.is_file() else ""
    okf_text = OKF_INSTRUMENT.read_text(encoding="utf-8") if OKF_INSTRUMENT.is_file() else ""

    for iid, text in items.items():
        checks.append(
            {
                "name": f"appendix_has_{iid}",
                "ok": iid in appendix_text and text[:12] in appendix_text,
            }
        )
        checks.append(
            {
                "name": f"okf_has_{iid}",
                "ok": iid in okf_text and text[:12] in okf_text,
            }
        )

    for row in scoring.get("interpretation") or []:
        label = str(row.get("label_ko") or "")
        checks.append({"name": f"appendix_band_{label}", "ok": label in appendix_text})

    checks.append(
        {
            "name": "appendix_delta_formula",
            "ok": "baseline" in appendix_text
            and re.search(r"baseline.*−.*baseline.*×\s*100", appendix_text) is not None,
        }
    )
    checks.append(
        {
            "name": "appendix_ssot_block",
            "ok": "SSOT 3층 정합" in appendix_text and "okf_bundles/han_vocology" in appendix_text,
        }
    )
    checks.append(
        {
            "name": "okf_resource_points_json",
            "ok": "km_vhi_questionnaire_v0_1_latest.json" in okf_text,
        }
    )

    ok = all(c["ok"] for c in checks)
    report = {
        "schema": "han_vocology_km_vhi_ssot_alignment_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "questionnaire_version": q.get("version"),
        "item_ids": sorted(items.keys()),
        "checks": checks,
        "paths": {
            "questionnaire": str(QUESTIONNAIRE.relative_to(ROOT)).replace("\\", "/"),
            "appendix": str(APPENDIX.relative_to(ROOT)).replace("\\", "/"),
            "okf_instrument": str(OKF_INSTRUMENT.relative_to(ROOT)).replace("\\", "/"),
        },
        "reproducible_command": "py scripts/check_han_vocology_km_vhi_ssot_alignment_v1.py",
        "boundary_ack": "[HYPO] B-track education — not clinical diagnosis · not Track A",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT), "checks_pass": sum(1 for c in checks if c["ok"]), "checks_total": len(checks)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
