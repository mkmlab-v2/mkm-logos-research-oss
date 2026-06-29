#!/usr/bin/env python3
"""PersonaDiary commercial readiness gate — local pytest + dev smoke + copy contract."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/personadiary_commercial_readiness_v1_latest.json"
REPORT_OUT = ROOT / "reports/personadiary_commercial_readiness_latest.json"
NO1KMEDI = ROOT / "projects/no1kmedi"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path | None = None) -> dict:
    proc = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    return {
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1200:],
        "stderr_tail": (proc.stderr or "")[-1200:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3010")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args()

    steps: list[dict] = []

    steps.append(
        {
            "id": "pytest_personadiary_suite",
            **_run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/test_personadiary_acode_persona_v1.py",
                    "tests/test_personadiary_acode_profile_v1.py",
                    "tests/test_personadiary_acode_survey_boost_v1.py",
                    "tests/test_personadiary_consumer_profile_bridge_v1.py",
                    "tests/test_personadiary_moment_route_v1.py",
                    "tests/test_personadiary_consumer_copy_v1.py",
                    "tests/test_personadiary_moment_nation_v1.py",
                    "tests/test_personadiary_hyper_local_poi_v1.py",
                    "tests/test_personadiary_persona_visual_card_v1.py",
                    "tests/test_personadiary_design_kernel_v1.py",
                    "tests/test_personadiary_moment_bundle_v1.py",
                    "tests/test_personadiary_live_dev_v1.py",
                    "tests/test_personadiary_commercial_readiness_v1.py",
                    "-q",
                ]
            ),
        }
    )

    if not args.skip_smoke:
        steps.append(
            {
                "id": "local_dev_smoke",
                **_run(
                    ["node", "scripts/smoke-personadiary-dev.mjs", args.base_url],
                    cwd=NO1KMEDI,
                ),
            }
        )
        steps.append(
            {
                "id": "live_commercial_ssr",
                **_run(
                    ["node", "scripts/verify-personadiary-live-commercial.mjs", args.base_url],
                    cwd=NO1KMEDI,
                ),
            }
        )

    steps.append(
        {
            "id": "copy_contract_pytest",
            **_run([sys.executable, "-m", "pytest", "tests/test_personadiary_consumer_copy_v1.py", "-q"]),
        }
    )

    required_files = [
        NO1KMEDI / "src/lib/personadiaryMomentQuotaV1.ts",
        NO1KMEDI / "src/components/personadiary/PersonadiaryPlusTeaser.tsx",
        NO1KMEDI / "public/data/personadiary_hyper_local_poi_catalog_v1.json",
        ROOT / "docs/final/artifacts/personadiary_hyper_local_poi_catalog_v1_latest.json",
    ]
    files_ok = all(p.is_file() for p in required_files)
    steps.append(
        {
            "id": "commercial_artifact_files",
            "ok": files_ok,
            "exit_code": 0 if files_ok else 1,
            "command": ["check", *[str(p.relative_to(ROOT)) for p in required_files]],
            "stdout_tail": "",
            "stderr_tail": "" if files_ok else "missing commercial artifact file(s)",
        }
    )

    page = NO1KMEDI / "src/app/personadiary/page.tsx"
    page_ok = "loadDailyGuidePackage" in page.read_text(encoding="utf-8")
    steps.append(
        {
            "id": "ssr_initial_package",
            "ok": page_ok,
            "exit_code": 0 if page_ok else 1,
            "command": ["check", str(page.relative_to(ROOT))],
            "stdout_tail": "",
            "stderr_tail": "" if page_ok else "missing SSR daily package load",
        }
    )

    release_ok = all(s.get("ok") for s in steps)
    doc = {
        "schema": "personadiary_commercial_readiness_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "phase": "preview_only",
        "send_gate": "HOLD",
        "payment_status": "deferred",
        "commercial_tier": "free_preview_plus_teaser",
        "release_ok": release_ok,
        "verdict_ko": (
            "상용 프리뷰 준비 완료 — 결제·서버 PII·Track A 합선 없음"
            if release_ok
            else "미완 — 아래 steps 확인"
        ),
        "steps": steps,
        "hot_reload": {
            "terminal_1": "cd projects/no1kmedi && npm run dev",
            "terminal_2": "npm run dev:personadiary:live",
            "url": f"{args.base_url.rstrip('/')}/personadiary",
        },
        "deploy_chain": "scripts/Invoke-PersonadiaryParallelBundle_v1.ps1 -Deploy",
        "live_smoke": "py scripts/run_personadiary_live_ops_smoke_v1.py",
        "disclaimer_ko": "[preview_only] 상용 UI·게이트 통과 ≠ 결제 오픈 · mkmlife/jema API 합선 없음",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"release_ok": release_ok, "out": str(args.out_json)}, ensure_ascii=False))
    return 0 if release_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
