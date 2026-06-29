"""[HYPO] Coordinator science kernel v2 — scalar loss + lens disagreement proxy."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.nextgen_latent_codec_v1 import WORD_RE, jaccard_text, token_salience

WORD_RE_LOCAL = WORD_RE

SASANG_HINTS = frozenset(
    {
        "sasang",
        "taeeum",
        "soeumin",
        "taeyang",
        "soyang",
        "사상",
        "체질",
        "태음",
        "소음",
        "소양",
        "태양",
        "사상의학",
    }
)

MYEONGNI_HINTS = frozenset(
    {
        "myeongri",
        "myeongni",
        "manseryeok",
        "four_pillars",
        "명리",
        "사주",
        "팔자",
        "오행",
        "천간",
        "지지",
        "간지",
        "십성",
        "대운",
        "세운",
        "만세력",
    }
)


def compute_coordinator_loss(
    *,
    saving: float,
    jaccard: float,
    byte_exact_violation: float,
    disagreement: float,
    w_s: float = 1.0,
    w_j: float = 2.0,
    lambda_disagreement: float = 0.5,
    mu_byte_exact: float = 1000.0,
    j_target: float = 0.89,
) -> float:
    j_gap = max(0.0, j_target - jaccard)
    return (
        w_s * (1.0 - saving)
        + w_j * j_gap
        + lambda_disagreement * disagreement
        + mu_byte_exact * byte_exact_violation
    )


def _salience_reconstruct_weighted(
    raw: str,
    keep_ratio: float,
    terms: frozenset[str],
    lane_boost: float,
) -> str:
    tokens = WORD_RE_LOCAL.findall(raw)
    if not tokens:
        return ""
    kr = max(0.05, min(0.98, keep_ratio))
    keep_n = max(1, int(round(len(tokens) * kr)))

    def score(i: int) -> float:
        tok = tokens[i]
        s = token_salience(tok)
        low = tok.lower()
        for lt in terms:
            if lt in low or low in lt:
                s += lane_boost
                break
        return (s, len(tok))

    ranked = sorted(range(len(tokens)), key=score, reverse=True)
    keep_idx = set(ranked[:keep_n])
    ordered = [tokens[i] for i in range(len(tokens)) if i in keep_idx]
    return " ".join(ordered)


def partition_lens_terms(
    all_terms: frozenset[str], science_terms: frozenset[str]
) -> tuple[frozenset[str], frozenset[str], frozenset[str], frozenset[str]]:
    """Logos · science · sasang · myeongni lane token partitions."""
    sci = frozenset(t for t in all_terms if t in science_terms)
    sasang = frozenset(
        t
        for t in all_terms
        if t in SASANG_HINTS or "사상" in t or "체질" in t
    )
    myeongni = frozenset(
        t
        for t in all_terms
        if t in MYEONGNI_HINTS or "명리" in t or "사주" in t
    )
    sasang = frozenset(t for t in sasang if t not in sci and t not in myeongni)
    myeongni = frozenset(t for t in myeongni if t not in sci and t not in sasang)
    logos = frozenset(
        t for t in all_terms if t not in sci and t not in sasang and t not in myeongni
    )
    return logos, sci, sasang, myeongni


def partition_trilane_terms(
    all_terms: frozenset[str], science_terms: frozenset[str]
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Backward-compatible 3-tuple; myeongni terms remain in logos bucket."""
    logos, sci, sas, mye = partition_lens_terms(all_terms, science_terms)
    return logos | mye, sci, sas


def lens_disagreement_proxy(
    raw: str,
    *,
    keep_ratio: float,
    logos_terms: frozenset[str],
    science_terms: frozenset[str],
    sasang_terms: frozenset[str],
    science_weight_scale: float,
    myeongni_terms: frozenset[str] | None = None,
    myeongni_weight: float = 18.0,
    disagreement_keep_ratio: float | None = None,
) -> float:
    """Spread of per-lane salience reconstructions (0..~1).

    Compares lane reconstructions to each other (not raw vs lane) so high
    keep_ratio sweeps do not collapse disagreement to zero.
    """
    kr_dis = (
        disagreement_keep_ratio
        if disagreement_keep_ratio is not None
        else min(keep_ratio, 0.55)
    )
    reconstructions = [
        _salience_reconstruct_weighted(raw, kr_dis, logos_terms, 40.0),
        _salience_reconstruct_weighted(
            raw, kr_dis, science_terms, 28.0 * science_weight_scale
        ),
        _salience_reconstruct_weighted(raw, kr_dis, sasang_terms, 22.0),
    ]
    if myeongni_terms:
        reconstructions.append(
            _salience_reconstruct_weighted(raw, kr_dis, myeongni_terms, myeongni_weight)
        )
    pair_sims: list[float] = []
    for i in range(len(reconstructions)):
        for j in range(i + 1, len(reconstructions)):
            pair_sims.append(jaccard_text(reconstructions[i], reconstructions[j]))
    if not pair_sims:
        return 0.0
    avg_sim = sum(pair_sims) / len(pair_sims)
    return round(max(0.0, 1.0 - avg_sim), 6)


def load_kernel_defaults(spec_path: Path) -> dict[str, Any]:
    doc = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    return doc.get("loss_function_v1", {}).get("defaults") or {}


def load_disagreement_probe_defaults(spec_path: Path) -> dict[str, Any]:
    sidecar_path = spec_path.resolve().parent / "SCIENCE_PRIOR_SIDECAR_SPEC_V1.json"
    if sidecar_path.is_file():
        sidecar_doc = json.loads(sidecar_path.read_text(encoding="utf-8-sig"))
        return sidecar_doc.get("disagreement_probe") or {}
    doc = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    return doc.get("disagreement_probe") or {}


def salience_boost_weights(spec_doc: dict[str, Any]) -> tuple[float, float, float, float]:
    sb = spec_doc.get("salience_boost") or {}
    return (
        float(sb.get("logos_weight", 40.0)),
        float(sb.get("science_weight", 28.0)),
        float(sb.get("sasang_weight", 22.0)),
        float(sb.get("myeongni_weight", 18.0)),
    )
