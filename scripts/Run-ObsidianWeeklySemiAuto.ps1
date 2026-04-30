param(
    [string]$VaultRoot = "",
    [string]$ContextSubdir = "obsidian_context",
    [string]$OutputDir = "C:\workspace\reports\obsidian_weekly"
)

$ErrorActionPreference = "Stop"

function Normalize-Title([string]$name) {
    $base = [System.IO.Path]::GetFileNameWithoutExtension($name)
    # Remove leading date/time prefixes like 20260322_1700_
    $base = $base -replace '^\d{8}(?:[_-]\d{2,4})?[_-]?', ''
    return $base.Trim().ToLowerInvariant()
}

function Resolve-VaultRoot([string]$candidateRoot) {
    if ($candidateRoot -and (Test-Path -LiteralPath $candidateRoot)) {
        return $candidateRoot
    }
    if (-not (Test-Path -LiteralPath "G:\")) {
        return $null
    }
    try {
        $dirs = Get-ChildItem -LiteralPath "G:\" -Directory -ErrorAction Stop
        foreach ($d in $dirs) {
            $probe = Join-Path (Join-Path $d.FullName "MKM_DATA_VAULT") "vault"
            if (Test-Path -LiteralPath $probe) {
                return $probe
            }
        }
    } catch {
        return $null
    }
    return $null
}

$resolvedVaultRoot = Resolve-VaultRoot -candidateRoot $VaultRoot
if (-not $resolvedVaultRoot) {
    throw "Could not resolve MKM_DATA_VAULT\\vault path on G: drive."
}

$contextRoot = Join-Path $resolvedVaultRoot $ContextSubdir
if (-not (Test-Path -LiteralPath $contextRoot)) {
    throw "Obsidian context path not found: $contextRoot"
}

$rawResearchPath = Join-Path $contextRoot "raw_research"
$allMd = @(Get-ChildItem -LiteralPath $contextRoot -Recurse -File -Filter "*.md" -ErrorAction SilentlyContinue)
$rawMd = @()
if (Test-Path -LiteralPath $rawResearchPath) {
    $rawMd = @(Get-ChildItem -LiteralPath $rawResearchPath -Recurse -File -Filter "*.md" -ErrorAction SilentlyContinue)
}

$grouped = $allMd | Group-Object { Normalize-Title $_.Name } | Where-Object { $_.Count -gt 1 } |
    Sort-Object Count -Descending

$duplicateCandidates = @()
foreach ($g in $grouped) {
    $duplicateCandidates += [ordered]@{
        normalized_title = $g.Name
        count = $g.Count
        files = @($g.Group | Sort-Object LastWriteTime -Descending | Select-Object -ExpandProperty FullName)
    }
}

$top3 = @($rawMd | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object {
    [ordered]@{
        file = $_.FullName
        updated_at = $_.LastWriteTime.ToString("o")
    }
})

if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$ts = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHHmmssZ")
$jsonPath = Join-Path $OutputDir "obsidian_weekly_semi_auto_latest.json"
$mdPath = Join-Path $OutputDir "obsidian_weekly_semi_auto_latest.md"

$payload = [ordered]@{
    schema = "obsidian_weekly_semi_auto_v1"
    generated_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    context_root = $contextRoot
    total_md_count = $allMd.Count
    raw_research_count = $rawMd.Count
    duplicate_candidate_count = $duplicateCandidates.Count
    duplicate_candidates = $duplicateCandidates
    top3_raw_research = $top3
    recommended_actions = @(
        "Keep only this week's top 3 in active NotebookLM source set.",
        "Mark non-SSOT conclusions with [HYPO] in Obsidian notes.",
        "Merge duplicate-title notes and keep the newest file as canonical."
    )
}

$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$lines = @()
$lines += "# Obsidian Weekly Semi-Auto Report"
$lines += ""
$lines += "- Generated (UTC): $($payload.generated_at_utc)"
$lines += "- Context root: $($payload.context_root)"
$lines += "- Markdown files: $($payload.total_md_count)"
$lines += "- raw_research files: $($payload.raw_research_count)"
$lines += "- Duplicate candidates: $($payload.duplicate_candidate_count)"
$lines += ""
$lines += "## Top3 raw_research (recent)"
foreach ($item in $top3) {
    $lines += "- $($item.updated_at) :: $($item.file)"
}
$lines += ""
$lines += "## Recommended Actions"
foreach ($a in $payload.recommended_actions) {
    $lines += "- $a"
}

Set-Content -LiteralPath $mdPath -Value ($lines -join "`r`n") -Encoding UTF8

Write-Host ("[obsidian-weekly] WROTE: {0}" -f $jsonPath)
Write-Host ("[obsidian-weekly] WROTE: {0}" -f $mdPath)
exit 0
