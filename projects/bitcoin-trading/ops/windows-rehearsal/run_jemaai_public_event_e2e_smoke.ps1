param(
    [string]$ApiBaseUrl = "https://api.jemaai.cloud",
    [int]$TimeoutSec = 10,
    [string]$PublicEventToken = $env:PUBLIC_EVENT_GATEWAY_TOKEN,
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\jemaai_e2e_smoke_report_latest.json"
)

$ErrorActionPreference = "Stop"

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

$latestUrl = $ApiBaseUrl.TrimEnd("/") + "/api/public-events/latest"
$ingestUrl = $ApiBaseUrl.TrimEnd("/") + "/api/public-events/ingest"
$profilesUrl = $ApiBaseUrl.TrimEnd("/") + "/character_profiles_v1_1.json"
$showroomUrl = $ApiBaseUrl.TrimEnd("/") + "/public_showroom_poll.html"

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
        source = "ops_e2e_smoke"
    }

    try {
        $post = Invoke-JsonPost -url $ingestUrl -body $payload
        $latest = Wait-LatestEvent -url $latestUrl -expectedEventId $eventId -waitMs 2600
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
} catch {
    Write-Step "Latest Schema Integrity" $false $_.Exception.Message
    $results += $false
    $detailMap.schema_ok = $false
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

$allOk = -not ($results -contains $false)
$reportObj = [ordered]@{
    schema = "jemaai_public_event_e2e_smoke_v2"
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
