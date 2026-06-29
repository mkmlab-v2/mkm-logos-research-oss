#!/usr/bin/env python3
"""[HYPO] Sweep birth+session overlay weights → JSONL → KOSPI strict OOS (research only)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/birth_overlay_param_sweep_v1_latest.json"
TMP_MY = ROOT / "data/myeongni/_tmp_birth_overlay_sweep_myeongni.jsonl"
TMP_SA = ROOT / "data/sasang/_tmp_birth_overlay_sweep_sasang.jsonl"
TMP_SIDECAR = ROOT / "docs/final/artifacts/_tmp_birth_overlay_sweep_sidecar.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-weights", default="0.25,0.35,0.45")
    ap.add_argument("--overlay-bands", default="0.06,0.08,0.10")
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    weights = [float(x.strip()) for x in args.session_weights.split(",") if x.strip()]
    bands = [float(x.strip()) for x in args.overlay_bands.split(",") if x.strip()]
    py = sys.executable
    rows: list[dict[str, Any]] = []

    for sw in weights:
        for band in bands:
            tag = f"sw{sw}_band{band}"
            subprocess.run(
                [
                    py,
                    str(ROOT / "scripts/build_myeongni_jsonl_from_birth_session_overlay_v1.py"),
                    "--session-weight",
                    str(sw),
                    "--overlay-band",
                    str(band),
                    "--myeongni-out",
                    str(TMP_MY),
                    "--sasang-out",
                    str(TMP_SA),
                ],
                cwd=str(ROOT),
                check=True,
            )
            subprocess.run(
                [
                    py,
                    str(ROOT / "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"),
                    "--score-json",
                    str(ROOT / "docs/final/artifacts/btrack_prophecy_score_30y_dual_latest.json"),
                    "--out",
                    str(TMP_SIDECAR),
                    "--myeongni-experiment-jsonl",
                    str(TMP_MY),
                    "--sasang-dynamics-jsonl",
                    str(TMP_SA),
                    "--skip-external-observations",
                ],
                cwd=str(ROOT),
                check=True,
            )
            oos_out = ROOT / "reports" / f"_tmp_birth_overlay_oos_{tag}.json"
            subprocess.run(
                [
                    py,
                    str(ROOT / "scripts/run_prophecy_lens_role_router_oos_gate_v1.py"),
                    "--score-json",
                    str(ROOT / "docs/final/artifacts/btrack_prophecy_score_30y_dual_latest.json"),
                    "--sidecar-json",
                    str(TMP_SIDECAR),
                    "--target-instrument",
                    "kospi",
                    "--month-lookback-grid",
                    "28",
                    "--neutral-size-grid",
                    "0.15",
                    "--oos-tail-days",
                    "252",
                    "--gate-min-hit-rate",
                    "0.52",
                    "--output",
                    str(oos_out),
                ],
                cwd=str(ROOT),
                check=True,
            )
            doc = _read(oos_out)
            oos = doc.get("oos_metrics") or {}
            gate = doc.get("gate") or {}
            rows.append(
                {
                    "tag": tag,
                    "session_weight": sw,
                    "overlay_band": band,
                    "oos_hit": oos.get("directional_hit_rate_active"),
                    "oos_n_active": oos.get("n_active_days"),
                    "oos_return": oos.get("total_return"),
                    "go": gate.get("go"),
                    "status": gate.get("status"),
                }
            )

    golden_hit = 0.565217
    best = max(rows, key=lambda r: float(r.get("oos_hit") or 0)) if rows else None
    out = {
        "schema": "birth_overlay_param_sweep_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "golden_sparse_hit_reference": golden_hit,
        "rows": rows,
        "best_row": best,
        "beats_golden": bool(best and float(best.get("oos_hit") or 0) > golden_hit),
        "note_ko": "승격·v1_latest 교체 없음. golden은 sparse_orig KOSPI 조합.",
    }
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(text, encoding="utf-8")
    print(json.dumps({"wrote": str(args.out_json), "best": best}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
