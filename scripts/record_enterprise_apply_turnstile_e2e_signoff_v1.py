#!/usr/bin/env python3
"""Record commander Tier-3 Turnstile E2E attestation (hg-02 closure)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "reports/enterprise_apply_live_smoke_v1_latest.json"
CHECKLIST = ROOT / "reports/enterprise_apply_turnstile_e2e_checklist_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/enterprise_apply_turnstile_e2e_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(*, attestation: str) -> dict[str, Any]:
    smoke = _load(SMOKE)
    checklist = _load(CHECKLIST)
    return {
        "schema": "enterprise_apply_turnstile_e2e_signoff_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "web_ops_tier3_human",
        "human_gate": "captcha_turnstile_tier3",
        "hg_id": "hg-02",
        "apply_url": checklist.get("apply_url") or "https://app.jema-ai.com/enterprise/apply",
        "commander_attestation": attestation,
        "submit_confirmed": True,
        "agent_browser_used": False,
        "api_smoke_post_submit": {
            "all_ok": smoke.get("all_ok"),
            "decision": smoke.get("decision"),
            "generated_at_utc": smoke.get("generated_at_utc"),
        },
        "checklist_ref": str(CHECKLIST.relative_to(ROOT)),
        "gate_ok": smoke.get("all_ok") is True and bool(attestation.strip()),
        "note": "Tier-3 human submit; no Turnstile bypass by agent",
        "reproduce": "py scripts/record_enterprise_apply_turnstile_e2e_signoff_v1.py --attestation \"<one line>\"",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attestation", required=True, help="Commander one-line submit confirmation")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build(attestation=args.attestation.strip())
    if not doc["api_smoke_post_submit"].get("all_ok"):
        print(json.dumps({"ok": False, "reason": "api_smoke_fail"}, ensure_ascii=False))
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate_ok": doc["gate_ok"]}, ensure_ascii=False))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
