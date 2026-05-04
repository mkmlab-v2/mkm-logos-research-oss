<#
.SYNOPSIS
  로컬 Fact-Lock 번들 — GitHub Actions `dual-regime-integrity.yml` 핵심 검증과 동일 순서(Windows).

.DESCRIPTION
  1. `py scripts/integrity_guard.py` (CI 첫 단계)
  2. `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`
     — dual-regime 스모크 + multilens marginal(V1) 후 워크스페이스 루트 Fact-Lock(Thin V2·시장 어댑터 등 명시 목록)
  3. `py -m pytest tests/test_sasang_interpretive_insight_bundle_v1.py` — 사상 통찰 참조 번들 v1.1 스키마·`synthesis_v1`(dual-regime 동일 단계)
  3b. `py -m pytest tests/test_bio_sasang_nstates_strict_comparison_rehydrate_v1.py` — Bio n-state strict JSON 재수화 계약(CONSTITUTION §3.5)
  3c. `py -m pytest tests/test_mkm_trinity_index_v1.py` — MKM Trinity 인덱스 JSON·스키마 계약(CONSTITUTION §1 렌즈 인덱스 bullet)
  4. `py -m pytest tests/test_build_daily_execution_insight_brief_v1.py` — 일일 실행 인사이트 브리프 머티리얼라이저(CONSTITUTION §3.3)
  5. `py -m pytest tests/test_emit_myeongni_thin_bridge_line_v1.py` — 명리 독립 렌즈 → Thin JSONL 브리지(§3.6)
  5b. `py -m pytest tests/test_validate_mkm_personal_briefing_guardrails_v1.py` — 개인 인사이트 브리핑 Fact-Lock 휴리스틱(운영 단계 라벨·시장↔부채 합선)
  6. (기본) 명리·멀티렌즈 **권장 스택** — CI `multilens-independent-lens-smoke`와 동일 9개 pytest(일일 브리프·Thin 브리지와 중복 제외). `-SkipMyeongniLensRecommendedStack` 로 생략.

  테스트 파일 목록 이중 관리를 피하기 위해 2단계는 기존 PS1에 위임합니다. 3·3b·3c·5·6단계는 본 스크립트에서 직접 실행합니다.

.PARAMETER SkipIntegrityGuard
  `integrity_guard.py` 생략(빠른 확인용). CI와 완전 동치가 아님.

.PARAMETER IncludeP1AB
  Fact-Lock 핵심 검증 후 `scripts/run_p1_ab_bundle.ps1`를 추가 실행한다.

.PARAMETER IncludeCodebookFactSafe
  압축 복원 브리지 이후 `scripts/run_codebook_factsafe_bundle.ps1 -IncludeRecoveredReadiness`를 실행한다(코드북·복구 레일 스모크).

.PARAMETER Include4dOhaengRegimeSnapshotGate
  B-track 스파이크: `scripts/run_4d_to_ohaeng_regime_snapshot_gate_chain_spike.ps1` 실행(스냅샷 갱신 + 게이트). 기본 번들과 격리; 아티팩트 없으면 실패한다.

.PARAMETER IncludeBtrackBalancedRegimeEval
  B-track 균형 레짐 평가 체인(`scripts/run_btrack_balanced_regime_eval_chain_v1.ps1`)을 후단에서 실행한다.

.PARAMETER IncludeTruthfulQaBenchmarkGate
  TruthfulQA A/B 벤치 산출물 존재 여부를 점검한다(빠른 파일 게이트).

.PARAMETER StrictTruthfulQaBenchmarkGate
  TruthfulQA A/B 벤치 산출물 미존재 시 경고 대신 실패(exit 1)로 처리한다.

.PARAMETER IncludeTruthfulQaBenchmarkEvalGate
  TruthfulQA MC/Generation 벤치 결과를 GO/NO_GO로 판정하는 게이트 스크립트를 실행한다.

.PARAMETER StrictTruthfulQaBenchmarkEvalGate
  TruthfulQA 판정 결과가 NO_GO면 실패(exit 1)로 처리한다.

.PARAMETER TruthfulQaEvalMcOnly
  Eval 게이트에 `--mc-only`를 넘겨 MC 비교만으로 판정한다(promotion-friendly). generation 산출물이 없어도 실행 가능.

