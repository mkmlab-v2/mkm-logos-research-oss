#!/usr/bin/env python3
"""Phase 11-P: Golden-40 compress observe + Layer C MDL gate enable + GATE_SPEC refresh [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11p_compress_layerc_gate_chain_v1_latest.json"
COMP_ATOM02 = ROOT / "reports/constitution/btrack_pilot/comp_atom02_lexicon_must_keep_analysis_v1.json"


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


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-comp-bench", action="store_true")
    ap.add_argument("--skip-mdl-gate", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_comp_bench:
        steps.append(_run("comp_atom02_golden40", [PY, "scripts/comp_atom02_lexicon_must_keep_analysis_v1.py"]))

    if not args.skip_mdl_gate:
        steps.append(_run("mdl_prune_gate", [PY, "scripts/check_universal_root_mdl_prune_gate_v1.py"]))

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))
        steps.append(
            _run(
                "check_gate_spec_enforce",
                [PY, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"],
            )
        )

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_gate_spec",
                [PY, "-m", "pytest", "tests/test_check_universal_root_gate_spec_v1.py", "-q", "--tb=short"],
                optional=True,
            )
        )

    comp_doc = _read_json(COMP_ATOM02)
    ablation = comp_doc.get("compression_ablation") or comp_doc.get("ablation") or {}
    parity = comp_doc.get("active_report_parity") or {}
    strict = ablation.get("lexicon_on") or {}
    gate_profile = parity if parity.get("global_token_saving_rate") is not None else strict
    saving = gate_profile.get("global_token_saving_rate")
    jaccard = gate_profile.get("avg_reconstruction_fidelity_jaccard")
    compress_would_pass = (
        saving is not None and jaccard is not None and float(saving) >= 0.465 and float(jaccard) >= 0.885
    )

    mdl_gate = _read_json(ROOT / "reports/universal_root_mdl_prune_gate_v1_latest.json")
    gate_eval = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    ev = gate_eval.get("evaluation") or {}
    spec = _read_json(ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json")
    planes = ((spec.get("promotion_gates") or {}).get("planes") or {})
    layer_c_enabled = bool((planes.get("layer_c_mdl") or {}).get("enabled"))
    compress_enabled = bool((planes.get("compress") or {}).get("enabled"))

    core_ok = all(s.get("ok") for s in steps)
    all_ok = core_ok and bool(mdl_gate.get("gate_ok")) and layer_c_enabled

    report = {
        "schema": "logos_graphrag_phase11p_compress_layerc_gate_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        "all_ok": all_ok,
        "compress_observed": {
            "gate_profile": comp_doc.get("gate_compress_profile") or "active_report_parity",
            "parity_saving_pct": round(float(saving) * 100, 4) if saving is not None else None,
            "parity_jaccard": jaccard,
            "strict_lexicon_on_saving_pct": round(float(strict.get("global_token_saving_rate") or 0) * 100, 4),
            "compress_plane_enabled": compress_enabled,
            "compress_plane_would_pass": compress_would_pass,
            "compress_blocker": None
            if compress_would_pass
            else f"parity saving {round(float(saving or 0) * 100, 2)}% < 46.5% threshold",
        },
        "layer_c_mdl": {
            "gate_ok": mdl_gate.get("gate_ok"),
            "plane_enabled_in_spec": layer_c_enabled,
        },
        "gate_eval_summary": {
            "research_ready_decision": ev.get("research_ready_decision"),
            "all_enabled_planes_ok": ev.get("all_enabled_planes_ok"),
            "planes": [
                {"plane": p.get("plane"), "enabled": p.get("enabled"), "ok": p.get("ok")}
                for p in (ev.get("planes") or [])
            ],
        },
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11p_compress_layerc_gate_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "layer_c_enabled": layer_c_enabled,
                "compress_would_pass": compress_would_pass,
                "research_ready_decision": ev.get("research_ready_decision"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
