#!/usr/bin/env python3
"""Logos Studio GraphRAG on/off insight quality A/B bench [HYPO].

Compares:
- on: query-time GraphRAG encode output
- off: closest preset-only fallback

Quality rubric is structural (grounding/path/specificity/governance),
not price KPI and not Track A promotion evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

DEFAULT_QUERIES = ROOT / "docs/final/fixtures/logos_studio_graphrag_insight_ab_queries_v1.json"
DEFAULT_PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_studio_graphrag_insight_ab_bench_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/logos_studio_graphrag_insight_ab_bench_v1_latest.json"

TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣_.]+")
CONFLICT_HINTS = (
    "네피림",
    "watcher",
    "감시자",
    "sons of god",
    "benei",
    "nephilim",
    "divine council",
    "신의 회의",
    "시편 82",
    "psalm 82",
    "하나님의 아들",
)

# Query anchor → preset id/keyword haystack hints (fair baseline for A/B off arm).
_BASELINE_DOMAIN_HINTS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("반도체", "semiconductor", "공급망"), ("semiconductor", "반도체", "iron_clay", "refined")),
    (("바벨", "babel", "언어", "탑"), ("babel", "gen_11", "gen.11", "hubris")),
    (("에덴", "타락", "eden", "fall"), ("gen_3", "gen.3", "eden", "타락")),
    (("divine council", "신의 회의", "시편 82", "psalm 82"), ("divine_council", "sons_of_god")),
    (("감시자", "watchers", "watcher"), ("watchers", "watcher", "nephilim")),
    (("욥", "job", "고난", "의회"), ("job", "suffering", "job_job")),
    (("다니엘", "daniel", "아람어"), ("daniel", "dan_aramaic", "dan_2")),
)


def _domain_baseline_bonus(query: str, preset: dict[str, Any]) -> float:
    q_lower = (query or "").lower()
    pid = str(preset.get("id") or "").lower()
    kw_blob = " ".join(str(x) for x in (preset.get("keywords") or [])).lower()
    hay = f"{pid} {kw_blob}"
    bonus = 0.0
    for query_needles, preset_needles in _BASELINE_DOMAIN_HINTS:
        if any(n in q_lower for n in query_needles):
            if any(n in hay for n in preset_needles):
                bonus += 8.0
            elif any(n in q_lower for n in ("반도체", "semiconductor")) and "watcher" in pid:
                bonus -= 6.0
    return bonus


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text or "") if t}


def _contains_governance(text: str) -> bool:
    s = (text or "").lower()
    return "[hypo]" in s or "non_gating" in s or "research_only" in s


def _run_graphrag(query: str, timeout_sec: int) -> dict[str, Any]:
    proc = subprocess.run(
        [PY, str(ROOT / "scripts/encode_logos_studio_query_graphrag_v1.py"), "--query", query],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_sec,
    )
    try:
        doc = json.loads((proc.stdout or "{}").strip())
    except json.JSONDecodeError:
        doc = {"ok": False, "error": "invalid_stdout_json"}
    if proc.returncode != 0 and doc.get("ok") is not True:
        doc["error"] = doc.get("error") or (proc.stderr or f"exit_{proc.returncode}")[:180]
    return doc


def _pick_baseline_preset(query: str, presets: list[dict[str, Any]]) -> dict[str, Any] | None:
    qt = _tokens(query)
    best: tuple[float, dict[str, Any] | None] = (-1.0, None)
    for p in presets:
        pt = _tokens(str(p.get("prompt_ko") or ""))
        kw = set()
        for item in p.get("keywords") or []:
            kw |= _tokens(str(item))
        overlap_prompt = len(qt & pt)
        overlap_kw = len(qt & kw)
        score = overlap_kw * 2.0 + overlap_prompt * 1.0 + _domain_baseline_bonus(query, p)
        if score > best[0]:
            best = (score, p)
    return best[1]


def _arm_metrics(
    *,
    answer: str,
    note: str,
    verse_refs: list[str],
    path_steps: list[str],
    conflict_parallel: bool,
) -> dict[str, float]:
    evidence_grounding = min(1.0, len(verse_refs) / 4.0)
    path_structure = min(1.0, len(path_steps) / 4.0)
    note_specificity = min(1.0, len((note or "").strip()) / 120.0)
    governance = 1.0 if _contains_governance(answer + " " + note) else 0.0
    school_parallel = 1.0 if conflict_parallel else 0.0
    total = (
        evidence_grounding * 0.35
        + path_structure * 0.25
        + note_specificity * 0.20
        + governance * 0.10
        + school_parallel * 0.10
    )
    return {
        "evidence_grounding": round(evidence_grounding, 4),
        "path_structure": round(path_structure, 4),
        "note_specificity": round(note_specificity, 4),
        "governance_honesty": round(governance, 4),
        "school_parallel": round(school_parallel, 4),
        "total": round(total, 4),
    }


def _conflict_expected(query: str) -> bool:
    lower = query.lower()
    return any(k in lower for k in CONFLICT_HINTS)


def run_bench(queries_doc: dict[str, Any], presets_doc: dict[str, Any], timeout_sec: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    presets = [p for p in (presets_doc.get("presets") or []) if isinstance(p, dict)]

    for item in queries_doc.get("items") or []:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("id") or "")
        query = str(item.get("query_ko") or "").strip()
        if not qid or not query:
            continue

        on_doc = _run_graphrag(query, timeout_sec=timeout_sec)
        baseline = _pick_baseline_preset(query, presets) or {}
        baseline_rp = baseline.get("router_path_v1") or {}

        on_rp = on_doc.get("router_path_v1") or {}
        on_refs = list(on_rp.get("verse_refs") or [])
        on_steps = list(on_rp.get("path_steps") or [])

        off_refs = list(baseline_rp.get("verse_refs") or [])
        off_steps = list(baseline_rp.get("path_steps") or [])

        conflict_on = _conflict_expected(query)
        conflict_off = bool(baseline.get("bigset_conflict_group_id"))

        on_metrics = _arm_metrics(
            answer=str(on_doc.get("answer_ko") or ""),
            note=str(on_rp.get("note_ko") or ""),
            verse_refs=on_refs,
            path_steps=on_steps,
            conflict_parallel=conflict_on,
        )
        off_metrics = _arm_metrics(
            answer=str(baseline.get("answer_ko") or ""),
            note=str(baseline_rp.get("note_ko") or ""),
            verse_refs=off_refs,
            path_steps=off_steps,
            conflict_parallel=conflict_off,
        )

        row = {
            "query_id": qid,
            "query_ko": query,
            "on": {
                "ok": on_doc.get("ok") is True,
                "query_mode": "graphrag_only",
                "bridges_matched": on_doc.get("bridges_matched"),
                "paths_count": on_doc.get("paths_count"),
                "metrics": on_metrics,
                "verse_refs": on_refs[:12],
                "path_steps": on_steps[:8],
            },
            "off": {
                "ok": bool(baseline),
                "query_mode": "preset_only",
                "preset_id": baseline.get("id"),
                "metrics": off_metrics,
                "verse_refs": off_refs[:12],
                "path_steps": off_steps[:8],
            },
            "delta_on_minus_off": {
                "total": round(on_metrics["total"] - off_metrics["total"], 4),
                "evidence_grounding": round(
                    on_metrics["evidence_grounding"] - off_metrics["evidence_grounding"], 4
                ),
                "path_structure": round(on_metrics["path_structure"] - off_metrics["path_structure"], 4),
                "note_specificity": round(
                    on_metrics["note_specificity"] - off_metrics["note_specificity"], 4
                ),
                "school_parallel": round(on_metrics["school_parallel"] - off_metrics["school_parallel"], 4),
            },
            "alignment_pass_on": on_metrics["total"] >= 0.6,
            "parse_ok": bool(baseline) and on_doc.get("ok") is True,
        }
        rows.append(row)

    n = len(rows)
    on_wins = sum(1 for r in rows if (r["delta_on_minus_off"]["total"] or 0) > 0)
    parse_ok = sum(1 for r in rows if r.get("parse_ok"))
    align_on = sum(1 for r in rows if r.get("alignment_pass_on"))
    mean_delta = round(sum((r["delta_on_minus_off"]["total"] or 0.0) for r in rows) / max(n, 1), 4)

    raw = {
        "parse_ok_rate": round(parse_ok / max(n, 1), 4),
        "alignment_pass_rate": round(align_on / max(n, 1), 4),
        "rows": n,
    }
    repair = {
        "parse_ok_rate": raw["parse_ok_rate"],
        "alignment_pass_rate": raw["alignment_pass_rate"],
        "repair_applied_count": 0,
        "rows": n,
    }

    return {
        "schema": "logos_studio_graphrag_insight_ab_bench_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "wires_to_scoring_core": False,
        "summary": {
            "rows": n,
            "on_win_rate": round(on_wins / max(n, 1), 4),
            "mean_total_delta_on_minus_off": mean_delta,
            "note": "Structural rubric only; not Track A promotion evidence.",
        },
        "rows": rows,
        "raw_repair_dual": {
            "raw": raw,
            "repair_v2": repair,
            "delta": {
                "alignment_pass_rate_delta_repair_v2_minus_raw": round(
                    repair["alignment_pass_rate"] - raw["alignment_pass_rate"], 4
                )
            },
        },
        "reproduce": "py scripts/run_logos_studio_graphrag_insight_ab_bench_v1.py",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queries-json", type=Path, default=DEFAULT_QUERIES)
    ap.add_argument("--presets-json", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--timeout-sec", type=int, default=35)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    queries_doc = _load_json(args.queries_json)
    presets_doc = _load_json(args.presets_json)
    if not queries_doc or not presets_doc:
        print(json.dumps({"ok": False, "error": "missing_inputs"}, ensure_ascii=False))
        return 1

    out = run_bench(queries_doc, presets_doc, timeout_sec=int(args.timeout_sec))
    payload = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(payload, encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "rows": out["summary"]["rows"],
                "on_win_rate": out["summary"]["on_win_rate"],
                "mean_delta": out["summary"]["mean_total_delta_on_minus_off"],
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
