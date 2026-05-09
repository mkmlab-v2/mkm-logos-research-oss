# -*- coding: utf-8 -*-
"""JSONL 배치: 각 행을 CDS 페이로드로 보내 `km_physician_cds_assist_envelope_v1` 봉투로 조립·검증.

입력 행 형식(택1):
- 평면: `{"id":"...", "clinical_question":..., "evidence_assessment":...}` — `id`/`sample_id`/`row_id`는 페이로드에서 제외.
- 래핑: `{"id":"...", "payload": { ...허용 필드만... }}`

출력 행: `{"id":"...", "ok": true, "envelope": {...}}` 또는 `{"id":"...", "ok": false, "error": "..."}`

SSOT: `scripts/build_km_physician_cds_assist_envelope_v1.py`, 스키마 `docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json`
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_builder():
    path = ROOT / "scripts" / "build_km_physician_cds_assist_envelope_v1.py"
    spec = importlib.util.spec_from_file_location("build_km_physician_cds_assist_envelope_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load builder: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_envelope_from_payload


def _row_id(row: dict[str, Any], idx: int) -> str:
    return str(row.get("id") or row.get("sample_id") or row.get("row_id") or f"row-{idx:06d}")


def _payload_from_row(row: dict[str, Any]) -> dict[str, Any]:
    inner = row.get("payload")
    if isinstance(inner, dict):
        return dict(inner)
    skip = frozenset({"id", "sample_id", "row_id", "_line", "payload"})
    return {k: v for k, v in row.items() if k not in skip}


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path} line {line_no}: invalid JSON: {e}") from e
            if not isinstance(row, dict):
                raise ValueError(f"{path} line {line_no}: row must be object")
            yield line_no, row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="input_path", type=Path, required=True, help="Input JSONL path")
    ap.add_argument(
        "--out",
        dest="output_path",
        type=Path,
        required=True,
        help="Output JSONL path (one result object per input row)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate only; print counts to stderr, no output file",
    )
    ap.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first row error (exit 2)",
    )
    ap.add_argument(
        "--allow-partial",
        action="store_true",
        help="Exit 0 even if some rows failed (stderr still reports counts)",
    )
    args = ap.parse_args()

    build_envelope_from_payload = _load_builder()

    inp = args.input_path
    if not inp.is_file():
        print(f"ERROR: input not found: {inp}", file=sys.stderr)
        return 2

    ok_n = 0
    fail_n = 0
    out_rows: list[dict[str, Any]] = []

    try:
        for line_no, row in _iter_jsonl(inp):
            rid = _row_id(row, line_no)
            try:
                payload = _payload_from_row(row)
                env = build_envelope_from_payload(payload)
                out_rows.append({"id": rid, "ok": True, "envelope": env})
                ok_n += 1
            except Exception as e:
                fail_n += 1
                out_rows.append({"id": rid, "ok": False, "error": str(e)})
                if args.fail_fast:
                    print(f"ERROR: row id={rid} line={line_no}: {e}", file=sys.stderr)
                    return 2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(f"km_physician_cds_assist_envelope_batch: ok={ok_n} fail={fail_n} in={inp}", file=sys.stderr)

    if args.dry_run:
        return 0 if (fail_n == 0 or args.allow_partial) else 2

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    with args.output_path.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    if fail_n > 0 and not args.allow_partial:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
