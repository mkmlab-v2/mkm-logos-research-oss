param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("lean", "with-openchrome", "base", "research", "ops", "hybrid")]
    [string]$Profile
)

$ErrorActionPreference = "Stop"

$workspace = "C:/workspace"
$profileDir = Join-Path $workspace ".cursor/mcp-profiles"
$targetFile = Join-Path $workspace ".cursor/mcp.json"

$profileMap = @{
    "lean"             = "lean.json"
    "with-openchrome"  = "with-openchrome.json"
    "base"             = "base.json"
    "research"         = "research-manseryeok-compression.json"
    "ops"              = "ops-deploy-hostinger.json"
    "hybrid"           = "hybrid-research-ops.json"
}

$sourceFile = Join-Path $profileDir $profileMap[$Profile]
if (-not (Test-Path $sourceFile)) {
    throw "Profile file not found: $sourceFile"
}

# Validate JSON before applying
$sourceRaw = Get-Content -Raw -Path $sourceFile
$null = $sourceRaw | ConvertFrom-Json

# Write UTF-8 without BOM to reduce parser inconsistencies
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($targetFile, $sourceRaw, $utf8NoBom)

Write-Output "Applied MCP profile: $Profile"
Write-Output "Source: $sourceFile"
Write-Output "Target: $targetFile"
