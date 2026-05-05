from scripts.build_sasang_4agent_promotion_gate_v1 import _decide_gate


def test_decide_gate_promoted_with_human_approval() -> None:
    decision = _decide_gate(
        all_core_pass=True,
        protective_subset_pass=True,
        human_approved=True,
    )
    assert decision == (
        "A_TRACK_PROMOTED_WITH_HUMAN_APPROVAL",
        False,
        True,
        "track_a_controlled_bridge",
    )


def test_decide_gate_veto_only_candidate_without_human_approval() -> None:
    decision = _decide_gate(
        all_core_pass=False,
        protective_subset_pass=True,
        human_approved=False,
    )
    assert decision == (
        "GATING_VETO_ONLY_CANDIDATE",
        True,
        False,
        "veto_only_non_directional",
    )


def test_decide_gate_veto_only_active_with_human_approval() -> None:
    decision = _decide_gate(
        all_core_pass=False,
        protective_subset_pass=True,
        human_approved=True,
    )
    assert decision == (
        "GATING_VETO_ONLY_ACTIVE_WITH_HUMAN_APPROVAL",
        False,
        False,
        "veto_only_non_directional",
    )


def test_decide_gate_hold_when_checks_fail() -> None:
    decision = _decide_gate(
        all_core_pass=False,
        protective_subset_pass=False,
        human_approved=False,
    )
    assert decision == (
        "HOLD",
        True,
        False,
        "hold_no_promotion",
    )
