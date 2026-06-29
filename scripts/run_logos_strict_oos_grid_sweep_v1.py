#!/usr/bin/env python3
"""[HYPO] Grid sweep for strict Logos OOS gate — pick best go=true hit (research only)."""
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
DEFAULT_SCORE = ART / "btrack_prophecy_score_30y_dual_latest.json"
DEFAULT_SCORE_FALLBACKS = (
    ART / "btrack_prophecy_score_latest.json",
    ART / "btrack_prophecy_score_kospi_dual_v2_per_date_latest.json",
)
DEFAULT_SIDECAR = ART / "btrack_prophecy_score_insight_sidecar_30y_latest.json"
DEFAULT_SIDECAR_FALLBACK = ART / "btrack_prophecy_score_insight_sidecar_v1_latest.json"
DEFAULT_BTC = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
OUT_DEFAULT = ROOT / "reports" / "logos_strict_oos_grid_sweep_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--target-instrument", type=str, default="kospi")
    ap.add_argument("--oos-tail-days", type=int, default=252)
    ap.add_argument("--lookbacks", type=str, default="21,63,126")
    ap.add_argument("--neutrals", type=str, default="0.2,0.3,0.5,0.7")
    ap.add_argument("--min-hit-rate", type=float, default=0.52)
    ap.add_argument("--promote-if-better", action="store_true", help="Copy best go snapshot to *_Nd_latest + promote")
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    if not args.score_json.is_file():
        for fb in DEFAULT_SCORE_FALLBACKS:
            if fb.is_file():
                args.score_json = fb
                break
    if not args.sidecar_json.is_file() and DEFAULT_SIDECAR_FALLBACK.is_file():
        args.sidecar_json = DEFAULT_SIDECAR_FALLBACK
    if not args.score_json.is_file():
        summary = {
            "schema": "logos_strict_oos_grid_sweep_v1",
            "generated_at_utc": _now(),
            "research_only": True,
            "error": "score_json_missing",
            "hint": "Regenerate btrack_prophecy_score_30y_dual_latest.json (long KOSPI panel) then re-run.",
            "requested_score": str(DEFAULT_SCORE),
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False))
        return 1

    lookbacks = [x.strip() for x in args.lookbacks.split(",") if x.strip()]
    neutrals = [x.strip() for x in args.neutrals.split(",") if x.strip()]
    oos_script = ROOT / "scripts" / "run_prophecy_lens_role_router_oos_gate_v1.py"
    tmp_dir = ART / "_logos_oos_sweep_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    best_hit = -1.0
    best_path: Path | None = None
    best_params: dict[str, Any] | None = None
    best_hit_any = -1.0
    best_hit_any_params: dict[str, Any] | None = None

    for lb in lookbacks:
        for nz in neutrals:
            out_path = tmp_dir / f"oos_lb{lb}_nz{nz.replace('.', 'p')}.json"
            cmd = [
                sys.executable,
                str(oos_script),
                "--score-json",
                str(args.score_json),
                "--sidecar-json",
                str(args.sidecar_json),
                "--btc-csv",
                str(args.btc_csv),
                "--target-instrument",
                str(args.target_instrument),
                "--oos-tail-days",
                str(args.oos_tail_days),
                "--month-lookback-grid",
                lb,
                "--neutral-size-grid",
                nz,
                "--gate-min-hit-rate",
                str(args.min_hit_rate),
                "--output",
                str(out_path),
            ]
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
            doc = _read(out_path)
            gate = doc.get("gate") if isinstance(doc.get("gate"), dict) else {}
            metrics = doc.get("oos_metrics") if isinstance(doc.get("oos_metrics"), dict) else {}
            hit = metrics.get("directional_hit_rate_active")
            try:
                h = float(hit)
            except (TypeError, ValueError):
                h = None
            go = bool(gate.get("go"))
            checks = gate.get("checks") if isinstance(gate.get("checks"), dict) else {}
            try:
                oos_ret = float(metrics.get("total_return"))
            except (TypeError, ValueError):
                oos_ret = None
            row = {
                "lookback": lb,
                "neutral": nz,
                "returncode": int(proc.returncode),
                "go": go,
                "hit": h,
                "oos_total_return": oos_ret,
                "gate_checks": checks,
                "status": gate.get("status"),
                "output": str(out_path),
                "best_train": doc.get("best_train_candidate"),
            }
            rows.append(row)
            if go and h is not None and h > best_hit:
                best_hit = h
                best_path = out_path
                best_params = {"lookback": lb, "neutral": nz}
            if h is not None and h > best_hit_any:
                best_hit_any = h
                best_hit_any_params = {
                    "lookback": lb,
                    "neutral": nz,
                    "go": go,
                    "oos_total_return": oos_ret,
                }

    promoted = False
    prev_hit_floor = -1.0
    suffix = f"{args.oos_tail_days}d"
    dest_252 = ART / f"prophecy_logos_revalidation_oos_gate_{suffix}_latest.json"
    prev_doc = _read(dest_252)
    prev_gate = prev_doc.get("gate") if isinstance(prev_doc.get("gate"), dict) else {}
    if prev_gate.get("go"):
        try:
            prev_hit_floor = float(
                (prev_doc.get("oos_metrics") or {}).get("directional_hit_rate_active")
            )
        except (TypeError, ValueError):
            prev_hit_floor = -1.0

    if (
        args.promote_if_better
        and best_path is not None
        and best_hit >= 0
        and best_hit > prev_hit_floor
    ):
        dest_252.write_bytes(best_path.read_bytes())
        from logos_oos_gate_promote_v1 import promote_best_logos_oos_gate

        promo = promote_best_logos_oos_gate(ART)
        promoted = bool(promo.get("promoted"))

    summary = {
        "schema": "logos_strict_oos_grid_sweep_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "target_instrument": str(args.target_instrument),
            "oos_tail_days": int(args.oos_tail_days),
            "lookbacks": lookbacks,
            "neutrals": neutrals,
        },
        "best": {
            "hit": best_hit if best_hit >= 0 else None,
            "params": best_params,
            "path": str(best_path) if best_path else None,
        },
        "best_by_hit": {
            "hit": best_hit_any if best_hit_any >= 0 else None,
            "params": best_hit_any_params,
        },
        "maturity_ssot_note_ko": "성숙도 D는 prophecy_logos_revalidation_oos_gate_latest(golden 0.534884) 유지. "
        "본 스윕은 신규 30y 패널 strict OOS 연구용이며 go=true만 promote-if-better 대상.",
        "maturity_d_threshold_hit_for_7_25": 0.55,
        "rows": rows,
        "promoted": promoted,
        "promote_prev_hit_floor": prev_hit_floor if prev_hit_floor >= 0 else None,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(args.out_json), "best_hit": summary["best"]["hit"], "promoted": promoted}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
