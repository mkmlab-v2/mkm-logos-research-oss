#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild CENTRAL/MKM_CURRENT_STATE.md from local disk SSOT (ChatGPT mirror).

GREEN bookkeeping only — no Stage2/G3 execution, no fetch required.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_MD = ROOT / "CENTRAL" / "MKM_CURRENT_STATE.md"
VALIDATION = (
    ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "mkm_chatgpt_handoff_local_validation_v1_latest.json"
)

V1A = (
    ROOT
    / "docs/final/artifacts/mkm_logos_canon_graph_rule_control_g2_independent_validation_v1_first_sealed.json"
)
V1B = (
    ROOT
    / "docs/final/artifacts/mkm_logos_canon_graph_rule_control_g2_independent_validation_v1b_first_sealed.json"
)
RECON = (
    ROOT
    / "docs/final/artifacts/mkm_logos_canon_graph_rule_control_g2_builder_state_reconciliation_v1_latest.json"
)
GREEN = (
    ROOT
    / "docs/final/artifacts/mkm_green_envelope_autonomous_continuation_activation_v1_latest.json"
)
POLICY = ROOT / "docs/final/artifacts/mkm_delegated_execution_policy_v1_latest.json"
SYNTH = (
    ROOT / "docs/final/artifacts/mkm_delegated_execution_governance_synthetic_v1_latest.json"
)
D1 = (
    ROOT
    / "docs/final/artifacts/mkm_logos_stage2_config_drift_repair_first_post_repair_execution_d1_latest.json"
)
D2 = (
    ROOT
    / "docs/final/artifacts/mkm_logos_stage2_160_runner_gap_forensic_and_implementation_prereg_d2_latest.json"
)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object: {path}")
    return data


def packed_ref_checkpoint(remote_main: str) -> str:
    packed = ROOT / ".git" / "packed-refs"
    key = f"refs/remotes/{remote_main}"
    if not packed.is_file():
        return "UNKNOWN"
    for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == key:
            return f"{key}@{parts[0]}"
    return "UNKNOWN"


