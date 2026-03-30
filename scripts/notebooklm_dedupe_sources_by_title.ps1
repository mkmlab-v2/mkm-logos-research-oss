<#
.SYNOPSIS
  NotebookLM 노트북에서 동일 display title(정규화 후) 중복 소스를 정리합니다.

.DESCRIPTION
  `nlm notebook get --json`으로 소스 목록을 받아, 제목을 Trim + 연속 공백 축약한 뒤
  같은 키가 여러 개이면 **sources 배열 순서상 마지막 id만 유지**하고 나머지를 삭제합니다.
  (정책: docs/NotebookLM_sources_manifest.md 작전지휘부 메모와 동일)

  전제: PATH에 `nlm`(NotebookLM CLI)이 있고, 해당 프로필로 로그인되어 있어야 합니다.

.PARAMETER NotebookId
  대상 노트북 UUID (기본: 작전지휘부 Ops20260318)

.PARAMETER WhatIf
  삭제하지 않고 제거 대상 source id와 제목만 출력합니다.

.EXAMPLE
  powershell -File scripts\notebooklm_dedupe_sources_by_title.ps1 -WhatIf

.EXAMPLE
  powershell -File scripts\notebooklm_dedupe_sources_by_title.ps1 -Confirm
#>
param(
    [string]$NotebookId = "347e5cbe-0ade-4615-9aac-8747d4fa644e",
    [switch]$WhatIf,
    [switch]$Confirm
)

$ErrorActionPreference = "Stop"

function Normalize-Title([string]$t) {
    if ($null -eq $t) { return "" }
    $x = $t.Trim()
    while ($x -match "  ") {
        $x = $x -replace "  ", " "
    }
    return $x
}

if (-not (Get-Command nlm -ErrorAction SilentlyContinue)) {
    throw "nlm not found in PATH (install NotebookLM CLI / add to PATH)."
}

$raw = & nlm notebook get $NotebookId --json 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "nlm notebook get failed: $raw"
}

$d = $raw | ConvertFrom-Json
$val = $d.value
if (-not $val) { $val = $d }
$sources = $val.sources
if (-not $sources) {
    throw "No sources in API response."
}

# normalized title -> id list in encounter order (same as API sources order)
$byTitle = @{}
foreach ($s in $sources) {
    $nt = Normalize-Title $s.title
    if (-not $byTitle.ContainsKey($nt)) {
        $byTitle[$nt] = New-Object System.Collections.Generic.List[string]
    }
    $byTitle[$nt].Add($s.id)
}

$toDelete = New-Object System.Collections.Generic.List[string]
foreach ($entry in $byTitle.GetEnumerator()) {
    $ids = $entry.Value
    if ($ids.Count -le 1) { continue }
    for ($i = 0; $i -lt $ids.Count - 1; $i++) {
        $toDelete.Add($ids[$i])
    }
}

if ($toDelete.Count -eq 0) {
    Write-Host "No duplicate titles after normalization. notebook_id=$NotebookId sources=$($sources.Count)"
    exit 0
}

Write-Host "Duplicate title groups found; will remove $($toDelete.Count) source(s) (keep last id per title key)."
foreach ($id in $toDelete) {
    Write-Host "  delete $id"
}

if ($WhatIf) {
    Write-Host "(WhatIf) no deletion performed."
    exit 0
}

if (-not $Confirm) {
    throw "Refusing to delete without -Confirm. Re-run with -Confirm or use -WhatIf first."
}

& nlm source delete @toDelete --confirm
if ($LASTEXITCODE -ne 0) {
    throw "nlm source delete failed with exit $LASTEXITCODE"
}

Write-Host "Done. Removed $($toDelete.Count) duplicate source(s)."
