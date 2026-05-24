# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.52, L:0.58, K:0.82, M:0.36}
# Balance: 84
# Purpose: Mine 보명지주·병증 한자 앵커 from IJEOMA chunk table (B-track harvest).
"""harvest_scm_boming_jiju_from_ijeoma_v1 — chunk preview phrase mining."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.core.scm_boming_jiju_lexicon_v1 import DEFAULT_LEXICON_PATH, SCHEMA_ID

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHUNK_TABLE = _ROOT / "data" / "corpus" / "ijeoma" / "_inventory" / "IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"

SECTION_TO_CONSTITUTION: dict[str, str] = {
    "soeum": "soeum_in",
    "soyang": "soyang_in",
    "taeeum": "taeeum_in",
    "taeyang": "taeyang_in",
}

_CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]+")
_HINT_SUBSTR = (
    "保命",
    "之主",
    "之氣",
    "表證",
    "受寒",
    "受熱",
    "表熱",
    "表寒",
    "脾",
    "胃",
    "腎",
    "肺",
    "肝",
    "心",
    "陽",
    "陰",
    "人",
)

HARVEST_SCHEMA = "scm_boming_jiju_ijeoma_harvest_v1"

# Section-title n-grams (e.g. 少陰人諸論) — clinical hint 없으면 제외
_SECTION_LABEL_NOISE = re.compile(
    r"^(太|少)?[陰陽]人(諸論|諸)?$|^人諸論$|^諸論$|人諸$"
)


def _is_rejected_phrase(phrase: str) -> bool:
    if _SECTION_LABEL_NOISE.match(phrase):
        return True
    if phrase.endswith("諸論") and len(phrase) >= 4 and not any(h in phrase for h in _HINT_SUBSTR):
        return True
    if phrase.endswith("人諸") and not any(
        h in phrase for h in ("表", "寒", "熱", "保命", "脾", "胃", "腎", "肺", "肝", "心")
    ):
        return True
    # constitution label only (太陽人 / 少陰人 …)
    if re.fullmatch(r"[太少][陰陽]?人", phrase):
        return True
    return False


def _extract_phrases(text: str, *, min_len: int = 2, max_len: int = 6) -> list[str]:
    out: list[str] = []
    for run in _CJK.findall(text):
        if len(run) < min_len:
            continue
        cap = min(max_len, len(run))
        for length in range(min_len, cap + 1):
            for i in range(len(run) - length + 1):
                out.append(run[i : i + length])
    return out


def _score_phrase(phrase: str, freq: int) -> int:
    base = min(freq * 10, 50)
    if any(h in phrase for h in _HINT_SUBSTR):
        base += 25
    if len(phrase) >= 4:
        base += 5
    return min(base, 95)


def _pillar_role_for(phrase: str) -> str:
    if "保命" in phrase or "之主" in phrase or "之氣" in phrase:
        return "boming_jiju"
    if "表" in phrase or "寒" in phrase or "熱" in phrase:
        return "byeongjeung_axis"
    return "ijeoma_harvest"


def load_chunk_rows(chunk_table: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not chunk_table.is_file():
        return rows
    for line in chunk_table.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def harvest_from_chunk_table(
    chunk_table: Path | None = None,
    *,
    min_freq: int = 2,
    min_score: int = 50,
    max_per_constitution: int = 40,
) -> dict[str, Any]:
    path = chunk_table or DEFAULT_CHUNK_TABLE
    rows = load_chunk_rows(path)
    phrase_counts: dict[str, Counter[str]] = {
        cid: Counter() for cid in SECTION_TO_CONSTITUTION.values()
    }
    chunk_samples: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for row in rows:
        sk = str(row.get("section_key") or "")
        cid = SECTION_TO_CONSTITUTION.get(sk)
        if not cid:
            continue
        preview = str(row.get("preview_80chars") or "")
        label = str(row.get("section_label") or "")
        blob = f"{label} {preview}"
        cid_phrases = phrase_counts[cid]
        for ph in _extract_phrases(blob):
            cid_phrases[ph] += 1
            samples = chunk_samples[cid][ph]
            cid_chunk = str(row.get("chunk_id") or "")
            if cid_chunk and len(samples) < 3 and cid_chunk not in samples:
                samples.append(cid_chunk)

    candidates_by: dict[str, list[dict[str, Any]]] = {}
    proposed: list[dict[str, Any]] = []
    rejected_title_noise = 0

    for cid, counter in phrase_counts.items():
        ranked: list[tuple[str, int]] = []
        for ph, cnt in counter.items():
            if cnt < min_freq:
                continue
            if _is_rejected_phrase(ph):
                rejected_title_noise += 1
                continue
            sc = _score_phrase(ph, cnt)
            if sc < min_score:
                continue
            ranked.append((ph, cnt))
        ranked.sort(key=lambda x: (-_score_phrase(x[0], x[1]), -x[1], x[0]))
        cand_list: list[dict[str, Any]] = []
        for ph, cnt in ranked[:max_per_constitution]:
            item = {
                "term": ph,
                "freq": cnt,
                "score": _score_phrase(ph, cnt),
                "sample_chunk_ids": chunk_samples[cid].get(ph, [])[:3],
                "pillar_role_suggested": _pillar_role_for(ph),
            }
            cand_list.append(item)
            proposed.append(
                {
                    "term": ph,
                    "normalized_form": ph.lower(),
                    "sasang_constitution": cid,
                    "pillar_role": _pillar_role_for(ph),
                    "priority": _score_phrase(ph, cnt),
                    "source": {"tier": "B_staged", "ref": "ijeoma_chunk_table_harvest_v1"},
                    "notes": f"IJEOMA preview harvest freq={cnt} [HYPO]",
                }
            )
        candidates_by[cid] = cand_list

    return {
        "schema": HARVEST_SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "boundary_ack": True,
        "chunk_table": str(path.relative_to(_ROOT)).replace("\\", "/")
        if path.is_relative_to(_ROOT)
        else path.as_posix(),
        "min_freq": min_freq,
        "min_score": min_score,
        "filter_stats": {"rejected_title_noise": rejected_title_noise},
        "candidates_by_constitution": candidates_by,
        "proposed_lexicon_entries": proposed,
        "disclaimer_ko": "[HYPO] 자동 harvest — 임상·처방 SSOT 아님. human review 후 --apply.",
    }


def merge_harvest_into_lexicon(
    harvest_doc: dict[str, Any],
    lexicon_path: Path | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    lp = lexicon_path or DEFAULT_LEXICON_PATH
    if not lp.is_file():
        raise FileNotFoundError(lp)
    lex = json.loads(lp.read_text(encoding="utf-8"))
    if lex.get("schema") != SCHEMA_ID or not lex.get("boundary_ack"):
        raise ValueError("invalid lexicon SSOT")

    existing_nf = {
        str(e.get("normalized_form") or str(e.get("term", "")).strip().lower())
        for e in lex.get("entries") or []
        if isinstance(e, dict)
    }
    added: list[dict[str, Any]] = []
    skipped = 0
    for prop in harvest_doc.get("proposed_lexicon_entries") or []:
        nf = str(prop.get("normalized_form") or prop.get("term", "")).strip().lower()
        if not nf or nf in existing_nf:
            skipped += 1
            continue
        existing_nf.add(nf)
        added.append(prop)

    stats = {"added": len(added), "skipped_duplicate": skipped, "dry_run": dry_run}
    if dry_run or not added:
        return {**stats, "lexicon_path": str(lp)}

    ver = str(lex.get("version") or "1.2.0")
    parts = ver.split(".")
    if len(parts) == 3 and parts[0].isdigit():
        parts[2] = str(int(parts[2]) + 1)
        lex["version"] = ".".join(parts)
    lex.setdefault("entries", []).extend(added)
    desc = str(lex.get("description") or "")
    if "ijeoma_harvest" not in desc:
        lex["description"] = (desc + " ijeoma_harvest merge.").strip()
    lp.write_text(json.dumps(lex, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**stats, "lexicon_path": str(lp), "new_version": lex.get("version")}
