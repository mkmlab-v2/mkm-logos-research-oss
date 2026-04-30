<#
.SYNOPSIS
  TruthfulQA A/B 재현 번들: (선택) HF 데이터셋 빌드 → MC 벤치 → (선택) generation 벤치 → 게이트.

.DESCRIPTION
  SSOT 경로는 `check_truthfulqa_ab_gate_v1.py` / `run_truthfulqa_ab_benchmark_v1.py` 기본값과 맞춘다.
  Ollama 등 OpenAI 호환 엔드포인트는 `--baseline-url` / `--candidate-url`로 전달한다.

.PARAMETER BuildDatasetsFromHf
  `datasets`/`fsspec`가 있는 환경에서 TruthfulQA MC·generation evalset JSONL을 HF로부터 생성한다(네트워크·시간).

.PARAMETER SkipDatasetBuild
  `-BuildDatasetsFromHf`를 생략할 때 기본. 이미 `docs/final/artifacts/*_evalset_latest.jsonl`이 있다고 가정.

.PARAMETER RunGeneration
  generation 벤치까지 실행한다(기본 끔). 끄면 게이트는 `--mc-only`로 실행된다.

.PARAMETER McOnlyGate
  `-RunGeneration`과 함께 쓸 때만 의미 있음: 벤치는 풀 스위트인데 게이트는 MC만 보려면 지정.

.PARAMETER StrictGate
  게이트 strict 실패 시 exit 1.

.PARAMETER MaxRows
  벤치에 `--max-rows`로 상한(기본 32, 빠른 재현).

.PARAMETER HfLimit
  HF 데이터셋 빌드 시 `--limit`(기본 200).

