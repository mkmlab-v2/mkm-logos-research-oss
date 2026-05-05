"""Smoke tests for external Bible anchor governance scripts (tmp-only inputs/outputs)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script_rel: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / script_rel), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_build_external_anchor_promotion_handoff_packet_already_promoted_no_redundant_signoff(
    tmp_path: Path,
) -> None:
    """READY_FOR_HUMAN_REVIEW + Tier1 promoted should not recommend another Tier1 signoff."""
    promo = tmp_path / "promotion.json"
    promoted = tmp_path / "promoted.json"
    recovery = tmp_path / "recovery.json"
    sustain = tmp_path / "sustain.json"
    policy = tmp_path / "policy.json"
    weekly_ab = tmp_path / "weekly_ab.json"
    drill = tmp_path / "drill.json"
    out = tmp_path / "handoff.json"

    promo.write_text(
        json.dumps(
            {
                "status": "READY_FOR_HUMAN_REVIEW",
                "promotion_candidates": [{"label": "alpha"}],
            }
        ),
        encoding="utf-8",
    )
    promoted.write_text(
        json.dumps(
            {
                "status": "PROMOTED_TIER1_CANDIDATES",
                "promoted_count": 1,
                "promoted_labels": ["alpha"],
            }
        ),
        encoding="utf-8",
    )
    recovery.write_text(
        json.dumps({"status": "NOT_TRIGGERED", "recovery_candidates": []}),
        encoding="utf-8",
    )
    sustain.write_text(
        json.dumps({"status": "MATURE", "current": {"pass_streak": 3, "fail_streak": 0}}),
        encoding="utf-8",
    )
    policy.write_text(
        json.dumps({"effective_action": "adopt_limited", "policy_stage": "limited"}),
        encoding="utf-8",
    )
    weekly_ab.write_text(
        json.dumps(
            {
                "summary": {
                    "status": "PASS",
                    "pass_rate_delta_adopt_minus_monitor": 0.05,
                }
            }
        ),
        encoding="utf-8",
    )
    drill.write_text(
        json.dumps({"results": [{"s": 1}, {"s": 2}, {"s": 3}], "strict_pass_streak_threshold": 6}),
        encoding="utf-8",
    )

    proc = _run(
        "scripts/build_external_anchor_promotion_handoff_packet_v1.py",
        [
            "--promotion-json",
            str(promo),
            "--promoted-json",
            str(promoted),
            "--recovery-json",
            str(recovery),
            "--sustain-json",
            str(sustain),
            "--policy-json",
            str(policy),
            "--weekly-ab-json",
            str(weekly_ab),
            "--policy-stage-drill-json",
            str(drill),
            "--output-json",
            str(out),
        ],
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "external_bible_anchor_promotion_handoff_packet_v1"
    assert doc["summary"]["recommendation"] == "keep_operating_policy_no_new_signoff"
    assert doc["summary"]["promotion_lane"] == "already_promoted"
    assert doc["summary"]["already_promoted"] is True


def test_build_external_anchor_weekly_ab_report_tmp(tmp_path: Path) -> None:
    hist = tmp_path / "history.jsonl"
    lines = [
        json.dumps(
            {"effective_action": "monitor_only", "regression_status": "PASS"},
            ensure_ascii=False,
        ),
        json.dumps(
            {"effective_action": "adopt_limited", "regression_status": "PASS"},
            ensure_ascii=False,
        ),
    ]
    hist.write_text("\n".join(lines) + "\n", encoding="utf-8")
    preflight = tmp_path / "preflight.json"
    preflight.write_text(json.dumps({}), encoding="utf-8")
    layer5 = tmp_path / "layer5.json"
    layer5.write_text(json.dumps({"metrics": {"false_positive_rate": 0.02}}), encoding="utf-8")
    sustain = tmp_path / "sustain.json"
    sustain.write_text(json.dumps({"status": "MATURE"}), encoding="utf-8")
    out = tmp_path / "weekly_ab.json"

    proc = _run(
        "scripts/build_external_anchor_weekly_ab_report_v1.py",
        [
            "--history-jsonl",
            str(hist),
            "--preflight-json",
            str(preflight),
            "--layer5-json",
            str(layer5),
            "--sustain-json",
            str(sustain),
            "--window",
            "12",
            "--output-json",
            str(out),
        ],
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "external_bible_anchor_weekly_ab_report_v1"
    assert doc["summary"]["status"] == "PASS"


def test_sync_external_anchor_tier1_into_operating_policy_strict_threshold(tmp_path: Path) -> None:
    tiering = tmp_path / "tiering.json"
    tiering.write_text(json.dumps({"policy_action": "monitor_only"}), encoding="utf-8")
    promoted = tmp_path / "promoted.json"
    promoted.write_text(
        json.dumps(
            {
                "status": "PROMOTED_TIER1_CANDIDATES",
                "promoted_labels": ["z"],
            }
        ),
        encoding="utf-8",
    )
    regression = tmp_path / "regression.json"
    regression.write_text(json.dumps({"status": "PASS", "recommended_action": "keep_adopt_limited"}), encoding="utf-8")
    sustain = tmp_path / "sustain.json"
    sustain.write_text(
        json.dumps({"status": "MATURE", "current": {"pass_streak": 6, "fail_streak": 0}}),
        encoding="utf-8",
    )
    out = tmp_path / "policy.json"

    proc = _run(
        "scripts/sync_external_anchor_tier1_into_operating_policy_v1.py",
        [
            "--tiering-json",
            str(tiering),
            "--promoted-json",
            str(promoted),
            "--regression-json",
            str(regression),
            "--sustain-json",
            str(sustain),
            "--strict-pass-streak-threshold",
            "6",
            "--output-json",
            str(out),
        ],
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "external_bible_anchor_operating_policy_v1"
    assert doc["effective_action"] == "adopt_limited_strict"
    assert doc["sustain_override"] == "mature_upgrade_to_adopt_limited_strict"


def test_build_external_anchor_recovery_candidates_downgrade(tmp_path: Path) -> None:
    sustain = tmp_path / "sustain.json"
    sustain.write_text(json.dumps({"status": "DOWNGRADE_TRIGGER"}), encoding="utf-8")
    shadow = tmp_path / "shadow.json"
    shadow.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "label": "s1",
                        "strict_shadow_pass": True,
                        "delta_random_baseline": 0.5,
                        "precision_at_k": 0.9,
                        "coverage_overlap": 0.1,
                    },
                    {
                        "label": "s2",
                        "strict_shadow_pass": True,
                        "delta_random_baseline": 0.4,
                        "precision_at_k": 0.8,
                        "coverage_overlap": 0.2,
                    },
                    {
                        "label": "s3",
                        "strict_shadow_pass": True,
                        "delta_random_baseline": 0.3,
                        "precision_at_k": 0.7,
                        "coverage_overlap": 0.15,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    current = tmp_path / "current.json"
    current.write_text(
        json.dumps({"promotion_candidates": [{"label": "current_only"}]}),
        encoding="utf-8",
    )
    out = tmp_path / "recovery.json"

    proc = _run(
        "scripts/build_external_anchor_recovery_candidates_v1.py",
        [
            "--sustain-json",
            str(sustain),
            "--shadow-json",
            str(shadow),
            "--current-candidates-json",
            str(current),
            "--target-candidates",
            "3",
            "--output-json",
            str(out),
        ],
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "external_bible_anchor_recovery_candidates_v1"
    assert doc["status"] == "RECOVERY_READY_FOR_REVIEW"
    assert len(doc["recovery_candidates"]) == 3


def _row(promoted_status: str, effective: str, regression: str) -> str:
    return json.dumps(
        {
            "promoted_status": promoted_status,
            "promoted_count": 1,
            "effective_action": effective,
            "regression_status": regression,
        },
        ensure_ascii=False,
    )


def test_sustain_gate_pass_streak_counts_adopt_limited_strict(tmp_path: Path) -> None:
    """History rows with adopt_limited_strict must continue the mature pass streak."""
    hist = tmp_path / "h.jsonl"
    lines = [
        _row("PROMOTED_TIER1_CANDIDATES", "adopt_limited", "PASS"),
        _row("PROMOTED_TIER1_CANDIDATES", "adopt_limited_strict", "PASS"),
        _row("PROMOTED_TIER1_CANDIDATES", "adopt_limited_strict", "PASS"),
    ]
    hist.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "sustain.json"
    proc = _run(
        "scripts/check_external_anchor_promotion_sustain_gate_v1.py",
        [
            "--history-jsonl",
            str(hist),
            "--required-pass-streak",
            "3",
            "--output-json",
            str(out),
        ],
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["status"] == "MATURE"
    assert doc["current"]["pass_streak"] == 3


def test_append_history_overwrite_last_row(tmp_path: Path) -> None:
    hist = tmp_path / "h.jsonl"
    row1 = _row("PROMOTED_TIER1_CANDIDATES", "adopt_limited", "PASS")
    row2 = _row("PROMOTED_TIER1_CANDIDATES", "adopt_limited", "PASS")
    hist.write_text(row1 + "\n" + row2 + "\n", encoding="utf-8")
    promoted = tmp_path / "p.json"
    promoted.write_text(json.dumps({"status": "PROMOTED_TIER1_CANDIDATES", "promoted_count": 1}), encoding="utf-8")
    policy = tmp_path / "pol.json"
    policy.write_text(json.dumps({"effective_action": "adopt_limited_strict"}), encoding="utf-8")
    reg = tmp_path / "r.json"
    reg.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    proc = _run(
        "scripts/append_external_anchor_promotion_history_v1.py",
        [
            "--promoted-json",
            str(promoted),
            "--policy-json",
            str(policy),
            "--regression-json",
            str(reg),
            "--history-jsonl",
            str(hist),
            "--overwrite-last-row",
        ],
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    last = json.loads(hist.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last["effective_action"] == "adopt_limited_strict"
    first = json.loads(hist.read_text(encoding="utf-8").strip().splitlines()[0])
    assert first["effective_action"] == "adopt_limited"


def test_external_anchor_weekly_double_sync_chain_reaches_adopt_limited_strict(tmp_path: Path) -> None:
    """Mirrors run_layer1_layer5_weekly_maintenance: sustain -> sync -> append -> sustain -> sync -> overwrite.

    With 5 trailing pass rows, first sync stays adopt_limited; after append, streak 6 -> final strict.
    """
    row = _row("PROMOTED_TIER1_CANDIDATES", "adopt_limited", "PASS")
    hist = tmp_path / "promotion_history.jsonl"
    hist.write_text("\n".join([row] * 5) + "\n", encoding="utf-8")

    tiering = tmp_path / "tiering.json"
    tiering.write_text(json.dumps({"policy_action": "monitor_only"}), encoding="utf-8")
    promoted = tmp_path / "promoted.json"
    promoted.write_text(
        json.dumps({"status": "PROMOTED_TIER1_CANDIDATES", "promoted_count": 1, "promoted_labels": ["p1"]}),
        encoding="utf-8",
    )
    regression = tmp_path / "regression.json"
    regression.write_text(json.dumps({"status": "PASS", "recommended_action": "keep_adopt_limited"}), encoding="utf-8")

    sustain1 = tmp_path / "sustain_pre_append.json"
    p1 = _run(
        "scripts/check_external_anchor_promotion_sustain_gate_v1.py",
        [
            "--history-jsonl",
            str(hist),
            "--required-pass-streak",
            "3",
            "--output-json",
            str(sustain1),
        ],
    )
    assert p1.returncode == 0, p1.stdout + p1.stderr
    s1 = json.loads(sustain1.read_text(encoding="utf-8"))
    assert s1["current"]["pass_streak"] == 5

    policy1 = tmp_path / "policy_pre.json"
    p1b = _run(
        "scripts/sync_external_anchor_tier1_into_operating_policy_v1.py",
        [
            "--tiering-json",
            str(tiering),
            "--promoted-json",
            str(promoted),
            "--regression-json",
            str(regression),
            "--sustain-json",
            str(sustain1),
            "--strict-pass-streak-threshold",
            "6",
            "--output-json",
            str(policy1),
        ],
    )
    assert p1b.returncode == 0, p1b.stdout + p1b.stderr
    assert json.loads(policy1.read_text(encoding="utf-8"))["effective_action"] == "adopt_limited"

    app1 = _run(
        "scripts/append_external_anchor_promotion_history_v1.py",
        [
            "--promoted-json",
            str(promoted),
            "--policy-json",
            str(policy1),
            "--regression-json",
            str(regression),
            "--history-jsonl",
            str(hist),
        ],
    )
    assert app1.returncode == 0, app1.stdout + app1.stderr
    assert len([ln for ln in hist.read_text(encoding="utf-8").splitlines() if ln.strip()]) == 6

    sustain2 = tmp_path / "sustain_post_append.json"
    p2 = _run(
        "scripts/check_external_anchor_promotion_sustain_gate_v1.py",
        [
            "--history-jsonl",
            str(hist),
            "--required-pass-streak",
            "3",
            "--output-json",
            str(sustain2),
        ],
    )
    assert p2.returncode == 0, p2.stdout + p2.stderr
    s2 = json.loads(sustain2.read_text(encoding="utf-8"))
    assert s2["current"]["pass_streak"] == 6

    policy2 = tmp_path / "policy_final.json"
    p3 = _run(
        "scripts/sync_external_anchor_tier1_into_operating_policy_v1.py",
        [
            "--tiering-json",
            str(tiering),
            "--promoted-json",
            str(promoted),
            "--regression-json",
            str(regression),
            "--sustain-json",
            str(sustain2),
            "--strict-pass-streak-threshold",
            "6",
            "--output-json",
            str(policy2),
        ],
    )
    assert p3.returncode == 0, p3.stdout + p3.stderr
    pol_final = json.loads(policy2.read_text(encoding="utf-8"))
    assert pol_final["effective_action"] == "adopt_limited_strict"

    app2 = _run(
        "scripts/append_external_anchor_promotion_history_v1.py",
        [
            "--promoted-json",
            str(promoted),
            "--policy-json",
            str(policy2),
            "--regression-json",
            str(regression),
            "--history-jsonl",
            str(hist),
            "--overwrite-last-row",
        ],
    )
    assert app2.returncode == 0, app2.stdout + app2.stderr
    last = json.loads(hist.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last["effective_action"] == "adopt_limited_strict"

    integ = tmp_path / "integrated.json"
    integ.write_text(json.dumps({"decision": "GO_CONTROLLED"}), encoding="utf-8")
    pre = tmp_path / "preflight.json"
    pre.write_text(json.dumps({"decision": "GO_LIVE_CANDIDATE"}), encoding="utf-8")
    micro = tmp_path / "microcosm.json"
    micro.write_text(
        json.dumps({"diagnosis": {"stage": "early", "risk_band": "low"}}),
        encoding="utf-8",
    )
    prof = tmp_path / "profile.json"
    prof.write_text(json.dumps({"runtime": {"track_mode": "A"}}), encoding="utf-8")
    blend_out = tmp_path / "blend.json"
    pb = _run(
        "scripts/build_symbolic_reality_blend_runtime_v1.py",
        [
            "--mode",
            "auto",
            "--integrated-json",
            str(integ),
            "--preflight-json",
            str(pre),
            "--microcosm-json",
            str(micro),
            "--profile-json",
            str(prof),
            "--anchor-tiering-json",
            str(tiering),
            "--anchor-operating-policy-json",
            str(policy2),
            "--output-json",
            str(blend_out),
        ],
    )
    assert pb.returncode == 0, pb.stdout + pb.stderr
    blend_doc = json.loads(blend_out.read_text(encoding="utf-8"))
    assert blend_doc["policy"]["anchor_effective_action"] == "adopt_limited_strict"
    assert blend_doc["weights"]["symbolic"] == 0.25
