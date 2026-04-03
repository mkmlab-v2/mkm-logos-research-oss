<#
.SYNOPSIS
  Fact-Lock: compare PowerShell $variable tokens in an agent review against a source script; flag "ghost" symbols not present in the source.

.DESCRIPTION
  Spike for local-model review QA. Extracts $identifiers from review text (optionally ${...}) and fails if any are not found as literal substrings in the source file.
  Does not prove semantic correctness — only catches invented symbol names like $I_0 when the script uses $snapshotExit.

.PARAMETER SourcePath
  Path to the authoritative .ps1 (or text) file.

.PARAMETER ReviewPath
  Path to a file containing the model's review text.

.PARAMETER ReviewText
  Inline review text (used when ReviewPath is empty).

.PARAMETER Json
  Emit one JSON object to stdout (still sets exit code).

.NOTES
  Excludes common automatic variables ($null, $true, ...) to reduce false positives from generic prose.
  Exit: 0 = no ghost symbols; 1 = ghosts found or input error; 2 = source/read failure.
#>
param(
    [Parameter(Mandatory = $true)][string]$SourcePath,
    [string]$ReviewPath = "",
    [string]$ReviewText = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$autoExclude = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($n in @(
        "true", "false", "null", "_", "PSItem", "args", "input", "Error", "ErrorActionPreference",
        "Host", "Home", "PWD", "ShellId", "StackTrace", "Matches", "LastExitCode", "MyInvocation",
        "PSBoundParameters", "PSScriptRoot", "PID", "foreach", "switch", "env", "Global"
    )) { [void]$autoExclude.Add($n) }

function Get-ReviewBody {
    if (-not [string]::IsNullOrWhiteSpace($ReviewPath)) {
        if (-not (Test-Path -LiteralPath $ReviewPath)) {
            throw "ReviewPath not found: $ReviewPath"
        }
        return [System.IO.File]::ReadAllText($ReviewPath)
    }
    if (-not [string]::IsNullOrWhiteSpace($ReviewText)) {
        return $ReviewText
    }
    throw "Provide -ReviewPath or -ReviewText."
}

try {
    if (-not (Test-Path -LiteralPath $SourcePath)) {
        Write-Error "SourcePath not found: $SourcePath"
        exit 2
    }
    $sourceRaw = [System.IO.File]::ReadAllText($SourcePath)
    $reviewRaw = Get-ReviewBody
}
catch {
    Write-Error $_.Exception.Message
    exit 2
}

# $word and ${word}
$rxVar = [regex]'(?<!\$)\$(?:\{([^}]+)\}|([A-Za-z_][\w:]*))'
$found = [System.Collections.Generic.List[string]]::new()
$seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)

foreach ($m in $rxVar.Matches($reviewRaw)) {
    $name = if ($m.Groups[1].Success) { $m.Groups[1].Value.Trim() } else { $m.Groups[2].Value }
    if ([string]::IsNullOrWhiteSpace($name)) { continue }
    if ($seen.Contains($name)) { continue }
    [void]$seen.Add($name)
    if ($autoExclude.Contains($name)) { continue }
    # Skip obvious non-PS tokens (${...} with spaces)
    if ($name -match '\s') { continue }

    $needle = if ($m.Groups[1].Success) { "`${$name}" } else { "`$$name" }
    if ($sourceRaw.IndexOf($needle, [StringComparison]::Ordinal) -lt 0) {
        $found.Add($name)
    }
}

$ghosts = @($found)
$ok = ($ghosts.Count -eq 0)
$payload = [ordered]@{
    schema          = "agent_review_symbol_lock_v1"
    ts_utc          = [DateTimeOffset]::UtcNow.ToString("o")
    source_path     = $SourcePath
    ghost_count     = $ghosts.Count
    ghost_variables = $ghosts
    status          = if ($ok) { "PASS" } else { "REJECTED" }
}

if ($Json) {
    $payload | ConvertTo-Json -Compress -Depth 6
}
else {
    if ($ok) {
        Write-Host "OK: no ghost `$variables vs source ($SourcePath)."
    }
    else {
        Write-Host "REJECTED: ghost symbols not in source:" -ForegroundColor Red
        foreach ($g in $ghosts) { Write-Host "  - `$$g" }
    }
}

exit $(if ($ok) { 0 } else { 1 })
