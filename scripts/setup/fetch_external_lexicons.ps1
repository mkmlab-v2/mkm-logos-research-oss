param(
    [string]$StagingRoot = "C:\workspace\vault\external_lexicon",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

function Ensure-Directory([string]$PathValue) {
    if (-not (Test-Path -LiteralPath $PathValue)) {
        New-Item -ItemType Directory -Path $PathValue -Force | Out-Null
    }
}

function Invoke-GitSync([string]$RepoUrl, [string]$TargetDir) {
    # Windows: avoid checkout failures on very long paths (STEPBible-Data, etc.)
    $lp = @("-c", "core.longpaths=true")
    if (Test-Path -LiteralPath $TargetDir) {
        Write-Host "Updating: $TargetDir"
        & git @lp -C $TargetDir fetch --all --tags --prune | Out-Null
        & git @lp -C $TargetDir pull --ff-only | Out-Null
    } else {
        Write-Host "Cloning: $RepoUrl"
        & git @lp clone $RepoUrl $TargetDir | Out-Null
    }
}

function Remove-RepoDir([string]$TargetDir) {
    if (Test-Path -LiteralPath $TargetDir) {
        Write-Host "Removing previous snapshot: $TargetDir"
        Remove-Item -LiteralPath $TargetDir -Recurse -Force
    }
}

function Sync-StepBibleDataSparse([string]$RepoUrl, [string]$TargetDir) {
    # Full checkout can fail on Windows due to extreme path lengths under Older Formats/Tagged-Bibles.
    # Sparse cone: lexicon-focused corpora only + explicit root metadata extraction.
    $lp = @("-c", "core.longpaths=true")

    Remove-RepoDir $TargetDir
    $parent = [System.IO.Path]::GetDirectoryName($TargetDir)
    Ensure-Directory $parent

    Write-Host "Cloning STEPBible-Data (sparse, longpaths): $RepoUrl"
    & git @lp clone --filter=blob:none --sparse $RepoUrl $TargetDir
    if ($LASTEXITCODE -ne 0) {
        throw "git clone (sparse) failed for STEPBible-Data (exit $LASTEXITCODE)"
    }

    Push-Location $TargetDir
    try {
        & git @lp sparse-checkout init --cone
        if ($LASTEXITCODE -ne 0) {
            throw "sparse-checkout init failed (exit $LASTEXITCODE)"
        }
        & git @lp sparse-checkout set Lexicons "Morphology codes" Versification "Proper Nouns" "Translators Amalgamated OT+NT"
        if ($LASTEXITCODE -ne 0) {
            throw "sparse-checkout set failed (exit $LASTEXITCODE)"
        }
    } finally {
        Pop-Location
    }

    $metaDir = Join-Path $TargetDir "_extracted_repo_root"
    Ensure-Directory $metaDir
    # Avoid case-duplicates: git emits fatal messages to stderr; capture with 2>&1 to prevent PS terminating.
    $metaFiles = @(
        "README.md",
        "LICENSE", "LICENSE.md", "LICENSE.txt", "License.md",
        "COPYING", "NOTICE", "NOTICE.md"
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        foreach ($name in $metaFiles) {
            $outPath = Join-Path $metaDir $name
            if (Test-Path -LiteralPath $outPath) {
                Remove-Item -LiteralPath $outPath -Force -ErrorAction SilentlyContinue
            }
            $allOutput = & git @lp -C $TargetDir show ("HEAD:{0}" -f $name) 2>&1
            if ($LASTEXITCODE -eq 0) {
                $text = (($allOutput | ForEach-Object { "$_" }) -join "`n").Trim()
                if (-not [string]::IsNullOrWhiteSpace($text)) {
                    $text | Set-Content -LiteralPath $outPath -Encoding UTF8
                }
            }
        }
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Get-OptionalGitValue([string]$RepoDir, [string]$Format) {
    try {
        return (git -C $RepoDir log -1 --format=$Format 2>$null).Trim()
    } catch {
        return ""
    }
}

function Get-MatchedFiles([string]$RootDir, [string[]]$Patterns) {
    $items = @()
    foreach ($pattern in $Patterns) {
        $items += Get-ChildItem -Path $RootDir -File -Recurse -Filter $pattern -ErrorAction SilentlyContinue
    }
    return $items | Sort-Object FullName -Unique
}

function Get-RelativePathCompat([string]$BasePath, [string]$TargetPath) {
    $base = [System.IO.Path]::GetFullPath($BasePath)
    if (-not $base.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $base = $base + [System.IO.Path]::DirectorySeparatorChar
    }
    $baseUri = [System.Uri]$base
    $targetUri = [System.Uri]([System.IO.Path]::GetFullPath($TargetPath))
    $relativeUri = $baseUri.MakeRelativeUri($targetUri)
    return [System.Uri]::UnescapeDataString($relativeUri.ToString()).Replace('/', '\')
}

Ensure-Directory $StagingRoot
Ensure-Directory (Join-Path $StagingRoot "sources")

$repos = @(
    [ordered]@{
        id = "openscriptures-morphhb"
        url = "https://github.com/openscriptures/morphhb.git"
        folder = "sources\openscriptures-morphhb"
        role = "precision_rail_hebrew"
        include_patterns = @("*.xml")
    },
    [ordered]@{
        id = "openscriptures-strongs"
        url = "https://github.com/openscriptures/strongs.git"
        folder = "sources\openscriptures-strongs"
        role = "audit_rail_strongs"
        include_patterns = @("*greek*.xml", "*hebrew*.xml", "strongs-dictionary*.xhtml")
    },
    [ordered]@{
        id = "stepbible-data"
        url = "https://github.com/STEPBible/STEPBible-Data.git"
        folder = "sources\stepbible-data"
        role = "audit_cross_validation"
        include_patterns = @("*.txt", "*.tsv", "*.csv", "*.json")
    }
)

$manifestFiles = @()
$repoSummaries = @()

foreach ($repo in $repos) {
    $repoDir = Join-Path $StagingRoot $repo.folder
    Ensure-Directory ([System.IO.Path]::GetDirectoryName($repoDir))
    if ($repo.id -eq "stepbible-data") {
        Sync-StepBibleDataSparse -RepoUrl $repo.url -TargetDir $repoDir
    } else {
        Invoke-GitSync -RepoUrl $repo.url -TargetDir $repoDir
    }

    $head = Get-OptionalGitValue -RepoDir $repoDir -Format "%H"
    $commitTime = Get-OptionalGitValue -RepoDir $repoDir -Format "%cI"
    $licenseFiles = Get-MatchedFiles -RootDir $repoDir -Patterns @("LICENSE*", "COPYING*", "NOTICE*")
    $matchedFiles = Get-MatchedFiles -RootDir $repoDir -Patterns $repo.include_patterns

    foreach ($file in $matchedFiles) {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
        $relative = Get-RelativePathCompat -BasePath $StagingRoot -TargetPath $file.FullName
        $manifestFiles += [ordered]@{
            repo_id = $repo.id
            role = $repo.role
            relative_path = $relative
            sha256 = $hash
            size_bytes = [int64]$file.Length
        }
    }

    $repoSummaries += [ordered]@{
        repo_id = $repo.id
        source_url = $repo.url
        local_path = $repoDir
        role = $repo.role
        head_commit = $head
        head_commit_time_utc = $commitTime
        matched_file_count = @($matchedFiles).Count
        license_files = @($licenseFiles | ForEach-Object { Get-RelativePathCompat -BasePath $StagingRoot -TargetPath $_.FullName })
    }
}

$manifest = [ordered]@{
    schema = "external_lexicon_manifest_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    staging_root = $StagingRoot
    repos = $repoSummaries
    files = $manifestFiles
}

$manifestPath = Join-Path $StagingRoot "MANIFEST.json"
($manifest | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host "Lexicon fetch complete. repos=$($repoSummaries.Count) files=$($manifestFiles.Count)"
Write-Host "Manifest: $manifestPath"

if (-not $SkipPush) {
    & "C:\workspace\scripts\push_external_lexicon_to_vault.ps1" -SourceRoot $StagingRoot
}
