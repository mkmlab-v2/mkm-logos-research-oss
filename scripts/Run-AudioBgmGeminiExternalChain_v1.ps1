<#
.SYNOPSIS
  AI BGM 배치: Gemini/Vertex 시드 확장 + 플레이스홀더 WAV (외부 훅 권장 경로).

.DESCRIPTION
  `MKM_AUDIO_EXTERNAL_SCRIPT` 기본은 `scripts/audio/gemini_placeholder_external_generator_v1.py`(선택 `-ExternalScript`로 교체).
  `run_bgm_generation_batch.py --emit external` 실행.
  권장 청구: Vertex·GCP 크레딧은 `.env`에 GOOGLE_CLOUD_PROJECT + ADC; 없으면 GEMINI_API_KEY (`--billing auto`와 동일 선상).

.PARAMETER SeedJson
  시드 JSON 경로 (저장소 루트 기준 상대 또는 절대).

.PARAMETER OutputDir
  WAV·메타 출력 디렉터리 (기본 workspace/audio_raw).

.PARAMETER Count
  생성 요청 수 (기본 1).

.PARAMETER DryRun
  `MKM_AUDIO_EXPAND_DRY_RUN=1` — Gemini 확장만 드라이런(API 호출 없음).

.PARAMETER PlaceholderSeconds
  무음 WAV 길이(초).

.PARAMETER RunGate
  배치 후 `evaluate_audio_gate.py`를 각 WAV에 대해 실행한다.
  기본으로 `-GateStrict`가 없으면 `--gate-waive-lufs --gate-waive-bpm-lens`를 붙여 로컬(smoke)에서 통과시킨다.

.PARAMETER GateStrict
  `-RunGate`와 함께: 웨이버 없이 엄격 게이트(의존성·시드에 따라 exit 7 가능).

.PARAMETER ExternalScript
  `MKM_AUDIO_EXTERNAL_SCRIPT`로 쓸 저장소 상대 경로. 비우면 `scripts/audio/gemini_placeholder_external_generator_v1.py`.
  예: `scripts/audio/tone_external_generator_v1.py`(Gemini 없음·오프라인 톤). `scripts/audio/expand_tone_external_generator_v1.py`(확장 후 톤; `-DryRun` 시 확장도 드라이런). `scripts/audio/ffmpeg_bed_external_generator_v1.py`(lavfi 컬러 노이즈 베드). `-DryRun`일 때 Gemini 확장 드라이런은 위 두 종류·플레이스홀더 경로에만 적용된다.

.EXAMPLE
  pwsh -NoProfile -File scripts\Run-AudioBgmGeminiExternalChain_v1.ps1 -SeedJson data/audio/seeds/tension_sasang_01.example.json -DryRun -ExternalScript scripts/audio/ffmpeg_bed_external_generator_v1.py -RunGate

.EXAMPLE
  pwsh -NoProfile -File scripts\Run-AudioBgmGeminiExternalChain_v1.ps1 -SeedJson data/audio/seeds/tension_sasang_01.example.json -DryRun

.EXAMPLE
  pwsh -NoProfile -File scripts\Run-AudioBgmGeminiExternalChain_v1.ps1 -SeedJson data/audio/seeds/tension_sasang_01.example.json -DryRun -RunGate

.EXAMPLE
  pwsh -NoProfile -File scripts\Run-AudioBgmGeminiExternalChain_v1.ps1 -SeedJson data/audio/seeds/tension_sasang_01.example.json -ExternalScript scripts/audio/tone_external_generator_v1.py -RunGate
#>
param(
    [Parameter(Mandatory = $true)][string]$SeedJson,
    [string]$OutputDir = "workspace/audio_raw",
    [int]$Count = 1,
    [switch]$DryRun,
    [double]$PlaceholderSeconds = 2.0,
    [switch]$RunGate,
    [switch]$GateStrict,
    [string]$ExternalScript = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$SeedResolved = if ([System.IO.Path]::IsPathRooted($SeedJson)) { $SeedJson } else { Join-Path $RepoRoot $SeedJson }
if (-not (Test-Path -LiteralPath $SeedResolved)) {
    throw "SeedJson not found: $SeedResolved"
}

$defaultExternal = "scripts/audio/gemini_placeholder_external_generator_v1.py"
$resolvedExternal = if ($ExternalScript.Trim()) { $ExternalScript.Trim() } else { $defaultExternal }

$prevExternal = $env:MKM_AUDIO_EXTERNAL_SCRIPT
$prevDry = $env:MKM_AUDIO_EXPAND_DRY_RUN
try {
    $env:MKM_AUDIO_EXTERNAL_SCRIPT = $resolvedExternal
    if ($DryRun) {
        if ($resolvedExternal -match 'gemini_placeholder_external_generator|expand_tone_external_generator') {
            $env:MKM_AUDIO_EXPAND_DRY_RUN = "1"
        }
        else {
            Remove-Item Env:\MKM_AUDIO_EXPAND_DRY_RUN -ErrorAction SilentlyContinue
        }
    }
    else {
        Remove-Item Env:\MKM_AUDIO_EXPAND_DRY_RUN -ErrorAction SilentlyContinue
    }

    Push-Location $RepoRoot
    try {
        $extra = @()
        if ($RunGate) {
            $extra += '--run-gate'
            if (-not $GateStrict) {
                $extra += '--gate-waive-lufs'
                $extra += '--gate-waive-bpm-lens'
            }
        }
        & py (Join-Path $RepoRoot "scripts/audio/run_bgm_generation_batch.py") `
            --seed-json $SeedResolved `
            --count $Count `
            --output-dir $OutputDir `
            --emit external `
            --placeholder-seconds $PlaceholderSeconds `
            @extra
        exit $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($null -ne $prevExternal) { $env:MKM_AUDIO_EXTERNAL_SCRIPT = $prevExternal } else { Remove-Item Env:\MKM_AUDIO_EXTERNAL_SCRIPT -ErrorAction SilentlyContinue }
    if ($null -ne $prevDry) { $env:MKM_AUDIO_EXPAND_DRY_RUN = $prevDry } else { Remove-Item Env:\MKM_AUDIO_EXPAND_DRY_RUN -ErrorAction SilentlyContinue }
}
