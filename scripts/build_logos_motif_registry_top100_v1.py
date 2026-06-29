#!/usr/bin/env python3
"""Build / refresh logos_motif_registry_top100_v1.json (100 slots, ~20 NL prefilled).

Reproducible:
  py scripts/build_logos_motif_registry_top100_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"
EXTENSIONS = ROOT / "docs/final/artifacts/logos_motif_human_gate_extensions_v1.json"
EXPANSION = ROOT / "docs/final/artifacts/logos_corpus_expansion_extensions_v1.json"
OVERLAY = ROOT / "docs/final/artifacts/logos_motif_corpus_enriched_overlay_v1.json"
BASE_SLOT_COUNT = 100

PREFILLED: list[dict[str, Any]] = [
    {
        "slot_id": "motif_001",
        "file_stem": "seed",
        "anchor_id": "cosmic_anchor_seed_jhn_12_24",
        "verse_refs": ["Jhn.12.24"],
        "category": "plant",
        "motif_lemma": {"greek": "σπερμα"},
        "gematria_text": "σπερμα",
        "gematria_texts": {
            "raw": (
                "αμην αμην λεγω υμιν εαν μη ο κοκκος του σιτου πεσων εις την γην "
                "αποθανη αυτος μονος μενει εαν δε αποθανη πολυν καρπον φερει"
            ),
            "compressed": "σπερμα",
            "reconstructed": "κοκκος σιτου πεσων εις την γην αποθανη",
        },
        "logos_summary_ko": "씨앗 motif — Jhn.12.24",
        "sasang_summary_ko": "응축·경계 motif (사상 card)",
        "constitution_hint": "none",
        "ohaeng_hint": "water",
        "source": "pilot_v1",
    },
    {
        "slot_id": "motif_002",
        "file_stem": "light",
        "anchor_id": "cosmic_anchor_light_jhn_1_5",
        "verse_refs": ["Jhn.1.5"],
        "category": "element",
        "motif_lemma": {"greek": "φως"},
        "gematria_text": "φως",
        "gematria_texts": {
            "raw": "και το φως εν τη σκοτια φαινει και η σκοτια αυτο ου κατελαβεν",
            "compressed": "φως",
            "reconstructed": "φως εν τη σκοτια φαινει",
        },
        "logos_summary_ko": "빛 motif — Jhn.1.5",
        "sasang_summary_ko": "화(火) 확장 motif (명리 accent)",
        "constitution_hint": "soeumin",
        "ohaeng_hint": "fire",
        "source": "pilot_v1",
    },
    {
        "slot_id": "motif_003",
        "file_stem": "way",
        "anchor_id": "cosmic_anchor_way_jhn_14_6",
        "verse_refs": ["Jhn.14.6"],
        "category": "path",
        "motif_lemma": {"greek": "οδος"},
        "gematria_text": "οδος",
        "gematria_texts": {
            "raw": (
                "λεγει αυτω ιησους εγω ειμι η οδος και η αληθεια και η ζωη "
                "ουδεις ερχεται προς τον πατερα ει μη δι εμου"
            ),
            "compressed": "οδος",
            "reconstructed": "εγω ειμι η οδος και η αληθεια",
        },
        "logos_summary_ko": "길 motif — Jhn.14.6",
        "sasang_summary_ko": "경로·프레임 motif (명리)",
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "source": "pilot_v1",
    },
    {
        "slot_id": "motif_004",
        "file_stem": "vine",
        "anchor_id": "cosmic_anchor_vine_jhn_15_1",
        "verse_refs": ["Jhn.15.1"],
        "category": "plant",
        "motif_lemma": {"greek": "αμπελος"},
        "gematria_text": "αμπελος",
        "gematria_texts": {
            "raw": "εγω ειμι η αμπελος η αληθινη και ο πατηρ μου ο γεωργος εστιν",
            "compressed": "αμπελος",
            "reconstructed": "εγω ειμι η αμπελος η αληθινη",
        },
        "logos_summary_ko": "포도나무 motif — Jhn.15.1",
        "sasang_summary_ko": "연결·가지 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "wood",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_005",
        "file_stem": "lamb",
        "anchor_id": "cosmic_anchor_lamb_jhn_1_29",
        "verse_refs": ["Jhn.1.29"],
        "category": "animal",
        "motif_lemma": {"greek": "αρνιον"},
        "gematria_text": "αρνιον",
        "gematria_texts": {
            "raw": "ιδε ο αμνος του θεου ο αιρων την αμαρτιαν του κοσμου",
            "compressed": "αρνιον",
            "reconstructed": "ο αμνος του θεου",
        },
        "logos_summary_ko": "양 motif — Jhn.1.29",
        "sasang_summary_ko": "순응·희생 motif",
        "constitution_hint": "soeumin",
        "ohaeng_hint": "metal",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_006",
        "file_stem": "lion",
        "anchor_id": "cosmic_anchor_lion_rev_5_5",
        "verse_refs": ["Rev.5.5"],
        "category": "animal",
        "motif_lemma": {"greek": "λεων"},
        "gematria_text": "λεων",
        "gematria_texts": {
            "raw": "ιδου ενικησεν ο λεων ο εκ της φυλης ιουδα",
            "compressed": "λεων",
            "reconstructed": "ο λεων ο εκ της φυλης ιουδα",
        },
        "logos_summary_ko": "사자 motif — Rev.5.5",
        "sasang_summary_ko": "권위·승리 motif",
        "constitution_hint": "taeyangin",
        "ohaeng_hint": "fire",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_007",
        "file_stem": "dove",
        "anchor_id": "cosmic_anchor_dove_mat_3_16",
        "verse_refs": ["Mat.3.16"],
        "category": "animal",
        "motif_lemma": {"greek": "περιστερα"},
        "gematria_text": "περιστερα",
        "gematria_texts": {
            "raw": "και ιδου ανεωχθησαν οι ουρανοι και ειδεν το πνευμα του θεου καταβαινον ωσει περιστεραν",
            "compressed": "περιστερα",
            "reconstructed": "το πνευμα καταβαινον ωσει περιστεραν",
        },
        "logos_summary_ko": "비둘기 motif — Mat.3.16",
        "sasang_summary_ko": "평화·성령 motif",
        "constitution_hint": "soeumin",
        "ohaeng_hint": "water",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_008",
        "file_stem": "bread",
        "anchor_id": "cosmic_anchor_bread_jhn_6_35",
        "verse_refs": ["Jhn.6.35"],
        "category": "food",
        "motif_lemma": {"greek": "αρτος"},
        "gematria_text": "αρτος",
        "gematria_texts": {
            "raw": "εγω ειμι ο αρτος της ζωης",
            "compressed": "αρτος",
            "reconstructed": "ο αρτος της ζωης",
        },
        "logos_summary_ko": "떡 motif — Jhn.6.35",
        "sasang_summary_ko": "양육· sustenance motif",
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_009",
        "file_stem": "water",
        "anchor_id": "cosmic_anchor_water_jhn_4_14",
        "verse_refs": ["Jhn.4.14"],
        "category": "element",
        "motif_lemma": {"greek": "υδωρ"},
        "gematria_text": "υδωρ",
        "gematria_texts": {
            "raw": "ο δε μοι πιειν δωσει υδωρ ζων",
            "compressed": "υδωρ",
            "reconstructed": "υδωρ ζων",
        },
        "logos_summary_ko": "물 motif — Jhn.4.14",
        "sasang_summary_ko": "순환·생명 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "water",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_010",
        "file_stem": "salt",
        "anchor_id": "cosmic_anchor_salt_mat_5_13",
        "verse_refs": ["Mat.5.13"],
        "category": "element",
        "motif_lemma": {"greek": "αλας"},
        "gematria_text": "αλας",
        "gematria_texts": {
            "raw": "υμεις εστε το αλας της γης",
            "compressed": "αλας",
            "reconstructed": "το αλας της γης",
        },
        "logos_summary_ko": "소금 motif — Mat.5.13",
        "sasang_summary_ko": "보존·경계 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "metal",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_011",
        "file_stem": "wheat",
        "anchor_id": "cosmic_anchor_wheat_mat_13_25",
        "verse_refs": ["Mat.13.25"],
        "category": "plant",
        "motif_lemma": {"greek": "σιτος"},
        "gematria_text": "σιτος",
        "gematria_texts": {
            "raw": "εν δε τω καθευδειν τους ανθρωπους ηλθεν ο εχθρος και επεσπειρεν ζιζανια ανα μεσον του σιτου",
            "compressed": "σιτος",
            "reconstructed": "ζιζανια ανα μεσον του σιτου",
        },
        "logos_summary_ko": "밀 motif — Mat.13.25",
        "sasang_summary_ko": "수확·구분 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_012",
        "file_stem": "fig",
        "anchor_id": "cosmic_anchor_fig_mar_11_13",
        "verse_refs": ["Mar.11.13"],
        "category": "plant",
        "motif_lemma": {"greek": "συκη"},
        "gematria_text": "συκη",
        "gematria_texts": {
            "raw": "και ιδων συκην απο μακροθεν εχουσαν φυλλα ηλθεν ει μη τι ευρησει εν αυτη",
            "compressed": "συκη",
            "reconstructed": "συκην εχουσαν φυλλα",
        },
        "logos_summary_ko": "무화과 motif — Mar.11.13",
        "sasang_summary_ko": "열매·시기 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "wood",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_013",
        "file_stem": "olive",
        "anchor_id": "cosmic_anchor_olive_rom_11_17",
        "verse_refs": ["Rom.11.17"],
        "category": "plant",
        "motif_lemma": {"greek": "ελαια"},
        "gematria_text": "ελαια",
        "gematria_texts": {
            "raw": "ει δε τινες των κλαδων εκκλασθησαν συ δε αγριελαιος ων ενεκεντρισθης εις αυτην",
            "compressed": "ελαια",
            "reconstructed": "αγριελαιος ενεκεντρισθης",
        },
        "logos_summary_ko": "올리브 motif — Rom.11.17",
        "sasang_summary_ko": "접붙임·연결 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "wood",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_014",
        "file_stem": "serpent",
        "anchor_id": "cosmic_anchor_serpent_jhn_3_14",
        "verse_refs": ["Jhn.3.14"],
        "category": "animal",
        "motif_lemma": {"greek": "οφις"},
        "gematria_text": "οφις",
        "gematria_texts": {
            "raw": "και καθως μωσης υψωσεν τον οφιν εν τη ερημω",
            "compressed": "οφις",
            "reconstructed": "μωσης υψωσεν τον οφιν",
        },
        "logos_summary_ko": "뱀 motif — Jhn.3.14",
        "sasang_summary_ko": "치유·역전 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "fire",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_015",
        "file_stem": "rock",
        "anchor_id": "cosmic_anchor_rock_mat_16_18",
        "verse_refs": ["Mat.16.18"],
        "category": "element",
        "motif_lemma": {"greek": "πετρα"},
        "gematria_text": "πετρα",
        "gematria_texts": {
            "raw": "και εγω δε σοι λεγω οτι συ ει πετρος και επι ταυτη τη πετρα οικοδομησω μου την εκκλησιαν",
            "compressed": "πετρα",
            "reconstructed": "επι ταυτη τη πετρα οικοδομησω",
        },
        "logos_summary_ko": "반석 motif — Mat.16.18",
        "sasang_summary_ko": "기초·안정 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_016",
        "file_stem": "shepherd",
        "anchor_id": "cosmic_anchor_shepherd_jhn_10_11",
        "verse_refs": ["Jhn.10.11"],
        "category": "role",
        "motif_lemma": {"greek": "ποιμην"},
        "gematria_text": "ποιμην",
        "gematria_texts": {
            "raw": "εγω ειμι ο ποιμην ο καλος",
            "compressed": "ποιμην",
            "reconstructed": "ο ποιμην ο καλος",
        },
        "logos_summary_ko": "목자 motif — Jhn.10.11",
        "sasang_summary_ko": "돌봄·인도 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_017",
        "file_stem": "mustard",
        "anchor_id": "cosmic_anchor_mustard_mat_13_31",
        "verse_refs": ["Mat.13.31"],
        "category": "plant",
        "motif_lemma": {"greek": "σιναπι"},
        "gematria_text": "σιναπι",
        "gematria_texts": {
            "raw": "ομοια εστιν η βασιλεια των ουρανων κοκκω σιναπεως",
            "compressed": "σιναπι",
            "reconstructed": "κοκκω σιναπεως",
        },
        "logos_summary_ko": "겨자 motif — Mat.13.31",
        "sasang_summary_ko": "작은 시작·확장 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "wood",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_018",
        "file_stem": "leaven",
        "anchor_id": "cosmic_anchor_leaven_mat_13_33",
        "verse_refs": ["Mat.13.33"],
        "category": "food",
        "motif_lemma": {"greek": "ζυμη"},
        "gematria_text": "ζυμη",
        "gematria_texts": {
            "raw": "ομοια εστιν η βασιλεια των ουρανων ζυμη",
            "compressed": "ζυμη",
            "reconstructed": "η βασιλεια των ουρανων ζυμη",
        },
        "logos_summary_ko": "누룩 motif — Mat.13.33",
        "sasang_summary_ko": "은밀 확산 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_019",
        "file_stem": "net",
        "anchor_id": "cosmic_anchor_net_mat_13_47",
        "verse_refs": ["Mat.13.47"],
        "category": "tool",
        "motif_lemma": {"greek": "δικτυον"},
        "gematria_text": "δικτυον",
        "gematria_texts": {
            "raw": "παλιν ομοια εστιν η βασιλεια των ουρανων σαγηνη",
            "compressed": "δικτυον",
            "reconstructed": "η βασιλεια σαγηνη",
        },
        "logos_summary_ko": "그물 motif — Mat.13.47",
        "sasang_summary_ko": "선별·수확 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "water",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_020",
        "file_stem": "fish",
        "anchor_id": "cosmic_anchor_fish_mat_4_19",
        "verse_refs": ["Mat.4.19"],
        "category": "animal",
        "motif_lemma": {"greek": "ιχθυς"},
        "gematria_text": "ιχθυς",
        "gematria_texts": {
            "raw": "δευτε οπισω μου και ποιησω υμας αλιεις ανθρωπων",
            "compressed": "ιχθυς",
            "reconstructed": "αλιεις ανθρωπων",
        },
        "logos_summary_ko": "물고기 motif — Mat.4.19",
        "sasang_summary_ko": "부르심·수확 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "water",
        "source": "nl_prefilled",
    },
    {
        "slot_id": "motif_021",
        "file_stem": "eagle",
        "anchor_id": "cosmic_anchor_eagle_rev_4_7",
        "verse_refs": ["Rev.4.7"],
        "category": "animal",
        "motif_lemma": {"greek": "αετος"},
        "gematria_text": "αετος",
        "gematria_texts": {
            "raw": "και το τεταρτον ζωον ομοιον αετω πετομενω",
            "compressed": "αετος",
            "reconstructed": "ομοιον αετω πετομενω",
        },
        "logos_summary_ko": "독수리 motif — Rev.4.7",
        "sasang_summary_ko": "승리·비상 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "fire",
        "source": "nl_lens_logos_top30",
    },
    {
        "slot_id": "motif_022",
        "file_stem": "lamp",
        "anchor_id": "cosmic_anchor_lamp_mat_5_15",
        "verse_refs": ["Mat.5.15"],
        "category": "tool",
        "motif_lemma": {"greek": "λυχνος"},
        "gematria_text": "λυχνος",
        "gematria_texts": {
            "raw": "ουδε καιουσιν λυχνον και τιθεασιν αυτον υπο τον μοδιον",
            "compressed": "λυχνος",
            "reconstructed": "λυχνον υπο τον μοδιον",
        },
        "logos_summary_ko": "등불 motif — Mat.5.15",
        "sasang_summary_ko": "국지 조명 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "fire",
        "source": "nl_lens_logos_top30",
    },
    {
        "slot_id": "motif_023",
        "file_stem": "door",
        "anchor_id": "cosmic_anchor_door_jhn_10_9",
        "verse_refs": ["Jhn.10.9"],
        "category": "path",
        "motif_lemma": {"greek": "θυρα"},
        "gematria_text": "θυρα",
        "gematria_texts": {
            "raw": "εγω ειμι η θυρα δι εμου εαν τις εισελθη σωθησεται",
            "compressed": "θυρα",
            "reconstructed": "εγω ειμι η θυρα",
        },
        "logos_summary_ko": "문 motif — Jhn.10.9",
        "sasang_summary_ko": "통제·authority motif",
        "constitution_hint": "none",
        "ohaeng_hint": "metal",
        "source": "nl_lens_logos_top30",
    },
    {
        "slot_id": "motif_024",
        "file_stem": "treasure",
        "anchor_id": "cosmic_anchor_treasure_mat_13_44",
        "verse_refs": ["Mat.13.44"],
        "category": "object",
        "motif_lemma": {"greek": "θησαυρος"},
        "gematria_text": "θησαυρος",
        "gematria_texts": {
            "raw": "ομοια εστιν η βασιλεια των ουρανων θησαυρω κεκρυμμενω",
            "compressed": "θησαυρος",
            "reconstructed": "θησαυρω κεκρυμμενω",
        },
        "logos_summary_ko": "보화 motif — Mat.13.44",
        "sasang_summary_ko": "가치·헌신 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "source": "nl_lens_logos_top30",
    },
    {
        "slot_id": "motif_025",
        "file_stem": "wine",
        "anchor_id": "cosmic_anchor_wine_mat_9_17",
        "verse_refs": ["Mat.9.17"],
        "category": "food",
        "motif_lemma": {"greek": "οινος"},
        "gematria_text": "οινος",
        "gematria_texts": {
            "raw": "ουδεις βαλλει οινον νεον εις ασκους παλαιους",
            "compressed": "οινος",
            "reconstructed": "οινον νεον εις ασκους",
        },
        "logos_summary_ko": "포도주 motif — Mat.9.17",
        "sasang_summary_ko": "갱신·언약 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "fire",
        "source": "nl_lens_logos_top30",
    },
    {
        "slot_id": "motif_026",
        "file_stem": "blood",
        "anchor_id": "cosmic_anchor_blood_mat_26_28",
        "verse_refs": ["Mat.26.28"],
        "category": "element",
        "motif_lemma": {"greek": "αιμα"},
        "gematria_text": "αιμα",
        "gematria_texts": {
            "raw": "τουτο γαρ εστιν το αιμα μου της καινης διαθηκης",
            "compressed": "αιμα",
            "reconstructed": "το αιμα μου της καινης διαθηκης",
        },
        "logos_summary_ko": "피 motif — Mat.26.28",
        "sasang_summary_ko": "언약·전환 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "water",
        "source": "nl_lens_logos_top30",
    },
    {
        "slot_id": "motif_027",
        "file_stem": "oil",
        "anchor_id": "cosmic_anchor_oil_mat_25_4",
        "verse_refs": ["Mat.25.4"],
        "category": "element",
        "motif_lemma": {"greek": "ελαιον"},
        "gematria_text": "ελαιον",
        "gematria_texts": {
            "raw": "αι δε φρονιμοι ελαβον ελαιον εν τοις αγγειοις μετα των λαμπαδων αυτων",
            "compressed": "ελαιον",
            "reconstructed": "ελαιον εν τοις αγγειοις",
        },
        "logos_summary_ko": "기름 motif — Mat.25.4",
        "sasang_summary_ko": "성화·지속 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "wood",
        "source": "nl_lens_logos_top30",
    },
    {
        "slot_id": "motif_028",
        "file_stem": "gold",
        "anchor_id": "cosmic_anchor_gold_rev_21_18",
        "verse_refs": ["Rev.21.18"],
        "category": "metal",
        "motif_lemma": {"greek": "χρυσος"},
        "gematria_text": "χρυσος",
        "gematria_texts": {
            "raw": "και η ενδωμησις του τειχους αυτης λιθος χρυσος καθαρος",
            "compressed": "χρυσος",
            "reconstructed": "λιθος χρυσος καθαρος",
        },
        "logos_summary_ko": "금 motif — Rev.21.18",
        "sasang_summary_ko": "영광·거룩 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "metal",
        "source": "nl_lens_logos_top30",
    },
    {
        "slot_id": "motif_029",
        "file_stem": "cross",
        "anchor_id": "cosmic_anchor_cross_1co_1_18",
        "verse_refs": ["1Co.1.18"],
        "category": "object",
        "motif_lemma": {"greek": "σταυρος"},
        "gematria_text": "σταυρος",
        "gematria_texts": {
            "raw": "ο λογος γαρ ο του σταυρου τοις μεν απολλυμενοις μωρια εστιν",
            "compressed": "σταυρος",
            "reconstructed": "ο λογος του σταυρου",
        },
        "logos_summary_ko": "십자가 motif — 1Co.1.18",
        "sasang_summary_ko": "대속·자아 소멸 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "metal",
        "source": "nl_lens_logos_top30",
    },
    {
        "slot_id": "motif_030",
        "file_stem": "star",
        "anchor_id": "cosmic_anchor_star_rev_22_16",
        "verse_refs": ["Rev.22.16"],
        "category": "element",
        "motif_lemma": {"greek": "αστηρ"},
        "gematria_text": "αστηρ",
        "gematria_texts": {
            "raw": "εγω ειμι ο ριζα και το γενος του δαυιδ ο αστηρ ο λαμπρος ο πρωινος",
            "compressed": "αστηρ",
            "reconstructed": "ο αστηρ ο λαμπρος ο πρωινος",
        },
        "logos_summary_ko": "별 motif — Rev.22.16",
        "sasang_summary_ko": "천상 노드·지도 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "fire",
        "source": "nl_lens_logos_top30",
    },
    {
        "slot_id": "motif_031",
        "file_stem": "death",
        "anchor_id": "cosmic_anchor_death_rev_1_18",
        "verse_refs": ["Rev.1.18"],
        "category": "pathology",
        "primitive_bias": "pathology",
        "motif_lemma": {"greek": "θανατος"},
        "gematria_text": "θανατος",
        "gematria_texts": {
            "raw": "εγω ειμι ο ζων και εγενομην νεκρος και ιδου ζων ειμι εις τους αιωνας",
            "compressed": "θανατος",
            "reconstructed": "εγενομην νεκρος",
        },
        "logos_summary_ko": "사망 motif — Rev.1.18 [human_gate pathology]",
        "sasang_summary_ko": "병증·전환 경계 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "metal",
        "source": "human_gate_wave25",
    },
    {
        "slot_id": "motif_032",
        "file_stem": "worm",
        "anchor_id": "cosmic_anchor_worm_mar_9_48",
        "verse_refs": ["Mar.9.48"],
        "category": "pathology",
        "primitive_bias": "pathology",
        "motif_lemma": {"greek": "σκωληξ"},
        "gematria_text": "σκωληξ",
        "gematria_texts": {
            "raw": "οπου ο σκωληξ αυτων ου τελευτα και το πυρ ου σβεννυται",
            "compressed": "σκωληξ",
            "reconstructed": "ο σκωληξ ου τελευτα",
        },
        "logos_summary_ko": "벌레 motif — Mar.9.48 [human_gate pathology]",
        "sasang_summary_ko": "부패·지속 손상 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "source": "human_gate_wave25",
    },
    {
        "slot_id": "motif_033",
        "file_stem": "thorn",
        "anchor_id": "cosmic_anchor_thorn_mat_27_29",
        "verse_refs": ["Mat.27.29"],
        "category": "pathology",
        "primitive_bias": "pathology",
        "motif_lemma": {"greek": "ακανθα"},
        "gematria_text": "ακανθα",
        "gematria_texts": {
            "raw": "και πλεξαντες στεφανον εξ ακανθων επεθηκαν επι της κεφαλης αυτου",
            "compressed": "ακανθα",
            "reconstructed": "στεφανον εξ ακανθων",
        },
        "logos_summary_ko": "가시 motif — Mat.27.29 [human_gate pathology]",
        "sasang_summary_ko": "고통·압박 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "metal",
        "source": "human_gate_wave25",
    },
    {
        "slot_id": "motif_034",
        "file_stem": "darkness",
        "anchor_id": "cosmic_anchor_darkness_mat_27_45",
        "verse_refs": ["Mat.27.45"],
        "category": "pathology",
        "primitive_bias": "pathology",
        "motif_lemma": {"greek": "σκοτος"},
        "gematria_text": "σκοτος",
        "gematria_texts": {
            "raw": "σκοτος δε εγενετο επι πασαν την γην απο ωρας εκτης εως ωρας ενατης",
            "compressed": "σκοτος",
            "reconstructed": "σκοτος επι πασαν την γην",
        },
        "logos_summary_ko": "어둠 motif — Mat.27.45 [human_gate pathology]",
        "sasang_summary_ko": "가림·단절 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "water",
        "source": "human_gate_wave25",
    },
    {
        "slot_id": "motif_035",
        "file_stem": "sword",
        "anchor_id": "cosmic_anchor_sword_mat_10_34",
        "verse_refs": ["Mat.10.34"],
        "category": "pathology",
        "primitive_bias": "pathology",
        "motif_lemma": {"greek": "μαχαιρα"},
        "gematria_text": "μαχαιρα",
        "gematria_texts": {
            "raw": "μη νομισητε οτι ηλθον βαλειν ειρηνην αλλα μαχαιραν",
            "compressed": "μαχαιρα",
            "reconstructed": "ηλθον βαλειν μαχαιραν",
        },
        "logos_summary_ko": "칼 motif — Mat.10.34 [human_gate pathology]",
        "sasang_summary_ko": "분열·긴장 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "metal",
        "source": "human_gate_wave25",
    },
    {
        "slot_id": "motif_036",
        "file_stem": "manna",
        "anchor_id": "cosmic_anchor_manna_exo_16_15",
        "verse_refs": ["Exo.16.15"],
        "category": "survival",
        "primitive_bias": "survival",
        "motif_lemma": {"hebrew": "מן"},
        "gematria_text": "מן",
        "gematria_texts": {
            "raw": "מן הוא כי אמרו מן הוא",
            "compressed": "מן",
            "reconstructed": "מן הוא",
        },
        "logos_summary_ko": "만나 motif — Exo.16.15 [human_gate survival]",
        "sasang_summary_ko": "광야 양육·생존 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "source": "human_gate_wave25",
    },
    {
        "slot_id": "motif_037",
        "file_stem": "ark",
        "anchor_id": "cosmic_anchor_ark_gen_6_14",
        "verse_refs": ["Gen.6.14"],
        "category": "survival",
        "primitive_bias": "survival",
        "motif_lemma": {"hebrew": "תבה"},
        "gematria_text": "תבה",
        "gematria_texts": {
            "raw": "עשה לך תבת עצי גפר",
            "compressed": "תבה",
            "reconstructed": "עשה לך תבת",
        },
        "logos_summary_ko": "방주 motif — Gen.6.14 [human_gate survival]",
        "sasang_summary_ko": "대피·보존 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "wood",
        "source": "human_gate_wave25",
    },
    {
        "slot_id": "motif_038",
        "file_stem": "refuge",
        "anchor_id": "cosmic_anchor_refuge_psa_91_2",
        "verse_refs": ["Psa.91.2"],
        "category": "survival",
        "primitive_bias": "survival",
        "motif_lemma": {"hebrew": "מחסה"},
        "gematria_text": "מחסה",
        "gematria_texts": {
            "raw": "אמר ליהוה מחסי ומצודתי",
            "compressed": "מחסה",
            "reconstructed": "מחסי ומצודתי",
        },
        "logos_summary_ko": "피난처 motif — Psa.91.2 [human_gate survival]",
        "sasang_summary_ko": "보호·경계 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "earth",
        "source": "human_gate_wave25",
    },
    {
        "slot_id": "motif_039",
        "file_stem": "shield",
        "anchor_id": "cosmic_anchor_shield_psa_3_3",
        "verse_refs": ["Psa.3.3"],
        "category": "survival",
        "primitive_bias": "survival",
        "motif_lemma": {"hebrew": "מגן"},
        "gematria_text": "מגן",
        "gematria_texts": {
            "raw": "ואתה יהוה מגן בעדי",
            "compressed": "מגן",
            "reconstructed": "יהוה מגן בעדי",
        },
        "logos_summary_ko": "방패 motif — Psa.3.3 [human_gate survival]",
        "sasang_summary_ko": "방어·생존 motif",
        "constitution_hint": "none",
        "ohaeng_hint": "metal",
        "source": "human_gate_wave25",
    },
    {
        "slot_id": "motif_040",
        "file_stem": "rest",
        "anchor_id": "cosmic_anchor_rest_mat_11_28",
        "verse_refs": ["Mat.11.28"],
        "category": "survival",
        "primitive_bias": "survival",
        "motif_lemma": {"greek": "αναπαυσις"},
        "gematria_text": "αναπαυσις",
        "gematria_texts": {
            "raw": "δευτε προς με παντες οι κοπιωντες και πεφορτισμενοι καγω αναπαυσω υμας",
            "compressed": "αναπαυσις",
            "reconstructed": "καγω αναπαυσω υμας",
        },
        "logos_summary_ko": "안식 motif — Mat.11.28 [human_gate survival]",
        "sasang_summary_ko": "회복·완충 motif",
        "constitution_hint": "soeumin",
        "ohaeng_hint": "water",
        "source": "human_gate_wave25",
    },
]


def _placeholder(slot_num: int) -> dict[str, Any]:
    sid = f"motif_{slot_num:03d}"
    return {
        "slot_id": sid,
        "enabled": False,
        "file_stem": None,
        "anchor_id": None,
        "verse_refs": [],
        "category": "reserved",
        "motif_lemma": {},
        "source": "placeholder",
        "notes_ko": "human_gate: lemma·verse 채우기 전까지 비활성",
    }


def _load_extensions() -> dict[str, dict[str, Any]]:
    if not EXTENSIONS.is_file():
        return {}
    data = json.loads(EXTENSIONS.read_text(encoding="utf-8"))
    return {e["slot_id"]: e for e in data.get("entries", []) if e.get("slot_id")}


def _load_expansion() -> dict[str, dict[str, Any]]:
    if not EXPANSION.is_file():
        return {}
    data = json.loads(EXPANSION.read_text(encoding="utf-8"))
    return {e["slot_id"]: e for e in data.get("entries", []) if e.get("slot_id")}


def _max_slot_num(*maps: dict[str, dict[str, Any]]) -> int:
    nums = [BASE_SLOT_COUNT]
    for m in maps:
        for sid in m:
            if sid.startswith("motif_"):
                nums.append(int(sid.split("_")[1]))
    return max(nums)


def _load_overlay() -> dict[str, dict[str, Any]]:
    if not OVERLAY.is_file():
        return {}
    data = json.loads(OVERLAY.read_text(encoding="utf-8"))
    return {e["slot_id"]: e for e in data.get("entries", []) if e.get("slot_id")}


def build_registry() -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    extensions = _load_extensions()
    expansion = _load_expansion()
    overlay = _load_overlay()
    max_slot = _max_slot_num(extensions, expansion, overlay)
    by_slot: dict[str, dict[str, Any]] = {}
    for spec in PREFILLED:
        by_slot[spec["slot_id"]] = dict(spec)
    for slot_id, spec in extensions.items():
        by_slot[slot_id] = dict(spec)
    for slot_id, spec in expansion.items():
        by_slot[slot_id] = dict(spec)
    for slot_id, patch in overlay.items():
        if slot_id in by_slot:
            merged = dict(by_slot[slot_id])
            merged.update(patch)
            by_slot[slot_id] = merged
        else:
            by_slot[slot_id] = dict(patch)
    entries: list[dict[str, Any]] = []
    for n in range(1, max_slot + 1):
        sid = f"motif_{n:03d}"
        if sid in by_slot:
            row = dict(by_slot[sid])
            row["enabled"] = True
            entries.append(row)
        else:
            entries.append(_placeholder(n))
    ext_count = len(extensions)
    exp_count = len(expansion)
    overlay_count = len(overlay)
    return {
        "schema": "logos_motif_registry_top100_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "slot_count": max_slot,
        "enabled_count": sum(1 for e in entries if e.get("enabled")),
        "prefilled_count": len(PREFILLED),
        "human_gate_extension_count": ext_count,
        "corpus_expansion_extension_count": exp_count,
        "corpus_overlay_count": overlay_count,
        "placeholder_count": sum(1 for e in entries if not e.get("enabled")),
        "entries": entries,
        "reproducible_command": "py scripts/build_logos_motif_registry_top100_v1.py",
        "extensions_path": EXTENSIONS.relative_to(ROOT).as_posix() if ext_count else None,
        "expansion_path": EXPANSION.relative_to(ROOT).as_posix() if exp_count else None,
        "corpus_overlay_path": OVERLAY.relative_to(ROOT).as_posix() if overlay_count else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    registry = build_registry()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"  enabled={registry['enabled_count']} placeholder={registry['placeholder_count']}")
    if registry.get("human_gate_extension_count"):
        print(f"  human_gate_extensions={registry['human_gate_extension_count']}")
    if registry.get("corpus_expansion_extension_count"):
        print(f"  corpus_expansion={registry['corpus_expansion_extension_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
