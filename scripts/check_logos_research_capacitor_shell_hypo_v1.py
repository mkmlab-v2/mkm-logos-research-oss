#!/usr/bin/env python3
"""Verify Logos Research Capacitor hypo shell vs mobile shell artifact."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/final/artifacts/logos_research_mobile_shell_hypo_v1_latest.json"
SHELL_DIR = ROOT / "projects/no1kmedi/logos-research-native-hypo-v1"
DEFAULT_OUT = ROOT / "reports/logos_research_capacitor_shell_hypo_readiness_latest.json"

REQUIRED = (
    SHELL_DIR / "package.json",
    SHELL_DIR / "capacitor.config.json",
    SHELL_DIR / "www/index.html",
    SHELL_DIR / "README.md",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check-bootstrap", action="store_true")
    args = ap.parse_args()

    errors: list[str] = []
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.is_file()]
    if missing:
        errors.extend([f"missing_file:{m}" for m in missing])

    if not ARTIFACT.is_file():
        errors.append(f"missing_file:{ARTIFACT.relative_to(ROOT)}")
        doc: dict = {}
    else:
        doc = json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))

    cap_cfg_path = SHELL_DIR / "capacitor.config.json"
    cap_cfg = json.loads(cap_cfg_path.read_text(encoding="utf-8")) if cap_cfg_path.is_file() else {}
    expected_url = f"{doc.get('server_url', '').rstrip('/')}{doc.get('start_path', '')}"
    actual_url = str((cap_cfg.get("server") or {}).get("url") or "")
    if doc and expected_url and actual_url != expected_url:
        errors.append(f"url_mismatch:expected={expected_url} actual={actual_url}")
    if doc and cap_cfg.get("appId") != doc.get("app_id"):
        errors.append("app_id_mismatch")

    node_modules_ok = (SHELL_DIR / "node_modules").is_dir()
    android_ok = (SHELL_DIR / "android").is_dir()
    if args.check_bootstrap:
        if not node_modules_ok:
            errors.append("bootstrap_missing:node_modules")
        if not android_ok:
            errors.append("bootstrap_missing:android")

    ok = not errors
    report = {
        "schema": "logos_research_capacitor_shell_hypo_readiness_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "ok": ok,
        "errors": errors,
        "capacitor_server_url": actual_url,
        "artifact_server_url": expected_url,
        "node_modules_ok": node_modules_ok,
        "android_ok": android_ok,
        "reproduce": "py scripts/check_logos_research_capacitor_shell_hypo_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
