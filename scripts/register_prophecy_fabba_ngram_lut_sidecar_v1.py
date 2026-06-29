#!/usr/bin/env python3
"""Register fABBA ngram_lut as non-gating feature_lut sidecar (180d/2bps) [HYPO].

Chains: merged LUT build → WF ablation smoke → governance registration artifact.
Does not mutate Primary score JSON or prophecy vote paths.
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_BASE_LUT = ROOT / "reports/btrack_ohlcv_feature_lut_v1_latest.json"
DEFAULT_MERGED_LUT = ROOT / "reports/btrack_ohlcv_feature_lut_with_fabba_sidecar_v1_latest.json"
DEFAULT_BRIDGE = ROOT / "reports/prophecy_fabba_sidecar_btrack_bridge_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_science_core_panel_v1.json"
DEFAULT_LINUX_AB = ROOT / "reports/prophecy_fabba_backend_ab_linux_wsl_v1_latest.json"
DEFAULT_PHASE3 = ROOT / "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json"
DEFAULT_ABLATION = ROOT / "reports/prophecy_fabba_lut_wf_ablation_smoke_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_fabba_ngram_lut_sidecar_registration_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/prophecy_fabba_ngram_lut_sidecar_registration_v1_latest.json"
SCHEMA = "prophecy_fabba_ngram_lut_sidecar_registration_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _ngram_hr_from_linux(linux_doc: dict[str, Any]) -> dict[str, Any]:
    arms = ((linux_doc.get("arms") or {}).get("fabba") or {}).get("dual_leg_pooled_arms") or []
    if not arms:
        arms = ((linux_doc.get("arms") or {}).get("apca_stub") or {}).get("dual_leg_pooled_arms") or []
    ngram = next((a for a in arms if a.get("arm_id") == "fabba_sidecar_ngram_lut"), {})
    per_kospi = next(
        (p for p in (ngram.get("per_instrument") or []) if p.get("instrument_id") == "kospi"),
        {},
    )
    return {
        "dual_leg_pooled_hr": ngram.get("pooled_test_directional_hit_rate"),
        "kospi_pooled_hr": per_kospi.get("pooled_test_directional_hit_rate"),
        "btc_pooled_hr": next(
            (
                p.get("pooled_test_directional_hit_rate")
                for p in (ngram.get("per_instrument") or [])
                if p.get("instrument_id") == "btc"
            ),
            None,
        ),
        "protocol": ngram.get("protocol"),
        "model": ngram.get("model"),
    }


def _arm_a_hr(phase3: dict[str, Any]) -> float | None:
    for row in phase3.get("lens_sharpe_ranking") or []:
        if row.get("strategy_id") == "science+sasang":
            v = row.get("directional_hit_rate_active")
            return float(v) if isinstance(v, (int, float)) else None
    return None


def register(
    *,
    kospi_csv: Path,
    btc_csv: Path,
    base_lut: Path,
    merged_lut: Path,
    bridge: Path,
    score_json: Path,
    linux_ab: Path,
    phase3: Path,
    ablation_out: Path,
    last_n_intersection: int,
    skip_build: bool,
    skip_ablation: bool,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []

    if not skip_build:
        cmd = [
            sys.executable,
            str(ROOT / "scripts/build_btrack_ohlcv_feature_lut_with_fabba_sidecar_v1.py"),
            "--kospi-csv",
            str(kospi_csv),
            "--btc-csv",
            str(btc_csv),
            "--base-lut",
            str(base_lut),
            "--rebuild-base-lut",
            "--last-n-intersection",
            str(last_n_intersection),
            "--output",
            str(merged_lut),
            "--bridge-output",
            str(bridge),
        ]
        rc = subprocess.call(cmd, cwd=str(ROOT))
        steps.append({"step": "build_merged_lut", "exit_code": rc})
        if rc != 0:
            return {"ok": False, "steps": steps}

    if not skip_ablation:
        cmd = [
            sys.executable,
            str(ROOT / "scripts/run_prophecy_fabba_lut_wf_ablation_smoke_v1.py"),
            "--score-json",
            str(score_json),
            "--base-lut",
            str(base_lut),
            "--merged-lut",
            str(merged_lut),
            "--output",
            str(ablation_out),
        ]
        rc = subprocess.call(cmd, cwd=str(ROOT))
        steps.append({"step": "lut_wf_ablation_smoke", "exit_code": rc, "output": _rel(ablation_out)})
        if rc != 0:
            return {"ok": False, "steps": steps}

    merged_doc = _read_json(merged_lut)
    ablation_doc = _read_json(ablation_out)
    linux_doc = _read_json(linux_ab)
    phase3_doc = _read_json(phase3)
    bridge_doc = _read_json(bridge)

    ngram_evidence = _ngram_hr_from_linux(linux_doc)
    arm_a_hr = _arm_a_hr(phase3_doc)
    kospi_ngram_hr = ngram_evidence.get("kospi_pooled_hr")

    parity_ok = ((ablation_doc.get("feature_parity") or {}).get("base_vs_merged_stripped_ok")) is True
    base_wf = ((ablation_doc.get("wf_variants") or {}).get("base_lut_maps") or {}).get(
        "mean_test_directional_hit_rate"
    ) or ((ablation_doc.get("wf_variants") or {}).get("base_lut_maps") or {}).get("mean_test_accuracy")
    fabba_opt_wf = ((ablation_doc.get("wf_variants") or {}).get("merged_lut_with_fabba_sidecar") or {}).get(
        "mean_test_directional_hit_rate"
    ) or ((ablation_doc.get("wf_variants") or {}).get("merged_lut_with_fabba_sidecar") or {}).get(
        "mean_test_accuracy"
    ) or ((ablation_doc.get("wf_variants") or {}).get("merged_lut_fabba_opt_in") or {}).get(
        "mean_test_directional_hit_rate"
    ) or ((ablation_doc.get("wf_variants") or {}).get("merged_lut_fabba_opt_in") or {}).get(
        "mean_test_accuracy"
    )

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "registration": {
            "primary_sidecar_arm": "fabba_sidecar_ngram_lut",
            "secondary_sidecar_arm": "fabba_sidecar_last_slope",
            "vote_participation": "none",
            "non_gating": True,
            "consumer_contract_ko": (
                "merged LUT의 fabba_ngram_* 컬럼은 feature/meta join 전용. "
                "prophecy lens vote·Primary score·Track A ensemble에 자동 합류 금지."
            ),
            "opt_in_only": True,
        },
        "protocol": {
            "last_n_intersection": last_n_intersection,
            "neutral_bps": merged_doc.get("sidecar_params", {}).get("neutral_bps", 2.0),
            "tol": merged_doc.get("sidecar_params", {}).get("tol"),
            "ngram_size": merged_doc.get("sidecar_params", {}).get("ngram_size"),
            "lookback": merged_doc.get("sidecar_params", {}).get("lookback"),
        },
        "artifacts": {
            "merged_lut": _rel(merged_lut),
            "base_lut": _rel(base_lut),
            "bridge": _rel(bridge),
            "ablation_smoke": _rel(ablation_out),
            "linux_dual_leg_ab": _rel(linux_ab),
            "phase3_shadow": _rel(phase3),
        },
        "shadow_hr_evidence": {
            "ngram_lut_kospi_dual_leg_180d_2bps": ngram_evidence,
            "arm_a_science_sasang_panel_hr_180d": arm_a_hr,
            "delta_ngram_kospi_vs_arm_a_pp": round((float(kospi_ngram_hr) - float(arm_a_hr)) * 100.0, 4)
            if kospi_ngram_hr is not None and arm_a_hr is not None
            else None,
        },
        "lut_ablation_smoke": {
            "feature_parity_ok": parity_ok,
            "base_lut_wf_mean_hr": base_wf,
            "merged_fabba_opt_in_wf_mean_hr": fabba_opt_wf,
            "fabba_opt_in_delta_pp": round((float(fabba_opt_wf) - float(base_wf)) * 100.0, 4)
            if fabba_opt_wf is not None and base_wf is not None
            else None,
        },
        "bridge_snapshot": {
            "recommended_shadow_params": bridge_doc.get("recommended_shadow_params"),
            "usage_ko": bridge_doc.get("usage_ko"),
        },
        "steps": steps,
        "ok": True,
        "headline_ko": [
            f"ngram_lut KOSPI HR={kospi_ngram_hr} (dual-leg shadow)",
            f"Arm A panel HR={arm_a_hr}",
            f"LUT parity ok={parity_ok}",
            "vote=none sidecar-only registration",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--base-lut", type=Path, default=DEFAULT_BASE_LUT)
    ap.add_argument("--merged-lut", type=Path, default=DEFAULT_MERGED_LUT)
    ap.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--linux-ab", type=Path, default=DEFAULT_LINUX_AB)
    ap.add_argument("--phase3", type=Path, default=DEFAULT_PHASE3)
    ap.add_argument("--ablation-out", type=Path, default=DEFAULT_ABLATION)
    ap.add_argument("--last-n-intersection", type=int, default=180)
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--skip-ablation", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    payload = register(
        kospi_csv=args.kospi_csv,
        btc_csv=args.btc_csv,
        base_lut=args.base_lut,
        merged_lut=args.merged_lut,
        bridge=args.bridge,
        score_json=args.score_json,
        linux_ab=args.linux_ab,
        phase3=args.phase3,
        ablation_out=args.ablation_out,
        last_n_intersection=max(1, int(args.last_n_intersection)),
        skip_build=bool(args.skip_build),
        skip_ablation=bool(args.skip_ablation),
    )

    for path in (args.output, args.artifact_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not payload.get("ok"):
        print(f"FAIL steps={payload.get('steps')}", file=sys.stderr)
        return 1
    hr = (payload.get("shadow_hr_evidence") or {}).get("ngram_lut_kospi_dual_leg_180d_2bps") or {}
    print(
        f"OK ngram_lut registered kospi_hr={hr.get('kospi_pooled_hr')} "
        f"parity={((payload.get('lut_ablation_smoke') or {}).get('feature_parity_ok'))} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
