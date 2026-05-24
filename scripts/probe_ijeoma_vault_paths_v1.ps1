# Shallow probe for ijeoma corpus dirs on F: / G: vault
$gVault = $null
if ($env:MKM_VAULT_ROOT -and (Test-Path -LiteralPath $env:MKM_VAULT_ROOT)) {
    $gVault = $env:MKM_VAULT_ROOT
} else {
    $found = Get-ChildItem -Path 'G:\' -Directory -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq 'vault' -and $_.FullName -match 'MKM_DATA_VAULT' } |
        Select-Object -First 1
    if ($found) { $gVault = $found.FullName }
}
$roots = @('F:\BACKUP\MKM_ARCHIVE_FROM_F')
if ($gVault) {
    $roots += $gVault
    $roots += (Join-Path $gVault 'btrack_artifacts_verified')
}
foreach ($r in $roots) {
    if (Test-Path -LiteralPath $r) {
        Write-Host "OK $r"
        Get-ChildItem -LiteralPath $r -Directory -Filter '*ijeoma*' -ErrorAction SilentlyContinue |
            Select-Object -First 10 -ExpandProperty FullName
        Get-ChildItem -LiteralPath $r -Recurse -Filter 'IJEOMA_CHUNK_TABLE*.jsonl' -ErrorAction SilentlyContinue |
            Select-Object -First 3 -ExpandProperty FullName
    } else {
        Write-Host "MISS $r"
    }
}
