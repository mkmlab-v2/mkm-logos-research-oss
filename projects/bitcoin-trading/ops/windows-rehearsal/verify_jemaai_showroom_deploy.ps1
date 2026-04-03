param(
    [string]$GatewayBaseUrl = "https://api.jemaai.cloud",
    [string]$PublicApiBaseUrl = "",
    [string]$ProfilesUrl = "",
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
    return [pscustomobject]@{ Ok = $true; Detail = "latest OK"; Headers = $r.Headers; BodyObject = $obj }
}

function Test-CharacterProfiles([string]$url) {
    try {
        $r = Invoke-JsonGet -url $url
        if ($r.StatusCode -lt 200 -or $r.StatusCode -ge 300) {
            return [pscustomobject]@{ Ok = $false; Detail = "HTTP $($r.StatusCode)"; Profiles = @() }
        }
        $obj = $r.Body | ConvertFrom-Json -ErrorAction Stop
        if (-not $obj.profiles) {
            return [pscustomobject]@{ Ok = $false; Detail = "profiles key missing"; Profiles = @() }
        }
        $names = @($obj.profiles.PSObject.Properties.Name)
        if ($names.Count -lt 4) {
            return [pscustomobject]@{ Ok = $false; Detail = "profiles too small ($($names.Count))"; Profiles = $names }
        }
        if (-not ($names -contains "unknown_guard")) {
            return [pscustomobject]@{ Ok = $false; Detail = "unknown_guard missing"; Profiles = $names }
        }
        return [pscustomobject]@{ Ok = $true; Detail = "profiles OK ($($names.Count))"; Profiles = $names }
    } catch {
        return [pscustomobject]@{ Ok = $false; Detail = $_.Exception.Message; Profiles = @() }
    }
}

function Test-CharacterProfilesFromFile([string]$path) {
    try {
        if (-not (Test-Path -LiteralPath $path)) {
            return [pscustomobject]@{ Ok = $false; Detail = "file missing"; Profiles = @() }
        }
        $obj = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
        if (-not $obj.profiles) {
            return [pscustomobject]@{ Ok = $false; Detail = "profiles key missing"; Profiles = @() }
        }
        $names = @($obj.profiles.PSObject.Properties.Name)
        if ($names.Count -lt 4) {
            return [pscustomobject]@{ Ok = $false; Detail = "profiles too small ($($names.Count))"; Profiles = $names }
        }
        if (-not ($names -contains "unknown_guard")) {
            return [pscustomobject]@{ Ok = $false; Detail = "unknown_guard missing"; Profiles = $names }
        }
        return [pscustomobject]@{ Ok = $true; Detail = "profiles OK ($($names.Count))"; Profiles = $names }
    } catch {
        return [pscustomobject]@{ Ok = $false; Detail = $_.Exception.Message; Profiles = @() }
    }
}

function Get-HeaderValue($headers, [string]$name) {
    if ($null -eq $headers) { return "" }
    try {
        return [string]$headers[$name]
    } catch {
        return ""
    }
}

function Test-UrlStatus([string]$url) {
    try {
        $r = Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -TimeoutSec 8
        return [pscustomobject]@{ Url = $url; StatusCode = [int]$r.StatusCode; Ok = $true; Error = "" }
    } catch {
        $statusCode = $null
        try {
            $statusCode = $_.Exception.Response.StatusCode.value__
        } catch { }
        return [pscustomobject]@{ Url = $url; StatusCode = $statusCode; Ok = $false; Error = $_.Exception.Message }
    }
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
    $serverHeader = ""
    try {
        $serverHeader = [string]$_.Exception.Response.Headers["Server"]
    } catch { }
    $platformHeader = ""
    try {
        $platformHeader = [string]$_.Exception.Response.Headers["platform"]
    } catch { }
    $hint = ""
    if ($serverHeader -match "hcdn" -or $platformHeader -match "hostinger") {
        $hint = " (hint: domain appears to terminate at Hostinger/CDN, not this VPS nginx)"
    }
    Write-Step "Nginx/API Mapping" $false ($_.Exception.Message + $hint)
    $results += $false
}

