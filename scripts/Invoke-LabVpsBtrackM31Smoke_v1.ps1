#Requires -Version 5.1
<#
.SYNOPSIS
  Lab VPS minimal smoke: B-track hypothesis JSON once + M31 hormone trend JSON (no network/Gemini).

.DESCRIPTION
  If mkm-lab-workspace-v2 omits these scripts, stages scripts + schema + local bundle via scp, then runs
  python3 under /opt/mkm-lab-workspace-v2. Outputs:
    docs/final/artifacts/btrack_hypothesis_prophecy_latest.json
    docs/final/artifacts/lens_music_hormone_trend_latest.json

.PARAMETER VpsHost
  SSH Host (default: vps-mkmlife).

.PARAMETER RemoteLabRoot
  Lab clone path (default: /opt/mkm-lab-workspace-v2).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LabVpsBtrackM31Smoke_v1.ps1
#>
param(
    [string]$VpsHost = "vps-mkmlife",
    [string]$RemoteLabRoot = "/opt/mkm-lab-workspace-v2"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$bundleLocal = Join-Path $repo "docs\final\artifacts\btrack_llm_input_bundle_latest.json"
if (-not (Test-Path -LiteralPath $bundleLocal)) {
    throw "Missing local bundle (build or restore first): $bundleLocal"
}

$files = @(
    @{ Local = "scripts\generate_btrack_hypothesis_prophecy_v1.py"; Remote = "$RemoteLabRoot/scripts/" },
    @{ Local = "scripts\build_lens_music_hormone_trend_v1.py"; Remote = "$RemoteLabRoot/scripts/" },
    @{ Local = "docs\final\BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json"; Remote = "$RemoteLabRoot/docs/final/" }
)
foreach ($f in $files) {
    $src = Join-Path $repo $f.Local
    if (-not (Test-Path -LiteralPath $src)) { throw "Missing: $src" }
    & scp $src "${VpsHost}:$($f.Remote)"
}

$remoteBundle = "/tmp/btrack_smoke_bundle_lab.json"
& scp $bundleLocal "${VpsHost}:${remoteBundle}"

$bashPayload = (@"
set -euo pipefail
cd $RemoteLabRoot
mkdir -p docs/final/artifacts docs/final
python3 scripts/generate_btrack_hypothesis_prophecy_v1.py --bundle $remoteBundle --output docs/final/artifacts/btrack_hypothesis_prophecy_latest.json
python3 scripts/build_lens_music_hormone_trend_v1.py --out docs/final/artifacts/lens_music_hormone_trend_latest.json
ls -la docs/final/artifacts/btrack_hypothesis_prophecy_latest.json docs/final/artifacts/lens_music_hormone_trend_latest.json
"@) -replace "`r`n", "`n" -replace "`r", "`n"
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($bashPayload))

Write-Host ">>> SSH smoke: $VpsHost $RemoteLabRoot" -ForegroundColor Cyan
ssh $VpsHost "echo $b64 | base64 -d | bash"
if ($LASTEXITCODE -ne 0) { throw "Remote smoke exit $LASTEXITCODE" }
Write-Host "Done." -ForegroundColor Green
