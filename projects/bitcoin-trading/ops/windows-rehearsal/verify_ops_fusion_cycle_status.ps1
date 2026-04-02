param(
    [string]$StatusPath = "C:\workspace\docs\final\artifacts\ops_fusion_cycle_status_latest.json"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $StatusPath)) {
    Write-Host "[verify-ops-fusion] FAIL: status file missing — run run_ops_fusion_cycle.ps1 once."
    exit 1
}

$doc = Get-Content -LiteralPath $StatusPath -Raw -Encoding UTF8 | ConvertFrom-Json

function Test-OverallOkFromArtifacts([string]$C2Path, [string]$TrinityPath) {
    if (-not (Test-Path -LiteralPath $TrinityPath)) { return @{ ok = $false; reason = "missing_trinity_json" } }
    if (-not (Test-Path -LiteralPath $C2Path)) { return @{ ok = $false; reason = "missing_c2_json" } }
    try {
        $c2 = Get-Content -LiteralPath $C2Path -Raw -Encoding UTF8 | ConvertFrom-Json
        $st = [string]$c2.status
        $breakAlert = $false
        if ($c2.PSObject.Properties.Name -contains "structural_break_alert") {
            $breakAlert = [bool]$c2.structural_break_alert
        }
        if ([string]::IsNullOrWhiteSpace($st)) { return @{ ok = $false; reason = "c2_status_empty" } }
        if ($breakAlert) { return @{ ok = $false; reason = "c2_structural_break_alert" } }
        if ($st -like "*RED*") { return @{ ok = $false; reason = "c2_status_red" } }
        return @{ ok = $true; reason = "c2_green_or_yellow_no_structural_break" }
    } catch {
        return @{ ok = $false; reason = "c2_parse_error" }
    }
}

$c2Default = "C:\workspace\docs\final\artifacts\c2_aegis_guardrail_status_latest.json"
$tDefault = "C:\workspace\docs\final\artifacts\trinity_scoring_distribution_btc_latest.json"
$c2Path = if ($doc.c2_guardrail_status_path) { [string]$doc.c2_guardrail_status_path } else { $c2Default }
$triPath = if ($doc.trinity_btc_distribution_path) { [string]$doc.trinity_btc_distribution_path } else { $tDefault }

if ($null -eq $doc.overall_ok) {
    Write-Host "[verify-ops-fusion] overall_ok absent; evaluating from C2/Trinity artifacts..."
    $ev = Test-OverallOkFromArtifacts -C2Path $c2Path -TrinityPath $triPath
    if ($ev.ok) {
        Write-Host "[verify-ops-fusion] PASS: derived overall_ok=true ($($ev.reason))"
        exit 0
    }
    Write-Host "[verify-ops-fusion] FAIL: derived overall_ok=false ($($ev.reason))"
    exit 1
}

if ($doc.overall_ok -eq $true) {
    Write-Host "[verify-ops-fusion] PASS: overall_ok=true"
    exit 0
}

$reason = ""
if ($doc.PSObject.Properties.Name -contains "overall_ok_reason") {
    $reason = [string]$doc.overall_ok_reason
}
Write-Host ("[verify-ops-fusion] FAIL: overall_ok=false {0}" -f $(if ($reason) { "($reason)" } else { "" }))
exit 1
