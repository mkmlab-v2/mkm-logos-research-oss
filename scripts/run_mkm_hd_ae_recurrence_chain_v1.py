#!/usr/bin/env python3
"""Run HD AE recurrence numerator chain with profile/defaults.

Chain:
  1) build_mkm_hd_ae_recurrence_observations_v1.py
  2) stamp_mkm_hd_ae_regression_rate_v1.py --observations ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "docs/final/artifacts/mkm_hd_ae_recurrence_profile_v1_latest.json"
OBS_OUT = ROOT / "docs/final/artifacts/mkm_hd_ae_recurrence_observations_v1_latest.json"
STAMP_OUT = ROOT / "docs/final/artifacts/mkm_hd_ae_regression_rate_v1_latest.json"
CHAIN_OUT = ROOT / "docs/final/artifacts/mkm_hd_ae_recurrence_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_profile(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"window_days": 7, "repeat_threshold": 2}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"window_days": 7, "repeat_threshold": 2}


def _run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return p.returncode, p.stdout, p.stderr


def _catalog_stats(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"catalog_rule_count": None, "enforced_count": None, "catalog_sha256": None}
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except json.JSONDecodeError:
        return {"catalog_rule_count": None, "enforced_count": None, "catalog_sha256": sha}
    rows = data.get("named_defects") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return {"catalog_rule_count": None, "enforced_count": None, "catalog_sha256": sha}
    catalog_rule_count = 0
    enforced_count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("id") or "").strip():
            catalog_rule_count += 1
            if str(row.get("enforcement_status") or "") == "enforced":
                enforced_count += 1
    return {
        "catalog_rule_count": catalog_rule_count,
        "enforced_count": enforced_count,
        "catalog_sha256": sha,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", type=Path, default=PROFILE)
    ap.add_argument("--window-days", type=int, default=None)
    ap.add_argument("--repeat-threshold", type=int, default=None)
    ap.add_argument("--out", type=Path, default=CHAIN_OUT)
    args = ap.parse_args()

    prof = _load_profile(args.profile if args.profile.is_absolute() else ROOT / args.profile)
    window_days = int(args.window_days if args.window_days is not None else prof.get("window_days", 7))
    repeat_threshold = int(
        args.repeat_threshold if args.repeat_threshold is not None else prof.get("repeat_threshold", 2)
    )

    build_cmd = [
        sys.executable,
        str(ROOT / "scripts/build_mkm_hd_ae_recurrence_observations_v1.py"),
        "--window-days",
        str(window_days),
        "--repeat-threshold",
        str(repeat_threshold),
    ]
    b_code, b_out, b_err = _run(build_cmd)

    stamp_cmd = [
        sys.executable,
        str(ROOT / "scripts/stamp_mkm_hd_ae_regression_rate_v1.py"),
        "--observations",
        str(OBS_OUT),
    ]
    s_code, s_out, s_err = _run(stamp_cmd)

    ok = b_code == 0 and s_code == 0
    catalog_path = ROOT / "docs/final/artifacts/mkm_hd_ae_named_defect_catalog_v1.json"
    cat = _catalog_stats(catalog_path)

    doc = {
        "schema": "mkm_hd_ae_recurrence_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "pass_claimed": False,
        "profile_path": str((args.profile if args.profile.is_absolute() else ROOT / args.profile).resolve()),
        "window_days": window_days,
        "repeat_threshold": repeat_threshold,
        "denominator_registry_path": "docs/final/artifacts/mkm_hd_ae_named_defect_catalog_v1.json",
        "catalog_rule_count": cat["catalog_rule_count"],
        "enforced_count": cat["enforced_count"],
        "catalog_sha256": cat["catalog_sha256"],
        "status_label": "CHAIN_RUN_LOCAL_ONLY",
        "ci_state": "CI_WIRE_ADDED_UNTRIGGERED",
        "tuning_eval_split": {
            "tuning_data_scope": "profile_static_params_only",
            "evaluation_data_scope": "registry_window_observations",
            "self_referential_tuning": False
        },
        "steps": {
            "build_observations": {"exit_code": b_code, "stdout": b_out.strip(), "stderr": b_err.strip()},
            "stamp_regression": {"exit_code": s_code, "stdout": s_out.strip(), "stderr": s_err.strip()},
        },
        "ok": ok,
        "observations_out": str(OBS_OUT).replace("\\", "/"),
        "stamp_out": str(STAMP_OUT).replace("\\", "/"),
        "reproducible_command": "py scripts/run_mkm_hd_ae_recurrence_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "window_days": window_days,
                "repeat_threshold": repeat_threshold,
                "out": str(args.out).replace("\\", "/"),
                "pass_claimed": False,
                "ci_state": "CI_WIRE_ADDED_UNTRIGGERED",
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
