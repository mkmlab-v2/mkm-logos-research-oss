#!/usr/bin/env python3
"""Build news_observation_v1 JSONL from a minimal CSV (B-track ingest stub).

CSV columns (header required):
  published_utc, source_id, canonical_text, dataset_partition
Optional columns:
  source_record_url, embargo_lift_utc, as_of_utc (override), observation_id (UUID),
  hypothesis_tag (default [HYPO])

Computes text_sha256, sets ingested_at_utc to now UTC, and as_of_utc = max(published, embargo)
unless as_of_utc column provided.

Example:
  py scripts/build_news_observation_jsonl_from_csv_v1.py --input tmp/news.csv --output tmp/news.jsonl --validate
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str) -> datetime:
    t = str(s).strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="CSV → news_observation_v1 JSONL")
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--validate", action="store_true", help="Run validate_news_observation_jsonl_v1.py after write.")
    ap.add_argument("--skip-validation-exit-code", action="store_true", help="Keep exit 0 even if validate fails.")
    args = ap.parse_args()

    inp = Path(args.input).resolve()
    out = Path(args.output).resolve()
    if not inp.is_file():
        print(f"ERROR: not found {inp}", file=sys.stderr)
        return 1

    rows_out: list[str] = []
    ingested = _utc_now_iso()

    with inp.open(newline="", encoding="utf-8-sig") as fh:
        rdr = csv.DictReader(fh)
        required = {"published_utc", "source_id", "canonical_text", "dataset_partition"}
        if not rdr.fieldnames or not required.issubset(set(rdr.fieldnames)):
            print(f"ERROR: CSV must include columns {sorted(required)}", file=sys.stderr)
            return 1
        for row in rdr:
            pub_s = (row.get("published_utc") or "").strip()
            src = (row.get("source_id") or "").strip()
            text = (row.get("canonical_text") or "").strip()
            part = (row.get("dataset_partition") or "").strip()
            if not pub_s or not src or not text or not part:
                print("ERROR: empty required field in row", file=sys.stderr)
                return 1

            oid = (row.get("observation_id") or "").strip() or str(uuid.uuid4())
            hypo = (row.get("hypothesis_tag") or "").strip() or "[HYPO]"
            pub_dt = _parse_iso(pub_s)

            emb_s = (row.get("embargo_lift_utc") or "").strip()
            emb_dt = _parse_iso(emb_s) if emb_s else None

            as_override = (row.get("as_of_utc") or "").strip()
            if as_override:
                as_of_dt = _parse_iso(as_override)
            else:
                as_of_dt = pub_dt
                if emb_dt and emb_dt > as_of_dt:
                    as_of_dt = emb_dt

            rec: dict = {
                "schema_version": "news_observation_v1",
                "observation_id": oid,
                "as_of_utc": _iso_z(as_of_dt),
                "published_utc": _iso_z(pub_dt),
                "source_id": src,
                "canonical_text": text,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "ingested_at_utc": ingested,
                "dataset_partition": part,
                "hypothesis_tag": hypo,
            }
            url = (row.get("source_record_url") or "").strip()
            if url:
                rec["source_record_url"] = url
            if emb_s:
                rec["embargo_lift_utc"] = _iso_z(emb_dt) if emb_dt else emb_s

            rows_out.append(json.dumps(rec, ensure_ascii=False))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows_out) + ("\n" if rows_out else ""), encoding="utf-8")
    print(f"WROTE: {out} rows={len(rows_out)}")

    if args.validate:
        script = ROOT / "scripts" / "validate_news_observation_jsonl_v1.py"
        cmd = [sys.executable, str(script), "--news-jsonl", str(out)]
        pr = subprocess.run(cmd, cwd=str(ROOT))
        if pr.returncode != 0 and not args.skip_validation_exit_code:
            return pr.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
