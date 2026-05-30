#!/usr/bin/env python3
"""Build A-D dissection report for ann_lite defer ranks 9 and 11 (with 8/10 baseline)."""
from __future__ import annotations

import json
import math
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KO_GLOSS = {
    "Gen.1.16": "하나님이 두 큰 광체(해·달)와 별들을 만드심",
    "Gen.1.21": "하나님이 큰 sea creatures와 날짐승 등 물·공중 생물을 창조하심",
    "Gen.2.2": "일곱째 날에 하나님이 하신 일을 마치고 쉬심",
    "Gen.2.3": "하나님이 일곱째 날을 복 주시고 거룩하게 하심(안식)",
    "Jer.26.11": "제사장·선지자들이 예레미야에게 사형을 요구함(성전 뜰)",
    "Jer.17.19": "여호와께서 예레미야에게 백성의 성(城) 문으로 나가라 하심",
}

PAIRS = {
    8: {
        "pair_key": "aramaic::Gen.1.16|aramaic::Gen.1.21",
        "similarity": 0.928553,
        "cross_book": False,
        "review": "approve_baseline",
    },
    9: {
        "pair_key": "aramaic::Gen.1.21|aramaic::Jer.26.11",
        "similarity": 0.925269,
        "cross_book": True,
        "review": "defer_final",
    },
    10: {
        "pair_key": "aramaic::Gen.2.2|aramaic::Gen.2.3",
        "similarity": 0.923738,
        "cross_book": False,
        "review": "approve_baseline",
    },
    11: {
        "pair_key": "aramaic::Gen.2.3|aramaic::Jer.17.19",
        "similarity": 0.921388,
        "cross_book": True,
        "review": "defer_final",
    },
}


def load_verse_text(ref: str) -> dict:
    for rel in (
        "data/logos/verse_decoded_v2_complete_v1.jsonl",
        "data/logos/verse_decoded_v2_single_anchor_v1.jsonl",
    ):
        path = ROOT / rel
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("verse_id") == ref:
                return {
                    "ref": ref,
                    "source_ref": obj.get("source_ref"),
                    "edition": obj.get("edition"),
                    "text_hebrew_norm": obj.get("text"),
                    "gloss_ko": KO_GLOSS.get(ref),
                    "vector_4d": obj.get("vector_4d") or obj.get("unified_4d_vector"),
                }
    return {"ref": ref, "text_hebrew_norm": None, "gloss_ko": KO_GLOSS.get(ref), "note": "not_in_verse_decoded_ssot"}


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def ann_neighbors(ref: str, top_k: int = 8) -> list[dict]:
    sqlite_path = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1.sqlite"
    if not sqlite_path.is_file():
        return []
    con = sqlite3.connect(str(sqlite_path))
    rows = con.execute("SELECT verse_id, dim, vec_blob FROM logos_vec_stub").fetchall()
    con.close()
    target = None
    vecs: dict[str, list[float]] = {}
    for vid, dim, blob in rows:
        v = list(struct.unpack(f"<{dim}f", blob))
        vecs[str(vid)] = v
        if str(vid) == ref:
            target = v
    if target is None:
        return []
    scored = [(cosine(target, v), vid) for vid, v in vecs.items() if vid != ref]
    scored.sort(reverse=True)
    return [{"ref": r, "ann_lite_cosine": round(s, 6)} for s, r in scored[:top_k]]


def book(ref: str) -> str:
    return ref.split(".")[0]


def analyze_pair(rank: int, meta: dict) -> dict:
    src_ref, dst_ref = meta["pair_key"].replace("aramaic::", "").split("|")
    va = load_verse_text(src_ref)
    vb = load_verse_text(dst_ref)
    na = ann_neighbors(src_ref, 6)
    nb = ann_neighbors(dst_ref, 6)
    cross_a = [n for n in na if book(n["ref"]) != book(src_ref)]
    cross_b = [n for n in nb if book(n["ref"]) != book(dst_ref)]

    if rank == 9:
        thematic = [
            "[HYPO] 표면: 창조(바다 생물) vs 사형 재판 — 직접 주제 연결 약함",
            "[HYPO] Jer.26.11은 종교·법정 권력의 사형 요구 담화",
            "ann_lite: Gen.1.21 이웃에 Jer 상위권 여부로 embedding artifact 여부 판단",
        ]
        decision = "defer_maintain"
        rationale = "교차서(Gen↔Jer) + 표면 주제 불연속 — ann_lite cosine만으로 승격 불가"
    elif rank == 11:
        thematic = [
            "[HYPO] Gen.2.3=안식일 성화 vs Jer.17.19=성문(게) — 거룩/문/백성 약한 은유만 가능",
            "[HYPO] 직접 예언·인과 단정 금지 — Logos NON_GATING",
            "ann_lite: Gen.2.3 vs Jer.17.19 이웃 분포 비교",
        ]
        decision = "defer_maintain"
        rationale = "교차서(Gen↔Jer) + 표면 주제 불연속 — ann_lite cosine만으로 승격 불가"
    else:
        thematic = ["intra-Genesis 인접 구절 — ann_lite 의미 연속성 baseline"]
        decision = "approve_baseline_intra_genesis"
        rationale = "동일 책(Gen) 인접 구절 — ann_lite 의미 연속성 높음, approve baseline"

    return {
        "queue_rank": rank,
        "pair_key": meta["pair_key"],
        "ann_lite_similarity": meta["similarity"],
        "cross_book": meta["cross_book"],
        "review_decision": meta["review"],
        "A_surface_text": {"src": va, "dst": vb},
        "B_embedding_neighbors": {
            "src_top6": na,
            "dst_top6": nb,
            "src_cross_book_in_top6": cross_a,
            "dst_cross_book_in_top6": cross_b,
        },
        "C_human_theme_reading_ko": thematic,
        "D_decision": {
            "recommendation": decision,
            "canonical_promote": False,
            "rationale_ko": rationale,
        },
    }


