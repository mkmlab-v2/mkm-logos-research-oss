#!/usr/bin/env python3
"""Philosophy / counsel lane RAG pilot (Track B only, Fact-Lock).

- Forbidden-domain gate (no network, no orders).
- Optional ANN-lite Top-K via query_logos_vector_index_ann_lite_v1.py (local sqlite).
- Optional cross_lens_rag_fusion refresh (subprocess; may no-op if inputs missing).
- Writes disk SSOT JSON for mkmlife-style \"one question\" pipelines; does NOT promote to A-track.

Exit codes:
  0 wrote pilot JSON (including fallback_rejection)
  1 unexpected failure
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
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "philosophy_lane_rag_pilot_v1_latest.json"
DEFAULT_SQLITE = ROOT / "docs" / "final" / "artifacts" / "logos_vector_index_ann_lite_v1.sqlite"
QUERY_SCRIPT = ROOT / "scripts" / "query_logos_vector_index_ann_lite_v1.py"
FUSION_SCRIPT = ROOT / "scripts" / "build_cross_lens_rag_fusion_v1.py"
DEFAULT_FORBIDDEN_CONFIG = (
    ROOT / "docs" / "final" / "artifacts" / "schemas" / "philosophy_lane_rag_pilot_forbidden_substrings_v1.json"
)

SCHEMA = "philosophy_lane_rag_pilot_v1"
VERSION = "1.0.1"

# Fallback if JSON missing or invalid (keep in sync with default JSON when possible).
_FORBIDDEN_SUBSTRINGS_FALLBACK = (
    "btcusdt",
    "binance",
    "주식",
    "투자",
    "매매",
    "비트코인",
    "선물",
    "옵션",
    "날씨",
    "기상",
    "진단",
    "처방",
    "약물",
    "암 ",
    "암이",
    "수술",
    "정치",
    "선거",
    "투표",
    "stock",
    "invest",
    "etf",
    "forex",
    "weather forecast",
    "diagnos",
    "prescription",
    "election",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_forbidden_substrings(config_path: Path) -> tuple[tuple[str, ...], str | None]:
    """Return (substrings, config_error_or_none)."""
    if not config_path.is_file():
        return _FORBIDDEN_SUBSTRINGS_FALLBACK, f"missing_forbidden_config:{config_path}"
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return _FORBIDDEN_SUBSTRINGS_FALLBACK, f"forbidden_config_read_error:{e}"
    subs = raw.get("substrings") if isinstance(raw, dict) else None
    if not isinstance(subs, list):
        return _FORBIDDEN_SUBSTRINGS_FALLBACK, "forbidden_config_invalid_substrings"
    out: list[str] = []
    for x in subs:
        if isinstance(x, str) and (s := x.strip()):
            out.append(s)
    if not out:
        return _FORBIDDEN_SUBSTRINGS_FALLBACK, "forbidden_config_empty_substrings"
    return tuple(out), None


def _forbidden_hit(text: str, substrings: tuple[str, ...]) -> str | None:
    hay = text.lower()
    for s in substrings:
        if s.lower() in hay:
            return s
    return None


def _run_ann_lite_query(query: str, top_k: int, sqlite: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Return (query_result_doc, error_message)."""
    if not sqlite.is_file():
        return None, f"missing_sqlite:{sqlite}"
    if not QUERY_SCRIPT.is_file():
        return None, "missing_query_script"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        tmp_path = Path(tmp.name)
    try:
        cmd = [
            sys.executable,
            str(QUERY_SCRIPT),
            "--sqlite",
            str(sqlite),
            "--query",
            query,
            "--top-k",
            str(top_k),
            "--output-json",
            str(tmp_path),
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip() or f"exit_{proc.returncode}"
            return None, err
        if not tmp_path.is_file():
            return None, "query_output_missing"
        doc = json.loads(tmp_path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else None, None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        return None, str(e)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _run_cross_lens_fusion() -> tuple[bool, str | None]:
    if not FUSION_SCRIPT.is_file():
        return False, "missing_fusion_script"
    proc = subprocess.run(
        [sys.executable, str(FUSION_SCRIPT), "--skip-history-append", "--skip-alert-emit"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-800:]
        return False, tail.strip() or f"exit_{proc.returncode}"
    return True, None


def _blocks_from_ann(ann: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not ann:
        return []
    top = ann.get("top_k")
    if not isinstance(top, list):
        return []
    out: list[dict[str, Any]] = []
    for row in top[:10]:
        if not isinstance(row, dict):
            continue
        vid = row.get("verse_id")
        score = row.get("score")
        out.append(
            {
                "source_rail": "logos_ann_lite",
                "hypothesis_tag": "[HYPO]",
                "summary": f"logos_ann_lite hit verse_id={vid!r} score={score}",
                "detail": "ANN-lite retrieval is not semantic when embedding_mode is hash_stub_v1; see query result notes.",
                "evidence_path": str(DEFAULT_SQLITE),
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user-query", required=True, help="User question text (pilot channel).")
    ap.add_argument("--menu-id", default="mkm_philosophy_chat_v1")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--forbidden-config",
        type=Path,
        default=DEFAULT_FORBIDDEN_CONFIG,
        help="JSON with schema philosophy_lane_rag_pilot_forbidden_substrings_v1 and substrings[].",
    )
    ap.add_argument(
        "--invoke-cross-lens-fusion",
        action="store_true",
        help="Run build_cross_lens_rag_fusion_v1.py after ANN step (Track B artifact refresh).",
    )
    ap.add_argument(
        "--redact-query",
        action="store_true",
        help="Do not embed raw user_query in output (store sha256 prefix only).",
    )
    args = ap.parse_args()

    raw_q = str(args.user_query or "").strip()
    if not raw_q:
        print("Empty --user-query.", file=sys.stderr)
        return 1

    forbidden_path = Path(args.forbidden_config)
    forbidden_subs, forbidden_cfg_err = _load_forbidden_substrings(forbidden_path)
    hit = _forbidden_hit(raw_q, forbidden_subs)
    ann_doc: dict[str, Any] | None = None
    ann_err: str | None = None
    fusion_ok = False
    fusion_err: str | None = None

    status = "ok"
    reasons: list[str] = []
    if forbidden_cfg_err:
        reasons.append(forbidden_cfg_err)

    if hit:
        status = "fallback_rejection"
        reasons.append(f"forbidden_domain_keyword:{hit}")
    else:
        ann_doc, ann_err = _run_ann_lite_query(raw_q, max(1, int(args.top_k)), Path(args.sqlite))
        if ann_err:
            status = "ann_lite_skipped"
            reasons.append(ann_err)
        if args.invoke_cross_lens_fusion:
            fusion_ok, fusion_err = _run_cross_lens_fusion()
            if not fusion_ok and fusion_err:
                reasons.append(f"cross_lens_fusion:{fusion_err[:400]}")

    q_out: str | dict[str, Any]
    if args.redact_query:
        import hashlib

        h = hashlib.sha256(raw_q.encode("utf-8")).hexdigest()
        q_out = {"redacted": True, "sha256": h}
    else:
        q_out = raw_q

    out_doc: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "menu_id": str(args.menu_id),
        "track": "B",
        "research_only": True,
        "non_gating_ack": True,
        "promotion_status": "local_only_human_signoff_required",
        "status": status,
        "reasons": reasons,
        "user_query": q_out,
        "disclaimer_pack": {
            "hypothesis": "Outputs are [HYPO] / Track B; not medical, investment, or trading advice.",
            "medical": "Not a diagnosis; seek licensed professionals for symptoms.",
            "investment": "No buy/sell recommendations; finance domain is blocked in this pilot.",
            "logos": "Logos lens is advisory / [NON_GATING] per workspace lens contract.",
        },
        "forbidden_config_path": str(forbidden_path.resolve()),
        "forbidden_config_fallback": forbidden_cfg_err is not None,
        "rails_used": ["forbidden_substrings_v1", "logos_ann_lite_query_v1"]
        + (["cross_lens_rag_fusion_v1"] if args.invoke_cross_lens_fusion else []),
        "ann_lite_query": ann_doc,
        "cross_lens_fusion_invoked": bool(args.invoke_cross_lens_fusion),
        "cross_lens_fusion_ok": fusion_ok if args.invoke_cross_lens_fusion else None,
        "fusion_artifact_hint": "docs/final/artifacts/cross_lens_rag_fusion_latest.json",
        "m31_hormone_gate": {"status": "skipped_v1", "note": "Pilot v1 does not wire lens_music M31; add in v2 if needed."},
        "blocks": [] if status == "fallback_rejection" else _blocks_from_ann(ann_doc),
    }

    if status == "fallback_rejection":
        out_doc["blocks"] = [
            {
                "source_rail": "pilot_gate",
                "hypothesis_tag": "[HYPO]",
                "summary": "Question routed to safe fallback (forbidden domain).",
                "detail": "Retry with a philosophy / counsel / general life question outside blocked domains.",
                "evidence_path": None,
            }
        ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
