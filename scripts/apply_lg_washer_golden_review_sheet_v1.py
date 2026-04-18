# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.85, K:0.52, M:0.68}
# Balance: 90
# Purpose: Merge reviewed TSV rows into golden train/holdout JSONL and rebuild split manifest.
# Keywords: LG, washer, golden, TSV, import, manifest
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_TRAIN = ART / "lg_washer_voice_golden_train_v1.jsonl"
DEFAULT_HOLDOUT = ART / "lg_washer_voice_golden_holdout_v1.jsonl"
DEFAULT_TSV = ART / "lg_washer_voice_golden_review_sheet_v1.tsv"
DEFAULT_MANIFEST = ART / "lg_washer_voice_golden_split_manifest_v1.json"

REJECT_STATUSES = frozenset(s.lower() for s in ("REJECT", "SKIP", "DROP"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _strip_cell(s: str | None) -> str:
    if s is None:
        return ""
    return str(s).strip()


def _merge_row(base: dict[str, Any], tsv: dict[str, str]) -> dict[str, Any]:
    out = dict(base)
    out["utterance"] = _strip_cell(tsv.get("utterance")) or out.get("utterance", "")
    out["intent"] = _strip_cell(tsv.get("intent")) or out.get("intent", "")
    sj = _strip_cell(tsv.get("slots_json"))
    if sj:
        try:
            out["slots"] = json.loads(sj)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid slots_json for id={out.get('id')}: {exc}") from exc
    if not isinstance(out.get("slots"), dict):
        out["slots"] = {}
    sp = _strip_cell(tsv.get("split"))
    if sp in ("train", "holdout"):
        out["split"] = sp
    ea = _strip_cell(tsv.get("expected_action"))
    if ea:
        out["expected_action"] = ea
    dt = _strip_cell(tsv.get("data_tier"))
    if dt:
        out["data_tier"] = dt
    bp = _strip_cell(tsv.get("build_pack"))
    if bp:
        out["build_pack"] = bp
    ch = tsv.get("conflict_hint")
    if ch is not None and _strip_cell(ch) == "":
        out.pop("conflict_hint", None)
    elif _strip_cell(ch):
        out["conflict_hint"] = _strip_cell(ch)
    ah = tsv.get("ambiguity_hint")
    if ah is not None and _strip_cell(ah) == "":
        out.pop("ambiguity_hint", None)
    elif _strip_cell(ah):
        out["ambiguity_hint"] = _strip_cell(ah)
    return out


def _rebuild_manifest(
    train_rows: list[dict[str, Any]],
    hold_rows: list[dict[str, Any]],
    prior: dict[str, Any] | None,
    tsv_rel: str,
) -> dict[str, Any]:
    tr_i = Counter(str(r["intent"]) for r in train_rows)
    ho_i = Counter(str(r["intent"]) for r in hold_rows)
    total = tr_i + ho_i
    base: dict[str, Any] = {
        "schema": "lg_washer_voice_golden_split_manifest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "source_report": (prior or {}).get("source_report", "docs/final/artifacts/lg_washer_integrity_validation_report_sample_v1.json"),
        "execution_pack": "docs/final/artifacts/challenge_ax_vertical_lg_hs_execution_pack_v1.json",
        "device_profile_placeholder": "docs/final/artifacts/lg_washer_device_profile_placeholder_v1.json",
        "review_sheet_applied": tsv_rel.replace("\\", "/"),
        "outputs": {
            "train_jsonl": "docs/final/artifacts/lg_washer_voice_golden_train_v1.jsonl",
            "holdout_jsonl": "docs/final/artifacts/lg_washer_voice_golden_holdout_v1.jsonl",
        },
        "split_policy": {
            "strategy": "review_sheet_merge_v1",
            "note_ko": "TSV 검토본을 베이스 JSONL에 병합한 뒤 의도별 집계를 재산출함. REJECT/SKIP/DROP은 --drop-rejected일 때만 제외.",
            "train_count": len(train_rows),
            "holdout_count": len(hold_rows),
            "counts_total_per_intent": dict(total),
            "counts_train_per_intent": dict(tr_i),
            "counts_holdout_per_intent": dict(ho_i),
        },
        "data_governance": (prior or {}).get("data_governance")
        or {
            "data_tier_notes_ko": [
                "utt_*: 샘플 시드.",
                "s300_*: 합성 조합(실골든 전 교체).",
            ]
        },
    }
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    ap.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--tsv", type=Path, default=DEFAULT_TSV)
    ap.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument(
        "--drop-rejected",
        action="store_true",
        help="Remove rows whose review_status is REJECT/SKIP/DROP (case-insensitive)",
    )
    ap.add_argument("--no-validate", action="store_true")
    args = ap.parse_args()

    train_rows = _load_jsonl(args.train)
    hold_rows = _load_jsonl(args.holdout)
    by_id: dict[str, dict[str, Any]] = {}
    for r in train_rows + hold_rows:
        by_id[str(r["id"])] = dict(r)

    tsv_rows = _load_tsv(args.tsv)
    excluded: set[str] = set()
    for tr in tsv_rows:
        rid = _strip_cell(tr.get("id"))
        if not rid:
            continue
        st = _strip_cell(tr.get("review_status")).lower()
        if args.drop_rejected and st in REJECT_STATUSES:
            excluded.add(rid)

    for tr in tsv_rows:
        rid = _strip_cell(tr.get("id"))
        if not rid or rid in excluded:
            continue
        if rid not in by_id:
            raise SystemExit(f"TSV references unknown id {rid!r} (not in current golden JSONL).")
        by_id[rid] = _merge_row(by_id[rid], tr)

    for rid in list(by_id.keys()):
        if rid in excluded:
            del by_id[rid]

    final_train = sorted((r for r in by_id.values() if r.get("split") == "train"), key=lambda x: str(x["id"]))
    final_hold = sorted((r for r in by_id.values() if r.get("split") == "holdout"), key=lambda x: str(x["id"]))
    bad = [r for r in by_id.values() if r.get("split") not in ("train", "holdout")]
    if bad:
        raise SystemExit(f"Invalid split values: {[r.get('id') for r in bad]}")

    prior_manifest: dict[str, Any] | None = None
    if args.manifest_out.exists():
        prior_manifest = json.loads(args.manifest_out.read_text(encoding="utf-8"))

    _write_jsonl(args.train, final_train)
    _write_jsonl(args.holdout, final_hold)

    try:
        tsv_rel = str(args.tsv.relative_to(ROOT))
    except ValueError:
        tsv_rel = str(args.tsv)
    manifest = _rebuild_manifest(final_train, final_hold, prior_manifest, tsv_rel)
    args.manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(str(args.train))
    print(str(args.holdout))
    print(str(args.manifest_out))
    print(f"train={len(final_train)} holdout={len(final_hold)}")

    if not args.no_validate:
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "validate_lg_washer_voice_golden_jsonl_v1.py"),
            "--train",
            str(args.train),
            "--holdout",
            str(args.holdout),
            "--manifest",
            str(args.manifest_out),
        ]
        subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