def write_md(items: list[dict], generated_at: str) -> None:
    lines = [
        "# Logos candidate edge defer 9·11 dissection v1",
        "",
        f"Generated: {generated_at} · `[HYPO]` · `research_only` · canonical merge **금지**",
        "",
        "## 요약",
        "",
        "| rank | 쌍 | sim | 교차서 | 권고 |",
        "|------|-----|-----|--------|------|",
    ]
    for it in items:
        a, b = it["pair_key"].replace("aramaic::", "").split("|")
        cross = "Y" if it["cross_book"] else "N"
        lines.append(
            f"| {it['queue_rank']} | {a} ↔ {b} | {it['ann_lite_similarity']:.4f} | {cross} | {it['D_decision']['recommendation']} |"
        )

    r9 = next(x for x in items if x["queue_rank"] == 9)
    lines += ["", "## Rank 9 — Gen.1.21 ↔ Jer.26.11", ""]
    lines.append(f"- **A 표면:** {r9['A_surface_text']['src']['gloss_ko']} / {r9['A_surface_text']['dst']['gloss_ko']}")
    for t in r9["C_human_theme_reading_ko"]:
        lines.append(f"- {t}")
    nb = ", ".join(f"{n['ref']}({n['ann_lite_cosine']})" for n in r9["B_embedding_neighbors"]["src_top6"][:4])
    lines += ["", f"- **B 이웃 (Gen.1.21 top):** {nb}", ""]

    r11 = next(x for x in items if x["queue_rank"] == 11)
    lines += ["", "## Rank 11 — Gen.2.3 ↔ Jer.17.19", ""]
    lines.append(f"- **A 표면:** {r11['A_surface_text']['src']['gloss_ko']} / {r11['A_surface_text']['dst']['gloss_ko']}")
    for t in r11["C_human_theme_reading_ko"]:
        lines.append(f"- {t}")

    lines += ["", "## Baseline (approve) 대조", ""]
    for rank in (8, 10):
        it = next(x for x in items if x["queue_rank"] == rank)
        a, b = it["pair_key"].replace("aramaic::", "").split("|")
        lines.append(f"- rank {rank}: {a} ↔ {b} — intra-Gen, sim={it['ann_lite_similarity']:.4f}")

    lines += [
        "",
        "## 판정",
        "",
        "- **9·11: defer_maintain** (교차서 + 표면 주제 단절)",
        "- canonical / showroom / Track A 합선 없음",
    ]
    out_md = ROOT / "reports/logos_candidate_edge_defer_9_11_dissection_v1_latest.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = [analyze_pair(r, PAIRS[r]) for r in (8, 9, 10, 11)]
    doc = {
        "schema": "logos_candidate_edge_defer_9_11_dissection_v1",
        "generated_at_utc": now,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "method": (
            "A-D structured review (surface text from data/logos/verse_decoded_v2_complete_v1.jsonl; "
            "ann_lite neighbors from logos_vector_index_ann_lite_v1.sqlite)"
        ),
        "defer_final_ref": "reports/logos_candidate_edge_defer_9_11_final_v1_latest.json",
        "pairs_analyzed": items,
        "cross_book_policy_ko": (
            "ann_lite primary rank 9·11은 Gen↔Jer 교차서 — defer 확정 유지. rank 8·10은 intra-Gen baseline."
        ),
        "commander_next": [
            "defer 9·11 유지(권장)",
            "또는 reject로 닫기",
            "approve는 추가 전문 검토 없이 비권장",
        ],
    }
    out_json = ROOT / "reports/logos_candidate_edge_defer_9_11_dissection_v1_latest.json"
    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_md(items, now)
    print(json.dumps({"json": str(out_json), "md": str(ROOT / 'reports/logos_candidate_edge_defer_9_11_dissection_v1_latest.md')}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