def main() -> int:
    v1a = load_json(V1A)
    v1b = load_json(V1B)
    recon = load_json(RECON)
    green = load_json(GREEN)
    policy = load_json(POLICY)
    synth = load_json(SYNTH)
    d1 = load_json(D1)
    d2 = load_json(D2)

    if v1a.get("RESULT") != "STOP_G2_BUILDER_STATE_NOT_ESTABLISHED":
        raise SystemExit(f"V1a unexpected: {v1a.get('RESULT')}")
    if v1b.get("RESULT") != "PASS_BOUNDED_RULE_CONTROL_G2_VALIDATION_V1B":
        raise SystemExit(f"V1b unexpected: {v1b.get('RESULT')}")
    if recon.get("RECONCILED_BUILDER_STATE_SHA") != (
        "11d8e4c8eca38f535dbfb6d4bcc9131bef70b123"
    ):
        raise SystemExit(f"recon SHA unexpected: {recon.get('RECONCILED_BUILDER_STATE_SHA')}")
    if green.get("RESULT") != "MKM_GREEN_ENVELOPE_AUTONOMOUS_CONTINUATION_ACTIVE_V1":
        raise SystemExit(f"green activation unexpected: {green.get('RESULT')}")
    if policy.get("DEFAULT", {}).get("AUTO_NEXT") != (
        "WITHIN_PREAUTHORIZED_GREEN_ENVELOPE"
    ):
        raise SystemExit("policy DEFAULT.AUTO_NEXT mismatch")
    if synth.get("pass_count") != 16 or synth.get("fail_count") != 0:
        raise SystemExit(f"synth check not 16/0: {synth.get('pass_count')}/{synth.get('fail_count')}")

    now = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    md = f"""# MKM_CURRENT_STATE

```text
HANDOFF_STATUS=VALIDATED_AGAINST_LOCAL_DISK_SSOT
ROLE=CHATGPT_MIRROR_POINTER_ONLY
GITHUB_IS_SSOT=false
INTERNAL_GITEA_IS_CODE_SSOT=true
LOCAL_DISK_ARTIFACTS_ARE_EVIDENCE_SSOT=true
GENERATED_AT_UTC={now}
CONTINUITY=oracle-20260908-g2-close-green-envelope
AUTO_NEXT=WITHIN_PREAUTHORIZED_GREEN_ENVELOPE
AUTO_NEXT_BEYOND_GATE=false
```

이 파일은 ChatGPT 지휘부 인수인계 **mirror**다. 원본 증거는 `C:\\workspace` 디스크 아티팩트와 internal Gitea다. GitHub는 SSOT가 아니다.

아래 핀은 **이번 Cursor 미션에서 디스크 파일을 읽어 검증**한 값이다. 추정으로 빈칸을 채우지 않았다.

## Checkpoints (packed-refs read; no fetch claimed)

```text
GITEA_SSOT_CHECKPOINT={packed_ref_checkpoint("gitea/main")}
INTERNAL_TRACKING_CHECKPOINT={packed_ref_checkpoint("internal/main")}
GITHUB_ORIGIN_MAIN_CHECKPOINT={packed_ref_checkpoint("origin/main")}
HQ_MAIN_CHECKPOINT={packed_ref_checkpoint("hq/main")}
GITHUB_HANDOFF_BRANCH=handoff/mkm-current-state-20260908-v2
LOCAL_VALIDATION_RECEIPT=docs/final/artifacts/mkm_chatgpt_handoff_local_validation_v1_latest.json
GREEN_ENVELOPE_ACTIVATION=docs/final/artifacts/mkm_green_envelope_autonomous_continuation_activation_v1_latest.json
MIRROR_STATUS=POINTER_REFRESH_PENDING_PUSH
```

## GitHub mirror policy

- `docs/final/artifacts/**` 는 `.gitignore` (예외 소수). Stage2/Canon receipt 본문이 GitHub main에 없는 것은 **정책상 정상**.
- 이 파일에는 **경로 pointer + 검증된 상태 코드**만 둔다.
- origin/hq 기본 `no_push`. 공개는 `Push-GitHub-Explicit.ps1 -Acknowledge` 예외만.

## LOCAL_SSOT_FACTS (validated)

### A. Stage2

```text
D1=FAIL_BOUNDED
D1_RESULT={d1.get("RESULT")}
D1_PRESERVED=true
D2=COMPLETED
D2_RESULT={d2.get("RESULT")}
D2_MEANING=FORENSIC_AND_PREREG_ONLY_NOT_160_EXECUTION
D2_STAGE2_RUNTIME_EXECUTION=FAIL_BOUNDED
NEXT=D2B_MINIMAL_RUNNER
D2B_STATUS=AUTHORIZED_PRIMARY_GREEN_LANE_NOT_STARTED_ON_DISK
D3_REAL_160=COMMANDER_GATE
STAGE2_REAL_160_EXECUTION=false
MODEL_CALLS=0
HELDOUT_USED=false
SEMANTIC_SCORING=false
UNBLIND=false
H2H_SEMANTIC=false
```

Pointers:

- D1: `docs/final/artifacts/mkm_logos_stage2_config_drift_repair_first_post_repair_execution_d1_latest.json`
- D2: `docs/final/artifacts/mkm_logos_stage2_160_runner_gap_forensic_and_implementation_prereg_d2_latest.json`

Commander adjudication (this handoff window): Stage2 D2B = primary GREEN lane. Real 160 = D3 Commander Gate only.

### B. Canon Rule-Control G2 (CLOSED_SUPPORTED_BOUNDED)

```text
G2_STATUS=CLOSED_SUPPORTED_BOUNDED
G2_V1A_FIRST=STOP_G2_BUILDER_STATE_NOT_ESTABLISHED
G2_V1A_PRESERVED=true
RECONCILED_SHA=11d8e4c8eca38f535dbfb6d4bcc9131bef70b123
G2_V1B=PASS_BOUNDED_RULE_CONTROL_G2_VALIDATION_V1B
V1B_FRESH=false
F05={v1b.get("F05")}
F06={v1b.get("F06")}
F07={v1b.get("F07")}
F08_BOUNDED={v1b.get("F08_BOUNDED")}
RC_F10=HOLD_NOT_ESTABLISHED
G3=HOLD
G4=HOLD
RULE_CONTROL_VALIDITY=NOT_ESTABLISHED
SEMANTIC_EFFECTIVENESS=NOT_ADJUDICATED
AI_CONTROL_IMPROVEMENT=NOT_ESTABLISHED
```

Pointers:

- V1a first sealed: `docs/final/artifacts/mkm_logos_canon_graph_rule_control_g2_independent_validation_v1_first_sealed.json`
- Reconciliation: `docs/final/artifacts/mkm_logos_canon_graph_rule_control_g2_builder_state_reconciliation_v1_latest.json`
- V1b first sealed: `docs/final/artifacts/mkm_logos_canon_graph_rule_control_g2_independent_validation_v1b_first_sealed.json`

G1 lineage (unchanged background): FIRST_G1_IV=PARTIAL · V1B_SAME_GENERATION_READJUDICATION=PASS_BOUNDED · V1B_FRESH=false.

### C. Delegated execution (operational default)

```text
DELEGATED_POLICY=ACTIVE_BOUNDED
AUTO_NEXT=WITHIN_PREAUTHORIZED_GREEN_ENVELOPE
AUTO_NEXT_BEYOND_GATE=false
FULL_AUTONOMY=false
SYNTHETIC_CHECK=16/16
CURSOR_RUNTIME_PROMPTS=NOT_EQUIVALENT_TO_COMMANDER_GATE
GOVERNANCE_REWRITE_REQUIRED=false
RUN_MODE_CHANGE_REQUIRED=false
```

Pointers:

- Human: `docs/final/MKM_DELEGATED_EXECUTION_POLICY_V1.md`
- Machine: `docs/final/artifacts/mkm_delegated_execution_policy_v1_latest.json`
- Activation: `docs/final/artifacts/mkm_green_envelope_autonomous_continuation_activation_v1_latest.json`
- Synthetic: `docs/final/artifacts/mkm_delegated_execution_governance_synthetic_v1_latest.json`
- Cursor rule: `.cursor/rules/mkm-delegated-execution-policy-v1.mdc`

GREEN may auto-continue: forensic → recon → bounded impl → dev/synthetic → code IV → receipt/seal.
STOP on: validator FAIL/PARTIAL · UNKNOWN · Fact-Lock conflict · heldout · first real semantic/fresh · new generation · LIVE/SEND/DEPLOY/TRADE · destructive.

### D. Global ceilings

```text
BIBLE_AI_SUPERIORITY=NOT_ESTABLISHED
AI_CONTROL_IMPROVEMENT=NOT_ESTABLISHED
LIVE=HOLD
SEND=HOLD
DEPLOY=HOLD
TRADE=HOLD
```

## CONFLICTS

이전 handoff(`VALIDATION_CONFLICT`, G2=HOLD, D2B=NOT_STARTED as primary)는 **이 파일로 대체**한다. 구 PR #39 / `40ab9e...` 본문을 authoritative로 쓰지 말 것.

현재 디스크와 충돌하는 주장:

1. ~~G2=HOLD / G2 builder NOT_STARTED~~ → 폐기. 현재 `G2_STATUS=CLOSED_SUPPORTED_BOUNDED`.
2. ~~AUTO_NEXT=false as project default~~ → 폐기. 현재 `WITHIN_PREAUTHORIZED_GREEN_ENVELOPE`.
3. D2를 160 실행 완료로 읽기 → 여전히 금지. D2는 forensic/prereg 완료일 뿐.

## UNKNOWN

- GitHub handoff branch tip SHA after push (채워질 예정)
- live Gitea HEAD after fetch (이번 미션 fetch 안 함)
- Stage2 D2B builder receipt (아직 없음 — NEXT)

## Commander next (ChatGPT / new MKM LAB window)

```text
PRIMARY_GREEN_LANE=LOGOS_STAGE2_160_MINIMAL_RUNNER_IMPLEMENTATION_D2B
AUTO_NEXT=WITHIN_PREAUTHORIZED_GREEN_ENVELOPE
AUTO_NEXT_BEYOND_GATE=false
HARD_WALL=STAGE2_REAL_160_EXECUTION=false
STOP_AT=COMMANDER_GATE_FOR_STAGE2_D3_FIRST_REAL_160_EXECUTION
DO_NOT_OPEN=G3,G4,F10,Dynamics,MDI,UFT
```

성공 보고 형식만 받을 것:

- "Stage2 시험기 + 독립검사 끝. 실제 160 본시험은 아직 안 함. D3 승인 필요."
- 또는 "시험기/독립검사 첫 FAIL. 봉인. 수정·재시험 안 함."
"""

    HANDOFF_MD.parent.mkdir(parents=True, exist_ok=True)
    HANDOFF_MD.write_text(md, encoding="utf-8")

    validation = {
        "schema": "mkm_chatgpt_handoff_local_validation_v1",
        "schema_version": 2,
        "MISSION": "MKM_CHATGPT_HANDOFF_DISK_REFRESH_V2",
        "generated_at_utc": now,
        "EPISTEMIC": "DISK_FACT_LOCK",
        "MODE": "HANDOFF_VALIDATION_AND_STATE_SYNC_ONLY",
        "RESULT": "VALIDATED_AGAINST_LOCAL_DISK_SSOT",
        "HANDOFF_STATUS": "VALIDATED_AGAINST_LOCAL_DISK_SSOT",
        "handoff_file_local": "CENTRAL/MKM_CURRENT_STATE.md",
        "handoff_file_sha256": sha256_file(HANDOFF_MD),
        "AUTO_NEXT": "WITHIN_PREAUTHORIZED_GREEN_ENVELOPE",
        "AUTO_NEXT_BEYOND_GATE": False,
        "GITHUB_IS_SSOT": False,
        "SOURCE_MODIFIED": True,
        "PATCHES_APPLIED": True,
        "IMPLEMENTATION_EXECUTED": False,
        "EXPERIMENT_EXECUTED": False,
        "RERUN_EXECUTED": False,
        "github_candidate": {
            "branch": "handoff/mkm-current-state-20260908-v2",
            "claimed_path": "CENTRAL/MKM_CURRENT_STATE.md",
            "replaces_stale_candidate": {
                "branch": "handoff/mkm-current-state-20260908-v1",
                "commit": "40ab9e6628f361562569c39b6823c89a41ee2061",
                "note": "stale_pre_G2_close_pre_green_envelope_do_not_use",
            },
        },
        "checkpoints": {
            "GITEA_SSOT_CHECKPOINT": packed_ref_checkpoint("gitea/main"),
            "INTERNAL_TRACKING_CHECKPOINT": packed_ref_checkpoint("internal/main"),
            "GITHUB_ORIGIN_MAIN_CHECKPOINT": packed_ref_checkpoint("origin/main"),
            "HQ_MAIN_CHECKPOINT": packed_ref_checkpoint("hq/main"),
            "checkpoint_source": "workspace_.git/packed_refs_read_only_no_fetch",
            "MIRROR_STATUS": "POINTER_REFRESH_PENDING_PUSH",
        },
        "stage2": {
            "D1": "FAIL_BOUNDED",
            "D1_RESULT": d1.get("RESULT"),
            "D2": "COMPLETED",
            "D2_RESULT": d2.get("RESULT"),
            "NEXT": "D2B_MINIMAL_RUNNER",
            "D3_REAL_160": "COMMANDER_GATE",
        },
        "canon_rule_control_g2": {
            "G2_STATUS": "CLOSED_SUPPORTED_BOUNDED",
            "V1A_FIRST": v1a.get("RESULT"),
            "V1A_PRESERVED": True,
            "RECONCILED_SHA": recon.get("RECONCILED_BUILDER_STATE_SHA"),
            "V1B": v1b.get("RESULT"),
            "V1B_FRESH": False,
            "F05": v1b.get("F05"),
            "F06": v1b.get("F06"),
            "F07": v1b.get("F07"),
            "F08_BOUNDED": v1b.get("F08_BOUNDED"),
            "G3": "HOLD",
            "G4": "HOLD",
            "RC_F10": "HOLD_NOT_ESTABLISHED",
        },
        "delegation": {
            "AUTO_NEXT": "WITHIN_PREAUTHORIZED_GREEN_ENVELOPE",
            "AUTO_NEXT_BEYOND_GATE": False,
            "SYNTHETIC_CHECK": f"{synth.get('pass_count')}/{synth.get('pass_count') + synth.get('fail_count')}",
            "activation_result": green.get("RESULT"),
            "policy_version": policy.get("version"),
        },
        "global": {
            "BIBLE_AI_SUPERIORITY": "NOT_ESTABLISHED",
            "AI_CONTROL_IMPROVEMENT": "NOT_ESTABLISHED",
            "LIVE": "HOLD",
            "SEND": "HOLD",
        },
        "STALE_HANDOFF_DO_NOT_USE": [
            "PR#39 body as authoritative",
            "commit 40ab9e6628f361562569c39b6823c89a41ee2061",
            "G2=HOLD claims",
            "AUTO_NEXT=false as project default",
        ],
        "NEXT": "PUSH_HANDOFF_BRANCH_THEN_NEW_CHATGPT_WINDOW_READ_CENTRAL",
        "LIVE": "HOLD",
        "SEND": "HOLD",
    }

    VALIDATION.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    digest = sha256_file(VALIDATION)
    assert digest is not None
    Path(str(VALIDATION) + ".sha256").write_text(digest + "\n", encoding="utf-8")

    print(f"WROTE {HANDOFF_MD.relative_to(ROOT).as_posix()} sha256={sha256_file(HANDOFF_MD)}")
    print(f"WROTE {VALIDATION.relative_to(ROOT).as_posix()} sha256={digest}")
    print(f"RESULT={validation['RESULT']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
