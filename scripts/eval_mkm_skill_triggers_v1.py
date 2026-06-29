from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "mkm_skill_trigger_eval_v1"
AB_SCHEMA = "mkm_skill_trigger_ab_v1"
DEFAULT_FIXTURE = "docs/final/fixtures/mkm_skill_trigger_eval_v1.json"
DEFAULT_AB_FIXTURE = "docs/final/fixtures/mkm_skill_trigger_ab_v1.json"
DEFAULT_OUTPUT = "docs/final/artifacts/skill_trigger_eval_latest.json"
DEFAULT_AB_OUTPUT = "docs/final/artifacts/skill_trigger_eval_ab_latest.json"


@dataclass
class SkillProfile:
    name: str
    path: str
    description: str = ""
    phrases: list[str] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Heuristic eval for MKM skill trigger routing (description + Trigger section)."
    )
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--fixture", default=DEFAULT_FIXTURE)
    p.add_argument("--output-json", default=DEFAULT_OUTPUT)
    p.add_argument(
        "--ab-json",
        default=DEFAULT_AB_FIXTURE,
        help="A/B description variant fixture (runs after main eval by default)",
    )
    p.add_argument(
        "--skip-ab",
        action="store_true",
        help="Skip description A/B comparison",
    )
    p.add_argument(
        "--ab-output-json",
        default=DEFAULT_AB_OUTPUT,
        help="Artifact path for A/B comparison output",
    )
    p.add_argument(
        "--ab-only",
        action="store_true",
        help="Skip main eval; run A/B comparison only",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when recall/precision/cross-skill FP/conflict thresholds fail",
    )
    return p.parse_args()


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5 :]


def _parse_yaml_description(frontmatter: str) -> str:
    block = re.search(
        r"^description:\s*>-\s*\n((?:  .+\n?)+)",
        frontmatter,
        re.MULTILINE,
    )
    if block:
        return " ".join(line.strip() for line in block.group(1).splitlines() if line.strip())
    quoted = re.search(r'^description:\s*"(.+)"\s*$', frontmatter, re.MULTILINE)
    if quoted:
        return quoted.group(1).strip()
    inline = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not inline:
        return ""
    raw = inline.group(1).strip()
    if raw.startswith(">"):
        return ""
    return raw.strip('"')


def _extract_trigger_section(body: str) -> str:
    m = re.search(
        r"^##\s+Triggers?\s*$([\s\S]*?)(?=^##\s|\Z)",
        body,
        re.MULTILINE | re.IGNORECASE,
    )
    return m.group(1) if m else ""


def _normalize_token(token: str) -> str:
    return re.sub(r"\s+", " ", token.strip().lower())


def _tokenize(text: str) -> set[str]:
    parts = re.findall(r"[a-zA-Z0-9가-힣_/]+", text.lower())
    return {p for p in parts if len(p) >= 2}


def _collect_phrases(*chunks: str) -> list[str]:
    phrases: list[str] = []
    for chunk in chunks:
        for match in re.findall(r'"([^"]{3,120})"|「([^」]{2,80})」', chunk):
            phrase = match[0] or match[1]
            phrase = _normalize_token(phrase)
            if phrase:
                phrases.append(phrase)
    return phrases


def _split_trigger_fragments(item: str) -> list[str]:
    cleaned = re.sub(r"`([^`]+)`", r"\1", item)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    fragments: list[str] = []
    for paren in re.findall(r"\(([^)]+)\)", cleaned):
        for part in re.split(r"[,/·]", paren):
            part = _normalize_token(part)
            if part and len(part) >= 2:
                fragments.append(part)
    for part in re.split(r"[/·,]", cleaned):
        part = re.sub(r"\([^)]*\)", "", part)
        part = _normalize_token(part)
        if part and len(part) >= 2:
            fragments.append(part)
    return fragments


def _collect_terms(trigger_section: str, description: str) -> list[str]:
    terms: list[str] = []
    for line in trigger_section.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        item = re.sub(r"^-\s*", "", line)
        terms.extend(_split_trigger_fragments(item))
    for token in _tokenize(description):
        terms.append(token)
    return terms


RESUME_DOMINANCE_MARKERS = ("전에", "먼저", "이어서", "이어")

