#!/usr/bin/env python3
"""Build engine myeongni_full_report for physician_gold capture [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "reports/tkm_physician_gold_myeongni_engine_build_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_birth_mod():
    path = ROOT / "scripts/tkm_physician_gold_birth_profile_v1.py"
    spec = importlib.util.spec_from_file_location("tkm_physician_gold_birth_profile_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_for_capture(capture: dict[str, Any], *, out_path: Path | None = None) -> dict[str, Any]:
    birth_mod = _load_birth_mod()
    anchor = birth_mod.resolve_birth_anchor(capture)
    if not anchor:
        return {"ok": False, "reason": "no_birth_anchor"}
    enc = capture.get("encounter") if isinstance(capture.get("encounter"), dict) else {}
    ref = str(enc.get("ref_token") or "ENC-UNKNOWN")
    rel = birth_mod.engine_report_relpath(ref)
    target = out_path or (ROOT / rel)
    target.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_myeongni_full_report_v1.py"),
        "--local",
        str(int(anchor["year"])),
        str(int(anchor["month"])),
        str(int(anchor["day"])),
        str(int(anchor.get("hour", 12))),
        str(int(anchor.get("minute", 0))),
        "0",
        "--iana-tz",
        str(anchor.get("iana_tz") or "Asia/Seoul"),
        "--annual-years",
        "3",
        "--monthly-months-per-year",
        "2",
        "--out-json",
        str(target),
    ]
    if anchor.get("is_male") is True:
        cmd.append("--is-male")

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        return {
            "ok": False,
            "reason": "engine_build_failed",
            "ref_token": ref,
            "stderr": (proc.stderr or proc.stdout or "")[-500:],
        }

    report = json.loads(target.read_text(encoding="utf-8-sig"))
    meta = report.get("meta") if isinstance(report.get("meta"), dict) else {}
    meta.update(
        {
            "research_only": True,
            "stub": False,
            "engine_built": True,
            "lane": "physician_gold_sidecar",
            "birth_anchor_deid": True,
            "ref_token": ref,
        }
    )
    report["meta"] = meta
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "ref_token": ref,
        "report_path": str(target).replace("\\", "/"),
        "calculation_method": (report.get("birth_engine") or {}).get("calculation_method"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture-json", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--report", type=Path, default=OUT)
    args = ap.parse_args()
    capture = json.loads(args.capture_json.read_text(encoding="utf-8-sig"))
    doc = build_for_capture(capture, out_path=args.out_json)
    doc["schema"] = "tkm_physician_gold_myeongni_engine_build_v1"
    doc["generated_at_utc"] = _utc()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "ref_token": doc.get("ref_token")}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
