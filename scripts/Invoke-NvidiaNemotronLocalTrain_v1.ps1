# Nemotron: default NVIDIA API (NIM). WSL QLoRA only with -WslTrain (16GB often fails).
param(
    [switch] $NimApi,
    [switch] $WslTrain,
    [switch] $DryRunLocal,
    [switch] $Smoke,
    [switch] $Full,
    [string] $Distro = 'Ubuntu-24.04',
    [int] $Limit = 8
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($NimApi -or (-not $WslTrain)) {
    Write-Host '[primary] NVIDIA API / NIM (replaces local 30B QLoRA for inference)'
    & py scripts/run_nvidia_api_primary_lane_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if (-not $WslTrain) { exit 0 }
}

function Get-MkmHfToken {
    if ($env:HF_TOKEN) { return $env:HF_TOKEN.Trim() }
    if ($env:HUGGING_FACE_HUB_TOKEN) { return $env:HUGGING_FACE_HUB_TOKEN.Trim() }
    $envFile = Join-Path $root '.env'
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^\s*HF_TOKEN=(.+)$') { return $Matches[1].Trim().Trim('"') }
            if ($_ -match '^\s*HUGGING_FACE_HUB_TOKEN=(.+)$') { return $Matches[1].Trim().Trim('"') }
        }
    }
    return $null
}

$trainArgs = @()
if ($DryRunLocal) { $trainArgs += @('--dry-run', '--limit', "$Limit", '--out-report-json', 'reports/nvidia_nemotron_wsl_dryrun_latest.json') }
elseif ($Smoke) { $trainArgs += @('--smoke', '--limit', '4', '--out-report-json', 'reports/nvidia_nemotron_wsl_smoke_latest.json') }
elseif ($Full) { $trainArgs += @('--full', '--out-report-json', 'reports/nvidia_nemotron_wsl_full_latest.json') }
else {
    Write-Host 'Specify -DryRunLocal, -Smoke, or -Full'
    exit 1
}

$argStr = ($trainArgs | ForEach-Object { if ($_ -match '\s') { "'$_'" } else { $_ } }) -join ' '
$hf = Get-MkmHfToken
$exportPrefix = ''
if ($hf) {
    $escaped = $hf -replace "'", "'\\''"
    $exportPrefix = "export HF_TOKEN='$escaped'; export HUGGING_FACE_HUB_TOKEN='$escaped'; "
    Write-Host '[info] HF_TOKEN will be exported into WSL for this run'
} elseif ($Smoke -or $Full) {
    Write-Warning 'HF_TOKEN not found — gated model download may fail in WSL'
}
$cmd = "${exportPrefix}cd /mnt/c/workspace && bash scripts/wsl/nemotron_local_setup_and_train_v1.sh $argStr"
Write-Host "[run] wsl -d $Distro bash -lc ..."
wsl -d $Distro -e bash -lc $cmd
exit $LASTEXITCODE
