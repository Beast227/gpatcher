function Test-IsExcluded {
    param(
        [Parameter(Mandatory)][string]$RelPath,
        [string[]]$CustomExcludes = @()
    )

    $defaultPatterns = @(
        # Saves, userdata, settings
        '(?:^|/|\\)(?:saves?|savegames?|userdata|profiles?)(?:$|/|\\)',
        '\.(?:sav|save)$',
        
        # Steam emulators / cracks settings
        '(?:^|/|\\)(?:steam_settings|steam_saves|steam_autocloud\.vdf)(?:$|/|\\)',
        'steam_emu\.ini$',
        
        # Crash logs and debug symbols
        '(?:^|/|\\)(?:logs?|crashes|crashdumps?)(?:$|/|\\)',
        '\.(?:log|dmp|pdb|tmp|temp)$',
        
        # Cache / temporary
        '(?:^|/|\\)(?:shadercache|cache)(?:$|/|\\)',
        '\.cache$',
        
        # System junk
        'desktop\.ini$',
        'Thumbs\.db$'
    )

    $normalizedPath = $RelPath -replace '\\', '/'

    foreach ($pat in $defaultPatterns) {
        if ($normalizedPath -match $pat) {
            return $true
        }
    }

    foreach ($glob in $CustomExcludes) {
        if ($normalizedPath -like $glob) {
            return $true
        }
    }

    return $false
}

function Get-FileTree {
    param(
        [Parameter(Mandatory)][string]$Root,
        [string[]]$CustomExcludes = @()
    )
    $rootFull = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\','/')
    $files = Get-ChildItem -LiteralPath $rootFull -Recurse -File -Force
    $results = New-Object System.Collections.Generic.List[object]
    $total = $files.Count
    $idx = 0
    $excludedCount = 0

    foreach ($f in $files) {
        Assert-NotReparse -Item $f
        $rel = Get-RelPath -Root $rootFull -Full $f.FullName
        
        if (Test-IsExcluded -RelPath $rel -CustomExcludes $CustomExcludes) {
            $excludedCount++
            $idx++
            continue
        }

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
    if ($excludedCount -gt 0) {
        LogInfo "Excluded $excludedCount non-game file(s) (saves, logs, steam settings, etc.) from $Root"
    }
    ,$results.ToArray()
}
