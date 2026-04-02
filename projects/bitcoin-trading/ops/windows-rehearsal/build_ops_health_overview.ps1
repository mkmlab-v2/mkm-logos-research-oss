param(
    [string]$JemaaiPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_alert_health_latest.json",
    [string]$BlindReplayPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\blind_replay_multi_seed_health_latest.json",
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_health_overview_latest.json"
)

$ErrorActionPreference = "Stop"

function Read-JsonOrNull([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try { return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return $null }
}

$jemaai = Read-JsonOrNull -path $JemaaiPath
$blind = Read-JsonOrNull -path $BlindReplayPath
$jemaaiOk = ($null -ne $jemaai) -and [bool]$jemaai.overall_ok
$blindOk = ($null -ne $blind) -and [bool]$blind.overall_ok
$overall = $jemaaiOk -and $blindOk

$obj = [ordered]@{
    schema = "ops_health_overview_v1"
    checked_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    overall_ok = $overall
    jemaai_e2e_alert = [ordered]@{
        available = ($null -ne $jemaai)
        overall_ok = $jemaaiOk
        path = $JemaaiPath
    }
    blind_replay_multi_seed = [ordered]@{
        available = ($null -ne $blind)
        overall_ok = $blindOk
        path = $BlindReplayPath
        best_balanced_accuracy_mean = if ($null -ne $blind) { $blind.metrics.balanced_accuracy_mean } else { $null }
        best_hit_rate_mean = if ($null -ne $blind) { $blind.metrics.hit_rate_mean } else { $null }
    }
}

$json = $obj | ConvertTo-Json -Depth 6
$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
Write-Host $json
Write-Host ("Saved ops overview: {0}" -f $OutputPath)
if (-not $overall) { exit 1 }
exit 0
