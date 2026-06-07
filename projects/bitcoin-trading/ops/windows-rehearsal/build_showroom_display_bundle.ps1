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

function Format-ShowroomUtcZ {
    param($Raw)
    if ($null -eq $Raw) { return $null }
    if ($Raw -is [DateTime]) {
        $dt = [DateTime]$Raw
        if ($dt.Kind -eq [DateTimeKind]::Unspecified) {
            $dt = [DateTime]::SpecifyKind($dt, [DateTimeKind]::Utc)
        }
        return $dt.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    if ($Raw -is [DateTimeOffset]) {
        return $Raw.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    $s = [string]$Raw
    if ([string]::IsNullOrWhiteSpace($s)) { return $null }
    try {
        return ([DateTimeOffset]::Parse($s)).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    } catch {
        return $s
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

# Showroom UX tokens (public-event.v1 optional keys) — ASCII only; Korean copy lives in public_showroom_poll.html.
function Get-ShowroomDisplayMode {
    param([string]$SystemStatus, [string]$RiskLevel, [string]$PublicSignalDirection)
    $sys = ([string]$SystemStatus).Trim().ToLowerInvariant()
    if ($sys -eq "maintenance") { return "defend" }
    $r = ([string]$RiskLevel).Trim().ToUpperInvariant()
    if ($r -eq "SAFE") { return "idle" }
    if ($r -eq "WARNING" -or $r -eq "CRITICAL") { return "defend" }
    $d = ([string]$PublicSignalDirection).Trim().ToUpperInvariant()
    if ($d -match "^(BUY|LONG|SELL|SHORT)$") { return "attack" }
    return "idle"
}

function Get-ShowroomTickerKey {
    param([string]$SystemStatus, [string]$RiskLevel, [string]$PublicSignalDirection, [string]$DirAbstract)
    $sys = ([string]$SystemStatus).Trim().ToUpperInvariant() -replace "[^A-Z0-9]", ""
    if ([string]::IsNullOrWhiteSpace($sys)) { $sys = "ONLINE" }
    $r = ([string]$RiskLevel).Trim().ToUpperInvariant() -replace "[^A-Z0-9]", ""
    if ([string]::IsNullOrWhiteSpace($r)) { $r = "INFO" }
    $psd = ([string]$PublicSignalDirection).Trim().ToUpperInvariant() -replace "[^A-Z0-9]", ""
    if ([string]::IsNullOrWhiteSpace($psd)) { $psd = "HOLD" }
    $da = ([string]$DirAbstract).Trim().ToUpperInvariant() -replace "[^A-Z0-9]", ""
    if ([string]::IsNullOrWhiteSpace($da)) { $da = "FLAT" }
    "S_{0}_R_{1}_PSD_{2}_DA_{3}" -f $sys, $r, $psd, $da
}

function Get-ShowroomReactionLineIds {
    param([string]$DisplayMode, [string]$SystemStatus, [string]$RiskLevel)
    $out = [System.Collections.ArrayList]@()
    if (([string]$SystemStatus).Trim().ToLowerInvariant() -eq "maintenance") {
        [void]$out.Add("R_SYS_MAINT_01")
    }
    $m = ([string]$DisplayMode).Trim().ToLowerInvariant()
    $rk = ([string]$RiskLevel).Trim().ToUpperInvariant()
    if ($m -eq "defend") {
        [void]$out.Add("R_MODE_DEF_01")
        if ($rk -match "WARNING|CRITICAL") { [void]$out.Add("R_RISK_HIGH_01") }
    }
    elseif ($m -eq "attack") {
        [void]$out.Add("R_MODE_ATK_01")
    }
    else {
        [void]$out.Add("R_MODE_IDLE_01")
    }
    if ($out.Count -gt 3) {
        return @($out[0], $out[1], $out[2])
    }
    return @($out)
}

$root = $WorkspaceRoot
$c2Path = Join-Path $root "docs\final\artifacts\c2_aegis_guardrail_status_latest.json"
$fusionPath = Join-Path $root "docs\final\artifacts\ops_fusion_cycle_status_latest.json"
$runtimePath = Join-Path $root "projects\bitcoin-trading\memory\v2\ops\runtime_health_latest.json"
$privateMetricsPath = Join-Path $root "projects\bitcoin-trading\memory\v2\public\public_trading_metrics_latest.json"
$tradeWindowPath = Join-Path $root "projects\bitcoin-trading\exports\cursor_trade_history\all_trades_latest_24h.json"
$daemonStatusPath = Join-Path $root "projects\bitcoin-trading\memory\v2\status\trading_daemon_status.json"
$tradingStatePath = Join-Path $root "projects\bitcoin-trading\logs\trading_state.json"
$baselineCandidate = Join-Path $root "projects\bitcoin-trading\memory\v2\ops\showroom_equity_baseline_usdt.local.json"
$autoBaselinePath = Join-Path $root "projects\bitcoin-trading\memory\v2\ops\showroom_equity_baseline_auto.json"
$logos4dStatePath = Join-Path $root "docs\final\artifacts\logos_4d_state_v1_latest.json"
$logosGraphBundlePath = Join-Path $root "docs\final\artifacts\logos_corpus_graph_bundle_v1_latest.json"
$logosFreshnessSidecarPath = Join-Path $root "docs\final\artifacts\logos_track_c_freshness_sidecar_v1_latest.json"
$topologySnapshotPath = Join-Path $root "docs\final\artifacts\showroom_topology_radar_snapshot_v1_latest.json"
$macroHorizonSlicePath = Join-Path $root "docs\final\artifacts\showroom_macro_horizon_2030_slice_v1_latest.json"
$exodusPressurePath = Join-Path $root "docs\final\artifacts\exodus_pressure_v1_latest.json"

$c2 = Read-JsonFile -Path $c2Path
$fusion = Read-JsonFile -Path $fusionPath
$runtime = Read-JsonFile -Path $runtimePath
$priv = Read-JsonFile -Path $privateMetricsPath
$tradeWindow = Read-JsonFile -Path $tradeWindowPath
$daemonStatus = Read-JsonFile -Path $daemonStatusPath
$tradingState = Read-JsonFile -Path $tradingStatePath
$logos4d = Read-JsonFile -Path $logos4dStatePath
$logosGraphDoc = Read-JsonFile -Path $logosGraphBundlePath
$freshnessDoc = Read-JsonFile -Path $logosFreshnessSidecarPath
$topologyDoc = Read-JsonFile -Path $topologySnapshotPath
$macroHorizonDoc = Read-JsonFile -Path $macroHorizonSlicePath

$logosGraphBundlePresent = $false
$logosGraphNlc = $null
$logosGraphElc = $null
$logosGraphDedupe = $null
$logosGraphTs = $null
$logosGraphMeta = [ordered]@{
    present         = $false
    schema          = "showroom_logos_graph_meta_v1"
    hypothesis_tier = "B"
}
if ($logosGraphDoc -and [string]$logosGraphDoc.schema -eq "logos_corpus_graph_bundle_v1") {
    $logosGraphBundlePresent = $true
    if ($logosGraphDoc.dedupe_bundle_key_sha256) { $logosGraphDedupe = [string]$logosGraphDoc.dedupe_bundle_key_sha256 }
    if ($logosGraphDoc.ts_utc) {
        $rawTsG = $logosGraphDoc.ts_utc
        if ($rawTsG -is [DateTime]) {
            $dtG = [DateTime]$rawTsG
            if ($dtG.Kind -eq [DateTimeKind]::Unspecified) {
                $dtG = [DateTime]::SpecifyKind($dtG, [DateTimeKind]::Utc)
            }
            $logosGraphTs = $dtG.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        } elseif ($rawTsG -is [DateTimeOffset]) {
            $logosGraphTs = $rawTsG.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        } else {
            $logosGraphTs = [string]$rawTsG
        }
    }
    if ($logosGraphDoc.graph_files) {
        if ($logosGraphDoc.graph_files.nodes_line_count -ne $null) { $logosGraphNlc = [int]$logosGraphDoc.graph_files.nodes_line_count }
        if ($logosGraphDoc.graph_files.edges_line_count -ne $null) { $logosGraphElc = [int]$logosGraphDoc.graph_files.edges_line_count }
    }
    $logosGraphMeta = [ordered]@{
        present                  = $true
        schema                   = "showroom_logos_graph_meta_v1"
        hypothesis_tier          = "B"
        source_schema            = "logos_corpus_graph_bundle_v1"
        dedupe_bundle_key_sha256 = $logosGraphDedupe
        ts_utc                   = $logosGraphTs
        nodes_line_count         = $logosGraphNlc
        edges_line_count         = $logosGraphElc
    }
}

$freshnessSidecarPresent = $false
$freshnessStalenessSec = $null
$freshnessGeneratedAtUtc = $null
if ($freshnessDoc -and [string]$freshnessDoc.schema -eq "logos_track_c_freshness_sidecar_v1") {
    $freshnessSidecarPresent = $true
    if ($freshnessDoc.freshness -and $freshnessDoc.freshness.staleness_seconds -ne $null) {
        try { $freshnessStalenessSec = [int]$freshnessDoc.freshness.staleness_seconds } catch { $freshnessStalenessSec = $null }
    }
    if ($freshnessDoc.generated_at_utc) {
        $freshnessGeneratedAtUtc = Format-ShowroomUtcZ -Raw $freshnessDoc.generated_at_utc
    }
}

function Format-TopologyUtcString {
    param($Raw)
    return Format-ShowroomUtcZ -Raw $Raw
}

$topologyRadarPresent = $false
$topologyRadarGenAt = $null
$topologyRadarStaleAfter = $null
$topologyRadarHypo = $null
$topologyRadarRefCount = $null
$topologyRadarNoTrade = $null
$topologyRadarDisclaimer = $null
$topologyRadarStub = $false
if ($topologyDoc -and [string]$topologyDoc.schema_version -eq "showroom_topology_radar_snapshot_v1" -and ($topologyDoc.no_trade_signals -eq $true)) {
    $topologyRadarPresent = $true
    $topologyRadarGenAt = Format-TopologyUtcString -Raw $topologyDoc.generated_at_utc
    $topologyRadarStaleAfter = Format-TopologyUtcString -Raw $topologyDoc.stale_after_utc
    if ($topologyDoc.hypo_banner) {
        $topologyRadarHypo = [string]$topologyDoc.hypo_banner
        if ($topologyRadarHypo.Length -gt 480) { $topologyRadarHypo = $topologyRadarHypo.Substring(0, 480) }
        if ($topologyRadarHypo -match "(?i)stub") { $topologyRadarStub = $true }
    }
    if ($topologyDoc.artifact_refs) {
        try { $topologyRadarRefCount = @($topologyDoc.artifact_refs).Count } catch { $topologyRadarRefCount = $null }
    }
    if ($topologyDoc.no_trade_signals -ne $null) {
        $topologyRadarNoTrade = [bool]$topologyDoc.no_trade_signals
    }
    if ($topologyDoc.disclaimer_ref) {
        $topologyRadarDisclaimer = [string]$topologyDoc.disclaimer_ref
    }
}

$macroHorizonPresent = $false
$macroHorizonGenAt = $null
$macroHorizonStaleAfter = $null
$macroHorizonHypo = $null
$macroHorizonFinalAction = $null
$macroHorizonBtcBase = $null
$macroHorizonBtcStress = $null
$macroHorizonNoTrade = $null
$macroHorizonDisclaimer = $null
if ($macroHorizonDoc -and [string]$macroHorizonDoc.schema_version -eq "showroom_macro_horizon_2030_slice_v1" -and ($macroHorizonDoc.no_trade_signals -eq $true)) {
    $macroHorizonPresent = $true
    $macroHorizonGenAt = Format-TopologyUtcString -Raw $macroHorizonDoc.generated_at_utc
    $macroHorizonStaleAfter = Format-TopologyUtcString -Raw $macroHorizonDoc.stale_after_utc
    if ($macroHorizonDoc.hypo_banner) {
        $macroHorizonHypo = [string]$macroHorizonDoc.hypo_banner
        if ($macroHorizonHypo.Length -gt 480) { $macroHorizonHypo = $macroHorizonHypo.Substring(0, 480) }
    }
    if ($macroHorizonDoc.final_action) { $macroHorizonFinalAction = [string]$macroHorizonDoc.final_action }
    if ($macroHorizonDoc.btc_path) {
        if ($macroHorizonDoc.btc_path.base_weight -ne $null) { $macroHorizonBtcBase = [double]$macroHorizonDoc.btc_path.base_weight }
        if ($macroHorizonDoc.btc_path.stress_weight -ne $null) { $macroHorizonBtcStress = [double]$macroHorizonDoc.btc_path.stress_weight }
    }
    if ($macroHorizonDoc.no_trade_signals -ne $null) { $macroHorizonNoTrade = [bool]$macroHorizonDoc.no_trade_signals }
    if ($macroHorizonDoc.disclaimer_ref) { $macroHorizonDisclaimer = [string]$macroHorizonDoc.disclaimer_ref }
}

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

function Get-NewestUtcAnchor {
    param([string[]]$Candidates)
    $bestStr = $null
    $bestDto = $null
    foreach ($c in $Candidates) {
        if ([string]::IsNullOrWhiteSpace($c)) { continue }
        try {
            $dto = [DateTimeOffset]::Parse($c)
            if ($null -eq $bestDto -or $dto -gt $bestDto) {
                $bestDto = $dto
                $bestStr = $c
            }
        } catch {
            # ignore unparsable
        }
    }
    return @{ UtcString = $bestStr; Dto = $bestDto }
}

# Showroom context age: C2 guardrail may lag; prefer freshest Track-C observability anchor.
$contextAnchorSource = "generated_fallback"
$anchorPick = Get-NewestUtcAnchor -Candidates @($c2AsOf, $freshnessGeneratedAtUtc, $topologyRadarGenAt, $macroHorizonGenAt, $generatedUtc)
$asOf = $anchorPick.UtcString
if ([string]::IsNullOrWhiteSpace($asOf)) { $asOf = $generatedUtc; $contextAnchorSource = "generated_fallback" }
elseif ($asOf -eq $c2AsOf) { $contextAnchorSource = "c2_guardrail" }
elseif ($asOf -eq $freshnessGeneratedAtUtc) { $contextAnchorSource = "logos_freshness_sidecar" }
elseif ($asOf -eq $topologyRadarGenAt) { $contextAnchorSource = "topology_radar_snapshot" }
elseif ($asOf -eq $macroHorizonGenAt) { $contextAnchorSource = "macro_horizon_2030_slice" }
else { $contextAnchorSource = "generated_fallback" }

$contextTtlSec = 14400
try {
    $ttlRaw = [Environment]::GetEnvironmentVariable("SHOWROOM_CONTEXT_TTL_SECONDS", "Process")
    if (-not [string]::IsNullOrWhiteSpace($ttlRaw)) {
        $contextTtlSec = [int]$ttlRaw
    }
} catch {}
if ($contextTtlSec -lt 300) { $contextTtlSec = 300 }

$contextAgeSec = $null
$contextStale = $false
try {
    $asOfDt = [DateTimeOffset]::Parse($asOf)
    $contextAgeSec = [math]::Max(0, [int]([DateTimeOffset]::UtcNow - $asOfDt).TotalSeconds)
    $contextStale = ($contextAgeSec -gt $contextTtlSec)
} catch {
    $contextStale = $true
}

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

$tradeCount24h = 0
$latestTradeTs = $null
$latestTradeSide = "unknown"
if ($tradeWindow -and $tradeWindow.counts -and $tradeWindow.counts.total -ne $null) {
    $tradeCount24h = [int]$tradeWindow.counts.total
}
if ($tradeWindow) {
    $allTrades = @()
    if ($tradeWindow.control) { $allTrades += @($tradeWindow.control) }
    if ($tradeWindow.treatment) { $allTrades += @($tradeWindow.treatment) }
    if ($allTrades.Count -gt 0) {
        $tsKeys = @("timestamp","ts","time","created_at","updated_at","entry_time","exit_time","opened_at","closed_at","event_time","signal_time")
        $sideKeys = @("side","position_side","signal","direction","action")
        $best = $null
        $bestDt = $null
        foreach ($t in $allTrades) {
            foreach ($k in $tsKeys) {
                if ($t.PSObject.Properties.Name -contains $k -and $t.$k) {
                    try {
                        $d = [DateTimeOffset]::Parse([string]$t.$k)
                        if ($null -eq $bestDt -or $d -gt $bestDt) {
                            $bestDt = $d
                            $best = $t
                        }
                    } catch {}
                    break
                }
            }
        }
        if ($bestDt) { $latestTradeTs = $bestDt.ToString("o") }
        if ($best) {
            foreach ($k in $sideKeys) {
                if ($best.PSObject.Properties.Name -contains $k -and $best.$k) {
                    $latestTradeSide = [string]$best.$k
                    break
                }
            }
        }
    }
}
$recentFillsCount = $null
$positionSide = $null
if ($tradingState -and $tradingState.startup_reconcile) {
    if ($tradingState.startup_reconcile.recent_fills_count -ne $null) {
        $recentFillsCount = [int]$tradingState.startup_reconcile.recent_fills_count
    }
    if ($tradingState.startup_reconcile.position_side) {
        $positionSide = [string]$tradingState.startup_reconcile.position_side
    }
}
if ($tradeCount24h -le 0 -and $null -ne $recentFillsCount -and $recentFillsCount -gt 0) {
    $tradeCount24h = $recentFillsCount
}
if (($latestTradeSide -eq "unknown" -or [string]::IsNullOrWhiteSpace($latestTradeSide)) -and -not [string]::IsNullOrWhiteSpace($positionSide)) {
    $latestTradeSide = $positionSide
}
$successfulTrades = $null
$failedTrades = $null
if ($daemonStatus) {
    if ($daemonStatus.successful_trades -ne $null) { $successfulTrades = [int]$daemonStatus.successful_trades }
    if ($daemonStatus.failed_trades -ne $null) { $failedTrades = [int]$daemonStatus.failed_trades }
}
if (($null -eq $successfulTrades -or $successfulTrades -le 0) -and $null -ne $recentFillsCount -and $recentFillsCount -gt 0) {
    $successfulTrades = $recentFillsCount
}

$signalTotalCount = 0
$lastSignalUtc = $null
$integratedSignal = "HOLD"
$integratedConfidence = $null
$minConfidence = 0.52
$singularAction = "LOCKED"
$singularDecision = "HOLD"
$singularReason = "unknown"
$singularScore = $null
$warningLevel = "NORMAL"
$regimeDefenseMode = $false
$regimeId = "unknown"
if ($tradingState) {
    if ($tradingState.signal_total_count -ne $null) {
        $signalTotalCount = [int]$tradingState.signal_total_count
    }
    if ($tradingState.last_signal_summary) {
        $lss = $tradingState.last_signal_summary
        if ($lss.timestamp) { $lastSignalUtc = [string]$lss.timestamp }
        if ($lss.integrated_signal) { $integratedSignal = [string]$lss.integrated_signal }
        if ($lss.integrated_confidence -ne $null) { $integratedConfidence = [double]$lss.integrated_confidence }
        if ($lss.singular_action) { $singularAction = [string]$lss.singular_action }
        if ($lss.singular_decision) { $singularDecision = [string]$lss.singular_decision }
        if ($lss.singular_reason) { $singularReason = [string]$lss.singular_reason }
        if ($lss.singular_score -ne $null) { $singularScore = [double]$lss.singular_score }
        if ($lss.warning_level) { $warningLevel = [string]$lss.warning_level }
        if ($lss.regime_defense_mode -ne $null) { $regimeDefenseMode = [bool]$lss.regime_defense_mode }
        if ($lss.regime_id) { $regimeId = [string]$lss.regime_id }
    }
}
$lockReason = "NONE"
if ($signalTotalCount -le 0) {
    $lockReason = "WARMUP"
} elseif ($regimeDefenseMode) {
    $lockReason = "REGIME_DEFENSE"
} elseif ([string]$warningLevel -eq "CRITICAL") {
    $lockReason = "RISK_GUARD"
} elseif ($null -ne $integratedConfidence -and [double]$integratedConfidence -lt $minConfidence) {
    $lockReason = ("MIN_CONFIDENCE({0:0.00}<{1:0.00})" -f [double]$integratedConfidence, $minConfidence)
} elseif ([string]$singularAction -eq "LOCKED") {
    if (-not [string]::IsNullOrWhiteSpace($singularReason) -and $singularReason -ne "unknown") {
        if ($null -ne $singularScore) {
            $lockReason = ("SINGULAR_HOLD({0};score={1:0.00})" -f $singularReason, [double]$singularScore)
        } else {
            $lockReason = "SINGULAR_HOLD:" + $singularReason
        }
    } else {
        $lockReason = "SINGULAR_HOLD"
    }
} elseif ([string]$integratedSignal -eq "HOLD") {
    $lockReason = "INTEGRATED_HOLD"
}

# Machine-readable UI tokens only (Korean copy ships in public_showroom_poll.html — avoids PS1 encoding issues on Windows).
$logosXIndex = $null
$logosYFrag = $null
$logosQuad = $null
$logosXBand = $null
$logos4dGenAt = $null
if ($logos4d -and $logos4d.schema -eq "logos_4d_state_v1") {
    if ($logos4d.generated_at_utc) {
        $rawGa = $logos4d.generated_at_utc
        if ($rawGa -is [DateTime]) { $logos4dGenAt = $rawGa.ToString("o") }
        else { $logos4dGenAt = [string]$rawGa }
    }
    if ($logos4d.quadrant_info -and $logos4d.quadrant_info.current_quadrant) {
        $logosQuad = [string]$logos4d.quadrant_info.current_quadrant
    }
    $cx = $logos4d.coordinates
    if ($cx) {
        if ($cx.x_exodus_pressure -ne $null) {
            $xv = [double]$cx.x_exodus_pressure
            $logosXIndex = [int][math]::Round([math]::Max(0.0, [math]::Min(100.0, $xv)), 0)
            if ($logosXIndex -lt 40) { $logosXBand = "LOW" }
            elseif ($logosXIndex -le 60) { $logosXBand = "MID" }
            else { $logosXBand = "HIGH" }
        }
        if ($cx.y_babel_fragility -ne $null) {
            $yv = [double]$cx.y_babel_fragility
            $logosYFrag = [int][math]::Round([math]::Max(0.0, [math]::Min(100.0, $yv)), 0)
        }
    }
}

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
    logos_x_band                   = $logosXBand
    logos_quadrant                 = $logosQuad
    logos_x_index_0_100            = $logosXIndex
    logos_y_fragility_0_100      = $logosYFrag
}

$delayed = [ordered]@{
    delay_seconds = $delaySec
    as_of_utc     = $asOf
}
if ($null -ne $pnlPct) {
    $delayed["pnl_pct_vs_start"] = $pnlPct
}
if ($null -ne $logosXIndex) { $delayed["logos_x_index_0_100"] = $logosXIndex }
if ($null -ne $logosXBand) { $delayed["logos_x_band"] = $logosXBand }
if (-not [string]::IsNullOrWhiteSpace($logosQuad)) { $delayed["logos_quadrant"] = $logosQuad }
if ($null -ne $logosYFrag) { $delayed["logos_y_fragility_0_100"] = $logosYFrag }
if (-not [string]::IsNullOrWhiteSpace($logos4dGenAt)) { $delayed["logos_4d_state_generated_at_utc"] = $logos4dGenAt }

$delayed["logos_graph_bundle_present"] = $logosGraphBundlePresent
if ($logosGraphBundlePresent) {
    if ($null -ne $logosGraphNlc) { $delayed["logos_graph_nodes_line_count"] = $logosGraphNlc }
    if ($null -ne $logosGraphElc) { $delayed["logos_graph_edges_line_count"] = $logosGraphElc }
    if (-not [string]::IsNullOrWhiteSpace($logosGraphDedupe)) { $delayed["logos_graph_bundle_dedupe_sha256"] = $logosGraphDedupe }
    if (-not [string]::IsNullOrWhiteSpace($logosGraphTs)) { $delayed["logos_graph_bundle_ts_utc"] = $logosGraphTs }
}
if ($null -ne $freshnessStalenessSec) {
    $delayed["logos_graph_staleness_seconds"] = $freshnessStalenessSec
}
if ($freshnessSidecarPresent -and -not [string]::IsNullOrWhiteSpace($freshnessGeneratedAtUtc)) {
    $delayed["logos_freshness_sidecar_generated_at_utc"] = $freshnessGeneratedAtUtc
}

# ASCII-only abstract_reason avoids mojibake when writing UTF-8 without BOM edge cases in legacy consoles.
$abstract = "C2=$c2Status | exploratory monitor | no investment advice."
if ($null -ne $score) {
    $abstract = "C2=$c2Status | score_obs=$([math]::Round($score, 5)) | exploratory monitor | no investment advice."
}
if ($signalTotalCount -gt 0) {
    $abstract = "$abstract | signal=$integratedSignal/$singularAction | regime=$regimeId"
}
if ($null -ne $logosXBand -and -not [string]::IsNullOrWhiteSpace($logosQuad)) {
    $abstract = "$abstract | logos_x=$logosXBand quad=$logosQuad [NON_GATING]"
} elseif ($null -ne $logosXBand) {
    $abstract = "$abstract | logos_x=$logosXBand [NON_GATING]"
}
if ($logosGraphBundlePresent) {
    $abstract = "$abstract | logos_graph_bundle=B [NON_GATING]"
}
if ($topologyRadarPresent) {
    $abstract = "$abstract | topology_radar_snapshot=B [NON_GATING]"
}
if ($macroHorizonPresent) {
    $mhTail = if ($null -ne $macroHorizonBtcBase -and $null -ne $macroHorizonBtcStress) {
        " btc_base_stress=$macroHorizonBtcBase/$macroHorizonBtcStress"
    } else { "" }
    $abstract = "$abstract | macro_horizon_2030=$macroHorizonFinalAction$mhTail [HYPO][NON_GATING]"
}

$sys = Get-SystemStatus -RuntimeOk $runtimeOk -FusionOk $fusionOk
if ($contextStale) { $sys = "degraded" }
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
    order_summary_public     = [ordered]@{
        trades_24h_count      = $tradeCount24h
        latest_trade_utc      = $latestTradeTs
        latest_trade_side     = $latestTradeSide
        successful_trades_all = $successfulTrades
        failed_trades_all     = $failedTrades
    }
    signal_gate_public       = [ordered]@{
        signal_total_count    = $signalTotalCount
        last_signal_utc       = $lastSignalUtc
        integrated_signal     = $integratedSignal
        integrated_confidence = $integratedConfidence
        singular_action       = $singularAction
        singular_decision     = $singularDecision
        singular_reason       = $singularReason
        warning_level         = $warningLevel
        regime_defense_mode   = $regimeDefenseMode
        regime_id             = $regimeId
        lock_reason           = $lockReason
    }
}

if ($contextStale) {
    $publicEvent.risk_level = "WARNING"
    $publicEvent.public_signal_direction = "HOLD"
    $publicEvent.abstract_reason = "context_stale_age=${contextAgeSec}s | fallback_hold | no investment advice."
}

$sdm = Get-ShowroomDisplayMode -SystemStatus $sys -RiskLevel $publicEvent.risk_level -PublicSignalDirection $publicEvent.public_signal_direction
if ($contextStale) { $sdm = "defend" }
$publicEvent.showroom_display_mode = $sdm
$publicEvent.showroom_ticker_key = Get-ShowroomTickerKey -SystemStatus $sys -RiskLevel $publicEvent.risk_level -PublicSignalDirection $publicEvent.public_signal_direction -DirAbstract $dirAbs
$publicEvent.showroom_reaction_line_ids = @(Get-ShowroomReactionLineIds -DisplayMode $sdm -SystemStatus $sys -RiskLevel $publicEvent.risk_level)

foreach ($k in $delayed.Keys) {
    $publicEvent.delayed_metrics[$k] = $delayed[$k]
}

# Lens media Thin Slice (Track C §3.9) — weekday CPU mapping -> playback_id + video_playback_id.
$lensMediaBuilder = Join-Path $root "scripts\build_showroom_lens_media_observability_v1.py"
$lensAudioBlockPath = Join-Path $root "docs\final\artifacts\showroom_lens_audio_observability_v1_latest.json"
$lensVideoBlockPath = Join-Path $root "docs\final\artifacts\showroom_lens_video_observability_v1_latest.json"
$lensMediaPresent = $false
$lensPlaybackId = $null
$lensVideoPlaybackId = $null
$lensGateDecision = $null
$lensVideoGateDecision = $null
if (Test-Path -LiteralPath $lensMediaBuilder) {
    try {
        & py $lensMediaBuilder --showroom-display-mode $sdm --audio-out-json $lensAudioBlockPath --video-out-json $lensVideoBlockPath 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $lensAudioBlockPath)) {
            $lensBlock = Read-JsonFile -Path $lensAudioBlockPath
            $lensVideoBlock = $null
            if (Test-Path -LiteralPath $lensVideoBlockPath) {
                $lensVideoBlock = Read-JsonFile -Path $lensVideoBlockPath
            }
            if ($lensBlock -and [string]$lensBlock.schema -eq "public_event_lens_audio_thin_slice_v1") {
                $publicEvent["lens_audio_observability_v1"] = $lensBlock
                $publicEvent["research_only"] = $true
                $lensMediaPresent = $true
                if ($lensBlock.playback_id) { $lensPlaybackId = [string]$lensBlock.playback_id }
                if ($lensBlock.gate -and $lensBlock.gate.decision) { $lensGateDecision = [string]$lensBlock.gate.decision }
                if ($lensVideoBlock -and [string]$lensVideoBlock.schema -eq "public_event_lens_video_thin_slice_v1") {
                    $publicEvent["lens_video_observability_v1"] = $lensVideoBlock
                    if ($lensVideoBlock.video_playback_id) { $lensVideoPlaybackId = [string]$lensVideoBlock.video_playback_id }
                    if ($lensVideoBlock.gate -and $lensVideoBlock.gate.decision) { $lensVideoGateDecision = [string]$lensVideoBlock.gate.decision }
                }
                $videoTail = if ($lensVideoPlaybackId) { " lens_video=$lensVideoPlaybackId gate_v=$lensVideoGateDecision" } else { "" }
                $publicEvent.abstract_reason = "$abstract | lens_audio=$lensPlaybackId gate=$lensGateDecision$videoTail [HYPO][NON_GATING]"
            }
        }
    } catch {
        Write-Warning "[showroom-bundle] lens media observability skipped: $_"
    }
}

