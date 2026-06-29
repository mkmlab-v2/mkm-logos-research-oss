#!/usr/bin/env python3
"""Free auditable cinematic proof bundle — economy + hybrid donor reuse, no Veo API."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "auditable_cinematic_free_bundle_v1_latest.json"
POC = ROOT / "scripts" / "cinematic" / "run_auditable_cinematic_poc_v1.py"
MANIFEST = ROOT / "scripts" / "cinematic" / "build_cinematic_injection_manifest_v1.py"
RUBRIC = ROOT / "scripts" / "cinematic" / "check_cinematic_hero_rubric_v1.py"
BRIEF = ROOT / "scripts" / "cinematic" / "build_cinematic_kocca_partner_brief_v1.py"
AUDIO_MIX = ROOT / "scripts" / "cinematic" / "run_auditable_cinematic_audio_mix_v1.py"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_py(script: Path, args: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, str(script), *args]
    p = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    tail = ""
    for stream in (p.stdout, p.stderr):
        if stream:
            tail = stream.strip().splitlines()[-1] if stream.strip() else tail
    return {
        "cmd": " ".join(cmd),
        "exit_code": p.returncode,
        "summary_tail": tail,
        "stdout_tail": (p.stdout or "")[-1500:],
        "stderr_tail": (p.stderr or "")[-1500:],
    }


def load_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-hybrid", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    economy = run_py(POC, ["--variant", "economy"])
    steps.append({"name": "economy", **economy})

    hybrid: dict[str, Any] | None = None
    if not args.skip_hybrid:
        hybrid = run_py(POC, ["--variant", "hybrid"])
        steps.append({"name": "hybrid", **hybrid})

    manifest_step = run_py(
        MANIFEST,
        [
            "--economy-report",
            str(ART / "auditable_cinematic_poc_economy_latest.json"),
            "--hybrid-report",
            str(ART / "auditable_cinematic_poc_hybrid_latest.json"),
        ],
    )
    steps.append({"name": "injection_manifest", **manifest_step})

    rubric_step = run_py(
        RUBRIC,
        [
            "--economy-report",
            str(ART / "auditable_cinematic_poc_economy_latest.json"),
            "--hybrid-report",
            str(ART / "auditable_cinematic_poc_hybrid_latest.json"),
        ],
    )
    steps.append({"name": "hero_rubric", **rubric_step})

    brief_step = run_py(BRIEF, [])
    steps.append({"name": "kocca_partner_brief", **brief_step})

    audio_args = ["--variant", "all"]
    if "--pro-audio" in sys.argv:
        audio_args.append("--pro-audio")
    audio_step = run_py(AUDIO_MIX, audio_args)
    steps.append({"name": "audio_mix", **audio_step})

    economy_doc = load_report(ART / "auditable_cinematic_poc_economy_latest.json")
    hybrid_doc = load_report(ART / "auditable_cinematic_poc_hybrid_latest.json")
    ok = all(s.get("exit_code", 1) == 0 for s in steps) and bool(economy_doc.get("ok"))

    bundle: dict[str, Any] = {
        "schema": "auditable_cinematic_free_bundle_v1",
        "generated_at_utc": now_utc(),
        "ok": ok,
        "cost_usd": 0,
        "veo_api_called": False,
        "variants": {
            "economy": {
                "ok": economy_doc.get("ok"),
                "scenario_aligned": economy_doc.get("scenario_aligned"),
                "master_mp4": (economy_doc.get("outputs") or {}).get("master_mp4"),
                "report_json": str(ART / "auditable_cinematic_poc_economy_latest.json"),
            },
            "hybrid": {
                "ok": hybrid_doc.get("ok") if hybrid_doc else None,
                "scenario_aligned": hybrid_doc.get("scenario_aligned"),
                "master_mp4": (hybrid_doc.get("outputs") or {}).get("master_mp4"),
                "report_json": str(ART / "auditable_cinematic_poc_hybrid_latest.json"),
                "skipped": args.skip_hybrid,
            },
        },
        "manifest_json": str(ART / "cinematic_injection_manifest_v1_latest.json"),
        "rubric_json": str(ART / "cinematic_hero_rubric_check_v1_latest.json"),
        "kocca_brief_json": str(ART / "cinematic_kocca_partner_brief_v1_latest.json"),
        "kocca_brief_md": str(ART / "cinematic_kocca_partner_brief_v1_latest.md"),
        "audio_mix_json": str(ART / "auditable_cinematic_audio_mix_v1_latest.json"),
        "readme_md": str(ART / "cinematic_auditable_poc_proof_readme_v1.md"),
        "steps": steps,
        "reproduce_cmd": "py scripts/cinematic/run_auditable_cinematic_free_bundle_v1.py",
        "send_gate": "HOLD",
        "promotion": "infra_only",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "bundle_json": str(args.out_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
