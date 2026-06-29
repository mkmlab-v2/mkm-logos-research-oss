#!/usr/bin/env python3
"""Snapshot harness + verify gates after v5 operational promotion (B-track, no GPU)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
PROMO = ROOT / "reports/myeongri_interpret_v5_operational_adapter_promotion_latest.json"
OUT = ROOT / "reports/myeongri_interpret_v5_operational_post_promotion_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    doc: dict = {
        "schema": "myeongri_interpret_v5_operational_post_promotion_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
    }
    if STATUS.is_file():
        st = json.loads(STATUS.read_text(encoding="utf-8"))
        doc["harness"] = {
            "recommended_operational_adapter": st.get("recommended_operational_adapter"),
            "recommended_operational_eval": st.get("recommended_operational_eval"),
            "recommended_operational_preds_jsonl": st.get("recommended_operational_preds_jsonl"),
            "recommended_operational_diversity_audit": st.get("recommended_operational_diversity_audit"),
            "operational_adapter_promotion_v5": st.get("operational_adapter_promotion_v5"),
        }
    if PROMO.is_file():
        doc["promotion_report"] = json.loads(PROMO.read_text(encoding="utf-8"))

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_myeongri_interpret_v4_guard_bundle_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    verify_out = (proc.stdout or "").strip()
    if verify_out:
        try:
            doc["verify"] = json.loads(verify_out)
        except json.JSONDecodeError:
            doc["verify"] = {"raw_tail": verify_out[-2000:]}
    doc["verify_exit_code"] = proc.returncode
    doc["post_promotion_ok"] = proc.returncode == 0 and (doc.get("verify") or {}).get("ok") is True

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["post_promotion_ok"], "report": str(OUT).replace("\\", "/")}, ensure_ascii=False))
    return 0 if doc["post_promotion_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
