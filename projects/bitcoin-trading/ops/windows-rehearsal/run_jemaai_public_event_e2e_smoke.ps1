param(
    [string]$ApiBaseUrl = "https://api.jemaai.cloud",
    [int]$TimeoutSec = 10,
    [string]$PublicEventToken = "",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_smoke_report_latest.json"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($PublicEventToken)) {
    # Prefer User-scope token to avoid stale process env mismatch.
    $PublicEventToken = [Environment]::GetEnvironmentVariable("PUBLIC_EVENT_GATEWAY_TOKEN", "User")
    if ([string]::IsNullOrWhiteSpace($PublicEventToken)) {
        $PublicEventToken = $env:PUBLIC_EVENT_GATEWAY_TOKEN
    }
}

function Write-Step([string]$name, [bool]$ok, [string]$detail) {
    $status = if ($ok) { "PASS" } else { "FAIL" }
    $color = if ($ok) { "Green" } else { "Red" }
    $safeDetail = if ([string]::IsNullOrWhiteSpace($detail)) { "-" } else { $detail }
    Write-Host ("[{0}] {1} - {2}" -f $status, $name, $safeDetail) -ForegroundColor $color
}

function Invoke-JsonGet([string]$url) {
    $r = Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -TimeoutSec $TimeoutSec
    return ($r.Content | ConvertFrom-Json -ErrorAction Stop)
}

function Invoke-JsonPost([string]$url, [object]$body) {
    $raw = $body | ConvertTo-Json -Depth 8 -Compress
    $args = @{
        Uri         = $url
        Method      = "POST"
        ContentType = "application/json"
        Body        = $raw
        TimeoutSec  = $TimeoutSec
    }
    if (-not [string]::IsNullOrWhiteSpace($PublicEventToken)) {
        $args.Headers = @{ "X-Public-Event-Token" = $PublicEventToken }
    }
    return Invoke-RestMethod @args
}

function Expected-CharacterId([string]$rawId) {
    $id = ""
    if (-not [string]::IsNullOrWhiteSpace($rawId)) {
        $id = $rawId.Trim().ToLowerInvariant()
    }
    $allow = @(
        "rat_arbitrage","ox_guard","tiger_shield","rabbit_scalper",
        "dragon_quant","snake_hedger","horse_trend","sheep_yield",
        "monkey_momentum","rooster_oracle","dog_sentinel","pig_accumulator",
        "demo_guard","unknown_guard","bull_alpha","bear_shield"
    )
    if ([string]::IsNullOrWhiteSpace($id)) { return "unknown_guard" }
    if ($allow -contains $id) { return $id }
    if ($id.Contains("bull") -or $id.Contains("attack")) { return "bull_alpha" }
    if ($id.Contains("bear") -or $id.Contains("shield") -or $id.Contains("guard")) { return "bear_shield" }
    return "unknown_guard"
}

function Wait-LatestEvent([string]$url, [string]$expectedEventId, [int]$waitMs = 2400) {
    $attempts = [Math]::Max(1, [Math]::Ceiling($waitMs / 300))
    for ($i = 0; $i -lt $attempts; $i += 1) {
        $latest = Invoke-JsonGet -url $url
        if ($null -ne $latest -and [string]$latest.event_id -eq $expectedEventId) {
            return $latest
        }
        Start-Sleep -Milliseconds 300
    }
    return $null
}

