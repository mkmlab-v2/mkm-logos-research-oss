param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$SyncFreshnessHours = 168
)

$ErrorActionPreference = "Stop"

function New-CheckResult {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    [ordered]@{
        name   = $Name
        passed = $Passed
        detail = $Detail
    }
}

function Resolve-NotebooklmSyncMarkerPath {
    param([string]$WorkspaceRootValue)

    $candidates = @()
    $candidateRoots = @(
        "G:\MKM_DATA_VAULT\vault\notebooklm_sources",
        "G:\vault\notebooklm_sources",
        (Join-Path $WorkspaceRootValue "vault\notebooklm_sources")
    )

    foreach ($root in $candidateRoots) {
        $marker = Join-Path $root "_LAST_SYNC.txt"
        if (Test-Path -LiteralPath $marker) {
            $candidates += $marker
        }
    }

    $wildCandidates = Get-ChildItem -LiteralPath "G:\" -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.FullName "MKM_DATA_VAULT\vault\notebooklm_sources\_LAST_SYNC.txt" } |
        Where-Object { Test-Path -LiteralPath $_ }
    $candidates += $wildCandidates

    if ($candidates.Count -eq 0) {
        return $null
    }

    $latest = $candidates |
        Sort-Object { (Get-Item -LiteralPath $_).LastWriteTimeUtc } -Descending |
        Select-Object -First 1
    return $latest
}

$results = @()
$utcNow = (Get-Date).ToUniversalTime()

$mcpPath = Join-Path $WorkspaceRoot ".cursor\mcp.json"
if (-not (Test-Path -LiteralPath $mcpPath)) {
    throw "Missing MCP profile: $mcpPath"
}
$mcp = Get-Content -LiteralPath $mcpPath -Raw | ConvertFrom-Json
$results += New-CheckResult -Name "mcp_profile_json" -Passed $true -Detail "Loaded $mcpPath"

$expectedCore = @(
    "filesystem",
    "openchrome",
    "athena-core",
    "sequential-thinking",
    "athena-manseryeok",
    "compression-server",
    "devops-mcp"
)
$optionalServers = @(
    # NotebookLM MCP can be present depending on local auth/session workflow.
    "notebooklm"
)
$actualServers = @($mcp.mcpServers.PSObject.Properties.Name | Sort-Object)
$expectedSorted = @($expectedCore | Sort-Object)
$missing = @($expectedSorted | Where-Object { $_ -notin $actualServers })
$allowed = @($expectedCore + $optionalServers | Sort-Object -Unique)
$extra = @($actualServers | Where-Object { $_ -notin $allowed })
$corePassed = ($missing.Count -eq 0 -and $extra.Count -eq 0)
$coreDetail = "actual=$($actualServers -join ', '); missing=$($missing -join ', '); extra=$($extra -join ', '); optional_present=$(@($optionalServers | Where-Object { $_ -in $actualServers }) -join ', ')"
$results += New-CheckResult -Name "core_mcp_set_exact" -Passed $corePassed -Detail $coreDetail

$forbidden = @("playwright", "manseryeok-mcp")
$foundForbidden = @($forbidden | Where-Object { $_ -in $actualServers })
$forbiddenPassed = ($foundForbidden.Count -eq 0)
$forbiddenDetail = if ($forbiddenPassed) { "No forbidden servers found" } else { "Found: $($foundForbidden -join ', ')" }
$results += New-CheckResult -Name "forbidden_mcp_absent" -Passed $forbiddenPassed -Detail $forbiddenDetail

$athenaCore = $mcp.mcpServers."athena-core"
$ltmMode = $null
if ($athenaCore -and $athenaCore.env) {
    $ltmMode = $athenaCore.env.MKM12_LTM_DB_TYPE
}
$ltmPassed = ($ltmMode -eq "file")
$results += New-CheckResult -Name "athena_core_ltm_file_mode" -Passed $ltmPassed -Detail "MKM12_LTM_DB_TYPE=$ltmMode"

$syncMarkerPath = Resolve-NotebooklmSyncMarkerPath -WorkspaceRootValue $WorkspaceRoot
if (-not $syncMarkerPath) {
    $results += New-CheckResult -Name "notebooklm_sync_marker_exists" -Passed $false -Detail "Could not locate _LAST_SYNC.txt"
    $results += New-CheckResult -Name "notebooklm_sync_fresh" -Passed $false -Detail "Cannot evaluate freshness without marker"
}
else {
    $results += New-CheckResult -Name "notebooklm_sync_marker_exists" -Passed $true -Detail "Found $syncMarkerPath"
    $syncRaw = Get-Content -LiteralPath $syncMarkerPath -Raw
    $utcLine = ($syncRaw -split "`r?`n" | Where-Object { $_ -like "UTC:*" } | Select-Object -First 1)
    $syncUtc = $null
    if ($utcLine) {
        $syncUtcText = $utcLine.Substring(4).Trim()
        try {
            $syncUtc = [datetime]::Parse($syncUtcText).ToUniversalTime()
        }
        catch {
            $syncUtc = $null
        }
    }

    if ($null -eq $syncUtc) {
        $results += New-CheckResult -Name "notebooklm_sync_fresh" -Passed $false -Detail "UTC parse failed from marker"
    }
    else {
        $ageHours = [math]::Round(($utcNow - $syncUtc).TotalHours, 2)
        $freshPassed = ($ageHours -le $SyncFreshnessHours)
        $detail = "age_hours=$ageHours threshold_hours=$SyncFreshnessHours"
        $results += New-CheckResult -Name "notebooklm_sync_fresh" -Passed $freshPassed -Detail $detail
    }
}

$centralPath = Join-Path $WorkspaceRoot "docs\final\CENTRAL_AGENT_MEMORY_V1.md"
if (-not (Test-Path -LiteralPath $centralPath)) {
    $results += New-CheckResult -Name "central_memory_exists" -Passed $false -Detail "Missing $centralPath"
    $results += New-CheckResult -Name "central_memory_has_mcp_entry" -Passed $false -Detail "Cannot verify entry without file"
}
else {
    $results += New-CheckResult -Name "central_memory_exists" -Passed $true -Detail "Found $centralPath"
    $centralRaw = Get-Content -LiteralPath $centralPath -Raw
    $hasMcpEntry = ($centralRaw -match "athena-core\(MKM12_LTM_DB_TYPE=file\)")
    $detail = if ($hasMcpEntry) { "Found athena-core MCP entry in central memory" } else { "athena-core MCP entry missing" }
    $results += New-CheckResult -Name "central_memory_has_mcp_entry" -Passed $hasMcpEntry -Detail $detail
}

$allPassed = @($results | Where-Object { -not $_.passed }).Count -eq 0
$artifact = [ordered]@{
    schema           = "mkm_ai_v2_readiness_check_v1"
    generated_at_utc = $utcNow.ToString("o")
    workspace_root   = $WorkspaceRoot
    overall_passed   = $allPassed
    checks           = $results
}

$artifactDir = Join-Path $WorkspaceRoot "docs\final\artifacts"
if (-not (Test-Path -LiteralPath $artifactDir)) {
    New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
}
$artifactPath = Join-Path $artifactDir "mkm_ai_v2_readiness_latest.json"
$artifact | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $artifactPath -Encoding UTF8

Write-Host "MKM AI v2 readiness artifact written: $artifactPath"
if ($allPassed) {
    Write-Host "OVERALL: PASS"
    exit 0
}

Write-Host "OVERALL: FAIL"
exit 1
