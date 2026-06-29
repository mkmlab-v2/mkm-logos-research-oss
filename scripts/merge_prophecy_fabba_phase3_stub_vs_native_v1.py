#!/usr/bin/env python3
"""Merge phase3 apca_stub vs WSL fABBA native compare artifact [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUB = ROOT / "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json"
DEFAULT_NATIVE = ROOT / "reports/prophecy_lens_profile_shadow_ablation_phase3_fabba_native_v1_latest.json"
DEFAULT_LINUX = ROOT / "reports/prophecy_fabba_backend_ab_linux_wsl_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_fabba_phase3_stub_vs_native_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/prophecy_fabba_phase3_stub_vs_native_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _fabba_hr(doc: dict[str, Any]) -> float | None:
    pooled = ((doc.get("fabba_delta_arms") or {}).get("pooled_test_hr")) or {}
    v = pooled.get("fabba_sidecar_last_slope")
    return float(v) if isinstance(v, (int, float)) else None


def build_compare(*, stub: Path, native: Path, linux_dual: Path) -> dict[str, Any]:
    stub_doc = _read(stub)
    native_doc = _read(native)
    linux_doc = _read(linux_dual)
    stub_hr = _fabba_hr(stub_doc)
    native_hr = _fabba_hr(native_doc)
    arm_a_hr = ((stub_doc.get("myeongni_sasang_lane") or {}).get("metrics") or {}).get(
        "directional_hit_rate_active"
    )
    # science+sasang from lens ranking
    arm_a = None
    for row in stub_doc.get("lens_sharpe_ranking") or []:
        if row.get("strategy_id") == "science+sasang":
            arm_a = row.get("directional_hit_rate_active")
            break

    linux_cmp = linux_doc.get("compare") or {}
    return {
        "schema": "prophecy_fabba_phase3_stub_vs_native_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "inputs": {
            "phase3_apca_stub": str(stub),
            "phase3_fabba_native": str(native),
            "linux_dual_leg_ab": str(linux_dual),
        },
        "kospi_180d_2bps_fabba_last_slope_pooled_hr": {
            "apca_stub_windows": stub_hr,
            "fabba_native_wsl": native_hr,
            "delta_native_minus_stub_pp": round((native_hr - stub_hr) * 100.0, 4)
            if stub_hr is not None and native_hr is not None
            else None,
        },
        "arm_a_science_sasang_panel_hr": arm_a,
        "linux_dual_leg_180d": {
            "fabba_native_available": linux_doc.get("fabba_native_available"),
            "ngram_hr_delta_fabba_minus_apca": linux_cmp.get("ngram_hr_delta_fabba_minus_apca"),
            "pooled_dual_leg_apca": ((linux_doc.get("arms") or {}).get("apca_stub") or {})
            .get("dual_leg_pooled_arms"),
        },
        "verdict_ko": (
            "Windows apca_stub vs WSL fABBA wheel: KOSPI 180d last_slope HR 차이는 sidecar shadow만. "
            "native≠자동 승격; Arm A science+sasang quant SSOT 유지."
        ),
        "headline_ko": [
            f"stub HR={stub_hr} native HR={native_hr}",
            f"delta pp={(round((native_hr - stub_hr) * 100.0, 4) if stub_hr is not None and native_hr is not None else None)}",
            f"Arm A HR={arm_a}",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stub-phase3", type=Path, default=DEFAULT_STUB)
    ap.add_argument("--native-phase3", type=Path, default=DEFAULT_NATIVE)
    ap.add_argument("--linux-dual-ab", type=Path, default=DEFAULT_LINUX)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    payload = build_compare(stub=args.stub_phase3, native=args.native_phase3, linux_dual=args.linux_dual_ab)
    for path in (args.output, args.artifact_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK stub={payload['kospi_180d_2bps_fabba_last_slope_pooled_hr']['apca_stub_windows']} "
          f"native={payload['kospi_180d_2bps_fabba_last_slope_pooled_hr']['fabba_native_wsl']} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