.PARAMETER BaselineUrl
  OpenAI 호환 chat base(예: http://127.0.0.1:11434/v1). 생략 시 TRUTHFULQA_BASELINE_URL → OLLAMA_HOST 정규화.

.PARAMETER CandidateUrl
  후보 URL. 생략 시 BaselineUrl과 동일(동일 호스트·다른 모델 비교).

.PARAMETER DryRun
  실행할 명령만 출력하고 종료.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-TruthfulQAReproBundleV1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-TruthfulQAReproBundleV1.ps1 -BuildDatasetsFromHf -MaxRows 64

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-TruthfulQAReproBundleV1.ps1 -RunGeneration -StrictGate
#>
param(
    [switch]$BuildDatasetsFromHf,
    [switch]$SkipDatasetBuild,
    [string]$BaselineUrl = '',
    [string]$CandidateUrl = '',
    [string]$BaselineModel = '',
    [string]$CandidateModel = '',
    [int]$MaxRows = 32,
    [int]$HfLimit = 200,
    [switch]$RunGeneration,
    [switch]$McOnlyGate,
    [switch]$StrictGate,
    [switch]$GenerateSampleDataset,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$benchScript = Join-Path $workspaceRoot 'scripts\run_truthfulqa_ab_benchmark_v1.py'
$gateScript = Join-Path $workspaceRoot 'scripts\check_truthfulqa_ab_gate_v1.py'
$mcEvalset = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_mc_evalset_latest.jsonl'
$genEvalset = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_generation_evalset_latest.jsonl'
$mcBenchOut = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_ab_benchmark_latest.json'
$genBenchOut = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_generation_ab_benchmark_latest.json'
$gateOut = Join-Path $workspaceRoot 'docs\final\artifacts\truthfulqa_ab_gate_latest.json'

if (-not (Test-Path -LiteralPath $benchScript)) { throw "Missing: $benchScript" }
if (-not (Test-Path -LiteralPath $gateScript)) { throw "Missing: $gateScript" }

if ($RunGeneration) {
    $useMcOnly = [bool]$McOnlyGate
} else {
    $useMcOnly = $true
}

function Get-OpenAiCompatBase {
    param([string]$Primary, [string]$EnvPrimary, [string]$EnvOllama)
    if ($Primary) { return $Primary.TrimEnd('/') }
    $e = [Environment]::GetEnvironmentVariable($EnvPrimary)
    if ($e) { return $e.TrimEnd('/') }
    $h = [Environment]::GetEnvironmentVariable($EnvOllama)
    if ($h) {
        $h = $h.TrimEnd('/')
        if ($h -match '/v1$') { return $h }
        return ($h + '/v1')
    }
    return ''
}

$bUrl = Get-OpenAiCompatBase -Primary $BaselineUrl -EnvPrimary 'TRUTHFULQA_BASELINE_URL' -EnvOllama 'OLLAMA_HOST'
if (-not $bUrl) {
    $bUrl = 'http://127.0.0.1:11434/v1'
}
if ($CandidateUrl) {
    $cUrl = $CandidateUrl.TrimEnd('/')
} else {
    $cEnv = [Environment]::GetEnvironmentVariable('TRUTHFULQA_CANDIDATE_URL')
    if ($cEnv) {
        $cUrl = $cEnv.TrimEnd('/')
    } else {
        $cUrl = $bUrl
    }
}

if (-not $BaselineModel) {
    $BaselineModel = [Environment]::GetEnvironmentVariable('TRUTHFULQA_BASELINE_MODEL')
    if (-not $BaselineModel) { $BaselineModel = 'llama3.1:8b' }
}
if (-not $CandidateModel) {
    $CandidateModel = [Environment]::GetEnvironmentVariable('TRUTHFULQA_CANDIDATE_MODEL')
    if (-not $CandidateModel) { $CandidateModel = 'gemma4:e2b' }
}

Set-Location -LiteralPath $workspaceRoot

if ($GenerateSampleDataset) {
    Write-Host '== Sample dataset: MC + generation JSONL ==' -ForegroundColor Cyan
    $c1 = @(
        $benchScript,
        '--task', 'mc',
        '--generate-sample-dataset',
        '--dataset-jsonl', $mcEvalset
    )
    $c2 = @(
        $benchScript,
        '--task', 'generation',
        '--generate-sample-dataset',
        '--dataset-jsonl', $genEvalset
    )
    if ($DryRun) {
        Write-Host ("py " + ($c1 -join ' '))
        Write-Host ("py " + ($c2 -join ' '))
        exit 0
    }
    & py @c1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py @c2
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host 'Sample datasets written. Run without -GenerateSampleDataset to benchmark.' -ForegroundColor Green
    exit 0
}

if ($BuildDatasetsFromHf -and -not $SkipDatasetBuild) {
    Write-Host '== Build evalsets from Hugging Face ==' -ForegroundColor Cyan
    $buildMc = @(
        $benchScript,
        '--task', 'mc',
        '--build-truthfulqa-mc-from-hf',
        '--dataset-jsonl', $mcEvalset,
        '--limit', "$HfLimit"
    )
    $buildGen = @(
        $benchScript,
        '--task', 'generation',
        '--build-truthfulqa-generation-from-hf',
        '--dataset-jsonl', $genEvalset,
        '--limit', "$HfLimit"
    )
    if ($DryRun) {
        Write-Host ("py " + ($buildMc -join ' '))
        Write-Host ("py " + ($buildGen -join ' '))
    } else {
        & py @buildMc
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & py @buildGen
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host '== TruthfulQA MC A/B benchmark ==' -ForegroundColor Cyan
$runMc = @(
    $benchScript,
    '--task', 'mc',
    '--dataset-jsonl', $mcEvalset,
    '--out-json', $mcBenchOut,
    '--baseline-url', $bUrl,
    '--candidate-url', $cUrl,
    '--baseline-model', $BaselineModel,
    '--candidate-model', $CandidateModel,
    '--max-rows', "$MaxRows"
)
if ($DryRun) {
    Write-Host ("py " + ($runMc -join ' '))
} else {
    & py @runMc
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($RunGeneration) {
    Write-Host '== TruthfulQA generation A/B benchmark ==' -ForegroundColor Cyan
    $runGen = @(
        $benchScript,
        '--task', 'generation',
        '--dataset-jsonl', $genEvalset,
        '--out-json', $genBenchOut,
        '--baseline-url', $bUrl,
        '--candidate-url', $cUrl,
        '--baseline-model', $BaselineModel,
        '--candidate-model', $CandidateModel,
        '--max-rows', "$MaxRows",
        '--max-tokens', '128'
    )
    if ($DryRun) {
        Write-Host ("py " + ($runGen -join ' '))
    } else {
        & py @runGen
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host '== TruthfulQA A/B gate ==' -ForegroundColor Cyan
$gateArgs = @(
    $gateScript,
    '--mc-json', $mcBenchOut,
    '--generation-json', $genBenchOut,
    '--out-json', $gateOut
)
if ($useMcOnly) {
    $gateArgs += '--mc-only'
}
if ($StrictGate) {
    $gateArgs += '--strict'
}
if ($DryRun) {
    Write-Host ("py " + ($gateArgs -join ' '))
    exit 0
}
& py @gateArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: repro bundle complete. Gate: $gateOut" -ForegroundColor Green
exit 0
