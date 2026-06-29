#!/usr/bin/env python3
"""D11-3 chain: DeepNSM shadow explication → remapped crosswalk audit → gate refresh [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_SIDECAR = ROOT / "docs/final/artifacts/deepnsm_shadow_explication_v1.jsonl"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"
DEFAULT_OUT = ROOT / "reports/deepnsm_shadow_distortion_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-800:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def _read_audit_summary(path: Path) -> dict:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    base = doc.get("baseline") or {}
    return {
        "audit_mode": doc.get("audit_mode"),
        "prime_hit_rate": base.get("prime_hit_rate"),
        "english_only_distortion_rate": base.get("english_only_distortion_rate"),
        "aligned_original_language_count": base.get("aligned_original_language_count"),
        "gap_count": base.get("gap_count"),
        "gate_ok": (doc.get("gates") or {}).get("gate_ok"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    fixture = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture
    sidecar = args.sidecar if args.sidecar.is_absolute() else ROOT / args.sidecar

    steps: dict[str, dict] = {}
    steps["raw_baseline_audit"] = _run(
        [
            PY,
            "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py",
            "--fixture",
            str(fixture.relative_to(ROOT)),
            "--expected-pairs",
            "500",
            "--out",
            "reports/nsm_41k_lexicon_crosswalk_audit_raw_v1_latest.json",
        ]
    )
    steps["build_shadow_explication"] = _run(
        [
            PY,
            "scripts/run_deepnsm_shadow_explication_chain_v1.py",
            "--fixture",
            str(fixture.relative_to(ROOT)),
            "--out",
            str(sidecar.relative_to(ROOT)),
        ]
    )
    steps["shadow_remapped_audit"] = _run(
        [
            PY,
            "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py",
            "--fixture",
            str(fixture.relative_to(ROOT)),
            "--expected-pairs",
            "500",
            "--explication-sidecar",
            str(sidecar.relative_to(ROOT)),
            "--out",
            "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json",
        ]
    )
    if not args.skip_gate_spec:
        steps["refresh_gate_spec_baseline"] = _run(
            [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]
        )
        steps["check_gate_spec"] = _run([PY, "scripts/check_universal_root_gate_spec_v1.py"])
    if not args.skip_pytest:
        steps["pytest_deepnsm"] = _run(
            [PY, "-m", "pytest", "tests/test_deepnsm_shadow_explication_v1.py", "-q", "--tb=short"]
        )

    ok = all(s["exit_code"] == 0 for s in steps.values())
    raw_summary = _read_audit_summary(ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_raw_v1_latest.json")
    shadow_summary = _read_audit_summary(ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json")
    explication_report = ROOT / "reports/deepnsm_shadow_explication_chain_v1_latest.json"
    explication_summary = {}
    if explication_report.is_file():
        explication_summary = json.loads(explication_report.read_text(encoding="utf-8")).get("summary") or {}

    delta = {}
    if raw_summary and shadow_summary:
        delta = {
            "prime_hit_rate_delta": round(
                (shadow_summary.get("prime_hit_rate") or 0) - (raw_summary.get("prime_hit_rate") or 0),
                4,
            ),
            "distortion_rate_delta": round(
                (shadow_summary.get("english_only_distortion_rate") or 0)
                - (raw_summary.get("english_only_distortion_rate") or 0),
                4,
            ),
        }

    out_doc = {
        "schema": "deepnsm_shadow_distortion_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "ok": ok,
        "steps": steps,
        "raw_baseline_summary": raw_summary,
        "shadow_remapped_summary": shadow_summary,
        "explication_summary": explication_summary,
        "delta_shadow_minus_raw": delta,
        "reproduce": "py scripts/run_deepnsm_shadow_distortion_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "out": str(args.out),
                "raw": raw_summary,
                "shadow": shadow_summary,
                "delta": delta,
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
