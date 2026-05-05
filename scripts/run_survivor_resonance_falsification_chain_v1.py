# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.6, M:0.6}
# Balance: 88
# Purpose: Run proxy/real survivor resonance backtests and emit comparison + gate decisions.
# Keywords: chain, proxy, real, backtest, falsification, gate
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

DEFAULT_PROXY_RESONANCE_JSONL = ART / "global_atom_survivor_resonance_daily_latest.jsonl"
DEFAULT_REAL_RESONANCE_JSONL = ART / "global_atom_survivor_resonance_daily_real_latest.jsonl"
DEFAULT_PROXY_BACKTEST_OUT = ART / "btrack_survivor_crash_correlation_backtest_proxy_latest.json"
DEFAULT_REAL_BACKTEST_OUT = ART / "btrack_survivor_crash_correlation_backtest_real_latest.json"
DEFAULT_PROXY_GATE_OUT = ART / "btrack_survivor_crash_falsification_gate_proxy_latest.json"
DEFAULT_REAL_GATE_OUT = ART / "btrack_survivor_crash_falsification_gate_real_latest.json"
DEFAULT_SUMMARY_OUT = ART / "btrack_survivor_resonance_falsification_chain_latest.json"
DEFAULT_TUNING_JSON = ART / "btrack_survivor_real_resonance_tuning_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str]) -> dict[str, Any]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": int(p.returncode),
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _extract_best_weights(tuning_doc: dict[str, Any]) -> dict[str, float] | None:
    best = tuning_doc.get("best") if isinstance(tuning_doc.get("best"), dict) else {}
    weights = best.get("weights") if isinstance(best.get("weights"), dict) else {}
    if not weights:
        return None
    try:
        return {
            "w_candidate": float(weights.get("w_candidate")),
            "w_flow": float(weights.get("w_flow")),
            "w_temporal": float(weights.get("w_temporal")),
        }
    except (TypeError, ValueError):
        return None