.PARAMETER TruthfulQaBenchmarkGateMcOnly
  `-IncludeTruthfulQaBenchmarkGate` 사용 시 generation JSON 없어도 경고/실패 대상에서 제외(MC 파일만 필수).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipIntegrityGuard

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipIntegrityGuard -IncludeP1AB

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeCodebookFactSafe

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -Include4dOhaengRegimeSnapshotGate

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeBtrackBalancedRegimeEval

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeTruthfulQaBenchmarkGate

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeTruthfulQaBenchmarkEvalGate -StrictTruthfulQaBenchmarkEvalGate

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -IncludeTruthfulQaBenchmarkGate -TruthfulQaBenchmarkGateMcOnly -IncludeTruthfulQaBenchmarkEvalGate -TruthfulQaEvalMcOnly -StrictTruthfulQaBenchmarkEvalGate

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipNewsObservationContractSmoke

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_fact_lock_bundle.ps1 -SkipMyeongniLensRecommendedStack

.PARAMETER SkipMyeongniLensRecommendedStack
  명리 독립 렌즈 v0/v1·융합 브리지·봇 체인·융합 스텁 등 9종 멀티렌즈 pytest(권장 CI 패리티)를 생략한다.

.NOTES
  SSOT 순서: `.github/workflows/dual-regime-integrity.yml`
  pytest·`py` 규칙: `docs/final/P0_COMMERCIALIZATION_TRACKER.md`