$observability = [ordered]@{
        unified_score_balanced = $score
        c2_status               = $c2Status
        c2_signal_lamp          = $lamp
        direction_abstract      = $dirAbs
        direction_source        = $dirResolved
        ops_fusion_overall_ok   = $fusionOk
        runtime_overall_ok      = $runtimeOk
        snapshot_as_of_utc      = $asOf
        context_age_seconds     = $contextAgeSec
        context_ttl_seconds     = $contextTtlSec
        context_stale           = $contextStale
        context_anchor_source   = $contextAnchorSource
        public_pnl_pct_mode     = $(if ($null -ne $pnlPct) { "equity_vs_baseline_" + $baselineMode } else { "unavailable_no_metrics" })
        logos_x_index_0_100     = $logosXIndex
        logos_x_band            = $logosXBand
        logos_quadrant          = $logosQuad
        logos_y_fragility_0_100 = $logosYFrag
        logos_graph_meta        = $logosGraphMeta
        track_b_non_gating      = $true
        logos_freshness_sidecar_present   = $freshnessSidecarPresent
        logos_freshness_staleness_seconds  = $freshnessStalenessSec
        logos_freshness_generated_at_utc   = $freshnessGeneratedAtUtc
}
if ($topologyRadarPresent) {
    $observability["topology_radar_snapshot_present"] = $true
    $observability["topology_radar_snapshot_generated_at_utc"] = $topologyRadarGenAt
    $observability["topology_radar_snapshot_stale_after_utc"] = $topologyRadarStaleAfter
    $observability["topology_radar_snapshot_hypo_banner"] = $topologyRadarHypo
    $observability["topology_radar_snapshot_artifact_ref_count"] = $topologyRadarRefCount
    $observability["topology_radar_snapshot_no_trade_signals"] = $topologyRadarNoTrade
    $observability["topology_radar_snapshot_disclaimer_ref"] = $topologyRadarDisclaimer
    $observability["topology_radar_snapshot_stub"] = $topologyRadarStub
}
if ($macroHorizonPresent) {
    $observability["macro_horizon_2030_snapshot_present"] = $true
    $observability["macro_horizon_2030_snapshot_generated_at_utc"] = $macroHorizonGenAt
    $observability["macro_horizon_2030_snapshot_stale_after_utc"] = $macroHorizonStaleAfter
    $observability["macro_horizon_2030_snapshot_hypo_banner"] = $macroHorizonHypo
    $observability["macro_horizon_2030_snapshot_final_action"] = $macroHorizonFinalAction
    $observability["macro_horizon_2030_snapshot_btc_base_weight"] = $macroHorizonBtcBase
    $observability["macro_horizon_2030_snapshot_btc_stress_weight"] = $macroHorizonBtcStress
    $observability["macro_horizon_2030_snapshot_no_trade_signals"] = $macroHorizonNoTrade
    $observability["macro_horizon_2030_snapshot_disclaimer_ref"] = $macroHorizonDisclaimer
}
if ($lensMediaPresent) {
    $observability["lens_audio_observability_present"] = $true
    $observability["lens_audio_playback_id"] = $lensPlaybackId
    $observability["lens_audio_gate_decision"] = $lensGateDecision
    $observability["lens_audio_track_b_hypo"] = $true
    if ($lensVideoPlaybackId) {
        $observability["lens_video_observability_present"] = $true
        $observability["lens_video_playback_id"] = $lensVideoPlaybackId
        $observability["lens_video_gate_decision"] = $lensVideoGateDecision
        $observability["lens_video_track_b_hypo"] = $true
    }
}