def _extract_key_metrics(backtest_doc: dict[str, Any]) -> dict[str, Any]:
    analysis = backtest_doc.get("analysis") if isinstance(backtest_doc.get("analysis"), dict) else {}
    out: dict[str, Any] = {}
    for asset in ("kospi", "btc"):
        a = analysis.get(asset) if isinstance(analysis.get(asset), dict) else {}
        best = a.get("best_abs_corr_row") if isinstance(a.get("best_abs_corr_row"), dict) else {}
        out[asset] = {
            "best_lag_days": best.get("lag_days"),
            "best_return_corr": best.get("return_corr"),
            "best_return_corr_n": best.get("return_n"),
            "best_return_corr_permutation_pvalue": a.get("best_return_corr_permutation_pvalue"),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Proxy/real split falsification chain for survivor resonance.")
    ap.add_argument("--proxy-resonance-jsonl", type=Path, default=DEFAULT_PROXY_RESONANCE_JSONL)
    ap.add_argument("--real-resonance-jsonl", type=Path, default=DEFAULT_REAL_RESONANCE_JSONL)
    ap.add_argument("--proxy-backtest-out", type=Path, default=DEFAULT_PROXY_BACKTEST_OUT)
    ap.add_argument("--real-backtest-out", type=Path, default=DEFAULT_REAL_BACKTEST_OUT)
    ap.add_argument("--proxy-gate-out", type=Path, default=DEFAULT_PROXY_GATE_OUT)
    ap.add_argument("--real-gate-out", type=Path, default=DEFAULT_REAL_GATE_OUT)
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY_OUT)
    ap.add_argument("--tuning-json", type=Path, default=DEFAULT_TUNING_JSON)
    ap.add_argument("--apply-best-tuned-weights", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--min-abs-corr", type=float, default=0.5)
    ap.add_argument("--max-pvalue", type=float, default=0.05)
    ap.add_argument("--min-n", type=int, default=250)
    args = ap.parse_args()

    runs: dict[str, Any] = {}
    notes: list[str] = []

    # Proxy path (expected to exist after builder).
    proxy_backtest_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_btrack_survivor_crash_correlation_backtest_v1.py"),
        "--resonance-jsonl",
        str(args.proxy_resonance_jsonl),
        "--output",
        str(args.proxy_backtest_out),
    ]
    runs["proxy_backtest"] = _run(proxy_backtest_cmd)
    proxy_gate_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "check_survivor_crash_falsification_gate_v1.py"),
        "--backtest-json",
        str(args.proxy_backtest_out),
        "--output",
        str(args.proxy_gate_out),
        "--min-abs-corr",
        str(args.min_abs_corr),
        "--max-pvalue",
        str(args.max_pvalue),
        "--min-n",
        str(args.min_n),
    ]
    runs["proxy_gate"] = _run(proxy_gate_cmd)

    # Real path (optional; if absent, hold by contract).
    real_available = args.real_resonance_jsonl.is_file()
    if real_available:
        applied_weights = None
        if args.apply_best_tuned_weights and args.tuning_json.is_file():
            tuning_doc = _read_json(args.tuning_json)
            applied_weights = _extract_best_weights(tuning_doc)
            if applied_weights is not None:
                rebuild_real_cmd = [
                    sys.executable,
                    str(ROOT / "scripts" / "build_global_atom_survivor_resonance_daily_real_v1.py"),
                    "--w-candidate",
                    str(applied_weights["w_candidate"]),
                    "--w-flow",
                    str(applied_weights["w_flow"]),
                    "--w-temporal",
                    str(applied_weights["w_temporal"]),
                    "--output-jsonl",
                    str(args.real_resonance_jsonl),
                ]
                runs["real_rebuild_with_tuned_weights"] = _run(rebuild_real_cmd)
            else:
                notes.append("tuning_json_present_but_best_weights_unreadable")
        elif args.apply_best_tuned_weights and not args.tuning_json.is_file():
            notes.append("tuning_json_missing_skip_weight_apply")

        real_backtest_cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_btrack_survivor_crash_correlation_backtest_v1.py"),
            "--resonance-jsonl",
            str(args.real_resonance_jsonl),
            "--output",
            str(args.real_backtest_out),
        ]
        runs["real_backtest"] = _run(real_backtest_cmd)
        real_gate_cmd = [
            sys.executable,
            str(ROOT / "scripts" / "check_survivor_crash_falsification_gate_v1.py"),
            "--backtest-json",
            str(args.real_backtest_out),
            "--output",
            str(args.real_gate_out),
            "--min-abs-corr",
            str(args.min_abs_corr),
            "--max-pvalue",
            str(args.max_pvalue),
            "--min-n",
            str(args.min_n),
        ]
        runs["real_gate"] = _run(real_gate_cmd)
    else:
        notes.append("real_resonance_jsonl_missing")

    proxy_backtest_doc = _read_json(args.proxy_backtest_out)
    proxy_gate_doc = _read_json(args.proxy_gate_out)
    real_backtest_doc = _read_json(args.real_backtest_out) if real_available else {}
    real_gate_doc = _read_json(args.real_gate_out) if real_available else {}

    if real_available:
        final_decision = (real_gate_doc.get("result") or {}).get("decision") or "HOLD_RESEARCH_ONLY"
    else:
        final_decision = "HOLD_RESEARCH_ONLY"

    summary = {
        "schema": "btrack_survivor_resonance_falsification_chain_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "thresholds": {
            "min_abs_corr": float(args.min_abs_corr),
            "max_pvalue": float(args.max_pvalue),
            "min_n": int(args.min_n),
        },
        "inputs": {
            "proxy_resonance_jsonl": str(args.proxy_resonance_jsonl),
            "real_resonance_jsonl": str(args.real_resonance_jsonl),
            "real_resonance_available": real_available,
            "apply_best_tuned_weights": bool(args.apply_best_tuned_weights),
            "tuning_json": str(args.tuning_json),
        },
        "proxy": {
            "backtest_path": str(args.proxy_backtest_out),
            "gate_path": str(args.proxy_gate_out),
            "metrics": _extract_key_metrics(proxy_backtest_doc),
            "gate_decision": (proxy_gate_doc.get("result") or {}).get("decision"),
        },
        "real": {
            "backtest_path": str(args.real_backtest_out) if real_available else None,
            "gate_path": str(args.real_gate_out) if real_available else None,
            "metrics": _extract_key_metrics(real_backtest_doc) if real_available else None,
            "gate_decision": (real_gate_doc.get("result") or {}).get("decision") if real_available else None,
        },
        "runs": runs,
        "notes": notes,
        "result": {
            "final_decision": final_decision,
            "decision_policy": "real_signal_required_for_go; if missing -> HOLD_RESEARCH_ONLY",
        },
    }

    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.summary_out}")
    print(f"final_decision={final_decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
