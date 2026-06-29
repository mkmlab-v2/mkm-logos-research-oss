#!/usr/bin/env python3
"""A/B: v2b max(panel,global) vs v2b_strict per-row density gates (research-only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"

PROFILES: dict[str, dict[str, Path]] = {
    "timeseries_v2": {
        "panel": ART / "btrack_31k41k_daily_anchor_panel_v1_latest.json",
        "eval_v2b": ART / "btrack_31k41k_prophecy_shadow_eval_v2b_latest.json",
        "eval_strict": ART / "btrack_31k41k_prophecy_shadow_eval_v2b_strict_latest.json",
        "fold_v2b": ART / "btrack_31k41k_prophecy_shadow_fold_stability_v1_latest.json",
        "fold_strict": ART / "btrack_31k41k_prophecy_shadow_fold_stability_v2b_strict_v1_latest.json",
        "out": ART / "btrack_31k41k_shadow_v2b_ab_v1_latest.json",
    },
    "contrast_zero_density": {
        "panel": ART / "btrack_31k41k_daily_anchor_panel_contrast_zero_v1_latest.json",
        "eval_v2b": ART / "btrack_31k41k_prophecy_shadow_eval_v2b_contrast_zero_latest.json",
        "eval_strict": ART / "btrack_31k41k_prophecy_shadow_eval_v2b_strict_contrast_zero_latest.json",
        "fold_v2b": ART / "btrack_31k41k_prophecy_shadow_fold_stability_v2b_contrast_zero_latest.json",
        "fold_strict": ART / "btrack_31k41k_prophecy_shadow_fold_stability_v2b_strict_contrast_zero_latest.json",
        "out": ART / "btrack_31k41k_shadow_v2b_ab_contrast_zero_v1_latest.json",
    },
    "static_global_proxy": {
        "panel": ART / "btrack_31k41k_daily_anchor_panel_static_proxy_v1_latest.json",
        "eval_v2b": ART / "btrack_31k41k_prophecy_shadow_eval_v2b_static_proxy_latest.json",
        "eval_strict": ART / "btrack_31k41k_prophecy_shadow_eval_v2b_strict_static_proxy_latest.json",
        "fold_v2b": ART / "btrack_31k41k_prophecy_shadow_fold_stability_v2b_static_proxy_latest.json",
        "fold_strict": ART / "btrack_31k41k_prophecy_shadow_fold_stability_v2b_strict_static_proxy_latest.json",
        "out": ART / "btrack_31k41k_shadow_v2b_ab_static_proxy_v1_latest.json",
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_py(script_rel: str, *argv: str) -> int:
    cmd = [sys.executable, str(ROOT / script_rel), *argv]
    print("RUN:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def _eval_summary(doc: dict[str, Any]) -> dict[str, Any]:
    sp = doc.get("shadow_probe") if isinstance(doc.get("shadow_probe"), dict) else {}
    ps = doc.get("panel_summary") if isinstance(doc.get("panel_summary"), dict) else {}
    return {
        "schema": doc.get("schema"),
        "delta_hit_rate": sp.get("delta_hit_rate"),
        "overlay_applied_count": sp.get("overlay_applied_count"),
        "overlay_applied_fraction": sp.get("overlay_applied_fraction"),
        "panel_merge_policy": (doc.get("control_flags") or {}).get("panel_merge_policy"),
        "per_row_density_min": ps.get("per_row_density_min"),
        "per_row_density_max": ps.get("per_row_density_max"),
    }


def _fold_summary(doc: dict[str, Any]) -> dict[str, Any]:
    pooled = doc.get("pooled_panel") if isinstance(doc.get("pooled_panel"), dict) else {}
    agg = doc.get("aggregates") if isinstance(doc.get("aggregates"), dict) else {}
    checks = doc.get("checks") if isinstance(doc.get("checks"), dict) else {}
    return {
        "pooled_delta_hit_rate": pooled.get("delta_hit_rate"),
        "worst_fold_delta": agg.get("worst_fold_delta"),
        "positive_delta_folds": agg.get("positive_delta_folds"),
        "stability_status": (doc.get("summary") or {}).get("status"),
        "stability_not_worse": checks.get("stability_not_worse"),
    }


def _build_panel(profile: str, paths: dict[str, Path]) -> int:
    panel = paths["panel"]
    if profile == "timeseries_v2":
        return _run_py(
            "scripts/build_btrack_31k41k_daily_anchor_panel_v1.py",
            "--feature-mode",
            "timeseries_v2",
            "--rolling-sample-size",
            "256",
            "--out-json",
            str(panel),
        )
    if profile == "contrast_zero_density":
        return _run_py(
            "scripts/build_btrack_31k41k_daily_anchor_panel_v1.py",
            "--feature-mode",
            "timeseries_v2",
            "--rolling-sample-size",
            "256",
            "--per-row-density-scale",
            "0",
            "--out-json",
            str(panel),
        )
    if profile == "static_global_proxy":
        return _run_py(
            "scripts/build_btrack_31k41k_daily_anchor_panel_v1.py",
            "--feature-mode",
            "static_global_proxy",
            "--out-json",
            str(panel),
        )
    raise SystemExit(f"unknown profile: {profile}")


def _run_profile(profile: str, paths: dict[str, Path], skip_rerun: bool) -> dict[str, Any]:
    if not skip_rerun:
        rc = _build_panel(profile, paths)
        if rc != 0:
            raise SystemExit(rc)
        panel = paths["panel"]
        for overlay, eval_out in (("v2b", paths["eval_v2b"]), ("v2b_strict", paths["eval_strict"])):
            rc = _run_py(
                "scripts/run_btrack_31k41k_prophecy_shadow_eval_v1.py",
                "--overlay-version",
                overlay,
                "--panel-json",
                str(panel),
                "--out-json",
                str(eval_out),
            )
            if rc not in (0, 1):
                raise SystemExit(rc)
        for overlay, fold_out in (("v2b", paths["fold_v2b"]), ("v2b_strict", paths["fold_strict"])):
            rc = _run_py(
                "scripts/run_btrack_31k41k_prophecy_shadow_fold_stability_v1.py",
                "--overlay-version",
                overlay,
                "--panel-json",
                str(panel),
                "--out-json",
                str(fold_out),
            )
            if rc not in (0, 1):
                raise SystemExit(rc)

    eval_v2b = _read_json(paths["eval_v2b"])
    eval_strict = _read_json(paths["eval_strict"])
    fold_v2b = _read_json(paths["fold_v2b"])
    fold_strict = _read_json(paths["fold_strict"])

    v2b_delta = float((eval_v2b.get("shadow_probe") or {}).get("delta_hit_rate") or 0.0)
    strict_delta = float((eval_strict.get("shadow_probe") or {}).get("delta_hit_rate") or 0.0)
    v2b_overlay = int((eval_v2b.get("shadow_probe") or {}).get("overlay_applied_count") or 0)
    strict_overlay = int((eval_strict.get("shadow_probe") or {}).get("overlay_applied_count") or 0)

    panel_doc = _read_json(paths["panel"])
    return {
        "panel_profile": profile,
        "panel_json": str(paths["panel"]),
        "panel_feature_mode": panel_doc.get("feature_mode"),
        "panel_inputs": panel_doc.get("inputs") if isinstance(panel_doc.get("inputs"), dict) else {},
        "variants": {
            "v2b_max_merge": {
                "eval_json": str(paths["eval_v2b"]),
                "fold_json": str(paths["fold_v2b"]),
                "eval": _eval_summary(eval_v2b),
                "fold": _fold_summary(fold_v2b),
            },
            "v2b_strict_per_row": {
                "eval_json": str(paths["eval_strict"]),
                "fold_json": str(paths["fold_strict"]),
                "eval": _eval_summary(eval_strict),
                "fold": _fold_summary(fold_strict),
            },
        },
        "comparison": {
            "delta_hit_rate_diff_strict_minus_max": round(strict_delta - v2b_delta, 6),
            "overlay_count_diff_strict_minus_max": strict_overlay - v2b_overlay,
            "strict_reduces_overlay_vs_max": strict_overlay < v2b_overlay,
            "interpretation": (
                "contrast_zero_density: per-row density forced to 0; max merge should keep "
                "global density for gates. timeseries_v2: per-row usually exceeds global. "
                "static_global_proxy: per-row equals global; expect no merge difference."
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--profile",
        choices=tuple(PROFILES.keys()),
        default="timeseries_v2",
        help="Panel/eval artifact set (default: timeseries_v2).",
    )
    ap.add_argument(
        "--run-all-profiles",
        action="store_true",
        help="Run timeseries_v2, contrast_zero_density, static_global_proxy sequentially.",
    )
    ap.add_argument("--skip-rerun", action="store_true", help="Only compare existing artifacts.")
    args = ap.parse_args()

    if args.run_all_profiles:
        profiles_out: dict[str, Any] = {}
        for name in PROFILES:
            print(f"\n=== profile: {name} ===")
            profiles_out[name] = _run_profile(name, PROFILES[name], args.skip_rerun)
        combined = {
            "schema": "btrack_31k41k_shadow_v2b_ab_multi_v1",
            "generated_at_utc": _iso_now(),
            "hypothesis_tier": "B",
            "research_only": True,
            "non_gating": True,
            "profiles": profiles_out,
        }
        out_path = ART / "btrack_31k41k_shadow_v2b_ab_multi_v1_latest.json"
        out_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {out_path}")
        if not args.skip_rerun:
            _build_panel("timeseries_v2", PROFILES["timeseries_v2"])
        return 0

    paths = PROFILES[args.profile]
    block = _run_profile(args.profile, paths, args.skip_rerun)

    out = {
        "schema": "btrack_31k41k_shadow_v2b_ab_v1",
        "generated_at_utc": _iso_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        **block,
    }

    paths["out"].parent.mkdir(parents=True, exist_ok=True)
    paths["out"].write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {paths['out']}")
    cmp_ = block["comparison"]
    print(
        f"profile={args.profile} v2b_delta={block['variants']['v2b_max_merge']['eval']['delta_hit_rate']} "
        f"strict_delta={block['variants']['v2b_strict_per_row']['eval']['delta_hit_rate']} "
        f"overlay_diff={cmp_['overlay_count_diff_strict_minus_max']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
