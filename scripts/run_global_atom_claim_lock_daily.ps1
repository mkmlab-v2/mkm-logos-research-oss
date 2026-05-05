param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

py "scripts/check_global_atom_claim_lock_v1.py" --strict
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

py "scripts/check_global_atom_edge_claim_atom_set_v1.py" --strict
exit $LASTEXITCODE
