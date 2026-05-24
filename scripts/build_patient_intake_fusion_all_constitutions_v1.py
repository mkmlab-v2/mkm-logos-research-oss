#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build patient intake fusion bundles for all four clinical fixtures (B-track smoke)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = [
    ("soeum_in", "tests/fixtures/patient_intake_soeum_clinical_v1.example.json"),
    ("taeeum_in", "tests/fixtures/patient_intake_taeeum_clinical_v1.example.json"),
    ("soyang_in", "tests/fixtures/patient_intake_soyang_clinical_v1.example.json"),
    ("taeyang_in", "tests/fixtures/patient_intake_taeyang_clinical_v1.example.json"),
]
OUT_SUMMARY = ROOT / "reports" / "patient_intake_fusion_four_constitution_smoke_latest.json"
BUILD_LENS = ROOT / "scripts" / "build_sasang_boming_jiju_clinical_lens_pack_v1.py"
BUILD_INTAKE = ROOT / "scripts" / "build_patient_intake_fusion_draft_v1.py"


def main() -> int:
    subprocess.run([sys.executable, str(BUILD_LENS)], cwd=str(ROOT), check=True)
    rows: list[dict] = []
    for cid, rel in FIXTURES:
        fixture = ROOT / rel
        bundle = ROOT / "reports" / f"patient_intake_fusion_bundle_{cid}_latest.json"
        mye = ROOT / "reports" / f"patient_intake_fusion_myeongni_{cid}_latest.json"
        rat = ROOT / "reports" / f"patient_intake_fusion_rationale_{cid}_latest.json"
        cp = subprocess.run(
            [
                sys.executable,
                str(BUILD_INTAKE),
                "--intake-json",
                str(fixture),
                "--bundle-out",
                str(bundle),
                "--myeongni-out",
                str(mye),
                "--rationale-out",
                str(rat),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        ok = cp.returncode == 0
        row: dict = {"constitution_id": cid, "fixture": rel, "ok": ok}
        if not ok:
            row["stderr"] = (cp.stderr or cp.stdout)[-2000:]
            rows.append(row)
            continue
        rat_doc = json.loads(rat.read_text(encoding="utf-8-sig"))
        cc = rat_doc.get("cross_checks_v1") or {}
        row.update(
            {
                "clinical_label": (rat_doc.get("inputs_echo") or {})
                .get("intake", {})
                .get("sasang_estimate", {})
                .get("label"),
                "myeongni_sasang_status": cc.get("myeongni_sasang_clinical_v1", {}).get("status"),
                "boming_deep_links": cc.get("sasang_boming_jiju_lens_v1", {}).get("deep_link_count"),
                "bundle_out": str(bundle.relative_to(ROOT)).replace("\\", "/"),
            }
        )
        rows.append(row)

    summary = {
        "schema": "patient_intake_fusion_four_constitution_smoke_v1",
        "hypothesis_tag": "[HYPO]",
        "all_ok": all(r.get("ok") for r in rows),
        "rows": rows,
    }
    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": summary["all_ok"], "out": str(OUT_SUMMARY), "count": len(rows)}, ensure_ascii=False))
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
