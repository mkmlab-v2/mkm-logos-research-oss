"""Cosmic anchor ↔ GraphRAG / lemma / themed bridge linkage (HYPO, no batch mutation)."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts.core.logos_verse_corpus_lookup_v1 import normalize_verse_ref
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

VERSE_RE = re.compile(r"^\d*[A-Za-z][A-Za-z0-9]*\.\d+\.\d+$")


def _verse_from_node(row: dict[str, Any]) -> str | None:
    ref = row.get("ref")
    if isinstance(ref, str) and VERSE_RE.match(ref.strip()):
        return canonical_verse_ref(ref.strip())
    nid = row.get("node_id")
    if isinstance(nid, str) and "::" in nid:
        tail = nid.split("::", 1)[1].strip()
        if VERSE_RE.match(tail):
            return canonical_verse_ref(tail)
    vid = row.get("verse_id")
    if isinstance(vid, str) and VERSE_RE.match(vid.strip()):
        return canonical_verse_ref(vid.strip())
    return None


def load_lemma_index(lemma_path: Path) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not lemma_path.is_file():
        return out
    for line in lemma_path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        dst = canonical_verse_ref(str(row.get("dst_node_id") or ""))
        if dst:
            out[dst].append(row)
    return out


def load_meaning_graph(
    nodes_path: Path,
    edges_path: Path,
) -> tuple[dict[str, str], dict[str, list[dict[str, Any]]]]:
    ref_to_node: dict[str, str] = {}
    if nodes_path.is_file():
        for line in nodes_path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            vr = _verse_from_node(row)
            if vr:
                ref_to_node[vr] = str(row.get("node_id") or vr)
    adj: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if edges_path.is_file():
        for line in edges_path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            src = str(row.get("src_node_id") or "")
            dst = str(row.get("dst_node_id") or "")
            if src and dst:
                adj[src].append(row)
    return ref_to_node, adj


def load_themed_bridge_index(themed_glob: list[Path]) -> dict[str, list[str]]:
    verse_to_themes: dict[str, list[str]] = defaultdict(list)
    for path in themed_glob:
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        theme_id = str((doc.get("policy") or {}).get("theme_id") or path.stem)
        for node in doc.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            vid = node.get("verse_id")
            if isinstance(vid, str):
                vr = canonical_verse_ref(normalize_verse_ref(vid))
                if vr and theme_id not in verse_to_themes[vr]:
                    verse_to_themes[vr].append(theme_id)
    return verse_to_themes


def _motif_tokens(anchor: dict[str, Any]) -> set[str]:
    lemma = anchor.get("motif_lemma") or {}
    tokens: set[str] = set()
    for key in ("greek", "hebrew"):
        val = str(lemma.get(key) or "").strip().lower()
        if len(val) >= 3:
            tokens.add(val)
    return tokens


def _top_primitive(anchor: dict[str, Any]) -> str | None:
    rows = anchor.get("kernel_alignment") or []
    if not rows:
        return None
    top = max(rows, key=lambda r: float(r.get("similarity_adjusted", r.get("similarity", 0))))
    return str(top.get("primitive") or "")


def link_anchor(
    anchor: dict[str, Any],
    *,
    file_stem: str,
    lemma_index: dict[str, list[dict[str, Any]]],
    ref_to_node: dict[str, str],
    graph_adj: dict[str, list[dict[str, Any]]],
    verse_to_themes: dict[str, list[str]],
) -> dict[str, Any]:
    verse_refs = [canonical_verse_ref(normalize_verse_ref(str(v))) for v in anchor.get("verse_refs") or []]
    lemma_hits: list[dict[str, Any]] = []
    themed_hits: list[str] = []
    graph_edges: list[dict[str, Any]] = []
    for vr in verse_refs:
        for row in lemma_index.get(vr, [])[:5]:
            lemma_hits.append(
                {
                    "verse_ref": vr,
                    "path_id": row.get("path_id"),
                    "src_node_id": row.get("src_node_id"),
                    "edge_type": row.get("edge_type"),
                }
            )
        for theme in verse_to_themes.get(vr, []):
            if theme not in themed_hits:
                themed_hits.append(theme)
        node_id = ref_to_node.get(vr)
        if node_id:
            for edge in graph_adj.get(node_id, [])[:3]:
                graph_edges.append(
                    {
                        "verse_ref": vr,
                        "edge_type": edge.get("edge_type"),
                        "dst_node_id": edge.get("dst_node_id"),
                        "weight": edge.get("weight"),
                    }
                )
    return {
        "file_stem": file_stem,
        "anchor_id": anchor.get("anchor_id"),
        "verse_refs": verse_refs,
        "vector_4d": anchor.get("vector_4d"),
        "top_primitive": _top_primitive(anchor),
        "motif_tokens": sorted(_motif_tokens(anchor)),
        "lemma_edge_count": len(lemma_hits),
        "lemma_hits": lemma_hits,
        "themed_bridge_ids": themed_hits,
        "meaning_graph_edge_count": len(graph_edges),
        "meaning_graph_edges": graph_edges,
    }


def build_resonance_edges(
    linked: list[dict[str, Any]],
    *,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for i, a in enumerate(linked):
        scored: list[tuple[float, int, str]] = []
        for j, b in enumerate(linked):
            if i == j:
                continue
            score = 0.0
            reasons: list[str] = []
            if a.get("top_primitive") and a["top_primitive"] == b.get("top_primitive"):
                score += 0.4
                reasons.append("shared_top_primitive")
            shared = set(a.get("motif_tokens") or []) & set(b.get("motif_tokens") or [])
            if shared:
                score += 0.5
                reasons.append("shared_motif_token")
            shared_themes = set(a.get("themed_bridge_ids") or []) & set(b.get("themed_bridge_ids") or [])
            if shared_themes:
                score += 0.3
                reasons.append("shared_themed_bridge")
            a_ot = str((a.get("verse_refs") or [""])[0]).startswith(("Isa.", "Ps.", "Gen.", "Exod.", "Lev."))
            b_nt = str((b.get("verse_refs") or [""])[0]).startswith(("Jhn.", "Matt.", "Luke.", "Rom.", "Rev."))
            if a_ot and b_nt:
                score += 0.2
                reasons.append("ot_to_nt_span")
            if score > 0:
                scored.append((score, j, ",".join(reasons)))
        scored.sort(reverse=True)
        for score, j, reason in scored[:top_k]:
            b = linked[j]
            edges.append(
                {
                    "src_anchor_id": a["anchor_id"],
                    "dst_anchor_id": b["anchor_id"],
                    "src_verse": (a.get("verse_refs") or [""])[0],
                    "dst_verse": (b.get("verse_refs") or [""])[0],
                    "edge_type": "anchor_resonance_hypo",
                    "weight": round(score, 4),
                    "reason": reason,
                }
            )
    return edges


def _path_hop(anchor_id: str, linked_by_id: dict[str, dict[str, Any]], hop: int) -> dict[str, Any]:
    row = linked_by_id[anchor_id]
    return {
        "hop": hop,
        "anchor_id": anchor_id,
        "verse_ref": (row.get("verse_refs") or [""])[0],
        "top_primitive": row.get("top_primitive"),
        "themed_bridge_ids": row.get("themed_bridge_ids") or [],
    }


def build_narrative_path_samples(
    linked: list[dict[str, Any]],
    resonance_edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {row["anchor_id"]: row for row in linked}
    id_by_stem = {row["file_stem"]: row["anchor_id"] for row in linked}

    def _curated(sample_id: str, query_ko: str, stems: list[str]) -> dict[str, Any] | None:
        ids = [id_by_stem.get(s) for s in stems]
        if not all(ids):
            return None
        return {
            "sample_id": sample_id,
            "query_ko": query_ko,
            "hypothesis_class": "HYPO",
            "non_gating": True,
            "path": [_path_hop(aid, by_id, hop) for hop, aid in enumerate(ids)],
            "edge_types": ["curated_narrative_transition"],
        }

    samples: list[dict[str, Any]] = []
    for item in (
        _curated(
            "isa53_wound_to_jhn_light",
            "[HYPO] 고난(이사야)→양→빛(요한) 서사 전이 샘플 — 신학 단정 아님",
            ["wound", "lamb", "light"],
        ),
        _curated(
            "seed_to_way_core",
            "[HYPO] 씨앗→길 Top100 코어 motif 전이",
            ["seed", "way"],
        ),
        _curated(
            "water_to_bread_jhn",
            "[HYPO] 요한 생명수→떡 motif 연쇄",
            ["water", "bread"],
        ),
        _curated(
            "wrath_to_healing_restoration",
            "[HYPO] 진노→상처→치유 motif 전이 — 신학 단정 아님",
            ["wrath", "wound", "healing"],
        ),
        _curated(
            "vine_to_door_abiding_access",
            "[HYPO] 포도나무→문(요한) abiding/access motif 연쇄",
            ["vine", "door"],
        ),
        _curated(
            "living_water_to_well_jhn4",
            "[HYPO] 생수→우물(요한4) 수증기 motif 클러스터",
            ["living_water", "well"],
        ),
        _curated(
            "harbor_to_tent_sojourn",
            "[HYPO] 항구→장막 순례·피난 motif 연쇄",
            ["harbor", "tent"],
        ),
        _curated(
            "shepherd_to_door_pastoral",
            "[HYPO] 목자→문(요한10) pastoral access motif 연쇄",
            ["shepherd", "door"],
        ),
        _curated(
            "blood_to_cross_covenant",
            "[HYPO] 피→십자가 언약·기념 motif 연쇄",
            ["blood", "cross"],
        ),
        _curated(
            "fire_to_rock_refuge",
            "[HYPO] 불→반석 심판·피난처 motif 연쇄",
            ["fire", "rock"],
        ),
        _curated(
            "cross_to_lamb_redeemer",
            "[HYPO] 십자가→어린양 구속 motif 연쇄",
            ["cross", "lamb"],
        ),
        _curated(
            "ark_to_star_eschaton",
            "[HYPO] 방주→샛별(계) 종말·인도 motif 연쇄",
            ["ark", "star"],
        ),
        _curated(
            "chaff_to_fire_winnow",
            "[HYPO] 쭉정이→불 타작·분별 motif 연쇄",
            ["chaff", "fire"],
        ),
        _curated(
            "bondage_to_harbor_liberation",
            "[HYPO] 속박→항구 해방·피난 motif 연쇄",
            ["bondage", "harbor"],
        ),
        _curated(
            "oil_to_honey_abundance",
            "[HYPO] 기름→꿀 풍요·지혜 motif 연쇄",
            ["oil", "honey"],
        ),
        _curated(
            "salt_to_light_preservative",
            "[HYPO] 소금→빛 보존·계시 motif 연쇄",
            ["salt", "light"],
        ),
        _curated(
            "ashes_to_healing_restoration",
            "[HYPO] 재→치유 회복·위로 motif 연쇄",
            ["ashes", "healing"],
        ),
        _curated(
            "dove_to_olive_covenant",
            "[HYPO] 비둘기→올리브 평화·언약 motif 연쇄",
            ["dove", "olive"],
        ),
        _curated(
            "fish_to_bread_provision",
            "[HYPO] 물고기→떡 공급·양육 motif 연쇄",
            ["fish", "bread"],
        ),
        _curated(
            "darkness_to_light_epiphany",
            "[HYPO] 어둠→빛 계시·해방 motif 연쇄",
            ["darkness", "light"],
        ),
        _curated(
            "eagle_to_rock_soar",
            "[HYPO] 독수리→반석 높이·피난 motif 연쇄",
            ["eagle", "rock"],
        ),
        _curated(
            "famine_to_manna_wilderness",
            "[HYPO] 기근→만나 광야 공급 motif 연쇄",
            ["famine", "manna"],
        ),
        _curated(
            "wheat_to_bread_harvest",
            "[HYPO] 밀→떡 수확·양식 motif 연쇄",
            ["wheat", "bread"],
        ),
        _curated(
            "cloak_to_shelter_refuge",
            "[HYPO] 겉옷→피난처 보호·은신 motif 연쇄",
            ["cloak", "shelter"],
        ),
        _curated(
            "cup_to_wine_covenant",
            "[HYPO] 잔→포도주 언약·나눔 motif 연쇄",
            ["cup", "wine"],
        ),
        _curated(
            "chains_to_deliverance_freedom",
            "[HYPO] 사슬→해방 구원·자유 motif 연쇄",
            ["chains", "deliverance"],
        ),
        _curated(
            "bitterness_to_honey_sweetness",
            "[HYPO] 쓴뿌리→꿀 달콤·치유 motif 연쇄",
            ["bitterness", "honey"],
        ),
        _curated(
            "blindness_to_healing_sight",
            "[HYPO] 맹목→치유 시각 회복 motif 연쇄",
            ["blindness", "healing"],
        ),
        _curated(
            "exile_to_harbor_return",
            "[HYPO] 유배→항구 귀환·피난 motif 연쇄",
            ["exile", "harbor"],
        ),
        _curated(
            "fortress_to_rock_bastion",
            "[HYPO] 요새→반석 견고·피난처 motif 연쇄",
            ["fortress", "rock"],
        ),
        _curated(
            "flood_judgment_to_ark_salvation",
            "[HYPO] 홍수 심판→방주 구원 motif 연쇄",
            ["flood_judgment", "ark"],
        ),
        _curated(
            "earthquake_to_rock_tremor",
            "[HYPO] 지진→반석 흔들림·견고 motif 연쇄",
            ["earthquake", "rock"],
        ),
        _curated(
            "fig_to_vine_parable",
            "[HYPO] 무화과→포도나무 비유·연결 motif 연쇄",
            ["fig", "vine"],
        ),
        _curated(
            "daily_bread_to_bread_petition",
            "[HYPO] 오늘 양식→떡 기도·공급 motif 연쇄",
            ["daily_bread", "bread"],
        ),
        _curated(
            "garment_to_cloak_covering",
            "[HYPO] 의복→겉옷 덮음·보호 motif 연쇄",
            ["garment", "cloak"],
        ),
        _curated(
            "furnace_to_fire_refinement",
            "[HYPO] 풀무→불 단련·정화 motif 연쇄",
            ["furnace", "fire"],
        ),
        _curated(
            "dark_cloud_to_light_stormbreak",
            "[HYPO] 먹은 구름→빛 폭풍·해방 motif 연쇄",
            ["dark_cloud", "light"],
        ),
        _curated(
            "curse_to_ashes_judgment",
            "[HYPO] 저주→재 심판·소멸 motif 연쇄",
            ["curse", "ashes"],
        ),
        _curated(
            "breastplate_to_shield_armor",
            "[HYPO] 흉배→방패 갑옷·보호 motif 연쇄",
            ["breastplate", "shield"],
        ),
        _curated(
            "deaf_to_healing_hearing",
            "[HYPO] 귀먹음→치유 청각 회복 motif 연쇄",
            ["deaf", "healing"],
        ),
        _curated(
            "mustard_to_seed_kingdom",
            "[HYPO] 겨자→씨앗 나라·성장 motif 연쇄",
            ["mustard", "seed"],
        ),
        _curated(
            "leaven_to_bread_ferment",
            "[HYPO] 누룩→떡 발효·퍼짐 motif 연쇄",
            ["leaven", "bread"],
        ),
        _curated(
            "milk_to_honey_nourishment",
            "[HYPO] 젖→꿀 양육·달콤함 motif 연쇄",
            ["milk", "honey"],
        ),
        _curated(
            "lion_to_shepherd_kingdom",
            "[HYPO] 사자→목자 왕·인도 motif 연쇄",
            ["lion", "shepherd"],
        ),
        _curated(
            "lamp_to_light_guidance",
            "[HYPO] 등불→빛 인도·계시 motif 연쇄",
            ["lamp", "light"],
        ),
        _curated(
            "leprosy_to_healing_cleansing",
            "[HYPO] 문둥병→치유 정결·회복 motif 연쇄",
            ["leprosy", "healing"],
        ),
        _curated(
            "nest_to_shelter_home",
            "[HYPO] 둥지→피난처 보금자리 motif 연쇄",
            ["nest", "shelter"],
        ),
        _curated(
            "helmet_to_shield_warfare",
            "[HYPO] 투구→방패 전쟁·보호 motif 연쇄",
            ["helmet", "shield"],
        ),
        _curated(
            "locust_to_famine_plague",
            "[HYPO] 메뚜기→기근 재앙·고난 motif 연쇄",
            ["locust", "famine"],
        ),
        _curated(
            "persecution_to_deliverance_trial",
            "[HYPO] 핍박→해방 시련·구원 motif 연쇄",
            ["persecution", "deliverance"],
        ),
        _curated(
            "net_to_fish_harvest",
            "[HYPO] 그물→물고기 수확·포획 motif 연쇄",
            ["net", "fish"],
        ),
        _curated(
            "gold_to_honey_treasure",
            "[HYPO] 금→꿀 보물·풍요 motif 연쇄",
            ["gold", "honey"],
        ),
        _curated(
            "hail_to_fire_judgment",
            "[HYPO] 우박→불 심판·재앙 motif 연쇄",
            ["hail", "fire"],
        ),
        _curated(
            "shadow_to_light_emergence",
            "[HYPO] 그늘→빛 출현·해방 motif 연쇄",
            ["shadow", "light"],
        ),
        _curated(
            "rest_to_still_waters_peace",
            "[HYPO] 안식→잔잔한 물 평안 motif 연쇄",
            ["rest", "still_waters"],
        ),
        _curated(
            "storm_to_rock_shelter",
            "[HYPO] 폭풍→반석 피난·견고 motif 연쇄",
            ["storm", "rock"],
        ),
        _curated(
            "spring_to_living_water_revival",
            "[HYPO] 샘→생수 부흥·갱신 motif 연쇄",
            ["spring", "living_water"],
        ),
        _curated(
            "serpent_to_cross_victory",
            "[HYPO] 뱀→십자가 승리·구원 motif 연쇄",
            ["serpent", "cross"],
        ),
        _curated(
            "stronghold_to_fortress_bastion",
            "[HYPO] 요새→성채 견고·방어 motif 연쇄",
            ["stronghold", "fortress"],
        ),
        _curated(
            "tribulation_to_deliverance_endurance",
            "[HYPO] 환난→해방 인내·구원 motif 연쇄",
            ["tribulation", "deliverance"],
        ),
        _curated(
            "weeping_to_healing_comfort",
            "[HYPO] 울음→치유 위로·회복 motif 연쇄",
            ["weeping", "healing"],
        ),
        _curated(
            "wing_to_eagle_shelter",
            "[HYPO] 날개→독수리 보호·피난 motif 연쇄",
            ["wing", "eagle"],
        ),
        _curated(
            "worm_to_ashes_humility",
            "[HYPO] 벌레→재 겸손·쇠퇴 motif 연쇄",
            ["worm", "ashes"],
        ),
        _curated(
            "sword_to_shield_warfare",
            "[HYPO] 칼→방패 전쟁·방어 motif 연쇄",
            ["sword", "shield"],
        ),
        _curated(
            "tower_to_fortress_watch",
            "[HYPO] 망대→요새 감시·견고 motif 연쇄",
            ["tower", "fortress"],
        ),
        _curated(
            "refuge_to_shelter_haven",
            "[HYPO] 피난처→대피소 안식 motif 연쇄",
            ["refuge", "shelter"],
        ),
        _curated(
            "millstone_to_rock_burden",
            "[HYPO] 맷돌→반석 짐·심판 motif 연쇄",
            ["millstone", "rock"],
        ),
        _curated(
            "death_to_cross_victory_redeemed",
            "[HYPO] 사망→십자가 승리·구속 motif 연쇄",
            ["death", "cross"],
        ),
        _curated(
            "anchor_rope_to_harbor_hope",
            "[HYPO] 닻줄→항구 소망·정박 motif 연쇄",
            ["anchor_rope", "harbor"],
        ),
        _curated(
            "rod_staff_to_staff_guidance",
            "[HYPO] 지팡이→막대 인도·목양 motif 연쇄",
            ["rod_staff", "staff"],
        ),
        _curated(
            "desolation_to_ashes_lament",
            "[HYPO] 황폐→재 애가·심판 motif 연쇄",
            ["desolation", "ashes"],
        ),
        _curated(
            "fire_unquenchable_to_fire_judgment",
            "[HYPO] 꺼지지 않는 불→불 심판 motif 연쇄",
            ["fire_unquenchable", "fire"],
        ),
        _curated(
            "fold_to_shepherd_gathering",
            "[HYPO] 우리→목자 모음·인도 motif 연쇄",
            ["fold", "shepherd"],
        ),
        _curated(
            "stumbling_to_rock_foundation",
            "[HYPO] 거침돌→반석 기초·견고 motif 연쇄",
            ["stumbling", "rock"],
        ),
        _curated(
            "table_to_bread_fellowship",
            "[HYPO] 상→떡 교제·양식 motif 연쇄",
            ["table", "bread"],
        ),
        _curated(
            "thorn_to_wound_suffering",
            "[HYPO] 가시→상처 고난·치유 motif 연쇄",
            ["thorn", "wound"],
        ),
        _curated(
            "treasure_to_gold_wealth",
            "[HYPO] 보물→금 부·영광 motif 연쇄",
            ["treasure", "gold"],
        ),
        _curated(
            "green_pasture_to_pasture_rest",
            "[HYPO] 푸른 초장→목장 안식 motif 연쇄",
            ["green_pasture", "pasture"],
        ),
        _curated(
            "pestilence_to_plague_affliction",
            "[HYPO] 전염병→재앙 고난 motif 연쇄",
            ["pestilence", "plague"],
        ),
        _curated(
            "vid_gen_1_1_to_gen_1_3_creation_light",
            "[HYPO][VERSE-ID-PILOT] 창조 서사 — 시작→빛 (verse-id 앵커)",
            ["gen_1_1", "gen_1_3"],
        ),
        _curated(
            "vid_gen_1_2_to_gen_1_6_firmament",
            "[HYPO][VERSE-ID-PILOT] 창조 서사 — 흑암→궁창",
            ["gen_1_2", "gen_1_6"],
        ),
        _curated(
            "vid_gen_1_9_to_gen_1_14_lights",
            "[HYPO][VERSE-ID-PILOT] 창조 서사 — 땅→광체",
            ["gen_1_9", "gen_1_14"],
        ),
        _curated(
            "vid_gen_1_20_to_gen_1_24_creature_kind",
            "[HYPO][VERSE-ID-PILOT] 창조 서사 — 생물→종류",
            ["gen_1_20", "gen_1_24"],
        ),
        _curated(
            "vid_gen_1_27_to_gen_1_28_image_blessing",
            "[HYPO][VERSE-ID-PILOT] 창조 서사 — 형상→축복",
            ["gen_1_27", "gen_1_28"],
        ),
        _curated(
            "vid_gen_2_5_to_gen_2_7_formed_life",
            "[HYPO][VERSE-ID-PILOT] 에덴 서사 — 물→사람",
            ["gen_2_5", "gen_2_7"],
        ),
        _curated(
            "vid_gen_3_9_to_gen_3_14_fall_judgment",
            "[HYPO][VERSE-ID-PILOT] 타락 서사 — 부르심→저주",
            ["gen_3_9", "gen_3_14"],
        ),
        _curated(
            "vid_gen_6_3_to_gen_7_1_flood_judgment",
            "[HYPO][VERSE-ID-PILOT] 홍수 서사 — 한숨→방주",
            ["gen_6_3", "gen_7_1"],
        ),
        _curated(
            "vid_gen_8_1_to_gen_8_7_dry_land",
            "[HYPO][VERSE-ID-PILOT] 홍수 후 — 기억→마른 땅",
            ["gen_8_1", "gen_8_7"],
        ),
        _curated(
            "vid_gen_9_18_to_gen_11_4_covenant_tower",
            "[HYPO][VERSE-ID-PILOT] 언약→바벨 (verse-id)",
            ["gen_9_18", "gen_11_4"],
        ),
        _curated(
            "vid_gen_15_5_to_gen_17_1_promise_covenant",
            "[HYPO][VERSE-ID-PILOT] 아브라함 서사 — 별→언약",
            ["gen_15_5", "gen_17_1"],
        ),
        _curated(
            "vid_gen_22_15_to_gen_25_23_sacrifice_line",
            "[HYPO][VERSE-ID-PILOT] 이삭→야곱 계보 (verse-id)",
            ["gen_22_15", "gen_25_23"],
        ),
        _curated(
            "vid_gen_28_17_to_gen_28_5_bethel_encounter",
            "[HYPO][VERSE-ID-PILOT] 벧엘 서사 — 사다리→약속",
            ["gen_28_17", "gen_28_5"],
        ),
        _curated(
            "vid_exod_21_20_to_exod_24_4_law_covenant",
            "[HYPO][VERSE-ID-PILOT] 율법 서사 — 판결→언약",
            ["exod_21_20", "exod_24_4"],
        ),
        _curated(
            "vid_acts_16_26_to_acts_25_9_mission_trial",
            "[HYPO][VERSE-ID-PILOT] 사도행전 — 갇힘→재판",
            ["acts_16_26", "acts_25_9"],
        ),
        _curated(
            "vid_deut_14_15_to_deut_26_15_statute_pledge",
            "[HYPO][VERSE-ID-PILOT] 신명 서사 — 규례→서원",
            ["deut_14_15", "deut_26_15"],
        ),
        _curated(
            "vid_matt_3_10_to_matt_3_15_baptism",
            "[HYPO][VERSE-ID-PILOT] 마태 — 도끼→세례",
            ["matt_3_10", "matt_3_15"],
        ),
        _curated(
            "vid_matt_4_4_to_matt_5_22_temptation_ethics",
            "[HYPO][VERSE-ID-PILOT] 마태 — 시험→율법",
            ["matt_4_4", "matt_5_22"],
        ),
        _curated(
            "vid_matt_11_4_to_matt_11_25_messenger",
            "[HYPO][VERSE-ID-PILOT] 마태 — 메시아→감사",
            ["matt_11_4", "matt_11_25"],
        ),
        _curated(
            "vid_matt_12_39_to_matt_12_48_sign_family",
            "[HYPO][VERSE-ID-PILOT] 마태 — 표적→가족",
            ["matt_12_39", "matt_12_48"],
        ),
        _curated(
            "vid_matt_14_28_to_matt_16_16_faith_confession",
            "[HYPO][VERSE-ID-PILOT] 마태 — 물위→시몬 고백",
            ["matt_14_28", "matt_16_16"],
        ),
        _curated(
            "vid_matt_17_4_to_matt_17_17_transfiguration",
            "[HYPO][VERSE-ID-PILOT] 마태 — 변화산→믿음",
            ["matt_17_4", "matt_17_17"],
        ),
        _curated(
            "vid_luke_1_19_to_luke_1_35_annunciation",
            "[HYPO][VERSE-ID-PILOT] 누가 — 가브리엘→성령",
            ["luke_1_19", "luke_1_35"],
        ),
        _curated(
            "vid_luke_4_8_to_luke_4_12_temptation_word",
            "[HYPO][VERSE-ID-PILOT] 누가 — 경배→말씀",
            ["luke_4_8", "luke_4_12"],
        ),
        _curated(
            "vid_luke_10_27_to_luke_10_42_love_mary",
            "[HYPO][VERSE-ID-PILOT] 누가 — 사랑→마리아",
            ["luke_10_27", "luke_10_42"],
        ),
        _curated(
            "vid_luke_22_36_to_luke_22_51_sword_ear",
            "[HYPO][VERSE-ID-PILOT] 누가 — 칼→귀",
            ["luke_22_36", "luke_22_51"],
        ),
        _curated(
            "vid_luke_23_3_to_luke_23_41_cross_penitent",
            "[HYPO][VERSE-ID-PILOT] 누가 — 십자가 선언→회개",
            ["luke_23_3", "luke_23_41"],
        ),
        _curated(
            "vid_rev_6_13_to_rev_6_14_seal_cosmos",
            "[HYPO][VERSE-ID-PILOT] 계시 — 인→하늘",
            ["rev_6_13", "rev_6_14"],
        ),
        _curated(
            "vid_rev_11_1_to_rev_11_6_two_witnesses",
            "[HYPO][VERSE-ID-PILOT] 계시 — 두 증인",
            ["rev_11_1", "rev_11_6"],
        ),
        _curated(
            "vid_rev_12_15_to_rev_14_18_dragon_harvest",
            "[HYPO][VERSE-ID-PILOT] 계시 — 용→추수",
            ["rev_12_15", "rev_14_18"],
        ),
        _curated(
            "vid_gen_13_14_to_gen_14_19_abram_call",
            "[HYPO][VERSE-ID-PILOT] 창세 — 땅→멜기세덱",
            ["gen_13_14", "gen_14_19"],
        ),
        _curated(
            "vid_gen_18_17_to_gen_19_14_sodom_warning",
            "[HYPO][VERSE-ID-PILOT] 창세 — 아브라함→소돔 경고",
            ["gen_18_17", "gen_19_14"],
        ),
        _curated(
            "vid_matt_12_47_to_matt_13_11_parables",
            "[HYPO][VERSE-ID-PILOT] 마태 — 가족→비유",
            ["matt_12_47", "matt_13_11"],
        ),
        _curated(
            "vid_matt_15_3_to_matt_15_28_syrophoenician",
            "[HYPO][VERSE-ID-PILOT] 마태 — 전통→수로보니게",
            ["matt_15_3", "matt_15_28"],
        ),
        _curated(
            "vid_matt_15_13_to_matt_15_24_mission",
            "[HYPO][VERSE-ID-PILOT] 마태 — 뿌리→선교",
            ["matt_15_13", "matt_15_24"],
        ),
        _curated(
            "vid_matt_21_24_to_matt_21_30_parable",
            "[HYPO][VERSE-ID-PILOT] 마태 — 두 아들→포도원",
            ["matt_21_24", "matt_21_30"],
        ),
        _curated(
            "vid_matt_22_1_to_matt_22_29_resurrection",
            "[HYPO][VERSE-ID-PILOT] 마태 — 혼인잔치→부활",
            ["matt_22_1", "matt_22_29"],
        ),
        _curated(
            "vid_matt_23_29_to_matt_23_35_woe",
            "[HYPO][VERSE-ID-PILOT] 마태 — 무덤→화",
            ["matt_23_29", "matt_23_35"],
        ),
        _curated(
            "vid_luke_10_41_to_luke_11_45_mary_pharisee",
            "[HYPO][VERSE-ID-PILOT] 누가 — 마리아→바리새",
            ["luke_10_41", "luke_11_45"],
        ),
        _curated(
            "vid_luke_13_2_to_luke_13_14_sabbath",
            "[HYPO][VERSE-ID-PILOT] 누가 — 갈릴리→안식",
            ["luke_13_2", "luke_13_14"],
        ),
        _curated(
            "vid_luke_13_8_to_luke_14_3_dining",
            "[HYPO][VERSE-ID-PILOT] 누가 — 무화과→안식 식사",
            ["luke_13_8", "luke_14_3"],
        ),
        _curated(
            "vid_luke_15_29_to_luke_17_14_ten_lepers",
            "[HYPO][VERSE-ID-PILOT] 누가 — 형→나병",
            ["luke_15_29", "luke_17_14"],
        ),
        _curated(
            "vid_rev_10_2_to_rev_11_1_little_book",
            "[HYPO][VERSE-ID-PILOT] 계시 — 작은 책→증인",
            ["rev_10_2", "rev_11_1"],
        ),
        _curated(
            "vid_rev_8_7_to_rev_8_12_trumpet",
            "[HYPO][VERSE-ID-PILOT] 계시 — 나팔→별",
            ["rev_8_7", "rev_8_12"],
        ),
        _curated(
            "vid_rev_18_8_to_rev_19_16_babylon",
            "[HYPO][VERSE-ID-PILOT] 계시 — 바벨론→왕",
            ["rev_18_8", "rev_19_16"],
        ),
        _curated(
            "vid_rev_18_22_to_rev_18_24_babylon_judgment",
            "[HYPO][VERSE-ID-PILOT] 계시 — 바벨론 심판",
            ["rev_18_22", "rev_18_24"],
        ),
        _curated(
            "vid_gen_1_5_to_gen_1_10_creation_day",
            "[HYPO][VERSE-ID-PILOT] 창세 — 빛→땅",
            ["gen_1_5", "gen_1_10"],
        ),
        _curated(
            "vid_gen_14_22_to_gen_17_3_covenant",
            "[HYPO][VERSE-ID-PILOT] 창세 — 맹세→언약",
            ["gen_14_22", "gen_17_3"],
        ),
        _curated(
            "vid_matt_15_15_to_matt_15_26_tradition",
            "[HYPO][VERSE-ID-PILOT] 마태 — 전통→믿음",
            ["matt_15_15", "matt_15_26"],
        ),
        _curated(
            "vid_matt_17_11_to_matt_17_12_elijah",
            "[HYPO][VERSE-ID-PILOT] 마태 — 엘리야→회복",
            ["matt_17_11", "matt_17_12"],
        ),
        _curated(
            "vid_matt_19_4_to_matt_19_27_marriage",
            "[HYPO][VERSE-ID-PILOT] 마태 — 혼인→천국",
            ["matt_19_4", "matt_19_27"],
        ),
        _curated(
            "vid_matt_24_2_to_matt_24_4_eschaton",
            "[HYPO][VERSE-ID-PILOT] 마태 — 성전→미혹",
            ["matt_24_2", "matt_24_4"],
        ),
        _curated(
            "vid_matt_25_12_to_matt_25_26_parables",
            "[HYPO][VERSE-ID-PILOT] 마태 — 등불→달란트",
            ["matt_25_12", "matt_25_26"],
        ),
        _curated(
            "vid_matt_26_23_to_matt_26_33_passion",
            "[HYPO][VERSE-ID-PILOT] 마태 — 배반→부인",
            ["matt_26_23", "matt_26_33"],
        ),
        _curated(
            "vid_luke_11_51_to_luke_17_17_prophets",
            "[HYPO][VERSE-ID-PILOT] 누가 — 선지→감사",
            ["luke_11_51", "luke_17_17"],
        ),
        _curated(
            "vid_luke_17_18_to_luke_19_40_samaritan",
            "[HYPO][VERSE-ID-PILOT] 누가 — 사마리아→찬양",
            ["luke_17_18", "luke_19_40"],
        ),
        _curated(
            "vid_luke_20_3_to_luke_20_4_authority",
            "[HYPO][VERSE-ID-PILOT] 누가 — 권위 질문",
            ["luke_20_3", "luke_20_4"],
        ),
        _curated(
            "vid_luke_23_40_to_luke_24_18_cross_road",
            "[HYPO][VERSE-ID-PILOT] 누가 — 십자가→엠마오",
            ["luke_23_40", "luke_24_18"],
        ),
        _curated(
            "vid_rev_9_13_to_rev_18_23_trumpet_babylon",
            "[HYPO][VERSE-ID-PILOT] 계시 — 나팔→바벨론",
            ["rev_9_13", "rev_18_23"],
        ),
        _curated(
            "vid_gen_1_7_to_gen_1_8_creation_waters",
            "[HYPO][VERSE-ID-PILOT] 창세 — 궁창→하늘",
            ["gen_1_7", "gen_1_8"],
        ),
        _curated(
            "vid_gen_19_24_to_gen_20_2_sodom_abimelech",
            "[HYPO][VERSE-ID-PILOT] 창세 — 소돔→아비멜렉",
            ["gen_19_24", "gen_20_2"],
        ),
        _curated(
            "vid_gen_24_1_to_gen_24_17_isaac_rebekah",
            "[HYPO][VERSE-ID-PILOT] 창세 — 이삭→리브가",
            ["gen_24_1", "gen_24_17"],
        ),
        _curated(
            "vid_gen_27_18_to_gen_27_41_jacob_deception",
            "[HYPO][VERSE-ID-PILOT] 창세 — 야곱→에서",
            ["gen_27_18", "gen_27_41"],
        ),
        _curated(
            "vid_jhn_19_32_to_jhn_19_34_blood_water",
            "[HYPO][VERSE-ID-PILOT] 요한 — 피와 물",
            ["jhn_19_32", "jhn_19_34"],
        ),
        _curated(
            "vid_matt_20_13_to_matt_21_29_vineyard",
            "[HYPO][VERSE-ID-PILOT] 마태 — 포도원→아들",
            ["matt_20_13", "matt_21_29"],
        ),
        _curated(
            "vid_matt_22_2_to_matt_23_30_wedding",
            "[HYPO][VERSE-ID-PILOT] 마태 — 혼인→무덤",
            ["matt_22_2", "matt_23_30"],
        ),
        _curated(
            "vid_matt_23_34_to_matt_25_27_woe",
            "[HYPO][VERSE-ID-PILOT] 마태 — 선지→달란트",
            ["matt_23_34", "matt_25_27"],
        ),
        _curated(
            "vid_matt_26_25_to_matt_27_21_judas",
            "[HYPO][VERSE-ID-PILOT] 마태 — 유다→바라바",
            ["matt_26_25", "matt_27_21"],
        ),
        _curated(
            "vid_matt_28_5_to_matt_3_11_resurrection",
            "[HYPO][VERSE-ID-PILOT] 마태 — 부활→세례",
            ["matt_28_5", "matt_3_11"],
        ),
        _curated(
            "vid_matt_5_23_to_matt_5_24_reconciliation",
            "[HYPO][VERSE-ID-PILOT] 마태 — 제물→화해",
            ["matt_5_23", "matt_5_24"],
        ),
        _curated(
            "vid_luke_3_11_to_luke_5_5_calling",
            "[HYPO][VERSE-ID-PILOT] 누가 — 나눔→어망",
            ["luke_3_11", "luke_5_5"],
        ),
        _curated(
            "vid_luke_5_22_to_luke_5_31_healing",
            "[HYPO][VERSE-ID-PILOT] 누가 — 중풍→세리",
            ["luke_5_22", "luke_5_31"],
        ),
        _curated(
            "vid_luke_6_3_to_luke_6_4_sabbath",
            "[HYPO][VERSE-ID-PILOT] 누가 — 안식 밀밭",
            ["luke_6_3", "luke_6_4"],
        ),
        _curated(
            "vid_luke_7_22_to_luke_8_21_messiah_family",
            "[HYPO][VERSE-ID-PILOT] 누가 — 메시아→가족",
            ["luke_7_22", "luke_8_21"],
        ),
        _curated(
            "vid_gen_20_8_to_gen_21_1_isaac_birth",
            "[HYPO][VERSE-ID-PILOT] 창세 — 아비멜렉→이삭",
            ["gen_20_8", "gen_21_1"],
        ),
        _curated(
            "vid_gen_21_14_to_gen_21_26_ishmael",
            "[HYPO][VERSE-ID-PILOT] 창세 — 이스마엘→우물",
            ["gen_21_14", "gen_21_26"],
        ),
        _curated(
            "vid_gen_23_3_to_gen_24_23_sarah_rebekah",
            "[HYPO][VERSE-ID-PILOT] 창세 — 사라→리브가",
            ["gen_23_3", "gen_24_23"],
        ),
        _curated(
            "vid_gen_1_25_to_gen_2_6_creation_man",
            "[HYPO][VERSE-ID-PILOT] 창세 — 피조→안개",
            ["gen_1_25", "gen_2_6"],
        ),
        _curated(
            "vid_heb_9_3_to_heb_9_14_tabernacle",
            "[HYPO][VERSE-ID-PILOT] 히브 — 성소→피",
            ["heb_9_3", "heb_9_14"],
        ),
        _curated(
            "vid_acts_5_29_to_acts_8_34_mission",
            "[HYPO][VERSE-ID-PILOT] 사도행전 — 순종→에티오피아",
            ["acts_5_29", "acts_8_34"],
        ),
        _curated(
            "vid_matt_7_19_to_matt_8_8_faith",
            "[HYPO][VERSE-ID-PILOT] 마태 — 믿음→고침",
            ["matt_7_19", "matt_8_8"],
        ),
        _curated(
            "vid_luke_5_23_to_luke_5_24_paralytic",
            "[HYPO][VERSE-ID-PILOT] 누가 — 중풍→일어남",
            ["luke_5_23", "luke_5_24"],
        ),
        _curated(
            "vid_luke_7_40_to_luke_7_43_forgiveness",
            "[HYPO][VERSE-ID-PILOT] 누가 — 죄 사함",
            ["luke_7_40", "luke_7_43"],
        ),
        _curated(
            "vid_luke_9_20_to_luke_9_49_messiah",
            "[HYPO][VERSE-ID-PILOT] 누가 — 그리스도→제자",
            ["luke_9_20", "luke_9_49"],
        ),
        _curated(
            "vid_gen_2_9_to_gen_2_19_eden",
            "[HYPO][VERSE-ID-PILOT] 창세 — 에덴→흙",
            ["gen_2_9", "gen_2_19"],
        ),
        _curated(
            "vid_gen_3_12_to_gen_3_23_fall",
            "[HYPO][VERSE-ID-PILOT] 창세 — 타락→추방",
            ["gen_3_12", "gen_3_23"],
        ),
        _curated(
            "vid_gen_4_11_to_gen_4_23_cain",
            "[HYPO][VERSE-ID-PILOT] 창세 — 가인→라멕",
            ["gen_4_11", "gen_4_23"],
        ),
        _curated(
            "vid_gen_6_7_to_gen_8_2_flood",
            "[HYPO][VERSE-ID-PILOT] 창세 — 홍수→방주",
            ["gen_6_7", "gen_8_2"],
        ),
        _curated(
            "vid_gen_21_15_to_gen_24_55_isaac",
            "[HYPO][VERSE-ID-PILOT] 창세 — 이삭→리브가",
            ["gen_21_15", "gen_24_55"],
        ),
        _curated(
            "vid_gen_27_31_to_gen_27_39_jacob",
            "[HYPO][VERSE-ID-PILOT] 창세 — 야곱→에서",
            ["gen_27_31", "gen_27_39"],
        ),
        _curated(
            "vid_gen_29_14_to_gen_37_14_joseph",
            "[HYPO][VERSE-ID-PILOT] 창세 — 라헬→요셉",
            ["gen_29_14", "gen_37_14"],
        ),
        _curated(
            "vid_gen_40_12_to_gen_41_14_dream",
            "[HYPO][VERSE-ID-PILOT] 창세 — 꿈→왕",
            ["gen_40_12", "gen_41_14"],
        ),
        _curated(
            "vid_gen_49_10_to_gen_49_28_blessing",
            "[HYPO][VERSE-ID-PILOT] 창세 — 지팡이→축복",
            ["gen_49_10", "gen_49_28"],
        ),
        _curated(
            "vid_lev_11_16_to_lev_11_29_clean",
            "[HYPO][VERSE-ID-PILOT] 레위 — 정결 규례",
            ["lev_11_16", "lev_11_29"],
        ),
        _curated(
            "vid_jer_8_2_to_jer_16_4_judgment",
            "[HYPO][VERSE-ID-PILOT] 예레 — 심판 예고",
            ["jer_8_2", "jer_16_4"],
        ),
        _curated(
            "vid_heb_9_4_to_heb_9_13_blood",
            "[HYPO][VERSE-ID-PILOT] 히브 — 금단→피",
            ["heb_9_4", "heb_9_13"],
        ),
        _curated(
            "vid_gen_2_20_to_gen_2_22_river",
            "[HYPO][VERSE-ID-PILOT] 창세 — 강→금",
            ["gen_2_20", "gen_2_22"],
        ),
        _curated(
            "vid_gen_3_17_to_gen_4_19_curse",
            "[HYPO][VERSE-ID-PILOT] 창세 — 저주→라멕",
            ["gen_3_17", "gen_4_19"],
        ),
        _curated(
            "vid_gen_5_29_to_gen_7_7_lineage",
            "[HYPO][VERSE-ID-PILOT] 창세 — 족보→홍수",
            ["gen_5_29", "gen_7_7"],
        ),
        _curated(
            "vid_gen_7_17_to_gen_7_18_ark",
            "[HYPO][VERSE-ID-PILOT] 창세 — 방주→물",
            ["gen_7_17", "gen_7_18"],
        ),
        _curated(
            "vid_gen_8_8_to_gen_8_16_dove",
            "[HYPO][VERSE-ID-PILOT] 창세 — 비둘기→무지개",
            ["gen_8_8", "gen_8_16"],
        ),
        _curated(
            "vid_gen_24_40_to_gen_24_56_rebekah",
            "[HYPO][VERSE-ID-PILOT] 창세 — 리브가→은",
            ["gen_24_40", "gen_24_56"],
        ),
        _curated(
            "vid_gen_25_30_to_gen_26_32_esau",
            "[HYPO][VERSE-ID-PILOT] 창세 — 에서→우물",
            ["gen_25_30", "gen_26_32"],
        ),
        _curated(
            "vid_gen_27_32_to_gen_27_33_blessing",
            "[HYPO][VERSE-ID-PILOT] 창세 — 축복→은혜",
            ["gen_27_32", "gen_27_33"],
        ),
        _curated(
            "vid_gen_29_25_to_gen_30_38_rachel",
            "[HYPO][VERSE-ID-PILOT] 창세 — 라헬→양",
            ["gen_29_25", "gen_30_38"],
        ),
        _curated(
            "vid_gen_33_5_to_gen_33_15_esau_meet",
            "[HYPO][VERSE-ID-PILOT] 창세 — 에서→선물",
            ["gen_33_5", "gen_33_15"],
        ),
        _curated(
            "vid_gen_37_21_to_gen_37_32_joseph_pit",
            "[HYPO][VERSE-ID-PILOT] 창세 — 구덩이→옷",
            ["gen_37_21", "gen_37_32"],
        ),
        _curated(
            "vid_gen_38_17_to_gen_38_20_tamar",
            "[HYPO][VERSE-ID-PILOT] 창세 — 다말→인",
            ["gen_38_17", "gen_38_20"],
        ),
        _curated(
            "vid_jhn_19_33_to_heb_9_5_passion",
            "[HYPO][VERSE-ID-PILOT] 요한→히브 — 십자가→언약",
            ["jhn_19_33", "heb_9_5"],
        ),
        _curated(
            "vid_luke_9_41_to_acts_8_24_gospel_mission",
            "[HYPO][VERSE-ID-PILOT] 누가→행전 — 세대→사마리아",
            ["luke_9_41", "acts_8_24"],
        ),
        _curated(
            "vid_lev_11_22_to_2sam_14_7_clean_king",
            "[HYPO][VERSE-ID-PILOT] 레위→사무엘 — 정결→왕",
            ["lev_11_22", "2sam_14_7"],
        ),
        _curated(
            "vid_2chr_6_25_to_hos_2_20_temple_covenant",
            "[HYPO][VERSE-ID-PILOT] 역대→호세아 — 성전→언약",
            ["2chr_6_25", "hos_2_20"],
        ),
        _curated(
            "vid_gen_24_65_to_gen_31_24_labans",
            "[HYPO][VERSE-ID-PILOT] 창세 — 리브가→라반",
            ["gen_24_65", "gen_31_24"],
        ),
        _curated(
            "vid_gen_2_21_to_gen_33_8_eden_jacob",
            "[HYPO][VERSE-ID-PILOT] 창세 — 에덴→야곱",
            ["gen_2_21", "gen_33_8"],
        ),
        _curated(
            "vid_gen_35_4_to_gen_40_18_bethel_dream",
            "[HYPO][VERSE-ID-PILOT] 창세 — 벧엘→꿈",
            ["gen_35_4", "gen_40_18"],
        ),
        _curated(
            "vid_gen_41_3_to_gen_41_8_pharaoh",
            "[HYPO][VERSE-ID-PILOT] 창세 — 바로→꿈",
            ["gen_41_3", "gen_41_8"],
        ),
        _curated(
            "vid_gen_42_21_to_gen_49_16_joseph_blessing",
            "[HYPO][VERSE-ID-PILOT] 창세 — 형제→축복",
            ["gen_42_21", "gen_49_16"],
        ),
        _curated(
            "vid_gen_7_4_to_gen_8_12_ark_waters",
            "[HYPO][VERSE-ID-PILOT] 창세 — 방주→비둘기",
            ["gen_7_4", "gen_8_12"],
        ),
        _curated(
            "vid_gen_8_13_to_gen_8_15_dry_land",
            "[HYPO][VERSE-ID-PILOT] 창세 — 마른 땅→언약",
            ["gen_8_13", "gen_8_15"],
        ),
        _curated(
            "vid_gen_8_19_to_gen_8_9_covenant_sign",
            "[HYPO][VERSE-ID-PILOT] 창세 — 무지개→제단",
            ["gen_8_19", "gen_8_9"],
        ),
    ):
        if item:
            samples.append(item)

    # Resonance-derived OT→NT sample
    ot_nt = [
        e
        for e in resonance_edges
        if "ot_to_nt_span" in str(e.get("reason") or "") and float(e.get("weight") or 0) >= 0.5
    ]
    if ot_nt:
        e = max(ot_nt, key=lambda row: float(row.get("weight") or 0))
        samples.append(
            {
                "sample_id": "resonance_ot_nt_top",
                "query_ko": "[HYPO] 앵커 공명 그래프 OT→NT 최고 가중 샘플",
                "hypothesis_class": "HYPO",
                "non_gating": True,
                "path": [
                    _path_hop(e["src_anchor_id"], by_id, 0),
                    _path_hop(e["dst_anchor_id"], by_id, 1),
                ],
                "edge_types": ["anchor_resonance_hypo"],
                "weight": e.get("weight"),
            }
        )
    return samples