PRIORITY_BOOSTS: list[tuple[str, list[str], float]] = [
    (
        "mkm-cursor-session-ops",
        [
            "장기기억",
            "미션로그",
            "central 기준",
            "checkpoint",
            "핸드오프",
            "design 레인",
            "세션 재개",
            "세션 시작",
            "athena_checkpoint",
        ],
        12.0,
    ),
    (
        "mkm-dispatch-vip-pipeline",
        [
            "vip 리포트",
            "vip tactical",
            "funnel payload",
            "vip funnel",
            "vip 스냅샷",
        ],
        12.0,
    ),
    (
        "mkm-internal-standardized-briefing",
        [
            "시장 전망",
            "market outlook",
            "multi-lens",
            "멀티렌즈",
            "브리핑",
            "final action",
            "internal decision",
            "상태 체크",
            "의사결정",
        ],
        12.0,
    ),
    (
        "mkm-gut-brain-trackc-comms",
        [
            "gut-brain",
            "gut brain",
            "장-뇌",
            "vagus",
            "fermentation",
            "track c one-pager",
            "b2b deck",
            "showroom narrative",
            "over-claim",
            "outcome_class",
            "public_facing",
            "pedagogical isomorphism",
        ],
        12.0,
    ),
]


def load_skill_profile(
    root: Path,
    name: str,
    rel_path: str,
    description_override: str | None = None,
    description_only: bool = False,
) -> SkillProfile:
    path = root / rel_path
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    description = (
        description_override
        if description_override is not None
        else _parse_yaml_description(frontmatter)
    )
    trigger_section = "" if description_only else _extract_trigger_section(body)
    phrase_chunks = [description] if description_only else [description, trigger_section, body[:2000]]
    phrases = _collect_phrases(*phrase_chunks)
    terms = _collect_terms(trigger_section, description)
    skill_tokens = [t for t in name.replace("-", " ").split() if t]
    terms.extend(skill_tokens)
    return SkillProfile(
        name=name,
        path=rel_path.replace("\\", "/"),
        description=description,
        phrases=sorted(set(phrases)),
        terms=sorted(set(terms)),
    )


def load_profiles(
    root: Path,
    skill_specs: list[dict],
    description_overrides: dict[str, str | None] | None = None,
    description_only: bool = False,
) -> list[SkillProfile]:
    overrides = description_overrides or {}
    return [
        load_skill_profile(
            root,
            spec["name"],
            spec["path"],
            description_override=overrides.get(spec["name"]),
            description_only=description_only,
        )
        for spec in skill_specs
    ]


def score_prompt(
    profile: SkillProfile,
    prompt: str,
    *,
    use_priority_boosts: bool = True,
) -> tuple[float, list[str]]:
    prompt_norm = _normalize_token(prompt)
    prompt_tokens = _tokenize(prompt)
    score = 0.0
    reasons: list[str] = []

    for phrase in profile.phrases:
        if phrase and phrase in prompt_norm:
            score += 10.0
            reasons.append(f"phrase:{phrase}")

    for term in profile.terms:
        term_norm = _normalize_token(term)
        if not term_norm:
            continue
        if " " in term_norm and term_norm in prompt_norm:
            score += 5.0
            reasons.append(f"term_phrase:{term_norm}")
        elif term_norm in prompt_tokens:
            score += 2.0
            reasons.append(f"term:{term_norm}")

    name_bits = profile.name.split("-")
    for bit in name_bits:
        if bit in prompt_tokens:
            score += 1.0
            reasons.append(f"name:{bit}")

    if use_priority_boosts:
        for skill_name, phrases, boost in PRIORITY_BOOSTS:
            if skill_name != profile.name:
                continue
            for phrase in phrases:
                if phrase in prompt_norm:
                    score += boost
                    reasons.append(f"priority:{phrase}")
                    break

    return score, reasons


def _apply_resume_dominance(prompt: str, ranked: list[dict]) -> list[dict]:
    prompt_norm = _normalize_token(prompt)
    if not any(marker in prompt_norm for marker in RESUME_DOMINANCE_MARKERS):
        return ranked
    session = next((r for r in ranked if r["skill"] == "mkm-cursor-session-ops"), None)
    if not session or session["score"] <= 0:
        return ranked
    if not any(reason.startswith("priority:") for reason in session["reasons"]):
        return ranked
    session["score"] = round(session["score"] + 10.0, 2)
    session["reasons"].append("conflict:resume_dominance")
    ranked.sort(key=lambda row: (-row["score"], row["skill"]))
    return ranked


