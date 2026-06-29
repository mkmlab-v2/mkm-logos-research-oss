# Customer-masked JSONL -> bootstrap -> routed pilot ROI (1:1 proxy; SEND_GATE HOLD until counsel).
# Auto local (synthetic 20–30 rows, no manual drop): scripts/Invoke-CompressionCustomerPilotAutoLocal_v1.ps1

param(

    [Parameter(Mandatory = $true)]

    [string]$TenantId,

    [Parameter(Mandatory = $true)]

    [string]$CustomerJsonl,

    [string]$WorkspaceRoot = "C:\workspace",

    [int]$MaxCases = 30,

    [int]$MinCases = 20,

    [string]$Sku = "MKM-CHAT-D1",

    [ValidateSet("economy", "fidelity", "literal")]

    [string]$CompressionProfile = "economy",

    [switch]$RelaxPassGate,

    [switch]$StrictPassGate,

    [switch]$DryRun,

    # [HYPO] CS short-chat B-track: ablation winner (economy + shortcap 30/0.30 + body-only flatten).

    [switch]$BtrackCsShortContext,

    [switch]$StripRolePrefixes,

    [int]$ShortContextTokenThreshold = 30,

    [double]$ShortContextMaxSavingRate = 0.30

)



$ErrorActionPreference = "Stop"

$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path

Set-Location -LiteralPath $WorkspaceRoot



$CustomerPath = if ([System.IO.Path]::IsPathRooted($CustomerJsonl)) {

    (Resolve-Path -LiteralPath $CustomerJsonl).Path

} else {

    (Resolve-Path -LiteralPath (Join-Path $WorkspaceRoot $CustomerJsonl)).Path

}



if (-not (Test-Path -LiteralPath $CustomerPath)) {

    Write-Error "Customer JSONL not found: $CustomerPath"

}



$rowCount = (Get-Content -LiteralPath $CustomerPath | Where-Object { $_.Trim() -ne "" }).Count

if ($rowCount -lt $MinCases) {

    Write-Error "Customer JSONL has $rowCount rows; need at least $MinCases (max $MaxCases)."

}



$useStrip = $StripRolePrefixes -or $BtrackCsShortContext

$useShortCap = $BtrackCsShortContext

if ($StripRolePrefixes -and -not $BtrackCsShortContext) {

  Write-Host "WARN: -StripRolePrefixes without short-cap may not match ablation winner." -ForegroundColor Yellow

}



Write-Host "=== Customer pilot intake (masked JSONL) ===" -ForegroundColor Cyan

Write-Host "tenant: $TenantId | rows: $rowCount | SEND_GATE HOLD" -ForegroundColor Yellow

if ($BtrackCsShortContext) {

    Write-Host "btrack: CS short-context [HYPO] cap=$ShortContextMaxSavingRate @<=$ShortContextTokenThreshold tok + strip role prefixes" -ForegroundColor DarkYellow

}

Write-Host "kit: docs/final/artifacts/compression_pilot_target_intake_kit_v1_latest.json" -ForegroundColor DarkGray



if ($DryRun) {

    Write-Host "[DryRun] bootstrap + routed pilot chain" -ForegroundColor DarkGray

    exit 0

}



Write-Host "=== Step 1/2: bootstrap tenant from customer JSONL ===" -ForegroundColor Cyan

$bootstrapArgs = @(

    "scripts/bootstrap_compression_pilot_tenant_v1.py",

    "--tenant-id", $TenantId,

    "--source-jsonl", $CustomerPath,

    "--max-cases", "$MaxCases",

    "--customer-masked"

)

if ($useStrip) { $bootstrapArgs += "--strip-role-prefixes" }

if ($useShortCap) {

    $bootstrapArgs += @(

        "--short-context-token-threshold", "$ShortContextTokenThreshold",

        "--short-context-max-saving-rate", "$ShortContextMaxSavingRate"

    )

}

& py @bootstrapArgs

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



Write-Host "=== Step 2/2: routed pilot chain ===" -ForegroundColor Cyan

$pilotArgs = @(

    "scripts/Run-CompressionPilotIntakeBlueprint_v1.ps1",

    "-TenantId", $TenantId,

    "-MaxCases", "$MaxCases",

    "-Sku", $Sku,

    "-CompressionProfile", $CompressionProfile,

    "-SkipProofCompletion"

)

if ($RelaxPassGate -or -not $StrictPassGate) { $pilotArgs += "-RelaxPassGate" }

if ($BtrackCsShortContext) {

    $pilotArgs += @(

        "-BtrackCsShortContext",

        "-ShortContextTokenThreshold", "$ShortContextTokenThreshold",

        "-ShortContextMaxSavingRate", "$ShortContextMaxSavingRate"

    )

}

if ($useStrip) { $pilotArgs += "-StripRolePrefixes" }

& powershell -NoProfile -ExecutionPolicy Bypass -File @pilotArgs

exit $LASTEXITCODE

