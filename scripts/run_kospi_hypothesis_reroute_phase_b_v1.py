#!/usr/bin/env python3

"""Phase B: KOSPI price-axis overnight overlay + before/after delta vs Phase A [HYPO]."""



from __future__ import annotations



import argparse

import json

import subprocess

import sys

from datetime import datetime, timezone

from pathlib import Path

from typing import Any



ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUT = ROOT / "reports/kospi_hypothesis_reroute_phase_b_v1_latest.json"

PHASE_A_DELTA = ROOT / "reports/kospi_hypothesis_reroute_delta_v1_latest.json"

HYPOTHESIS_PATH = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"

OVERNIGHT_PATH = ROOT / "docs/final/artifacts/global_market_overnight_signals_v1_latest.json"





def _utc_now() -> str:

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")





def _read_json(path: Path) -> dict[str, Any]:

    if not path.is_file():

        return {}

    return json.loads(path.read_text(encoding="utf-8-sig"))





def _hypo_summary(doc: dict[str, Any]) -> dict[str, Any]:

    pred = doc.get("prediction") or {}

    rm = doc.get("runtime_meta") or {}

    pm = rm.get("price_meta") if isinstance(rm.get("price_meta"), dict) else {}

    return {

        "ts_utc": doc.get("ts_utc"),

        "instrument": pred.get("instrument"),

        "direction": pred.get("direction"),

        "confidence": pred.get("confidence"),

        "weighted_score": rm.get("weighted_score"),

        "lens_values": rm.get("lens_values") or {},

        "price_meta": pm,

        "kospi_overnight_overlay": pm.get("kospi_overnight_overlay"),

    }





def _run_py(script: str, *args: str) -> int:

    cmd = [sys.executable, str(ROOT / script), *args]

    print("==>", " ".join(cmd))

    return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode





def main(argv: list[str] | None = None) -> int:

    ap = argparse.ArgumentParser(description=__doc__)

    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)

    ap.add_argument("--skip-fetch", action="store_true")

    args = ap.parse_args(argv)



    steps: list[dict[str, Any]] = []

    phase_a = _read_json(PHASE_A_DELTA)

    before = phase_a.get("after") if isinstance(phase_a.get("after"), dict) else _hypo_summary(_read_json(HYPOTHESIS_PATH))

    steps.append({"step": "before_source", "from": "phase_a_delta.after" if phase_a.get("after") else "current_hypothesis"})



    if not args.skip_fetch:

        for script in (

            "scripts/fetch_kospi_yfinance_csv.py",

            "scripts/fetch_nasdaq_yfinance_csv.py",

            "scripts/fetch_ndx_yfinance_csv.py",

            "scripts/fetch_global_overnight_indices_yfinance_v1.py",

        ):

            rc = _run_py(script)

            steps.append({"step": script, "exit_code": rc})

            if rc != 0:

                steps.append({"step": "abort", "reason": f"{script} failed"})

                break

        else:

            rc = _run_py("scripts/build_global_market_overnight_signals_v1.py")

            steps.append({"step": "build_global_market_overnight_signals_v1.py", "exit_code": rc})

            if rc != 0:

                return rc



    overnight = _read_json(OVERNIGHT_PATH)

    steps.append({"step": "overnight_artifact", "present": bool(overnight), "composite": overnight.get("composite_tilt")})



    rc = _run_py("scripts/build_btrack_news_macro_lens_adapters_v1.py")

    steps.append({"step": "build_btrack_news_macro_lens_adapters_v1.py", "exit_code": rc})

    if rc != 0:

        return rc



    rc = _run_py("scripts/build_btrack_llm_input_bundle.py")

    steps.append({"step": "build_btrack_llm_input_bundle.py", "exit_code": rc})

    if rc != 0:

        return rc



    rc = _run_py(

        "scripts/generate_btrack_hypothesis_prophecy_v1.py",

        "--research-evaluation-instrument",

        "kospi",

    )

    steps.append({"step": "generate_btrack_hypothesis_prophecy_v1.py", "exit_code": rc})

    if rc != 0:

        return rc



    after_doc = _read_json(HYPOTHESIS_PATH)

    after = _hypo_summary(after_doc)

    overlay = after.get("kospi_overnight_overlay") if isinstance(after.get("kospi_overnight_overlay"), dict) else {}



    def _f(x: Any) -> float | None:

        try:

            return float(x) if x is not None else None

        except (TypeError, ValueError):

            return None



    b_dir = before.get("direction")

    a_dir = after.get("direction")

    flipped = bool(b_dir and a_dir and b_dir != a_dir)

    overlay_applied = bool(overlay.get("applied"))



    out = {

        "schema": "kospi_hypothesis_reroute_phase_b_v1",

        "generated_at_utc": _utc_now(),

        "hypothesis_tier": "B",

        "research_only": True,

        "track_a_auto_merge_forbidden": True,

        "live_trading_trigger_forbidden": True,

        "phase": "B",

        "operational_verdict": (

            "DIRECTION_FLIPPED_RESEARCH_ONLY"

            if flipped

            else ("OVERLAY_APPLIED_HOLD_ZERO_TRUST" if overlay_applied else "OVERLAY_NOT_APPLIED_HOLD")

        ),

        "before": before,

        "after": after,

        "delta": {

            "direction_before": b_dir,

            "direction_after": a_dir,

            "direction_flipped": flipped,

            "confidence_delta": (_f(after.get("confidence")) or 0) - (_f(before.get("confidence")) or 0),

            "weighted_score_delta": (_f(after.get("weighted_score")) or 0) - (_f(before.get("weighted_score")) or 0),

            "price_score_before": _f((before.get("lens_values") or {}).get("price", {}).get("score")),

            "price_score_after": _f((after.get("lens_values") or {}).get("price", {}).get("score")),

            "kospi_overnight_overlay_applied": overlay_applied,

            "kospi_overnight_overlay": overlay,

        },

        "overnight_artifact_path": str(OVERNIGHT_PATH.relative_to(ROOT)).replace("\\", "/"),

        "steps": steps,

        "note": "Phase B price-axis overlay; not MS/Track A/live promotion.",

    }



    args.out_json.parent.mkdir(parents=True, exist_ok=True)

    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out_json.resolve()}")

    print(

        f"DELTA: {b_dir} -> {a_dir} "

        f"price {_f((before.get('lens_values') or {}).get('price', {}).get('score'))} -> "

        f"{_f((after.get('lens_values') or {}).get('price', {}).get('score'))} "

        f"overlay={'yes' if overlay_applied else 'no'}"

    )

    return 0





if __name__ == "__main__":

    raise SystemExit(main())

