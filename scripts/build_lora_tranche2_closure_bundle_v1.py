#!/usr/bin/env python3
"""LoRA tranche-2 B-track closure bundle — artifact + signoff gate rollup.

research_only — closure_ok does not authorize Track A, MS, or live trading.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SIGNOFF = ROOT / "reports/lora_tranche2_signoff_pack_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/lora_tranche2_closure_bundle_v1_latest.json"
DEFAULT_ARTIFACTS_OUT = ROOT / "docs/final/artifacts/lora_tranche2_closure_bundle_v1_latest.json"

TRANCHE2_PYTEST = [
    "tests/test_build_lora_tranche2_signoff_pack_v1.py",
    "tests/test_build_lora_tranche2_trackc_copy_v1.py",
    "tests/test_run_lora_tranche2_microtrain_diversity_probe_v1.py",
    "tests/test_run_lora_tranche2_qwen4pack_train_ablation_v1.py",
    "tests/test_apply_lora_tranche2_multipack_human_approval_v1.py",
    "tests/test_build_lora_tranche2_closure_bundle_v1.py",
]

FOLLOW_ON_OPTIONAL = [
    "A-code 12-pack locked_eval expanded grid (100 rows/pack; GPU time; quality not GO)",
    "Track C slide external send after legal sign-off",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_pytest(tests: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, "-m", "pytest", *tests, "-q"]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "") + (cp.stderr or "")
    return cp.returncode, tail[-2000:] if len(tail) > 2000 else tail


def build_bundle(*, signoff_path: Path, skip_pytest: bool) -> dict[str, Any]:
    signoff = _read_json(signoff_path)
    gates = signoff.get("gates", {})
    exists = signoff.get("artifact_exists", {})
    missing = [k for k, ok in exists.items() if ok is not True]

    pytest_rc = 0
    pytest_tail = ""
    if not skip_pytest:
        pytest_rc, pytest_tail = _run_pytest(TRANCHE2_PYTEST)

    checks = {
        "signoff_present": bool(signoff),
        "tranche2_btrack_ready": signoff.get("tranche2_btrack_ready") is True,
        "all_artifacts_exist": len(missing) == 0,
        "multipack_btrack_go": gates.get("allow_deploy_multipack_btrack") is True,
        "hybrid12_diversity_ok": gates.get("hybrid12_diversity_ok") is True,
        "qwen4pack_diversity_ok": gates.get("qwen4pack_diversity_ok") is True,
        "expanded_eval_present": gates.get("expanded_eval_mean_alignment") is not None,
        "pytest_passed": skip_pytest or pytest_rc == 0,
    }

    closure_ok = all(checks.values())

    return {
        "schema": "lora_tranche2_closure_bundle_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "closure_ok": closure_ok,
        "checks": checks,
        "missing_artifacts": missing,
        "pytest_exit_code": None if skip_pytest else pytest_rc,
        "pytest_tail": pytest_tail if pytest_tail else None,
        "signoff_pointer": str(signoff_path.relative_to(ROOT)).replace("\\", "/")
        if signoff_path.is_relative_to(ROOT)
        else str(signoff_path),
        "gates_excerpt": {
            "sweep_best_id": gates.get("sweep_best_id"),
            "hybrid_hit_rate": gates.get("hybrid_hit_rate"),
            "expanded_eval_mean_alignment": gates.get("expanded_eval_mean_alignment"),
            "allow_deploy_multipack_btrack": gates.get("allow_deploy_multipack_btrack"),
        },
        "recommendation_excerpt": signoff.get("recommendation"),
        "acode_mkm12_lane": {
            "router_smoke_ok": gates.get("acode_router_smoke_ok"),
            "acode12pack_diversity_ok": gates.get("acode12pack_diversity_ok"),
            "acode12pack_shard_mode": gates.get("acode12pack_shard_mode"),
            "acode12pack_multi_pack_production_go": gates.get("acode12pack_multi_pack_production_go"),
        },
        "follow_on_optional": FOLLOW_ON_OPTIONAL,
        "summary_ko": (
            "LoRA Tranche 2 B-track 일단락: 모든 필수 아티팩트·게이트·pytest 통과."
            if closure_ok
            else f"LoRA Tranche 2 closure 미충족: {', '.join(k for k, v in checks.items() if not v)}."
        ),
        "disclaimer": (
            "B-track bench 4×40 + commander multipack scope only. "
            "Not Track A·MS·live-trading. alignment_pass_rate is smoke, not quality GO."
        ),
        "reproduction_commands": [
            "py scripts/build_lora_tranche2_signoff_pack_v1.py",
            "py scripts/build_lora_tranche2_closure_bundle_v1.py",
        ],
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build LoRA tranche-2 closure bundle.")
    p.add_argument("--signoff-json", default=str(DEFAULT_SIGNOFF))
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    p.add_argument("--artifacts-json", default=str(DEFAULT_ARTIFACTS_OUT))
    p.add_argument("--skip-pytest", action="store_true")
    p.add_argument("--stdout-only", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    signoff_path = Path(args.signoff_json)
    if not signoff_path.is_absolute():
        signoff_path = ROOT / signoff_path

    bundle = build_bundle(signoff_path=signoff_path, skip_pytest=bool(args.skip_pytest))
    text = json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"

    if args.stdout_only:
        print(text)
        return 0 if bundle["closure_ok"] else 1

    for out in (Path(args.out_json), Path(args.artifacts_json)):
        path = out if out.is_absolute() else ROOT / out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"WROTE: {path}")

    return 0 if bundle["closure_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
