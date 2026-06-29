#!/usr/bin/env python3
"""Verify Job 42:5–6 bridge lemmas against BHS corpus + topology sidecar ([HYPO]).

Reproducible:
  py scripts/verify_logos_job_bridge_lemma_v1.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CORPUS = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
TOPOLOGY = ROOT / "docs/final/artifacts/logos_topology_sidecar_job_suffering_reason_v1_latest.json"
ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
OUT = ROOT / "reports/logos_job_bridge_lemma_verify_v1_latest.json"

VERSE_425 = "Job.42.5"
VERSE_426 = "Job.42.6"

# Consonantal roots expected in Job 42:6 (BHS WLC)
LEMMA_CHECKS = (
    {
        "lemma": "מאס",
        "verse_ref": VERSE_426,
        "consonant_pattern": re.compile(r"מ.?א.?ס"),
        "surface_hint": "אמאס",
        "lexicon_gloss_ko": "거부·경멸·폐기 (1인칭 אֶמְאַס)",
        "pack1_reading_ko": "이전 사법적 요구·공허 변론의 전면 폐기 [HYPO]",
    },
    {
        "lemma": "נחם",
        "verse_ref": VERSE_426,
        "consonant_pattern": re.compile(r"נ.?ח.?מ"),
        "surface_hint": "נחמתי",
        "lexicon_gloss_ko": "회개·위로·안도 (1인칭 וְ/נִחַמְתִּי; stem disputed Niph/Hithp)",
        "pack1_reading_ko": "징벌 사죄가 아닌 유한 피조성 위 실존적 안도 [HYPO]",
    },
)

HEARING_SEEING_425 = (
    {"root": "שמע", "pattern": re.compile(r"ש.?מ.?ע"), "role_ko": "귀로 듣던 것 (hearsay)"},
    {"root": "ראה", "pattern": re.compile(r"ר.?א[הת]"), "role_ko": "눈으로 본 것 (presence) [HYPO]"},
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _strip_marks(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _load_verse_row(jsonl: Path, verse_id: str) -> dict[str, Any] | None:
    if not jsonl.is_file():
        return None
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if str(row.get("verse_id") or "") == verse_id:
                return row
    return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _topology_lemmas(topology: dict[str, Any]) -> list[dict[str, str]]:
    bridge = ((topology.get("topology") or {}).get("bridge_pivot") or {})
    return list(bridge.get("hebrew_lemmas") or [])


def _router_has_nacham(router: dict[str, Any]) -> bool:
    blob = json.dumps(router, ensure_ascii=False)
    return "nacham" in blob.lower() or "נחם" in blob


def verify(*, corpus: Path, topology_path: Path, router_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    lemma_rows: list[dict[str, Any]] = []
    bridge_425: list[dict[str, Any]] = []

    row425 = _load_verse_row(corpus, VERSE_425)
    row426 = _load_verse_row(corpus, VERSE_426)
    if not row425:
        errors.append(f"missing corpus row: {VERSE_425}")
    if not row426:
        errors.append(f"missing corpus row: {VERSE_426}")

    for check in LEMMA_CHECKS:
        row = row426 if check["verse_ref"] == VERSE_426 else row425
        ok = False
        original = ""
        stripped = ""
        if row:
            original = str(row.get("original_text") or row.get("text") or "")
            stripped = _strip_marks(original)
            ok = bool(check["consonant_pattern"].search(stripped))
        lemma_rows.append(
            {
                "lemma": check["lemma"],
                "verse_ref": check["verse_ref"],
                "corpus_present": ok,
                "surface_hint": check["surface_hint"],
                "original_text_bhs": original,
                "lexicon_gloss_ko": check["lexicon_gloss_ko"],
                "pack1_reading_ko": check["pack1_reading_ko"],
                "interpretive_only": True,
            }
        )
        if not ok:
            errors.append(f"lemma {check['lemma']} not found in {check['verse_ref']}")

    if row425:
        original425 = str(row425.get("original_text") or row425.get("text") or "")
        stripped425 = _strip_marks(original425)
        for item in HEARING_SEEING_425:
            bridge_425.append(
                {
                    "root": item["root"],
                    "verse_ref": VERSE_425,
                    "corpus_present": bool(item["pattern"].search(stripped425)),
                    "role_ko": item["role_ko"],
                }
            )

    topology_doc = _load_json(topology_path) if topology_path.is_file() else {}
    sidecar_lemmas = _topology_lemmas(topology_doc)
    sidecar_ok = True
    for check in LEMMA_CHECKS:
        match = next((x for x in sidecar_lemmas if x.get("lemma") == check["lemma"]), None)
        if not match:
            sidecar_ok = False
            errors.append(f"topology sidecar missing lemma: {check['lemma']}")

    router_doc = _load_json(router_path) if router_path.is_file() else {}

    return {
        "schema": "logos_job_bridge_lemma_verify_v1",
        "generated_at_utc": _utc(),
        "ok": not errors,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "why_question_assembled": False,
        "query_id": "job_suffering_reason",
        "verses": {
            VERSE_425: {
                "original_text_bhs": (row425 or {}).get("original_text"),
                "hearing_seeing_roots": bridge_425,
            },
            VERSE_426: {
                "original_text_bhs": (row426 or {}).get("original_text"),
                "text_plain": (row426 or {}).get("text"),
            },
        },
        "lemma_verification": lemma_rows,
        "topology_sidecar_lemmas": sidecar_lemmas,
        "topology_sidecar_aligned": sidecar_ok,
        "router_nacham_proxy_linked": _router_has_nacham(router_doc),
        "interpretive_boundary_ko": (
            "corpus·lemma 존재 확인 ≠ Pack1 확장 독해 확정. "
            "מאס/נחם 다의성·stem dispute는 unknown_gap 유지."
        ),
        "errors": errors,
        "source_paths": {
            "corpus": corpus.relative_to(ROOT).as_posix(),
            "topology": topology_path.relative_to(ROOT).as_posix(),
            "router": router_path.relative_to(ROOT).as_posix(),
        },
        "reproducible_command": "py scripts/verify_logos_job_bridge_lemma_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--topology", type=Path, default=TOPOLOGY)
    ap.add_argument("--router", type=Path, default=ROUTER)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    report = verify(
        corpus=args.corpus if args.corpus.is_absolute() else ROOT / args.corpus,
        topology_path=args.topology if args.topology.is_absolute() else ROOT / args.topology,
        router_path=args.router if args.router.is_absolute() else ROOT / args.router,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"  ok={report['ok']} lemmas={len(report['lemma_verification'])} errors={len(report['errors'])}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
