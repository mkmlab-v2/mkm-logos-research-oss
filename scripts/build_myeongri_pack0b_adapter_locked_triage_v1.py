"""Aggregate Pack 0-B adapter locked-eval reports into one triage JSON (GPU-free)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def _short_run(adapter_path: str | None, oracle: bool) -> str:
    if oracle:
        return "oracle_golden_replay"
    if not adapter_path:
        return "base_no_adapter"
    p = adapter_path.replace("\\", "/").lower()
    for marker in (
        "run_pack0b_",
        "run_tier0_",
        "run_train_",
        "myeongri_pillars_only_v0/",
        "myeongri_pillars_multiclass_v1/",
    ):
        if marker in p:
            idx = p.index(marker)
            return p[idx:].split("/")[0]
    return Path(adapter_path).name


def _split_label(d: dict[str, Any]) -> str:
    sp = d.get("split")
    if sp:
        return str(sp)
    gj = str(d.get("golden_jsonl") or "")
    if "locked_eval" in gj:
        return "locked_eval"
    if "train.jsonl" in gj:
        return "train"
    return "?"


def _row_from_eval(fp: Path, d: dict[str, Any]) -> dict[str, Any] | None:
    schema = d.get("schema") or ""
    if schema == "myeongri_hybrid_eval_bridge_v1":
        return {
            "file": fp.name,
            "run": d.get("mode", "hybrid_bridge"),
            "model": "(sklearn RF/XGB hybrid)",
            "split": "locked_eval",
            "n": d.get("rows_completed"),
            "parse_ok": d.get("weighted_parse_ok_rate"),
            "pillars_pct": d.get("weighted_pillars_alignment_pass_rate"),
            "align_pct": d.get("weighted_alignment_pass_rate"),
            "four_pillars_all": None,
            "slot_y_m_d_h": d.get("slot_match_rate"),
            "ilgan_match": None,
            "local_iso_match": None,
            "compact": None,
            "pillars_only_curriculum": None,
            "note": "not end-to-end LoRA",
        }
    if schema == "myeongri_locked_eval_batched_summary_v1":
        return {
            "file": fp.name,
            "run": _short_run(d.get("adapter_path"), False),
            "model": "",
            "split": _split_label(d),
            "n": d.get("rows_completed"),
            "parse_ok": d.get("weighted_parse_ok_rate"),
            "pillars_pct": d.get("weighted_pillars_alignment_pass_rate"),
            "align_pct": d.get("weighted_alignment_pass_rate"),
            "four_pillars_all": None,
            "slot_y_m_d_h": None,
            "ilgan_match": None,
            "local_iso_match": None,
            "compact": None,
            "pillars_only_curriculum": None,
            "note": f"batched max_rows={d.get('max_rows')}",
        }
    if schema != "myeongri_deterministic_lora_inference_eval_v1":
        return None
    fda = d.get("field_diff_aggregate") or {}
    return {
        "file": fp.name,
        "run": _short_run(d.get("adapter_path"), bool(d.get("oracle_golden"))),
        "model": (d.get("model_name") or "")[:48],
        "split": "locked_eval" if (d.get("rows") or 0) <= 100 else _split_label(d),
        "n": d.get("rows"),
        "parse_ok": d.get("parse_ok_rate"),
        "pillars_pct": d.get("pillars_alignment_pass_rate"),
        "align_pct": d.get("alignment_pass_rate"),
        "four_pillars_all": fda.get("four_pillars_all_match_rate"),
        "slot_y_m_d_h": fda.get("four_pillars_by_key") or d.get("slot_match_rate"),
        "ilgan_match": fda.get("ilgan_match_rate"),
        "local_iso_match": fda.get("local_iso_match_rate"),
        "compact": d.get("compact_instruction"),
        "pillars_only_curriculum": d.get("pillars_only_curriculum"),
        "alignment_tier": d.get("alignment_tier"),
        "note": "",
    }


def _mismatch_histogram(fp: Path) -> dict[str, int]:
    if not fp.exists():
        return {}
    d = json.loads(fp.read_text(encoding="utf-8-sig"))
    counts: dict[str, int] = {}
    for r in d.get("per_row") or []:
        note = r.get("mismatch_note") or "unknown"
        counts[note] = counts.get(note, 0) + 1
    return counts


def main() -> int:
    patterns = [
        "myeongri_*eval*.json",
        "myeongri_*summary*.json",
        "myeongri_deterministic_lora_locked_eval*.json",
        "myeongri_hybrid_eval_bridge_latest.json",
    ]
    files: set[Path] = set()
    for pat in patterns:
        files.update(REPORTS.glob(pat))

    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for fp in sorted(files):
        try:
            d = json.loads(fp.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            continue
        row = _row_from_eval(fp, d)
        if not row:
            continue
        sig = (row["run"], row["n"], row["parse_ok"], row["pillars_pct"], row["file"])
        if sig in seen:
            continue
        seen.add(sig)
        rows.append(row)

    rows.sort(key=lambda r: (-(r.get("pillars_pct") or 0), -(r.get("parse_ok") or 0), r["run"]))

    qwen_compact = REPORTS / "myeongri_deterministic_lora_locked_eval_inference_eval_qwen_compact_v1.json"
    crosscheck = REPORTS / "myeongri_pillars_engine_crosscheck_v1_latest.json"
    cc = {}
    if crosscheck.exists():
        cc_data = json.loads(crosscheck.read_text(encoding="utf-8-sig"))
        cc = {
            "classification_counts": cc_data.get("classification_counts"),
            "golden_matches_engine_rate": cc_data.get("golden_matches_engine_rate"),
            "recommendations_ko": cc_data.get("recommendations_ko"),
        }

    out = {
        "schema": "myeongri_pack0b_adapter_locked_triage_v1",
        "generated_at_utc": __import__("datetime").datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "eval_ceiling_oracle": {
            "file": "myeongri_pillars_locked25_oracle_eval.json",
            "pillars_pct": 1.0,
            "note": "labels+eval pipeline OK",
        },
        "runs": rows,
        "mismatch_notes_qwen_compact_locked25": _mismatch_histogram(qwen_compact),
        "engine_crosscheck_excerpt": cc,
        "dominant_failure_mode": "model_mode_collapse_while_golden_ok",
        "track_wall": {
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
        },
    }

    out_path = REPORTS / "myeongri_pack0b_adapter_locked_triage_latest.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"runs={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