$bundle = [ordered]@{
    schema               = "showroom_public_bundle_v1"
    generated_at_utc     = $generatedUtc
    runner               = "projects/bitcoin-trading/ops/windows-rehearsal/build_showroom_display_bundle.ps1"
    sources              = @{
        c2_guardrail_status = $c2Path
        ops_fusion_status     = $fusionPath
        runtime_health        = $runtimePath
        trade_window_24h      = $tradeWindowPath
        daemon_status         = $daemonStatusPath
        trading_state         = $tradingStatePath
        logos_4d_state_v1          = $logos4dStatePath
        logos_corpus_graph_bundle_v1 = $logosGraphBundlePath
        logos_track_c_freshness_sidecar_v1 = $logosFreshnessSidecarPath
        showroom_topology_radar_snapshot_v1 = $topologySnapshotPath
        showroom_macro_horizon_2030_slice_v1 = $macroHorizonSlicePath
        exodus_pressure_v1    = $exodusPressurePath
        lens_music_hormone_trend_v1 = (Join-Path $root "docs\final\artifacts\lens_music_hormone_trend_latest.json")
        dynamic_bgm_hp_sweep_v1 = (Join-Path $root "docs\final\artifacts\dynamic_bgm_hp_sweep_v1_latest.json")
        showroom_lens_audio_observability_v1 = $lensAudioBlockPath
        showroom_lens_video_observability_v1 = $lensVideoBlockPath
    }
    observability        = $observability
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
