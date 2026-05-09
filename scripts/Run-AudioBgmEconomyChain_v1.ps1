<#
.SYNOPSIS
  AI BGM 가성비 체인: 먼저 드라이런+게이트(비용 0), 선택 시에만 라이브 확장.

.DESCRIPTION
  1) Phase A — 항상 실행: `Run-AudioBgmGeminiExternalChain_v1.ps1 -DryRun -RunGate`
     Gemini 시드 확장 API 호출 없이 파이프라인·게이트 스모크.
  2) Phase B — `-Live` 일 때만: 동일 시드로 유료 확장(`Count`회, 기본 1; Flash 모델은 환경 `MKM_AUDIO_GEMINI_MODEL`).

  `-ExternalScript scripts/audio/tone_external_generator_v1.py` 는 Gemini 없이 오프라인 톤만 생성한다(Phase B `-Live`여도 유료 확장 없음).

  `scripts/audio/ffmpeg_bed_external_generator_v1.py` 는 ffmpeg lavfi 컬러 노이즈 베드(프롬프트 해시로 대역·색 결정론 조정); ffmpeg 미설치 시 톤 폴백.

  비용 절감 팁:
  - 반복·튜닝은 `-Live` 없이 Phase A만 사용.
  - 라이브는 `Count`를 1로 유지하고, 확정 후에만 늘리기.
  - `MKM_AUDIO_GEMINI_MODEL=gemini-2.5-flash`(기본) 유지.
  - 청구 경로는 `MKM_AUDIO_GEMINI_BILLING`(auto|developer|vertex)로 조직 정책에 맞춤.

.PARAMETER SeedJson
  시드 JSON (저장소 루트 기준 상대 또는 절대).

.PARAMETER OutputDir
  루트 출력 폴더. 하위에 `_dry_smoke/` 및 `-Live` 시 `_live/` 가 생성된다.

.PARAMETER Count
  배치당 생성 수 — Phase A·B 모두 동일 (기본 1). 드라이런에서 여러 트랙 게이트 스모크 시 `-Count 2` 등.

.PARAMETER PlaceholderSeconds
  WAV 무음 길이. 게이트 스모크용; 짧을수록 디스크·후처리 부담 감소.

.PARAMETER Live
  Phase A 성공 후 Phase B(실제 Gemini/Vertex 확장) 실행.

.PARAMETER GateStrict
  게이트 웨이버 없이 엄격 모드.

.PARAMETER ExternalScript
  내부 `Run-AudioBgmGeminiExternalChain_v1.ps1`에 전달. 예: `scripts/audio/tone_external_generator_v1.py`면 Gemini 없이 오프라인 톤만 생성(`-Live`여도 유료 확장 없음).

.EXAMPLE
  pwsh -File scripts\Run-AudioBgmEconomyChain_v1.ps1 -SeedJson data/audio/seeds/tension_sasang_01.example.json -ExternalScript scripts/audio/ffmpeg_bed_external_generator_v1.py
#>
param(
    [Parameter(Mandatory = $true)][string]$SeedJson,
    [string]$OutputDir = "workspace/audio_raw_economy",
    [int]$Count = 1,
    [double]$PlaceholderSeconds = 1.5,
    [switch]$Live,
    [switch]$GateStrict,
    [string]$ExternalScript = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Chain = Join-Path $RepoRoot "scripts\Run-AudioBgmGeminiExternalChain_v1.ps1"

$dryOut = Join-Path $RepoRoot (Join-Path $OutputDir "_dry_smoke")
$liveOut = Join-Path $RepoRoot (Join-Path $OutputDir "_live")

$gateArgs = @()
if ($GateStrict) { $gateArgs += '-GateStrict' }

$extArg = @()
if ($ExternalScript.Trim()) {
    $extArg += '-ExternalScript'
    $extArg += $ExternalScript.Trim()
}

Write-Host "[Economy] Phase A: dry-run + gate -> $dryOut"
& pwsh -NoProfile -ExecutionPolicy Bypass -File $Chain `
    -SeedJson $SeedJson `
    -OutputDir $dryOut `
    -Count $Count `
    -PlaceholderSeconds $PlaceholderSeconds `
    -DryRun `
    -RunGate `
    @extArg `
    @gateArgs

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $Live) {
    Write-Host "[Economy] Phase A OK. Skipping paid expand (omit -Live for zero-cost iteration)."
    exit 0
}

Write-Host "[Economy] Phase B: live expand + gate -> $liveOut"
& pwsh -NoProfile -ExecutionPolicy Bypass -File $Chain `
    -SeedJson $SeedJson `
    -OutputDir $liveOut `
    -Count $Count `
    -PlaceholderSeconds $PlaceholderSeconds `
    -RunGate `
    @extArg `
    @gateArgs

exit $LASTEXITCODE
