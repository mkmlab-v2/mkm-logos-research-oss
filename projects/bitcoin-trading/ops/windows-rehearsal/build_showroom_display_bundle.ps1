# Builds production showroom bundles: public (SPEC-compliant public-event.v1) + private command snapshot.
# Public JSON never contains API keys; wallet fields only appear in private bundle.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\build_showroom_display_bundle.ps1
#
# Equity % for public (SPEC: % only — never emit balance strings on public JSON):
#   Priority: Env SHOWROOM_EQUITY_BASELINE_USDT > manual file showroom_equity_baseline_usdt.local.json
#   > auto file showroom_equity_baseline_auto.json (created on first run from balance_total; re-seed by deleting file)
# Direction on public strip (SPEC: direction_abstract only — no size/price):
#   - Env: SHOWROOM_DIRECTION_SOURCE=c2 | account | auto
#     account = LONG/SHORT from public_trading_metrics_latest.json -> long/short (no quantity).
#     auto (default when env unset) = account if position_side exists in metrics file, else c2.

param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        return Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Get-C2SignalLamp {
    param([string]$Status)
    $s = [string]$Status
    if ($s -like "*GREEN*") { return "GREEN" }
    if ($s -like "*YELLOW*") { return "YELLOW" }
    if ($s -like "*RED*") { return "RED" }
    return "UNKNOWN"
}

function Get-PublicDirectionAbstractFromC2 {
    param([string]$C2Status)
    $s = [string]$C2Status
    if ($s -like "*GREEN*") { return "flat" }
    if ($s -like "*YELLOW*") { return "short" }
    if ($s -like "*RED*") { return "short" }
    return "flat"
}

function Get-PublicDirectionAbstractFromAccount {
    param($Priv)
    if (-not $Priv -or -not $Priv.position_side) { return "flat" }
    $ps = [string]$Priv.position_side
    if ($ps -match "(?i)^LONG") { return "long" }
    if ($ps -match "(?i)^SHORT") { return "short" }
    return "flat"
}

function Get-RiskLevel {
    param([string]$C2Status)
    $s = [string]$C2Status
    if ($s -like "*RED*") { return "CRITICAL" }
    if ($s -like "*YELLOW*") { return "WARNING" }
    return "INFO"
}

function Get-PublicSignalDirection {
    param([string]$C2Status)
    $s = [string]$C2Status
    if ($s -like "*RED*") { return "CAUTION" }
    return "HOLD"
}

function Get-SystemStatus {
    param([bool]$RuntimeOk, [bool]$FusionOk)
    if ($RuntimeOk -and $FusionOk) { return "online" }
    if (-not $RuntimeOk) { return "degraded" }
    return "degraded"
}

$root = $WorkspaceRoot
$c2Path = Join-Path $root "docs\final\artifacts\c2_aegis_guardrail_status_latest.json"
$fusionPath = Join-Path $root "docs\final\artifacts\ops_fusion_cycle_status_latest.json"
$runtimePath = Join-Path $root "projects\bitcoin-trading\memory\v2\ops\runtime_health_latest.json"
$privateMetricsPath = Join-Path $root "projects\bitcoin-trading\memory\v2\public\public_trading_metrics_latest.json"
$baselineCandidate = Join-Path $root "projects\bitcoin-trading\memory\v2\ops\showroom_equity_baseline_usdt.local.json"
$autoBaselinePath = Join-Path $root "projects\bitcoin-trading\memory\v2\ops\showroom_equity_baseline_auto.json"

$c2 = Read-JsonFile -Path $c2Path
$fusion = Read-JsonFile -Path $fusionPath
$runtime = Read-JsonFile -Path $runtimePath
$priv = Read-JsonFile -Path $privateMetricsPath

$generatedUtc = ([DateTimeOffset]::UtcNow).ToString("o")
$c2Status = if ($c2 -and $c2.status) { [string]$c2.status } else { "UNKNOWN" }
$score = $null
if ($c2 -and $c2.current -and $c2.current.unified_score_balanced -ne $null) {
    $score = [double]$c2.current.unified_score_balanced
} elseif ($c2 -and $c2.baseline -and $c2.baseline.unified_score_balanced -ne $null) {
    $score = [double]$c2.baseline.unified_score_balanced
}

$fusionOk = $false
if ($fusion -and $fusion.overall_ok -ne $null) {
    $fusionOk = [bool]$fusion.overall_ok
}

$runtimeOk = $true
$runtimeTs = $null
if ($runtime) {
    if ($runtime.overall_ok -ne $null) { $runtimeOk = [bool]$runtime.overall_ok }
    if ($runtime.timestamp) { $runtimeTs = [string]$runtime.timestamp }
}

$c2AsOf = $null
if ($c2 -and $c2.generated_at_utc) { $c2AsOf = [string]$c2.generated_at_utc }

