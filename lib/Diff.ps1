function Invoke-HDiffz {
    param(
        [Parameter(Mandatory)][string]$OldFile,
        [Parameter(Mandatory)][string]$NewFile,
        [Parameter(Mandatory)][string]$PatchOut
    )
    $exe = Get-BinPath 'hdiffz.exe'
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "hdiffz.exe not found at $exe. Run tools\fetch-hdiffpatch.ps1."
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
    $exe = Get-BinPath 'hpatchz.exe'
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "hpatchz.exe not found at $exe. Run tools\fetch-hdiffpatch.ps1."
    }
    & $exe -f $OldFile $PatchFile $NewOut 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "hpatchz failed (exit $LASTEXITCODE) on $OldFile + $PatchFile"
    }
}
