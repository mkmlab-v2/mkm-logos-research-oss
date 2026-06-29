#!/usr/bin/env python3
"""Aggregate PersonaDiary Lovable-equivalent DoD gates (tier_0 default · credit-aware)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOD_SSOT = ROOT / "docs/final/artifacts/personadiary_lovable_dod_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/personadiary_lovable_dod_bundle_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path | None = None) -> dict:
    proc = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    return {
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-800:],
        "stderr_tail": (proc.stderr or "")[-800:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--include-vision-qa", action="store_true")
    parser.add_argument(
        "--billing",
        choices=("dry-run", "developer", "vertex", "azure"),
        default="dry-run",
    )
    parser.add_argument("--skip-android", action="store_true")
    parser.add_argument("--strict-planned", action="store_true", help="Fail if planned gates missing")
    parser.add_argument("--strict-vision", action="store_true", help="Vision judge fail blocks release_ok")
    args = parser.parse_args()

    dod = json.loads(DOD_SSOT.read_text(encoding="utf-8"))
    steps: list[dict] = []

    steps.append({"id": "G01", **_run([sys.executable, "scripts/run_personadiary_live_ops_smoke_v1.py"])})
    steps.append(
        {
            "id": "G02",
            **_run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "scripts/Invoke-PersonadiaryLiveOpsAuto_v1.ps1",
                    "-SmokeOnly",
                ]
            ),
        }
    )
    steps.append(
        {
            "id": "G03",
            **_run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/test_personadiary_mobile_ops_v1_schema.py",
                    "tests/test_personadiary_hygiene_prefs_hypo_v1_schema.py",
                    "tests/test_personadiary_btrack_export_v1_schema.py",
                    "-q",
                ]
            ),
        }
    )
    steps.append(
        {
            "id": "G04",
            **_run([sys.executable, "-m", "pytest", "tests/test_personadiary_consumer_copy_v1.py", "-q"]),
        }
    )
    steps.append(
        {
            "id": "G05",
            **_run(
                [
                    sys.executable,
                    "scripts/run_personadiary_visual_qa_judge_v1.py",
                    "--mode",
                    "capture-only",
                ]
            ),
        }
    )

    if args.include_vision_qa:
        billing = args.billing if args.billing != "dry-run" else "developer"
        v = _run(
            [
                sys.executable,
                "scripts/run_personadiary_visual_qa_judge_v1.py",
                "--billing",
                billing,
            ]
        )
        if args.strict_vision and not v["ok"]:
            v["ok"] = False
        elif v.get("exit_code") != 0 and not args.strict_vision:
            v["ok"] = True
            v["warn"] = "vision_non_strict"
        steps.append({"id": "G06", **v})
    else:
        steps.append({"id": "G06", "ok": True, "skipped": True, "reason": "include_vision_qa_false"})

    for gate_id, note in (("G07", "lighthouse_pwa"), ("G08", "offline_pwa_scenario")):
        script = ROOT / f"scripts/run_personadiary_{note}_v1.py"
        if script.is_file():
            steps.append({"id": gate_id, **_run([sys.executable, str(script)])})
        else:
            steps.append(
                {
                    "id": gate_id,
                    "ok": not args.strict_planned,
                    "skipped": True,
                    "reason": "planned_not_implemented",
                    "planned_script": str(script.relative_to(ROOT)),
                }
            )

    if shutil.which("semgrep"):
        s = _run(
            [
                "semgrep",
                "scan",
                "--config",
                "auto",
                "projects/no1kmedi/src/components/personadiary",
                "projects/no1kmedi/src/app/personadiary",
                "--json",
            ]
        )
        steps.append({"id": "G09", **s})
    else:
        steps.append({"id": "G09", "ok": True, "skipped": True, "reason": "semgrep_not_installed"})

    if args.skip_android:
        steps.append({"id": "G10", "ok": True, "skipped": True, "reason": "skip_android_flag"})
    else:
        steps.append(
            {
                "id": "G10",
                **_run([sys.executable, "scripts/run_personadiary_android_emulator_smoke_v1.py"]),
            }
        )

    required = [s for s in steps if s["id"] in ("G01", "G02", "G03", "G04", "G05")]
    release_ok = all(s.get("ok") for s in required)
    if args.strict_planned:
        release_ok = release_ok and all(s.get("ok") for s in steps if not s.get("skipped"))

    credit_tier = "tier_0"
    if args.include_vision_qa:
        if args.billing == "vertex":
            credit_tier = "tier_google_vertex"
        elif args.billing == "azure":
            credit_tier = "tier_azure_openai"
        elif args.billing == "developer":
            credit_tier = "tier_google_developer"

    report = {
        "schema": "personadiary_lovable_dod_bundle_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "dod_ssot": str(DOD_SSOT.relative_to(ROOT)),
        "credit_tier": credit_tier,
        "release_ok": release_ok,
        "steps": steps,
        "boundary_ack": "release_ok is preview PWA QA only; not App Store or SEND_GATE.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"release_ok={release_ok}")
    return 0 if release_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