function Read-BundleRuntime([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try {
        $doc = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
        if ($doc.PSObject.Properties.Name -contains "runtime") { return $doc.runtime }
        if ($doc.PSObject.Properties.Name -contains "observability") { return $doc.observability }
        return $null
    } catch {
        return $null
    }
}

$latestUrl = $ApiBaseUrl.TrimEnd("/") + "/api/public-events/latest"
$ingestUrl = $ApiBaseUrl.TrimEnd("/") + "/api/public-events/ingest"
$profilesUrl = $ApiBaseUrl.TrimEnd("/") + "/character_profiles_v1_1.json"
$showroomUrl = $ApiBaseUrl.TrimEnd("/") + "/public_showroom_poll.html"
$bundleBuildScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\build_showroom_display_bundle.ps1"
$bundlePublishScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\publish_showroom_public_event.ps1"
$bundlePath = Join-Path $WorkspaceRoot "docs\final\artifacts\showroom_public_bundle_v1.json"

$results = @()
$detailMap = [ordered]@{}

try {
    $profiles = Invoke-JsonGet -url $profilesUrl
    $profileCount = @($profiles.profiles.PSObject.Properties.Name).Count
    $okProfiles = ($profileCount -ge 16)
    Write-Step "Profiles Endpoint" $okProfiles ("count=" + $profileCount)
    $results += $okProfiles
    $detailMap.profiles_ok = $okProfiles
    $detailMap.profile_count = $profileCount
} catch {
    Write-Step "Profiles Endpoint" $false $_.Exception.Message
    $results += $false
    $detailMap.profiles_ok = $false
    $detailMap.profile_count = $null
}

$cases = @(
    @{ Name = "whitelist pass"; Input = "dragon_quant" },
    @{ Name = "bull pattern"; Input = "bull_custom_agent" },
    @{ Name = "bear pattern"; Input = "bear_runtime" },
    @{ Name = "unknown fallback"; Input = "non_mapped_id_x" }
)

foreach ($c in $cases) {
    $eventId = "smoke-" + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $payload = @{
        timestamp = [DateTime]::UtcNow.ToString("o")
        active_character_id = $c.Input
        risk_level = "WARNING"
        public_signal_direction = "HOLD"
        abstract_reason = "e2e smoke " + $c.Name
        schema_version = "public-event.v1"
        event_id = $eventId
        # Use top-priority source so mapping checks remain valid
        # after source-priority policy is enforced.
        source = "ops_showroom_bundle_v1"
    }

    try {
        $post = Invoke-JsonPost -url $ingestUrl -body $payload
        $latest = Wait-LatestEvent -url $latestUrl -expectedEventId $eventId -waitMs 4200
        $expected = Expected-CharacterId -rawId $c.Input
        $postOk = ($null -ne $post) -and (($post.ok -eq $true) -or ([string]$post.event_id -eq $eventId))
        $latestOk = ($null -ne $latest) -and ([string]$latest.event_id -eq $eventId)
        $actual = if ($null -ne $latest) { [string]$latest.active_character_id } else { "<no-latest-match>" }
        $ok = $postOk -and $latestOk -and ($actual -eq $expected)
        $detail = "in=" + $c.Input + "; expected=" + $expected + "; actual=" + $actual
        Write-Step ("Character Mapping - " + $c.Name) $ok $detail
        $results += $ok
        $detailMap["mapping_" + ($c.Name -replace "\s+","_")] = $ok
    } catch {
        Write-Step ("Character Mapping - " + $c.Name) $false $_.Exception.Message
        $results += $false
        $detailMap["mapping_" + ($c.Name -replace "\s+","_")] = $false
    }
}

try {
    $highEventId = "smoke-hi-" + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $highPayload = @{
        timestamp = [DateTime]::UtcNow.ToString("o")
        active_character_id = "dragon_quant"
        risk_level = "WARNING"
        public_signal_direction = "HOLD"
        abstract_reason = "e2e smoke high-priority anchor"
        schema_version = "public-event.v1"
        event_id = $highEventId
        source = "ops_showroom_bundle_v1"
    }
    $highPost = Invoke-JsonPost -url $ingestUrl -body $highPayload
    $highLatest = Wait-LatestEvent -url $latestUrl -expectedEventId $highEventId -waitMs 4200
    $highOk = ($null -ne $highPost) -and ($null -ne $highLatest) -and ([string]$highLatest.source -eq "ops_showroom_bundle_v1")
    Write-Step "Priority Anchor Publish" $highOk ("event_id=" + $highEventId + "; source=" + [string]$highLatest.source)
    $results += $highOk
    $detailMap.priority_anchor_publish_ok = $highOk

    $lowEventId = "smoke-lo-" + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $lowPayload = @{
        timestamp = [DateTime]::UtcNow.ToString("o")
        active_character_id = "unknown_guard"
        risk_level = "INFO"
        public_signal_direction = "HOLD"
        abstract_reason = "e2e smoke low-priority heartbeat"
        schema_version = "public-event.v1"
        event_id = $lowEventId
        source = "linux_runtime_heartbeat"
    }
    $lowPost = Invoke-JsonPost -url $ingestUrl -body $lowPayload
    Start-Sleep -Milliseconds 500
    $latestAfterLow = Invoke-JsonGet -url $latestUrl
    $priorityOk = ($null -ne $lowPost) -and ([string]$latestAfterLow.event_id -eq $highEventId) -and ([string]$latestAfterLow.source -eq "ops_showroom_bundle_v1")
    $priorityDetail = "after_low(event_id=" + [string]$latestAfterLow.event_id + "; source=" + [string]$latestAfterLow.source + ")"
    Write-Step "Source Priority Protection" $priorityOk $priorityDetail
    $results += $priorityOk
    $detailMap.source_priority_protection_ok = $priorityOk
} catch {
    Write-Step "Source Priority Protection" $false $_.Exception.Message
    $results += $false
    $detailMap.source_priority_protection_ok = $false
}

try {
    $final = Invoke-JsonGet -url $latestUrl
    $required = @("timestamp","active_character_id","risk_level","public_signal_direction","abstract_reason","schema_version","event_id","source")
    $missing = @()
    foreach ($k in $required) {
        if (-not ($final.PSObject.Properties.Name -contains $k)) { $missing += $k }
    }
    $okSchema = ($missing.Count -eq 0)
    $schemaDetail = "required keys present"
    if (-not $okSchema) {
        $schemaDetail = "missing: " + ($missing -join ", ")
    }
    Write-Step "Latest Schema Integrity" $okSchema $schemaDetail
    $results += $okSchema
    $detailMap.schema_ok = $okSchema

    # Ensure we validate against showroom bundle payload (not a transient smoke anchor event).
    if ((Test-Path -LiteralPath $bundleBuildScript) -and (Test-Path -LiteralPath $bundlePublishScript)) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $bundleBuildScript | Out-Null
        if ($LASTEXITCODE -eq 0) {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $bundlePublishScript | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Start-Sleep -Milliseconds 500
                $final = Invoke-JsonGet -url $latestUrl
            }
        }
    }

    $signalGateRequired = @("signal_total_count","integrated_signal","singular_action","singular_decision","lock_reason")
    $signalGateMissing = @()
    $signalGate = $null
    if ($final.PSObject.Properties.Name -contains "signal_gate_public") {
        $signalGate = $final.signal_gate_public
    }
    foreach ($k in $signalGateRequired) {
        if ($null -eq $signalGate -or -not ($signalGate.PSObject.Properties.Name -contains $k)) {
            $signalGateMissing += $k
        }
    }
    $signalGateOk = ($signalGateMissing.Count -eq 0)
    $signalGateDetail = if ($signalGateOk) {
        "signal_gate_public present"
    } else {
        "missing: " + ($signalGateMissing -join ", ")
    }
    Write-Step "Signal Gate Public Fields" $signalGateOk $signalGateDetail
    $results += $signalGateOk
    $detailMap.signal_gate_public_ok = $signalGateOk
} catch {
    Write-Step "Latest Schema Integrity" $false $_.Exception.Message
    $results += $false
    $detailMap.schema_ok = $false
    Write-Step "Signal Gate Public Fields" $false $_.Exception.Message
    $results += $false
    $detailMap.signal_gate_public_ok = $false
}