$asOf = $c2AsOf
if ([string]::IsNullOrWhiteSpace($asOf)) { $asOf = $generatedUtc }

$delaySec = 180
$baselineUsdt = $null
$rawBaselineEnv = [Environment]::GetEnvironmentVariable("SHOWROOM_EQUITY_BASELINE_USDT", "Process")
if (-not [string]::IsNullOrWhiteSpace($rawBaselineEnv)) {
    try {
        $ev = [double]$rawBaselineEnv
        if ($ev -gt 0) { $baselineUsdt = $ev }
    } catch {}
}
if ($null -eq $baselineUsdt -and (Test-Path -LiteralPath $baselineCandidate)) {
    $bdoc = Read-JsonFile -Path $baselineCandidate
    if ($bdoc -and $bdoc.baseline_usdt -ne $null) {
        $baselineUsdt = [double]$bdoc.baseline_usdt
    }
}

$baselineMode = "none"
if ($null -ne $baselineUsdt -and $baselineUsdt -gt 0) {
    $baselineMode = "manual_or_env"
}
if ($null -eq $baselineUsdt) {
    if (Test-Path -LiteralPath $autoBaselinePath) {
        $adoc = Read-JsonFile -Path $autoBaselinePath
        if ($adoc -and $adoc.baseline_usdt -ne $null) {
            $bv = [double]$adoc.baseline_usdt
            if ($bv -gt 0) {
                $baselineUsdt = $bv
                $baselineMode = "auto_file"
            }
        }
    }
}
if ($null -eq $baselineUsdt -and $priv -and $priv.balance_total_usdt -ne $null) {
    $balNow = [double]$priv.balance_total_usdt
    if ($balNow -gt 0) {
        $baselineUsdt = $balNow
        $baselineMode = "auto_seeded"
        $autoPayload = [ordered]@{
            schema        = "showroom_equity_baseline_auto_v1"
            baseline_usdt = $balNow
            seeded_at_utc = $generatedUtc
            note          = "Anchored to balance on first run; delete file to re-anchor. Public bundle never includes wallet amounts."
        }
        $autoJson = $autoPayload | ConvertTo-Json -Depth 6
        $utf8Auto = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($autoBaselinePath, $autoJson, $utf8Auto)
    }
}

$pnlPct = $null
if ($null -ne $baselineUsdt -and $baselineUsdt -gt 0 -and $priv -and $priv.balance_total_usdt -ne $null) {
    $bal = [double]$priv.balance_total_usdt
    $pnlPct = [math]::Round((($bal - $baselineUsdt) / $baselineUsdt) * 100.0, 2)
    if ($pnlPct -gt 999.0) { $pnlPct = 999.0 }
    if ($pnlPct -lt -99.0) { $pnlPct = -99.0 }
}

$unrealPct = $null
if ($priv -and $priv.unrealized_pnl_usdt -ne $null -and $priv.balance_total_usdt -ne $null) {
    $bt = [double]$priv.balance_total_usdt
    if ($bt -gt 0) {
        $unrealPct = [math]::Round(([double]$priv.unrealized_pnl_usdt / $bt) * 100.0, 3)
        if ($unrealPct -gt 999.0) { $unrealPct = 999.0 }
        if ($unrealPct -lt -999.0) { $unrealPct = -999.0 }
    }
}

$dirSource = [Environment]::GetEnvironmentVariable("SHOWROOM_DIRECTION_SOURCE", "Process")
if ([string]::IsNullOrWhiteSpace($dirSource)) {
    if ($priv -and $priv.position_side) {
        $dirSource = "auto_account"
    } else {
        $dirSource = "auto_c2"
    }
} else {
    $dirSource = $dirSource.Trim().ToLowerInvariant()
}

$dirResolved = "c2"
if ($dirSource -eq "account" -or $dirSource -eq "auto_account") {
    $dirResolved = "account"
    $dirAbs = Get-PublicDirectionAbstractFromAccount -Priv $priv
} elseif ($dirSource -eq "c2" -or $dirSource -eq "auto_c2") {
    $dirResolved = "c2"
    $dirAbs = Get-PublicDirectionAbstractFromC2 -C2Status $c2Status
} else {
    $dirResolved = "c2"
    $dirAbs = Get-PublicDirectionAbstractFromC2 -C2Status $c2Status
}

$lamp = Get-C2SignalLamp -Status $c2Status

