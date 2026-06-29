#!/usr/bin/env python3
"""Build btrack OHLCV LUT with read-only fabba sidecar join (non-gating meta).

Does not overwrite ``btrack_ohlcv_feature_lut_v1_latest.json``. Primary score/WF
paths remain unchanged unless explicitly pointed at merged output.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ohlcv_feature_lut_lib_v1 import (  # noqa: E402
    DEFAULT_BTC,
    DEFAULT_KOSPI,
    DEFAULT_LUT,
    build_fabba_sidecar_maps_for_lut,
    build_lut_document,
    load_lut_document,
    merge_fabba_sidecar_into_lut_document,
    prior_and_feature_maps_from_lut,
)

DEFAULT_OUT = ROOT / "reports/btrack_ohlcv_feature_lut_with_fabba_sidecar_v1_latest.json"
DEFAULT_REVALIDATE = ROOT / "reports/prophecy_fabba_sidecar_sweep_dual_leg_revalidate_v1_latest.json"
DEFAULT_BRIDGE = ROOT / "reports/prophecy_fabba_sidecar_btrack_bridge_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_recommended_params(revalidate_path: Path) -> dict[str, float | int]:
    defaults = {"tol": 0.03, "ngram_size": 2, "lookback": 20, "neutral_bps": 2.0}
    if not revalidate_path.is_file():
        return defaults
    try:
        doc = json.loads(revalidate_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return defaults
    rec = (doc.get("overfit_assessment") or {}).get("recommended_shadow_params") or {}
    return {
        "tol": float(rec.get("tol", defaults["tol"])),
        "ngram_size": int(rec.get("ngram_size", defaults["ngram_size"])),
        "lookback": int(defaults["lookback"]),
        "neutral_bps": float(defaults["neutral_bps"]),
    }


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--base-lut", type=Path, default=DEFAULT_LUT)
    ap.add_argument("--rebuild-base-lut", action="store_true")
    ap.add_argument("--last-n-intersection", type=int, default=180)
    ap.add_argument("--tol", type=float, default=None)
    ap.add_argument("--ngram-size", type=int, default=None)
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--backend", default="apca_stub")
    ap.add_argument("--revalidate-json", type=Path, default=DEFAULT_REVALIDATE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--bridge-output", type=Path, default=DEFAULT_BRIDGE)
    args = ap.parse_args()

    if not args.kospi_csv.is_file() or not args.btc_csv.is_file():
        raise SystemExit("missing kospi or btc csv")

    rec = _load_recommended_params(args.revalidate_json)
    tol = float(args.tol if args.tol is not None else rec["tol"])
    ngram_size = int(args.ngram_size if args.ngram_size is not None else rec["ngram_size"])

    if args.rebuild_base_lut or not args.base_lut.is_file():
        base_doc = build_lut_document(
            kospi_csv=args.kospi_csv,
            btc_csv=args.btc_csv,
            generated_at_utc=_utc_now(),
            last_n_intersection=args.last_n_intersection,
        )
        args.base_lut.parent.mkdir(parents=True, exist_ok=True)
        args.base_lut.write_text(json.dumps(base_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        base_doc = load_lut_document(args.base_lut)

    intersection = list(base_doc.get("intersection_dates") or [])
    sidecar = build_fabba_sidecar_maps_for_lut(
        kospi_csv=args.kospi_csv,
        btc_csv=args.btc_csv,
        intersection_dates=intersection,
        lookback=args.lookback,
        ngram_size=ngram_size,
        tol=tol,
        neutral_bps=args.neutral_bps,
        backend=args.backend,
    )

    sidecar_params = {
        "tol": tol,
        "ngram_size": ngram_size,
        "lookback": args.lookback,
        "neutral_bps": args.neutral_bps,
        "backend": args.backend,
        "source": "prophecy_fabba_sidecar_sweep_dual_leg_revalidate_v1",
    }

    merged = merge_fabba_sidecar_into_lut_document(
        base_doc,
        sidecar_by_instrument=sidecar,
        sidecar_params=sidecar_params,
        revalidate_pointer=_rel(args.revalidate_json) if args.revalidate_json.is_file() else None,
        generated_at_utc=_utc_now(),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    bridge = {
        "schema": "prophecy_fabba_sidecar_btrack_bridge_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "pointers": {
            "btrack_ohlcv_feature_lut_base": _rel(args.base_lut),
            "btrack_ohlcv_feature_lut_merged": _rel(args.output),
            "dual_leg_revalidate": _rel(args.revalidate_json) if args.revalidate_json.is_file() else None,
        },
        "recommended_shadow_params": sidecar_params,
        "stats": merged.get("stats"),
        "usage_ko": "WF/score Primary는 base LUT; merged는 fabba sidecar numeric+meta join — opt-in only.",
    }
    args.bridge_output.parent.mkdir(parents=True, exist_ok=True)
    args.bridge_output.write_text(json.dumps(bridge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    km, bm, kf, bf = prior_and_feature_maps_from_lut(base_doc)
    sample_d = intersection[-1] if intersection else None
    base_keys = set(kf.get(sample_d, {}).keys()) if sample_d else set()
    merged_kf = (merged.get("features_by_instrument") or {}).get("kospi") or {}
    merged_keys = set(merged_kf.get(sample_d, {}).keys()) if sample_d else set()
    fabba_only = merged_keys - base_keys

    print(
        f"WROTE: {args.output.resolve()} "
        f"n_merged={merged['stats'].get('n_sidecar_feature_rows_merged')} "
        f"fabba_cols={sorted(fabba_only)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
