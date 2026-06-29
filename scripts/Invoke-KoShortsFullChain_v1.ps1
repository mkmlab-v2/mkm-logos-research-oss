# Full ko shorts STT chain — fetch clinical_sim → spike → gate → burn-in → Cursor QA.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-KoShortsFullChain_v1.ps1
#   powershell -File scripts\Invoke-KoShortsFullChain_v1.ps1 -Quick
#   powershell -File scripts\Invoke-KoShortsFullChain_v1.ps1 -WithBrowser
#
param(
    [switch]$Quick,
    [switch]$SkipFetch,
    [switch]$SkipSpike,
    [switch]$SkipBurn,
    [switch]$IncludeTtsBench,
    [switch]$IncludeAlignmentSpike,
    [switch]$IncludeWhisperx,
    [switch]$IncludeDelegate,
    [switch]$IncludeDriftKpi,
    [string]$AlignmentBackend = 'auto',
    [string]$RoutingSidecar = '',
    [switch]$WithBrowser,
    [int]$Port = 8796,
    [string]$Profile = 'netflix_v16'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

function Write-Step([string]$Msg) { Write-Host "==> $Msg" -ForegroundColor Cyan }

$args = @('scripts/run_ko_shorts_full_chain_v1.py', '--profile', $Profile, '--port', "$Port")
if ($Quick) { $args += '--quick' }
if ($SkipFetch) { $args += '--skip-fetch' }
if ($SkipSpike) { $args += '--skip-spike' }
if ($SkipBurn) { $args += '--skip-burn' }
if ($IncludeTtsBench) { $args += '--include-tts-bench' }
if ($IncludeAlignmentSpike) { $args += '--include-alignment-spike' }
if ($IncludeAlignmentSpike) { $args += @('--alignment-backend', $AlignmentBackend) }
if ($RoutingSidecar) { $args += @('--routing-sidecar', $RoutingSidecar) }
if ($IncludeWhisperx) { $args += '--include-whisperx' }
if ($IncludeDelegate) { $args += '--include-delegate' }
if ($IncludeDriftKpi) { $args += '--include-drift-kpi' }

Write-Step 'run_ko_shorts_full_chain_v1.py'
& py @args
if ($LASTEXITCODE -ne 0) { throw "full chain exit $LASTEXITCODE" }

if ($WithBrowser) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'scripts/Invoke-KoShortsCursorBrowserSmoke_v1.ps1') -Port $Port
}

Write-Host 'OK: Invoke-KoShortsFullChain_v1' -ForegroundColor Green
Write-Host 'Report: reports/ko_shorts_full_chain_v1_latest.json' -ForegroundColor DarkGray
exit 0
