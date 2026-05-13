# -*- coding: utf-8 -*-
"""B-track spike: Hebrew gematria 4D (bridge) + Myeongri 4D blend — geometric metrics only.

Not prediction accuracy, not doctrinal consistency. AD birth years only (BC unsupported
in PerfectManseryeok). Output: optional JSON artifact for internal vector deltas.

See also: independent_lens_fusion_stub_v0 (lens direction consensus; no consistency_rate).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge
from scripts.myeongri_complete_fusion import MyeongriCompleteFusion
from tools.myeongni.gematria_myeongri_math_v1 import (
    MATH_MODULE_ID,
    MATH_MODULE_VERSION,
    blend_convex_renorm,
    coerce_4d,
    geometric_metrics,
)


def run_spike(
    *,
    hebrew_text: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    is_solar: bool,
    is_male: bool,
    blend_weight_myeongri: float,
) -> Dict[str, Any]:
    meta = build_gematria_metadata(
        raw_text=hebrew_text,
        compressed_text=hebrew_text,
        reconstructed_text=hebrew_text,
    )
    bridge = build_gematria_4d_bridge(gematria_metadata=meta)
    vanilla = coerce_4d(bridge["vector_4d"])  # type: ignore[index]
    fusion = MyeongriCompleteFusion().calculate_complete_fusion(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        is_solar=is_solar,
        is_male=is_male,
    )
    myeongri = coerce_4d(fusion["vector_4d"])
    hybrid = blend_convex_renorm(vanilla, myeongri, blend_weight_myeongri)
    metrics = geometric_metrics(vanilla, myeongri, hybrid)

    return {
        "schema": "gematria_myeongri_spike_blend_v0",
        "version": "0.1.0",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "label": (
            "[HYPO][NON-MEDICAL] Gematria–Myeongri 4D blend spike; deterministic geometry "
            f"({MATH_MODULE_ID} v{MATH_MODULE_VERSION}); not trading or doctrinal accuracy."
        ),
        "disclaimer": (
            "Geometric distances in 4D only; not accuracy, not trading, not doctrinal claim. "
            "Birth inputs are [HYPO] unless sourced."
        ),
        "inputs": {
            "hebrew_text": hebrew_text,
            "birth_year": birth_year,
            "birth_month": birth_month,
            "birth_day": birth_day,
            "birth_hour": birth_hour,
            "is_solar": is_solar,
            "is_male": is_male,
            "blend_weight_myeongri": blend_weight_myeongri,
        },
        "gematria_metadata": meta,
        "vanilla_bridge": {k: bridge[k] for k in bridge if k != "vector_4d"},
        "vector_4d": {
            "vanilla": vanilla,
            "myeongri": myeongri,
            "hybrid": hybrid,
        },
        "metrics": metrics,
        "fact_lock": {
            "gematria_myeongri_math_module": MATH_MODULE_ID,
            "gematria_myeongri_math_version": MATH_MODULE_VERSION,
            "independent_lens_fusion_stub_has_consistency_rate": False,
            "consistency_rate_where_defined": (
                "docs/final/MYEONGNI_16_STATE_EXPERIMENT_JSON_SCHEMA.json (16-state experiment ledger)"
            ),
            "fusion_stub_consensus_fields": "agreement_rate, consensus_score (lens directions), not vector blend",
        },
    }


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--hebrew-text",
        default="\u05d9\u05e9\u05d5\u05e2",
        help="Hebrew text for gematria (default: Yeshua four-letter spelling)",
    )
    p.add_argument("--birth-year", type=int, default=4, help="AD year only (BC unsupported)")
    p.add_argument("--birth-month", type=int, default=1)
    p.add_argument("--birth-day", type=int, default=1)
    p.add_argument("--birth-hour", type=int, default=12)
    p.add_argument("--solar", action="store_true", default=True)
    p.add_argument("--no-solar", action="store_false", dest="solar")
    p.add_argument("--male", action="store_true", default=True)
    p.add_argument("--female", action="store_false", dest="male")
    p.add_argument(
        "--blend-weight",
        type=float,
        default=0.5,
        help="Weight of myeongri in convex blend before renormalization (0..1)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=_WS / "docs" / "final" / "artifacts" / "gematria_myeongri_spike_blend_latest.json",
    )
    p.add_argument("--stdout-only", action="store_true", help="Print JSON; do not write file")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    doc = run_spike(
        hebrew_text=args.hebrew_text,
        birth_year=args.birth_year,
        birth_month=args.birth_month,
        birth_day=args.birth_day,
        birth_hour=args.birth_hour,
        is_solar=args.solar,
        is_male=args.male,
        blend_weight_myeongri=args.blend_weight,
    )
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"\nWrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