#>
param(
    [switch]$SkipIntegrityGuard,
    [switch]$IncludeP1AB,
    [switch]$SkipCompressionRestoreBridge,
    [switch]$IncludeCodebookFactSafe,
    [switch]$Include4dOhaengRegimeSnapshotGate,
    [switch]$IncludeBtrackBalancedRegimeEval,
    [switch]$IncludeTruthfulQaBenchmarkGate,
    [switch]$StrictTruthfulQaBenchmarkGate,
    [switch]$IncludeTruthfulQaBenchmarkEvalGate,
    [switch]$StrictTruthfulQaBenchmarkEvalGate,
    [switch]$TruthfulQaEvalMcOnly,
    [switch]$TruthfulQaBenchmarkGateMcOnly,

    # B-track news_observation JSONL contract smoke runs by default after prophecy alignment; use -Skip to omit.
    [switch]$SkipNewsObservationContractSmoke,

    # Myeongni / multilens recommended CI parity (9 pytests, excluding daily brief + thin bridge already run above)
    [switch]$SkipMyeongniLensRecommendedStack
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$prophecyBundle = Join-Path $workspaceRoot 'projects\bitcoin-trading\ops\v2\tasks\run_prophecy_alignment_pytest.ps1'
$p1AbBundle = Join-Path $workspaceRoot 'scripts\run_p1_ab_bundle.ps1'
$insightScoreboardScript = Join-Path $workspaceRoot 'scripts\build_insight_effectiveness_scoreboard.py'
$trackbQuaternionGateScript = Join-Path $workspaceRoot 'scripts\report_trackb_quaternion_two_stage_gate.py'
$compressionRestoreBridgeScript = Join-Path $workspaceRoot 'scripts\run_agent_compression_restore_bridge.ps1'
$codebookFactSafeBundleScript = Join-Path $workspaceRoot 'scripts\run_codebook_factsafe_bundle.ps1'
$ohaengRegimeSnapshotGateChain = Join-Path $workspaceRoot 'scripts\run_4d_to_ohaeng_regime_snapshot_gate_chain_spike.ps1'
$btrackBalancedRegimeEvalChain = Join-Path $workspaceRoot 'scripts\run_btrack_balanced_regime_eval_chain_v1.ps1'
$trackCEvidenceScript = Join-Path $workspaceRoot 'scripts\build_track_c_evidence_pack_v1.py'
$trackCCopyGuardScript = Join-Path $workspaceRoot 'scripts\check_track_c_copy_guard_v1.py'
$trackCClaimValidatorScript = Join-Path $workspaceRoot 'scripts\validate_track_c_landing_claims_v1.py'
$sajuGoldenReplayScript = Join-Path $workspaceRoot 'scripts\run_saju_golden_replay.py'
$sasangInterpretiveBundleTest = Join-Path $workspaceRoot 'tests\test_sasang_interpretive_insight_bundle_v1.py'
$bioSasangNstatesRehydrateTest = Join-Path $workspaceRoot 'tests\test_bio_sasang_nstates_strict_comparison_rehydrate_v1.py'
$mkmTrinityIndexTest = Join-Path $workspaceRoot 'tests\test_mkm_trinity_index_v1.py'
$dailyExecutionInsightBriefTest = Join-Path $workspaceRoot 'tests\test_build_daily_execution_insight_brief_v1.py'
$myeongniThinBridgeTest = Join-Path $workspaceRoot 'tests\test_emit_myeongni_thin_bridge_line_v1.py'
$mkmBriefingGuardrailsTest = Join-Path $workspaceRoot 'tests\test_validate_mkm_personal_briefing_guardrails_v1.py'
$myeongniLensRecommendedPytests = @(
    (Join-Path $workspaceRoot 'tests\test_independent_lenses_v0.py'),
    (Join-Path $workspaceRoot 'tests\test_myeongni_independent_lens_v0.py'),
    (Join-Path $workspaceRoot 'tests\test_myeongni_lens_v1_contract.py'),
    (Join-Path $workspaceRoot 'tests\test_myeongni_fusion_bridge_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_myeongni_lens_chain_from_bot_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_independent_lens_shadow_gate_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_independent_lens_fusion_stub_v0.py'),
    (Join-Path $workspaceRoot 'tests\test_scm_boming_jiju_lexicon_v1.py'),
    (Join-Path $workspaceRoot 'tests\test_eval_btrack_insight_sidecar_lens_hit_agreement_v1.py')
)
$truthfulQaBenchmarkScript = Join-Path $workspaceRoot 'scripts\run_truthfulqa_ab_benchmark_v1.py'
$truthfulQaBenchmarkEvalGateScript = Join-Path $workspaceRoot 'scripts\check_truthfulqa_ab_gate_v1.py'
$truthfulQaMcBenchmarkArtifact = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_ab_benchmark_latest.json'
$truthfulQaGenerationBenchmarkArtifact = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_generation_ab_benchmark_latest.json'
$truthfulQaGateArtifact = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_ab_gate_latest.json'

if (-not (Test-Path -LiteralPath $prophecyBundle)) {
    throw "Bundle script not found: $prophecyBundle"
}

Set-Location -LiteralPath $workspaceRoot

if (-not $SkipIntegrityGuard) {
    Write-Host '== Fact-Lock: integrity_guard.py ==' -ForegroundColor Cyan
    & py (Join-Path $workspaceRoot 'scripts\integrity_guard.py')
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Host '== Fact-Lock: run_prophecy_alignment_pytest.ps1 ==' -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File $prophecyBundle
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipNewsObservationContractSmoke) {
    $newsSmoke = Join-Path $workspaceRoot 'scripts\Run-NewsObservationContractSmoke.ps1'
    if (-not (Test-Path -LiteralPath $newsSmoke)) {
        throw "News observation contract smoke script not found: $newsSmoke"
    }
    Write-Host '== Fact-Lock: Run-NewsObservationContractSmoke.ps1 (default) ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $newsSmoke
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($IncludeP1AB) {
    if (-not (Test-Path -LiteralPath $p1AbBundle)) {
        throw "P1 A/B bundle script not found: $p1AbBundle"
    }
    Write-Host '== Fact-Lock: run_p1_ab_bundle.ps1 ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $p1AbBundle
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path -LiteralPath $insightScoreboardScript)) {
    throw "Insight scoreboard script not found: $insightScoreboardScript"
}
Write-Host '== Fact-Lock: build_insight_effectiveness_scoreboard.py ==' -ForegroundColor Cyan
& py $insightScoreboardScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $trackbQuaternionGateScript)) {
    throw "Track B quaternion two-stage gate script not found: $trackbQuaternionGateScript"
}
Write-Host '== Fact-Lock: report_trackb_quaternion_two_stage_gate.py ==' -ForegroundColor Cyan
& py $trackbQuaternionGateScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipCompressionRestoreBridge) {
    if (-not (Test-Path -LiteralPath $compressionRestoreBridgeScript)) {
        throw "Compression/restore bridge script not found: $compressionRestoreBridgeScript"
    }
    Write-Host '== Fact-Lock: run_agent_compression_restore_bridge.ps1 ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $compressionRestoreBridgeScript
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path -LiteralPath $trackCEvidenceScript)) {
    throw "Track C evidence script not found: $trackCEvidenceScript"
}
Write-Host '== Fact-Lock: build_track_c_evidence_pack_v1.py ==' -ForegroundColor Cyan
& py $trackCEvidenceScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $trackCCopyGuardScript)) {
    throw "Track C copy guard script not found: $trackCCopyGuardScript"
}
Write-Host '== Fact-Lock: check_track_c_copy_guard_v1.py ==' -ForegroundColor Cyan
& py $trackCCopyGuardScript (Join-Path $workspaceRoot 'docs\final\TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md')
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $trackCClaimValidatorScript)) {
    throw "Track C landing validator script not found: $trackCClaimValidatorScript"
}
Write-Host '== Fact-Lock: validate_track_c_landing_claims_v1.py ==' -ForegroundColor Cyan
& py $trackCClaimValidatorScript --evidence-pack (Join-Path $workspaceRoot 'docs\final\artifacts\track_c_evidence_pack_latest.json')
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $sajuGoldenReplayScript)) {
    throw "Saju golden replay script not found: $sajuGoldenReplayScript"
}
Write-Host '== Fact-Lock: run_saju_golden_replay.py ==' -ForegroundColor Cyan
& py $sajuGoldenReplayScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $sasangInterpretiveBundleTest)) {
    throw "Sasang interpretive bundle pytest not found: $sasangInterpretiveBundleTest"
}
Write-Host '== Fact-Lock: test_sasang_interpretive_insight_bundle_v1.py ==' -ForegroundColor Cyan
& py -m pytest $sasangInterpretiveBundleTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $bioSasangNstatesRehydrateTest)) {
    throw "Bio Sasang n-states rehydrate pytest not found: $bioSasangNstatesRehydrateTest"
}
Write-Host '== Fact-Lock: test_bio_sasang_nstates_strict_comparison_rehydrate_v1.py ==' -ForegroundColor Cyan
& py -m pytest $bioSasangNstatesRehydrateTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $mkmTrinityIndexTest)) {
    throw "MKM Trinity index pytest not found: $mkmTrinityIndexTest"
}
Write-Host '== Fact-Lock: test_mkm_trinity_index_v1.py ==' -ForegroundColor Cyan
& py -m pytest $mkmTrinityIndexTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $dailyExecutionInsightBriefTest)) {
    throw "Daily execution insight brief pytest not found: $dailyExecutionInsightBriefTest"
}
Write-Host '== Fact-Lock: test_build_daily_execution_insight_brief_v1.py ==' -ForegroundColor Cyan
& py -m pytest $dailyExecutionInsightBriefTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $myeongniThinBridgeTest)) {
    throw "Myeongni thin bridge pytest not found: $myeongniThinBridgeTest"
}
Write-Host '== Fact-Lock: test_emit_myeongni_thin_bridge_line_v1.py ==' -ForegroundColor Cyan
& py -m pytest $myeongniThinBridgeTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $mkmBriefingGuardrailsTest)) {
    throw "MKM personal briefing guardrails pytest not found: $mkmBriefingGuardrailsTest"
}
Write-Host '== Fact-Lock: test_validate_mkm_personal_briefing_guardrails_v1.py ==' -ForegroundColor Cyan
& py -m pytest $mkmBriefingGuardrailsTest -q --tb=short
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipMyeongniLensRecommendedStack) {
    foreach ($t in $myeongniLensRecommendedPytests) {
        if (-not (Test-Path -LiteralPath $t)) {
            throw "Myeongni lens recommended pytest not found: $t"
        }
    }
    Write-Host '== Fact-Lock: Myeongni lens recommended stack (multilens CI parity, 9 tests) ==' -ForegroundColor Cyan
    & py -m pytest @myeongniLensRecommendedPytests -q --tb=short
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($IncludeCodebookFactSafe) {
    if (-not (Test-Path -LiteralPath $codebookFactSafeBundleScript)) {
        throw "Codebook Fact-Safe bundle script not found: $codebookFactSafeBundleScript"
    }
    Write-Host '== Fact-Lock: run_codebook_factsafe_bundle.ps1 ==' -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $codebookFactSafeBundleScript -IncludeRecoveredReadiness
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($Include4dOhaengRegimeSnapshotGate) {
    if (-not (Test-Path -LiteralPath $ohaengRegimeSnapshotGateChain)) {
        Write-Host "WARN: 4D->Ohaeng chain script not in repo; skip (not a gate failure): $ohaengRegimeSnapshotGateChain" -ForegroundColor Yellow
    } else {
        Write-Host '== Fact-Lock (optional): 4D->Ohaeng regime snapshot + gate ==' -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $ohaengRegimeSnapshotGateChain
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}

if ($IncludeBtrackBalancedRegimeEval) {
    if (-not (Test-Path -LiteralPath $btrackBalancedRegimeEvalChain)) {
        Write-Host "WARN: B-track balanced regime eval script not in repo; skip (not a gate failure): $btrackBalancedRegimeEvalChain" -ForegroundColor Yellow
    } else {
        Write-Host '== Fact-Lock (optional): B-track balanced regime eval chain ==' -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $btrackBalancedRegimeEvalChain
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}

if ($IncludeTruthfulQaBenchmarkGate) {
    if (-not (Test-Path -LiteralPath $truthfulQaBenchmarkScript)) {
        throw "TruthfulQA benchmark script not found: $truthfulQaBenchmarkScript"
    }

    Write-Host '== Fact-Lock (optional): TruthfulQA A/B benchmark artifact gate ==' -ForegroundColor Cyan
    $missingTruthfulQaArtifacts = @()
    if (-not (Test-Path -LiteralPath $truthfulQaMcBenchmarkArtifact)) {
        $missingTruthfulQaArtifacts += $truthfulQaMcBenchmarkArtifact
    }
    if (-not $TruthfulQaBenchmarkGateMcOnly) {
        if (-not (Test-Path -LiteralPath $truthfulQaGenerationBenchmarkArtifact)) {
            $missingTruthfulQaArtifacts += $truthfulQaGenerationBenchmarkArtifact
        }
    }

    if ($missingTruthfulQaArtifacts.Count -gt 0) {
        if ($StrictTruthfulQaBenchmarkGate) {
            Write-Host 'FAIL: TruthfulQA benchmark artifacts missing:' -ForegroundColor Red
            $missingTruthfulQaArtifacts | ForEach-Object { Write-Host "  $_" }
            exit 1
        }
        Write-Host 'WARN: TruthfulQA benchmark artifacts missing (run A/B benchmark script to generate):' -ForegroundColor Yellow
        $missingTruthfulQaArtifacts | ForEach-Object { Write-Host "  $_" }
    } else {
        if ($TruthfulQaBenchmarkGateMcOnly) {
            Write-Host 'OK: TruthfulQA MC benchmark artifact present (generation not required).' -ForegroundColor Green
        } else {
            Write-Host 'OK: TruthfulQA benchmark artifacts present (mc + generation).' -ForegroundColor Green
        }
    }
}

if ($IncludeTruthfulQaBenchmarkEvalGate) {
    if (-not (Test-Path -LiteralPath $truthfulQaBenchmarkEvalGateScript)) {
        throw "TruthfulQA eval gate script not found: $truthfulQaBenchmarkEvalGateScript"
    }
    Write-Host '== Fact-Lock (optional): TruthfulQA A/B eval gate ==' -ForegroundColor Cyan
    $truthfulQaEvalArgs = @(
        $truthfulQaBenchmarkEvalGateScript,
        '--mc-json', $truthfulQaMcBenchmarkArtifact,
        '--generation-json', $truthfulQaGenerationBenchmarkArtifact,
        '--out-json', $truthfulQaGateArtifact
    )
    if ($StrictTruthfulQaBenchmarkEvalGate) {
        $truthfulQaEvalArgs += '--strict'
    }
    if ($TruthfulQaEvalMcOnly) {
        $truthfulQaEvalArgs += '--mc-only'
    }
    & py @truthfulQaEvalArgs
    if ($LASTEXITCODE -ne 0) {
        if ($StrictTruthfulQaBenchmarkEvalGate) {
            exit $LASTEXITCODE
        }
        Write-Host "WARN: TruthfulQA eval gate returned NO_GO (strict disabled)." -ForegroundColor Yellow
    }
}

exit 0