if (-not $apiCheck.Ok) {
    # Extra probes: sometimes nginx location differs only by trailing slash / path prefix.
    $altPaths = @(
        "/api/public-events/latest/",
        "/api/public-events/",
        "/public-events/latest",
        "/public-events/",
        "/api/public-events/latest?x=1"
    )
    Write-Host "[probe] Trying alternative endpoint paths to narrow nginx mapping mismatch..." -ForegroundColor DarkCyan
    foreach ($p in $altPaths) {
        $probeUrl = $apiBase.TrimEnd("/") + $p
        $s = Test-UrlStatus -url $probeUrl
        $tag = if ($s.Ok) { "OK" } else { "ERR" }
        Write-Host ("  [{0}] {1} -> {2}" -f $tag, $p, $s.StatusCode) -ForegroundColor DarkGray
    }
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
$corsDetail = "API check unavailable; could not read CORS header."
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

# 3.5) Profiles JSON and latest character_id mapping integrity
$profilesCheck = $null
$resolvedProfilesUrl = if ([string]::IsNullOrWhiteSpace($ProfilesUrl)) {
    if (-not [string]::IsNullOrWhiteSpace($PublicApiBaseUrl)) {
        $PublicApiBaseUrl.TrimEnd("/") + "/character_profiles_v1_1.json"
    } else {
        $GatewayBaseUrl.TrimEnd("/") + "/character_profiles_v1_1.json"
    }
} else { $ProfilesUrl }

$localProfilesPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp\character_profiles_v1_1.json"
$preferLocalProfiles = (
    [string]::IsNullOrWhiteSpace($ProfilesUrl) -and
    [string]::IsNullOrWhiteSpace($PublicApiBaseUrl) -and
    ($GatewayBaseUrl.TrimEnd("/") -eq "http://127.0.0.1:8788")
)

if ($preferLocalProfiles -and (Test-Path -LiteralPath $localProfilesPath)) {
    $profilesCheck = Test-CharacterProfilesFromFile -path $localProfilesPath
    $profilesSource = "local_file"
} else {
    $profilesCheck = Test-CharacterProfiles -url $resolvedProfilesUrl
    $profilesSource = "url"
    if (-not $profilesCheck.Ok) {
        $fallbackCheck = Test-CharacterProfilesFromFile -path $localProfilesPath
        if ($fallbackCheck.Ok) {
            $profilesCheck = $fallbackCheck
            $profilesSource = "local_file"
        }
    }
}
if ($profilesSource -eq "url") {
    Write-Step "Character Profiles JSON" $profilesCheck.Ok ("url=" + $resolvedProfilesUrl + "; " + $profilesCheck.Detail)
} else {
    Write-Step "Character Profiles JSON" $profilesCheck.Ok ("fallback=local_file; path=C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp\character_profiles_v1_1.json; " + $profilesCheck.Detail)
}
$results += $profilesCheck.Ok

$charMapOk = $false
$charMapDetail = "API check unavailable"
if ($apiCheck -and $apiCheck.Ok -and $profilesCheck -and $profilesCheck.Ok) {
    $latestChar = ""
    try {
        $latestChar = [string]$apiCheck.BodyObject.active_character_id
    } catch { }
    $aliasMap = @{
        "horse_quant" = "horse_trend"
    }
    if ([string]::IsNullOrWhiteSpace($latestChar)) {
        $charMapOk = $false
        $charMapDetail = "latest.active_character_id missing"
    } elseif ($profilesCheck.Profiles -contains $latestChar) {
        $charMapOk = $true
        $charMapDetail = "latest.active_character_id maps to profile: $latestChar"
    } elseif ($aliasMap.ContainsKey($latestChar) -and ($profilesCheck.Profiles -contains $aliasMap[$latestChar])) {
        $charMapOk = $true
        $charMapDetail = "latest.active_character_id alias-mapped: $latestChar -> $($aliasMap[$latestChar])"
    } else {
        $charMapOk = $false
        $charMapDetail = "latest.active_character_id not in profiles: $latestChar"
    }
}
Write-Step "Latest Character Mapping" $charMapOk $charMapDetail
$results += $charMapOk

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
        $gatewayBase = $GatewayBaseUrl.TrimEnd("/")
        $pollCandidates = @($gatewayBase, "https://api.jemaai.cloud", "http://127.0.0.1:8788")
        $matchedBase = $null
        foreach ($c in $pollCandidates) {
            if (-not [string]::IsNullOrWhiteSpace($c) -and $poll.Contains($c)) {
                $matchedBase = $c
                break
            }
        }
        $baseOk = -not [string]::IsNullOrWhiteSpace($matchedBase)
        $baseDetail = if ($baseOk) { "poll html base present: $matchedBase" } else { "poll html base string missing for gateway/default candidates" }
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