def rank_skills(
    profiles: list[SkillProfile],
    prompt: str,
    *,
    use_priority_boosts: bool = True,
    use_resume_dominance: bool = True,
) -> list[dict]:
    ranked: list[dict] = []
    for profile in profiles:
        score, reasons = score_prompt(
            profile, prompt, use_priority_boosts=use_priority_boosts
        )
        ranked.append(
            {
                "skill": profile.name,
                "score": round(score, 2),
                "reasons": reasons,
            }
        )
    ranked.sort(key=lambda row: (-row["score"], row["skill"]))
    if use_resume_dominance:
        return _apply_resume_dominance(prompt, ranked)
    return ranked


def evaluate_case(
    profiles: list[SkillProfile],
    case: dict,
    *,
    use_priority_boosts: bool = True,
    use_resume_dominance: bool = True,
) -> dict:
    prompt = case["prompt"]
    expected = case["expected_skill"]
    kind = case["kind"]
    ranked = rank_skills(
        profiles,
        prompt,
        use_priority_boosts=use_priority_boosts,
        use_resume_dominance=use_resume_dominance,
    )
    winner = ranked[0]["skill"] if ranked and ranked[0]["score"] > 0 else None

    if kind == "positive":
        ok = winner == expected
        failure = None if ok else "false_negative"
    elif kind == "negative":
        ok = winner != expected
        failure = None if ok else "false_positive"
    else:
        ok = winner == expected
        failure = None if ok else "wrong_priority"

    return {
        "id": case["id"],
        "kind": kind,
        "prompt": prompt,
        "expected_skill": expected,
        "winner": winner,
        "ok": ok,
        "failure": failure,
        "notes": case.get("notes"),
        "ranking": ranked,
    }


def aggregate(results: list[dict]) -> dict:
    positive = [r for r in results if r["kind"] == "positive"]
    negative = [r for r in results if r["kind"] == "negative"]
    conflict = [r for r in results if r["kind"] == "conflict"]

    tp = sum(1 for r in positive if r["ok"])
    fn = sum(1 for r in positive if not r["ok"])
    recall = tp / len(positive) if positive else 1.0

    tn = sum(1 for r in negative if r["ok"])
    fp = sum(1 for r in negative if not r["ok"])
    specificity = tn / len(negative) if negative else 1.0
    cross_fp_rate = fp / len(negative) if negative else 0.0

    precision_denom = tp + fp
    precision = tp / precision_denom if precision_denom else 1.0

    conflict_ok = sum(1 for r in conflict if r["ok"])
    conflict_rate = conflict_ok / len(conflict) if conflict else 1.0

    return {
        "cases_total": len(results),
        "positive": {"total": len(positive), "tp": tp, "fn": fn, "recall": round(recall, 4)},
        "negative": {
            "total": len(negative),
            "tn": tn,
            "fp": fp,
            "specificity": round(specificity, 4),
            "cross_skill_false_positive_rate": round(cross_fp_rate, 4),
        },
        "conflict": {
            "total": len(conflict),
            "ok": conflict_ok,
            "priority_accuracy": round(conflict_rate, 4),
        },
        "precision": round(precision, 4),
    }


def aggregate_skill_subset(results: list[dict], skill_name: str) -> dict:
    subset = [
        r
        for r in results
        if r["expected_skill"] == skill_name and r["kind"] in ("positive", "negative")
    ]
    metrics = aggregate(subset)
    return {
        "skill": skill_name,
        "cases_total": metrics["cases_total"],
        "skill_recall": metrics["positive"]["recall"],
        "skill_cross_fp_rate": metrics["negative"]["cross_skill_false_positive_rate"],
        "positive_total": metrics["positive"]["total"],
        "negative_total": metrics["negative"]["total"],
        "failures": [r for r in subset if not r["ok"]],
    }


