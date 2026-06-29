#!/usr/bin/env python3
"""Phase 11-E chain: DeepNSM shadow explication → lexicon-aware crosswalk audit → GATE_SPEC refresh [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11e_nsm_crosswalk_repair_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, optional: bool = False) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    ok = proc.returncode == 0
    row = {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": ok,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }
    if not ok and not optional:
        raise SystemExit(f"{label} failed rc={proc.returncode}\n{row['tail']}")
    return row


def _read_chain_summary(path: Path) -> dict:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        "ok": doc.get("ok"),
        "raw": doc.get("raw_baseline_summary") or {},
        "shadow": doc.get("shadow_remapped_summary") or {},
        "delta": doc.get("delta_shadow_minus_raw") or {},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    steps.append(
        _run(
            "deepnsm_shadow_distortion_chain",
            [PY, "scripts/run_deepnsm_shadow_distortion_chain_v1.py"],
        )
    )
    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))
    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_deepnsm_shadow",
                [PY, "-m", "pytest", "tests/test_deepnsm_shadow_explication_v1.py", "-q", "--tb=short"],
                optional=True,
            )
        )

    chain_summary = _read_chain_summary(ROOT / "reports/deepnsm_shadow_distortion_chain_v1_latest.json")
    gate_eval = ROOT / "reports/universal_root_gate_eval_v1_latest.json"
    gate_doc = json.loads(gate_eval.read_text(encoding="utf-8-sig")) if gate_eval.is_file() else {}

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_graphrag_phase11e_nsm_crosswalk_repair_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "shadow_distortion_chain_ok": chain_summary.get("ok"),
        "raw_distortion_rate": (chain_summary.get("raw") or {}).get("english_only_distortion_rate"),
        "shadow_distortion_rate": (chain_summary.get("shadow") or {}).get("english_only_distortion_rate"),
        "distortion_delta_shadow_minus_raw": chain_summary.get("delta"),
        "gate_schema_ok": gate_doc.get("schema_validation_ok"),
        "all_enabled_planes_ok": (gate_doc.get("evaluation") or {}).get("all_enabled_planes_ok"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11e_nsm_crosswalk_repair_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "raw_distortion_rate": report["raw_distortion_rate"],
                "shadow_distortion_rate": report["shadow_distortion_rate"],
                "gate_schema_ok": report["gate_schema_ok"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