try {
    $showroomResp = Invoke-WebRequest -Uri $showroomUrl -Method GET -UseBasicParsing -TimeoutSec $TimeoutSec
    $html = [string]$showroomResp.Content
    $hasQualityTag = $html.Contains("quality=")
    $hasFpsTag = $html.Contains("fps=")
    $hasQualityState = $html.Contains("quality: ""high""")
    $showroomOk = $hasQualityTag -and $hasFpsTag -and $hasQualityState
    $detail = "quality_tag=" + $hasQualityTag + "; fps_tag=" + $hasFpsTag + "; quality_state=" + $hasQualityState
    Write-Step "Showroom Quality Hooks" $showroomOk $detail
    $results += $showroomOk
    $detailMap.showroom_quality_hooks_ok = $showroomOk
} catch {
    Write-Step "Showroom Quality Hooks" $false $_.Exception.Message
    $results += $false
    $detailMap.showroom_quality_hooks_ok = $false
}

try {
    $runtimeCheckOk = $false
    $runtimeCheckDetail = "bundle runtime unavailable"
    if (Test-Path -LiteralPath $bundleBuildScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $bundleBuildScript | Out-Null
        $buildExit = $LASTEXITCODE
        if ($buildExit -eq 0) {
            $rt = Read-BundleRuntime -path $bundlePath
            if ($null -ne $rt) {
                $hasAge = $rt.PSObject.Properties.Name -contains "context_age_seconds"
                $hasTtl = $rt.PSObject.Properties.Name -contains "context_ttl_seconds"
                $hasStale = $rt.PSObject.Properties.Name -contains "context_stale"
                $runtimeCheckOk = $hasAge -and $hasTtl -and $hasStale
                $runtimeCheckDetail = "age=" + [string]$rt.context_age_seconds + "; ttl=" + [string]$rt.context_ttl_seconds + "; stale=" + [string]$rt.context_stale
            } else {
                $runtimeCheckDetail = "bundle runtime parse failed"
            }
        } else {
            $runtimeCheckDetail = "bundle build failed"
        }
    } else {
        $runtimeCheckDetail = "build_showroom_display_bundle.ps1 missing"
    }
    Write-Step "TTL Runtime Fields" $runtimeCheckOk $runtimeCheckDetail
    $results += $runtimeCheckOk
    $detailMap.ttl_runtime_fields_ok = $runtimeCheckOk
} catch {
    Write-Step "TTL Runtime Fields" $false $_.Exception.Message
    $results += $false
    $detailMap.ttl_runtime_fields_ok = $false
}

$allOk = -not ($results -contains $false)
$reportObj = [ordered]@{
    schema = "jemaai_public_event_e2e_smoke_v3"
    checked_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    api_base = $ApiBaseUrl
    overall_ok = $allOk
    checks = $detailMap
}
$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
$reportObj | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
if ($allOk) {
    Write-Host "Overall: READY (E2E smoke)" -ForegroundColor Green
    exit 0
}

Write-Host "Overall: INCOMPLETE (E2E smoke)" -ForegroundColor Yellow
exit 1