# Machine-readable UI tokens only (Korean copy ships in public_showroom_poll.html — avoids PS1 encoding issues on Windows).
$publicUi = [ordered]@{
    schema                         = "showroom_public_ui_v1"
    direction_abstract             = $dirAbs
    direction_source               = $dirResolved
    c2_lamp                        = $lamp
    ops_fusion_ok                  = $fusionOk
    return_pct_vs_baseline         = $pnlPct
    has_return_pct                 = ($null -ne $pnlPct)
    unrealized_pnl_pct_of_equity   = $unrealPct
    has_unrealized_pct             = ($null -ne $unrealPct)
    baseline_mode                  = $baselineMode
    unified_score_balanced         = $score
}

$delayed = [ordered]@{
    delay_seconds = $delaySec
    as_of_utc     = $asOf
}
if ($null -ne $pnlPct) {
    $delayed["pnl_pct_vs_start"] = $pnlPct
}

# ASCII-only abstract_reason avoids mojibake when writing UTF-8 without BOM edge cases in legacy consoles.
$abstract = "C2=$c2Status | exploratory monitor | no investment advice."
if ($null -ne $score) {
    $abstract = "C2=$c2Status | score_obs=$([math]::Round($score, 5)) | exploratory monitor | no investment advice."
}

$sys = Get-SystemStatus -RuntimeOk $runtimeOk -FusionOk $fusionOk
$eventId = "showroom-{0}-{1}" -f ([DateTimeOffset]::UtcNow.ToString("yyyyMMddTHHmmss")), ([guid]::NewGuid().ToString("N").Substring(0, 8))

$publicEvent = [ordered]@{
    timestamp                = $generatedUtc
    active_character_id      = "dragon_quant"
    risk_level               = (Get-RiskLevel -C2Status $c2Status)
    public_signal_direction  = (Get-PublicSignalDirection -C2Status $c2Status)
    abstract_reason          = $abstract
    schema_version           = "public-event.v1"
    event_id                 = $eventId
    source                   = "ops_showroom_bundle_v1"
    system_status            = $sys
    active_strategies_count  = 1
    delayed_metrics          = [ordered]@{}
    direction_abstract       = $dirAbs
    disclaimer_ref           = "jemaai_showroom_v1"
    last_ok_utc              = $generatedUtc
}

foreach ($k in $delayed.Keys) {
    $publicEvent.delayed_metrics[$k] = $delayed[$k]
}

$bundle = [ordered]@{
    schema               = "showroom_public_bundle_v1"
    generated_at_utc     = $generatedUtc
    runner               = "projects/bitcoin-trading/ops/windows-rehearsal/build_showroom_display_bundle.ps1"
    sources              = @{
        c2_guardrail_status = $c2Path
        ops_fusion_status     = $fusionPath
        runtime_health        = $runtimePath
    }
    observability        = @{
        unified_score_balanced = $score
        c2_status               = $c2Status
        c2_signal_lamp          = $lamp
        direction_abstract      = $dirAbs
        direction_source        = $dirResolved
        ops_fusion_overall_ok   = $fusionOk
        runtime_overall_ok      = $runtimeOk
        snapshot_as_of_utc      = $asOf
        public_pnl_pct_mode     = $(if ($null -ne $pnlPct) { "equity_vs_baseline_" + $baselineMode } else { "unavailable_no_metrics" })
    }
    public_ui            = $publicUi
    public_event_v1      = $publicEvent
}

$outArtifacts = Join-Path $root "docs\final\artifacts\showroom_public_bundle_v1.json"
$outMvp = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp\showroom_public_bundle_v1.json"

$jsonOpts = @{ Depth = 12 }
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
function Write-JsonNoBom {
    param([string]$Path, [string]$Json)
    [System.IO.File]::WriteAllText($Path, $Json, $utf8NoBom)
}
$bundleJson = $bundle | ConvertTo-Json @jsonOpts
Write-JsonNoBom -Path $outArtifacts -Json $bundleJson
Write-JsonNoBom -Path $outMvp -Json $bundleJson

$privateCmd = [ordered]@{
    schema                = "showroom_private_command_v1"
    generated_at_utc      = $generatedUtc
    runner                = "projects/bitcoin-trading/ops/windows-rehearsal/build_showroom_display_bundle.ps1"
    note                  = "Private lane — do not publish to public static CDN. Serve only behind auth."
    trading_metrics_path  = $privateMetricsPath
    overall_ok_runtime    = $runtimeOk
    overall_ok_fusion     = $fusionOk
    runtime_checked_at    = $runtimeTs
    position_snapshot     = $priv
}

$outPriv = Join-Path $root "projects\bitcoin-trading\memory\v2\ops\showroom_private_command_latest.json"
$privJson = $privateCmd | ConvertTo-Json @jsonOpts
Write-JsonNoBom -Path $outPriv -Json $privJson

Write-Host "[showroom-bundle] WROTE: $outArtifacts"
Write-Host "[showroom-bundle] WROTE: $outMvp"
Write-Host "[showroom-bundle] WROTE: $outPriv"
