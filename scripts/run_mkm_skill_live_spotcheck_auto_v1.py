from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from eval_mkm_skill_triggers_v1 import load_profiles, rank_skills

SCHEMA = "mkm_skill_live_spotcheck_v1"
DEFAULT_CONFIG = "docs/final/fixtures/mkm_skill_live_spotcheck_v1.json"
DEFAULT_EVAL_FIXTURE = "docs/final/fixtures/mkm_skill_trigger_eval_v1.json"
DEFAULT_RESULTS = "docs/final/artifacts/skill_live_spotcheck_results_latest.json"
DEFAULT_SCORE = "docs/final/artifacts/skill_live_spotcheck_score_latest.json"
AUTO_SESSION_PREFIX = "auto-heuristic"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Auto-fill live spot-check results using heuristic skill routing "
            "(not real Cursor chat chips)."
        )
    )
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--eval-fixture", default=DEFAULT_EVAL_FIXTURE)
    p.add_argument("--output-json", default=DEFAULT_RESULTS)
    p.add_argument("--score-json", default=DEFAULT_SCORE)
    p.add_argument("--strict", action="store_true", help="Exit 1 if auto score below thresholds")
    p.add_argument("--skip-score", action="store_true")
    return p.parse_args()


def _case_map(eval_fixture: dict) -> dict[str, dict]:
    return {case["id"]: case for case in eval_fixture["cases"]}


def _heuristic_pass(kind: str, expected: str, winner: str | None) -> bool:
    if kind == "positive":
        return winner == expected
    if kind == "negative":
        return winner != expected
    return winner == expected


def auto_fill_rows(
    root: Path,
    config: dict,
    eval_fixture: dict,
) -> dict:
    profiles = load_profiles(root, eval_fixture["skills"])
    cases_by_id = _case_map(eval_fixture)
    rows: list[dict] = []

    for case_id in config["selected_case_ids"]:
        src = cases_by_id[case_id]
        ranked = rank_skills(profiles, src["prompt"])
        winner = ranked[0]["skill"] if ranked and ranked[0]["score"] > 0 else None
        ok = _heuristic_pass(src["kind"], src["expected_skill"], winner)

        rows.append(
            {
                "id": case_id,
                "kind": src["kind"],
                "prompt": src["prompt"],
                "expected_skill": src["expected_skill"],
                "notes": src.get("notes"),
                "chat_session": f"{AUTO_SESSION_PREFIX}:{case_id}",
                "observed_skill": winner or "none",
                "pass": ok,
                "observer_notes": "filled by run_mkm_skill_live_spotcheck_auto_v1.py",
                "run_provenance": "heuristic_auto",
                "heuristic_ranking": ranked,
            }
        )

    return {
        "schema": SCHEMA,
        "run_provenance": "heuristic_auto",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": config["protocol"],
        "thresholds": config["thresholds"],
        "source_fixture": (root / config["source_fixture"]).as_posix(),
        "config": (root / DEFAULT_CONFIG).as_posix(),
        "auto_method": (
            "Heuristic routing proxy — same engine as eval_mkm_skill_triggers_v1.py. "
            "Does NOT observe Cursor skill chips in real chats."
        ),
        "rows": rows,
        "reproducible_command": "py scripts/run_mkm_skill_live_spotcheck_auto_v1.py --strict",
    }


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    config_path = root / args.config
    eval_path = root / args.eval_fixture
    out_path = root / args.output_json

    if not config_path.is_file() or not eval_path.is_file():
        print("mkm_skill_live_spotcheck_auto=ERROR missing_config_or_eval_fixture")
        return 2

    config = json.loads(config_path.read_text(encoding="utf-8"))
    eval_fixture = json.loads(eval_path.read_text(encoding="utf-8"))
    doc = auto_fill_rows(root, config, eval_fixture)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    failures = [r for r in doc["rows"] if not r["pass"]]
    print(
        "mkm_skill_live_spotcheck_auto=OK "
        f"rows={len(doc['rows'])} failures={len(failures)} "
        f"provenance=heuristic_auto output={out_path.as_posix()}"
    )
    for row in failures:
        print(
            f"  fail {row['id']} expected={row['expected_skill']} "
            f"observed={row['observed_skill']}"
        )

    exit_code = 1 if failures else 0

    if not args.skip_score:
        score_proc = subprocess.run(
            [
                sys.executable,
                str(root / "scripts/score_mkm_skill_live_spotcheck_v1.py"),
                "--input-json",
                str(out_path.relative_to(root)).replace("\\", "/"),
                "--output-json",
                str(Path(args.score_json).as_posix()),
                *(["--strict"] if args.strict else []),
                "--allow-heuristic",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        print(score_proc.stdout.strip())
        if score_proc.stderr.strip():
            print(score_proc.stderr.strip())
        if args.strict and score_proc.returncode != 0:
            exit_code = 1
        elif failures and args.strict:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
