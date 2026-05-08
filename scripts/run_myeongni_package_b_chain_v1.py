#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ADV_OUT = ART / "mkm_myeongni_package_b_advanced_input_latest.json"
LENS_OUT = ART / "myeongni_independent_lens_package_b_latest.json"
V2_BAL_OUT = ART / "mkm_myeongni_response_v2_package_b_latest.json"
V2_ATK_OUT = ART / "mkm_myeongni_response_v2_package_b_attack_latest.json"
SUMMARY_OUT = ART / "mkm_myeongni_package_b_chain_summary_latest.json"
PROFILE_POLICY = ART / "mkm_myeongni_profile_switch_policy_v1.json"
PROFILE_REC_OUT = ART / "mkm_myeongni_profile_switch_recommendation_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{cp.stdout}\n{cp.stderr}")


def _decision_margin(doc: dict[str, Any]) -> dict[str, Any]:
    core = doc.get("core_layer") if isinstance(doc.get("core_layer"), dict) else {}
    cal = doc.get("calibration") if isinstance(doc.get("calibration"), dict) else {}
    coord = doc.get("coordinator_layer") if isinstance(doc.get("coordinator_layer"), dict) else {}
    d = float(core.get("direction_core") or 0.0)
    c = float(coord.get("confidence_adjusted") or 0.0)
    rd = float(cal.get("reduce_direction_cut") or 0.0)
    rc = float(cal.get("reduce_confidence_cut") or 0.0)
    hd = float(cal.get("hold_confidence_cut") or 0.0)
    return {
        "direction_minus_reduce_cut": round(abs(d) - rd, 6),
        "confidence_minus_reduce_cut": round(c - rc, 6),
        "confidence_minus_hold_cut": round(c - hd, 6),
    }


