# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.85, L:0.85, K:0.5, M:0.65}
# Balance: 85
# Purpose: Sync workspace biblical-lane gate artifacts into bitcoin-trading memory hook for BTC bot.
# Keywords: bitcoin, biblical, hook, gate, BTCUSDT
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
ART = REPO / "docs" / "final" / "artifacts"
DEFAULT_PROPHECY = ART / "kospi_biblical_prophecy_output_v2_latest.json"
DEFAULT_STATUS = ART / "kospi_biblical_single_lane_stability_status_latest.json"
DEFAULT_EXPLAINABLE = ART / "general_prophecy_explainable_latest.json"
DEFAULT_OUT = REPO / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops" / "biblical_single_lane_trading_hook_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _artifact_rel_path(p: Path) -> str:
    """Repo-relative posix path for portable hook JSON (no drive-letter literals)."""
    try:
        return p.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def merge_general_prophecy_explainable_hook(
    hook: dict[str, Any],
    explainable_json: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """
    Inject reference_only_extensions.general_prophecy_explainable for crypto_nitro_live_trader
    (_compute_general_explainable_soft_influence). Hard gates unchanged; caps only when enabled.
    """
    root = repo_root or REPO
    explainable_json = explainable_json.resolve()
    if not explainable_json.is_file():
        return hook
    try:
        rel = explainable_json.relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = explainable_json.as_posix()

    sa = dict(hook.get("source_artifacts") or {})
    sa["general_prophecy_explainable"] = rel
    hook["source_artifacts"] = sa
    ref_ext = dict(hook.get("reference_only_extensions") or {})
    ref_ext["general_prophecy_explainable"] = {
        "enabled": True,
        "reference_only": True,
        "must_not_trigger_orders": True,
        "source_artifact": rel,
    }
    hook["reference_only_extensions"] = ref_ext
    return hook


def build_hook(
    prophecy: dict[str, Any],
    status: dict[str, Any],
    instrument: str,
) -> dict[str, Any]:
    lt = status.get("live_trading") if isinstance(status.get("live_trading"), dict) else {}
    if not lt and isinstance(prophecy.get("live_trading"), dict):
        lt = prophecy["live_trading"]

    base = prophecy.get("prophecy", {}).get("base_scenario", {}) or {}
    return {
        "schema_version": "biblical_single_lane_trading_hook_v1",
        "generated_at_utc": _now(),
        "instrument": instrument,
        "market": "BTC",
        "note": (
            "Evidence is produced by the workspace biblical single-lane pipeline (KOSPI-indexed); "
            "this hook maps gate state + bias snapshot for the BTC daemon. Not a price forecast."
        ),
        "source_artifacts": {
            "prophecy_v2": _artifact_rel_path(DEFAULT_PROPHECY),
            "stability_status": _artifact_rel_path(DEFAULT_STATUS),
        },
        "live_trading": {
            "lane": str(lt.get("lane", "biblical_only")),
            "phase": str(lt.get("phase", "research")),
            "allowed": bool(lt.get("allowed", False)),
            "reasons_if_blocked": list(lt.get("reasons_if_blocked", [])),
            "policy": str(
                lt.get(
                    "policy",
                    "Biblical lane only; broker path separate; use BIBLICAL_SINGLE_LANE_GATE_MODE.",
                )
            ),
        },
        "prophecy_snapshot": {
            "direction_bias": str(base.get("direction_bias", "neutral")),
            "confidence": float(base.get("confidence", 0.0) or 0.0),
            "regime_label": str(base.get("regime_label", "")),
        },
        "operator_brief": prophecy.get("operator_brief", {}),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync biblical lane hook into bitcoin-trading memory")
    ap.add_argument("--prophecy-json", type=Path, default=DEFAULT_PROPHECY)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--instrument",
        default=os.getenv("BIBLICAL_LANE_INSTRUMENT", "BTCUSDT"),
        help="Trading symbol label for the hook (default BTCUSDT or env BIBLICAL_LANE_INSTRUMENT)",
    )
    ap.add_argument(
        "--explainable-json",
        type=Path,
        default=None,
        help=(
            "General prophecy explainable artifact (default: docs/final/artifacts/general_prophecy_explainable_latest.json "
            "when present). Ignored with --no-explainable-extension."
        ),
    )
    ap.add_argument(
        "--no-explainable-extension",
        action="store_true",
        help="Do not inject reference_only_extensions.general_prophecy_explainable.",
    )
    args = ap.parse_args()

    if not args.prophecy_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing prophecy: {args.prophecy_json}"}, ensure_ascii=False))
        return 2
    if not args.status_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing status: {args.status_json}"}, ensure_ascii=False))
        return 2

    prophecy = _load(args.prophecy_json)
    status = _load(args.status_json)
    hook = build_hook(prophecy, status, str(args.instrument).strip() or "BTCUSDT")

    explainable_merge_info: dict[str, Any] = {"applied": False}
    if not args.no_explainable_extension:
        cand = args.explainable_json if args.explainable_json is not None else DEFAULT_EXPLAINABLE
        cand = cand.resolve()
        explicit = args.explainable_json is not None
        if explicit and not cand.is_file():
            print(json.dumps({"ok": False, "error": f"missing explainable-json: {cand}"}, ensure_ascii=False))
            return 2
        if cand.is_file():
            merge_general_prophecy_explainable_hook(hook, cand)
            explainable_merge_info = {"applied": True, "path": str(cand)}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(hook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out.resolve()),
                "allowed": hook["live_trading"]["allowed"],
                "general_prophecy_explainable": explainable_merge_info,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
