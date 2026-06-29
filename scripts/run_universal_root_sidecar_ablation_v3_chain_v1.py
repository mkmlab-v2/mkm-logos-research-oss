#!/usr/bin/env python3
"""Universal Root sidecar ablation v3: retrieve (gold sidecar v2) + distortion (raw vs shadow) [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/universal_root_sidecar_ablation_v3_latest.json"
V2_OUT = ROOT / "reports/logos_subgraph_sidecar_ablation_v2_latest.json"
RAW_AUDIT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_raw_v1_latest.json"
SHADOW_AUDIT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json"
SIDECAR = ROOT / "docs/final/artifacts/deepnsm_shadow_explication_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
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


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _audit_summary(path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    base = doc.get("baseline") or {}
    gates = doc.get("gates") or {}
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/") if path.is_file() else None,
        "audit_mode": doc.get("audit_mode"),
        "prime_hit_rate": base.get("prime_hit_rate"),
        "english_only_distortion_rate": base.get("english_only_distortion_rate"),
        "gate_ok": gates.get("gate_ok"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-v2", action="store_true", help="Skip gold 48 sidecar ablation v2 rerun")
    ap.add_argument("--skip-distortion", action="store_true", help="Skip raw/shadow distortion audits")
    ap.add_argument("--quick-v2", action="store_true", help="Pass --quick to v2 ablation")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_v2:
        v2_cmd = [PY, "scripts/run_logos_subgraph_sidecar_ablation_v2_v1.py"]
        if args.quick_v2:
            v2_cmd.append("--quick")
        steps.append(_run("sidecar_ablation_v2", v2_cmd))

    if not args.skip_distortion:
        steps.append(
            _run(
                "build_shadow_explication",
                [
                    PY,
                    "scripts/run_deepnsm_shadow_explication_chain_v1.py",
                    "--out",
                    str(SIDECAR.relative_to(ROOT)),
                ],
            )
        )
        steps.append(
            _run(
                "distortion_raw_latin",
                [
                    PY,
                    "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py",
                    "--expected-pairs",
                    "500",
                    "--out",
                    str(RAW_AUDIT.relative_to(ROOT)),
                ],
            )
        )
        steps.append(
            _run(
                "distortion_shadow_remapped",
                [
                    PY,
                    "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py",
                    "--expected-pairs",
                    "500",
                    "--explication-sidecar",
                    str(SIDECAR.relative_to(ROOT)),
                    "--out",
                    str(SHADOW_AUDIT.relative_to(ROOT)),
                ],
            )
        )

    v2_doc = _read_json(V2_OUT)
    raw = _audit_summary(RAW_AUDIT)
    shadow = _audit_summary(SHADOW_AUDIT)
    delta = {}
    if raw.get("prime_hit_rate") is not None and shadow.get("prime_hit_rate") is not None:
        delta = {
            "prime_hit_rate_shadow_minus_raw": round(
                float(shadow["prime_hit_rate"]) - float(raw["prime_hit_rate"]), 4
            ),
            "distortion_rate_shadow_minus_raw": round(
                float(shadow["english_only_distortion_rate"])
                - float(raw["english_only_distortion_rate"]),
                4,
            ),
        }

    retrieve_ok = bool(v2_doc.get("no_hit_at_1_regression")) and bool(v2_doc.get("all_ok"))
    distortion_ok = bool(shadow.get("gate_ok")) if not args.skip_distortion else None
    all_ok = all(s.get("ok") for s in steps) and retrieve_ok and (
        distortion_ok is not False if distortion_ok is not None else True
    )

    report = {
        "schema": "universal_root_sidecar_ablation_v3",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "planes": {
            "retrieve_sidecar_v2": {
                "report": str(V2_OUT.relative_to(ROOT)).replace("\\", "/"),
                "config_count": v2_doc.get("config_count"),
                "no_hit_at_1_regression": v2_doc.get("no_hit_at_1_regression"),
                "regression_labels": v2_doc.get("regression_labels"),
                "baseline_hit_at_k_rates": v2_doc.get("baseline_hit_at_k_rates"),
                "ok": retrieve_ok,
            },
            "distortion_raw_latin": raw,
            "distortion_shadow_remapped": shadow,
            "distortion_delta_shadow_minus_raw": delta,
            "distortion_ok": distortion_ok,
        },
        "explication_sidecar": str(SIDECAR.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
        "reproduce": "py scripts/run_universal_root_sidecar_ablation_v3_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "retrieve_ok": retrieve_ok,
                "distortion_ok": distortion_ok,
                "delta": delta,
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
