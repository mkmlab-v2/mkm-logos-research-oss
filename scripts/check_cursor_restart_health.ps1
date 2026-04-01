param(
    [string]$LogsRoot = "$env:APPDATA\Cursor\logs",
    [int]$RecentLines = 1200,
    [switch]$InitBaseline,
    [string]$BaselineFile = "c:/workspace/tmp/cursor_restart_health_baseline.json"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $LogsRoot)) {
    throw "Cursor logs path not found: $LogsRoot"
}

$latestSession = Get-ChildItem -Path $LogsRoot -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latestSession) {
    throw "No Cursor log sessions found under: $LogsRoot"
}

$hookLogs = Get-ChildItem -Path $latestSession.FullName -Recurse -File -Filter "cursor.hooks.log" -ErrorAction SilentlyContinue
$rendererLogs = Get-ChildItem -Path $latestSession.FullName -Recurse -File -Filter "renderer.log" -ErrorAction SilentlyContinue

$patterns = @{
    HookParseError = @(
        "Failed to parse JSON response from hook",
        "Unexpected token 'C', ""C Drive Po""",
        "invalid non-printable character U+FEFF"
    )
    SecurityImportError = @(
        "Security Agent를 import할 수 없습니다",
        "ImportError: cannot import name 'BinanceClient'"
    )
    ExtensionHealth = @(
        "JEMA12 Server Error",
        "TypeError: fetch failed",
        "potential listener LEAK detected"
    )
}

function Count-Matches {
    param(
        [string[]]$Files,
        [string[]]$Needles
    )
    $count = 0
    foreach ($f in $Files) {
        if (-not (Test-Path $f)) { continue }
        try {
            $fs = [System.IO.File]::Open($f, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            $sr = New-Object System.IO.StreamReader($fs)
            $content = $sr.ReadToEnd()
            $sr.Close()
            $fs.Close()
            if ($RecentLines -gt 0) {
                $lines = $content -split "`r?`n"
                if ($lines.Count -gt $RecentLines) {
                    $content = ($lines[($lines.Count - $RecentLines)..($lines.Count - 1)] -join "`n")
                }
            }
        } catch {
            continue
        }
        foreach ($n in $Needles) {
            $count += ([regex]::Matches($content, [regex]::Escape($n))).Count
        }
    }
    return $count
}

function Read-NewContentFromBaseline {
    param(
        [string]$FilePath,
        [long]$StartOffset
    )
    if (-not (Test-Path $FilePath)) { return "" }
    try {
        $fs = [System.IO.File]::Open($FilePath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        if ($StartOffset -lt 0 -or $StartOffset -gt $fs.Length) { $StartOffset = 0 }
        $fs.Seek($StartOffset, [System.IO.SeekOrigin]::Begin) | Out-Null
        $sr = New-Object System.IO.StreamReader($fs)
        $content = $sr.ReadToEnd()
        $sr.Close()
        $fs.Close()
        return $content
    } catch {
        return ""
    }
}

function Normalize-Key {
    param([string]$PathText)
    if (-not $PathText) { return "" }
    return ($PathText -replace "\\", "/").ToLowerInvariant()
}

$hookPaths = @($hookLogs | ForEach-Object { $_.FullName })
$rendererPaths = @($rendererLogs | ForEach-Object { $_.FullName })

if ($InitBaseline) {
    $baselineDir = Split-Path -Parent $BaselineFile
    if (-not (Test-Path $baselineDir)) {
        New-Item -ItemType Directory -Path $baselineDir -Force | Out-Null
    }
    $baseline = [ordered]@{
        session = $latestSession.Name
        ts = (Get-Date).ToString("o")
        files = @{}
    }
    foreach ($p in (@($hookPaths) + @($rendererPaths))) {
        if (Test-Path $p) {
            $fi = Get-Item $p
            $k = Normalize-Key -PathText $p
            $baseline.files[$k] = [ordered]@{
                length = [long]$fi.Length
            }
        }
    }
    $baselineJson = $baseline | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText(
        $BaselineFile,
        $baselineJson,
        (New-Object System.Text.UTF8Encoding($false))
    )
    Write-Output (@{ status = "BASELINE_SAVED"; baseline_file = $BaselineFile; session = $latestSession.Name; ts = (Get-Date).ToString("o") } | ConvertTo-Json -Depth 4)
    exit 0
}

$useBaseline = Test-Path $BaselineFile
if ($useBaseline) {
    try {
        $rawBaseline = Get-Content -Path $BaselineFile -Raw
        if ($rawBaseline.Length -gt 0 -and [int][char]$rawBaseline[0] -eq 65279) {
            $rawBaseline = $rawBaseline.Substring(1)
        }
        $baseline = $rawBaseline | ConvertFrom-Json
    } catch {
        $useBaseline = $false
    }
}

if ($useBaseline) {
    $hookParseErrorCount = 0
    $securityImportErrorCount = 0
    $extensionHealthCount = 0

    foreach ($p in $hookPaths) {
        $start = 0
        $k = Normalize-Key -PathText $p
        $entry = $null
        if ($baseline.files.PSObject.Properties.Name -contains $k) {
            $entry = $baseline.files.PSObject.Properties[$k].Value
        }
        if ($entry -and $entry.length) { $start = [long]$entry.length }
        $content = Read-NewContentFromBaseline -FilePath $p -StartOffset $start
        foreach ($n in $patterns.HookParseError) {
            $hookParseErrorCount += ([regex]::Matches($content, [regex]::Escape($n))).Count
        }
        foreach ($n in $patterns.SecurityImportError) {
            $securityImportErrorCount += ([regex]::Matches($content, [regex]::Escape($n))).Count
        }
    }

    foreach ($p in $rendererPaths) {
        $start = 0
        $k = Normalize-Key -PathText $p
        $entry = $null
        if ($baseline.files.PSObject.Properties.Name -contains $k) {
            $entry = $baseline.files.PSObject.Properties[$k].Value
        }
        if ($entry -and $entry.length) { $start = [long]$entry.length }
        $content = Read-NewContentFromBaseline -FilePath $p -StartOffset $start
        foreach ($n in $patterns.ExtensionHealth) {
            $extensionHealthCount += ([regex]::Matches($content, [regex]::Escape($n))).Count
        }
    }
} else {
    $hookParseErrorCount = Count-Matches -Files $hookPaths -Needles $patterns.HookParseError
    $securityImportErrorCount = Count-Matches -Files $hookPaths -Needles $patterns.SecurityImportError
    $extensionHealthCount = Count-Matches -Files $rendererPaths -Needles $patterns.ExtensionHealth
}

$status = if ($hookParseErrorCount -eq 0 -and $securityImportErrorCount -eq 0) { "PASS" } else { "FAIL" }
$warnings = @()
if ($extensionHealthCount -gt 0) {
    $warnings += "renderer_extension_health_signals_detected"
}

$report = [ordered]@{
    status = $status
    session = $latestSession.Name
    logs_root = $LogsRoot
    hook_logs = $hookPaths
    renderer_logs = $rendererPaths
    counts = [ordered]@{
        hook_parse_errors = $hookParseErrorCount
        security_import_errors = $securityImportErrorCount
        extension_health_errors = $extensionHealthCount
    }
    warnings = $warnings
    baseline_mode = $useBaseline
    baseline_file = $BaselineFile
    ts = (Get-Date).ToString("o")
}

$json = $report | ConvertTo-Json -Depth 6
Write-Output $json

if ($status -eq "FAIL") {
    exit 1
}
exit 0
