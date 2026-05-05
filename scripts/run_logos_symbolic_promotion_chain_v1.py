#!/usr/bin/env python3
"""One-shot chain: Logos symbolic backtest + promotion gate.

Defaults to fixture paths when runtime paths are not supplied.
This keeps the chain executable in clean clones while allowing real-path override.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

BACKTEST_SCRIPT = ROOT / "scripts" / "run_logos_symbolic_event_backtest_v1.py"
GATE_SCRIPT = ROOT / "scripts" / "check_logos_symbolic_event_promotion_gate_v1.py"

DEFAULT_NEWS = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_latest.jsonl"
DEFAULT_LABELS = ROOT / "docs" / "final" / "artifacts" / "direction_label_bar_v1_latest.jsonl"
DEFAULT_MAP = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_map_v1.json"

DEFAULT_BACKTEST_JSON = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_backtest_latest.json"
DEFAULT_BACKTEST_CSV = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_backtest_rows_latest.csv"
DEFAULT_GATE_JSON = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_promotion_gate_latest.json"
DEFAULT_AUTO_LABELS = ROOT / "docs" / "final" / "artifacts" / "direction_label_bar_v1_latest.jsonl"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_fixture_path(path: Path) -> bool:
    parts = [p.lower() for p in path.parts]
    return "tests" in parts and "fixtures" in parts


def _jsonl_schema_version(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                sv = obj.get("schema_version")
                return str(sv) if isinstance(sv, str) else None
            return None
    except Exception:
        return None
    return None


def _discover_latest_path(
    candidates: list[Path],
    globs: list[str],
    *,
    allow_fixtures: bool,
    required_schema_version: str,
) -> Path | None:
    for p in candidates:
        if (
            p.is_file()
            and (allow_fixtures or not _is_fixture_path(p))
            and _jsonl_schema_version(p) == required_schema_version
        ):
            return p
    for pat in globs:
        matches = sorted(ROOT.glob(pat), key=lambda x: x.stat().st_mtime, reverse=True)
        for m in matches:
            if (
                m.is_file()
                and (allow_fixtures or not _is_fixture_path(m))
                and _jsonl_schema_version(m) == required_schema_version
            ):
                return m
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--labels-jsonl", type=Path, default=DEFAULT_LABELS)
    ap.add_argument("--symbol-map-json", type=Path, default=DEFAULT_MAP)
    ap.add_argument("--instrument-id", type=str, default="KOSPI")
    ap.add_argument("--horizon", type=str, default="1d")
    ap.add_argument("--neutral-score-band", type=float, default=0.25)
    ap.add_argument(
        "--synthetic-source-ids",
        type=str,
        default="label_guided_seed,manual_seed",
        help="Comma-separated source_id values treated as synthetic/seed.",
    )
    ap.add_argument("--backtest-json", type=Path, default=DEFAULT_BACKTEST_JSON)
    ap.add_argument("--backtest-csv", type=Path, default=DEFAULT_BACKTEST_CSV)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE_JSON)
    ap.add_argument("--min-samples", type=int, default=30)
    ap.add_argument("--min-hit-rate", type=float, default=0.53)
    ap.add_argument("--min-symbol-coverage", type=int, default=3)
    ap.add_argument("--min-holdout-samples", type=int, default=0)
    ap.add_argument("--min-holdout-hit-rate", type=float, default=0.0)
    ap.add_argument("--min-non-synthetic-samples", type=int, default=0)
    ap.add_argument(
        "--allow-fixture-fallback",
        action="store_true",
        help="Allow tests/fixtures fallback during input auto-discovery.",
    )
    ap.add_argument(
        "--auto-build-labels-if-missing",
        action="store_true",
        default=True,
        help="When labels JSONL is missing, build direction_label_bar_v1 from KOSPI OHLCV if available.",
    )
    args = ap.parse_args()

    news_jsonl = args.news_jsonl
    labels_jsonl = args.labels_jsonl
    auto_discovery: dict[str, Any] = {"news_used_autodiscovery": False, "labels_used_autodiscovery": False}

    if not news_jsonl.is_file():
        discovered_news = _discover_latest_path(
            candidates=[
                ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_latest.jsonl",
                ROOT / "reports" / "news_observation_v1_latest.jsonl",
            ],
            globs=[
                "docs/final/artifacts/**/*news*observation*latest*.jsonl",
                "reports/**/*news*observation*latest*.jsonl",
                "reports/**/*news*.jsonl",
            ],
            allow_fixtures=bool(args.allow_fixture_fallback),
            required_schema_version="news_observation_v1",
        )
        if discovered_news is not None:
            news_jsonl = discovered_news
            auto_discovery["news_used_autodiscovery"] = True
    if not labels_jsonl.is_file():
        discovered_labels = _discover_latest_path(
            candidates=[
                ROOT / "docs" / "final" / "artifacts" / "direction_label_bar_v1_latest.jsonl",
                ROOT / "reports" / "direction_label_bar_v1_latest.jsonl",
            ],
            globs=[
                "docs/final/artifacts/**/*direction*label*latest*.jsonl",
                "reports/**/*direction*label*latest*.jsonl",
                "reports/**/*label*.jsonl",
            ],
            allow_fixtures=bool(args.allow_fixture_fallback),
            required_schema_version="direction_label_bar_v1",
        )
        if discovered_labels is not None:
            labels_jsonl = discovered_labels
            auto_discovery["labels_used_autodiscovery"] = True

    if not labels_jsonl.is_file():
        if args.auto_build_labels_if_missing and DEFAULT_KOSPI_CSV.is_file():
            build_labels_script = ROOT / "scripts" / "build_direction_label_bar_jsonl_from_ohlcv_v1.py"
            if build_labels_script.is_file():
                build_cmd = [
                    sys.executable,
                    str(build_labels_script),
                    "--csv",
                    str(DEFAULT_KOSPI_CSV),
                    "--instrument-id",
                    str(args.instrument_id),
                    "--horizon",
                    str(args.horizon),
                    "--output",
                    str(DEFAULT_AUTO_LABELS),
                    "--validate-labels",
                ]
                built = _run(build_cmd)
                if built.returncode == 0 and DEFAULT_AUTO_LABELS.is_file():
                    labels_jsonl = DEFAULT_AUTO_LABELS
                    auto_discovery["labels_built_from_ohlcv"] = True
                else:
                    print(built.stdout)
                    print(built.stderr, file=sys.stderr)
                    raise SystemExit("Failed to auto-build direction labels from OHLCV.")
        if not labels_jsonl.is_file():
            raise SystemExit(f"Missing --labels-jsonl: {labels_jsonl}")
    if not news_jsonl.is_file():
        hint = (
            'Missing --news-jsonl. Build one via: '
            'py scripts/build_news_observation_jsonl_from_csv_v1.py '
            '--input <news.csv> --output docs/final/artifacts/news_observation_v1_latest.jsonl --validate'
        )
        raise SystemExit(f"{hint}\nresolved path: {news_jsonl}")
    if not args.symbol_map_json.is_file():
        raise SystemExit(f"Missing --symbol-map-json: {args.symbol_map_json}")

    bt_cmd = [
        sys.executable,
        str(BACKTEST_SCRIPT),
        "--news-jsonl",
        str(news_jsonl),
        "--labels-jsonl",
        str(labels_jsonl),
        "--symbol-map-json",
        str(args.symbol_map_json),
        "--instrument-id",
        str(args.instrument_id),
        "--horizon",
        str(args.horizon),
        "--neutral-score-band",
        str(args.neutral_score_band),
        "--synthetic-source-ids",
        str(args.synthetic_source_ids),
        "--output-json",
        str(args.backtest_json),
        "--output-csv",
        str(args.backtest_csv),
    ]
    bt = _run(bt_cmd)
    if bt.returncode != 0:
        print(bt.stdout)
        print(bt.stderr, file=sys.stderr)
        raise SystemExit(bt.returncode)

    gate_cmd = [
        sys.executable,
        str(GATE_SCRIPT),
        "--backtest-json",
        str(args.backtest_json),
        "--out",
        str(args.gate_json),
        "--min-samples",
        str(args.min_samples),
        "--min-hit-rate",
        str(args.min_hit_rate),
        "--min-symbol-coverage",
        str(args.min_symbol_coverage),
        "--min-holdout-samples",
        str(args.min_holdout_samples),
        "--min-holdout-hit-rate",
        str(args.min_holdout_hit_rate),
        "--min-non-synthetic-samples",
        str(args.min_non_synthetic_samples),
    ]
    gate = _run(gate_cmd)
    if gate.returncode != 0:
        print(gate.stdout)
        print(gate.stderr, file=sys.stderr)
        raise SystemExit(gate.returncode)

    bt_doc = _load_json(args.backtest_json)
    gate_doc = _load_json(args.gate_json)
    gate_doc["input_refs"] = {
        "news_jsonl": str(news_jsonl).replace("\\", "/"),
        "labels_jsonl": str(labels_jsonl).replace("\\", "/"),
        "symbol_map_json": str(args.symbol_map_json).replace("\\", "/"),
    }
    args.gate_json.write_text(json.dumps(gate_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {
        "ok": True,
        "schema": "logos_symbolic_promotion_chain_v1",
        "backtest_hit_rate": (bt_doc.get("summary") or {}).get("hit_rate"),
        "backtest_n": (bt_doc.get("summary") or {}).get("n_evaluated"),
        "decision": gate_doc.get("decision"),
        "all_pass": gate_doc.get("all_pass"),
        "auto_discovery": auto_discovery,
        "outputs": {
            "backtest_json": str(args.backtest_json).replace("\\", "/"),
            "backtest_csv": str(args.backtest_csv).replace("\\", "/"),
            "gate_json": str(args.gate_json).replace("\\", "/"),
        },
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

