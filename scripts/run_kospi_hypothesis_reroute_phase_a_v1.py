#!/usr/bin/env python3
"""Phase A: KOSPI hypothesis reroute — fetch, global overnight ingest, before/after delta [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/kospi_hypothesis_reroute_delta_v1_latest.json"
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
    lv = rm.get("lens_values") or {}
    return {
        "ts_utc": doc.get("ts_utc"),
        "instrument": pred.get("instrument"),
        "direction": pred.get("direction"),
        "confidence": pred.get("confidence"),
        "weighted_score": rm.get("weighted_score"),
        "lens_values": lv,
        "price_meta": rm.get("price_meta"),
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
    before_doc = _read_json(HYPOTHESIS_PATH)
    before = _hypo_summary(before_doc)

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

    macro_lens = _read_json(ROOT / "docs/final/artifacts/macro_independent_lens_latest.json")
    news_lens = _read_json(ROOT / "docs/final/artifacts/news_independent_lens_latest.json")

    def _f(x: Any) -> float | None:
        try:
            return float(x) if x is not None else None
        except (TypeError, ValueError):
            return None

    b_dir = before.get("direction")
    a_dir = after.get("direction")
    flipped = b_dir != a_dir and b_dir and a_dir

    out = {
        "schema": "kospi_hypothesis_reroute_delta_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_a_auto_merge_forbidden": True,
        "live_trading_trigger_forbidden": True,
        "phase": "A",
        "operational_verdict": "HOLD_ZERO_TRUST_UNTIL_WF" if not flipped else "DIRECTION_FLIPPED_RESEARCH_ONLY",
        "before": before,
        "after": after,
        "delta": {
            "direction_before": b_dir,
            "direction_after": a_dir,
            "direction_flipped": flipped,
            "confidence_delta": (_f(after.get("confidence")) or 0) - (_f(before.get("confidence")) or 0),
            "weighted_score_delta": (_f(after.get("weighted_score")) or 0) - (_f(before.get("weighted_score")) or 0),
            "macro_direction_score": (macro_lens.get("scores") or {}).get("direction_score"),
            "news_direction_score": (news_lens.get("scores") or {}).get("direction_score"),
            "global_overnight_seed_count": (macro_lens.get("macro_stream_outputs") or {}).get(
                "global_overnight_seed_count"
            ),
            "global_overnight_headline_count": (news_lens.get("news_stream_outputs") or {}).get(
                "global_overnight_headline_count"
            ),
        },
        "overnight_artifact_path": str(OVERNIGHT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
        "note": "Phase A ingest test; not MS/Track A/live promotion.",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(
        f"DELTA: {b_dir} -> {a_dir} "
        f"weighted_score {_f(before.get('weighted_score'))} -> {_f(after.get('weighted_score'))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
