#!/usr/bin/env python3
"""Run small BTC-focused weight profile sweep for B-track hypothesis generator.

Produces:
- docs/final/artifacts/btc_weight_ab_sweep_latest.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_GENERATOR = ROOT / "scripts/generate_btrack_hypothesis_prophecy_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/btc_weight_ab_sweep_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _profile_weights(profile: str) -> dict[str, float]:
    # BTC-first profiles; sums to 1.0.
    m = {
        "btc_65": {"price": 0.65, "macro": 0.2, "news": 0.1, "myeongni_sasang": 0.05},
        "btc_70": {"price": 0.7, "macro": 0.15, "news": 0.1, "myeongni_sasang": 0.05},
        "btc_80": {"price": 0.8, "macro": 0.1, "news": 0.05, "myeongni_sasang": 0.05},
    }
    if profile not in m:
        raise ValueError(f"unknown profile: {profile}")
    return m[profile]


def _run_one(generator: Path, bundle: Path, score: Path, cfg: Path, out: Path) -> tuple[int, dict[str, Any]]:
    cp = subprocess.run(
        [
            sys.executable,
            str(generator),
            "--bundle",
            str(bundle),
            "--score-json",
            str(score),
            "--ensemble-config",
            str(cfg),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        return cp.returncode, {"stderr": cp.stderr[-2000:], "stdout": cp.stdout[-1000:]}
    doc = _load(out)
    pred = doc.get("prediction") if isinstance(doc.get("prediction"), dict) else {}
    meta = doc.get("runtime_meta") if isinstance(doc.get("runtime_meta"), dict) else {}
    guard = meta.get("btc_only_guard") if isinstance(meta.get("btc_only_guard"), dict) else {}
    return 0, {
        "instrument": pred.get("instrument"),
        "direction": pred.get("direction"),
        "confidence": pred.get("confidence"),
        "weighted_score": meta.get("weighted_score"),
        "guard_blocked": guard.get("blocked"),
    }


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profiles", default="btc_65,btc_70,btc_80")
    ap.add_argument("--config-json", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--generator", type=Path, default=DEFAULT_GENERATOR)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    base = _load(args.config_json)
    base_rules = base.get("rules") if isinstance(base.get("rules"), dict) else {}
    # Hard lock for BTC-only sweep.
    base_rules["price_instrument"] = "btc"
    base_rules["enforce_btc_only_guard"] = True
    base["rules"] = base_rules

    results: list[dict[str, Any]] = []
    profiles = [p.strip() for p in str(args.profiles).split(",") if p.strip()]
    with tempfile.TemporaryDirectory(prefix="btc_weight_sweep_") as td:
        tdp = Path(td)
        for p in profiles:
            cfg = dict(base)
            cfg["weights"] = _profile_weights(p)
            cfg_path = tdp / f"{p}_cfg.json"
            out_path = tdp / f"{p}_out.json"
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            code, rec = _run_one(args.generator, args.bundle_json, args.score_json, cfg_path, out_path)
            results.append(
                {
                    "profile": p,
                    "weights": cfg["weights"],
                    "ok": code == 0,
                    "result": rec,
                }
            )

    payload = {
        "schema": "btc_weight_ab_sweep_v1",
        "generated_at_utc": _utc_now(),
        "profiles": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