def check_thresholds(metrics: dict, thresholds: dict) -> list[str]:
    violations: list[str] = []
    if metrics["positive"]["recall"] < thresholds["min_recall"]:
        violations.append(
            f"recall={metrics['positive']['recall']}<{thresholds['min_recall']}"
        )
    if metrics["precision"] < thresholds["min_precision"]:
        violations.append(
            f"precision={metrics['precision']}<{thresholds['min_precision']}"
        )
    if (
        metrics["negative"]["cross_skill_false_positive_rate"]
        > thresholds["max_cross_skill_false_positive_rate"]
    ):
        violations.append(
            "cross_skill_false_positive_rate="
            f"{metrics['negative']['cross_skill_false_positive_rate']}"
            f">{thresholds['max_cross_skill_false_positive_rate']}"
        )
    min_conflict = thresholds.get("min_conflict_accuracy", 1.0)
    if metrics["conflict"]["priority_accuracy"] < min_conflict:
        violations.append(
            "conflict_accuracy="
            f"{metrics['conflict']['priority_accuracy']}<{min_conflict}"
        )
    return violations


def run_main_eval(root: Path, fixture_path: Path) -> dict:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    profiles = load_profiles(root, fixture["skills"])
    results = [evaluate_case(profiles, case) for case in fixture["cases"]]
    metrics = aggregate(results)
    violations = check_thresholds(metrics, fixture["thresholds"])
    failures = [r for r in results if not r["ok"]]
    return {
        "fixture": fixture,
        "profiles": profiles,
        "results": results,
        "metrics": metrics,
        "violations": violations,
        "failures": failures,
        "ok": len(violations) == 0,
    }


def _pick_ab_winner(rows: list[dict]) -> str | None:
    if not rows:
        return None
    ranked = sorted(
        rows,
        key=lambda row: (
            -row["skill_recall"],
            row["skill_cross_fp_rate"],
            row["variant_id"],
        ),
    )
    return ranked[0]["variant_id"]


def run_ab_compare(root: Path, ab_path: Path, parent_fixture_path: Path | None = None) -> dict:
    ab_doc = json.loads(ab_path.read_text(encoding="utf-8"))
    parent_rel = parent_fixture_path or root / ab_doc["parent_fixture"]
    parent = json.loads(parent_rel.read_text(encoding="utf-8"))
    variant_rows: list[dict] = []

    for variant in ab_doc["variants"]:
        skill_name = variant["skill"]
        override = variant.get("description")
        profiles = load_profiles(
            root,
            parent["skills"],
            description_overrides={skill_name: override},
            description_only=True,
        )
        results = [
            evaluate_case(
                profiles,
                case,
                use_priority_boosts=False,
                use_resume_dominance=False,
            )
            for case in parent["cases"]
        ]
        skill_metrics = aggregate_skill_subset(results, skill_name)
        variant_rows.append(
            {
                "variant_id": variant["id"],
                "skill": skill_name,
                "description": override if override is not None else "SKILL.md baseline",
                "notes": variant.get("notes"),
                "skill_recall": skill_metrics["skill_recall"],
                "skill_cross_fp_rate": skill_metrics["skill_cross_fp_rate"],
                "positive_total": skill_metrics["positive_total"],
                "negative_total": skill_metrics["negative_total"],
                "failures": skill_metrics["failures"],
            }
        )

    winners_by_skill: dict[str, str] = {}
    for skill_name in sorted({row["skill"] for row in variant_rows}):
        skill_rows = [row for row in variant_rows if row["skill"] == skill_name]
        winner = _pick_ab_winner(skill_rows)
        if winner:
            winners_by_skill[skill_name] = winner

    control_beats_vague = True
    for skill_name in winners_by_skill:
        control_id = next(
            (v["id"] for v in ab_doc["variants"] if v["skill"] == skill_name and v["id"].endswith("-control")),
            None,
        )
        vague_variant_id = next(
            (v["id"] for v in ab_doc["variants"] if v["skill"] == skill_name and "vague" in v["id"]),
            None,
        )
        if control_id and vague_variant_id:
            control_row = next(r for r in variant_rows if r["variant_id"] == control_id)
            vague_row = next(r for r in variant_rows if r["variant_id"] == vague_variant_id)
            if vague_row["skill_recall"] >= control_row["skill_recall"]:
                control_beats_vague = False

    return {
        "ab_doc": ab_doc,
        "parent_fixture": parent_rel.as_posix(),
        "variants": variant_rows,
        "winners_by_skill": winners_by_skill,
        "control_beats_vague": control_beats_vague,
        "ok": control_beats_vague,
    }


