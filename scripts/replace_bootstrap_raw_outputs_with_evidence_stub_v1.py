#!/usr/bin/env python3
"""Replace bootstrap-filled Athena raw outputs with deterministic evidence stubs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "docs" / "final" / "artifacts" / "vibe_runs_raw" / "athena_raw_outputs"
EXTERNAL_JSONL = ROOT / "docs" / "final" / "artifacts" / "vibe_external_inputs_latest.jsonl"

BOOTSTRAP_TAG = "auto_fill_codex_bootstrap"
STUB_TAG = "research_stub_evidence_v1"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def parse_slot_meta(path: Path) -> tuple[str | None, int | None]:
    m = re.match(r"^(prompt_\d{2})_run_(\d+)\.(?:md|txt)$", path.name, flags=re.IGNORECASE)
    if not m:
        return None, None
    return m.group(1).lower(), int(m.group(2))


def parse_existing_decision(text: str) -> str | None:
    upper = text.upper()
    for d in ("HOLD", "REDUCE", "WATCH"):
        if re.search(rf"\b{d}\b", upper):
            return d
    # crude Korean confidence patterns already handled elsewhere
    return None


def stable_float(seed: str, lo: float = 0.55, hi: float = 0.72) -> float:
    """Deterministic pseudo-float in [lo, hi] from seed."""
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    x = int.from_bytes(h[:8], "big") / float(2**64)
    return round(lo + (hi - lo) * x, 2)


def summarize_external(rows: list[dict[str, Any]]) -> dict[str, Any]:
    # Minimal deterministic aggregation for conservative shadow guidance.
    macro_stress = 0.0
    risk_off = 0.0
    crypto_risk = 0.0
    geo_stress = 0.0

    evidence_lines: list[str] = []
    for row in rows:
        bucket = str(row.get("bucket", ""))
        series = str(row.get("series", ""))
        value = row.get("value")
        direction = str(row.get("direction", "unknown"))
        conf = float(row.get("confidence", 0.7) or 0.7)
        line = f"- {bucket}/{series}: value={value} dir={direction} conf={conf}"
        evidence_lines.append(line)

        if bucket == "macro_rates_liquidity" and series in {"US10Y", "DXY"}:
            macro_stress += 0.15 * conf
        if bucket == "risk_sentiment_volatility" and series in {"VIX"}:
            risk_off += 0.20 * conf
        if bucket == "risk_sentiment_volatility" and series in {"CRYPTO_FGI"}:
            # High greed can imply elevated positioning risk (shadow heuristic).
            try:
                fgi = float(value)  # type: ignore[arg-type]
            except Exception:
                fgi = 50.0
            crypto_risk += max(0.0, (fgi - 50.0) / 50.0) * 0.15 * conf
        if bucket == "crypto_microstructure" and series in {"BTC_FUNDING_RATE", "BTC_OPEN_INTEREST"}:
            crypto_risk += 0.12 * conf
        if bucket == "geopolitical_event":
            geo_stress += float(value) * 0.25 * conf if isinstance(value, (int, float)) else 0.10 * conf

    score = macro_stress + risk_off + crypto_risk + geo_stress
    return {
        "macro_stress": macro_stress,
        "risk_off": risk_off,
        "crypto_risk": crypto_risk,
        "geo_stress": geo_stress,
        "aggregate_score": score,
        "evidence_lines": evidence_lines[:12],
    }


def decide_action(prompt_id: str, run_index: int, agg: dict[str, Any]) -> str:
    # Conservative defaults with mild variation by slot id for consistency testing.
    s = float(agg["aggregate_score"])
    seed = f"{prompt_id}:{run_index}:{s:.6f}"
    jitter = stable_float(seed, 0.0, 0.06)

    # Prompt-specific bias (research-only).
    if prompt_id == "prompt_03":
        s += 0.05
    if prompt_id == "prompt_02":
        s += 0.02

    thr_watch = 0.35 + jitter
    thr_reduce = 0.55 + jitter

    if s >= thr_reduce:
        return "REDUCE"
    if s >= thr_watch:
        return "WATCH"
    return "HOLD"


def confidence_for(decision: str, seed: str) -> float:
    if decision == "HOLD":
        return stable_float(seed + ":c", 0.58, 0.72)
    if decision == "WATCH":
        return stable_float(seed + ":c", 0.52, 0.66)
    return stable_float(seed + ":c", 0.50, 0.62)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-all-slots",
        action="store_true",
        help="Rewrite every prompt_XX_run_YY.(md|txt) slot in RAW_DIR (dangerous; use with care).",
    )
    args = parser.parse_args()

    external_rows = read_jsonl(EXTERNAL_JSONL)
    agg = summarize_external(external_rows)

    replaced = 0
    skipped = 0
    for path in sorted(RAW_DIR.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        is_bootstrap = BOOTSTRAP_TAG in text
        is_stub = STUB_TAG in text
        if not (is_bootstrap or is_stub or args.force_all_slots):
            skipped += 1
            continue

        prompt_id, run_index = parse_slot_meta(path)
        seed = f"{prompt_id or 'unknown'}:{run_index or 0}"

        # Prefer preserving an explicit decision if present and user didn't force everything blindly.
        existing = parse_existing_decision(text)
        if existing and not args.force_all_slots and not is_bootstrap:
            decision = existing
        else:
            decision = decide_action(prompt_id or "prompt_unknown", int(run_index or 0), agg)
        conf = confidence_for(decision, seed)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        evidence_block = "\n".join(agg["evidence_lines"]) if agg["evidence_lines"] else "- (no external rows parsed)"

        content = "\n".join(
            [
                f"# {path.name}",
                "",
                f"Generated (UTC): {now}",
                f"Stub: {STUB_TAG}",
                "",
                "Final Action: " + decision,
                f"Confidence: {conf:.2f}",
                "Risk Flags: [research_stub, evidence_summarized, no_live_price_targets]",
                "",
                "Evidence Inputs (Fact-Lock pointers):",
                f"- external_inputs_jsonl: docs/final/artifacts/vibe_external_inputs_latest.jsonl",
                "",
                "Evidence Summary (derived, deterministic):",
                f"- aggregate_score: {agg['aggregate_score']:.4f}",
                f"- macro_stress: {agg['macro_stress']:.4f}",
                f"- risk_off: {agg['risk_off']:.4f}",
                f"- crypto_risk: {agg['crypto_risk']:.4f}",
                f"- geo_stress: {agg['geo_stress']:.4f}",
                "",
                "External Rows (subset):",
                evidence_block,
                "",
                "Rationale:",
                "- Shadow-only heuristic maps external stress proxies to HOLD/WATCH/REDUCE with conservative bias.",
                "- Replace this stub with a real Athena answer when ready; remove stub markers after replacement.",
                "",
            ]
        )

        # Normalize slot filenames to .md for downstream tooling consistency.
        target_path = path
        if path.suffix.lower() == ".txt":
            md_path = path.with_suffix(".md")
            target_path = md_path

        target_path.write_text(content, encoding="utf-8")
        if target_path != path:
            try:
                path.unlink()
            except OSError:
                pass
        replaced += 1

    print(f"external_rows: {len(external_rows)}")
    print(f"replaced_files: {replaced}")
    print(f"skipped_files_not_targeted: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
