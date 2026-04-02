param(
    [string]$GatewayBaseUrl = "http://127.0.0.1:8788",
    [string]$PublicApiBaseUrl = "",
    [string]$ExpectedOrigin = "",
    [string]$PollHtmlPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp\public_showroom_poll.html",
    [string]$N8nHeaderJsonPath = "",
    [switch]$AutoFixLocal
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$name, [bool]$ok, [string]$detail) {
    $status = if ($ok) { "PASS" } else { "FAIL" }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host ("[{0}] {1} - {2}" -f $status, $name, $detail) -ForegroundColor $color
}

function Invoke-JsonGet([string]$url) {
    $response = Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -TimeoutSec 8
    [pscustomobject]@{
        StatusCode = [int]$response.StatusCode
        Headers    = $response.Headers
        Body       = $response.Content
    }
}

function Test-ApiLatest([string]$baseUrl) {
    $url = ($baseUrl.TrimEnd("/") + "/api/public-events/latest")
    $r = Invoke-JsonGet -url $url
    if ($r.StatusCode -lt 200 -or $r.StatusCode -ge 300) {
        return [pscustomobject]@{ Ok = $false; Detail = "HTTP $($r.StatusCode)"; Headers = $r.Headers }
    }
    try {
        $obj = $r.Body | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return [pscustomobject]@{ Ok = $false; Detail = "JSON parse failed"; Headers = $r.Headers }
    }
    $required = @("timestamp","active_character_id","risk_level","public_signal_direction","abstract_reason","schema_version","event_id","source")
    foreach ($k in $required) {
        if (-not ($obj.PSObject.Properties.Name -contains $k)) {
            return [pscustomobject]@{ Ok = $false; Detail = "Missing key: $k"; Headers = $r.Headers }
        }
    }
    return [pscustomobject]@{ Ok = $true; Detail = "latest OK"; Headers = $r.Headers }
}

function Test-LocalPort8788 {
    try {
        $listen = Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue
        if ($listen) { return $true }
    } catch { }
    return $false
}

function Fix-PollBaseUrl([string]$path, [string]$newBase) {
    if (-not (Test-Path -LiteralPath $path)) { return $false }
    $content = Get-Content -LiteralPath $path -Raw
    $updated = $content `
        -replace 'value="http://127\.0\.0\.1:8788"', ('value="' + $newBase + '"') `
        -replace 'params\.get\("api"\) \|\| "http://127\.0\.0\.1:8788"', ('params.get("api") || "' + $newBase + '"')
    if ($updated -ne $content) {
        Set-Content -LiteralPath $path -Value $updated -Encoding UTF8
        return $true
    }
    return $false
}

$results = @()

# 1) Nginx/API mapping (observable as /latest health)
$apiBase = if ([string]::IsNullOrWhiteSpace($PublicApiBaseUrl)) { $GatewayBaseUrl } else { $PublicApiBaseUrl }
$apiCheck = $null
try {
    $apiCheck = Test-ApiLatest -baseUrl $apiBase
    Write-Step "Nginx/API Mapping" $apiCheck.Ok ("base=" + $apiBase + "; " + $apiCheck.Detail)
    $results += $apiCheck.Ok
} catch {
    Write-Step "Nginx/API Mapping" $false $_.Exception.Message
    $results += $false
}

# 2) Auth token present for n8n payload path
$tokenOk = $false
$tokenDetail = "N8n header file not provided; checked env only."
if (-not [string]::IsNullOrWhiteSpace($N8nHeaderJsonPath) -and (Test-Path -LiteralPath $N8nHeaderJsonPath)) {
    try {
        $headerJson = Get-Content -LiteralPath $N8nHeaderJsonPath -Raw | ConvertFrom-Json -ErrorAction Stop
        $tokenValue = $headerJson.'X-Public-Event-Token'
        if (-not [string]::IsNullOrWhiteSpace($tokenValue)) {
            $tokenOk = $true
            $tokenDetail = "X-Public-Event-Token key exists in n8n headers."
        } else {
            $tokenDetail = "X-Public-Event-Token missing/empty in n8n headers."
        }
    } catch {
        $tokenDetail = "Could not parse n8n header json."
    }
} else {
    $envToken = [System.Environment]::GetEnvironmentVariable("PUBLIC_EVENT_GATEWAY_TOKEN", "User")
    if (-not [string]::IsNullOrWhiteSpace($envToken)) {
        $tokenOk = $true
        $tokenDetail = "PUBLIC_EVENT_GATEWAY_TOKEN exists in User env."
    } else {
        $tokenDetail = "PUBLIC_EVENT_GATEWAY_TOKEN not found in User env."
    }
}
Write-Step "Auth Token Wiring" $tokenOk $tokenDetail
$results += $tokenOk

# 3) CORS allow-origin
$corsOk = $false
$corsDetail = "Expected origin not provided; skipped strict compare."
if ($apiCheck -and $apiCheck.Headers) {
    $allowOrigin = [string]$apiCheck.Headers["Access-Control-Allow-Origin"]
    if ([string]::IsNullOrWhiteSpace($ExpectedOrigin)) {
        $corsOk = -not [string]::IsNullOrWhiteSpace($allowOrigin)
        $corsDetail = "Gateway allow-origin=" + $allowOrigin
    } else {
        $corsOk = ($allowOrigin -eq "*" -or $allowOrigin -eq $ExpectedOrigin)
        $corsDetail = "allow-origin=" + $allowOrigin + "; expected=" + $ExpectedOrigin
    }
}
Write-Step "CORS / Origin" $corsOk $corsDetail
$results += $corsOk

# 4) Polling UI base URL
$baseOk = $false
$baseDetail = "poll html not found"
if (Test-Path -LiteralPath $PollHtmlPath) {
    $poll = Get-Content -LiteralPath $PollHtmlPath -Raw
    if (-not [string]::IsNullOrWhiteSpace($PublicApiBaseUrl)) {
        $baseOk = $poll.Contains($PublicApiBaseUrl)
        $baseDetail = if ($baseOk) { "poll html contains PublicApiBaseUrl" } else { "poll html does not contain PublicApiBaseUrl" }
        if (-not $baseOk -and $AutoFixLocal) {
            if (Fix-PollBaseUrl -path $PollHtmlPath -newBase $PublicApiBaseUrl) {
                $baseOk = $true
                $baseDetail = "poll html base URL updated automatically"
            }
        }
    } else {
        $baseOk = $poll.Contains("http://127.0.0.1:8788")
        $baseDetail = if ($baseOk) { "poll html currently local default" } else { "local default string missing" }
    }
}
Write-Step "Polling UI Base URL" $baseOk $baseDetail
$results += $baseOk

# 5) Firewall/port (local listener check)
$portOk = Test-LocalPort8788
if (-not $portOk -and $AutoFixLocal) {
    $ensureScript = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\ensure_public_event_gateway.ps1"
    if (Test-Path -LiteralPath $ensureScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $ensureScript -Strict
        Start-Sleep -Seconds 1
        $portOk = Test-LocalPort8788
    }
}
$portDetail = if ($portOk) { "TCP 8788 listening" } else { "TCP 8788 not listening" }
Write-Step "Firewall / Port Reachability" $portOk $portDetail
$results += $portOk

$allOk = -not ($results -contains $false)
if ($allOk) {
    Write-Host "Overall: READY" -ForegroundColor Green
    exit 0
}

Write-Host "Overall: INCOMPLETE (see failed checks above)" -ForegroundColor Yellow
exit 1
