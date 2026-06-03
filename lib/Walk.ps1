function Get-FileTree {
    param(
        [Parameter(Mandatory)][string]$Root
    )
    $rootFull = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\','/')
    $files = Get-ChildItem -LiteralPath $rootFull -Recurse -File -Force
    $results = New-Object System.Collections.Generic.List[object]
    $total = $files.Count
    $idx = 0
    foreach ($f in $files) {
        Assert-NotReparse -Item $f
        $rel = Get-RelPath -Root $rootFull -Full $f.FullName
        $sha = Get-FileSha256 -Path $f.FullName
        $results.Add([pscustomobject]@{
            RelPath = $rel
            Size    = $f.Length
            Sha256  = $sha
        })
        $idx++
        if ($idx % 25 -eq 0 -or $idx -eq $total) {
            $pct = if ($total -gt 0) { ($idx / $total) * 100 } else { 100 }
            Write-Progress -Activity "Hashing $Root" -Status "$idx/$total" -PercentComplete $pct
        }
    }
    Write-Progress -Activity "Hashing $Root" -Completed
    ,$results.ToArray()
}
