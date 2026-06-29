#!/usr/bin/env python3
"""Build schema-exact SFT rows from golden JSONL (strict instruction + engine JSON output)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDEN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl"
DEFAULT_OUT = ROOT / "data/training/myeongri_deterministic_lora_schema_exact_sft_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "reports/myeongri_schema_exact_sft_manifest_v1_latest.json"

_SHAPE_KEYS = {
    "resolution": (
        "birth_instant_utc",
        "iana_tz",
        "local_iso",
        "engine_inputs",
        "warnings",
        "meta",
    ),
    "full_saju": (
        "birth_info",
        "saju",
        "ilgan",
        "daewoon",
        "daewoon_qiyun_v1",
        "verification",
        "calculation_method",
        "note",
    ),
    "engine_inputs": ("year", "month", "day", "hour"),
    "saju": ("year", "month", "day", "hour"),
}


def _shape_line(label: str, obj: dict[str, Any], keys: tuple[str, ...]) -> str:
    present = [k for k in keys if k in obj]
    return f"{label}: " + ", ".join(present)


def _row_to_schema_exact_sft(row: dict[str, Any], *, reason: str) -> dict[str, Any]:
    utc = str(row.get("birth_instant_utc") or "").strip()
    tz = str(row.get("iana_tz") or "").strip()
    male = row.get("is_male")
    male_s = "unspecified (engine default false)" if male is None else ("true" if male else "false")
    exp = row.get("expected_result")
    if not isinstance(exp, dict):
        raise ValueError("expected_result must be object")

    res = exp.get("resolution") if isinstance(exp.get("resolution"), dict) else {}
    fs = exp.get("full_saju") if isinstance(exp.get("full_saju"), dict) else {}
    ei = res.get("engine_inputs") if isinstance(res.get("engine_inputs"), dict) else {}
    saju = fs.get("saju") if isinstance(fs.get("saju"), dict) else {}

    contract = "\n".join(
        [
            _shape_line("resolution", res, _SHAPE_KEYS["resolution"]),
            _shape_line("full_saju", fs, _SHAPE_KEYS["full_saju"]),
            _shape_line("resolution.engine_inputs", ei, _SHAPE_KEYS["engine_inputs"]),
            _shape_line("full_saju.saju", saju, _SHAPE_KEYS["saju"]),
        ]
    )

    instruction = (
        "STRICT deterministic myeongri task.\n"
        "Return ONLY one valid JSON object for schema saju_global_birth_result_v1.\n"
        "No markdown, no explanation, no extra keys, no trailing text.\n"
        "Do NOT emit narrative astrology fields (joseon_saju, myeongri text, age, constellation).\n"
        "Copy engine deterministic structure exactly (keys and nested shapes below).\n"
        f"{contract}\n"
        f"birth_instant_utc: {utc}\n"
        f"iana_tz: {tz}\n"
        f"is_male: {male_s}"
    )
    return {
        "sample_id": row.get("sample_id"),
        "split": row.get("split"),
        "hard_negative_reason": reason,
        "instruction": instruction,
        "output": json.dumps(exp, ensure_ascii=False, separators=(",", ":")),
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-jsonl", type=Path, default=DEFAULT_GOLDEN)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--limit", type=int, default=0, help="Max rows (0=all)")
    args = ap.parse_args()

    if not args.golden_jsonl.is_file():
        raise SystemExit(f"missing golden: {args.golden_jsonl}")

    golden_rows = _load_jsonl(args.golden_jsonl)
    if args.limit > 0:
        golden_rows = golden_rows[: args.limit]

    out_rows = [_row_to_schema_exact_sft(r, reason="schema_exact_engine_shape") for r in golden_rows]

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "schema": "myeongri_schema_exact_sft_manifest_v1",
        "golden_jsonl": str(args.golden_jsonl).replace("\\", "/"),
        "out_jsonl": str(args.out_jsonl).replace("\\", "/"),
        "counts": {"written_rows": len(out_rows)},
        "track_wall": {
            "research_only": True,
            "a_track_auto_promotion": False,
            "live_trading": False,
        },
    }
    args.manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out_jsonl": str(args.out_jsonl), "rows": len(out_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