def _build_package_b_advanced_input() -> dict[str, Any]:
    from run_lens_myeongni import _recommended_advanced_and_provenance_path
    from myeongni_lens_v1.advanced_payload import parse_advanced_input
    from myeongni_lens_v1.school_registry import (
        KNOWN_SCHOOL_IDS,
        score_school_stub,
    )

    adv_raw, _ = _recommended_advanced_and_provenance_path()
    adv = parse_advanced_input(adv_raw)
    ctx = {
        "pillars": adv.get("pillars") if isinstance(adv.get("pillars"), dict) else {},
        "dayun": adv.get("dayun") if isinstance(adv.get("dayun"), list) else [],
        "sinsal": adv.get("sinsal") if isinstance(adv.get("sinsal"), list) else [],
        "sajeong_interpolation": (
            adv.get("sajeong_interpolation")
            if isinstance(adv.get("sajeong_interpolation"), dict)
            else {}
        ),
    }
    signals = [score_school_stub(s, ctx) for s in sorted(KNOWN_SCHOOL_IDS)]
    signals = sorted(signals, key=lambda x: float(x.get("direction_hint") or 0.0), reverse=True)
    # package_b target school direction was solved from reverse map: 0.48363
    top1, top2 = signals[0], signals[1]
    d1 = float(top1["direction_hint"])
    d2 = float(top2["direction_hint"])
    target = 0.48363
    if abs(d1 - d2) < 1e-9:
        w1 = 0.5
    else:
        w1 = max(0.0, min(1.0, (target - d2) / (d1 - d2)))
    w2 = 1.0 - w1

    out = dict(adv_raw if isinstance(adv_raw, dict) else {})
    out["schema"] = "myeongni_lens_advanced_input_v1"
    out["schools_active"] = [top1["school_id"], top2["school_id"]]
    out["coordinator_weights"] = {
        top1["school_id"]: round(w1, 6),
        top2["school_id"]: round(w2, 6),
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Run package_b myeongni chain (adv input + v1 lens + v2 balanced/attack).")
    ap.add_argument("--mode", choices=("balanced", "attack", "both"), default="both")
    ap.add_argument("--advanced-output", type=Path, default=ADV_OUT)
    ap.add_argument("--lens-output", type=Path, default=LENS_OUT)
    ap.add_argument("--v2-balanced-output", type=Path, default=V2_BAL_OUT)
    ap.add_argument("--v2-attack-output", type=Path, default=V2_ATK_OUT)
    ap.add_argument("--summary-output", type=Path, default=SUMMARY_OUT)
    ap.add_argument("--profile-policy-json", type=Path, default=PROFILE_POLICY)
    ap.add_argument("--profile-recommendation-output", type=Path, default=PROFILE_REC_OUT)
    args = ap.parse_args()

    adv_out = args.advanced_output if args.advanced_output.is_absolute() else ROOT / args.advanced_output
    lens_out = args.lens_output if args.lens_output.is_absolute() else ROOT / args.lens_output
    v2_bal_out = args.v2_balanced_output if args.v2_balanced_output.is_absolute() else ROOT / args.v2_balanced_output
    v2_atk_out = args.v2_attack_output if args.v2_attack_output.is_absolute() else ROOT / args.v2_attack_output
    summary_out = args.summary_output if args.summary_output.is_absolute() else ROOT / args.summary_output
    profile_policy = (
        args.profile_policy_json if args.profile_policy_json.is_absolute() else ROOT / args.profile_policy_json
    )
    profile_rec_out = (
        args.profile_recommendation_output
        if args.profile_recommendation_output.is_absolute()
        else ROOT / args.profile_recommendation_output
    )

    adv_doc = _build_package_b_advanced_input()
    adv_out.parent.mkdir(parents=True, exist_ok=True)
    adv_out.write_text(json.dumps(adv_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_lens_myeongni.py"),
            "--emit-schema",
            "v1",
            "--advanced-input",
            str(adv_out),
            "--output",
            str(lens_out),
        ]
    )
    run_balanced = args.mode in ("balanced", "both")
    run_attack = args.mode in ("attack", "both")
    if run_balanced:
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_mkm_myeongni_response_v2.py"),
                "--profile",
                "balanced",
                "--lens-json",
                str(lens_out),
                "--output-json",
                str(v2_bal_out),
            ]
        )
    if run_attack:
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_mkm_myeongni_response_v2.py"),
                "--profile",
                "attack",
                "--lens-json",
                str(lens_out),
                "--output-json",
                str(v2_atk_out),
            ]
        )

    bal = _read_json(v2_bal_out) if run_balanced and v2_bal_out.is_file() else {}
    atk = _read_json(v2_atk_out) if run_attack and v2_atk_out.is_file() else {}
    summary = {
        "schema": "mkm_myeongni_package_b_chain_summary_v1",
        "generated_at_utc": _now(),
        "mode": args.mode,
        "inputs": {
            "advanced_input": str(adv_out),
            "lens_output": str(lens_out),
            "v2_balanced_output": str(v2_bal_out) if run_balanced else None,
            "v2_attack_output": str(v2_atk_out) if run_attack else None,
        },
        "snapshot": {
            "direction_core": ((bal or atk).get("core_layer") or {}).get("direction_core"),
            "confidence_adjusted_balanced": (bal.get("coordinator_layer") or {}).get("confidence_adjusted"),
            "confidence_adjusted_attack": (atk.get("coordinator_layer") or {}).get("confidence_adjusted"),
            "decision_balanced": (bal.get("final_action") or {}).get("decision"),
            "decision_attack": (atk.get("final_action") or {}).get("decision"),
        },
        "margins": {
            "balanced": _decision_margin(bal) if bal else None,
            "attack": _decision_margin(atk) if atk else None,
        },
        "governance": {
            "research_only": True,
            "human_signoff_required": True,
            "note": "Track B scenario comparison only; no auto live trigger.",
        },
    }
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    profile_recommendation: dict[str, Any] | None = None
    if profile_policy.is_file():
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "decide_myeongni_profile_switch_v1.py"),
                "--summary-json",
                str(summary_out),
                "--policy-json",
                str(profile_policy),
                "--output-json",
                str(profile_rec_out),
            ]
        )
        if profile_rec_out.is_file():
            profile_recommendation = _read_json(profile_rec_out)
    else:
        profile_recommendation = {"warning": f"missing policy: {profile_policy}"}

    if profile_recommendation is not None:
        summary["profile_switch_recommendation"] = profile_recommendation.get("state")
        summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "summary_out": str(summary_out),
                "snapshot": summary["snapshot"],
                "profile_switch_recommendation": summary.get("profile_switch_recommendation"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