def write_main_payload(root: Path, out_path: Path, eval_result: dict) -> None:
    fixture = eval_result["fixture"]
    metrics = eval_result["metrics"]
    payload = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if eval_result["ok"] else "FAIL",
        "ok": eval_result["ok"],
        "violations": eval_result["violations"],
        "fixture": (root / DEFAULT_FIXTURE).as_posix(),
        "thresholds": fixture["thresholds"],
        "metrics": metrics,
        "skills": [
            {
                "name": p.name,
                "path": p.path,
                "description_excerpt": p.description[:160],
                "phrase_count": len(p.phrases),
                "term_count": len(p.terms),
            }
            for p in eval_result["profiles"]
        ],
        "failures": eval_result["failures"],
        "results": eval_result["results"],
        "reproducible_command": "py scripts/eval_mkm_skill_triggers_v1.py --strict",
        "method": (
            "Heuristic proxy for Cursor skill routing: YAML description + Trigger section "
            "phrases/terms scored against user prompt. Not a live agent invocation."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_ab_payload(root: Path, out_path: Path, ab_result: dict) -> None:
    payload = {
        "schema": AB_SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if ab_result["ok"] else "FAIL",
        "ok": ab_result["ok"],
        "parent_fixture": ab_result["parent_fixture"],
        "winner_rule": ab_result["ab_doc"].get(
            "winner_rule", "highest_skill_recall_then_lowest_skill_cross_fp"
        ),
        "winners_by_skill": ab_result["winners_by_skill"],
        "control_beats_vague": ab_result["control_beats_vague"],
        "variants": ab_result["variants"],
        "reproducible_command": (
            "py scripts/eval_mkm_skill_triggers_v1.py --ab-json "
            f"{DEFAULT_AB_FIXTURE} --strict"
        ),
        "method": (
            "Description A/B: override one skill description per variant; score uses description "
            "only (not SKILL.md Trigger body) to mirror Cursor skill-discovery routing."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    fixture_path = root / args.fixture
    out_path = root / args.output_json
    ab_path = root / (args.ab_json or DEFAULT_AB_FIXTURE)
    ab_out_path = root / args.ab_output_json

    exit_code = 0

    if not args.ab_only:
        if not fixture_path.is_file():
            payload = {
                "schema": SCHEMA,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "ERROR",
                "reason": "fixture_missing",
                "fixture": fixture_path.as_posix(),
            }
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"mkm_skill_trigger_eval=ERROR fixture_missing output={out_path.as_posix()}")
            return 2

        eval_result = run_main_eval(root, fixture_path)
        write_main_payload(root, out_path, eval_result)
        metrics = eval_result["metrics"]
        failures = eval_result["failures"]
        print(
            "mkm_skill_trigger_eval="
            f"{'PASS' if eval_result['ok'] else 'FAIL'} "
            f"recall={metrics['positive']['recall']} "
            f"precision={metrics['precision']} "
            f"cross_fp={metrics['negative']['cross_skill_false_positive_rate']} "
            f"conflict={metrics['conflict']['priority_accuracy']} "
            f"failures={len(failures)} output={out_path.as_posix()}"
        )
        for row in failures:
            print(
                f"  fail {row['id']} kind={row['kind']} expected={row['expected_skill']} "
                f"winner={row['winner']}"
            )
        for v in eval_result["violations"]:
            print(f"  violation: {v}")
        if args.strict and not eval_result["ok"]:
            exit_code = 1

    if not args.skip_ab or args.ab_only:
        if not ab_path.is_file():
            print(f"mkm_skill_trigger_ab=ERROR ab_fixture_missing path={ab_path.as_posix()}")
            return 2 if exit_code == 0 else exit_code

        ab_result = run_ab_compare(root, ab_path, root / args.fixture if fixture_path.is_file() else None)
        write_ab_payload(root, ab_out_path, ab_result)
        print(
            "mkm_skill_trigger_ab="
            f"{'PASS' if ab_result['ok'] else 'FAIL'} "
            f"control_beats_vague={ab_result['control_beats_vague']} "
            f"winners={ab_result['winners_by_skill']} output={ab_out_path.as_posix()}"
        )
        for row in ab_result["variants"]:
            print(
                f"  variant {row['variant_id']} skill={row['skill']} "
                f"recall={row['skill_recall']} cross_fp={row['skill_cross_fp_rate']}"
            )
        if args.strict and not ab_result["ok"]:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
