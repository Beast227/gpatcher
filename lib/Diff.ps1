function Invoke-HDiffz {
    param(
        [Parameter(Mandatory)][string]$OldFile,
        [Parameter(Mandatory)][string]$NewFile,
        [Parameter(Mandatory)][string]$PatchOut
    )
    $binName = if (Test-IsWindows) { 'hdiffz.exe' } else { 'hdiffz' }
    $exe = Get-BinPath $binName
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "$binName not found at $exe. Run tools/fetch-hdiffpatch.ps1."
    }
    if (-not (Test-IsWindows)) {
        & chmod +x $exe 2>$null
    }
    & $exe -f $OldFile $NewFile $PatchOut 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "hdiffz failed (exit $LASTEXITCODE) on $OldFile -> $NewFile"
    }
}

function Invoke-HPatchz {
    param(
        [Parameter(Mandatory)][string]$OldFile,
        [Parameter(Mandatory)][string]$PatchFile,
        [Parameter(Mandatory)][string]$NewOut
    )
    $binName = if (Test-IsWindows) { 'hpatchz.exe' } else { 'hpatchz' }
    $exe = Get-BinPath $binName
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "$binName not found at $exe. Run tools/fetch-hdiffpatch.ps1."
    }
    if (-not (Test-IsWindows)) {
        & chmod +x $exe 2>$null
    }
    & $exe -f $OldFile $PatchFile $NewOut 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "hpatchz failed (exit $LASTEXITCODE) on $OldFile + $PatchFile"
    }
}
